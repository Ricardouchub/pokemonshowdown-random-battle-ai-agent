from __future__ import annotations

from typing import Dict, Iterable, List, Optional, Tuple

from ps_agent.policy.baseline_rules import ActionInsight, BaselinePolicy
from ps_agent.policy.evaluator import Evaluator
from ps_agent.policy.legal_actions import enumerate_legal_actions
from ps_agent.state.battle_state import BattleState
from ps_agent.state.pokemon_state import PokemonState


class LookaheadPolicy(BaselinePolicy):
    """
    1-Ply Lookahead Policy for Random Battles.
    
    It extends BaselinePolicy but adjusts scores based on anticipating the opponent's 
    best response. Crucially, it handles hidden information by assuming the opponent 
    HAS moves matching their types (STAB) if specific moves are not yet revealed.
    """

    def __init__(self, evaluator: Evaluator | None = None, risk_aversion: float = 1.0) -> None:
        super().__init__(evaluator)
        self.risk_aversion = risk_aversion  # Weight for incoming damage penalty

    def choose_action(
        self,
        state: BattleState,
        legal_actions: Optional[Iterable[str]] = None,
        top_k: int = 3,
    ) -> Tuple[str, List[str], List[ActionInsight]]:
        actions_iterable = legal_actions or enumerate_legal_actions(state)
        actions = sorted(set(actions_iterable))
        if not actions:
            raise ValueError("No legal actions provided")

        scored_actions = []
        for action in actions:
            # 1. Base Score (Immediate value: causing damage, status, etc.)
            base_score = self.evaluator.evaluate(state, action)

            # 2. Anticipated Outcome Score (Incoming damage in response)
            risk_penalty = self._anticipate_incoming_damage(state, action)
            
            # Final Score = Benefit - Risk
            final_score = base_score - (risk_penalty * self.risk_aversion)
            
            scored_actions.append((final_score, action, base_score, risk_penalty))

        # Sort by Final Score Descending
        scored_actions.sort(key=lambda x: (-x[0], x[1]))
        
        chosen = scored_actions[0][1]
        ordered = [act for _, act, _, _ in scored_actions]
        
        insights = []
        for score, action, base, risk in scored_actions[:top_k]:
            breakdown = self.evaluator.explain(state, action)
            breakdown["lookahead_risk"] = risk
            breakdown["final_score"] = score
            insights.append(ActionInsight(action=action, score=score, breakdown=breakdown))

        return chosen, ordered, insights

    def _anticipate_incoming_damage(self, state: BattleState, action: str) -> float:
        """
        Estimate the maximum damage the opponent can deal in response to 'action'.
        """
        # Determine who will be our active pokemon after our action
        if action.startswith("switch:"):
            # If we switch, the incoming pokemon takes the hit
            switch_name = action.split(":", 1)[1]
            # Find the pokemon in our team
            defender = next((p for p in state.player_self.team if p.species == switch_name), None)
            if not defender:
                 # Fallback to current if not found (shouldn't happen with valid actions)
                defender = state.player_self.active_pokemon()
        else:
            # If we move, the current pokemon stays (ignoring self-switch moves for simplicity 1-ply)
            defender = state.player_self.active_pokemon()

        attacker = state.player_opponent.active_pokemon()
        
        # Calculate max damage from known moves + heuristic STABs
        max_damage = 0.0
        
        # 1. Check Known Moves
        known_moves = attacker.moves_known
        for move_name in known_moves:
            dmg = self.evaluator.estimate_damage(attacker, defender, move_name)
            if dmg > max_damage:
                max_damage = dmg

        # 2. Heuristic: Assume STAB moves for opponent types if we haven't seen 4 moves
        # This is critical for Random Battles where moves are hidden.
        # If I am Fire vs Water, I assume Water has a Water move even if I haven't seen it.
        if len(known_moves) < 4:
            for opp_type in attacker.types:
                # Simulate a generic 80 BP move of this type
                # We construct a fake move name or query the type chart directly in evaluator?
                # Easier: we cheat and use estimate_damage logic directly here
                
                # Manual calculation of generic STAB hit
                # STAB (1.5) * Effectiveness * BasePower(80) / 100
                effectiveness = 1.0
                for def_type in defender.types:
                    effectiveness *= self.evaluator.knowledge.type_chart.get(opp_type, {}).get(def_type, 1.0)
                
                generic_damage = 80 * 1.5 * effectiveness / 100.0
                
                if generic_damage > max_damage:
                    max_damage = generic_damage

        return max_damage
