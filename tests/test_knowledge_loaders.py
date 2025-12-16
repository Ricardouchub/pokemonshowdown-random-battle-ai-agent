import json
from pathlib import Path

from ps_agent.knowledge.loader import load_all_knowledge
from ps_agent.knowledge.type_chart import load_type_chart


def test_loaders_use_cache(tmp_path: Path):
    cache = tmp_path
    # type chart cache
    chart_data = {
        "fire": {
            "double_damage_to": ["grass"],
            "half_damage_to": ["water"],
            "no_damage_to": [],
            "double_damage_from": [],
            "half_damage_from": [],
            "no_damage_from": [],
        }
    }
    (cache / "type_chart.json").write_text(json.dumps(chart_data))
    (cache / "move_ember.json").write_text(json.dumps({"name": "ember", "type": "fire", "power": 40, "accuracy": 100, "damage_class": {"name": "special"}, "priority": 0}))
    (cache / "item_leftovers.json").write_text(json.dumps({"name": "leftovers", "effect_entries": [{"short_effect": "Heal"}]}))
    (cache / "ability_levitate.json").write_text(json.dumps({"name": "levitate", "effect_entries": [{"short_effect": "Immune to ground"}]}))

    knowledge = load_all_knowledge(cache)
    assert knowledge.type_chart["fire"]["grass"] == 2.0
    assert knowledge.moves["ember"].power == 40
    assert knowledge.items["leftovers"].category == "recovery"
    assert knowledge.abilities["levitate"].name == "levitate"


def test_type_chart_fallback():
    chart = load_type_chart(cache_dir="nonexistent")
    assert chart["fire"]["grass"] > 1.0
