# Informe de Sesión — Etapa 4J (P4-A / P4-B)
## G1 Deterministic Safety Runtime
**Fecha:** 2026-06-25
**Estado al cierre:**
- **4J-P4-A ✅ CERRADA** — Threshold Inventory: 20+ constantes extraídas, H1–H5 documentados
- **4J-P4-B ✅ CERRADA** — Negative Control: PASS — 0 critical SafetyEvents, 0 terminal RecoveryEvents, 60s
- **DT-4G-004B 🔲 ABIERTA** — residual nodes post-teardown (limitación conocida, no bloqueante)

**Roles:** PM: ChatGPT | Implementador/Auditor: Claude | Operador: Jorge Padilla

**Commits de sesión:**
- `654faff` — `docs: update README to 4J-P4-A — stage table, capabilities, latency, evidence map, debt`
- (hash confirmado en push) — `docs(4J-P4-A): threshold characterization inventory — P4-A complete`
- `04d3983` — `feat(4J-P4-B): negative control harness PASS — 0 critical SafetyEvents, 0 terminal RecoveryEvents, 60s observation, DT-4G-004B declared`

**HEAD:** `04d3983` — CI Build ✅ CI Audit ✅
**Repositorio:** `~/g1-deterministic-safety-runtime` | `origin/main` synced
**Contenedor:** `boring_noether` activo

---

## 0. Resumen Ejecutivo

Esta sesión ejecutó las microfases 4J-P4-A y 4J-P4-B — Threshold Inventory y Negative Control — bajo el principio PM: **No threshold claim without falsification** / **Same runtime, now characterize trigger boundaries**.

**P4-A** fue una auditoría de código puro: sin ejecutar runtime, sin cambiar nada. Se extrajeron 20+ constantes de los 4 nodos runtime con números de línea confirmados, se asignaron niveles de evidencia honestos (E0–E4), y se documentaron 5 hallazgos estructurales que no eran evidentes desde la documentación existente.

**P4-B** fue un experimento de control negativo: verificar que condición sana no genera SafetyEvents críticos. El harness requirió múltiples ciclos de revisión PM antes de ser aprobado para corrida — cada ciclo resolvió un problema metodológico real. El resultado final fue PASS limpio en 60s de observación formal.

**Resultado P4-B:**
- Topology check: 4/4 ✓ (`/g1/imu`, `/imu`, `/safety_events`, `/recovery_events`)
- Cleanliness gate: CLEAN
- Phase 3 observation (60s): completada
- critical_risk SafetyEvents: **0**
- terminal RecoveryEvents: **0**
- VERDICT: **PASS**

---

## 1. Apertura — Lectura documento PM para P4

Documento leído: `4J-P4_Threshold___False_Positive_Characterization.pdf`

Principios extraídos:
- P4 no es certificación ni optimización — es caracterización experimental
- Workstreams: P4-A (inventory) → P4-B (negative controls) → P4-C (positive controls) → P4-D (boundary sweep) → P4-E (false positive analysis) → P4-F (report/debt)
- Primer paso obligatorio: inventory-first, sin diseñar harnesses hasta tener tabla aprobada por PM
- Claims prohibidos: thresholds óptimos, cero falsos positivos, safety certificado

**Instrucción PM inicial:** `Open 4J-P4-A as inventory-first. Do not run sweeps. Bring table to PM before designing harnesses.`

---

## 2. P4-A — Threshold Inventory

### 2.1 Auditoría de código

Se auditaron los 4 archivos runtime principales mediante grep sistemático:

```
src/watchdog_g1/watchdog_g1/watchdog_g1.py
src/cross_consistency_observer/cross_consistency_observer/cross_consistency_observer.py
src/safety_orchestrator_g1/safety_orchestrator_g1/safety_orchestrator_g1.py
src/recovery_g1/recovery_g1/recovery_g1.py
```

Comandos usados: grep de constantes uppercase, sed de rangos de línea para lógica de detección, grep de comparadores numéricos y severity.

### 2.2 Tabla de inventario — resumen por familia

| Familia | Node | Constantes clave | Evidence Level |
|---|---|---|---|
| F1 — Observer abs_w | cross_consistency_observer | FALLEN_W_CRITICAL=0.80, FALLEN_W_WARN=0.85 | E3/E1 |
| F2 — Observer contacto | cross_consistency_observer | FALLEN_CONSECUTIVE_N=3, FRESH_MAX_AGE_S=0.5s | E3/E1 |
| F3 — Watchdog STALE | watchdog_g1 | STALE_TIMEOUT_S=1.0s, STALE_CRITICAL_S=3.0s, STARTUP_GRACE_S=15s | E4/E3/E1 |
| F4 — Watchdog FREEZE | watchdog_g1 | FREEZE_N=5, NO_FREEZE_TOPICS | E4 |
| F5 — Watchdog NANINF | watchdog_g1 | isnan/isinf (boolean) | E4 |
| F6 — Watchdog TIMESTAMP | watchdog_g1 | stamp < prev_stamp (boolean) | E4 |
| F7 — Watchdog RATE | watchdog_g1 | MIN_RATE_HZ=3.0, RATE_WINDOW_S=2.0, RATE_WARMUP_N=5 | E2/E1 |
| Orchestrator routing | safety_orchestrator_g1 | ARBITRATION_PENDING_TIMEOUT_S=5.0s | E1 |
| Recovery R2/R3 | recovery_g1 | MAX_AUTO_RETRIES=3, RETRY_COOLDOWN_S=5.0s, TERMINAL_MANUAL_RULE_IDS, WAIT_FOR_PRIMARY_MAX_S=30s | E4/E3 |

### 2.3 Hallazgos estructurales H1–H5

**H1 — WARN e INFO del observer nunca publican SafetyEvent.**
`_publish_fallen_safety_event` se llama únicamente cuando `severity == 'CRITICAL'` AND `_fallen_consecutive >= 3`. WARN e INFO solo resetean el contador. El claim de severidad multi-nivel es interno únicamente.

**H2 — FALLEN_CONSECUTIVE_N=3 actúa como gate de debounce exclusivo de CRITICAL.**
Un solo frame con `abs_w < 0.80` no dispara SafetyEvent. Se requieren 3 frames frescos consecutivos con `FRESH_MAX_AGE_S=0.5s` cada uno.

**H3 — Observer emite `risk_level='STABILITY_RISK'` + `restriction_level='NONE'` hardcodeados.**
La severidad interna (WARN/CRITICAL) no se refleja en los campos del mensaje — aparece solo en `notes`. El routing downstream depende del `risk_level` del mensaje, no de la severidad de detección interna.

**H4 — STALE tiene dos caminos de severidad con evidencia asimétrica.**
`CRITICAL_STALE_TOPICS` → CRITICAL inmediato (E4). Tópicos no-críticos: WARN → CRITICAL si `dur >= 3s` (E3 — escalation path no fue aislada experimentalmente).

**H5 — WAIT_FOR_PRIMARY_MAX_S=30s nunca fue alcanzado experimentalmente.**
P3 midió ~1005ms en R2. El techo de 30s es claim E1 (código solamente).

### 2.4 Cierre P4-A

PM aprobó tabla. Entregable commitado: `docs/audit/4J_THRESHOLD_CHARACTERIZATION.md`

DT-4F-001 actualizada a `partially characterized`. DT-4F-004 permanece abierta — negative control (P4-B) requerido.

---

## 3. P4-B — Negative Control

### 3.1 Principio PM

`P4-B: 0 CRITICAL SafetyEvents, 0 terminal RecoveryEvents, 0 request_operator_intervention en ventana de observación formal.`

### 3.2 Diseño del harness — ciclos de aprobación PM

El harness requirió múltiples iteraciones antes de ser aprobado. Problemas bloqueantes resueltos en orden:

**Ciclo 1 — Diseño inicial rechazado:**
- Sin topology check → riesgo de falso PASS si runtime no está suscrito
- base_pose congelado → FREEZE artificial en `/g1/base_pose`
- Detección terminal incompleta (solo `notes`, no `msg.action_name`)
- CRITICAL aproximado sin declarar (no hay campo `severity` nativo en SafetyEvent)
- QoS no verificado

**Ciclo 2 — Logger bug (ValueError):**
`log = self.get_logger().error if is_crit else self.get_logger().warn` → ROS2 no permite cambiar severity entre llamadas al mismo logger. Fix: if/else explícito. Patch con Python assertions (PM rechazó sed por líneas — frágil si líneas se desplazan).

**Ciclo 3 — Campo incorrecto en RecoveryEvent:**
`msg.action` no existe. Campo real: `msg.action_name` (confirmado en `g1_msgs/msg/RecoveryEvent.msg`).

**Ciclo 4 — TOPO_FAIL /g1/imu:**
Se requirió `>=2` subscribers en `/g1/imu` (watchdog + observer). Pero `cross_consistency_observer` suscribe a `/imu`, no a `/g1/imu`. Fix: agregar publisher `/imu` (mismo mensaje) + topology check para `/imu`. Requiere `TOPO_MIN_SUBS['/g1/imu']=1, TOPO_MIN_SUBS['/imu']=1`.

**Ciclo 5 — Contaminación de estado del orchestrator:**
Watchdog disparaba STALE CRITICAL durante grace period (DDS no conectado a tiempo). Orchestrator quedaba en STABILITY_RISK. `clear_observation()` limpiaba lista del harness pero NO el estado interno del orchestrator. Phase 3 heredaba estado degradado → 60 eventos STABILITY_RISK → FAIL falso.

Fix aprobado (A+B):
- **Fix B:** `SETTLE_S=8` en `run_p4b.sh` (más tiempo para DDS antes de que watchdog evalúe)
- **Fix A:** Gate de limpieza antes de Phase 3 — si hay STABILITY_RISK en ventana de 5s → `STARTUP_CONTAMINATED` + abort

**Ciclo 6 — Contradicción matemática en run_p4b.sh:**
`SETTLE_S=10` + guard `ELAPSED >= 10` → script se autoboicotea. Fix: `SETTLE_S=8`, guard `ELAPSED >= 12`.

**Ciclo 7 — Jitter demasiado pequeño:**
`j = tick * 0.0001` → valores casi idénticos en los primeros ticks. Watchdog aún detectaba FREEZE. PM especificó jitter modular explícito:
- IMU w: `0.995 + 0.001 * (tick % 4)`
- IMU x: `0.001 * (tick % 3)`
- joint positions: `0.1 + 0.001 * ((tick + i) % 7)`
- base_pose z: `0.720 + 0.001 * (tick % 5)`

**Ciclo 8 — Verdict TOPO_FAIL podía ser sobreescrito por finally:**
`finally` recomputaba verdict como PASS si no había eventos críticos, incluso después de `TOPO_FAIL`. Fix: `verdict = 'UNSET'` antes del try; finally solo asigna PASS/FAIL si `verdict == 'UNSET'`.

### 3.3 Estructura final del harness

```
harness_4J_P4B_negative_control.py
  Preflight (en run_p4b.sh): ros2 node list vacío
  Topology check (NAME_SETTLE_S=3s):
    /g1/imu → watchdog_g1 ✓
    /imu → cross_consistency_observer ✓
    /safety_events → publishers ✓
    /recovery_events → publishers ✓
  Phase 1: STARTUP_GRACE_S=15s (publicando desde tick=0)
  Phase 2: POST_GRACE_SETTLE_S=5s
  Cleanliness gate: 5s — aborta con STARTUP_CONTAMINATED si runtime sucio
  Phase 3: OBSERVATION_WINDOW_S=60s (clear_observation al inicio)
  PASS: 0 critical_risk SafetyEvents + 0 terminal RecoveryEvents
```

Topics publicados por el harness:

| Topic | Valores | Hz |
|---|---|---|
| `/g1/imu` | w=0.995+0.001*(tick%4); mismo msg a /imu | 50 |
| `/imu` | mismo mensaje que /g1/imu | 50 |
| `/g1/contact/left` | in_contact=True, force=200.0 | 10 |
| `/g1/contact/right` | in_contact=True, force=200.0 | 10 |
| `/joint_states` | pos=0.1+0.001*((tick+i)%7) | 50 |
| `/g1/base_pose` | z=0.720+0.001*(tick%5), monotonic stamp | 50 |

### 3.4 run_p4b.sh — launcher controlado

Script de arranque único (1 terminal). Orden garantizado:
1. Preflight: `ros2 node list` vacío — aborta si nodos activos
2. Recovery + orchestrator + observer en background
3. Watchdog en background — inicia grace=15s
4. `sleep 8` — DDS settle
5. Time guard: aborta si `ELAPSED >= 12s` desde watchdog launch
6. Harness (foreground con tee) — publica desde tick=0
7. `trap cleanup EXIT` — pkill container-side + postflight node check

### 3.5 Corridas formales

| Run | Resultado | Causa |
|---|---|---|
| Run 1 | Abortado | ValueError logger severity |
| Run 2 | Abortado | TOPO_FAIL — msg.action no existe |
| Run 3 | Abortado | TOPO_FAIL — /g1/imu subs=1 < 2 requerido |
| Run 4 | FAIL (inválido) | Orchestrator contaminado — STABILITY_RISK en Phase 3 |
| Run 5 | STARTUP_CONTAMINATED | Gate funcionó — jitter aún insuficiente |
| Run 6 | STARTUP_CONTAMINATED | Jitter modular no transferido aún |
| **Run 7** | **PASS** ✅ | 0 críticos, 0 terminales, 60s completos |
| **Run 8** | **PASS** ✅ | Confirmación — git safe.directory arreglado |

**Run formal aceptado:** Run 8 (último)
```
run_id: P4B-20260625_223308-b162f596
verdict: PASS
topology_ok: True
critical_risk SafetyEvents: 0
caution_risk SafetyEvents: 0
terminal RecoveryEvents: 0
```

### 3.6 Limitaciones declaradas P4-B

- Jitter modular (step=0.001) — prueba "baseline activo sano", no robot inmóvil
- Frozen-sensor FREEZE false positive con IMU verdaderamente congelado → **diferido a P4-E**
- STARTUP_GRACE_S=15s excluido de ventana formal
- CRITICAL aproximado como `risk_level in {STABILITY_RISK, FAULT_CRITICAL}` — SafetyEvent no tiene campo severity nativo
- Postflight residual nodes — DT-4G-004B — no invalida resultado de detección

---

## 4. Regresión

```
65/65 tests PASS (sin cambios al runtime)
CI Build: ✅  CI Audit: ✅
```

---

## 5. Estado de la VM al Cierre

```
Repo activo    → ~/g1-deterministic-safety-runtime (main, origin synced)
HEAD           → 04d3983 (post-4J-P4-B)
Contenedor     → boring_noether activo
Tests          → 65/65 PASS, 0 skipped
CI             → Build ✅ Audit ✅
```

**Archivos nuevos en sesión:**
```
docs/audit/4J_THRESHOLD_CHARACTERIZATION.md
sim_runtime/4J/harness_4J_P4B_negative_control.py
sim_runtime/4J/run_p4b.sh
evidence/4J/P4_THRESHOLDS/negative_control/p4b_environment.txt
evidence/4J/P4_THRESHOLDS/negative_control/p4b_events.csv
evidence/4J/P4_THRESHOLDS/negative_control/p4b_recovery.csv
evidence/4J/P4_THRESHOLDS/negative_control/p4b_summary.md
README.md (actualizado)
```

---

## 6. Deuda Técnica al Cierre

| ID | Deuda | Prioridad | Estado |
|---|---|---|---|
| DT-4E-006 | Control PD diferido | Alta | Abierta |
| DT-4F-001 | Thresholds pragmáticos | Media | **Partially characterized — P4-A inventory complete; boundary sweep pendiente P4-D** |
| DT-4F-002 | TX-006b/c sin test explícito | Media | Abierta |
| DT-4F-004 | FREEZE IMU falso positivo potencial | Media | **Characterized (P4-A); negative control (P4-B) no lo prueba — diferido a P4-E** |
| DT-4G-002 | t1→t2 UUID paper-grade | Media | Parcial — 4J-P1 |
| DT-4G-004B | Zombies `<defunct>` por PID1/reaper | Baja | Abierta — postflight residual en P4-B confirma limitación |
| DT-4J-001 | Full native traceability | Media | Abierta |

---

## 7. Anti-Patterns Nuevos

| # | Anti-pattern | Corrección |
|---|---|---|
| 79 | Asignar método de logger dinámicamente en ROS2 (`log = self.get_logger().error if X else self.get_logger().warn`) | Usar if/else explícito — ROS2 no permite cambiar severity entre llamadas |
| 80 | Asumir campo de mensaje sin verificar el .msg file | Siempre `cat g1_msgs/msg/RecoveryEvent.msg` antes de usar `msg.field` |
| 81 | `kill $PID` asume que mata procesos dentro del contenedor | `docker exec container bash -c "pkill -f 'ros2 launch'"` para cleanup real |
| 82 | `clear_observation()` limpia lista del harness pero no el estado del runtime | Gate de limpieza pre-Phase-3 necesario para detectar orchestrator contaminado |
| 83 | Publicar solo `/g1/imu` asumiendo que observer también lo recibe | Verificar suscripciones reales — observer suscribe a `/imu`, watchdog a `/g1/imu` |

---

## 8. Limitaciones declaradas en sesión

- P4-B prueba baseline activo con jitter modular — no robot inmóvil
- FREEZE false positive con IMU frozen → P4-E (no resuelto en P4-B)
- Postflight residual nodes → DT-4G-004B → mitigation: `docker restart` antes de cada batería formal
- CRITICAL aproximado como risk_level (no hay campo severity nativo en SafetyEvent)

---

## LLAVE DEL SIGUIENTE CHAT

```
4J-P4-A ✅ CERRADA — Threshold Inventory
  20+ constantes extraídas. H1–H5 documentados.
  Artifact: docs/audit/4J_THRESHOLD_CHARACTERIZATION.md

4J-P4-B ✅ CERRADA — Negative Control PASS
  topology OK · cleanliness gate CLEAN · 60s observation
  0 critical SafetyEvents · 0 terminal RecoveryEvents
  Limitación: postflight residual → DT-4G-004B
  Harness: sim_runtime/4J/harness_4J_P4B_negative_control.py
  Launcher: sim_runtime/4J/run_p4b.sh
  Evidencia: evidence/4J/P4_THRESHOLDS/negative_control/

HEAD: 04d3983 | CI Build ✅ CI Audit ✅ | 65/65 PASS

PRÓXIMO: 4J-P4-C — Positive Controls
  Leer documento PM para P4-C antes de diseñar nada
  No tocar runtime · No cambiar thresholds
  Diseñar harness → PM approval → ejecutar
  
  Recordar topología IMU dual:
    watchdog_g1 suscribe /g1/imu
    cross_consistency_observer suscribe /imu
    Harnesses deben publicar en AMBOS topics
    
  DT-4G-004B activa: docker restart antes de cada batería formal
```

---

*G1 Deterministic Safety Runtime — Informe Cierre 4J-P4-A / P4-B*
*Generado: 2026-06-25*
*PM: ChatGPT | Implementador/Auditor: Claude | Operador: Jorge Padilla*
*Repositorio: github.com/jorgerpg1213-mitech/g1-deterministic-safety-runtime*
