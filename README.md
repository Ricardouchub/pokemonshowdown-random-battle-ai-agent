# Pokemon Showdown Random Battle AI Agent

Este es un **agente autónomo avanzado** diseñado para competir en **Pokemon Showdown (Random Battles)**. Su arquitectura híbrida combina la velocidad de algoritmos clásicos con el razonamiento profundo de Modelos de Lenguaje (LLMs).

> [!WARNING]
> **Aviso Importante**: Este agente está diseñado estrictamente para su uso en **servidores locales privados** o en entornos controlados donde se permitan bots. Su uso en el servidor oficial de Pokemon Showdown (play.pokemonshowdown.com) puede violar los Términos de Servicio y resultar en un ban.

### 🧠 Arquitectura Híbrida
El agente opera bajo un sistema de **"Doble Sistema Cognitivo"**:
1.  **Fast System (Baseline)**: Un motor determinista basado en **Minimax (Lookahead 1-ply)** y heurísticas de evaluación de daño/riesgo. Garantiza decisiones seguras y legales en milisegundos.
2.  **Slow System (LLM Policy)**: Un modelo **Deepseek** en el loop que analiza el estado complejo del tablero, infiere sets del oponente y sugiere estrategias de alto nivel (Chain of Thought).

### ⚡ Características Clave
*   **Conectividad Real-Time**: Cliente WebSocket asíncrono que juega partidas en vivo contra humanos.
*   **Aprendizaje Continuo**: Sistema de "Observed Effectiveness" que aprende de resistencias/inmunidades en tiempo real y pipelines offline para mejorar su base de conocimiento.
*   **Observabilidad**: Dashboard web completo para visualizar el "proceso de pensamiento" del agente turno a turno.
*   **Modular**: Diseño desacoplado (Connector ↔ State ↔ Policy) que facilita la experimentación con nuevos modelos o reglas.

## Estado actual / problemas conocidos
- ✅ MVP offline: estructuras (`BattleState`, extractor de features), baseline policy, evaluator, runners y logging determinista.
- ✅ Knowledge: scripts para poblar cache desde PokeAPI/Deepseek (`fetch_cache`, `cache_agent`, `deepseek_agent`, `deepseek_cache_agent`) y manifest de features.
- ✅ LLM en tiempo real: `LLMPolicy` usa Deepseek para razonar turno a turno; `knowledge_feedback.jsonl` registra sugerencias de mejora.
- ✅ Live tooling: `runner/live_match.py` (WebSocket + auto login/autojoin/autochallenge) y dashboard `ps_agent.tools.live_monitor`.
- ✅ Lookahead Policy: Estrategia de anticipación (Minimax 1-ply) que calcula riesgos considerando la respuesta del rival (asume STAB si los ataques son desconocidos).
- ✅ Memoria a Corto Plazo: `BattleState` ahora tiene historial de eventos, permitiendo al LLM recordar fallos o patrones recientes.
- ✅ Safety Guardrails: Penalizaciones heurísticas y reglas estrictas en el prompt para evitar spam de estados y setups suicidas.
- ✅ Context Awareness: El LLM ahora recibe telemetría completa (HP%, Status, Boosts) para tomar decisiones informadas.
- ✅ Inmunidades Robustas: Corrección de fallo en tabla de tipos para garantizar conocimiento de inmunidades básicas (Tierra vs Volador, etc.).
- ✅ Chain of Thought (CoT): Razonamiento paso a paso integrado en el prompt para decisiones más profundas.
- ✅ Stat Awareness: Base de datos (`pokedex_db`) con stats reales. El agente conoce **Speed Tiers** y estima velocidad para decidir atacar/cambiar.
- ✅ Smart Pokedex Populator: Script (`populate_pokedex.py`) que usa IA para descubrir amenazas o descarga masiva (`--all`) desde PokeAPI, con tolerancia a fallos.
- ✅ Anti-Switch-Looping: Lógica heurística que detecta y penaliza fuertemente los bucles de cambios inútiles.
- 🚀 Próximo paso: Ampliar inferencia de sets y mejorar el manejo de errores de red.

## Custom Framework Architecture
Este proyecto implementa una arquitectura **100% Custom Python** diseñada específicamente para batallas en tiempo real, evitando el overhead de frameworks genéricos como LangChain o AutoGen.
- **Low Latency Core**: Pipeline de decisión optimizado que opera en milisegundos.
- **Direct LLM Integration**: Cliente `DeepseekClient` propio sin capas intermedias de abstracción.
- **Hybrid Intelligence**: Fusión determinista (Minimax/Heurísticas) + Probabilística (LLM) con control total sobre el flujo.


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
- Live runner (LLM Policy): `uv run python -m ps_agent.runner.live_match --server-url ws://localhost:8000/showdown/websocket --http-base https://play.pokemonshowdown.com --username CodexBot --autojoin lobby --policy llm`
- Live runner (Baseline Policy): `uv run python -m ps_agent.runner.live_match --server-url ws://localhost:8000/showdown/websocket --http-base https://play.pokemonshowdown.com --username CodexBot --autojoin lobby --policy baseline`
- Dashboard Web App: `uv run python -m ps_agent.tools.web_dashboard`


## Knowledge y cache
- `src/ps_agent/knowledge/online_agent.py`: usa PokeAPI para moves/items/abilities/type chart.
  ```bash
  uv run python -m ps_agent.knowledge.online_agent --move ember --item leftovers --ability levitate --type-chart
  ```
- `src/ps_agent/knowledge/fetch_cache.py`: CLI para cargar lotes desde listas/archivos.
- `src/ps_agent/knowledge/populate_pokedex.py`: Descarga stats de PokeAPI.
  ```bash
  # Descarga masiva (recomendado)
  uv run python -m ps_agent.knowledge.populate_pokedex --all
  # Descarga sugerida por IA
  uv run python -m ps_agent.knowledge.populate_pokedex --count 50
  ```
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
- **Offline Learning (Feedback Loop)**: Procesa el historial de batallas para enriquecer el knowledge automaticamente.
  ```bash
  uv run python -m ps_agent.learning.learner
  ```

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
1. Ajustar el parser contra logs reales (hazards, boosts, status, side conditions) y enriquecer el evaluador con heurísticas de daño/hazards.
2. Automatizar benchmarks en `runner/tournament.py`, generar reportes en `artifacts/reports/` y extender inference/belief state.
