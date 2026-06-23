# 4J Timing Traceability Report
## G1 Deterministic Safety Runtime — Microfase 4J-P3

**Estado:** CERRADA — pendiente commit/push
**Commit harness:** f9cbdcf
**Principio rector:** No timing claim without trace
**Principio PM:** same behavior as P2, now with time

---

## Objetivo

Medir la latencia interna del safety runtime para rutas validadas en 4J-P2,
con trazabilidad por event_id unico por muestra. P3 es una fase de medicion,
no de descubrimiento.

## Metodologia

- Harness: `sim_runtime/4J/harness_4J_P3_timing_matrix.py`
- t0 = harness publish timestamp inmediatamente antes de publish (no tiempo DDS exacto)
- t1 = primera linea de callback RecoveryEvent (R2/R3) o SafetyAction (R1)
- t2 = primera linea de callback RecoveryEvent (R1)
- Topologia verificada por nombre de nodo antes de cada run
- docker restart antes de cada case group (anti-patterns #71 #78)
- Estado limpio confirmado antes de cada batch

---

## Rutas medidas

### P3-A — Direct / Terminal

| Case | Route | N validas | min_ms | mean_ms | max_ms | p95_ms_exploratory | Limitacion |
|---|---|---|---|---|---|---|---|
| STALE | R2 | 3 | 1005.513 | 1005.696 | 1005.890 | 1005.685 | MAX_AUTO_RETRIES=3 |
| FREEZE | R3 | 10 | 3.527 | 3.725 | 3.957 | 3.811 | — |
| NANINF | R3 | 10 | 3.485 | 3.777 | 4.212 | 4.018 | — |
| TIMESTAMP | R3 | 10 | 3.596 | 3.861 | 4.628 | 4.012 | — |
| FALLEN_DIRECT | R2 | 3 | 1005.620 | 1005.846 | 1006.206 | 1005.711 | MAX_AUTO_RETRIES=3 |

### P3-B — Governed

| Case | Route | N validas | T_event_to_action_ms | T_action_to_recovery_ms | T_event_to_recovery_ms | Limitacion |
|---|---|---|---|---|---|---|
| TX-011 | R1 | 1 | 3.503 | 2.627 | 6.130 | one-shot por sesion orchestrator |

**Event ID Run 1:** `4JP3-TX011_GOVERNED-001-1f6a`

---

## Metricas duales — rutas R2 (STALE / FALLEN_DIRECT)

La latencia ~1005ms en rutas R2 incluye `wait_for_primary_restore` (~1s simulada).
No es dispatch puro. Dos metricas separadas:

| Metrica | Valor | Fuente |
|---|---|---|
| t0 → RecoveryEvent (harness) | ~1005ms | harness timing |
| t1 → t2 dispatch interno recovery_g1 | ~0.86ms | logs 4F-P5 |

No mezclar estas dos metricas en claims de paper.

---

## Limitaciones de protocolo

### STALE y FALLEN_DIRECT — N=3
`recovery_g1` tiene `MAX_AUTO_RETRIES=3` por diseno. Runs 4+ cambian
la condicion experimental de auto-recovery timing a politica de escalacion manual.
N=3 es el maximo valido para rutas R2/REC-AUTO por sesion de contenedor.
Aprobado PM explicitamente.

### TX-011 governed — N=1
La maquina de estados del orchestrator realiza TX-011 desde estado `(SAFE, NONE)`.
Despues de Run 1 el estado queda en `(STABILITY_RISK, R3)` y TX-011 no es
elegible nuevamente sin reinicio. N=1 es el maximo valido por sesion.
Aprobado PM explicitamente.

### p95 exploratorio
Con N=3 y N=10, p95_ms_exploratory no es estadisticamente fuerte.
Etiquetado como exploratorio en todos los outputs.

---

## Trazabilidad causal preservada

Todas las muestras validas preservan:
- `SafetyEvent.event_id` unico por muestra
- `RecoveryEvent.notes` contiene `parent_event_id=<event_id>`
- Para governed: `SafetyAction.parent_event_id=<event_id>`

---

## Regresion

```
safety_orchestrator_g1: 63/63 PASS
test_g1_safety_layer:    2/2 PASS
Total:                  65/65 PASS, 0 skipped
```

---

## Claims permitidos post-P3

El runtime safety G1 tiene latencia interna de reaccion medida para rutas
de fault individual validadas bajo inyeccion controlada.

Rutas directas, terminales y gobernadas preservan trazabilidad causal
produciendo tiempos de reaccion medibles bajo inyeccion controlada.

---

## Claims prohibidos post-P3

- hard real-time
- certified real-time
- robot physically recovers
- safe under all faults
- timing guaranteed under load
- faults simultaneos
- real hardware faults

---

## Evidencia

```
evidence/4J/P3_TIMING/raw/
  p3_timing_raw_stale_20260623_205340.csv
  p3_timing_raw_freeze_20260623_210340.csv
  p3_timing_raw_naninf_20260623_211141.csv
  p3_timing_raw_timestamp_20260623_212127.csv
  p3_timing_raw_fallen_direct_20260623_212707.csv
  p3_timing_raw_tx011_governed_20260623_215302.csv

evidence/4J/P3_TIMING/summaries/
  p3_timing_summary.md

evidence/4J/P3_TIMING/logs/
  p3_env_stale_2026-06-23T205340604143.txt
  p3_env_freeze_2026-06-23T210340128377.txt
  p3_env_naninf_2026-06-23T211141105252.txt
  p3_env_timestamp_2026-06-23T212127558877.txt
  p3_env_fallen_direct_2026-06-23T212707746103.txt
  p3_env_tx011_governed_2026-06-23T215302403122.txt
```

---

*G1 Deterministic Safety Runtime — 4J Timing Traceability Report*
*Generado: 2026-06-23 | Harness commit: f9cbdcf*
*PM: ChatGPT | Implementador/Auditor: Claude | Operador: Jorge Padilla*
