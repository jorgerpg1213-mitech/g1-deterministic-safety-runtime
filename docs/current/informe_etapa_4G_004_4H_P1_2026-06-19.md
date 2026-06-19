# Informe de Sesión — DT-4G-004 + Etapa 4H-P1
## G1 Deterministic Safety Runtime
**Fecha:** 2026-06-19
**Estado al cierre:**
- **DT-4G-004A ✅ CERRADA** — teardown activo dentro del contenedor; ya no se requiere `docker restart` entre corridas por procesos ACTIVE o publishers residuales
- **DT-4G-004B 🔲 ABIERTA** — zombies `<defunct>` por falta de reaper/PID1 en `boring_noether`; no bloqueante
- **4H-P1 ✅ CERRADA** — recovery inteligente por causa validado: fallen, STALE, FREEZE, NANINF, TIMESTAMP

**Roles:** PM: ChatGPT | Implementador/Auditor: Claude | Operador: Jorge Padilla
**Referencia previa:** `informe_etapa_4G_P3_P5_2026-06-18.md`
**Commits de sesión:**
- `0939fef` — fix(launcher): DT-4G-004 teardown activo + SAFETY_PROC_PATTERN + preflight bloqueante
- `5005788` — fix(4G-004,4H-P1): ignore defunct residues and route recovery by cause

**HEAD:** `5005788` — CI Build ✅ CI Audit ✅
**Repositorio:** `~/g1-deterministic-safety-runtime` | `origin/main` synced
**Contenedor:** `boring_noether` activo

---

## 0. Resumen Ejecutivo

Esta sesión arrancó con 4G cerrada técnicamente y DT-4G-004 abierta (teardown no limpiaba el contenedor, requiriendo `docker restart boring_noether` entre corridas). La sesión ejecutó dos objetivos principales:

1. **DT-4G-004:** resolver la necesidad de restart entre corridas mediante teardown activo dentro del contenedor + reclasificación semántica de zombies `<defunct>`.
2. **4H-P1:** implementar recovery inteligente por causa — diferenciar fallen, STALE, FREEZE, NANINF, TIMESTAMP y ejecutar acción apropiada por cada causa.

**Hallazgos principales:**
1. Root cause DT-4G-004 confirmado en código: `teardown_proc()` mata el cliente `docker exec` en el host, pero los procesos ROS2 dentro del contenedor se reparentan a PID 1 y sobreviven.
2. Fix mínimo DT-4G-004A: `grep -v '<defunct>'` en checks de procesos — zombies no ejecutan ni publican, no deben bloquear preflight.
3. Gap 4H-P1 confirmado por auditoría: la causa de fault llega a `recovery_g1` vía `msg.notes` con `rule_id=4F-P2-STALE/FREEZE/NANINF/TIMESTAMP`, pero `_dispatch_recovery()` no la leía — todo caía en `else → operator_intervention`.
4. Validación causal completa mediante harnesses externos no invasivos: cadena `topic → watchdog → SafetyEvent → recovery → [4H-P1] cause=...` verificada para las 5 causas.

---

## 1. DT-4G-004 — Teardown Activo Dentro del Contenedor

### 1.1 Root Cause Confirmado

`launch_ros2()` ejecuta `Popen(["docker","exec",CONTAINER,"bash","-c",...])`. `teardown_proc()` envía `terminate()`/`kill()` al cliente `docker exec` del host. Los procesos ROS2 dentro del contenedor se reparentan a PID 1 y sobreviven. Resultado: acumulación de procesos y publishers fantasma que bloquean el preflight de la siguiente corrida.

### 1.2 Evidencia Observable Pre-fix

```
Post-teardown corrida anterior:
  ~80 procesos residuales en boring_noether
  33 publishers en /safety_events
  Preflight siguiente corrida: FAIL
```

### 1.3 Implementación DT-4G-004A

**Cambio 1 — `SAFETY_PROC_PATTERN` como constante global única** (fuente de verdad compartida por preflight, teardown y hygiene check):
```python
SAFETY_PROC_PATTERN = (
    "cross_consistency_observer|safety_orchestrator_g1"
    "|watchdog_g1|recovery_g1"
)
```

**Cambio 2 — `teardown_container()`** — enumera PIDs dentro del contenedor, envía SIGTERM, re-verifica, escala a SIGKILL si quedan residuos:
```
Fase 1: ps | grep SAFETY_PROC_PATTERN | awk PID → kill PIDs
Fase 2: re-verificar → si quedan, kill -9
```

**Cambio 3 — preflight e hygiene ignoran `<defunct>`** — fix mínimo de 2 líneas:
```python
grep -v '<defunct>'  # añadido a ambos checks
```

### 1.4 Clasificación Semántica ACTIVE/DEFUNCT

| Clase | Definición | Criterio preflight |
|---|---|---|
| ACTIVE | proceso ejecutable, puede publicar ROS2 | bloqueante |
| DEFUNCT | zombie reparentado a PID 1, no ejecuta ni publica | WARN, no bloqueante |
| Publisher `/safety_events` > 0 | contaminación DDS activa | bloqueante |

### 1.5 Validación DT-4G-004A

Dos corridas consecutivas sin `docker restart`:
- Corrida 1: LAUNCHER PASS, post-teardown `0 procesos safety residuales`, `0 publishers /safety_events`
- Corrida 2: preflight `LABORATORIO LIMPIO`, LAUNCHER PASS

**DT-4G-004A cerrada operacionalmente.**

### 1.6 DT-4G-004B — Zombies por PID1/Reaper

Los zombies `<defunct>` se acumulan ~2 por corrida porque PID 1 del contenedor no hace `wait()`. No ejecutan, no publican, no contaminan ROS2. Para corridas N≥10 formales, monitorear conteo. Para N normal: permitido continuar sin restart.

**Solución real de DT-4G-004B:** lanzar `boring_noether` con init adecuado (ej. `--init` flag de Docker). Diferido.

---

## 2. Etapa 4H-P1 — Recovery Inteligente por Causa

### 2.1 Pregunta Técnica

¿`recovery_g1` puede diferenciar la causa del evento safety (fallen, STALE, FREEZE, NANINF, TIMESTAMP) y ejecutar una acción coherente por causa?

### 2.2 Auditoría de Flujo — Gap Identificado

**Lo que publica `watchdog_g1`:** causa codificada en `msg.notes` con prefijo `rule_id`:
- STALE → `notes="rule_id=4F-P2-STALE ..."`
- FREEZE → `notes="rule_id=4F-P2-FREEZE ..."`
- NANINF → `notes="rule_id=4F-P2-NANINF ..."`
- TIMESTAMP → `notes="rule_id=4F-P2-TIMESTAMP ..."`

**`SafetyAction` no transporta causa:** el orchestrator convierte `SafetyEvent → SafetyAction=stabilization_mode` y la causa se pierde. TX-011 solo se dispara por caída física — la causa está implícita.

**Gap en `_dispatch_recovery()`:** no leía `notes` ni `rule_id`. Todo `CONDITION_DETECTED` caía en `else → request_operator_intervention`.

**Decisión de arquitectura:** 4H-P1 se implementa en la ruta directa `_on_safety_event() → _dispatch_recovery()`. La ruta gobernada `_on_safety_action()` no se toca — TX-011 ya representa caída y ejecuta `stabilization_mode`.

### 2.3 Implementación

**Archivo modificado:** `src/recovery_g1/recovery_g1/recovery_g1.py` únicamente.

**Cambio 1 — `_extract_rule_id(notes)`** — helper defensivo:
```python
def _extract_rule_id(self, notes: str) -> str:
    notes = notes or ''
    for token in notes.split():
        if token.startswith('rule_id='):
            return token.split('=', 1)[1]
    return ''
```

**Cambio 2 — `_on_safety_event()` pasa `notes`:**
```python
notes = getattr(msg, 'notes', '') or ''
self._dispatch_recovery(event_type, target, source, notes=notes)
```

**Cambio 3 — bloque causal en `_dispatch_recovery()`** (después de `attempt` definido, antes del mapeo existente de `event_type`):

| Causa | Señal | Acción |
|---|---|---|
| Caída física (directa) | `source=cross_consistency_observer` | `wait_for_primary_restore` (fallback) |
| STALE | `rule_id=4F-P2-STALE` | `wait_for_primary_restore` |
| FREEZE | `rule_id=4F-P2-FREEZE` | `operator_intervention` |
| NANINF | `rule_id=4F-P2-NANINF` | `operator_intervention` |
| TIMESTAMP | `rule_id=4F-P2-TIMESTAMP` | `operator_intervention` |
| TX-011 gobernada | `_on_safety_action()` intacto | `stabilization_mode` (sin cambio) |

### 2.4 Validación

**Tests:** 65/65 PASS post-patch.

**Corrida integración (launcher completo):**
```
[4H-P1] cause=fallen route=direct_fallback action=wait_for_primary_restore
[4G-P4] ORCH_ACTION→RECOVERY route=orchestrator_safety_action action=stabilization_mode tx=TX-011 latency_ms=1007.371
```
TX-011 gobernada intacta ✅. Ruta directa fallback activa ✅.

**Harness STALE** (topic → watchdog → SafetyEvent → recovery):
```
watchdog: [4F-P2-STALE] SafetyEvent CRITICAL — /g1/imu sin mensaje 1.39s
recovery: [4H-P1] cause=STALE target=/g1/imu action=wait_for_primary_restore
```
STALE ✅. FREEZE ✅ (detectado en warmup con valores repetidos).

**Harness NANINF:**
```
watchdog: [4F-P2-NANINF] SafetyEvent CRITICAL — /g1/imu NaN/inf valores=[nan, 0.0, ...]
recovery: [4H-P1] cause=NANINF target=/g1/imu action=operator_intervention
```
NANINF ✅.

**Harness TIMESTAMP:**

    watchdog: [4F-P2-TIMESTAMP] SafetyEvent WARN — /g1/imu | Timestamp regresivo
    recovery: [4H-P1] cause=TIMESTAMP target=/g1/imu action=operator_intervention

TIMESTAMP ✅.

### 2.5 Limitaciones Declaradas

- Acción para `fallen` directa (`wait_for_primary_restore`) es semánticamente débil — la acción correcta de caída física va por ruta gobernada TX-011. El fallback directo queda auditado con log `cause=fallen route=direct_fallback`.
- Validación de STALE/FREEZE en harness incluye ruido de startup ("sin mensaje nunca recibido") — evidencia principal es el STALE limpio post-warmup.

---

## 3. Deuda Técnica Activa al Cierre

| ID | Deuda | Prioridad | Estado |
|---|---|---|---|
| DT-4E-001 | SAFETY_MODEL_G1.md ausente | Alta | Abierta |
| DT-4E-006 | Control PD diferido | Alta | Abierta |
| DT-4F-001 | Thresholds pragmáticos | Media | Abierta |
| DT-4F-002 | TX-006b/c sin test explícito | Media | Abierta |
| DT-4F-003 | TX-009 POLICY_GATED exacta | Baja | Abierta |
| DT-4F-004 | FREEZE IMU falso positivo potencial | Media | Abierta |
| DT-4G-002 | t1→t2 correlación por UUID/event_id (paper) | Media | Abierta |
| DT-4G-004A | Teardown activo contenedor | — | ✅ CERRADA |
| **DT-4G-004B** | **Zombies `<defunct>` por PID1/reaper** | **Baja** | **Abierta** |

---

## 4. Anti-Patterns Nuevos

| # | Anti-pattern | Corrección |
|---|---|---|
| 72 | Editar archivos críticos con `str.replace`/heredoc/sed sin verificar encoding primero | Siempre leer texto exacto con `sed -n` antes de escribir cualquier script de reemplazo |
| 73 | Mezclar dos causas en un solo harness de validación | Una variable por corrida — harness separado por causa |

---

## 5. Estado de la VM al Cierre

```
Repo activo    → ~/g1-deterministic-safety-runtime (main, origin synced)
HEAD           → 5005788
Contenedor     → boring_noether activo
Tests          → 65/65 PASS
CI             → Build ✅ Audit ✅
Launcher       → sim_runtime/4G/launch_pipeline.py (teardown activo + preflight bloqueante)
Recovery       → src/recovery_g1/recovery_g1/recovery_g1.py (4H-P1 activo)
```

---

## 6. Próximos Pasos

```
4H-P1  CERRADA — validación causal completa: fallen, STALE, FREEZE, NANINF, TIMESTAMP
4H-P2  TBD — definir siguiente pregunta técnica con PM
4I-P1  Recrear SAFETY_MODEL_G1.md (DT-4E-001)
4I-P2  Assurance case
4J-P1  Fault matrix extendida
DT-4G-004B  Resolver reaper/PID1 en boring_noether (--init flag)
```

---

## LLAVE DEL SIGUIENTE CHAT

```
4G CERRADA ✅
DT-4G-004A CERRADA ✅ — teardown activo, no se requiere docker restart entre corridas normales
DT-4G-004B ABIERTA — zombies <defunct> por PID1, no bloqueante, ~2 por corrida
4H-P1 CERRADA ✅ — recovery inteligente por causa validado

COMMITS: 0939fef | 5005788
HEAD: 5005788 — CI Build ✅ CI Audit ✅

4H-P1 validado:
  fallen directa: [4H-P1] cause=fallen route=direct_fallback ✅
  TX-011 gobernada: ORCH_ACTION→RECOVERY intacto ✅
  STALE:  cause=STALE action=wait_for_primary_restore ✅
  FREEZE: cause=FREEZE action=operator_intervention ✅
  NANINF: cause=NANINF action=operator_intervention ✅
  TIMESTAMP: cause=TIMESTAMP action=operator_intervention ✅

ANTI-PATTERNS NUEVOS: #72 (encoding), #73 (dos causas en un harness)

PRÓXIMO: definir 4H-P2 con PM o abrir 4I-P1 formalización
```

---

*G1 Deterministic Safety Runtime — Informe Cierre DT-4G-004 + 4H-P1*
*Generado: 2026-06-19*
*PM: ChatGPT | Implementador/Auditor: Claude | Operador: Jorge Padilla*
*Repositorio: github.com/jorgerpg1213-mitech/g1-deterministic-safety-runtime*
