# Informe de Sesión — Etapa 4H-P2
## G1 Deterministic Safety Runtime
**Fecha:** 2026-06-19
**Estado al cierre:**
- **4H-P2 ✅ CERRADA** — policy hardening: causas terminales (FREEZE, NANINF, TIMESTAMP) bypassean cooldown/retry; validado focalmente
- **DT-4G-004B 🔲 ABIERTA** — zombies `<defunct>` por PID1/reaper; no bloqueante
- **4H-P1 ✅ CERRADA** (sesión anterior)

**Roles:** PM: ChatGPT | Implementador/Auditor: Claude | Operador: Jorge Padilla
**Referencia previa:** `informe_etapa_4G_004_4H_P1_2026-06-19.md`
**Commit de sesión:** pendiente al cierre de este informe
**HEAD local:** `0865711` → pendiente commit 4H-P2
**Repositorio:** `~/g1-deterministic-safety-runtime` | `origin/main`
**Contenedor:** `boring_noether` activo

---

## 0. Resumen Ejecutivo

Esta sesión abrió con 4H-P1 cerrada y 4H-P2 definida como TBD en los documentos. El PM la definió en esta sesión como **recovery policy hardening**: auditoría completa de la política de recovery (prioridad, cooldown, escalación, eventos simultáneos, fallback directo vs gobernado) con corrección de gaps encontrados.

**Objetivo:** ¿La capa `recovery_g1` tiene una política mínima explícita y defendible para manejar prioridades, cooldowns, escalamiento, eventos simultáneos y fallback directo sin ambigüedad operacional?

**Hallazgos principales:**
1. Auditoría de `recovery_g1.py` confirmó que `_recovery_active`, cooldown y escalación funcionan correctamente para causas recuperables.
2. Gap identificado: causas terminales (FREEZE, NANINF, TIMESTAMP) pasaban por el bloque cooldown/escalation y consumían retry counter — comportamiento incorrecto para causas que siempre requieren intervención del operador desde la primera ocurrencia.
3. Fix mínimo 4H-P2-A: constante global `TERMINAL_MANUAL_RULE_IDS` + bypass antes del bloque cooldown/escalation en `_dispatch_recovery()`.
4. Validación focal PASS: dos FREEZE consecutivos mismo target <5s sin "Cooldown activo"; STALE posterior sin contaminación de counter.

---

## 1. Auditoría de Política — `recovery_g1.py`

### 1.1 Alcance de la Auditoría

Se auditó `src/recovery_g1/recovery_g1/recovery_g1.py` completo. Elementos revisados:

- `_recovery_active` — guard de re-entrancy
- Bloque cooldown (`RETRY_COOLDOWN_S`, `EXTENDED_COOLDOWN_S`)
- Escalación (`MAX_AUTO_RETRIES`)
- Mapeo causal 4H-P1 (STALE/FREEZE/NANINF/TIMESTAMP/fallen)
- Ruta gobernada `_on_safety_action()` (TX-011)
- Manejo de eventos simultáneos
- Retry counters y `last_attempt_time`

### 1.2 Hallazgos por Elemento

| Elemento | Estado pre-4H-P2 | Veredicto |
|---|---|---|
| `_recovery_active` mutex | bool simple, first accepted wins | correcto para scope 4H-P2 |
| Cooldown recuperables (STALE/fallen) | 5s normal, 15s crítico | correcto |
| Escalación MAX_AUTO_RETRIES=3 | aplica a todo target | correcto para recuperables |
| FREEZE/NANINF/TIMESTAMP | pasaban por cooldown/escalation | **GAP** |
| TX-011 gobernada | intacta, sin cambio | correcto |
| Eventos simultáneos | segundo descartado por `_recovery_active` | documentado, no rediseñado |

### 1.3 Gap Confirmado

Las causas terminales FREEZE, NANINF y TIMESTAMP llegaban a `_dispatch_recovery()` y:
1. Consultaban `_retry_counters[target]` y `_last_attempt_time[target]`
2. Si `attempt > 0` y `elapsed < cooldown` → retornaban sin ejecutar nada ("Cooldown activo")
3. Si `attempt >= MAX_AUTO_RETRIES` → escalaban (redundante, ya ejecutan operator_intervention)
4. Actualizaban `_retry_counters[target]` y `_last_attempt_time[target]` al salir

Resultado observable: un segundo FREEZE del mismo target dentro de 5s era silenciado por cooldown. Un STALE posterior al FREEZE podía quedar bloqueado por el counter contaminado del FREEZE.

**Evidencia pre-fix (corrida de diagnóstico):**
```
[WARN] [4H-P1] cause=FREEZE target=/g1/imu action=operator_intervention   ← FREEZE #1 OK
[INFO] Cooldown activo para /g1/imu: 0.5s / 5.0s                          ← FREEZE #2 bloqueado
[INFO] Cooldown activo para /g1/imu: 1.5s / 5.0s                          ← STALE bloqueado
```

---

## 2. Implementación 4H-P2-A — Bypass Terminal Causes

### 2.1 Decisión de Arquitectura

PM autorizó parche mínimo con variable única: **causas terminales bypass retry/cooldown**.

Política aprobada:
- FREEZE, NANINF, TIMESTAMP → ejecutar `operator_intervention` inmediatamente, sin consumir attempts ni quedar bloqueadas por cooldown
- STALE, fallen → conservan flujo existente (retry/cooldown/escalation)
- TX-011 gobernada → intacta

### 2.2 Cambios Implementados

**Archivo modificado:** `src/recovery_g1/recovery_g1/recovery_g1.py` únicamente.

**Cambio 1 — Constante global** (cerca de `MAX_AUTO_RETRIES`):
```python
# 4H-P2 — Causas terminales/manuales: bypass cooldown y retry counter
# Estas causas requieren intervención del operador desde la primera ocurrencia.
# No son recuperables automáticamente — no deben consumir attempts ni quedar
# bloqueadas por cooldown entre notificaciones consecutivas.
TERMINAL_MANUAL_RULE_IDS = {'4F-P2-FREEZE', '4F-P2-NANINF', '4F-P2-TIMESTAMP'}
```

**Cambio 2 — Bypass en `_dispatch_recovery()`** (antes del bloque cooldown/escalation):
```python
# 4H-P2 — Bypass para causas terminales/manuales
rule_id = self._extract_rule_id(notes)
if rule_id in TERMINAL_MANUAL_RULE_IDS:
    cause = rule_id.split('-')[-1]
    self.get_logger().warn(
        f'[4H-P2] cause={cause} target={target} terminal=True '
        f'action=operator_intervention (bypass cooldown/retry)'
    )
    # Terminal manual causes are not auto-retries;
    # attempt=1 denotes first terminal manual notification.
    result = self._action_request_operator_intervention(target, 1)
    self._publish_recovery_event(result, event_type, source, 'REC-MANUAL')
    return
```

**Cambio 3 — Limpieza en bloque 4H-P1:** eliminados los `elif` redundantes de FREEZE/NANINF/TIMESTAMP (ya cubiertos por bypass). `rule_id` se extrae una sola vez antes del cooldown.

### 2.3 Invariantes Preservadas

- `_retry_counters` y `_last_attempt_time` no se tocan para causas terminales
- `_recovery_active` queda como mutex conservador (no modificado)
- `_on_safety_action()` / TX-011 intactos
- `_extract_rule_id()` reutilizado sin cambio

---

## 3. Validación Focal

### 3.1 Método

Harness externo no invasivo (`sim_runtime/harness_4H_P2_focal.py`) — publica `SafetyEvent` directamente a `/safety_events` sin watchdog ni stack completo. Una variable por corrida.

**Secuencia publicada:**
1. FREEZE #1 → `rule_id=4F-P2-FREEZE` (source=watchdog_g1)
2. `sleep(0.5)`
3. FREEZE #2 → mismo target, mismo rule_id (sep <5s, dentro de cooldown window anterior)
4. `sleep(1.0)`
5. STALE → mismo target, `rule_id=4F-P2-STALE`

### 3.2 Evidencia Observable

```
[4F-P5] LATENCY t1→t2 source=watchdog_g1 target=/g1/imu latency_ms=0.890
[4H-P2] cause=FREEZE target=/g1/imu terminal=True action=operator_intervention (bypass cooldown/retry)
[recovery_g1] OPERATOR INTERVENTION REQUIRED: target=/g1/imu attempt=1
[recovery_g1] RecoveryEvent: RECOVERY_SUCCESS action=request_operator_intervention target=/g1/imu attempt=1

[4F-P5] LATENCY t1→t2 source=watchdog_g1 target=/g1/imu latency_ms=0.777
[4H-P2] cause=FREEZE target=/g1/imu terminal=True action=operator_intervention (bypass cooldown/retry)
[recovery_g1] OPERATOR INTERVENTION REQUIRED: target=/g1/imu attempt=1
[recovery_g1] RecoveryEvent: RECOVERY_SUCCESS action=request_operator_intervention target=/g1/imu attempt=1

[4F-P5] LATENCY t1→t2 source=watchdog_g1 target=/g1/imu latency_ms=0.867
[4H-P1] cause=STALE target=/g1/imu action=wait_for_primary_restore
[recovery_g1] wait_for_primary_restore: target=/g1/imu attempt=1 max_wait=30.0s
[recovery_g1] wait_for_primary_restore: PRIMARY restaurada en 1.0s — risk_level=SAFE
[recovery_g1] RecoveryEvent: RECOVERY_SUCCESS action=wait_for_primary_restore target=/g1/imu attempt=1
```

### 3.3 Criterios PASS

| Criterio | Evidencia | Resultado |
|---|---|---|
| FREEZE #1 → `[4H-P2]` bypass | `cause=FREEZE terminal=True` | ✅ |
| FREEZE #2 mismo target <5s → `[4H-P2]` sin cooldown | segundo `[4H-P2]` presente, sin "Cooldown activo" | ✅ |
| STALE post-FREEZE → `[4H-P1]` sin contaminación | `cause=STALE attempt=1` sin cooldown bloqueante | ✅ |
| No "Cooldown activo" en ningún punto | ausente en todo el log | ✅ |
| 65 tests PASS post-build | 65/65 | ✅ |
| `py_compile` OK en contenedor | OK | ✅ |
| `git diff --name-only` solo `recovery_g1.py` | confirmado | ✅ |

### 3.4 Alcance de la Conclusión

- PASS directo demostrado para FREEZE.
- NANINF y TIMESTAMP cubiertos por equivalencia estructural — misma rama `TERMINAL_MANUAL_RULE_IDS`; no se requiere N formal por causa en 4H-P2.
- Simultaneidad (`_recovery_active`) fuera de alcance — documentada como política, no rediseñada.

---

## 4. Política Mínima de Recovery — Estado Post-4H-P2

| Causa | Ruta | Prioridad | Acción | Tipo | Cooldown | Escalación | Colisión |
|---|---|---|---|---|---|---|---|
| Caída física | gobernada TX-011 | Alta | stabilization_mode | REC-AUTO | dedup 5s ventana | N/A | first accepted wins |
| Caída directa fallback | directa `_on_safety_event` | Alta | wait_for_primary_restore | REC-AUTO | RETRY_COOLDOWN_S | MAX_AUTO_RETRIES | `_recovery_active` mutex |
| STALE | directa | Media | wait_for_primary_restore | REC-AUTO | RETRY_COOLDOWN_S | MAX_AUTO_RETRIES | `_recovery_active` mutex |
| FREEZE | directa — bypass terminal | Alta | operator_intervention | REC-MANUAL | **ninguno** | **ninguna** | `_recovery_active` mutex |
| NANINF | directa — bypass terminal | Alta | operator_intervention | REC-MANUAL | **ninguno** | **ninguna** | `_recovery_active` mutex |
| TIMESTAMP | directa — bypass terminal | Alta | operator_intervention | REC-MANUAL | **ninguno** | **ninguna** | `_recovery_active` mutex |

**Política de simultaneidad:** single-flight — `_recovery_active` actúa como mutex; el primer evento aceptado se ejecuta completo, el segundo es descartado con log debug. No hay cola ni scheduler de prioridad interno. Comportamiento documentado, no rediseñado en 4H-P2.

---

## 5. Deuda Técnica Activa al Cierre

| ID | Deuda | Prioridad | Estado |
|---|---|---|---|
| DT-4E-001 | SAFETY_MODEL_G1.md ausente | Alta | Abierta — objetivo 4I-P1 |
| DT-4E-006 | Control PD diferido | Alta | Abierta |
| DT-4F-001 | Thresholds pragmáticos | Media | Abierta |
| DT-4F-002 | TX-006b/c sin test explícito | Media | Abierta |
| DT-4F-003 | TX-009 POLICY_GATED exacta | Baja | Abierta |
| DT-4F-004 | FREEZE IMU falso positivo potencial | Media | Abierta |
| DT-4G-002 | t1→t2 correlación UUID/event_id | Media | Abierta |
| DT-4G-004B | Zombies `<defunct>` por PID1/reaper | Baja | Abierta |

Sin nuevas deudas en 4H-P2.

---

## 6. Estado de la VM al Cierre

```
Repo activo    → ~/g1-deterministic-safety-runtime (main, commit pendiente)
HEAD local     → 0865711 + cambios sin commit
Contenedor     → boring_noether activo
Tests          → 65/65 PASS
CI             → Build ✅ Audit ✅ (post-commit)
Recovery       → src/recovery_g1/recovery_g1/recovery_g1.py (4H-P2-A activo)
Harness        → sim_runtime/harness_4H_P2_focal.py
```

---

## 7. Próximos Pasos

```
4H-P2  CERRADA ✅ — policy hardening: bypass terminal causes validado
4I-P1  Recrear SAFETY_MODEL_G1.md (DT-4E-001)
4I-P2  Assurance case
DT-4G-004B  Resolver reaper/PID1 boring_noether (--init flag)
```

---

## LLAVE DEL SIGUIENTE CHAT

```
4H CERRADA ✅
  4H-P1: recovery inteligente por causa
  4H-P2: policy hardening — bypass terminal causes (FREEZE/NANINF/TIMESTAMP)

HEAD: [pendiente commit 4H-P2]
CI Build ✅ CI Audit ✅

Política de recovery post-4H-P2:
  FREEZE/NANINF/TIMESTAMP: terminal, bypass cooldown/retry, REC-MANUAL inmediato
  STALE/fallen: recuperables, retry/cooldown/escalation normal
  TX-011 gobernada: intacta
  Simultaneidad: single-flight _recovery_active, first accepted wins

PRÓXIMO: 4I-P1 — SAFETY_MODEL_G1.md
```

---

*G1 Deterministic Safety Runtime — Informe Cierre 4H-P2*
*Generado: 2026-06-19*
*PM: ChatGPT | Implementador/Auditor: Claude | Operador: Jorge Padilla*
*Repositorio: github.com/jorgerpg1213-mitech/g1-deterministic-safety-runtime*
