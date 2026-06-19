# Informe de Sesión — Etapa 4G (P3-A → P5)
## G1 Deterministic Safety Runtime
**Fecha:** 2026-06-18
**Estado al cierre:**
- **4G-P3-C ✅ CERRADA** — t0→t1 N=10, 100% PASS, media=2474.60ms
- **4G-P3-D ✅ CERRADA** — t1→t2 ruta gobernada N=10, 100% PASS, media=1.19ms
- **4G-P4-A ✅ CERRADA** — auditoría orchestrator→recovery, gap confirmado
- **4G-P4-B ✅ CERRADA** — diseño subscriber /safety_actions aprobado
- **4G-P4-C ✅ CERRADA** — piloto ruta gobernada PASS
- **4G-P4-D ✅ CERRADA** — N=10, 100% PASS, ruta gobernada orchestrator→recovery
- **4G-P5 ✅ CERRADA** — preflight bloqueante + post-teardown hygiene validados
- **DT-4G-003 ✅ CERRADA** — ruta gobernada orchestrator→recovery validada
- **DT-4G-004 🔲 ABIERTA** — teardown activo dentro del contenedor (nueva deuda)

**Roles:** PM: ChatGPT | Implementador/Auditor: Claude | Operador: Jorge Padilla
**Referencia previa:** `informe_etapa_4G_P2C_2026-06-18.md`
**Commits de sesión:**
- `dde0ea3` — docstring observer alineado con umbrales reales (no-safety)
- `5a925c8` — instrumentación t0→t1: fall_marker_v1 Isaac + observer_event_time_v1
- `64d7f06` — parser t0→t1 con error logging explícito
- `846d994` — fix pub_marker scope + t0 antes de inyección caída
- `0c25f38` — feat(4G-P3/P4/P5): parser p3b, ruta gobernada orchestrator→recovery, preflight bloqueante

**Repositorio:** `~/g1-deterministic-safety-runtime` | `origin/main` synced
**Contenedor:** `boring_noether` activo
**HEAD:** `0c25f38`

---

## 0. Resumen Ejecutivo

Esta sesión arrancó con 4G-P2-C ya cerrada (bootstrap v19) y ejecutó cinco microfases completas: P3 (instrumentación temporal t0→t1→t2), P4 (ruta gobernada orchestrator→recovery), y P5 (higiene operacional). Al cierre, el pipeline tiene trazabilidad temporal completa desde el evento físico hasta la acción de recovery, por ruta gobernada determinista, con laboratorio limpio garantizado por preflight bloqueante.

**Hallazgos principales:**
1. Docstring del observer tenía umbrales desactualizados (0.75 vs 0.80 real) — corregido sin tocar lógica.
2. pub_marker fuera de scope crasheaba Isaac post-trigger — fix de orden de inicialización.
3. Múltiples instancias de nodos contaminaban corridas — diagnosticado por P5, mitigado por preflight bloqueante.
4. Recovery tenía race condition estructural: actuaba por SafetyEvent directo (no determinista) — resuelto por ruta gobernada vía /safety_actions.
5. t1→t2 por ruta gobernada = media 1.19ms vs ruta directa = media ~1ms (ambas válidas, gobernada es determinista).

---

## 1. Errata Documental P2-C

### 1.1 Disparador real del piloto 20260618_081905
El informe P2-C describía implícitamente el disparo como relacionado con pérdida de contacto. Auditoría de código confirmó:

- Campo: `abs_w = abs(q.w)` del cuaternión IMU
- Umbral: `FALLEN_W_CRITICAL = 0.80`
- Piloto: `abs_w=0.713 < 0.80` → disparo por **rama CRITICAL de umbral de orientación**
- `L=False, R=True` = `one_lost` → condición concurrente, **no disparadora** (one_lost solo califica WARN)

**Redacción correcta:** el SafetyEvent fue emitido por la rama CRITICAL de `_evaluate_fallen_rule`, por umbral de orientación `abs(q.w)=0.713 < FALLEN_W_CRITICAL=0.80`. `one_lost` fue condición concurrente no causal.

### 1.2 Docstring desactualizado observer (commit dde0ea3)
El docstring de `_evaluate_fallen_rule` declaraba umbrales 0.75/0.85 cuando la lógica ejecutable usa 0.80/0.85. Desfase presente desde 4F-P1. Corregido como texto muerto — sin impacto en runtime.

```diff
-        INFO  = abs_w>=0.85 + ambos pies en contacto.
-        WARN  = inclinacion moderada (0.75<=abs_w<0.85) O un pie perdido.
-        CRITICAL = inclinacion fuerte (abs_w<0.75) O ambos pies perdidos.
+        INFO  = abs_w>=FALLEN_W_WARN (0.85) + ambos pies en contacto.
+        WARN  = inclinacion moderada (FALLEN_W_CRITICAL<=abs_w<FALLEN_W_WARN, 0.80<=abs_w<0.85) O un pie perdido.
+        CRITICAL = inclinacion fuerte (abs_w<FALLEN_W_CRITICAL, 0.80) O ambos pies perdidos.
```

---

## 2. Sub-prueba de Reloj Común Isaac↔ROS2

**Objetivo:** verificar si `CLOCK_MONOTONIC` es compartido entre contenedor Isaac y `boring_noether` bajo `--network=host`.

**Método:** leer `time.monotonic_ns()` desde ambos contenedores casi-simultáneo y comparar delta.

**Resultados:**
```
boring_noether: 1023739802378206
host VM:        1023754777440295
delta:          ~14.97s = tiempo real entre comandos
```

**Conclusión:** delta corresponde exactamente al tiempo transcurrido entre los dos comandos — no hay divergencia de base. `CLOCK_MONOTONIC` es compartido. Base temporal única para correlación t0↔t1.

---

## 3. Microfase 4G-P3-A — Diseño Instrumentación t0→t1

**Decisión de diseño:** Opción B — marcador ROS2 explícito desde Isaac + timestamp en observer. No se usó parseo de logs existentes (jitter de flush invalida como métrica formal).

**Definición de timestamps:**
- `t0_trigger`: `time.monotonic_ns()` en Isaac en `it=450`, **antes** de inyectar la caída física
- `t1`: `time.monotonic_ns()` en observer al inicio de `_publish_fallen_safety_event`, justo antes de `publish(msg)`

**Tipo de marcador:** `std_msgs/String` + JSON congelado — sin nuevo `.msg`, sin recompilar `g1_msgs`. Schema: `g1_fall_marker_v1`.

**Schema congelado /g1/fall_marker:**
```json
{"schema": "g1_fall_marker_v1", "iteration": 450, "host_time_ns": <ns>, "reason": "FALL_TRIGGER"}
```

**Schema congelado observer log:**
```json
{"schema": "g1_observer_event_time_v1", "event_id": "<uuid>", "host_time_ns": <ns>, "event_type": "CONDITION_DETECTED", "source": "cross_consistency_observer"}
```

**Archivos modificados:**
- `sim_runtime/4F/g1ext_combo/.../obstelem_contact_3c2a/__init__.py`: t0 capturado antes del teleport, marker por log (pub_marker.publish comentado por scope issue)
- `src/cross_consistency_observer/cross_consistency_observer/cross_consistency_observer.py`: t1 capturado antes de publish(msg), print flush + logger.warn

---

## 4. Adversidades P3 — Diagnóstico y Corrección

### 4.1 pub_marker fuera de scope (INVALID 20260618_123528)
`pub_marker` se creaba en el bloque de setup pero no era visible en el bloque `_publish` anidado. Isaac crasheaba con `NameError: name 'pub_marker' is not defined` post-trigger, cortando telemetría. Observer se quedaba con snapshot sano congelado.

**Fix:** desactivar `pub_marker.publish(_sm)` — el marker `G1_FALL_MARKER` queda en `A_isaac.log` vía `print(..., flush=True)`. Suficiente para correlación temporal.

### 4.2 Procesos huérfanos contaminaban corridas (múltiples INVALID)
Corridas anteriores dejaban 4 instancias de cada nodo en `boring_noether`. TX-011 se disparaba por SafetyEvent de instancias viejas, no del proceso actual. `B_observer.log` de la corrida nueva no mostraba detección.

**Diagnóstico:** `ros2 topic info /safety_events -v` reveló 12 publishers activos simultáneos.
**Fix temporal:** `docker restart boring_noether` antes de cada corrida.
**Fix permanente (P5):** preflight bloqueante.

### 4.3 G1_OBSERVER_EVENT_TIME ausente en B_observer.log
Patch correcto en `src/` pero no propagado a `install/` — build sin `--symlink-install`. `inspect.getfile()` dentro del contenedor confirmó ruta exacta del módulo en runtime.

**Fix:** `colcon build --packages-select cross_consistency_observer` dentro de `boring_noether`.

### 4.4 t1→t2 ruta directa no determinista (5/10 en corridas P3-C contaminadas)
`_recovery_allowed()` bloquea recovery cuando compound state = `STABILITY_RISK/R3`. Race condition: si TX-011 actualiza `/system_state` antes de que recovery procese el SafetyEvent directo, recovery se bloquea.

**Causa raíz:** recovery no tiene subscriber a `/safety_actions`. Escucha SafetyEvent directo (ruta no gobernada). → DT-4G-003 → resuelto en P4.

---

## 5. Microfase 4G-P3-B/C — Piloto y N=10 t0→t1

**Piloto:** corrida `20260618_131606` — primer PASS limpio tras resolver todos los bugs de instrumentación.

```
G1_FALL_MARKER:           t0_ns=1027510942183560
G1_OBSERVER_EVENT_TIME:   t1_ns=1027513802807492
t0→t1:                    2860.62ms
SafetyEvent REAL:         abs_w=0.712, L=False, R=True ✅
TX-011:                   (SAFE,NONE)→(STABILITY_RISK,R3) ✅
```

**N=10 P3-C (corridas 20260618_133215 → 20260618_135904):**

| Corrida | t0→t1 ms |
|---|---|
| 133215 | 2046.47 |
| 133451 | 2074.16 |
| 133815 | 2702.89 |
| 134050 | 2570.75 |
| 134321 | 2135.10 |
| 134636 | 3511.02 |
| 134903 | 2301.68 |
| 135229 | 2126.52 |
| 135553 | 2305.44 |
| 135904 | 2972.01 |

```
N=10, 100% PASS
media:  2474.60ms
min:    2046.47ms
max:    3511.02ms
```

**Interpretación:** t0→t1 mide desde la orden de inyección de caída en Isaac hasta publicación del SafetyEvent. Incluye dinámica física, actualización de sensores, transporte ROS2/DDS, y 3 snapshots consecutivos requeridos por regla 3C2b (FALLEN_CONSECUTIVE_N=3).

---

## 6. Microfase 4G-P3-D — Parser t1→t2 y Diagnóstico

**Parser extendido:** `analyze_runs.py --phase p3b` extrae:
- `G1_FALL_MARKER` de `A_isaac.log`
- `G1_OBSERVER_EVENT_TIME` de `B_observer.log`
- `LATENCY t1→t2` de `D_recovery.log` (ruta directa)
- `ORCH_ACTION→RECOVERY` de `D_recovery.log` (ruta gobernada)

**Diagnóstico P3-D bloqueado por DT-4G-003:**
- t1→t2 presente en 5/10 corridas P3-C contaminadas vía ruta directa
- Corridas sin t1→t2: recovery no actuó — TX-011 ocurrió pero `_recovery_allowed()` bloqueó porque compound state ya era `STABILITY_RISK/R3`
- Causa raíz: race condition entre SafetyEvent directo y `/system_state` actualizado por TX-011

**Resolución:** P3-D se cierra con ruta gobernada (P4-D), no con ruta directa.

---

## 7. Microfase 4G-P4-A — Auditoría Orchestrator→Recovery

**Pregunta:** ¿existe infraestructura para ruta gobernada orchestrator→recovery?

**Hallazgos:**

| Componente | Estado |
|---|---|
| Orchestrator publica `/safety_actions` | ✅ Sí (línea 803) |
| TX-011 genera SafetyAction | ✅ Sí (línea 1065) |
| SafetyAction tiene `action_name`, `execution_authority`, `transition_id`, `timestamp` | ✅ Confirmado vía `ros2 interface show` |
| Recovery suscribe `/safety_actions` | ❌ No — grep vacío |
| Recovery usa `/system_state` | Solo como precondición (`_recovery_allowed()`) |

**Gap exacto:** recovery necesita subscriber a `/safety_actions`. La infraestructura de publicación ya existe en orchestrator — falta el subscriber en recovery.

**Causa raíz DT-4G-003 confirmada en código:**
```python
def _recovery_allowed(self) -> bool:
    with self._state_lock:
        risk_blocked = self._current_risk_level in BLOCKED_RISK_LEVELS      # STABILITY_RISK ✓
        restriction_blocked = self._current_restriction_level in BLOCKED_RESTRICTION_LEVELS  # R3 ✓
    return not (risk_blocked and restriction_blocked)
```
TX-011 transiciona a `STABILITY_RISK/R3` → `_recovery_allowed()=False` → recovery bloqueado si SafetyEvent llega después del state update.

---

## 8. Microfase 4G-P4-B — Diseño Subscriber Gobernado

**Decisión de diseño aprobada por PM:**

- Subscriber aditivo — ruta directa SafetyEvent queda como fallback
- Acepta solo: `action_name='stabilization_mode'` + `transition_id='TX-011'` + `execution_authority='AUTONOMOUS'`
- Guard anti-doble ejecución por ventana temporal 5s (no por transition_id permanente — se repetiría entre corridas)
- Log: `ORCH_ACTION→RECOVERY route=orchestrator_safety_action action=... tx=... latency_ms=... t1_ns=... t2_ns=...`
- Latencia medida desde `msg.timestamp` de SafetyAction (timestamp añadido en orchestrator — 1 línea)

**Fix orchestrator (1 línea):**
```python
action.timestamp = self.get_clock().now().to_msg()
```

---

## 9. Microfase 4G-P4-C/D — Implementación y N=10

**Callback implementado en recovery_g1:**
```python
def _on_safety_action(self, msg: SafetyAction):
    if msg.action_name != 'stabilization_mode': return
    if msg.transition_id != 'TX-011': return
    if msg.execution_authority != 'AUTONOMOUS': return
    with self._recovery_lock:
        if self._recovery_active: return
        key = (msg.transition_id, msg.action_name)
        now = time.monotonic()
        if key == self._last_governed_key and (now - self._last_governed_time) < 5.0: return
        self._last_governed_key = key
        self._last_governed_time = now
        self._recovery_active = True
    t2_ns = self.get_clock().now().nanoseconds
    t1_ns = msg.timestamp.sec * 1_000_000_000 + msg.timestamp.nanosec
    latency_ms = (t2_ns - t1_ns) / 1e6
    self.get_logger().warn(
        f'[4G-P4] ORCH_ACTION→RECOVERY route=orchestrator_safety_action '
        f'action={msg.action_name} tx={msg.transition_id} '
        f'latency_ms={latency_ms:.3f} t1_ns={t1_ns} t2_ns={t2_ns}'
    )
    try:
        self._dispatch_recovery('CONDITION_DETECTED', 'imu_contact_support', 'orchestrator')
    finally:
        with self._recovery_lock:
            self._recovery_active = False
```

**Piloto P4-C (20260618_144007):**
```
ORCH_ACTION→RECOVERY: latency_ms=2.388, t1_ns>0 ✅
LATENCY t1→t2 directo: latency_ms=0.951 ✅ (fallback activo)
Sin doble ejecución ✅
```

**N=10 P4-D (20260618_160555 → 20260618_164129) — laboratorio limpio:**

| Corrida | t0→t1 ms | t1→t2 ms |
|---|---|---|
| 160555 | 2545.14 | 0.95 |
| 161653 | 2055.00 | 0.99 |
| 162027 | 3009.17 | 1.06 |
| 162342 | 2972.58 | 1.06 |
| 162640 | 2533.75 | 1.01 |
| 162939 | 2086.43 | 2.02 |
| 163233 | 2728.42 | 1.70 |
| 163530 | 2072.15 | 1.12 |
| 163825 | 2867.30 | 1.20 |
| 164129 | 2966.14 | 0.83 |

```
N=10, 100% PASS
t0→t1: media=2583.61ms, min=2055.00ms, max=3009.17ms
t1→t2: media=1.19ms, min=0.83ms, max=2.02ms — ruta gobernada 10/10
```

**DT-4G-003 CERRADA.** Ruta gobernada orchestrator→recovery validada N=10.

---

## 10. Microfase 4G-P5 — Higiene Operacional

### 10.1 Diagnóstico causa raíz nodos huérfanos
El launcher mata sus subprocesos (`subprocess.Popen`) pero los procesos dentro de `boring_noether` persisten — son hijos del entrypoint `ros2 run` dentro del contenedor, no del proceso Python del launcher en el host.

Evidencia P5 observacional (corrida 20260618_152445):
- Post-teardown: ~80 procesos residuales + 33 publishers en `/safety_events`
- Causa: 10 corridas P4-D previas sin restart entre ellas

### 10.2 Implementación preflight bloqueante

**Checks añadidos al final de `preflight()` en `launch_pipeline.py`:**

1. Procesos safety en contenedor: `ps -ef | grep -E 'cross_consistency_observer|safety_orchestrator_g1|watchdog_g1|recovery_g1'`
   - 0 procesos → `LABORATORIO LIMPIO: 0 procesos safety residuales`
   - >0 procesos → `FAIL preflight: procesos safety residuales` → `ok = False`

2. Publishers en `/safety_events`: `ros2 topic info /safety_events -v | grep 'Publisher count'`
   - Publisher count: 0 → `LABORATORIO LIMPIO: 0 publishers en /safety_events`
   - Publisher count: >0 → `FAIL preflight: publishers residuales` → `ok = False`

### 10.3 Post-teardown hygiene (observacional)
Añadido al final del launcher para documentar residuos sin bloquear exit code. Permite auditoría de limpieza por corrida.

### 10.4 Validación P5 en N=10 P4-D
Todas las corridas P4-D mostraron `LABORATORIO LIMPIO` en preflight — el ciclo `docker restart boring_noether` + preflight bloqueante garantizó laboratorio limpio.

### 10.5 Deuda técnica nueva DT-4G-004
El `docker restart` entre corridas es necesario porque el teardown no limpia el contenedor. Para eliminar esta dependencia, el teardown debe ejecutar `pkill` activo dentro de `boring_noether`. Diferido — no impacta resultados actuales.

---

## 11. Latencia End-to-End — Resumen

```
t0→t1  evento físico Isaac → SafetyEvent observer
       media=2474ms (P3-C) / 2583ms (P4-D)
       Incluye: dinámica física, sensores, DDS, 3 snapshots 3C2b

t1→t2  SafetyEvent → recovery action (ruta gobernada)
       media=1.19ms (P4-D N=10)
       Ruta: orchestrator SafetyAction → /safety_actions → recovery

t1→t2  SafetyEvent → recovery action (ruta directa, fallback)
       media~1ms (presente en corridas P4-D cuando llega antes de TX-011)
       Race condition — no determinista
```

---

## 12. Deuda Técnica Activa al Cierre

| ID | Deuda | Prioridad |
|---|---|---|
| DT-4E-001 | SAFETY_MODEL_G1.md ausente | Alta |
| DT-4E-006 | Control PD diferido | Alta |
| DT-4F-001 | Thresholds pragmáticos | Media |
| DT-4F-002 | TX-006b/c sin test explícito | Media |
| DT-4F-003 | TX-009 POLICY_GATED exacta | Baja |
| DT-4F-004 | FREEZE IMU falso positivo potencial | Media |
| DT-4G-001 | TX-011 escalación gobernada SECONDARY/fallen | ✅ CERRADA |
| DT-4G-002 | t1→t2 correlación por UUID/event_id (paper) | Media |
| DT-4G-003 | Ruta gobernada orchestrator→recovery | ✅ CERRADA |
| **DT-4G-004** | **Teardown activo dentro del contenedor (docker restart requerido)** | **Media** |

---

## 13. Anti-Patterns Nuevos

| # | Anti-pattern | Corrección |
|---|---|---|
| 66 | Diseñar TX desde texto de informe, no código real | Auditar `_publish_fallen_safety_event` y `_eval_TX*` antes de cualquier propuesta |
| 67 | Tocar runtime safety para que pase un test de CI | Fix siempre en el test |
| 68 | Test de estado inicial con launch completo | Aislar: orchestrator-only para INIT |
| **69** | **Marcar dedup de safety action por transition_id permanente** | **Usar ventana temporal corta — transition_id se repite entre corridas** |
| **70** | **No verificar laboratorio limpio antes de corridas formales** | **Preflight bloqueante obligatorio — 0 procesos + 0 publishers** |
| **71** | **Correr N≥10 sin restart entre corridas en contenedor persistente** | **docker restart antes de cada corrida hasta DT-4G-004 resuelto** |

---

## 14. Estado de la VM al Cierre

```
Repo activo    → ~/g1-deterministic-safety-runtime (main, origin synced)
HEAD           → 0c25f38
Contenedor     → boring_noether activo
Logs 4G        → ~/runs/4G/ (P2-A + P2-B + P2-C + P3 + P4-D)
Launcher       → sim_runtime/4G/launch_pipeline.py (preflight bloqueante activo)
CI             → Build ✅ Audit ✅
Tests          → 65 tests total — todos PASS
```

---

## 15. Próximos Pasos

```
4H-P1  Recovery inteligente por causa
4I-P1  Recrear SAFETY_MODEL_G1.md (DT-4E-001)
4I-P2  Assurance case
4J-P1  Fault matrix extendida
```

---

## LLAVE DEL SIGUIENTE CHAT

```
4G CERRADA (técnicamente):
  P3-C: t0→t1 N=10, 100% PASS, media=2474.60ms
  P3-D: t1→t2 N=10, 100% PASS, media=1.19ms ruta gobernada
  P4-D: ruta gobernada orchestrator→recovery N=10, 100% PASS
  P5:   preflight bloqueante + post-teardown hygiene

COMMITS: dde0ea3 | 5a925c8 | 64d7f06 | 846d994 | 0c25f38
HEAD: 0c25f38 — CI Build ✅ CI Audit ✅

DEUDAS NUEVAS:
  DT-4G-004: teardown activo contenedor (docker restart requerido entre corridas)
  DT-4G-002: t1→t2 UUID correlación (paper)

ANTI-PATTERNS NUEVOS: #69 (dedup permanente), #70 (sin preflight limpio), #71 (N sin restart)

PRÓXIMO: 4H-P1 — Recovery inteligente por causa
         Diseño antes de implementar, aprobación PM antes de corridas
```

---

*G1 Deterministic Safety Runtime — Informe Cierre 4G-P3→P5*
*Generado: 2026-06-18*
*PM: ChatGPT | Implementador/Auditor: Claude | Operador: Jorge Padilla*
*Repositorio: github.com/jorgerpg1213-mitech/g1-deterministic-safety-runtime*
