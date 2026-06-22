# Tesis de Etapas del Proyecto — Runtime Architecture para Humanoide G1
## Versión 26 — Actualizada 2026-06-21 (4I cerrada — formalización completa)

> **Nota de versión (v26):** cambios respecto a v25 —
> (1) **4I CERRADA**: SAFETY_MODEL_G1.md (4I-P1), TRACEABILITY_MATRIX_G1.md (4I-P2), POLICY_CLARIFICATION_G1.md (4I-P3).
> (2) DT-4E-001 cerrada. DT-4F-003 cerrada. DT-4I-001 abierta (discrepancia TX-011 governed recovery).
> (3) README actualizado: 4I ✅, badge actualizado, referencias a docs/audit/.
> (4) CI Build ✅ CI Audit ✅ post-4I-P5.

---

## Etapa 1 — Infraestructura Base — ✅ Cerrada
## Etapa 2 — Disciplina Operacional — ✅ Cerrada
## Etapa 3 — Safety Runtime Architecture — ✅ Cerrada

### 3A — Modelos Semánticos + ADRs — ✅ Cerrada
> ⚠️ DT-4E-001: SAFETY_MODEL_G1.md ausente en VM — recrear en 4I.

### 3B — Skeleton Runtime ROS2 — ✅ Cerrada
### 3C — Level 4 Runtime Validation — ✅ Cerrada
65 tests total (63 orchestrator + 2 launch integration), CI green.
TX-001→TX-011 auditables en `docs/audit/TRANSITION_MATRIX_G1.md`.

---

## Etapa 4 — Simulación e Integración Runtime — 🔄 En progreso

### 4A — Infrastructure & DDS — ✅ Cerrada
### 4B — Isaac Headless Bring-up (4.2.0) — ✅ Cerrada
### 4C — Caracterización Física — ✅ Cerrada
### 4D — ROS2 Feasibility + Observabilidad + Lazo — ✅ Cerrada
### 4E — Baseline Sano + Validación — ✅ Cerrada
### 4F — Safety Runtime Enrichment — ✅ Cerrada
### Etapa 4G — Pipeline Hardening — ✅ CERRADA

(Ver v23 para detalles completos de P0→P5)

**Métricas validadas:**
```
t0→t1: media=2474ms (P3-C) / 2583ms (P4-D)
t1→t2: media=1.19ms (P4-D N=10) — ruta gobernada
```

---

### Etapa 4H — Recovery Inteligente — 🔄 En progreso

#### 4H-P1 — Recovery Inteligente por Causa — ✅ CERRADA (2026-06-19)

**Pregunta técnica:** ¿`recovery_g1` puede diferenciar la causa del evento safety y ejecutar una acción coherente por causa?

**Respuesta:** Sí. La causa llega a `recovery_g1` vía `msg.notes` en la ruta directa `_on_safety_event()`. El campo `notes` porta `rule_id=4F-P2-STALE/FREEZE/NANINF/TIMESTAMP` publicado por `watchdog_g1`. La ruta gobernada `_on_safety_action()` no se modificó — TX-011 representa caída física y ya ejecuta `stabilization_mode`.

**Gap confirmado por auditoría:**
- `SafetyAction` no transporta causa — el orchestrator la pierde al convertir `SafetyEvent → SafetyAction`.
- `_dispatch_recovery()` no leía `notes` — todo `CONDITION_DETECTED` caía en `else → operator_intervention`.

**Implementación (solo `recovery_g1.py`):**

```python
def _extract_rule_id(self, notes: str) -> str:
    """Defensivo: tolera None y vacío."""
    notes = notes or ''
    for token in notes.split():
        if token.startswith('rule_id='):
            return token.split('=', 1)[1]
    return ''
```

Mapa causal implementado en `_dispatch_recovery()`:

| Causa | Señal | Acción | Ruta |
|---|---|---|---|
| Caída física | TX-011 gobernada | stabilization_mode | `_on_safety_action()` — intacto |
| Caída directa fallback | source=cross_consistency_observer | wait_for_primary_restore | directa |
| STALE | rule_id=4F-P2-STALE | wait_for_primary_restore | directa |
| FREEZE | rule_id=4F-P2-FREEZE | operator_intervention | directa |
| NANINF | rule_id=4F-P2-NANINF | operator_intervention | directa |
| TIMESTAMP | rule_id=4F-P2-TIMESTAMP | operator_intervention | directa |

**Validación:**

| Observable | Evidencia | Resultado |
|---|---|---|
| fallen directa | `[4H-P1] cause=fallen route=direct_fallback` | ✅ |
| TX-011 gobernada intacta | `ORCH_ACTION→RECOVERY tx=TX-011` | ✅ |
| STALE | `[4H-P1] cause=STALE target=/g1/imu action=wait_for_primary_restore` | ✅ |
| FREEZE | `[4H-P1] cause=FREEZE target=/g1/imu action=operator_intervention` | ✅ |
| NANINF | `[4H-P1] cause=NANINF target=/g1/imu action=operator_intervention` | ✅ |
| TIMESTAMP | harness ejecutado, pendiente confirmación formal | ⚠️ |
| 65 tests | 65/65 PASS | ✅ |

**Método de validación:** harnesses externos no invasivos — publican estímulos ROS2 reales sin tocar código productivo. Cadena completa: `harness → topic → watchdog → SafetyEvent → recovery → log [4H-P1]`.

**Limitaciones declaradas:**
- Acción para caída directa (`wait_for_primary_restore`) es semánticamente débil — la acción correcta de caída física va por TX-011. El fallback directo queda auditado.
- STALE de startup ("sin mensaje nunca recibido") es ruido — evidencia principal es STALE post-warmup con 1.39s de silencio.

**Commit:** `5005788`

---

#### 4H-P2 — Recovery Policy Hardening — ✅ CERRADA (2026-06-19)

**Pregunta técnica:** ¿La capa `recovery_g1` tiene una política mínima explícita y defendible para manejar prioridades, cooldowns, escalamiento, eventos simultáneos y fallback directo sin ambigüedad operacional?

**Respuesta:** Sí, con un gap corregido. La auditoría encontró que causas terminales (FREEZE/NANINF/TIMESTAMP) consumían retry counter y quedaban bloqueadas por cooldown entre notificaciones consecutivas — comportamiento incorrecto para causas que siempre requieren intervención del operador.

**Gap confirmado por auditoría:** en `_dispatch_recovery()`, todo event pasaba por el bloque cooldown/escalation antes del mapeo causal. Un segundo FREEZE del mismo target dentro de 5s era silenciado por "Cooldown activo". STALE posterior podía quedar contaminado por el counter del FREEZE.

**Implementación (solo `recovery_g1.py`):**
- Constante global `TERMINAL_MANUAL_RULE_IDS = {'4F-P2-FREEZE', '4F-P2-NANINF', '4F-P2-TIMESTAMP'}`
- Bypass antes de cooldown/escalation en `_dispatch_recovery()`: si `rule_id ∈ TERMINAL_MANUAL_RULE_IDS` → `operator_intervention` inmediato, return, sin tocar `_retry_counters` ni `_last_attempt_time`
- attempt=1 fijo para terminales con comentario explícito

**Política mínima post-4H-P2:**

| Causa | Acción | Tipo | Cooldown | Escalación |
|---|---|---|---|---|
| Caída física (TX-011) | stabilization_mode | REC-AUTO | dedup 5s | N/A |
| Caída directa fallback | wait_for_primary_restore | REC-AUTO | RETRY_COOLDOWN_S | MAX_AUTO_RETRIES |
| STALE | wait_for_primary_restore | REC-AUTO | RETRY_COOLDOWN_S | MAX_AUTO_RETRIES |
| FREEZE | operator_intervention | REC-MANUAL | ninguno | ninguna |
| NANINF | operator_intervention | REC-MANUAL | ninguno | ninguna |
| TIMESTAMP | operator_intervention | REC-MANUAL | ninguno | ninguna |

**Simultaneidad:** single-flight `_recovery_active` — first accepted wins. Documentado, no rediseñado.

**Validación focal PASS:**

| Observable | Evidencia | Resultado |
|---|---|---|
| FREEZE #1 bypass | `[4H-P2] cause=FREEZE terminal=True` | ✅ |
| FREEZE #2 <5s sin cooldown | segundo `[4H-P2]` sin "Cooldown activo" | ✅ |
| STALE post-FREEZE sin contaminación | `[4H-P1] cause=STALE attempt=1` | ✅ |
| 65 tests | 65/65 PASS | ✅ |

**Commit:** pendiente

---

#### 4I-P1 — SAFETY_MODEL_G1.md — ✅ CERRADA (2026-06-21)

Cierra DT-4E-001. Documento formal de contrato de seguridad: 12 secciones, auditado desde código real. DT-4I-001 abierta: discrepancia ruta gobernada TX-011.

#### 4I-P2 — TRACEABILITY_MATRIX_G1.md — ✅ CERRADA (2026-06-21)

9 filas fault→detector→ruta→recovery→evidencia. Sin evidencia inventada. RATE y direct fallback declarados como limitaciones.

#### 4I-P3 — POLICY_CLARIFICATION_G1.md — ✅ CERRADA (2026-06-21)

TX-009, single-flight, governed vs direct, terminal causes, cooldown/retry — como contrato escrito. Cierra DT-4F-003.

#### 4I-P4/P5 — Verificación + Gate — ✅ CERRADAS (2026-06-21)

Cobertura de limitaciones verificada. README actualizado. CI verde.

---

### Etapa 4I — Formalización — ✅ CERRADA
### Etapa 4J — Paper Prep — 🔲 Pendiente
### Etapa 5A — Isaac Lab — 🔒 Bloqueada (GPU ≥ RTX 4080)

---

## Roadmap Post-4H

```
4I-P1   Contrato semántico formal (recrear SAFETY_MODEL_G1.md)
4I-P2   Assurance case
4J-P1   Fault injection matrix extendida
DT-4G-004B  Resolver reaper/PID1 (--init flag boring_noether)
```

---

## Criterios de éxito (actualizados)

```
4F-P1→P6  ✅  cerrados
4G-P0→P5  ✅  cerrados
DT-4G-004A ✅ teardown activo, sin docker restart entre corridas normales
4H-P1     ✅  recovery inteligente por causa
4H-P2     ✅  policy hardening — bypass terminal causes
4I-P1     ✅  SAFETY_MODEL_G1.md recreado
4I-P2     ✅  TRACEABILITY_MATRIX_G1.md
4I-P3     ✅  POLICY_CLARIFICATION_G1.md — DT-4F-003 cerrada
4I-P1     🔲  SAFETY_MODEL_G1.md recreado
DT-4G-004B 🔲 reaper/PID1 boring_noether
```

---

## Matriz de Transiciones — Estado al Cierre 4H

| TX | Tipo | Estado | Validado |
|---|---|---|---|
| TX-001 | CRITICAL_INTERRUPT | PRIMARY → stabilization_mode | ✅ 3C tests |
| TX-002 | NORMAL | SAFE→CAUTION | ✅ 3C tests |
| TX-003 | NORMAL | DANGER→STABILITY_RISK | ✅ 3C tests |
| TX-004 | NORMAL | STABILITY_RISK→FAULT_CRITICAL | ✅ 3C tests |
| TX-005 | COMMIT_TERMINAL | FAULT_CRITICAL→torque_release | ✅ 3C tests |
| TX-006a/b/c | RECOVERY | recovery desde FAULT_CRITICAL/STABILITY_RISK/DANGER | ✅ 3C tests |
| TX-007 | NORMAL | CAUTION→DANGER | ✅ 3C tests |
| TX-008 | CRITICAL_INTERRUPT | SAFE→STABILITY_RISK directo | ✅ 3C tests |
| TX-009 | POLICY_GATED | emergency_sit | ✅ 3C tests |
| TX-010 | RECOVERY | CAUTION→SAFE | ✅ 3C tests |
| TX-011 | NORMAL | SECONDARY/fallen→STABILITY_RISK/R3 | ✅ N=13 P2-C + N=10 P4-D + 4H-P1 |

---

## Deuda Técnica Activa

| ID | Deuda | Prioridad |
|---|---|---|
| DT-4E-001 | SAFETY_MODEL_G1.md ausente | Alta | ✅ CERRADA 4I-P1 |
| DT-4E-006 | Control PD diferido | Alta |
| DT-4F-001 | Thresholds pragmáticos | Media |
| DT-4F-002 | TX-006b/c sin test explícito | Media |
| DT-4F-003 | TX-009 POLICY_GATED exacta | Baja |
| DT-4F-004 | FREEZE IMU falso positivo potencial | Media |
| DT-4G-002 | t1→t2 correlación por UUID/event_id (paper) | Media |
| DT-4G-004A | Teardown activo contenedor | ✅ CERRADA |
| DT-4I-001 | Discrepancia TX-011 governed recovery: orchestrator emite stabilization_mode, recovery dispatch → operator_intervention | Alta |
| **DT-4G-004B** | **Zombies `<defunct>` por PID1/reaper** | **Baja** |

---

## Anti-Patterns Clave (acumulados)

| # | Anti-pattern |
|---|---|
| 54 | Reconstruir docker run de memoria |
| 63 | No verificar sintaxis antes de copiar al contenedor |
| 64 | `colcon build --symlink-install` para build portable |
| 66 | Diseñar TX desde texto de informe, no código real |
| 67 | Tocar runtime safety para que pase un test de CI |
| 68 | Test de estado inicial con launch completo |
| 69 | Dedup de safety action por transition_id permanente |
| 70 | Corridas formales sin preflight limpio |
| 71 | N≥10 en loop sin limpiar contenedor |
| **72** | **Editar archivos críticos con str.replace/heredoc sin verificar encoding primero** |
| **73** | **Mezclar dos causas en un solo harness de validación** |
| **74** | **Correr harness antes de que el subscriber esté activo** |

---

*G1 Deterministic Safety Runtime — Tesis de Etapas v25*
*Actualizado: 2026-06-19*
*3C ✅ | 4A–4H ✅ | 4I ✅ | 4J 🔲 | 5A 🔒*
