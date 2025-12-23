from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

from ps_agent.knowledge.loader import KnowledgeBase, load_all_knowledge
from ps_agent.state.battle_state import BattleState
from ps_agent.state.pokemon_state import PokemonState
from ps_agent.utils.format import to_id


@dataclass
class EvalWeights:
    material: float = 1.0
    position: float = 1.2  # Increased to prioritize damage/advantage
    field_control: float = 0.5
    risk: float = 0.3      # Reduced to encourage trading damage over fleeing
    wincon_progress: float = 0.8 # Increased to favor progress


class Evaluator:
    """Lightweight evaluator using knowledge for matchup and damage proxy."""

    def __init__(
        self, weights: EvalWeights | None = None, knowledge: KnowledgeBase | None = None
    ) -> None:
        self.weights = weights or EvalWeights()
        self.knowledge = knowledge or load_all_knowledge()

    def evaluate(self, state: BattleState, action: str) -> float:
        material = self._material_score(state)
        position = self._position_score(state, action)
        field = self._field_control_score(state)
        risk = self._risk_penalty(state, action)
        wincon = self._wincon_progress_score(state, action)
        return (
            self.weights.material * material
            + self.weights.position * position
            + self.weights.field_control * field
            - self.weights.risk * risk
            + self.weights.wincon_progress * wincon
        )

    def explain(self, state: BattleState, action: str) -> Dict[str, float]:
        material = self._material_score(state)
        position = self._position_score(state, action)
        field = self._field_control_score(state)
        risk = self._risk_penalty(state, action)
        wincon = self._wincon_progress_score(state, action)
        score = (
            self.weights.material * material
            + self.weights.position * position
            + self.weights.field_control * field
            - self.weights.risk * risk
            + self.weights.wincon_progress * wincon
        )
        return {
            "score": score,
            "material": material,
            "position": position,
            "field_control": field,
            "risk": risk,
            "wincon_progress": wincon,
        }

    @staticmethod
    def _material_score(state: BattleState) -> float:
        return sum(not p.is_fainted for p in state.player_self.team) - sum(
            not p.is_fainted for p in state.player_opponent.team
        )

    def _position_score(self, state: BattleState, action: str) -> float:
        self_poke = state.player_self.active_pokemon()
        opp_poke = state.player_opponent.active_pokemon()
        if action.startswith("switch:"):
            # Anti-Switch-Loop Logic
            switch_depth = self._detect_consecutive_switches(state)
            opp_switched = self._opp_switched_last_turn(state)
            
            # Base penalty for switching (loss of tempo is always a cost)
            penalty = 0.3
            
            if opp_switched:
                # If opponent switched, we are reacting to a new threat.
                # Reset penalties. We allow multiple switches if they are reaction chains.
                pass
            else:
                # Opponent stayed. We must justify switching.
                # Progressive penalty for switching repeatedly against a static opponent.
                penalty += switch_depth * 2.0
                
                # CRITICAL: If we switched and opponent stayed, FORBID switching again.
                # This breaks the "I switch, you stay, I switch back" infinite loop.
                if switch_depth >= 1:
                    penalty += 5.0
                
            return -penalty
        if action.startswith("move:"):
            move_name = action.split(":", 1)[1]
            # Heuristic: Penalize status moves if opponent already has a status
            move = self.knowledge.moves.get(move_name.lower()) or self.knowledge.moves.get(move_name)
            if move and move.is_status and opp_poke.status:
                return -0.5  # Strong penalty for redundant status
            
            damage = self.estimate_damage(state, self_poke, opp_poke, move_name)
            return damage
        return 0.0

    def _field_control_score(self, state: BattleState) -> float:
        score = 0.0
        score += 0.2 * state.field.hazards_opp_side.spikes_layers
        score += 0.5 if state.field.hazards_opp_side.stealth_rock else 0.0
        score -= 0.2 * state.field.hazards_self_side.spikes_layers
        score -= 0.5 if state.field.hazards_self_side.stealth_rock else 0.0
        return score

    def _risk_penalty(self, state: BattleState, action: str) -> float:
        # Simple proxy: avoid staying in low HP
        self_poke = state.player_self.active_pokemon()
        risk = 1.0 - self_poke.hp_fraction
        # Removed the half-risk bonus for switching to avoid panic swapping
        return risk

    def _wincon_progress_score(self, state: BattleState, action: str) -> float:
        if action.startswith("move:"):
            return 0.1
        return 0.0

    def estimate_damage(self, state: BattleState, attacker: PokemonState, defender: PokemonState, move_name: str) -> float:
        """Estimate damage percentage (0.0 to 1.0+) of a move against a defender."""
        move_id = to_id(move_name)
        move = self.knowledge.moves.get(move_id) or self.knowledge.moves.get(move_name)
        if move is None:
            return 0.0
        
        # Check observed effectiveness overrides
        obs = state.observed_effectiveness.get(defender.species, {})
        observed_mult = obs.get(move_id)
        if observed_mult is not None:
            # Override effectiveness calculation, but keep STAB/Power logic?
            # Usually users just want "don't use if ineffective".
            # If observed is 0.5 or 0.0, we just use that multiplier.
            # But we must apply it to Base Power.
            base_msg = " [OBSERVED]"
            effectiveness = observed_mult
        else:
            base_msg = ""
            effectiveness = 1.0
            for def_type in defender.types:
                effectiveness *= self.knowledge.type_chart.get(move.move_type, {}).get(def_type, 1.0)

        base_power = move.power or 0
        stab = 1.5 if move.move_type in attacker.types else 1.0
        damage = base_power * stab * effectiveness / 100.0
        return damage

    def _detect_consecutive_switches(self, state: BattleState) -> int:
        """
        Count how many times we have switched consecutively without using a move.
        Returns the count (0, 1, 2...).
        Also checks if opponent switched in the MOST RECENT turn (to allow matching switches).
        """
        if not state.history:
            return 0
            
        my_side = state.my_side or "p1"
        opp_side = "p2" if my_side == "p1" else "p1"
        
        consecutive_switches = 0
        
        # Iterate backwards through history events
        # We need to disregard the *current* turn-start events and look at completed actions
        # Protocol lines: |switch|p1a: Name|..., |move|p1a: Name|...
        
        for evt in reversed(state.history):
            parts = evt.split("|")
            if len(parts) < 3:
                continue
                
            cmd = parts[1]
            if cmd not in ("switch", "move"):
                continue
                
            # Who did it?
            actor_id = parts[2].split(":")[0].strip()
            is_me = actor_id.startswith(my_side)
            
            if is_me:
                if cmd == "switch":
                    consecutive_switches += 1
                elif cmd == "move":
                    # I attacked, so the chain is broken
                    break
        
        return consecutive_switches

    def _opp_switched_last_turn(self, state: BattleState) -> bool:
        """Check if opponent switched in the very last turn."""
        if not state.history:
            return False
            
        my_side = state.my_side or "p1"
        opp_side = "p2" if my_side == "p1" else "p1"
        
        # Scan only the last ~20 lines to cover the previous turn
        # We look for |switch|p2a...
        # But we must stop if we see |turn|N-1? history is linear log.
        
        # Simplified: Check last 15 events for an opponent switch
        for evt in reversed(state.history[-15:]):
            if "|switch|" in evt:
                parts = evt.split("|")
                if len(parts) > 2 and parts[2].startswith(opp_side):
                    return True
            if "|move|" in evt:
                parts = evt.split("|")
                if len(parts) > 2 and parts[2].startswith(opp_side):
                    # Opponent moved, so they didn't switch (last action was move)
                    return False
        return False
