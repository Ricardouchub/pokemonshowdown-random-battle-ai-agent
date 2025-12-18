from __future__ import annotations

import json
from typing import Iterable, List, Optional, Tuple

from ps_agent.llm.deepseek_client import DeepseekClient
from ps_agent.knowledge.feedback import KnowledgeFeedbackStore
from ps_agent.policy.baseline_rules import ActionInsight, BaselinePolicy
from ps_agent.policy.evaluator import Evaluator
from ps_agent.policy.legal_actions import enumerate_legal_actions
from ps_agent.state.battle_state import BattleState
from ps_agent.utils.logger import get_logger

logger = get_logger(__name__)


class LLMPolicy:
    """Policy that queries Deepseek in real time for reasoning and knowledge updates."""

    def __init__(
        self,
        llm: DeepseekClient | None = None,
        baseline: BaselinePolicy | None = None,
        feedback_store: KnowledgeFeedbackStore | None = None,
    ) -> None:
        self.llm = llm or DeepseekClient()
        # Use LookaheadPolicy as the default internal advisor if no baseline provided
        if baseline is None:
            from ps_agent.policy.lookahead import LookaheadPolicy
            self.baseline = LookaheadPolicy()
        else:
            self.baseline = baseline
        self.feedback_store = feedback_store or KnowledgeFeedbackStore()

    def choose_action(
        self, state: BattleState, legal_actions: Optional[Iterable[str]] = None
    ) -> Tuple[str, List[str], List[ActionInsight]]:
        actions_iterable = legal_actions or enumerate_legal_actions(state)
        legal = sorted(set(actions_iterable))
        if not legal:
            raise ValueError("No legal actions available for LLM policy")

        _, ordered_baseline, insights_baseline = self.baseline.choose_action(state, legal)
        llm_response = self._query_llm(state, legal, insights_baseline)
        if not llm_response:
            logger.warning("llm_response_empty", fallback_action=ordered_baseline[0])
            return ordered_baseline[0], ordered_baseline, insights_baseline

        chosen = llm_response.get("action")
        reason = llm_response.get("reason", "")
        knowledge_updates = llm_response.get("knowledge_updates", [])
        if not chosen or chosen not in legal:
            logger.warning(
                "llm_invalid_action",
                chosen=chosen,
                legal=legal,
            )
            chosen = ordered_baseline[0]

        insights: List[ActionInsight] = [
            ActionInsight(
                action=chosen,
                score=llm_response.get("confidence", 0.0),
                breakdown={
                    "score": llm_response.get("confidence", 0.0),
                    "material": llm_response.get("material", 0.0),
                    "position": llm_response.get("position", 0.0),
                    "field_control": llm_response.get("field_control", 0.0),
                    "risk": llm_response.get("risk", 0.0),
                    "wincon_progress": llm_response.get("wincon_progress", 0.0),
                    "llm_reason": reason,
                },
            )
        ] + insights_baseline

        if knowledge_updates:
            self.feedback_store.record(
                {
                    "state_summary": state.summary(),
                    "action": chosen,
                    "updates": knowledge_updates,
                }
            )

        ordered = [chosen] + [act for act in ordered_baseline if act != chosen]
        return chosen, ordered, insights

    def _query_llm(
        self, state: BattleState, legal_actions: List[str], baseline_insights: List[ActionInsight]
    ) -> dict | None:
        summary = state.summary()
        # Include risk/lookahead info in the prompt
        baseline_text = []
        for insight in baseline_insights[:4]:
             risk_info = ""
             if "lookahead_risk" in insight.breakdown:
                 risk_info = f" (Risk: -{round(insight.breakdown['lookahead_risk'], 2)})"
             baseline_text.append(f"{insight.action}:{round(insight.score, 3)}{risk_info}")

        prompt = (
            "You control a Pokemon Showdown Random Battle agent. "
            "You must choose an action from the provided legal actions. "
            "Return a strict JSON object with fields: "
            "`action` (one of the legal actions), "
            "`reason` (short string), "
            "`confidence` (0..1), "
            "`knowledge_updates` (list of {\"type\": str, \"data\": object} entries or empty). "
            "You may also provide optional numeric fields: `material`, `position`, "
            "`field_control`, `risk`, `wincon_progress`. "
            "Be deterministic and avoid randomness."
        )
        user_content = json.dumps(
            {
                "state_summary": summary,
                "legal_actions": legal_actions,
                "baseline_top": baseline_text,
            }
        )
        messages = [
            {"role": "system", "content": prompt},
            {"role": "user", "content": user_content},
        ]
        try:
            response = self.llm.chat(messages)
        except Exception as exc:
            logger.error("llm_request_failed", error=str(exc))
            return None
        try:
            parsed = json.loads(response)
            return parsed
        except json.JSONDecodeError:
            logger.warning("llm_invalid_json", response_preview=response[:200])
            return None
