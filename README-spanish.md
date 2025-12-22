# Pokemon Showdown Random Battle AI Agent

![Status](https://img.shields.io/badge/Status-Completed-2ECC71?logo=checkmarx&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.12%2B-3776AB?logo=python&logoColor=white)
![DeepSeek](https://img.shields.io/badge/DeepSeek-LLM-8A2BE2?logo=deepnote&logoColor=white)
![Pokemon Showdown](https://img.shields.io/badge/Pokemon%20Showdown-Server-3776AB?logo=pokemonshowdown&logoColor=white)
![uv](https://img.shields.io/badge/uv-Tool-3776AB?logo=uv&logoColor=white)
![Ruff](https://img.shields.io/badge/Ruff-Tool-3776AB?logo=ruff&logoColor=white)
![Pytest](https://img.shields.io/badge/Pytest-Tool-3776AB?logo=pytest&logoColor=white)

Este es un **agente autónomo avanzado** diseñado para competir en **Pokemon Showdown (Random Battles)**. Su arquitectura híbrida combina la velocidad de algoritmos clásicos con el razonamiento profundo de Modelos de Lenguaje (LLMs).

Además, el agente posee capacidades de **auto-aprendizaje**: es capaz de adaptar su estrategia a medida que se desarrollan las batallas mediante el sistema de *Observed Effectiveness* (aprendiendo inmunidades/resistencias en tiempo real) y refinar su base de conocimiento a largo plazo a través de bucles de retroalimentación (*Knowledge Feedback Loop*).

> [!WARNING]
> **Aviso Importante**: Este agente está diseñado estrictamente para su uso en **servidores locales privados** o en entornos controlados donde se permitan bots. Su uso en el servidor oficial de Pokemon Showdown (play.pokemonshowdown.com) puede violar los Términos de Servicio y resultar en un ban.

### Características
*   **Conectividad en tiempo real**: Cliente WebSocket asíncrono que juega partidas en vivo contra humanos.
*   **Aprendizaje Continuo**: Sistema de "Observed Effectiveness" que aprende de resistencias/inmunidades en tiempo real y pipelines offline para mejorar su base de conocimiento.
*   **Observabilidad**: Dashboard web completo para visualizar el "proceso de pensamiento" del agente turno a turno.
*   **Modular**: Diseño desacoplado (Connector ↔ State ↔ Policy) que facilita la experimentación con nuevos modelos o reglas.

### Arquitectura Híbrida
El agente opera bajo un sistema de **"Doble Sistema Cognitivo"**:
1.  **Fast System (Baseline)**: Un motor determinista basado en **Minimax (Lookahead 1-ply)** y heurísticas de evaluación de daño/riesgo. Garantiza decisiones seguras y legales en milisegundos.
2.  **Slow System (LLM Policy)**: Un modelo en el loop que analiza el estado complejo del tablero, infiere sets del oponente y sugiere estrategias de alto nivel (Chain of Thought).

### Chain of Thought (Razonamiento)
El agente no solo elige movimientos, **piensa**. El prompt de sistema incluye reglas estratégicas críticas ("CRITICAL STRATEGIC RULES") como:
1.  **Check Speed**: Antes de atacar, verifica si eres más rápido consultando la Pokedex.
2.  **Avoid Switch Spam**: Penaliza cambios consecutivos si no son forzados.
3.  **Analyze Matchup**: Evalúa tipos y estados antes de actuar.

La respuesta del LLM es un JSON estructurado que incluye un campo `chain_of_thought` donde explica su lógica paso a paso (ej: *"Garchomp es más rápido que yo, debo cambiar a Skarmory para resistir el ataque Tierra"*). Esto permite auditar y depurar estrategias complejas.

## Estado actual y/o problemas conocidos
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

## Arquitectura personalizada
Este proyecto implementa una arquitectura **100% Custom Python** diseñada específicamente para batallas en tiempo real, evitando el overhead de frameworks genéricos como LangChain o AutoGen.
- **Low Latency Core**: Pipeline de decisión optimizado que opera en milisegundos.
- **Direct LLM Integration**: Cliente `DeepseekClient` propio sin capas intermedias de abstracción.
- **Hybrid Intelligence**: Fusión determinista (Minimax/Heurísticas) + Probabilística (LLM) con control total sobre el flujo.


## Requisitos
- Python 3.11+
- [uv](https://github.com/astral-sh/uv)
- Opcional: `DEEPSEEK_API_KEY` en `.env`, o cambiarlo por cualquier otro LLM.

## Setup rapido
```bash
uv venv
uv sync --all-extras
```

## Comandos 
- Live runner (LLM Policy): `uv run python -m ps_agent.runner.live_match --server-url ws://localhost:8000/showdown/websocket --http-base https://play.pokemonshowdown.com --username CodexBot --autojoin lobby --policy llm`
- Live runner (Baseline Policy): `uv run python -m ps_agent.runner.live_match --server-url ws://localhost:8000/showdown/websocket --http-base https://play.pokemonshowdown.com --username CodexBot --autojoin lobby --policy baseline`
- Dashboard Web App: `uv run python -m ps_agent.tools.web_dashboard`
- Tests: `uv run pytest`


## Como funciona el Live match runner
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
Luego desafia al agente desde el cliente web. Cada batalla genera un log JSONL en `artifacts/logs/live/<battle-id>.log` con `legal_actions`, `top_actions` y el breakdown del evaluador.


## Como funciona el knowledge cache
- `src/ps_agent/knowledge/online_agent.py`: usa PokeAPI para moves/items/abilities/type chart.
  ```bash
  uv run python -m ps_agent.knowledge.online_agent --move ember --item leftovers --ability levitate --type-chart
  ```
- `src/ps_agent/knowledge/fetch_cache.py`: CLI para cargar lotes desde listas/archivos.
- `src/ps_agent/knowledge/populate_pokedex.py`: Descarga stats de PokeAPI.
  ```bash
  # Descarga masiva 
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


## Como funciona el logging / metricas
`EventLogger` coloca entradas en `artifacts/logs/*.log` con:
- `state_summary` por turno
- Acciones legales y top-k (score + breakdown)
- Razones del evaluador y campos extra (ranking, accion rival)


## Estructura del Proyecto

```text
pokemonshowdown-random-battle-ai-agent/
├── src/ps_agent/
│   ├── connector/          # Capa de conexión
│   │   ├── client.py           # Cliente WebSocket (ShowdownClient)
│   │   └── protocol_parser.py  # Traductor de mensajes brutos a estado
│   ├── knowledge/          # Base de Conocimiento
│   │   ├── pokedex_db.py       # DB de especies y Stats
│   │   ├── populate_pokedex.py # Script híbrido (LLM+API) para poblar DB
│   │   ├── type_chart.py       # Tabla de efectividades
│   │   └── moves_db.py         # DB de movimientos
│   ├── policy/             # Cerebro Híbrido
│   │   ├── llm_policy.py       # Slow System: Razonamiento vía Deepseek
│   │   ├── evaluator.py        # Fast System: Heurísticas y cálculo de daño
│   │   └── lookahead.py        # Minimax 1-ply (Baseline)
│   ├── state/              # Memoria del Agente
│   │   ├── battle_state.py     # Snapshot inmutable del turno actual
│   │   └── pokemon_state.py    # Representación de mons (HP, Status, Stats)
│   ├── llm/                # Integración IA
│   │   └── deepseek_client.py  # Cliente HTTP optimizado para LLMs
│   ├── runner/             # Ejecutables
│   │   └── live_match.py       # Loop principal para jugar en servidor real
│   └── tools/              # Herramientas de Observabilidad
│       ├── web_dashboard.py    # Backend del Dashboard (FastAPI)
│       └── static/index.html   # Frontend: Visualiza CoT y estado
├── data/knowledge_cache/   # Cache persistente (JSON) de PokeAPI
├── artifacts/logs/         # Logs detallados (JSONL) de cada partida
├── tests/                  # Tests unitarios (pytest)
├── WORKFLOW.md             # Diagrama de arquitectura y flujo de datos
└── README.md               # Documentación general
```

## Componentes principales
- `src/ps_agent/state`: `BattleState`, `PokemonState` (con soporte de stats), `FieldState` y extractores de features. Es la "memoria" del agente.
- `src/ps_agent/knowledge`:
    - `pokedex_db.py`: Base de datos de especies con base stats y tipos.
    - `populate_pokedex.py`: Script híbrido (LLM + PokeAPI) para poblar la BD.
    - `moves_db.py`, `items_db.py`, `abilities_db.py`: Bases de datos estáticas/cacheadas.
    - `type_chart.py`: Tabla de efectividades e inmunidades.
- `src/ps_agent/policy`:
    - `Evaluator`: Corazón del Fast System. Calcula daños, riesgos y heurísticas (anti-looping).
    - `Lookahead`: Implementación Minimax 1-ply.
    - `LLMPolicy`: Interfaz con Deepseek. Construye el prompt estratégico (CoT + Stats) y parsea la respuesta JSON.
- `src/ps_agent/llm`: `DeepseekClient`. Cliente directo HTTP optimizado para baja latencia.
- `src/ps_agent/connector`: `ShowdownClient` (WebSocket) y `ProtocolParser`. Traduce el stream de texto de Showdown a actualizaciones de estado atómicas.
- `src/ps_agent/runner`:
    - `live_match.py`: Orquestador para jugar en el servidor real.
    - `cache_agent.py` / `deepseek_agent.py`: Tools offline para generar conocimiento.
- `src/ps_agent/tools`:
    - `web_dashboard.py`: Backend FastAPI que sirve el estado en tiempo real.
    - `static/index.html`: Dashboard visual que muestra HP, Stats y el **Chain of Thought** del agente.
- `src/ps_agent/logging`: `EventLogger`. Sistema de logs estructurados (JSONL) para auditoría y aprendizaje post-partida.


## Autor
**Ricardo Urdaneta**

[LinkedIn](https://www.linkedin.com/in/ricardourdanetacastro/) | [GitHub](https://github.com/Ricardouchub)