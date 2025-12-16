from ps_agent.state.battle_state import BattleState, PlayerState
from ps_agent.state.field_state import FieldState
from ps_agent.state.pokemon_state import PokemonState


def test_battle_state_roundtrip():
    player = PlayerState(name="p1", team=[PokemonState(species="pikachu")] * 6, active_slot=0)
    opp = PlayerState(name="p2", team=[PokemonState(species="eevee")] * 6, active_slot=1)
    state = BattleState.new(
        battle_id="test",
        gen=9,
        format="randombattle",
        player_self=player,
        player_opponent=opp,
        turn=1,
        timestamp="now",
    )

    data = state.to_dict()
    restored = BattleState.from_dict(data)

    assert restored.battle_id == state.battle_id
    assert restored.player_self.name == "p1"
    assert restored.player_opponent.active_slot == 1
