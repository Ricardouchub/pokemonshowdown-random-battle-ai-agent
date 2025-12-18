import json

from ps_agent.policy.llm_policy import LLMPolicy
from ps_agent.policy.baseline_rules import BaselinePolicy
from ps_agent.state.battle_state import BattleState, PlayerState
from ps_agent.state.pokemon_state import PokemonState


class DummyLLM:
    def __init__(self, response: dict):
        self.response = response

    def chat(self, messages):
        return json.dumps(self.response)


def build_state():
    team_self = [PokemonState(species="charizard", moves_known=("flamethrower",))] + [
        PokemonState(species=f"s-{i}") for i in range(5)
    ]
    team_opp = [PokemonState(species="venusaur")] + [PokemonState(species=f"o-{i}") for i in range(5)]
    return BattleState.new(
        battle_id="battle-llm",
        gen=9,
        format="randombattle",
        player_self=PlayerState(name="self", team=team_self, active_slot=0),
        player_opponent=PlayerState(name="opp", team=team_opp, active_slot=0),
        turn=1,
        timestamp="",
    )


def test_llm_policy_uses_llm_action(tmp_path):
    llm = DummyLLM({"action": "move:flamethrower", "reason": "Fire beats grass", "confidence": 0.9})
    policy = LLMPolicy(llm=llm, baseline=BaselinePolicy())
    state = build_state()
    action, ordered, insights = policy.choose_action(state, ["move:flamethrower", "switch:bench"])
    assert action == "move:flamethrower"
    assert ordered[0] == "move:flamethrower"
    assert insights[0].action == "move:flamethrower"
