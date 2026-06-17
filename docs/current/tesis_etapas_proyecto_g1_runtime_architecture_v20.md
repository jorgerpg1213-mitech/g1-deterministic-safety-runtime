# Tesis de Etapas del Proyecto — Runtime Architecture para Humanoide G1
## Versión 20 — Actualizada 2026-06-17 (4G-P0+P1+P2-A cerradas)

> **Nota de versión (v20):** cambios respecto a v19 —
> (1) **4G-P0 CERRADA**: dependencia repo viejo eliminada. Build portable sin `--symlink-install`. CI hardening.
> (2) **4G-P1 CERRADA**: launcher unificado `launch_pipeline.py`. Preflight 7/7, señal objetiva, teardown robusto.
> (3) **4G-P2-A CERRADA**: reproducibilidad baseline sano N=10, 100% PASS, 0 FP. Analizador `analyze_runs.py`.
> (4) DT-4D-017 CERRADA: g1_msgs migrado + launcher implementado.
> (5) Próximo: 4G-P2-B (caída inducida), 4G-P3 (t0→t1).

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

**Resultado:** P2 + z_cmd=0.720 + drives fábrica = robot sano pasivo. Observer sin falsos positivos. Transición sano→caída capturada. PD activo diferido (DT-4E-006).

---

### Etapa 4F — Safety Runtime Enrichment — ✅ CERRADA (2026-06-16)

**P1 ✅** Observer severidad INFO/WARN/CRITICAL.
**P2 ✅** Watchdog STALE/FREEZE/NANINF/TIMESTAMP/RATE.
**P3 ✅** TRANSITION_MATRIX_G1.md — TX-001→TX-010.
**P4 ✅** Pipeline end-to-end 4 componentes.
**P5 ✅** Latencia t1→t2: 0.68–8.2ms en T4.
**P6 ✅** Fault injection matrix 5/5 PASS.

---

### Etapa 4G — Pipeline Hardening — 🔄 En progreso

#### 4G-P0 — Sanity Repo Nuevo / Runtime Paths — ✅ CERRADA (2026-06-17)

**Hallazgos:**
- `boring_noether` montaba repo viejo → recreado con mount correcto
- `colcon build --symlink-install` generaba symlinks no portables para Isaac → rebuild sin flag
- PYTHONPATH de Isaac faltaba bridge rclpy → `FootContact` no importable → corregido
- CI Build colgado en pull Docker Hub → timeout 25min + retry 3x

**Criterio PASS cumplido:**
- `/ws` → repo nuevo ✅
- g1_msgs portables (sin symlinks) ✅
- FootContact importable en Isaac ✅
- Build limpio 7/7 ✅
- CI Build + Audit verdes ✅
- DT-4D-017 frente g1_msgs: CERRADO ✅

**Commits:** `4907627`, `624d7e1`

---

#### 4G-P1 — Launcher Unificado — ✅ CERRADA (2026-06-17)

**Implementación:** `sim_runtime/4G/launch_pipeline.py` — Python host-side.

**Flujo:** preflight 7 checks → metadata completa → Isaac → esperar `P2+z0.720 SET` → Isaac alive check → B/C/D → verificar 3 nodos + 6 topics + procesos + Isaac → ventana 30s → post-ventana → teardown robusto.

**Fixes durante validación:**
- Shutdown idempotente en extensión Isaac: `if rclpy.ok(): rclpy.shutdown()`
- `isaac_ok=True/False` explícito en resumen PASS/FAIL

**Resultados validación (2 corridas):**
| Corrida | t_marker | t_bcd | t_total | isaac_ok | FP |
|---|---|---|---|---|---|
| 20260617_122311 | 36s | 13s | 49s | True | 0 |
| 20260617_124821 | 36s | 12s | 49s | True | 0 |

**Commits:** `715d362`, `7a604ab`

---

#### 4G-P2-A — Reproducibilidad Baseline Sano — ✅ CERRADA (2026-06-17)

**Protocolo:** N≥10 corridas de baseline sano, launcher congelado, sin caída inducida.

**Analizador:** `sim_runtime/4G/analyze_runs.py` con filtro `--since`.

**Criterios de invalidación:**
1. `false_positive_count_total > 0` → INVALID
2. `recovery_reaction_count > 0` → INVALID

**Resultados:**
```
N=10 corridas formales PASS (1 abort pre-protocolo excluido con --since)
PASS rate: 100%
FP observer: 0 | FP watchdog: 0 | Recovery reacciones: 0
```

| Métrica | min | media | std | max | p95 |
|---|---|---|---|---|---|
| t Isaac→marker (s) | 34.0 | 35.4 | 1.0 | 36.0 | 36.0 |
| t marker→B/C/D (s) | 12.0 | 12.5 | 0.5 | 13.0 | 13.0 |
| t total→PASS (s) | 47.0 | 48.4 | 1.0 | 49.0 | 49.0 |

**Commit:** `ce9b715`

---

#### 4G-P2-B — Reproducibilidad Caída Inducida + t1→t2 — 🔲 Pendiente

- Diseñar protocolo de caída reproducible antes de correr.
- Medir t1→t2 con N≥10.
- No mezclar con P2-A (variables separadas).

#### 4G-P3 — t0→t1 Clock Sync Isaac↔ROS2 — 🔲 Pendiente

- Definir t0 formalmente antes de medir.
- Opciones: Isaac FALL_TRIGGER it=450 / primer frame abs_w < umbral / primer cambio observable.
- No prometer número hasta tener diseño de clock sync.

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
4G-P2-B   🔲  reproducibilidad caída inducida N≥10
4G-P3     🔲  t0→t1 medido
4H-P1     🔲  recovery inteligente
4I-P1     🔲  SAFETY_MODEL_G1.md recreado
4E-P5     🔲  control activo PD (diferido)
5A        🔒  Isaac Lab fuera del T4
```

## Deuda Técnica Activa

| ID | Deuda | Prioridad |
|---|---|---|
| ~~DT-4D-017~~ | ~~Launcher; g1_msgs repo viejo~~ | CERRADA |
| DT-4E-001 | SAFETY_MODEL_G1.md ausente | Alta |
| DT-4E-006 | Control PD diferido | Alta |
| DT-4F-001 | Thresholds pragmáticos | Media |
| DT-4F-002 | TX-006b/c sin test explícito | Media |
| DT-4F-003 | TX-009 POLICY_GATED exacta | Baja |
| DT-4F-004 | FREEZE IMU falso positivo potencial | Media |
| DT-4F-005 | t0→t1 no medido | Alta |

---

*G1 Deterministic Safety Runtime — Tesis de Etapas v20*
*Actualizado: 2026-06-17*
*3C ✅ | 4A–4F ✅ | 4G-P0 ✅ | 4G-P1 ✅ | 4G-P2-A ✅ | 4G-P2-B 🔲 | 5A 🔒*
