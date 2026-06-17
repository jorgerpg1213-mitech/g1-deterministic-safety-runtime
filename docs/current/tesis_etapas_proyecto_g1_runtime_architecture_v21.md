# Tesis de Etapas del Proyecto — Runtime Architecture para Humanoide G1
## Versión 21 — Actualizada 2026-06-17 (4G-P2-B cerrada)

> **Nota de versión (v21):** cambios respecto a v20 —
> (1) **4G-P2-B CERRADA**: ruta directa observer→recovery N=10, 100% PASS, latencia 1–156ms.
> (2) Launcher extendido: Terminal E orchestrator, `RUN_WINDOW_S=90`, 4 nodos, 8 topics.
> (3) Hallazgo arquitectónico formal: mismatch doble `event_type` + `source_authority` bloquea ruta gobernada.
> (4) Deuda DT-4G-001 añadida: TX-011 escalación gobernada SECONDARY/fallen.
> (5) Próximo: 4G-P2-C (TX-011 diseño + implementación).

---

## Etapa 1 — Infraestructura Base — ✅ Cerrada
## Etapa 2 — Disciplina Operacional — ✅ Cerrada
## Etapa 3 — Safety Runtime Architecture — ✅ Cerrada

### 3A — Modelos Semánticos + ADRs — ✅ Cerrada
> ⚠️ DT-4E-001: SAFETY_MODEL_G1.md ausente en VM — recrear en 4I.

### 3B — Skeleton Runtime ROS2 — ✅ Cerrada
### 3C — Level 4 Runtime Validation — ✅ Cerrada
86 tests Level 4, CI green. TX-001→TX-010 auditables en `docs/audit/TRANSITION_MATRIX_G1.md`.

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

---

#### 4G-P2-B — Reproducibilidad Caída Inducida + t1→t2 — ✅ CERRADA (2026-06-17)

**Clasificación:** PASS parcial — ruta directa probada; ruta gobernada bloqueada por contrato.

**Cambios de config:**
- `RUN_WINDOW_S`: 30→90 (caída a t=54.67s desde SET, entra a ~42s dentro de ventana)
- Terminal E: `safety_orchestrator_g1` añadido al launcher
- Nodos verificados: 4 (añadido `/safety_orchestrator_g1`)
- Topics verificados: 8 (añadidos `/system_state`, `/safety_actions`)

**Commits:** `497f0a4`, `86a32c6`

**Hallazgo arquitectónico — mismatch doble de contrato:**
```
Observer emite:   event_type=CONDITION_DETECTED, source_authority=SECONDARY
TX-001 exige:     event_type∈{STABILITY_ANOMALY,...}, source_authority∈{PRIMARY_IMU,...}
Resultado:        orchestrator ACKea pero no escala → no hay /system_state → no hay ruta gobernada
```

El orchestrator SÍ funciona (recibe eventos, publica ACK al topic). El silencio en `E_orchestrator.log` se debe a que el ACK va al topic `/safety_events`, no a stdout.

**Resultados N=10:**
| Métrica | Valor |
|---|---|
| FALL_TRIGGER it=450 | 100% (10/10) |
| Observer CRITICAL | 100% (10/10) |
| Recovery reacción (ruta directa) | 100% (10/10) |
| t1→t2 ruta directa | 1.3–156ms |
| FP antes del trigger | 0 |
| INVALID/INFRA | 4 (timeout nodos, no falla detección) |
| PASS rate formal | 100% |

**Validado:**
- Caída inducida determinista: it=450, t=54.67s ✅
- Ruta directa observer→recovery: reproducible, rápida ✅
- Orchestrator vivo y conectado ✅

**NO validado:**
- Ruta gobernada observer→orchestrator→recovery (DT-4G-001/TX-011) ❌

---

#### 4G-P2-C — TX-011 Escalación Gobernada SECONDARY/fallen — 🔲 Pendiente

**Objetivo:** crear transición explícita para `SECONDARY + STABILITY_ANOMALY/fallen/no-support` en la matriz TX del orchestrator, habilitando la ruta gobernada completa.

**Restricciones:**
- No cambiar observer a PRIMARY (semánticamente incorrecto)
- Diseño aprobado por PM antes de implementar
- Tests Level 4 antes del piloto
- Piloto antes de N≥10

#### 4G-P3 — t0→t1 Clock Sync Isaac↔ROS2 — 🔲 Pendiente

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
4G-P2-C   🔲  ruta gobernada TX-011
4G-P3     🔲  t0→t1 medido
4H-P1     🔲  recovery inteligente
4I-P1     🔲  SAFETY_MODEL_G1.md recreado
4E-P5     🔲  control activo PD (diferido)
5A        🔒  Isaac Lab fuera del T4
```

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
| **DT-4G-001** | **TX-011: escalación gobernada SECONDARY/fallen pendiente** | **Alta** |

---

*G1 Deterministic Safety Runtime — Tesis de Etapas v21*
*Actualizado: 2026-06-17*
*3C ✅ | 4A–4F ✅ | 4G-P0 ✅ | 4G-P1 ✅ | 4G-P2-A ✅ | 4G-P2-B ✅ | 4G-P2-C 🔲 | 5A 🔒*
