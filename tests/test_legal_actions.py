from ps_agent.policy.legal_actions import enumerate_legal_actions
from ps_agent.state.battle_state import BattleState, PlayerState
from ps_agent.state.pokemon_state import PokemonState


def test_enumerate_legal_actions_includes_moves_and_switches():
    team = [
        PokemonState(species="lead", moves_known=("move-a", "move-b")),
        PokemonState(species="bench1"),
        PokemonState(species="bench2", is_fainted=True),
    ] + [PokemonState(species=f"extra{i}") for i in range(3)]
    player = PlayerState(name="self", team=team, active_slot=0)
    opp = PlayerState(name="opp", team=[PokemonState(species="opp")] * 6, active_slot=0)
    state = BattleState.new(
        battle_id="x",
        gen=9,
        format="randombattle",
        player_self=player,
        player_opponent=opp,
        turn=1,
        timestamp="",
    )

    actions = enumerate_legal_actions(state)
    assert "move:move-a" in actions
    assert "move:move-b" in actions
    assert "switch:bench1" in actions
    assert all("bench2" not in act for act in actions)
