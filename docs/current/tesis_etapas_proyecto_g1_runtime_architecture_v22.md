# Tesis de Etapas del Proyecto — Runtime Architecture para Humanoide G1
## Versión 22 — Actualizada 2026-06-18 (4G-P2-C cerrada)

> **Nota de versión (v22):** cambios respecto a v21 —
> (1) **4G-P2-C CERRADA**: TX-011 implementada, ruta gobernada observer→orchestrator→STABILITY_RISK/R3, N=13, 100% PASS.
> (2) Auditoría pre-implementación: 2 mismatches confirmados (no 3); `authority_effectiveness=EFFECTIVE` sí estaba seteado.
> (3) Decisión B1: TX-011 absorbe contrato real del observer sin tocar observer ni TX-001.
> (4) Crisis CI resuelta: separación test estado inicial (orchestrator-only) vs visibilidad (launch completo).
> (5) DT-4G-001 cerrada. DT-4G-002, DT-4G-003 añadidas.
> (6) Anti-patterns #66, #67, #68 documentados.
> (7) Próximo: 4G-P3 (t0→t1 clock sync Isaac↔ROS2).

---

## Etapa 1 — Infraestructura Base — ✅ Cerrada
## Etapa 2 — Disciplina Operacional — ✅ Cerrada
## Etapa 3 — Safety Runtime Architecture — ✅ Cerrada

### 3A — Modelos Semánticos + ADRs — ✅ Cerrada
> ⚠️ DT-4E-001: SAFETY_MODEL_G1.md ausente en VM — recrear en 4I.

### 3B — Skeleton Runtime ROS2 — ✅ Cerrada
### 3C — Level 4 Runtime Validation — ✅ Cerrada
63 tests Level 4 orchestrator + 2 tests launch integration, CI green.
TX-001→TX-011 auditables en `docs/audit/TRANSITION_MATRIX_G1.md`.

---

## Etapa 4 — Simulación e Integración Runtime — 🔄 En progreso

### 4A — Infrastructure & DDS — ✅ Cerrada
### 4B — Isaac Headless Bring-up (4.2.0) — ✅ Cerrada
### 4C — Caracterización Física — ✅ Cerrada
### 4D — ROS2 Feasibility + Observabilidad + Lazo — ✅ Cerrada
### 4E — Baseline Sano + Validación — ✅ Cerrada
### 4F — Safety Runtime Enrichment — ✅ Cerrada

---

### Etapa 4G — Pipeline Hardening — 🔄 En progreso

#### 4G-P0 — Sanity Repo Nuevo / Runtime Paths — ✅ CERRADA
#### 4G-P1 — Launcher Unificado — ✅ CERRADA
#### 4G-P2-A — Reproducibilidad Baseline Sano — ✅ CERRADA
#### 4G-P2-B — Reproducibilidad Caída Inducida + t1→t2 — ✅ CERRADA (PASS parcial)

---

#### 4G-P2-C — TX-011 Escalación Gobernada SECONDARY/fallen — ✅ CERRADA (2026-06-18)

**Clasificación:** PASS completo — ruta gobernada operativa N=13.

**Auditoría pre-implementación:**
- 2 mismatches confirmados entre observer y TX-001:
  - `event_type`: `CONDITION_DETECTED` vs `STABILITY_ANOMALY/...`
  - `source_authority`: `SECONDARY` vs `PRIMARY_IMU/PRIMARY_JOINT_STATES`
- `authority_effectiveness=EFFECTIVE` sí estaba seteado en observer — no es mismatch.
- `risk_level` del evento no disponible en `TransitionEvaluator` sin cambiar firma general — no usado como guard.

**Decisión de diseño: B1**
TX-011 absorbe contrato real del observer. No se toca observer, no se toca TX-001.

**Contrato TX-011:**
```
event_type           = 'CONDITION_DETECTED'
source_authority     = 'SECONDARY'
authority_eff        = 'EFFECTIVE'
estado_origen        ≠ ('STABILITY_RISK', 'R3')   ← guard anti-redisparo
→ stabilization_mode, STABILITY_RISK, R3, BEST_EFFORT, NORMAL
```

**Commits:** `b4064ea` (TX-011 + 3 tests), `07f9912` (fix CI tests)

**Crisis CI — resolución:**

El test `test_system_state_transient_local` levantaba 4 nodos (incluyendo observer). El observer podía disparar TX-011 durante el test, reemplazando el heartbeat INIT en el caché TRANSIENT_LOCAL. El test recibía `STABILITY_RISK/R3` en lugar de `SAFE/NONE/INIT`.

Resolución: separación en dos archivos por responsabilidad:
- `test_safety_layer_launch.py`: launch completo → solo visibilidad de `/system_state`
- `test_orchestrator_init_state.py`: launch orchestrator-only → valida INIT/SAFE/NONE

**Resultados N=13:**
| Métrica | Valor |
|---|---|
| FALL_TRIGGER it=450 | 100% (13/13) |
| Observer CRITICAL | 100% (13/13) |
| TX-011 ejecutada | 100% (13/13) |
| INVALID/INFRA | 1 (081655, preflight timeout) |
| PASS rate formal | 100% |

**Validado:**
- TX-011 ruta gobernada: observer→orchestrator→STABILITY_RISK/R3 ✅
- 63/63 tests Level 4 orchestrator ✅
- 2/2 tests launch integration ✅
- CI Build + Audit GREEN ✅

**NO validado:**
- Ruta gobernada orchestrator→recovery (DT-4G-003) ❌
- t0→t1 latencia física→observer (4G-P3 pendiente) ❌

---

#### 4G-P3 — t0→t1 Clock Sync Isaac↔ROS2 — 🔲 Pendiente

**Objetivo:** medir latencia entre evento físico en Isaac (t0) y publicación de SafetyEvent en ROS2 (t1). Requiere sincronización de relojes Isaac↔ROS2.

**Restricciones:**
- Diseño aprobado por PM antes de implementar
- Piloto antes de N≥10

---

### Etapa 4H — Recovery Inteligente — 🔲 Pendiente
### Etapa 4I — Formalización — 🔲 Pendiente
### Etapa 4J — Paper Prep — 🔲 Pendiente
### Etapa 5A — Isaac Lab — 🔒 Bloqueada (GPU ≥ RTX 4080)

---

## Criterios de éxito (actualizados)

```
4F-P1→P6  ✅  cerrados
4G-P0     ✅  repo nuevo, build portable, CI hardening
4G-P1     ✅  launcher unificado
4G-P2-A   ✅  reproducibilidad baseline sano N=10
4G-P2-B   ✅  reproducibilidad caída inducida N=10 (ruta directa)
4G-P2-C   ✅  TX-011 ruta gobernada N=13 100% PASS
4G-P3     🔲  t0→t1 medido
4H-P1     🔲  recovery inteligente
4I-P1     🔲  SAFETY_MODEL_G1.md recreado
4E-P5     🔲  control activo PD (diferido)
5A        🔒  Isaac Lab fuera del T4
```

---

## Matriz de Transiciones — Estado al Cierre P2-C

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
| **TX-011** | **NORMAL** | **SECONDARY/fallen→STABILITY_RISK/R3** | **✅ N=13 P2-C** |

---

## Deuda Técnica Activa

| ID | Deuda | Prioridad |
|---|---|---|
| DT-4E-001 | SAFETY_MODEL_G1.md ausente | Alta |
| DT-4E-006 | Control PD diferido | Alta |
| DT-4F-001 | Thresholds pragmáticos | Media |
| DT-4F-002 | TX-006b/c sin test explícito | Media |
| DT-4F-003 | TX-009 POLICY_GATED exacta | Baja |
| DT-4F-004 | FREEZE IMU falso positivo potencial | Media |
| DT-4F-005 | t0→t1 no medido | Alta |
| DT-4G-001 | TX-011 escalación gobernada SECONDARY/fallen | ✅ CERRADA |
| **DT-4G-002** | **t1→t2 correlación por UUID/event_id (paper)** | **Media** |
| **DT-4G-003** | **Ruta gobernada orchestrator→recovery no validada** | **Alta** |

---

## Anti-Patterns Clave (acumulados)

| # | Anti-pattern |
|---|---|
| 54 | Reconstruir docker run de memoria |
| 60 | Lanzar B/C/D antes de que Isaac esté listo |
| 63 | No verificar sintaxis antes de copiar al contenedor |
| 64 | `colcon build --symlink-install` para build portable |
| 65 | Cambiar `event_type` sin verificar `source_authority` en TX destino |
| 66 | Diseñar TX desde texto de informe, no desde código real |
| 67 | Tocar runtime safety para que pase un test de CI |
| 68 | Test de estado inicial con launch completo (4 nodos) |

---

*G1 Deterministic Safety Runtime — Tesis de Etapas v22*
*Actualizado: 2026-06-18*
*3C ✅ | 4A–4F ✅ | 4G-P0 ✅ | 4G-P1 ✅ | 4G-P2-A ✅ | 4G-P2-B ✅ | 4G-P2-C ✅ | 4G-P3 🔲 | 5A 🔒*
