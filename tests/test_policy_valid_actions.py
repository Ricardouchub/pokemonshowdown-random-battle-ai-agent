from ps_agent.policy.baseline_rules import BaselinePolicy
from ps_agent.state.battle_state import BattleState, PlayerState
from ps_agent.state.pokemon_state import PokemonState


def test_baseline_policy_returns_legal_action():
    player = PlayerState(name="self", team=[PokemonState(species="pikachu")] * 6, active_slot=0)
    opp = PlayerState(name="opp", team=[PokemonState(species="eevee")] * 6, active_slot=0)
    state = BattleState.new(
        battle_id="test",
        gen=9,
        format="randombattle",
        player_self=player,
        player_opponent=opp,
        turn=1,
        timestamp="",
    )
    legal = ["move1", "switch1"]
    policy = BaselinePolicy()
    action, candidates = policy.choose_action(state, legal)
    assert action in legal
    assert set(candidates) == set(legal)
