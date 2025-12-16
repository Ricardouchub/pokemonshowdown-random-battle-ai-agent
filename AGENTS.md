# AGENTS.md — Pokémon Showdown Random Battle AI Agent (Codex)

## 0) Objetivo del proyecto (alto nivel)
Construir un **agente de IA** que juegue **Pokémon Showdown** en formato **Random Battle**, capaz de:

1. **Conectarse** a Showdown (modo entrenamiento preferido: servidor local/privado o simulación offline).
2. **Leer** el combate (equipo propio, equipo rival observado, estado de campo, turnos, etc.).
3. **Razonar** con **información incompleta** (Random Battle): inferir sets probables del rival (moves/items/abilities) a partir de evidencia.
4. **Decidir** acciones (move / switch / otras acciones permitidas según gen) con:
   - un baseline heurístico fuerte,
   - y luego búsqueda limitada (lookahead),
   - y luego aprendizaje (opcional por fases).
5. **Mejorar** el winrate a través de evaluación reproducible (self-play / vs baselines / torneos internos).

---

## LLM a usar: Deepseek API

---

## 1) Restricciones y políticas (obligatorio)
- **No automatizar en ladder público** sin confirmar que está permitido por reglas/ToS del servidor. La implementación debe permitir:
  - **Simulación offline** (preferida) y/o
  - **servidor local/privado**.
- El agente debe ser **determinista** bajo una semilla cuando sea posible (para reproducibilidad de evaluación).
- El código debe ser **modular**: connector / parser / state / inference / policy / evaluation / training.

---

## 2) Entorno y tooling (solo uv; prohibido pip)
### 2.1 Python
- Usar Python 3.11+ (preferido 3.12 si compatible).

### 2.2 Gestión de entorno
- **Usar solo `uv`** para:
  - crear venv,
  - instalar dependencias,
  - ejecutar scripts.
- **No usar `pip` directamente** en ningún paso.

### 2.3 Convenciones
- Formateo: `ruff format` o `black` (elige uno y aplícalo consistente).
- Lint: `ruff` (o similar).
- Tests: `pytest`.
- Logging: `structlog` o `logging` estándar (pero consistente), con logs en JSON opcional.

### 2.4 Comandos de referencia (para README y CI)
- Crear venv: `uv venv`
- Instalar: `uv sync` (si usamos pyproject + lock) o `uv pip install -r requirements.txt` (preferible pyproject).
- Ejecutar: `uv run python -m <module>` / `uv run pytest`

---

## 3) Definición de entregables por Fases (MVP → Inteligencia → Inferencia → Aprendizaje)

### Fase 1 — MVP operativo (Conector + Parser + Policy simple)
**Objetivo:** Terminar partidas completas sin romperse y tomar decisiones válidas.

**Entregables:**
1. Conector a Showdown:
   - Modo A: simulación offline (si existe motor utilizable localmente).
   - Modo B: cliente que se conecta a un servidor controlado (local/privado).
2. Parser del battle protocol:
   - Convertir eventos del combate a un **estado estructurado** interno.
3. Policy baseline heurística:
   - Selección de move/switch basada en reglas simples.
4. Runner de partidas:
   - Ejecutar N partidas y guardar logs + resumen.

**Criterios de aceptación:**
- 100 partidas consecutivas sin crash.
- Todas las decisiones enviadas son válidas (no moves inexistentes, no switches imposibles).
- Se guardan logs por turno con estado y acción.

---

### Fase 2 — Motor de evaluación + heurísticas fuertes
**Objetivo:** Mejorar winrate con una función de valor (scoring) y heurísticas que consideran campo y riesgo.

**Entregables:**
1. Módulo de **damage approximation** (aunque sea heurístico):
   - Rango de daño estimado o proxy razonable.
2. Función de valor (eval):
   - Score = material + posición + control de campo + progreso de wincon + riesgo.
3. Policy mejorada:
   - Rankear todas las acciones legales por score esperado.

**Criterios de aceptación:**
- Subida medible de winrate vs policy de Fase 1 en un benchmark fijo (mismas seeds/oponentes).
- Explicación por acción: top-K acciones con razones.

---

### Fase 3 — Inferencia probabilística de sets (Random Battle)
**Objetivo:** Manejar información incompleta y actualizar creencias según evidencia.

**Entregables:**
1. Base de “hipótesis de set”:
   - Para cada especie, lista de sets plausibles (moves/items/abilities) con prior.
2. Belief state por Pokémon rival:
   - Distribución de probabilidad sobre sets.
3. Actualización bayesiana/heurística por evidencia:
   - Move revelado → filtra sets.
   - Daño observado → restringe posibles spreads/items.
   - Velocidad relativa → infiere scarf/boost/spread.
4. Policy que integra incertidumbre:
   - Evaluación esperada por acción usando muestreo de sets.

**Criterios de aceptación:**
- El sistema reduce incertidumbre (entropía) con el tiempo sin colapsar erróneamente.
- Mejora de winrate vs Fase 2 en benchmark con rivales variados.

---

### Fase 4 — “Mejora” vía aprendizaje (opcional, después de estabilizar)
**Objetivo:** Aumentar winrate mediante datos o self-play.

**Opciones (elegir una primero):**
- Imitation learning:
  - Dataset de replays procesados → modelo que predice acción.
- RL (self-play):
  - Recompensa por victoria, shaping por progreso.

**Criterios de aceptación:**
- Curva de aprendizaje reproducible y mejora vs baseline fuerte.

---

## 4) Arquitectura de carpetas (propuesta obligatoria)
pokemon-showdown-agent/
pyproject.toml
README.md
AGENTS.md
src/
ps_agent/
init.py
config/
default.yaml
connector/
showdown_client.py
protocol_parser.py
state/
battle_state.py
feature_extractor.py
encoding.py
knowledge/
type_chart.py
moves_db.py
items_db.py
abilities_db.py
randbats_sets.py
inference/
belief_state.py
set_inference.py
policy/
baseline_rules.py
evaluator.py
lookahead.py
runner/
play_match.py
tournament.py
logging/
event_log.py
tests/
test_protocol_parser.py
test_feature_extractor.py
test_policy_valid_actions.py
test_inference_updates.py
data/
replays_raw/
replays_parsed/
randbats_priors/
artifacts/
logs/
reports/


**Regla:** cada módulo debe poder testearse aislado.

---

## 5) “Single Source of Truth” para Estado (BattleState)
Codex debe implementar un `BattleState` que sea:
- inmutable por turno (o con snapshots),
- serializable a JSON,
- con versión de esquema (schema_version).

### 5.1 Campos mínimos de BattleState
**Metadatos**
- `battle_id`
- `gen`
- `format` (debe ser `"randombattle"` o equivalente)
- `turn`
- `timestamp`

**Jugadores**
- `self` y `opponent`:
  - `name`
  - `rating` (si está disponible)
  - `active_slot` (índice)
  - `team` (lista de 6 `PokemonState`)

**Campo global**
- `weather` (None | rain | sun | sand | hail/snow)
- `terrain` (None | electric | grassy | psychic | misty)
- `trick_room_turns_remaining`
- `tailwind_turns_remaining_self` / `tailwind_turns_remaining_opp`
- `screens_self`: reflect/light_screen/aurora_veil + turns
- `screens_opp`: idem
- `hazards_self_side`: stealth_rock, spikes_layers(0-3), toxic_spikes_layers(0-2), sticky_web(bool)
- `hazards_opp_side`: idem
- `field_effects`: list (substitute, safeguarding, etc. si aplica)
- `last_actions`: último move/switch por jugador (si disponible)

---

## 6) Lista EXACTA de FEATURES (Feature Extractor)
Codex debe crear un extractor que transforme `BattleState` → `FeatureVector`.

### 6.1 Convención de features
- Todas las features deben ser:
  - numéricas (float/int) o binarias (0/1),
  - sin strings en el vector final,
  - con nombres estables (para logging y ML).
- Output:
  - `features_dense: dict[str, float]`
  - y opcionalmente `features_sparse` si hace falta.

### 6.2 Features globales
1. `turn_norm` = min(turn, 50) / 50
2. `num_pokemon_alive_self`
3. `num_pokemon_alive_opp`
4. `total_hp_fraction_self` = suma hp_frac vivos / 6
5. `total_hp_fraction_opp`
6. `weather_onehot_{rain,sun,sand,snow,none}`
7. `terrain_onehot_{electric,grassy,psychic,misty,none}`
8. `trick_room_active` (0/1)
9. `trick_room_turns_norm` = turns_remaining / 5 (clamp 0..1)
10. `tailwind_active_self` (0/1)
11. `tailwind_turns_norm_self` = remaining/4
12. `tailwind_active_opp`
13. `tailwind_turns_norm_opp`
14. `reflect_active_self` (0/1)
15. `reflect_turns_norm_self`
16. `lightscreen_active_self` (0/1)
17. `lightscreen_turns_norm_self`
18. `auroraveil_active_self` (0/1)
19. `auroraveil_turns_norm_self`
20. `reflect_active_opp` (0/1)
21. `reflect_turns_norm_opp`
22. `lightscreen_active_opp` (0/1)
23. `lightscreen_turns_norm_opp`
24. `auroraveil_active_opp` (0/1)
25. `auroraveil_turns_norm_opp`
26. `hazard_sr_self` (0/1)
27. `hazard_spikes_layers_self` (0..3)
28. `hazard_tspikes_layers_self` (0..2)
29. `hazard_web_self` (0/1)
30. `hazard_sr_opp` (0/1)
31. `hazard_spikes_layers_opp`
32. `hazard_tspikes_layers_opp`
33. `hazard_web_opp`

### 6.3 Features del Pokémon activo (self y opp)
Para **cada lado** (self/opp), crear el mismo set con prefijo:
- `self_active_*`
- `opp_active_*`

**Identidad y tipo**
34. `{side}_active_type_onehot_<18 types>` (18 binarias)
35. `{side}_active_dual_type` (0/1)
36. `{side}_active_level_norm` (level/100 si aplica)

**HP/Status**
37. `{side}_active_hp_frac` (0..1)
38. `{side}_active_status_onehot_{none,brn,psn,tox,par,slp,frz}` (7)
39. `{side}_active_is_fainted` (0/1)

**Boosts (clamp -6..+6, norm a 0..1)**
40. `{side}_active_boost_atk_norm`
41. `{side}_active_boost_def_norm`
42. `{side}_active_boost_spa_norm`
43. `{side}_active_boost_spd_norm`
44. `{side}_active_boost_spe_norm`
45. `{side}_active_boost_acc_norm`
46. `{side}_active_boost_eva_norm`

**Volátiles relevantes**
47. `{side}_active_substitute` (0/1)
48. `{side}_active_confusion` (0/1)
49. `{side}_active_taunt` (0/1)
50. `{side}_active_torment` (0/1)
51. `{side}_active_encore` (0/1)
52. `{side}_active_disable` (0/1)
53. `{side}_active_leech_seeded` (0/1)
54. `{side}_active_perish_song_active` (0/1)
55. `{side}_active_perish_song_count_norm` (count/3)

**Información conocida**
56. `{side}_active_item_known` (0/1)
57. `{side}_active_ability_known` (0/1)
58. `{side}_active_moves_known_count` (0..4)
59. `{side}_active_last_move_known` (0/1)

### 6.4 Features “matchup” (self vs opp activos)
60. `type_effectiveness_self_to_opp_best` (máxima efectividad entre moves conocidos; si no hay, proxy por tipos)
61. `type_effectiveness_opp_to_self_best` (análogo)
62. `type_resistance_self_vs_opp_stab` (proxy)
63. `speed_advantage_prob` (0..1) — probabilidad de que self vaya primero
64. `ko_prob_self_to_opp` (0..1) — estimación/proxy de KO en 1 turno
65. `ko_prob_opp_to_self` (0..1)
66. `twohko_prob_self_to_opp` (0..1)
67. `twohko_prob_opp_to_self` (0..1)
68. `switch_disadvantage_score` (float) — penaliza quedar atrapado en mal matchup
69. `setup_risk_score` (float) — riesgo de que el rival se boostee “gratis”
70. `hazard_pressure_score` (float) — valor de hazards vs equipos actuales

### 6.5 Features de equipo (resumen por lado)
Para cada lado, prefijo `{side}_team_*`:
71. `{side}_team_has_spinner` (0/1) (si se conoce o se infiere para self; para opp usar probabilidad)
72. `{side}_team_has_defogger` (0/1)
73. `{side}_team_has_priority_user` (0/1) (bullet punch, extreme speed, etc.)
74. `{side}_team_has_scarfer_prob` (0..1)
75. `{side}_team_avg_hp_frac`
76. `{side}_team_num_statused`
77. `{side}_team_num_boosted` (cuántos tienen boosts != 0)
78. `{side}_team_type_coverage_<18 types>` (18 floats 0..1: fracción de tipos presentes en el team)

### 6.6 Features de incertidumbre (solo oponente)
79. `opp_active_set_entropy_norm` (0..1)
80. `opp_team_total_entropy_norm` (0..1)
81. `opp_active_item_choice_prob` (0..1)
82. `opp_active_item_boots_prob` (0..1)
83. `opp_active_item_sash_prob` (0..1)
84. `opp_active_ability_key_prob` (0..1) — abilities “game-changing” según base
85. `opp_active_has_recovery_prob` (0..1)
86. `opp_active_has_setup_prob` (0..1)
87. `opp_active_has_status_move_prob` (0..1)
88. `opp_active_has_hazard_move_prob` (0..1)
89. `opp_active_has_removal_prob` (0..1)

> Nota: El extractor debe producir el mismo orden y nombres siempre. Guardar un “feature manifest” en `artifacts/` con la lista y descripciones.

---

## 7) Knowledge Base (datos necesarios)
Codex debe implementar loaders para:
- Type chart (18 tipos).
- Moves: tipo, categoría, potencia, precisión, prioridad, flags (contact, sound, etc.), si es status.
- Items: efectos clave (boots, sash, choice, leftovers, berry…).
- Abilities: efectos clave (intimidate, levitate, regen…).
- Random Battle sets priors (si se dispone):
  - mapping especie → lista de sets con prior.

**Requisitos:**
- Los datos deben versionarse (hash/fecha).
- Si se actualizan, no romper experimentos pasados: guardar versión en logs.

---

## 8) Inference (Belief State) — especificación
Codex debe crear un `BeliefState` por Pokémon rival:

### 8.1 Estructura mínima
- `candidates`: lista de `SetHypothesis`
  - `moves` (set de movimientos)
  - `item`
  - `ability`
  - `nature/spread` (opcional)
  - `prior_prob`
  - `posterior_prob`
- `evidence_log`: lista de eventos usados para actualizar.

### 8.2 Reglas de actualización (mínimo viable)
Al observar:
1. **Move usado**:
   - eliminar sets que no contengan ese move.
2. **Item revelado**:
   - eliminar sets con item distinto, y setear `item_known = 1`.
3. **Ability revelada**:
   - igual que item.
4. **Daño observado** (aprox):
   - si un set implica daño imposible (muy alto/bajo), reducir prob.
5. **Velocidad relativa**:
   - si opp supera a self en condiciones donde no debería, aumentar prob de scarf/boost.

### 8.3 Métricas
- Calcular entropía normalizada:
  - `H = -sum(p log p) / log(N)` (clamp 0..1)

---

## 9) Policy / Decision Making — especificación

### 9.1 Baseline Rules (Fase 1)
Debe:
- Enumerar acciones legales (moves/switch).
- Aplicar reglas:
  1. Si hay KO “seguro” con un move → preferir atacar.
  2. Si estamos en matchup muy desfavorable y hay switch a resistencia → preferir switch.
  3. Evitar moves status “gratis” si el rival amenaza KO inmediato (salvo que sea wincon).
  4. No sacrificar un Pokémon clave si hay alternativa.

### 9.2 Evaluator (Fase 2)
Implementar `evaluate(state, action) -> score`:
Componentes sugeridos (pesos configurables):
- `material_score` (vivos + hp)
- `position_score` (type matchup + speed control)
- `field_control_score` (hazards + removal + screens)
- `wincon_progress_score` (debilitar checks, set up seguro)
- `risk_penalty` (prob de perder por KO / roll / setup rival)

### 9.3 Lookahead (Fase 2.5/3)
- Búsqueda 1–2 ply:
  - Simular respuesta rival usando:
    - policy rival simple, o
    - muestreo de sets + top actions.
- Score final = expected value (promedio ponderado).

### 9.4 Integración con incertidumbre (Fase 3)
- Para acciones, computar:
  - `E[score]` sobre muestreos de set rival (y/o ranges).
- Preferir acciones robustas:
  - penalizar varianza alta si hay alternativas seguras (configurable).

---

## 10) Runner & Evaluación — especificación
Codex debe implementar:
- `play_match(seed, policy_self, policy_opp, mode)` → resultado + logs.
- `tournament(N, opponents)` → métricas agregadas.

### 10.1 Métricas mínimas
- `winrate`
- `avg_turns`
- `crash_rate`
- `invalid_action_rate`
- `decision_latency_ms` (p50/p95)
- `entropy_reduction` (solo Fase 3)

### 10.2 Logging mínimo por turno
Guardar JSON line por turno con:
- `turn`
- `battle_id`
- `state_summary` (hp, status, hazards, weather)
- `features_hash` + top features (opcional)
- `belief_summary` (entropía + top-3 sets)
- `legal_actions_count`
- `chosen_action`
- `topk_actions` (acción + score + razones)

---

## 11) Tests (obligatorios)
Codex debe crear tests para:
1. Parser:
   - Dado un stream de eventos, produce BattleState consistente.
2. Feature extractor:
   - No NaNs, rangos correctos, one-hots válidos.
3. Policy validity:
   - La acción elegida siempre pertenece al set de acciones legales.
4. Belief updates:
   - Move observado reduce candidatos y aumenta posterior apropiadamente.
5. Reproducibilidad:
   - Con seed fija, el match runner produce el mismo resultado (si el motor lo permite).

---

## 12) Configuración (YAML)
Crear `config/default.yaml` con:
- Pesos del evaluator
- Número de muestras de sets
- Profundidad de lookahead
- Modo de riesgo: `safe | balanced | aggressive`
- Paths de datasets
- Semilla global

---

## 13) Prioridades de implementación (orden exacto)
Codex debe seguir este orden para minimizar bloqueos:

1. Estructuras de datos: `BattleState`, `PokemonState`, `FieldState`.
2. Logger de eventos + schema_version.
3. Conector + parser mínimo (convertir eventos a estado).
4. Enumeración de acciones legales.
5. Baseline policy (reglas simples).
6. Runner de N partidas + logs.
7. Feature extractor (con manifest).
8. Evaluator scoring + explicación (reasons).
9. Lookahead (1-ply).
10. Knowledge base loaders.
11. BeliefState + set inference + entropía.
12. Policy con incertidumbre.
13. Benchmark suite + report.

---

## 14) Definition of Done (DoD)
El proyecto se considera “listo” cuando:
- Puede ejecutar 500 partidas offline/privadas con crash_rate = 0.
- invalid_action_rate = 0.
- Tiene benchmark reproducible (misma semilla y opponents).
- Incluye:
  - README con instrucciones uv,
  - explicación de arquitectura,
  - reporte de métricas,
  - y logs interpretables por humano.

---

## 15) Notas de implementación (decisiones obligatorias)
- Mantener separación estricta:
  - `connector/parser` NO decide,
  - `policy` NO parsea,
  - `inference` NO envía acciones.
- Todo componente crítico debe ser mockeable para tests.
- Guardar versiones de datos (type chart / moves / sets) en cada ejecución.