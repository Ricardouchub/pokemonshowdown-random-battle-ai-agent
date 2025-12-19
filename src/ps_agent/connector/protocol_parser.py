from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Dict, Iterable, List, Tuple

from ps_agent.state.battle_state import BattleState, PlayerState
from ps_agent.state.field_state import FieldState, ScreensState, SideHazards
from ps_agent.state.pokemon_state import PokemonState, PokemonVolatile
from ps_agent.utils.format import to_id

Slot = Tuple[str, int]  # (side_id, slot_index)


@dataclass
class ProtocolEvent:
    raw: str
    kind: str
    args: List[str]


class ProtocolParser:
    """Parser for the Showdown battle protocol with minimal updates to BattleState."""

    def parse_events(self, messages: Iterable[str]) -> List[ProtocolEvent]:
        events: List[ProtocolEvent] = []
        for msg in messages:
            parts = msg.strip().split("|")
            if parts and parts[0] == "":
                parts = parts[1:]
            if not parts or parts[0] == "":
                continue
            kind, args = parts[0], parts[1:]
            events.append(ProtocolEvent(raw=msg, kind=kind, args=args))
        return events

    def apply(self, events: Iterable[ProtocolEvent], initial_state: BattleState) -> BattleState:
        state = initial_state
        for ev in events:
            state = self._apply_event(ev, state)
        return state

    def _apply_event(self, event: ProtocolEvent, state: BattleState) -> BattleState:
        kind = event.kind
        args = event.args
        if kind == "turn" and args:
            return state.with_turn(int(args[0]))
        if kind == "weather" and args:
            return replace(state, field=replace(state.field, weather=args[0]))
        if kind == "terrain" and args:
            return replace(state, field=replace(state.field, terrain=args[0]))
        if kind == "switch" and len(args) >= 3:
            return self._apply_switch(args, state)
        if kind in {"move", "-activate"} and len(args) >= 2:
            return self._apply_move(args, state)
        if kind in {"-damage", "-heal"} and args:
            return self._apply_hp(args, state)
        if kind == "-status" and len(args) >= 2:
            return self._apply_status(args, state)
        if kind == "-curestatus" and len(args) >= 2:
            return self._apply_status(args, state, cure=True)
        if kind == "-faint" and args:
            return self._apply_faint(args, state)
        if kind in {"-supereffective", "-resisted", "-immune"}:
            return self._apply_effectiveness_log(kind, args, state)

        if kind == "-sidestart" and len(args) >= 2:
            return self._apply_side_condition(args, state, add=True)
        if kind == "-sideend" and len(args) >= 2:
            return self._apply_side_condition(args, state, add=False)
        if kind == "player" and len(args) >= 2:
            return self._apply_player(args, state)
        return state

    def _apply_player(self, args: List[str], state: BattleState) -> BattleState:
        # args: [side_id, name, avatar, rating]
        side_id = args[0]
        name = args[1]
        
        # If this checks out as our name, mark our side
        # Note: names might be sanitized differently, simple check for now
        if name.lower() == state.player_self.name.lower():
            return replace(state, my_side=side_id)
        return state

    def _apply_switch(self, args: List[str], state: BattleState) -> BattleState:
        slot_id_raw, species_raw, hp_raw = args[0], args[1], args[2]
        side_id, slot_idx = self._parse_slot(slot_id_raw)
        species = species_raw.split(",")[0].strip()
        hp_fraction = self._parse_hp_fraction(hp_raw)
        player = self._get_player(state, side_id)
        team = list(player.team)
        base_mon = player.team[slot_idx] if slot_idx < len(player.team) else PokemonState(species=species)
        pokemon = PokemonState(
            species=species,
            level=base_mon.level,
            types=base_mon.types,
            hp_fraction=hp_fraction,
            status=None,
            is_fainted=False,
            boosts=base_mon.boosts,
            volatiles=base_mon.volatiles if base_mon.volatiles else PokemonVolatile(),
            item=base_mon.item,
            ability=base_mon.ability,
            moves_known=base_mon.moves_known,
            last_move=None,
            active=True,
        )
        if slot_idx >= len(team):
            team.extend(PokemonState.empty_team()[len(team) : slot_idx + 1])
        team[slot_idx] = pokemon
        team = self._mark_active(team, slot_idx)
        player_updated = replace(player, active_slot=slot_idx, team=team)
        state = self._replace_player(state, side_id, player_updated)
        return self._append_history(state, f"Switch: {side_id} sent out {species}")

    def _apply_move(self, args: List[str], state: BattleState) -> BattleState:
        slot_id_raw, move_name = args[0], args[1]
        side_id, slot_idx = self._parse_slot(slot_id_raw)
        
        # Track for effectiveness logic (normalized to ID)
        self._last_move = (side_id, to_id(move_name))
        
        player = self._get_player(state, side_id)
        team = list(player.team)
        mon = team[slot_idx]
        moves_known = list(mon.moves_known)
        if move_name not in moves_known:
            moves_known.append(move_name)
        mon = replace(mon, moves_known=tuple(moves_known), last_move=move_name)
        team[slot_idx] = mon
        player_updated = replace(player, team=team)
        field = replace(state.field, last_actions={**state.field.last_actions, side_id: move_name})
        state = self._replace_player(state, side_id, player_updated, field=field)
        return self._append_history(state, f"Move: {side_id} used {move_name}")

    def _apply_effectiveness_log(self, kind: str, args: List[str], state: BattleState) -> BattleState:
        # kind: -supereffective, -resisted, -immune
        # args: [slot_id] (for immune: [slot_id])
        if not hasattr(self, "_last_move") or not self._last_move:
            return state
        
        attacker_side, move_name = self._last_move
        defender_slot = args[0]
        defender_side, defender_idx = self._parse_slot(defender_slot)
        
        # Ensure it's the target of the last move (approximate check: different sides)
        if attacker_side == defender_side:
            # Self-hit or confusion? Ignore for now to be safe
            return state
            
        multiplier = 1.0
        if kind == "-supereffective":
            multiplier = 2.0
        elif kind == "-resisted":
            multiplier = 0.5
        elif kind == "-immune":
            multiplier = 0.0
            
        # Identify defender species
        defender_player = self._get_player(state, defender_side)
        if defender_idx < len(defender_player.team):
            species = defender_player.team[defender_idx].species
            
            # Update observation
            obs = dict(state.observed_effectiveness)
            if species not in obs:
                obs[species] = {}
            
            # We clone the inner dict to keep it immutable-ish
            species_obs = dict(obs[species])
            species_obs[move_name] = multiplier
            obs[species] = species_obs
            
            return replace(state, observed_effectiveness=obs)
            
        return state

    def _apply_hp(self, args: List[str], state: BattleState) -> BattleState:
        slot_id_raw = args[0]
        hp_raw = args[1] if len(args) >= 2 else ""
        side_id, slot_idx = self._parse_slot(slot_id_raw)
        player = self._get_player(state, side_id)
        team = list(player.team)
        mon = team[slot_idx]
        hp_fraction = self._parse_hp_fraction(hp_raw)
        mon = replace(mon, hp_fraction=hp_fraction, is_fainted=hp_fraction <= 0.0)
        team[slot_idx] = mon
        player_updated = replace(player, team=team)
        return self._replace_player(state, side_id, player_updated)

    def _apply_status(
        self, args: List[str], state: BattleState, cure: bool = False
    ) -> BattleState:
        slot_id_raw = args[0]
        status_val = None if cure else args[1]
        side_id, slot_idx = self._parse_slot(slot_id_raw)
        player = self._get_player(state, side_id)
        team = list(player.team)
        mon = team[slot_idx]
        mon = replace(mon, status=status_val)
        team[slot_idx] = mon
        player_updated = replace(player, team=team)
        return self._replace_player(state, side_id, player_updated)

    def _apply_faint(self, args: List[str], state: BattleState) -> BattleState:
        slot_id_raw = args[0]
        side_id, slot_idx = self._parse_slot(slot_id_raw)
        player = self._get_player(state, side_id)
        team = list(player.team)
        mon = replace(team[slot_idx], is_fainted=True, hp_fraction=0.0)
        team[slot_idx] = mon
        player_updated = replace(player, team=team)
        return self._replace_player(state, side_id, player_updated)

    def _apply_side_condition(self, args: List[str], state: BattleState, add: bool) -> BattleState:
        side_str = args[0]
        condition = args[1]
        side_id = self._parse_side_id(side_str)
        hazards_self = state.field.hazards_self_side
        hazards_opp = state.field.hazards_opp_side
        screens_self = state.field.screens_self
        screens_opp = state.field.screens_opp
        tailwind_self = state.field.tailwind_turns_remaining_self
        tailwind_opp = state.field.tailwind_turns_remaining_opp
        trick_room = state.field.trick_room_turns_remaining

        def toggle_hazard(hazards: SideHazards) -> SideHazards:
            if "Stealth Rock" in condition:
                return replace(hazards, stealth_rock=add)
            if "Spikes" in condition and "Toxic" not in condition:
                layers = hazards.spikes_layers + (1 if add else -hazards.spikes_layers)
                return replace(hazards, spikes_layers=max(0, min(3, layers)))
            if "Toxic Spikes" in condition:
                layers = hazards.toxic_spikes_layers + (1 if add else -hazards.toxic_spikes_layers)
                return replace(hazards, toxic_spikes_layers=max(0, min(2, layers)))
            if "Sticky Web" in condition:
                return replace(hazards, sticky_web=add)
            return hazards

        def toggle_screens(screens: ScreensState) -> ScreensState:
            if "Reflect" in condition:
                return replace(screens, reflect_turns=8 if add else 0)
            if "Light Screen" in condition:
                return replace(screens, light_screen_turns=8 if add else 0)
            if "Aurora Veil" in condition:
                return replace(screens, aurora_veil_turns=5 if add else 0)
            return screens

        if side_id == "p1":
            hazards_self = toggle_hazard(hazards_self)
            screens_self = toggle_screens(screens_self)
            if "Tailwind" in condition:
                tailwind_self = 4 if add else 0
            if "Trick Room" in condition:
                trick_room = 5 if add else 0
        else:
            hazards_opp = toggle_hazard(hazards_opp)
            screens_opp = toggle_screens(screens_opp)
            if "Tailwind" in condition:
                tailwind_opp = 4 if add else 0
            if "Trick Room" in condition:
                trick_room = 5 if add else 0

        new_field = replace(
            state.field,
            hazards_self_side=hazards_self,
            hazards_opp_side=hazards_opp,
            screens_self=screens_self,
            screens_opp=screens_opp,
            tailwind_turns_remaining_self=tailwind_self,
            tailwind_turns_remaining_opp=tailwind_opp,
            trick_room_turns_remaining=trick_room,
        )
        return replace(state, field=new_field)

    @staticmethod
    def _parse_slot(raw: str) -> Slot:
        # raw like "p1a: Charizard"
        side_part = raw.split(":")[0].strip()
        side_id = side_part[:2]
        slot_letter = side_part[2] if len(side_part) > 2 else "a"
        slot_idx = ord(slot_letter) - ord("a")
        return side_id, slot_idx

    @staticmethod
    def _parse_hp_fraction(hp_raw: str) -> float:
        if "fnt" in hp_raw:
            return 0.0
        if "/" in hp_raw:
            current, total = hp_raw.split("/")[0:2]
            try:
                return max(0.0, min(1.0, float(current) / float(total)))
            except ValueError:
                return 1.0
        try:
            return float(hp_raw)
        except ValueError:
            return 1.0

    @staticmethod
    def _parse_side_id(raw: str) -> str:
        if raw.startswith("p1"):
            return "p1"
        if raw.startswith("p2"):
            return "p2"
        return "p1"

    @staticmethod
    def _mark_active(team: List[PokemonState], active_idx: int) -> List[PokemonState]:
        updated: List[PokemonState] = []
        for idx, mon in enumerate(team):
            updated.append(replace(mon, active=idx == active_idx))
        return updated

    def _get_player(self, state: BattleState, side_id: str) -> PlayerState:
        # If my_side is known, use it. Else fall back to assuming p1 is self (legacy behavior)
        if state.my_side:
            is_self = (side_id == state.my_side)
            return state.player_self if is_self else state.player_opponent
        return state.player_self if side_id == "p1" else state.player_opponent

    def _replace_player(
        self, state: BattleState, side_id: str, player: PlayerState, field: FieldState | None = None
    ) -> BattleState:
        if state.my_side:
            is_self = (side_id == state.my_side)
            if is_self:
                return replace(state, player_self=player, field=field or state.field)
            else:
                return replace(state, player_opponent=player, field=field or state.field)
        
        # Legacy fallback
        if side_id == "p1":
            return replace(state, player_self=player, field=field or state.field)
        return replace(state, player_opponent=player, field=field or state.field)

    def _append_history(self, state: BattleState, event_str: str) -> BattleState:
        new_history = list(state.history) + [event_str]
        # Keep only last 20 events to avoid unlimited growth
        if len(new_history) > 20:
            new_history = new_history[-20:]
        return replace(state, history=new_history)

    @staticmethod
    def bootstrap(
        battle_id: str,
        gen: int,
        format: str,
        player_self: PlayerState,
        player_opp: PlayerState,
    ) -> BattleState:
        return BattleState.new(
            battle_id=battle_id,
            gen=gen,
            format=format,
            player_self=player_self,
            player_opponent=player_opp,
            turn=0,
        )
