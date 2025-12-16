from ps_agent.connector.protocol_parser import ProtocolParser
from ps_agent.state.battle_state import PlayerState
from ps_agent.state.pokemon_state import PokemonState


def test_protocol_parser_applies_events():
    parser = ProtocolParser()
    player_self = PlayerState(name="p1", team=[PokemonState(species="unknown")] * 6, active_slot=0)
    player_opp = PlayerState(name="p2", team=[PokemonState(species="unknown")] * 6, active_slot=0)
    state = parser.bootstrap("battle-1", 9, "randombattle", player_self, player_opp)
    messages = [
        "|turn|3",
        "|weather|sun",
        "|switch|p1a: Charizard|Charizard, L80|100/100",
        "|switch|p2a: Swampert|Swampert, L80|100/100",
        "|move|p1a: Charizard|Flamethrower|p2a: Swampert",
        "|-damage|p2a: Swampert|50/100",
        "|-sidestart|p2: opp|move: Stealth Rock",
    ]
    events = parser.parse_events(messages)
    new_state = parser.apply(events, state)

    assert new_state.turn == 3
    assert new_state.field.weather == "sun"
    assert new_state.player_self.active_pokemon().species == "Charizard"
    assert new_state.player_opponent.active_pokemon().species == "Swampert"
    assert new_state.player_opponent.active_pokemon().hp_fraction == 0.5
    assert new_state.field.hazards_opp_side.stealth_rock is True
    assert new_state.field.last_actions["p1"] == "Flamethrower"
