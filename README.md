# Pokemon Showdown Random Battle AI Agent

Agente modular para Pokémon Showdown (Random Battle) siguiendo las fases y entregables definidos en `AGENTS.md`. Incluye conectores, estado centralizado, políticas deterministas y herramientas de conocimiento alimentadas por PokeAPI y Deepseek.

## Requisitos
- Python 3.11+
- [uv](https://github.com/astral-sh/uv)
- (Opcional) `DEEPSEEK_API_KEY` configurado en `.env` o como variable de entorno para el agente LLM

## Setup rápido
```bash
uv venv
uv sync --all-extras
```

## Comandos útiles
- Lint/format: `uv run ruff check` y `uv run ruff format`
- Tests: `uv run pytest`
- Partida simulada stub: `uv run python -m ps_agent.runner.play_match`
- Feature manifest (se genera automáticamente en `artifacts/feature_manifest.json`)

## Knowledge y cache
- `src/ps_agent/knowledge/online_agent.py`: usa PokeAPI (moves/items/abilities/type chart).
  ```bash
  uv run python -m ps_agent.knowledge.online_agent --move ember --item leftovers --ability levitate --type-chart
  ```
- `src/ps_agent/knowledge/fetch_cache.py`: CLI para cargar múltiples recursos desde archivos/listas.
- `src/ps_agent/runner/cache_agent.py`: seed automatizado con conjuntos curados para PokeAPI.
- `src/ps_agent/knowledge/deepseek_agent.py`: genera perfiles JSON (pokémon/items/abilities) con Deepseek (`DEEPSEEK_API_KEY` en `.env`).
  ```bash
  uv run python -m ps_agent.knowledge.deepseek_agent --pokemon charizard --items life-orb --abilities levitate
  ```
- `src/ps_agent/runner/deepseek_cache_agent.py`: recorre nombres desde PokeAPI y genera perfiles con Deepseek de forma automática.
  ```bash
  uv run python -m ps_agent.runner.deepseek_cache_agent --pokemon-limit 100 --item-limit 80 --ability-limit 80
  ```
- `src/ps_agent/knowledge/loader.py`: carga todo el cache (`data/knowledge_cache/`) como `KnowledgeBase` para el evaluador/policy.

## Componentes principales
- `src/ps_agent/state`: `BattleState`, `PokemonState`, `FieldState`, feature extractor y encoding.
- `src/ps_agent/connector`: `ShowdownClient` (websocket) y `ProtocolParser` (convierte mensajes a `BattleState`).
- `src/ps_agent/policy`: `BaselinePolicy`, `Evaluator`, `Lookahead` y enumeración de acciones legales.
  - La política usa el knowledge cache para estimar daño/efectividad y devuelve top‑K acciones con su desglose (`material`, `position`, `field_control`, `risk`, `wincon_progress`).
- `src/ps_agent/runner`: `play_match`, `tournament`, agentes de cache (PokeAPI/Deepseek) y logging de eventos.
- `src/ps_agent/logging/event_log.py`: JSONL con `top_actions`, breakdown de la acción elegida, acciones legales y metadatos del turno.
- `src/ps_agent/inference`: belief state e inferencia de sets (placeholders listos para ampliar).

## Logging y métricas
`EventLogger` escribe en `artifacts/logs/*.log` con:
- `state_summary`, acción elegida y razones (desglose del evaluador)
- `top_actions` (lista ordenada con scores y breakdown)
- Acciones legales y datos adicionales (acción rival, ranking, etc.)

## Archivo `.env`
Coloca aquí los secretos necesarios:
```
DEEPSEEK_API_KEY=sk-...
```
El loader busca esta clave automáticamente para los agentes Deepseek.

## Próximos pasos sugeridos
- Integrar `ShowdownClient` con un servidor local/offline y validar `ProtocolParser`.
- Extender heurísticas del evaluador (daño aproximado, control de hazards, riesgo de setup).
- Añadir benchmarks reproducibles (`runner/tournament.py`) y reportes en `artifacts/reports/`.
