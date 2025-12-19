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
    position: float = 1.0
    field_control: float = 0.5
    risk: float = 0.5
    wincon_progress: float = 0.5


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
            return -0.05  # Slight penalty for losing a turn
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
