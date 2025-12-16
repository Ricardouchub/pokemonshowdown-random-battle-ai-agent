import json
from pathlib import Path

from ps_agent.knowledge.deepseek_agent import DeepseekConfig, DeepseekKnowledgeAgent


class DummyRequester:
    def __init__(self, payload: str):
        self.payload = payload
        self.requests = []

    def post(self, url, headers=None, json=None, timeout=30):
        self.requests.append({"url": url, "headers": headers, "json": json, "timeout": timeout})

        class _Resp:
            def __init__(self, payload):
                self._payload = payload

            def raise_for_status(self):
                return None

            def json(self):
                return {"choices": [{"message": {"content": self._payload}}]}

        return _Resp(self.payload)


def test_deepseek_agent_caches_json(tmp_path: Path):
    requester = DummyRequester(payload='{"species":"charizard","types":["fire","flying"]}')
    cfg = DeepseekConfig(api_key="test", cache_dir=tmp_path)
    agent = DeepseekKnowledgeAgent(cfg, requester=requester)
    data = agent.fetch_pokemon("Charizard")
    assert data["species"] == "charizard"
    cached = json.loads((tmp_path / "llm_pokemon_charizard.json").read_text())
    assert cached["species"] == "charizard"
