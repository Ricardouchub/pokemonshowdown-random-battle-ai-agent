from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from ps_agent.knowledge.type_chart import TYPE_LIST, load_type_chart
from ps_agent.state.battle_state import BattleState
from ps_agent.state.pokemon_state import PokemonState


def _boost_norm(value: int) -> float:
    clamped = max(-6, min(6, value))
    return (clamped + 6) / 12


def _status_onehot(status: str | None) -> Dict[str, int]:
    statuses = ["none", "brn", "psn", "tox", "par", "slp", "frz"]
    return {f"status_onehot_{s}": int((status or "none") == s) for s in statuses}


def _weather_onehot(weather: str | None) -> Dict[str, int]:
    options = ["rain", "sun", "sand", "snow", "none"]
    current = weather or "none"
    return {f"weather_onehot_{w}": int(current == w) for w in options}


def _terrain_onehot(terrain: str | None) -> Dict[str, int]:
    options = ["electric", "grassy", "psychic", "misty", "none"]
    current = terrain or "none"
    return {f"terrain_onehot_{t}": int(current == t) for t in options}


def _type_onehot(types: tuple[str, ...]) -> Dict[str, int]:
    return {f"type_onehot_{t}": int(t in types) for t in TYPE_LIST}


def _active_block(prefix: str, pokemon: PokemonState) -> Dict[str, float]:
    features: Dict[str, float] = {}
    features.update({f"{prefix}_{k}": v for k, v in _type_onehot(pokemon.types).items()})
    features[f"{prefix}_dual_type"] = 1 if len(pokemon.types) == 2 else 0
    features[f"{prefix}_level_norm"] = pokemon.level / 100
    features[f"{prefix}_hp_frac"] = pokemon.hp_fraction
    features.update({f"{prefix}_{k}": v for k, v in _status_onehot(pokemon.status).items()})
    features[f"{prefix}_is_fainted"] = int(pokemon.is_fainted)
    features[f"{prefix}_boost_atk_norm"] = _boost_norm(pokemon.boosts.get("atk", 0))
    features[f"{prefix}_boost_def_norm"] = _boost_norm(pokemon.boosts.get("def", 0))
    features[f"{prefix}_boost_spa_norm"] = _boost_norm(pokemon.boosts.get("spa", 0))
    features[f"{prefix}_boost_spd_norm"] = _boost_norm(pokemon.boosts.get("spd", 0))
    features[f"{prefix}_boost_spe_norm"] = _boost_norm(pokemon.boosts.get("spe", 0))
    features[f"{prefix}_boost_acc_norm"] = _boost_norm(pokemon.boosts.get("acc", 0))
    features[f"{prefix}_boost_eva_norm"] = _boost_norm(pokemon.boosts.get("eva", 0))
    features[f"{prefix}_substitute"] = int(pokemon.volatiles.substitute)
    features[f"{prefix}_confusion"] = int(pokemon.volatiles.confusion)
    features[f"{prefix}_taunt"] = int(pokemon.volatiles.taunt)
    features[f"{prefix}_torment"] = int(pokemon.volatiles.torment)
    features[f"{prefix}_encore"] = int(pokemon.volatiles.encore)
    features[f"{prefix}_disable"] = int(pokemon.volatiles.disable)
    features[f"{prefix}_leech_seeded"] = int(pokemon.volatiles.leech_seeded)
    features[f"{prefix}_perish_song_active"] = int(pokemon.volatiles.perish_song_active)
    features[f"{prefix}_perish_song_count_norm"] = pokemon.volatiles.perish_song_count / 3
    features[f"{prefix}_item_known"] = int(pokemon.item is not None)
    features[f"{prefix}_ability_known"] = int(pokemon.ability is not None)
    features[f"{prefix}_moves_known_count"] = pokemon.moves_known_count()
    features[f"{prefix}_last_move_known"] = int(pokemon.last_move is not None)
    return features


@dataclass
class FeatureVector:
    features_dense: Dict[str, float]


def extract_features(state: BattleState) -> FeatureVector:
    features: Dict[str, float] = {}
    features["turn_norm"] = min(state.turn, 50) / 50
    features["num_pokemon_alive_self"] = sum(not p.is_fainted for p in state.player_self.team)
    features["num_pokemon_alive_opp"] = sum(not p.is_fainted for p in state.player_opponent.team)
    features["total_hp_fraction_self"] = sum(p.hp_fraction for p in state.player_self.team) / 6
    features["total_hp_fraction_opp"] = sum(p.hp_fraction for p in state.player_opponent.team) / 6

    features.update(_weather_onehot(state.field.weather))
    features.update(_terrain_onehot(state.field.terrain))
    features["trick_room_active"] = int(state.field.trick_room_turns_remaining > 0)
    features["trick_room_turns_norm"] = state.field.trick_room_turns_remaining / 5
    features["tailwind_active_self"] = int(state.field.tailwind_turns_remaining_self > 0)
    features["tailwind_turns_norm_self"] = state.field.tailwind_turns_remaining_self / 4
    features["tailwind_active_opp"] = int(state.field.tailwind_turns_remaining_opp > 0)
    features["tailwind_turns_norm_opp"] = state.field.tailwind_turns_remaining_opp / 4

    features["reflect_active_self"] = int(state.field.screens_self.reflect_turns > 0)
    features["reflect_turns_norm_self"] = state.field.screens_self.reflect_turns / 8
    features["lightscreen_active_self"] = int(state.field.screens_self.light_screen_turns > 0)
    features["lightscreen_turns_norm_self"] = state.field.screens_self.light_screen_turns / 8
    features["auroraveil_active_self"] = int(state.field.screens_self.aurora_veil_turns > 0)
    features["auroraveil_turns_norm_self"] = state.field.screens_self.aurora_veil_turns / 8
    features["reflect_active_opp"] = int(state.field.screens_opp.reflect_turns > 0)
    features["reflect_turns_norm_opp"] = state.field.screens_opp.reflect_turns / 8
    features["lightscreen_active_opp"] = int(state.field.screens_opp.light_screen_turns > 0)
    features["lightscreen_turns_norm_opp"] = state.field.screens_opp.light_screen_turns / 8
    features["auroraveil_active_opp"] = int(state.field.screens_opp.aurora_veil_turns > 0)
    features["auroraveil_turns_norm_opp"] = state.field.screens_opp.aurora_veil_turns / 8

    features["hazard_sr_self"] = int(state.field.hazards_self_side.stealth_rock)
    features["hazard_spikes_layers_self"] = state.field.hazards_self_side.spikes_layers
    features["hazard_tspikes_layers_self"] = state.field.hazards_self_side.toxic_spikes_layers
    features["hazard_web_self"] = int(state.field.hazards_self_side.sticky_web)
    features["hazard_sr_opp"] = int(state.field.hazards_opp_side.stealth_rock)
    features["hazard_spikes_layers_opp"] = state.field.hazards_opp_side.spikes_layers
    features["hazard_tspikes_layers_opp"] = state.field.hazards_opp_side.toxic_spikes_layers
    features["hazard_web_opp"] = int(state.field.hazards_opp_side.sticky_web)

    self_active = state.player_self.active_pokemon()
    opp_active = state.player_opponent.active_pokemon()
    features.update(_active_block("self_active", self_active))
    features.update(_active_block("opp_active", opp_active))

    # Matchup placeholders
    features["type_effectiveness_self_to_opp_best"] = 1.0
    features["type_effectiveness_opp_to_self_best"] = 1.0
    features["type_resistance_self_vs_opp_stab"] = 1.0
    features["speed_advantage_prob"] = 0.5
    features["ko_prob_self_to_opp"] = 0.0
    features["ko_prob_opp_to_self"] = 0.0
    features["twohko_prob_self_to_opp"] = 0.0
    features["twohko_prob_opp_to_self"] = 0.0
    features["switch_disadvantage_score"] = 0.0
    features["setup_risk_score"] = 0.0
    features["hazard_pressure_score"] = 0.0

    for side in ("self", "opp"):
        features[f"{side}_team_has_spinner"] = 0
        features[f"{side}_team_has_defogger"] = 0
        features[f"{side}_team_has_priority_user"] = 0
        features[f"{side}_team_has_scarfer_prob"] = 0.0
        team = state.player_self.team if side == "self" else state.player_opponent.team
        features[f"{side}_team_avg_hp_frac"] = sum(p.hp_fraction for p in team) / 6
        features[f"{side}_team_num_statused"] = sum(1 for p in team if p.status)
        features[f"{side}_team_num_boosted"] = sum(
            1 for p in team if any(v != 0 for v in p.boosts.values())
        )
        for t in TYPE_LIST:
            features[f"{side}_team_type_coverage_{t}"] = 0.0

    # Uncertainty features (opponent only)
    for name in [
        "opp_active_set_entropy_norm",
        "opp_team_total_entropy_norm",
        "opp_active_item_choice_prob",
        "opp_active_item_boots_prob",
        "opp_active_item_sash_prob",
        "opp_active_ability_key_prob",
        "opp_active_has_recovery_prob",
        "opp_active_has_setup_prob",
        "opp_active_has_status_move_prob",
        "opp_active_has_hazard_move_prob",
        "opp_active_has_removal_prob",
    ]:
        features[name] = 0.0

    return FeatureVector(features_dense=features)


def feature_manifest() -> List[str]:
    # Sorted for stability
    return sorted(extract_features(_empty_state()).features_dense.keys())


def _empty_state() -> BattleState:
    dummy = PokemonState(species="dummy")
    from ps_agent.state.battle_state import PlayerState
    from ps_agent.state.field_state import FieldState

    return BattleState.new(
        battle_id="manifest",
        gen=9,
        format="randombattle",
        player_self=PlayerState(name="self", team=[dummy] * 6, active_slot=0),
        player_opponent=PlayerState(name="opp", team=[dummy] * 6, active_slot=0),
        turn=0,
        timestamp="",
    )
