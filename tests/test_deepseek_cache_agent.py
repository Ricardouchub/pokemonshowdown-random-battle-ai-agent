from pathlib import Path

from ps_agent.runner.deepseek_cache_agent import auto_deepseek_cache
from ps_agent.knowledge.deepseek_agent import DeepseekConfig, DeepseekKnowledgeAgent


class DummyAgent(DeepseekKnowledgeAgent):
    def __init__(self):
        self.calls = []

    def fetch_pokemon(self, name: str):
        self.calls.append(("pokemon", name))

    def fetch_item(self, name: str):
        self.calls.append(("item", name))

    def fetch_ability(self, name: str):
        self.calls.append(("ability", name))


def test_auto_deepseek_cache_enumerates(monkeypatch, tmp_path: Path):
    def fake_fetch_all_names(base_url, resource, limit):
        return [f"{resource}1", f"{resource}2"]

    monkeypatch.setattr(
        "ps_agent.runner.deepseek_cache_agent._fetch_all_names", fake_fetch_all_names
    )

    dummy = DummyAgent()

    def fake_agent_factory(config):
        return dummy

    monkeypatch.setattr(
        "ps_agent.runner.deepseek_cache_agent.DeepseekKnowledgeAgent", lambda config: dummy
    )

    auto_deepseek_cache(
        api_key="dummy",
        cache_dir=tmp_path,
        pokemon_limit=2,
        item_limit=2,
        ability_limit=2,
        batch_size=1,
    )

    assert ("pokemon", "pokemon1") in dummy.calls
    assert ("item", "item1") in dummy.calls
    assert ("ability", "ability1") in dummy.calls
