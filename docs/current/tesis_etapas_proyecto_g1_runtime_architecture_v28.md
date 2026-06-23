# Tesis de Etapas del Proyecto — Runtime Architecture para Humanoide G1
## Versión 28 — Actualizada 2026-06-23 (4J-P3 cerrada)

> **Nota de versión (v28):** cambios respecto a v27 —
> (1) **4J-P2-A CERRADA**: Extended Fault Injection Matrix. 7 fault rows. Commits `3414fe2` + housekeeping `edfef80`.
> (2) **4J-P3 CERRADA**: Timing Traceability Report. 6 rutas medidas. Harness `harness_4J_P3_timing_matrix.py`. Commits `53c3b12` + `f9cbdcf` + `9777103`.
> (3) Limitaciones documentadas: STALE/FALLEN_DIRECT N=3 (MAX_AUTO_RETRIES=3), TX-011 N=1 (one-shot orchestrator).
> (4) HEAD: `9777103` — CI Build ✅ CI Audit ✅ — 65/65 PASS 0 skipped.

---

## Etapa 1 — Infraestructura Base — ✅ Cerrada
## Etapa 2 — Disciplina Operacional — ✅ Cerrada
## Etapa 3 — Safety Runtime Architecture — ✅ Cerrada

### 3C — Level 4 Runtime Validation — ✅ Cerrada
65 tests total (63 orchestrator + 2 launch integration), CI green.
TX-001→TX-011 auditables en `docs/audit/TRANSITION_MATRIX_G1.md`.

---

## Etapa 4 — Simulación e Integración Runtime — 🔄 En progreso

### 4A–4H — ✅ Cerradas (ver v26 para detalles)

### Etapa 4I — Formalización — ✅ CERRADA

Entregables: `SAFETY_MODEL_G1.md`, `TRACEABILITY_MATRIX_G1.md`, `POLICY_CLARIFICATION_G1.md`. DT-4I-001 cerrada en 4J-P0.

---

### Etapa 4J — Paper Prep — 🔄 EN PROGRESO

#### 4J-P0 — Runtime Alignment / Cierre DT-4I-001 — ✅ CERRADA (2026-06-22)
(ver v27 para detalles)

#### 4J-P1 — Causal Traceability — ✅ CERRADA — minimum scope (2026-06-22)
(ver v27 para detalles)

#### 4J-P2-prep — Direct Path Traceability — ✅ CERRADA (2026-06-22)
(ver v27 para detalles)

---

#### 4J-P2-A — Extended Fault Injection Matrix — ✅ CERRADA (2026-06-23)

**Principio PM:** one fault · one route · one trace · one verdict

**Resultado — 7 fault rows:**

| ID | Fault | Ruta | Resultado |
|---|---|---|---|
| P2-A1 | STALE | R2 Direct | ✅ PASS — `wait_for_primary_restore REC-AUTO` |
| P2-A2 | FREEZE | R3 Terminal | ✅ PASS — `request_operator_intervention REC-MANUAL attempt=1` |
| P2-A3 | NANINF | R3 Terminal | ✅ PASS — `request_operator_intervention REC-MANUAL attempt=1` |
| P2-A4 | TIMESTAMP | R3 Terminal | ✅ PASS — `request_operator_intervention REC-MANUAL attempt=1` |
| P2-A5 | Fallen direct | R2 Direct fallback | ✅ PASS — `wait_for_primary_restore REC-AUTO` (CAUTION+R2) |
| P2-A6 | RATE | — | ✅ DECLARED LIMITATION — detection-only |
| P2-A7 | Fallen governed TX-011 | R1 Governed | ✅ CITADO — P0-B + P1-B |

Trazabilidad: `parent_event_id` en `RecoveryEvent.notes` para todas las rutas.
Artifact: `docs/audit/4J_FAULT_INJECTION_MATRIX.md`
Commit: `3414fe2`

---

#### 4J-P3 — Timing Traceability Report — ✅ CERRADA (2026-06-23)

**Principio PM:** No timing claim without trace / same behavior as P2, now with time.

**Harness:** `sim_runtime/4J/harness_4J_P3_timing_matrix.py`
- `rclpy.init()` una vez por case group
- `NAME_SETTLE_S=3.0s` fase 2 warmup (DDS node name resolution)
- `INTER_RUN_S=6.0s` (respeta COOLDOWN=5.0s)
- CSV por case+timestamp, environment PRE-RUN

**Resultados:**

| Case | Route | N válidas | mean_ms | Limitación |
|---|---|---|---|---|
| STALE | R2 | 3 | 1005.696 | MAX_AUTO_RETRIES=3 |
| FREEZE | R3 | 10 | 3.725 | — |
| NANINF | R3 | 10 | 3.777 | — |
| TIMESTAMP | R3 | 10 | 3.861 | — |
| FALLEN_DIRECT | R2 | 3 | 1005.846 | MAX_AUTO_RETRIES=3 |
| TX-011 governed | R1 | 1 | 6.130 (e2e) | one-shot orchestrator |

**Métricas duales R2:**
- Harness t0→RecoveryEvent: ~1005ms (incluye wait_for_primary_restore ~1s)
- dispatch interno 4F-P5: ~0.86ms
- No mezclar en paper.

**TX-011 desglose:**
- T_event_to_action: 3.503ms
- T_action_to_recovery: 2.627ms
- T_end_to_end: 6.130ms

**Limitaciones:**
- STALE/FALLEN_DIRECT N=3: MAX_AUTO_RETRIES=3 por diseño
- TX-011 N=1: one-shot orchestrator state machine
- p95_ms_exploratory — N pequeño, no estadístico fuerte

**Artifact:** `docs/audit/4J_TIMING_TRACEABILITY_REPORT.md`
**Evidencia:** `evidence/4J/P3_TIMING/`
**Commits:** `53c3b12` + `f9cbdcf` + `9777103`

---

#### 4J-P4 — Threshold / False-Positive Characterization — 🔲 PENDIENTE
#### 4J-P5 — Assurance Case + Paper Package — 🔲 PENDIENTE

### Etapa 5A — Isaac Lab — 🔒 Bloqueada (GPU ≥ RTX 4080)

---

## Deuda Técnica Activa

| ID | Deuda | Prioridad | Estado |
|---|---|---|---|
| DT-4E-001 | SAFETY_MODEL_G1.md ausente | Alta | ✅ CERRADA 4I-P1 |
| DT-4E-006 | Control PD diferido | Alta | Abierta |
| DT-4F-001 | Thresholds pragmáticos | Media | Abierta |
| DT-4F-002 | TX-006b/c sin test explícito | Media | Abierta |
| DT-4F-003 | TX-009 POLICY_GATED exacta | Baja | ✅ CERRADA 4I-P3 |
| DT-4F-004 | FREEZE IMU falso positivo potencial | Media | Abierta |
| DT-4G-002 | t1→t2 UUID paper-grade | Media | Parcial — 4J-P1 |
| DT-4G-004A | Teardown activo contenedor | — | ✅ CERRADA |
| DT-4G-004B | Zombies `<defunct>` por PID1/reaper | Baja | Abierta, no bloqueante |
| DT-4I-001 | Discrepancia TX-011 governed recovery | Alta | ✅ CERRADA 4J-P0 |
| **DT-4J-001** | **Full native traceability** | **Media** | **Abierta** |

---

## Anti-Patterns Clave (acumulados)

| # | Anti-pattern |
|---|---|
| 54 | Reconstruir docker run de memoria |
| 63 | No verificar sintaxis antes de copiar al contenedor |
| 66 | Diseñar TX desde texto de informe, no código real |
| 67 | Tocar runtime safety para que pase un test de CI |
| 68 | Test de estado inicial con launch completo |
| 70 | Corridas formales sin preflight limpio |
| 71 | N≥10 en loop sin limpiar contenedor |
| 72 | Editar archivos críticos con str.replace sin verificar encoding |
| 73 | Mezclar dos causas en un solo harness |
| 74 | Correr harness antes de que el subscriber esté activo |
| 75 | Ejecutar harness sin verificar topología exacta |
| 76 | Asumir `colcon test` tiene mismo entorno que import directo |
| 77 | Tomar `node._events[0]` sin filtrar por ID conocido |
| **78** | **Correr harness contra nodo con uptime largo sin verificar retry state** |

---

## Criterios de éxito (actualizados)

```
4H-P1      ✅  recovery inteligente por causa
4H-P2      ✅  policy hardening — bypass terminal causes
4I-P1      ✅  SAFETY_MODEL_G1.md
4I-P2      ✅  TRACEABILITY_MATRIX_G1.md
4I-P3      ✅  POLICY_CLARIFICATION_G1.md
4J-P0      ✅  DT-4I-001 cerrada — governed TX-011 autosuficiente
4J-P1      ✅  minimum causal traceability SafetyEvent→SafetyAction→RecoveryEvent
4J-P2-prep ✅  trazabilidad ruta directa habilitada
4J-P2-A    ✅  Extended Fault Injection Matrix — 7 fault rows
4J-P3      ✅  Timing Traceability Report — 6 rutas medidas
DT-4G-004B 🔲  reaper/PID1 boring_noether
DT-4J-001  🔲  full native traceability
4J-P4      🔲  Threshold / False-Positive Characterization
```

---

*G1 Deterministic Safety Runtime — Tesis de Etapas v28*
*Actualizado: 2026-06-23*
*3C ✅ | 4A–4I ✅ | 4J 🔄 (P0✅ P1✅ P2-prep✅ P2-A✅ P3✅) | 5A 🔒*
