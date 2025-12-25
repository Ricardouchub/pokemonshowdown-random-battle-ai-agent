from __future__ import annotations

import json
from typing import Iterable, List, Optional, Tuple

from ps_agent.llm.llm_client import LLMClient
from ps_agent.knowledge.feedback import KnowledgeFeedbackStore
from ps_agent.policy.baseline_rules import ActionInsight, BaselinePolicy
from ps_agent.policy.evaluator import Evaluator
from ps_agent.policy.legal_actions import enumerate_legal_actions
from ps_agent.state.battle_state import BattleState
from ps_agent.utils.logger import get_logger

logger = get_logger(__name__)


class LLMPolicy:
    """Policy that queries an LLM in real time for reasoning and knowledge updates."""

    def __init__(
        self,
        llm: LLMClient | None = None,
        baseline: BaselinePolicy | None = None,
        feedback_store: KnowledgeFeedbackStore | None = None,
    ) -> None:
        self.llm = llm or LLMClient()
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
        chain_of_thought = llm_response.get("chain_of_thought", "")
        knowledge_updates = llm_response.get("knowledge_updates", [])
        
        # Validation Logic
        if not chosen or chosen not in legal:
            logger.warning(
                "llm_invalid_action",
                chosen=chosen,
                legal=legal,
            )
            chosen = ordered_baseline[0]
        else:
            # SAFETY CHECK: "Hard Veto" for actions deemed catastrophic by Evaluator
            # (e.g., Infinite Switching Loops with score -5.0)
            # Find the score of the chosen action in baseline insights
            chosen_score = -999.0
            for insight in insights_baseline:
                if insight.action == chosen:
                    chosen_score = insight.score
                    break
            
            # Threshold: -4.0 is the "Guillotine" threshold set in Evaluator for loops
            if chosen_score < -4.0:
                logger.warning(
                    "llm_action_vetoed",
                    action=chosen,
                    score=chosen_score,
                    reason="Action vetoed by Hard Guardrail (Anti-Loop/Suicide)",
                    fallback=ordered_baseline[0]
                )
                # Override with the best safe action
                chosen = ordered_baseline[0]
                # Update reasoning to reflect the override
                reason = f"[VETOED] LLM wanted {llm_response.get('action')} but it was unsafe (Score {chosen_score}). Forced safest option."
                chain_of_thought += f"\n\n[SYSTEM OVERRIDE] Proposed action '{llm_response.get('action')}' was vetoed due to Loop Detection (Score {chosen_score}). Executing fallback."

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
                    "chain_of_thought": chain_of_thought,
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
            "CRITCAL STRATEGIC RULES:\n"
            "1. AVOID SWITCH SPAM: Do NOT switch if you just switched, unless facing guaranteed KO. Penalties are active.\n"
            "2. CHECK TEAM MOVES: Look at 'my_team' to see what your benched Pokemon can do. Do not switch blindly.\n"
            "3. PRIORITIZE ATTACKING: Trading damage is better than losing turns. If in doubt, ATTACK.\n"
            "4. CHECK SPEED: Look at 'speed' and 'base_stats'. Attack if you are faster and can KO. Switch if you are slower and will be KO'd.\n\n"
            "JSON Response Format:\n"
            "{ \"chain_of_thought\": \"1. Analyze matchup. 2. Compare switch vs attack. 3. Decide.\", \"action\": \"...\", \"reason\": \"...\", \"confidence\": 0.9, \"knowledge_updates\": [] }\n"
            "You may also provide optional numeric fields: `material`, `position`, "
            "field_control`, `risk`, `wincon_progress`. "
            "CRITICAL: Do not use status moves (like Toxic, Thunder Wave, Will-O-Wisp, etc.) "
            "if the opponent already has a status condition (par, brn, psn, tox, slp, frz). "
            "CRITICAL: Do not use setup moves (like Swords Dance, Calm Mind, Nasty Plot, Shell Smash) "
            "if you have low HP (<60%) or if you are already boosted (+2 or more). "
            "It is a wasted turn or too risky. "
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
            cleaned = response.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            if cleaned.startswith("```"):
                cleaned = cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            cleaned = cleaned.strip()
            parsed = json.loads(cleaned)
            return parsed
        except json.JSONDecodeError:
            logger.warning("llm_invalid_json", response_preview=response[:200])
            return None
