# 4J Fault Injection Matrix
## G1 Deterministic Safety Runtime — Microfase 4J-P2-A

**Estado:** CERRADA — 2026-06-23
**Commit de referencia:** 3414fe2
**Principio rector:** one fault · one route · one trace · one verdict
**Nivel de evidencia:** E3 — focal harness / individual fault

---

## Resumen ejecutivo

| ID | Fault | Ruta | Acción esperada | Resultado |
|---|---|---|---|---|
| P2-A1 | STALE | R2 Direct | `wait_for_primary_restore` | PASS |
| P2-A2 | FREEZE | R3 Terminal | `request_operator_intervention` | PASS |
| P2-A3 | NANINF | R3 Terminal | `request_operator_intervention` | PASS |
| P2-A4 | TIMESTAMP | R3 Terminal | `request_operator_intervention` | PASS |
| P2-A5 | Fallen direct fallback | R2 Direct fallback | `wait_for_primary_restore` | PASS (weak fallback) |
| P2-A6 | RATE | — | — | DECLARED LIMITATION |
| P2-A7 | Fallen governed TX-011 | R1 Governed | `stabilization_mode` | CITADO |

Regresion: 65/65 PASS — 0 skipped — CI Build OK CI Audit OK

---

## Contratos de fila

### P2-A1 — STALE (R2 Direct)

- **FIXED_ID:** `4JP2-DIRECT-001`
- **rule_id:** `4F-P2-STALE`
- **Harness:** `sim_runtime/4J/harness_4J_P2_direct_trace.py`
- **Parametros:** risk_level=CAUTION, restriction_level=R2 (default)
- **Observables requeridos:**
  - action_name = wait_for_primary_restore
  - recovery_type = REC-AUTO
  - parent_event_id = 4JP2-DIRECT-001
- **Resultado:** PASS
- **Evidencia:** commit cf4e835 (prep-phase, citado como P2-A1)
- **Nota:** state contamination (17h uptime) causo timeout silencioso inicial.
  Root cause: retry counters saturados — no bug de runtime. Docker restart resolvio.
  Anti-pattern #78 registrado.

---

### P2-A2 — FREEZE (R3 Terminal Manual)

- **FIXED_ID:** `4JP2-A2-FREEZE-001`
- **rule_id:** `4F-P2-FREEZE`
- **Harness:** `sim_runtime/4J/harness_P2_A2_freeze.py`
- **Observables requeridos:**
  - action_name = request_operator_intervention
  - recovery_type = REC-MANUAL
  - attempt_number = 1
  - parent_event_id = 4JP2-A2-FREEZE-001
- **Resultado:** PASS
- **Clase H registrada:** harness esperaba string "operator_intervention" —
  runtime publica "request_operator_intervention". Fix: sed en harness.
  No es bug de runtime.

---

### P2-A3 — NANINF (R3 Terminal Manual)

- **FIXED_ID:** `4JP2-A3-NANINF-001`
- **rule_id:** `4F-P2-NANINF`
- **Harness:** `sim_runtime/4J/harness_P2_A3_naninf.py`
- **Observables requeridos:**
  - action_name = request_operator_intervention
  - recovery_type = REC-MANUAL
  - attempt_number = 1
  - parent_event_id = 4JP2-A3-NANINF-001
- **Resultado:** PASS

---

### P2-A4 — TIMESTAMP (R3 Terminal Manual)

- **FIXED_ID:** `4JP2-A4-TIMESTAMP-001`
- **rule_id:** `4F-P2-TIMESTAMP`
- **Harness:** `sim_runtime/4J/harness_P2_A4_timestamp.py`
- **Observables requeridos:**
  - action_name = request_operator_intervention
  - recovery_type = REC-MANUAL
  - attempt_number = 1
  - parent_event_id = 4JP2-A4-TIMESTAMP-001
- **Resultado:** PASS

---

### P2-A5 — Fallen direct fallback (R2 Direct fallback)

- **FIXED_ID:** `4JP2-A5-FALLEN-001`
- **Harness:** `sim_runtime/4J/harness_P2_A5_fallen_direct.py`
- **Parametros:** risk_level=CAUTION, restriction_level=R2
- **Observables requeridos:**
  - action_name = wait_for_primary_restore
  - recovery_type = REC-AUTO
  - parent_event_id = 4JP2-A5-FALLEN-001
- **Resultado:** PASS — weak fallback declarado
- **Fix PM pre-ejecucion:** STABILITY_RISK + R3 activaba _recovery_allowed()
  bloqueando recovery antes de probar fallback. Corregido a CAUTION + R2
  para aislar ruta directa.
- **Limitacion:** ruta primaria para fallen es R1/TX-011. No reclama
  recuperacion fisica.

---

### P2-A6 — RATE

- **rule_id:** `4F-P2-RATE`
- **Deteccion:** watchdog_g1 detecta y emite evento RATE (confirmado con grep)
- **Recovery:** recovery_g1 sin rama explicita para RATE
  Si cae al else: fallthrough a request_operator_intervention — sin politica definida
- **Resultado:** DECLARED LIMITATION — detection-only
  Sin harness de recovery. Sin claim de recovery para RATE.

---

### P2-A7 — Fallen governed TX-011 (R1 Governed)

- **Ruta:** R1 Governed via safety_orchestrator_g1
- **Cadena:** SafetyEvent → SafetyAction TX-011 → RecoveryEvent stabilization_mode REC-AUTO
- **Resultado:** CITADO
- **Evidencia:** P0-B (commit cb3f777) + P1-B traceability (commit bbcc097)

---

## Limitaciones explicitas de P2-A

- Sin faults simultaneos
- Sin secuencias de faults
- Sin timing bounds (pertenece a P3)
- Sin recuperacion fisica
- Sin certificacion safety

---

## Claims permitidos post-P2-A

El runtime safety G1 produce la accion correcta ante cada fault individual
validado, con trazabilidad causal minima via parent_event_id.

## Claims prohibidos post-P2-A

- timing bounds de ninguna ruta
- comportamiento ante faults simultaneos
- recuperacion fisica del robot
- certificacion de ninguna clase

---

*G1 Deterministic Safety Runtime — 4J Fault Injection Matrix*
*Generado: 2026-06-23 | Commit base: 3414fe2*
*PM: ChatGPT | Implementador/Auditor: Claude | Operador: Jorge Padilla*
