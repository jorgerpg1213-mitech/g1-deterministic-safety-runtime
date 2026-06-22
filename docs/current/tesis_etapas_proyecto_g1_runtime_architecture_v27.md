# Tesis de Etapas del Proyecto — Runtime Architecture para Humanoide G1
## Versión 27 — Actualizada 2026-06-22 (4J-P0 + 4J-P1 + 4J-P2-prep cerradas)

> **Nota de versión (v27):** cambios respecto a v26 —
> (1) **4J-P0 CERRADA**: DT-4I-001 resuelta. `_on_safety_action()` autosuficiente. Commits `779821f` + `cb3f777`.
> (2) **4J-P1 CERRADA** (minimum causal traceability): `SafetyAction.msg` +`parent_event_id`, orchestrator propaga, recovery incluye en notes. Commit `bbcc097`. DT-4J-001 abierta.
> (3) **4J-P2-prep CERRADA**: trazabilidad ruta directa en `_dispatch_recovery()`. Bug `test_depend` corregido. Commit `cf4e835`.
> (4) DT-4I-001 ✅ cerrada. DT-4J-001 🔲 abierta.
> (5) CI Build ✅ CI Audit ✅ — 65/65 PASS 0 skipped post-4J-P2-prep.

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

Entregables: `SAFETY_MODEL_G1.md`, `TRACEABILITY_MATRIX_G1.md`, `POLICY_CLARIFICATION_G1.md`. DT-4E-001 y DT-4F-003 cerradas. DT-4I-001 identificada.

---

### Etapa 4J — Paper Prep — 🔄 EN PROGRESO

#### 4J-P0 — Runtime Alignment / Cierre DT-4I-001 — ✅ CERRADA (2026-06-22)

**Pregunta técnica:** ¿La ruta gobernada TX-011 ejecuta en `recovery_g1` la acción que el orchestrator emite?

**Root cause auditado:** `_on_safety_action()` pasaba TX-011 gobernada por `_dispatch_recovery()` — router causal de ruta directa. Router no reconocía `source='orchestrator'` ni causa causal → `else → operator_intervention`. `_action_stabilization_mode()` no existía.

**Diagnóstico arquitectónico:** `_dispatch_recovery()` es router de ruta directa. En ruta gobernada, la causa ya fue resuelta por el orchestrator — no debe redescubrirse. `_on_safety_action()` debe ser autosuficiente.

**Fix (un solo archivo — `recovery_g1.py`):**
- Nuevo método `_action_stabilization_mode()`: `success=True` = ejecución aceptada, `notes` declara `physical recovery not claimed`.
- `_on_safety_action()` autosuficiente: llama `_action_stabilization_mode()` directamente y publica `RecoveryEvent` con `recovery_type=REC-AUTO`.
- `REC-AUTO` respeta contrato `RecoveryEvent.msg` vigente. `REC-GOVERNED` descartado por PM: contract drift sin actualizar `.msg`.

**Validación:**

| Harness | PASS/FAIL | Observable clave |
|---|---|---|
| P0-A focal | ✅ PASS | `action_name=stabilization_mode`, `recovery_type=REC-AUTO`, `notes` con `governed_TX011` + `physical recovery not claimed` |
| P0-B integración | ✅ PASS | Cadena completa `SafetyEvent SECONDARY EFFECTIVE → orchestrator → SafetyAction TX-011 → RecoveryEvent` con topología aislada verificada |
| Regresión | ✅ 65/65 | Sin regresiones |

**Commits:** `779821f` + `cb3f777`
**DT-4I-001 ✅ CERRADA**

---

#### 4J-P1 — Causal Traceability — ✅ CERRADA — minimum scope (2026-06-22)

**Pregunta técnica:** ¿Puede trazarse un fault de punta a punta sin correlación manual por logs?

**Auditoría pre-P1:**
- `SafetyEvent.event_id` populado por observer (`uuid.uuid4()`) y watchdog (`uuid.uuid4()`) ✅
- Orchestrator NO propagaba `event_id` → `SafetyAction` — campo inexistente en `.msg`
- Correlación disponible solo por `transition_id` + `timestamp` — no paper-grade

**Fix aprobado (Opción A — mínima):**

| Archivo | Cambio |
|---|---|
| `SafetyAction.msg` | +`string parent_event_id` |
| `safety_orchestrator_g1.py` | `action.parent_event_id = getattr(triggering_event, 'event_id', '')` |
| `recovery_g1.py` | Lee `msg.parent_event_id` en `_on_safety_action()`, propaga en `RecoveryResult.notes` |

**Call path verificado:** `_execute_transition(tx, se.msg)` → `_publish_safety_action(tx, triggering_event)` — `triggering_event` es el `SafetyEvent` original con `event_id` real.

**Cadena implementada:**
```
SafetyEvent[event_id=A]
  → SafetyAction[parent_event_id=A]
    → RecoveryEvent.notes[parent_event_id=A]
```

**Harness P1-B PASS:** `event_id=4JP1B-TEST-001` trazado campo a campo. PASS exige ID exacto, no solo presencia del campo.

**Estado:** `4J-P1 ✅ cerrada como "minimum causal traceability"`. No como "full native traceability".

**No implementado → DT-4J-001:** `action_id`, `parent_action_id`, `RecoveryEvent.parent_event_id` nativo. Opcional P1-C o P3.

**Commit:** `bbcc097`

---

#### 4J-P2-prep — Direct Path Traceability — ✅ CERRADA (2026-06-22)

**Gap:** ruta directa (`_on_safety_event()` → `_dispatch_recovery()`) no propagaba `SafetyEvent.event_id`. `RecoveryResult.event_id` era UUID nuevo sin relación con el evento original.

**Fix (`recovery_g1.py` — un solo archivo):**
- `_dispatch_recovery()`: nuevo parámetro `parent_event_id: str = ''`
- `_on_safety_event()`: pasa `parent_event_id=getattr(msg, 'event_id', '')`
- 3 bloques de publicación (terminal bypass, escalation guard, path normal): propagan con guard `'parent_event_id=' not in (result.notes or '')`

**Bug de test_depend corregido:** `package.xml` de `safety_orchestrator_g1` sin `<test_depend>recovery_g1</test_depend>` causaba 9 skips en `colcon test`. Corregido. 65/65 PASS 0 skipped restaurado.

**Harness STALE directo PASS:** `event_id=4JP2-DIRECT-001` en `RecoveryEvent.notes`, `action_name=wait_for_primary_restore`, `recovery_type=REC-AUTO`. Topología: 1 subscriber exacto en `/safety_events`.

**Commit:** `cf4e835`

---

#### 4J-P2 — Extended Fault Injection Matrix — 🔲 PENDIENTE

**Fila ya ganada (no repetir):**

| Fault | Ruta | Acción | Evidencia |
|---|---|---|---|
| Fallen governed / physical instability | R1 / TX-011 | `stabilization_mode` | P0-B PASS + P1-B causal traceability |

**A ejecutar:** STALE, FREEZE, NANINF, TIMESTAMP, fallen direct fallback, RATE.

#### 4J-P3 — Timing Traceability Report — 🔲 PENDIENTE
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
| **DT-4J-001** | **Full native traceability** (`action_id`, `parent_action_id`, `RecoveryEvent.parent_event_id` nativo) | **Media** | **Abierta — P1-C o P3** |

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
| **75** | **Ejecutar harness sin verificar topología exacta (`ros2 topic info -v`)** |
| **76** | **Asumir `colcon test` tiene mismo entorno que import directo — sin `test_depend`** |
| **77** | **Tomar `node._events[0]` sin filtrar por ID conocido** |

---

## Criterios de éxito (actualizados)

```
4H-P1     ✅  recovery inteligente por causa
4H-P2     ✅  policy hardening — bypass terminal causes
4I-P1     ✅  SAFETY_MODEL_G1.md
4I-P2     ✅  TRACEABILITY_MATRIX_G1.md
4I-P3     ✅  POLICY_CLARIFICATION_G1.md — DT-4F-003 cerrada
4J-P0     ✅  DT-4I-001 cerrada — governed TX-011 autosuficiente
4J-P1     ✅  minimum causal traceability SafetyEvent→SafetyAction→RecoveryEvent
4J-P2-prep ✅ trazabilidad ruta directa habilitada
DT-4G-004B 🔲 reaper/PID1 boring_noether
DT-4J-001  🔲 full native traceability
4J-P2      🔲 Extended Fault Injection Matrix
```

---

*G1 Deterministic Safety Runtime — Tesis de Etapas v27*
*Actualizado: 2026-06-22*
*3C ✅ | 4A–4I ✅ | 4J 🔄 (P0✅ P1✅ P2-prep✅) | 5A 🔒*
