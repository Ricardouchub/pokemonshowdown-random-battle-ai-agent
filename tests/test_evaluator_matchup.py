from ps_agent.policy.baseline_rules import BaselinePolicy
from ps_agent.policy.evaluator import Evaluator
from ps_agent.knowledge.loader import load_all_knowledge
from ps_agent.state.battle_state import BattleState, PlayerState
from ps_agent.state.pokemon_state import PokemonState


def test_evaluator_prefers_supereffective_move(tmp_path):
    # Prepare cache with ember as fire move and type chart fire>grass
    cache = tmp_path
    (cache / "type_chart.json").write_text(
        '{"fire":{"double_damage_to":["grass"],"half_damage_to":[],"no_damage_to":[]}}'
    )
    (cache / "move_ember.json").write_text(
        '{"name":"ember","type":"fire","power":40,"accuracy":100,"damage_class":{"name":"special"},"priority":0}'
    )
    knowledge = load_all_knowledge(cache)
    evaluator = Evaluator(knowledge=knowledge)
    policy = BaselinePolicy(evaluator=evaluator)
    self_team = [PokemonState(species="charizard", types=("fire",), moves_known=("ember",))]
    self_team.extend([PokemonState(species=f"bench{i}") for i in range(5)])
    opp_team = [PokemonState(species="venusaur", types=("grass",))]
    opp_team.extend([PokemonState(species=f"opp{i}") for i in range(5)])
    state = BattleState.new(
        battle_id="b",
        gen=9,
        format="randombattle",
        player_self=PlayerState(name="p1", team=self_team, active_slot=0),
        player_opponent=PlayerState(name="p2", team=opp_team, active_slot=0),
        turn=1,
        timestamp="",
    )
    chosen, ordered = policy.choose_action(state)
    assert chosen.startswith("move:ember")
    assert ordered[0].startswith("move:ember")
