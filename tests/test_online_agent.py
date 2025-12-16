import json
from pathlib import Path

from ps_agent.knowledge.online_agent import KnowledgeFetcher


class DummyResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


def test_fetcher_caches_resources(tmp_path: Path):
    calls = []

    def requester(url, timeout=10):
        calls.append(url)
        if url.endswith("/type"):
            return DummyResponse({"results": [{"name": "fire", "url": "type/fire"}]})
        if url.endswith("type/fire"):
            return DummyResponse(
                {
                    "damage_relations": {
                        "double_damage_from": [{"name": "water"}],
                        "double_damage_to": [{"name": "grass"}],
                        "half_damage_from": [],
                        "half_damage_to": [],
                        "no_damage_from": [],
                        "no_damage_to": [],
                    }
                }
            )
        return DummyResponse({"name": "dummy"})

    fetcher = KnowledgeFetcher(cache_dir=tmp_path, requester=requester, base_url="http://example")

    fetcher.fetch_move("Tackle")
    fetcher.fetch_item("Leftovers")
    fetcher.fetch_ability("Levitate")
    chart = fetcher.fetch_type_chart()

    assert (tmp_path / "move_tackle.json").exists()
    assert (tmp_path / "item_leftovers.json").exists()
    assert (tmp_path / "ability_levitate.json").exists()
    assert (tmp_path / "type_chart.json").exists()
    assert chart["fire"]["double_damage_to"] == ["grass"]
    assert any("type" in c for c in calls)
