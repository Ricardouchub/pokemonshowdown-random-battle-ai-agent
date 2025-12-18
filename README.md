# Pokemon Showdown Random Battle AI Agent

Agente modular para Pokemon Showdown (Random Battle) alineado con lo definido en `AGENTS.md`. Incluye conectores, estado centralizado, politicas deterministas y pipelines de knowledge alimentados por PokeAPI y Deepseek.

## Estado actual / problemas conocidos
- ✅ MVP offline: estructuras (`BattleState`, extractor de features), baseline policy, evaluator, runners y logging determinista.
- ✅ Knowledge: scripts para poblar cache desde PokeAPI/Deepseek (`fetch_cache`, `cache_agent`, `deepseek_agent`, `deepseek_cache_agent`) y manifest de features.
- ✅ LLM en tiempo real: `LLMPolicy` usa Deepseek para razonar turno a turno; `knowledge_feedback.jsonl` registra sugerencias de mejora.
- ✅ Live tooling: `runner/live_match.py` (WebSocket + auto login/autojoin/autochallenge) y dashboard `ps_agent.tools.live_monitor`.
- ✅ Live tooling: `runner/live_match.py` (WebSocket + auto login/autojoin/autochallenge) funciona correctamente. El bug de "Waiting for opponent" fue resuelto (protocolo corregido + sanitización).
- ✅ Live tooling: `runner/live_match.py` (WebSocket + auto login/autojoin/autochallenge) funciona correctamente. El bug de "Waiting for opponent" fue resuelto (protocolo corregido + sanitización).
- ✅ Lookahead Policy: Estrategia de anticipación (Minimax 1-ply) que calcula riesgos considerando la respuesta del rival (asume STAB si los ataques son desconocidos).
- ✅ Memoria a Corto Plazo: `BattleState` ahora tiene historial de eventos, permitiendo al LLM recordar fallos o patrones recientes.
- ✅ Fusión de Políticas: `LLMPolicy` ahora integra `Lookahead` como consejero interno, proveyendo al LLM de cálculos de riesgo precisos en su prompt.
- 🚀 Próximo paso: Ampliar inferencia de sets y mejorar el manejo de errores de red.

## Requisitos
- Python 3.11+
- [uv](https://github.com/astral-sh/uv)
- Opcional: `DEEPSEEK_API_KEY` en `.env` para los agentes basados en Deepseek

## Setup rapido
```bash
uv venv
uv sync --all-extras
```

## Comandos utiles
- Lint/format: `uv run ruff check` y `uv run ruff format`
- Tests: `uv run pytest`
- Partida simulada stub: `uv run python -m ps_agent.runner.play_match --seed 42 --max-turns 5`
- Live runner (servidor local): `uv run python -m ps_agent.runner.live_match --server-url ws://localhost:8000/showdown/websocket --http-base https://play.pokemonshowdown.com --username CodexBot --autojoin lobby`
- Politica LLM (Deepseek): `uv run python -m ps_agent.runner.play_match --policy llm --seed 101`
- Dashboard live de reasoning: `uv run python -m ps_agent.tools.live_monitor --log-dir artifacts/logs/live`

## Knowledge y cache
- `src/ps_agent/knowledge/online_agent.py`: usa PokeAPI para moves/items/abilities/type chart.
  ```bash
  uv run python -m ps_agent.knowledge.online_agent --move ember --item leftovers --ability levitate --type-chart
  ```
- `src/ps_agent/knowledge/fetch_cache.py`: CLI para cargar lotes desde listas/archivos.
- `src/ps_agent/runner/cache_agent.py`: rellena el cache con un set curado de recursos PokeAPI.
- `src/ps_agent/knowledge/deepseek_agent.py`: genera perfiles JSON (pokemon/items/abilities) con Deepseek.
  ```bash
  uv run python -m ps_agent.knowledge.deepseek_agent --pokemon charizard --items life-orb --abilities levitate
  ```
- `src/ps_agent/runner/deepseek_cache_agent.py`: consulta PokeAPI para obtener nombres y genera perfiles con Deepseek automaticamente.
  ```bash
  uv run python -m ps_agent.runner.deepseek_cache_agent --pokemon-limit 100 --item-limit 80 --ability-limit 80
  ```
- `src/ps_agent/knowledge/loader.py`: construye un `KnowledgeBase` desde `data/knowledge_cache/` para el evaluador/policy.
- `artifacts/knowledge_feedback.jsonl`: log donde el LLM deja sugerencias de knowledge (acciones exitosas/fallidas).

## Live match runner
`src/ps_agent/runner/live_match.py` conecta el agente a un servidor Showdown via WebSocket. Maneja `challstr`, obtiene el assertion (vía `--http-base`), parsea `|request|` JSON, actualiza `BattleState`, arma el set de acciones legales y envia `/choose ...` usando la politica seleccionada (`baseline` o `llm`). La comunicación funciona (ver `sending_battle_command` en consola), pero la respuesta del servidor queda bloqueada (ver sección de problemas).

Uso tipico (servidor local en `http://localhost:8000`):
```bash
uv run python -m ps_agent.runner.live_match \
  --server-url ws://localhost:8000/showdown/websocket \
  --http-base https://play.pokemonshowdown.com \
  --username CodexBot \
  --autojoin lobby \
  --policy llm
```
Luego desafia a `CodexBot` desde el cliente web. Cada batalla genera un log JSONL en `artifacts/logs/live/<battle-id>.log` con `legal_actions`, `top_actions` y el breakdown del evaluador.

## Componentes principales
- `src/ps_agent/state`: `BattleState`, `PokemonState`, `FieldState`, extractor de features y encoding.
- `src/ps_agent/connector`: `ShowdownClient` (websocket) y `ProtocolParser` (convierte eventos del protocolo en snapshots).
- `src/ps_agent/policy`: `BaselinePolicy`, `Evaluator`, `Lookahead` y enumeracion de acciones legales. `LLMPolicy` delega el razonamiento al LLM (Deepseek) y registra sugerencias de knowledge; si no hay respuesta valida, cae en el baseline determinista.
- `src/ps_agent/runner`: `play_match`, `tournament`, agentes de cache (PokeAPI/Deepseek) y el live runner.
- `src/ps_agent/logging/event_log.py`: escribe JSONL con `legal_actions`, `chosen_action`, `top_actions` y metadatos del turno.
- `src/ps_agent/inference`: scaffolding para belief state e inferencia de sets.

## Logging y metricas
`EventLogger` coloca entradas en `artifacts/logs/*.log` con:
- `state_summary` por turno
- Acciones legales y top-k (score + breakdown)
- Razones del evaluador y campos extra (ranking, accion rival)

## Archivo `.env`
```
DEEPSEEK_API_KEY=sk-...
```
El loader usa esta clave cuando se ejecutan los agentes Deepseek.

## Siguientes pasos recomendados
1. **Resolver bloqueo “Waiting for opponent…”**: inspeccionar consola del servidor (`npm run start`) para detectar `CMDFAIL`/`error` y ajustar el formato del `/choose` o la sesión observada. Alternativa: integrar Poke-Env (como el `agents.py` de referencia) para aislar la política del frontend Showdown.
2. Ajustar el parser contra logs reales (hazards, boosts, status, side conditions) y enriquecer el evaluador con heurísticas de daño/hazards.
3. Automatizar benchmarks en `runner/tournament.py`, generar reportes en `artifacts/reports/` y extender inference/belief state.
