# Informe de Sesión — Etapa 4J (P2-A)
## G1 Deterministic Safety Runtime
**Fecha:** 2026-06-23
**Estado al cierre:**
- **4J-P2-A ✅ CERRADA** — Individual Fault Injection Matrix: STALE/FREEZE/NANINF/TIMESTAMP/FALLEN PASS, RATE declared limitation, TX-011 citado
- **Anti-pattern #78** registrado: `colcon test` sin `source install/setup.bash`
- **DT-4J-001 🔲 ABIERTA** — full native traceability (sin cambios esta sesión)

**Roles:** PM: ChatGPT | Implementador/Auditor: Claude | Operador: Jorge Padilla

**Commits de sesión:**
- `3414fe2` — `feat(4J-P2-A): individual fault injection matrix — STALE/FREEZE/NANINF/TIMESTAMP/FALLEN PASS, RATE declared limitation`

**HEAD:** `3414fe2` — CI Build ✅ CI Audit ✅
**Repositorio:** `~/g1-deterministic-safety-runtime` | `origin/main` synced
**Contenedor:** `boring_noether` activo

---

## 0. Resumen Ejecutivo

Esta sesión ejecutó la microfase 4J-P2-A — Extended Fault Injection Matrix — bajo el principio PM: **one fault · one route · one trace · one verdict**.

Se validaron los 7 fault rows definidos en el documento PM (`4J-P2_Extended_Fault_Injection_Matrix.pdf`). Cuatro filas terminaron PASS con evidencia trazable (FREEZE, NANINF, TIMESTAMP, FALLEN), una fue citada de evidencia previa (TX-011/STALE), una declarada limitation (RATE), y una fue citada de P0-B+P1-B (governed TX-011).

**Hallazgo principal de la sesión:** el harness STALE existente fallaba por state contamination del nodo con 17 horas de uptime — no por bug de runtime. Docker restart resolvió. Esta fue la señal para establecer anti-pattern #78.

**Clase H registrada en P2-A2:** el string esperado en el harness FREEZE era `operator_intervention` — el runtime publica `request_operator_intervention`. Corregido con `sed` directo en el contenedor, sin tocar runtime.

**Fix de PM en P2-A5:** `risk_level=STABILITY_RISK + restriction_level=R3` hubiera activado `_recovery_allowed()` bloqueando recovery antes de probar el fallback. Corregido a `CAUTION + R2` para aislar la ruta directa.

**Método:** auditoría de código real antes de cada harness, aprobación PM antes de correr, `ast.parse` en todos los archivos nuevos, `docker restart` entre filas formales, regresión 65/65 al cierre.

---

## 1. Contexto — Documento PM leído al inicio

### 1.1 `4J-P2_Extended_Fault_Injection_Matrix.pdf`

Documento PM completo para 4J-P2. Define:
- Principio rector: one fault · one route · one trace · one verdict
- 7 fault rows (P2-A1 → P2-A7)
- Tres rutas bajo prueba: R1 (governed), R2 (direct), R3 (terminal manual)
- Nivel de evidencia E3 — focal harness / individual fault
- Orden de ejecución: P2-A0 → P2-A1 → ... → P2-A8
- FAIL classes: H (harness), B (runtime bug), P (policy undefined), S (scope mismatch)
- Fix policy: solo si bug localizado, patch mínimo, regresión obligatoria
- Artifact structure: `docs/audit/4J_FAULT_INJECTION_MATRIX.md` + `evidence/4J/P2_FAULT_INJECTION/`
- Allowed claims post-P2: routing individual por ruta y tipo, trazabilidad mínima
- Forbidden claims: simultaneous faults, sequences, timing, physical recovery, certification

---

## 2. Apertura de sesión — Bootstrap y estado inicial

Al inicio se detectó que el harness STALE existente (`harness_4J_P2_direct_trace.py`) fallaba con timeout. Auditoría:

- `timestamp` en `SafetyEvent.msg` ✅ confirmado con `ros2 interface show`
- `_recovery_allowed()` arranca en `SAFE/NONE` ✅ — no bloqueante
- `_dispatch_recovery()` rama STALE ✅ — lógica correcta
- **Root cause:** nodo `recovery_g1` con 17 horas de uptime — retry counters saturados

**Resolución PM:** docker restart antes de correr. Tras reinicio, STALE PASS inmediato.

**Anti-pattern #78:** correr harness contra nodo con uptime largo sin verificar estado limpio de retry counters.

---

## 3. Matriz P2-A — Ejecución por fila

### P2-A0 — Matrix doc + harness template
Ejecutado post-hoc (se invirtió el orden respecto al plan PM). Documento `4J_FAULT_INJECTION_MATRIX.md` generado como skeleton con los 7 contratos de fila. Pendiente: commit a `docs/audit/` al inicio de próxima sesión.

### P2-A1 — STALE
- **Ruta:** R2 Direct
- **Harness:** `harness_4J_P2_direct_trace.py` (prep-phase, citado como P2-A1)
- **FIXED_ID:** `4JP2-DIRECT-001`
- **Topología:** 1 subscriber en `/safety_events` = `recovery_g1`
- **Resultado PASS:**
```
action_name:    wait_for_primary_restore  ✅
recovery_type:  REC-AUTO                  ✅
parent_event_id: 4JP2-DIRECT-001         ✅
```
- **Nota:** evidencia de prep-phase citada como P2-A1. Commit `cf4e835`.

### P2-A2 — FREEZE
- **Ruta:** R3 Terminal Manual
- **Harness:** `harness_P2_A2_freeze.py` — nuevo
- **FIXED_ID:** `4JP2-A2-FREEZE-001`
- **Clase H registrada:** string esperado `operator_intervention` → runtime publica `request_operator_intervention`. Corregido con `sed` en contenedor.
- **Resultado PASS:**
```
action_name:    request_operator_intervention  ✅
recovery_type:  REC-MANUAL                     ✅
attempt_number: 1                              ✅
parent_event_id: 4JP2-A2-FREEZE-001           ✅
```

### P2-A3 — NANINF
- **Ruta:** R3 Terminal Manual
- **Harness:** `harness_P2_A3_naninf.py` — nuevo
- **FIXED_ID:** `4JP2-A3-NANINF-001`
- **Nota:** harness creado con `sed` desde FREEZE — requirió reescritura completa por contaminación cosmética de strings (docstring, logs, prints).
- **Resultado PASS:**
```
action_name:    request_operator_intervention  ✅
recovery_type:  REC-MANUAL                     ✅
attempt_number: 1                              ✅
parent_event_id: 4JP2-A3-NANINF-001           ✅
```

### P2-A4 — TIMESTAMP
- **Ruta:** R3 Terminal Manual
- **Harness:** `harness_P2_A4_timestamp.py` — nuevo, reescrito de cero
- **FIXED_ID:** `4JP2-A4-TIMESTAMP-001`
- **Resultado PASS:**
```
action_name:    request_operator_intervention  ✅
recovery_type:  REC-MANUAL                     ✅
attempt_number: 1                              ✅
parent_event_id: 4JP2-A4-TIMESTAMP-001        ✅
```

### P2-A5 — Fallen direct fallback
- **Ruta:** R2 Direct fallback
- **Harness:** `harness_P2_A5_fallen_direct.py` — nuevo
- **FIXED_ID:** `4JP2-A5-FALLEN-001`
- **Fix PM pre-ejecución:** `risk_level=STABILITY_RISK + restriction_level=R3` activaba `_recovery_allowed()` bloqueando recovery. Cambiado a `CAUTION + R2` para aislar ruta directa.
- **Resultado PASS:**
```
action_name:    wait_for_primary_restore  ✅
recovery_type:  REC-AUTO                  ✅
parent_event_id: 4JP2-A5-FALLEN-001      ✅
```
- **Limitación declarada:** weak fallback — no reclama recuperación física. Ruta primaria es R1/TX-011.

### P2-A6 — RATE
- **Auditoría:**
  - `watchdog_g1`: detecta RATE → emite `rule_id=4F-P2-RATE` ✅
  - `recovery_g1`: sin rama explícita para RATE — `grep` retorna vacío
  - Si cae al `else`: sería fallthrough a `request_operator_intervention`, no política definida
- **Veredicto:** DECLARED LIMITATION — detection-only. No harness de recovery. No claim de recovery.

### P2-A7 — Fallen governed TX-011
- **Ruta:** R1 Governed
- **Estado:** CITADO — no requiere nuevo experimento
- **Evidencia:** P0-B PASS (`cb3f777`) + P1-B traceability (`bbcc097`)
- **Cadena citada:** `SafetyEvent → SafetyAction TX-011 → RecoveryEvent stabilization_mode REC-AUTO`

---

## 4. Regresión

Primer intento falló con `collection failure` — `ModuleNotFoundError: No module named 'launch'`. Causa: `colcon test` ejecutado sin `source /ws/install/setup.bash`. Corregido. Segunda ejecución:

```
safety_orchestrator_g1: 63/63 PASS
test_g1_safety_layer:    2/2 PASS
Total:                  65 tests PASS, 0 skipped
CI Build: ✅  CI Audit: ✅
```

---

## 5. Estado de la VM al Cierre

```
Repo activo    → ~/g1-deterministic-safety-runtime (main, origin synced)
HEAD           → 3414fe2 (post-4J-P2-A)
Contenedor     → boring_noether activo
Tests          → 65/65 PASS, 0 skipped
CI             → Build ✅ Audit ✅
```

**Archivos nuevos en sesión:**
```
sim_runtime/4J/harness_P2_A2_freeze.py
sim_runtime/4J/harness_P2_A3_naninf.py
sim_runtime/4J/harness_P2_A4_timestamp.py
sim_runtime/4J/harness_P2_A5_fallen_direct.py
```

**Pendiente (no commiteado):**
```
4J_FAULT_INJECTION_MATRIX.md → commitar a docs/audit/ al inicio de P3
```

---

## 6. Deuda Técnica al Cierre

| ID | Deuda | Prioridad | Estado |
|---|---|---|---|
| DT-4E-006 | Control PD diferido | Alta | Abierta |
| DT-4F-001 | Thresholds pragmáticos | Media | Abierta |
| DT-4F-002 | TX-006b/c sin test explícito | Media | Abierta |
| DT-4F-004 | FREEZE IMU falso positivo potencial | Media | Abierta |
| DT-4G-002 | t1→t2 UUID paper-grade | Media | Parcial — P1-B |
| DT-4G-004B | Zombies `<defunct>` por PID1/reaper | Baja | Abierta, no bloqueante |
| **DT-4J-001** | **Full native traceability** | Media | **Abierta — P3** |

---

## 7. Evidencia de Validación

| Harness | Ruta | PASS/FAIL | Evidencia clave |
|---|---|---|---|
| `harness_4J_P2_direct_trace.py` | R2 direct — STALE | ✅ PASS | `parent_event_id=4JP2-DIRECT-001` |
| `harness_P2_A2_freeze.py` | R3 terminal — FREEZE | ✅ PASS | `REC-MANUAL attempt=1 parent_event_id=4JP2-A2-FREEZE-001` |
| `harness_P2_A3_naninf.py` | R3 terminal — NANINF | ✅ PASS | `REC-MANUAL attempt=1 parent_event_id=4JP2-A3-NANINF-001` |
| `harness_P2_A4_timestamp.py` | R3 terminal — TIMESTAMP | ✅ PASS | `REC-MANUAL attempt=1 parent_event_id=4JP2-A4-TIMESTAMP-001` |
| `harness_P2_A5_fallen_direct.py` | R2 direct — FALLEN | ✅ PASS | `REC-AUTO parent_event_id=4JP2-A5-FALLEN-001` |
| RATE | — | ✅ DECLARED LIMITATION | detection-only, sin política recovery |
| TX-011 governed | R1 governed | ✅ CITADO | P0-B + P1-B |

**Regresión:** 65/65 PASS.

---

## 8. Anti-Patterns Nuevos

| # | Anti-pattern | Corrección |
|---|---|---|
| **78** | **Correr harness contra nodo con uptime largo sin verificar retry state** | `docker restart` antes de cada fila formal |

---

## 9. Próximos Pasos

```
4J-P2-A  ✅ CERRADA
         Limitación: no simultaneous faults, no sequences, no timing, no physical recovery

Inicio 4J-P3:
  Commitar 4J_FAULT_INJECTION_MATRIX.md a docs/audit/
  Leer documento PM para P3 — Timing Traceability Report
  Auditar logs de latencia t1→t2 disponibles (4F-P5 en recovery_g1)
```

---

## LLAVE DEL SIGUIENTE CHAT

```
4J-P2-A ✅ CERRADA — Individual Fault Injection Matrix
  P2-A1 STALE:    wait_for_primary_restore REC-AUTO parent_event_id=4JP2-DIRECT-001     ✅
  P2-A2 FREEZE:   request_operator_intervention REC-MANUAL attempt=1                    ✅
  P2-A3 NANINF:   request_operator_intervention REC-MANUAL attempt=1                    ✅
  P2-A4 TIMESTAMP:request_operator_intervention REC-MANUAL attempt=1                    ✅
  P2-A5 FALLEN:   wait_for_primary_restore REC-AUTO parent_event_id=4JP2-A5-FALLEN-001 ✅
  P2-A6 RATE:     DECLARED LIMITATION — detection-only                                  ✅
  P2-A7 TX-011:   CITADO — P0-B + P1-B                                                 ✅
  Commit: 3414fe2

Anti-pattern #78: docker restart antes de cada fila formal
Clase H registrada: operator_intervention → request_operator_intervention (harness bug, no runtime)

Pendiente: commitar 4J_FAULT_INJECTION_MATRIX.md a docs/audit/
HEAD: 3414fe2 | CI Build ✅ CI Audit ✅ | 65/65 PASS 0 skipped

PRÓXIMO: 4J-P3 — Timing Traceability Report
  Leer documento PM para P3 antes de diseñar
  Auditar logs 4F-P5 LATENCY disponibles en recovery_g1
```

---

*G1 Deterministic Safety Runtime — Informe Cierre 4J-P2-A*
*Generado: 2026-06-23*
*PM: ChatGPT | Implementador/Auditor: Claude | Operador: Jorge Padilla*
*Repositorio: github.com/jorgerpg1213-mitech/g1-deterministic-safety-runtime*
