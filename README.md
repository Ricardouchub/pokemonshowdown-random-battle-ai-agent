# Pokémon Showdown Random Battle AI Agent

Estructura inicial del agente de Random Battle para Pokémon Showdown. Sigue las fases y entregables descritos en `AGENTS.md`.

## Requisitos
- Python 3.11+
- [uv](https://github.com/astral-sh/uv) para crear venv, instalar y ejecutar.

## Configuración rápida
```bash
uv venv
uv sync --all-extras
```

## Comandos útiles
- Formato y lint: `uv run ruff format` y `uv run ruff check`
- Tests: `uv run pytest`
- Ejecutar stub de partida: `uv run python -m ps_agent.runner.play_match`

## Estructura
- `src/ps_agent/state`: `BattleState`, `PokemonState`, extractor de features y encodings.
- `src/ps_agent/connector`: stubs del cliente Showdown y parser del protocolo.
- `src/ps_agent/policy`: baseline, evaluator y lookahead.
- `src/ps_agent/inference`: belief state e inferencia de sets.
- `src/ps_agent/knowledge`: type chart, moves/items/abilities y priors de randbats.
- `src/ps_agent/knowledge/online_agent.py`: agente online que consulta PokeAPI y cachea JSON de moves/items/abilities/type chart.
- `src/ps_agent/knowledge/deepseek_agent.py`: agente que llama a Deepseek para generar perfiles JSON de Pokémon/items/abilities (requiere `DEEPSEEK_API_KEY`).
- `src/ps_agent/knowledge/fetch_cache.py` y `runner/cache_agent.py`: rellenan el cache con PokeAPI de forma manual o automatizada.
- `src/ps_agent/runner/deepseek_cache_agent.py`: recorre nombres desde PokeAPI y genera perfiles con Deepseek automáticamente (requiere `DEEPSEEK_API_KEY`).
- `src/ps_agent/knowledge/loader.py`: carga todos los datos cached en memoria para el evaluador/policy.
- `src/ps_agent/runner`: ejecución de partidas/tournaments.
- `artifacts/feature_manifest.json`: lista de features generada automáticamente.
- `config/default.yaml`: pesos y parámetros por defecto.

## Alimentar cache con Deepseek
```bash
export DEEPSEEK_API_KEY=sk-...
uv run python -m ps_agent.knowledge.deepseek_agent --pokemon charizard pikachu --items life-orb --abilities levitate
```

## Alimentar cache automáticamente (Deepseek + PokeAPI)
```bash
export DEEPSEEK_API_KEY=sk-...
uv run python -m ps_agent.runner.deepseek_cache_agent --pokemon-limit 100 --item-limit 80 --ability-limit 80
```

## Refrescar knowledge online (PokeAPI)
```bash
uv run python -m ps_agent.knowledge.online_agent --move tackle --item leftovers --ability levitate --type-chart
```
