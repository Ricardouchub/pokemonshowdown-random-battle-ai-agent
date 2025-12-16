import math

from ps_agent.state.battle_state import BattleState, PlayerState
from ps_agent.state.feature_extractor import extract_features, feature_manifest
from ps_agent.state.pokemon_state import PokemonState


def test_feature_extractor_outputs_all_features():
    player = PlayerState(name="self", team=[PokemonState(species="pikachu")] * 6, active_slot=0)
    opp = PlayerState(name="opp", team=[PokemonState(species="eevee")] * 6, active_slot=0)
    state = BattleState.new(
        battle_id="test",
        gen=9,
        format="randombattle",
        player_self=player,
        player_opponent=opp,
        turn=5,
        timestamp="t",
    )
    fv = extract_features(state)
    manifest = feature_manifest()
    assert set(manifest).issuperset(fv.features_dense.keys())
    assert all(not math.isnan(v) for v in fv.features_dense.values())
