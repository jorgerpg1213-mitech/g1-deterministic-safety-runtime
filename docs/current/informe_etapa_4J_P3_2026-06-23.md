# Informe de Sesión — Etapa 4J (P3)
## G1 Deterministic Safety Runtime
**Fecha:** 2026-06-23
**Estado al cierre:**
- **4J-P3 ✅ CERRADA** — Timing Traceability Report: 6 rutas medidas, evidencia commitada
- **DT-4J-001 🔲 ABIERTA** — full native traceability (sin cambios esta sesión)

**Roles:** PM: ChatGPT | Implementador/Auditor: Claude | Operador: Jorge Padilla

**Commits de sesión:**
- `edfef80` — `docs(4J-P2-A): add fault injection matrix, bootstrap v25, session informe` (housekeeping P2-A)
- `53c3b12` — `feat(4J-P3): add timing traceability matrix harness — P3-A0 approved`
- `f9cbdcf` — `fix(4J-P3): INTER_RUN_S=6s, NAME_SETTLE_S guard TOPO_UNRESOLVED — Clase H, aprobado PM`
- `9777103` — `feat(4J-P3): timing traceability report + evidence — P3 CERRADA`

**HEAD:** `9777103` — CI Build ✅ CI Audit ✅
**Repositorio:** `~/g1-deterministic-safety-runtime` | `origin/main` synced
**Contenedor:** `boring_noether` activo

---

## 0. Resumen Ejecutivo

Esta sesión ejecutó la microfase 4J-P3 — Timing Traceability Report — bajo el principio PM: **No timing claim without trace** / **same behavior as P2, now with time**.

Se midió la latencia interna del safety runtime para las 6 rutas validadas en 4J-P2. El harness `harness_4J_P3_timing_matrix.py` fue diseñado, aprobado por PM con dos rondas de ajustes, parcheado en campo por dos Clases H, y ejecutado contra todos los cases.

**Resultados:**

| Case | Route | N válidas | mean_ms | Limitación |
|---|---|---|---|---|
| STALE | R2 | 3 | 1005.696ms | MAX_AUTO_RETRIES=3 |
| FREEZE | R3 | 10 | 3.725ms | — |
| NANINF | R3 | 10 | 3.777ms | — |
| TIMESTAMP | R3 | 10 | 3.861ms | — |
| FALLEN_DIRECT | R2 | 3 | 1005.846ms | MAX_AUTO_RETRIES=3 |
| TX-011 governed | R1 | 1 | 6.130ms e2e | one-shot orchestrator |

**Hallazgos principales:**
- R3 terminal routes producen ~3.5–4.6ms de dispatch puro
- R2 direct routes incluyen `wait_for_primary_restore` (~1s) → ~1005ms total
- dispatch interno 4F-P5 de recovery_g1: ~0.8ms (medido en logs, no en harness)
- MAX_AUTO_RETRIES=3 limita STALE y FALLEN_DIRECT a N=3 por sesión
- One-shot orchestrator state machine limita TX-011 a N=1 por sesión

---

## 1. Apertura — Housekeeping P2-A

Al inicio se commitó el pendiente de P2-A:
- `4J_FAULT_INJECTION_MATRIX.md` — generado en sesión anterior, no estaba en disco (encontrado con `find`). Reconstruido desde evidencia del informe y commitado a `docs/audit/`.
- `chat_bootstrap_protocol_g1_pipeline_v25.md` y `informe_etapa_4J_P2A_2026-06-23.md` — untracked en `docs/current/`, commitados.
- Harnesses sueltos en raíz (`harness_4J_P1B_focal.py`, `harness_4J_P2_direct_trace.py`) — ya no existían en disco (cleanup anterior).

**Commit:** `edfef80` — 3 files, 618 insertions.

---

## 2. Lectura del documento PM para P3

Documento leído: `4J-P3_Timing_Traceability_Report.pdf`

Principios extraídos:
- P3 mide timing, no comportamiento nuevo
- Reutiliza rutas validadas en P2
- event_id único por muestra
- t0 = harness publish timestamp immediately before publish (no DDS exacto)
- Separación R2/R3 vs R1 governed
- N=10 por ruta, p95 exploratorio
- docker restart como precondición del operador — no dentro del harness
- Si aparece acción incorrecta → detener P3, regresar a bugfix

---

## 3. Diseño del harness — P3-A0 (dos rondas de aprobación PM)

### Ronda 1 — RECHAZADO con 4 ajustes

PM requirió:
1. t0 nombrado como "harness publish timestamp immediately before publish"
2. tx011_governed: topology check verifica por nombre de nodo, no solo conteo
3. docker restart documentado como precondición del operador, no dentro del harness
4. p95_ms_exploratory en todos los outputs

### Ronda 2 — RECHAZADO con 5 fixes

PM requirió adicionalmente:
1. `rclpy.init()` una vez por case group — no por cada run
2. Direct/terminal topology check verifica nombre `recovery_g1`, no solo len==1
3. Para tx011_governed: documenta remap explícito (`--remap /safety_events:=/safety_events_null`)
4. CSV por case+timestamp — sin mezcla de runs anteriores
5. `_write_environment` al inicio (PRE-RUN) — no al final

### Implementación final aprobada

Verificada con AST:
- `rclpy.init()` exactamente en línea 602 (main)
- `rclpy.shutdown()` exactamente en línea 614 (finally de main)
- Ninguno en `_run_single()` (líneas 306–416)
- `TOPO_UNRESOLVED` guard presente
- `NAME_SETTLE_S` presente
- `p95_ms_exploratory` en stats, summary, tabla

**Commit:** `53c3b12` — 636 líneas

---

## 4. Ejecución P3-A — Direct / Terminal

### P3-A1 — STALE (primera corrida — parcial)

Primera corrida antes de patches reveló dos Clases H:

**Clase H-1 — `_NODE_NAME_UNKNOWN_`:** runs 2–7 fallaron con TOPO_FAIL. Causa: DDS propagó subscriber (count=1 ✅) pero no resolvió nombre de nodo a tiempo. El subscriber ERA recovery_g1 — faltaba espera de metadatos DDS.

**Clase H-2 — Cooldown:** run 9 timeout. `INTER_RUN_S=3.0s < COOLDOWN=5.0s`. El run anterior saturó el cooldown.

Datos válidos primera corrida: runs 1, 8, 10 PASS.

### Patches aplicados (aprobados PM explícitamente)

**Patch 1:** `INTER_RUN_S = 3.0 → 6.0` — respetar COOLDOWN=5.0s

**Patch 2:** Fase 2 warmup `NAME_SETTLE_S=3.0s` — esperar resolución DDS de node names. Guard PM: si sigue `_NODE_NAME_UNKNOWN_` tras NAME_SETTLE_S → `TOPO_UNRESOLVED`, no publicar.

```python
NAME_SETTLE_S = 3.0
t_settle = time.monotonic()
while time.monotonic() - t_settle < NAME_SETTLE_S:
    rclpy.spin_once(node, timeout_sec=0.1)
    infos = node.get_subscriptions_info_by_topic('/safety_events')
    names = [i.node_name for i in infos]
    if infos and all('UNKNOWN' not in n for n in names):
        break
# Guard: si sigue UNKNOWN → TOPO_UNRESOLVED
```

**Commit:** `f9cbdcf`

### P3-A1 — STALE (segunda corrida — válida)

```
Run 1/10  PASS — latency=1005.890ms
Run 2/10  PASS — latency=1005.685ms
Run 3/10  PASS — latency=1005.513ms
Run 4/10  FAIL — request_operator_intervention (MAX_AUTO_RETRIES=3 agotado)
Runs 5-10 FAIL — escalación continúa
```

**Diagnóstico:** No es Clase B. `MAX_AUTO_RETRIES=3` por diseño. Runs 4+ cambian condición experimental de auto-recovery timing a política de escalación. Científicamente diferente — excluidos.

**Decisión PM:** N=3 válidas. Misma regla aplicará a FALLEN_DIRECT.

**Stats N=3:** min=1005.513 · mean=1005.696 · max=1005.890ms

### P3-A2 — FREEZE

10/10 PASS. Sin acumulación — R3 terminal bypass cooldown/retry (TERMINAL_MANUAL_RULE_IDS).

```
min=3.527  mean=3.725  max=3.957  p95_exp=3.811 ms
```

Logs T1 confirmaron: `terminal=True (bypass cooldown/retry)` en los 10 runs. dispatch interno 4F-P5: ~0.73–0.95ms.

### P3-A3 — NANINF

10/10 PASS.

```
min=3.485  mean=3.777  max=4.212  p95_exp=4.018 ms
```

### P3-A4 — TIMESTAMP

10/10 PASS.

```
min=3.596  mean=3.861  max=4.628  p95_exp=4.012 ms
```

Outlier 4.628ms en run 2 — jitter DDS normal, dentro de rango esperado.

### P3-A5 — FALLEN_DIRECT

Mismo patrón que STALE:
```
Run 1-3  PASS — ~1005ms
Run 4+   FAIL — MAX_AUTO_RETRIES=3 agotado → escalación
```

**Decisión PM:** misma regla que STALE — N=3, aprobado explícitamente.

**Stats N=3:** min=1005.620 · mean=1005.846 · max=1006.206ms

---

## 5. Ejecución P3-B — Governed

### P3-B1 — TX-011 governed

Topología gobernada requerida:
- Terminal 1: `safety_orchestrator_g1`
- Terminal 2: `recovery_g1 --ros-args --remap /safety_events:=/safety_events_null`

```
Run 1  PASS — T_event_to_action=3.503ms · T_action_to_recovery=2.627ms · T_e2e=6.130ms
Run 2+ FAIL-TIMEOUT_ACTION — orchestrator en STABILITY_RISK/R3 → TX-011 no elegible
```

**Diagnóstico:** No es Clase B. La máquina de estados del orchestrator hace TX-011 desde `(SAFE, NONE)`. Después de Run 1 queda en `(STABILITY_RISK, R3)`. Comportamiento correcto.

**Decisión PM:** N=1 válida por sesión. Runs 2+ excluidos — cambian condición experimental.

**Métricas Run 1:**
```
T_event_to_action_ms:    3.503
T_action_to_recovery_ms: 2.627
T_event_to_recovery_ms:  6.130
EVENT_ID: 4JP3-TX011_GOVERNED-001-1f6a
```

---

## 6. Métricas duales — rutas R2

Las ~1005ms de STALE y FALLEN_DIRECT incluyen `wait_for_primary_restore` (~1s simulada). No es dispatch puro.

| Métrica | Valor | Fuente |
|---|---|---|
| t0 → RecoveryEvent (harness) | ~1005ms | harness timing |
| t1 → t2 dispatch interno recovery_g1 | ~0.86ms | logs 4F-P5 |

Estas dos métricas miden cosas distintas y no deben mezclarse en claims de paper.

---

## 7. Regresión

```
safety_orchestrator_g1: 63/63 PASS
test_g1_safety_layer:    2/2 PASS
Total:                  65/65 PASS, 0 skipped
CI Build: ✅  CI Audit: ✅
```

---

## 8. Estado de la VM al Cierre

```
Repo activo    → ~/g1-deterministic-safety-runtime (main, origin synced)
HEAD           → 9777103 (post-4J-P3)
Contenedor     → boring_noether activo
Tests          → 65/65 PASS, 0 skipped
CI             → Build ✅ Audit ✅
```

**Archivos nuevos en sesión:**
```
sim_runtime/4J/harness_4J_P3_timing_matrix.py
docs/audit/4J_TIMING_TRACEABILITY_REPORT.md
evidence/4J/P3_TIMING/raw/      (6 CSVs por case)
evidence/4J/P3_TIMING/summaries/p3_timing_summary.md
evidence/4J/P3_TIMING/logs/     (7 environment files PRE-RUN)
```

---

## 9. Deuda Técnica al Cierre

| ID | Deuda | Prioridad | Estado |
|---|---|---|---|
| DT-4E-006 | Control PD diferido | Alta | Abierta |
| DT-4F-001 | Thresholds pragmáticos | Media | Abierta |
| DT-4F-002 | TX-006b/c sin test explícito | Media | Abierta |
| DT-4F-004 | FREEZE IMU falso positivo potencial | Media | Abierta |
| DT-4G-002 | t1→t2 UUID paper-grade | Media | Parcial — P1-B |
| DT-4G-004B | Zombies `<defunct>` por PID1/reaper | Baja | Abierta, no bloqueante |
| **DT-4J-001** | **Full native traceability** | **Media** | **Abierta — sin cambios** |

---

## 10. Anti-Patterns Nuevos

Ningún nuevo número registrado formalmente. Hallazgo documentado en harness:

**`_NODE_NAME_UNKNOWN_`:** DDS propaga subscriber (count>0) antes de resolver metadatos de participante. Requiere fase 2 de warmup (`NAME_SETTLE_S=3.0s`) antes de `_check_topology()`. Guard: si persiste → `TOPO_UNRESOLVED`, no publicar.

---

## 11. Limitaciones declaradas en P3

- STALE N=3: MAX_AUTO_RETRIES=3 por diseño del runtime
- FALLEN_DIRECT N=3: misma política
- TX-011 N=1: one-shot orchestrator state machine
- p95_ms_exploratory: N pequeño, no estadístico fuerte
- t0 no es DDS emission exacto — es timestamp del harness
- ~1005ms en R2 incluye wait_for_primary_restore (~1s) — no es dispatch puro

---

## LLAVE DEL SIGUIENTE CHAT

```
4J-P3 ✅ CERRADA — Timing Traceability Report

Rutas medidas:
  STALE         R2  N=3   min=1005.513 mean=1005.696 max=1005.890 ms (lim: MAX_AUTO_RETRIES=3)
  FREEZE        R3  N=10  min=3.527    mean=3.725    max=3.957    ms
  NANINF        R3  N=10  min=3.485    mean=3.777    max=4.212    ms
  TIMESTAMP     R3  N=10  min=3.596    mean=3.861    max=4.628    ms
  FALLEN_DIRECT R2  N=3   min=1005.620 mean=1005.846 max=1006.206 ms (lim: MAX_AUTO_RETRIES=3)
  TX-011        R1  N=1   T_e2a=3.503 T_a2r=2.627   T_e2e=6.130 ms (lim: one-shot orchestrator)

Harness: sim_runtime/4J/harness_4J_P3_timing_matrix.py (INTER_RUN_S=6.0, NAME_SETTLE_S=3.0)
Reporte: docs/audit/4J_TIMING_TRACEABILITY_REPORT.md
Evidencia: evidence/4J/P3_TIMING/

Commits: edfef80 → 53c3b12 → f9cbdcf → 9777103
HEAD: 9777103 | CI Build ✅ CI Audit ✅ | 65/65 PASS 0 skipped

PRÓXIMO: 4J-P4 — Threshold / False-Positive Characterization
  Leer documento PM para P4 antes de diseñar nada
  No tocar runtime
```

---

*G1 Deterministic Safety Runtime — Informe Cierre 4J-P3*
*Generado: 2026-06-23*
*PM: ChatGPT | Implementador/Auditor: Claude | Operador: Jorge Padilla*
*Repositorio: github.com/jorgerpg1213-mitech/g1-deterministic-safety-runtime*
