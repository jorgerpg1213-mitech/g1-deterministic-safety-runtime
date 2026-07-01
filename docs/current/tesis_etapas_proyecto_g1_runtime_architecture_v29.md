# Tesis de Etapas del Proyecto — Runtime Architecture para Humanoide G1
## Versión 29 — Actualizada 2026-06-25 (4J-P4-A y P4-B cerradas)

> **Nota de versión (v29):** cambios respecto a v28 —
> (1) **4J-P4-A CERRADA**: Threshold Inventory. 20+ constantes extraídas del código. H1–H5 documentados. `docs/audit/4J_THRESHOLD_CHARACTERIZATION.md` commitado.
> (2) **4J-P4-B CERRADA**: Negative Control PASS. 0 critical SafetyEvents, 0 terminal RecoveryEvents, 60s observación formal. Commit `04d3983`.
> (3) **Topología IMU dual**: watchdog_g1→`/g1/imu`; observer→`/imu`. Anti-pattern #83 registrado.
> (4) **DT-4F-001** actualizada a `partially characterized`. **DT-4F-004** diferida a P4-E.
> (5) HEAD: `04d3983` — CI Build ✅ CI Audit ✅ — 65/65 PASS 0 skipped.

---

## Etapa 1 — Infraestructura Base — ✅ Cerrada
## Etapa 2 — Disciplina Operacional — ✅ Cerrada
## Etapa 3 — Safety Runtime Architecture — ✅ Cerrada
## Etapas 4A–4I — ✅ Cerradas (ver v28 para detalles)

---

## Etapa 4J — Paper Prep — 🔄 EN PROGRESO

#### 4J-P0 a P3 — ✅ CERRADAS (ver v28 para detalles)

---

#### 4J-P4-A — Threshold Inventory — ✅ CERRADA (2026-06-25)

**Principio PM:** inventory-first — extraer thresholds reales del código, no de memoria ni documentación vieja.

**Fuentes auditadas:** cross_consistency_observer, watchdog_g1, safety_orchestrator_g1, recovery_g1.

**Threshold inventory resumido:**

| Familia | Constante clave | Valor | Evidence |
|---|---|---|---|
| F1 Observer abs_w | FALLEN_W_CRITICAL / FALLEN_W_WARN | 0.80 / 0.85 | E3 / E1 |
| F2 Observer contacto | FALLEN_CONSECUTIVE_N / FRESH_MAX_AGE_S | 3 / 0.5s | E3 / E1 |
| F3 Watchdog STALE | STALE_TIMEOUT_S / STALE_CRITICAL_S / STARTUP_GRACE_S | 1.0s / 3.0s / 15.0s | E4 / E3 / E1 |
| F4 Watchdog FREEZE | FREEZE_N / NO_FREEZE_TOPICS | 5 / {contacts} | E4 / E1 |
| F5 Watchdog NANINF | isnan/isinf (boolean) | — | E4 |
| F6 Watchdog TIMESTAMP | stamp < prev_stamp | — | E4 |
| F7 Watchdog RATE | MIN_RATE_HZ / RATE_WINDOW_S / RATE_WARMUP_N | 3.0Hz / 2.0s / 5 | E2 / E1 |
| Recovery R2/R3 | MAX_AUTO_RETRIES / RETRY_COOLDOWN_S | 3 / 5.0s | E4 |

**Hallazgos estructurales H1–H5:**
- H1: WARN/INFO del observer nunca publican SafetyEvent
- H2: FALLEN_CONSECUTIVE_N=3 gate de debounce exclusivo de CRITICAL
- H3: Observer emite STABILITY_RISK+NONE hardcodeados
- H4: STALE tiene dos caminos de severidad (E4 vs E3)
- H5: WAIT_FOR_PRIMARY_MAX_S=30s nunca alcanzado (E1)

**Artifact:** `docs/audit/4J_THRESHOLD_CHARACTERIZATION.md`
**DT-4F-001:** `partially characterized`
**DT-4F-004:** characterized, diferido a P4-E

---

#### 4J-P4-B — Negative Control — ✅ CERRADA (2026-06-25)

**Principio PM:** baseline sano no debe generar CRITICAL SafetyEvents ni terminal RecoveryEvents.

**Diseño:** datos sintéticos sanos en 6 topics (`/g1/imu`, `/imu`, `/g1/contact/left`, `/g1/contact/right`, `/joint_states`, `/g1/base_pose`). Jitter modular (step=0.001) previene FREEZE_N=5.

**Hallazgo de topología:** watchdog_g1 suscribe `/g1/imu`; cross_consistency_observer suscribe `/imu`. Harness publica en ambos. Anti-pattern #83 registrado.

**Launcher:** `sim_runtime/4J/run_p4b.sh` — preflight, trap cleanup, time guard, cleanliness gate pre-Phase-3, postflight.

**Resultado:**
```
topology OK (4/4 checks)
cleanliness gate: CLEAN
Phase 3 (60s): completada
critical_risk SafetyEvents: 0
terminal RecoveryEvents:    0
VERDICT: PASS
```

**Limitaciones:**
- Jitter modular — baseline activo; IMU frozen diferido a P4-E
- Postflight residual nodes → DT-4G-004B (no invalida resultado)

**Harness:** `sim_runtime/4J/harness_4J_P4B_negative_control.py`
**Evidencia:** `evidence/4J/P4_THRESHOLDS/negative_control/`
**Commit:** `04d3983`

---

#### 4J-P4-C — Positive Controls — 🔲 PENDIENTE
#### 4J-P4-D — Boundary Sweep — 🔲 PENDIENTE
#### 4J-P4-E — False Positive Analysis — 🔲 PENDIENTE
#### 4J-P4-F — Report / Debt — 🔲 PENDIENTE
#### 4J-P5 — Assurance Case + Paper Package — 🔲 PENDIENTE

---

## Deuda Técnica Activa

| ID | Deuda | Prioridad | Estado |
|---|---|---|---|
| DT-4E-006 | Control PD diferido | Alta | Abierta |
| DT-4F-001 | Thresholds pragmáticos | Media | **Partially characterized — P4-A; boundary sweep pendiente P4-D** |
| DT-4F-002 | TX-006b/c sin test explícito | Media | Abierta |
| DT-4F-004 | FREEZE IMU falso positivo potencial | Media | **Characterized (P4-A); diferido a P4-E** |
| DT-4G-002 | t1→t2 UUID paper-grade | Media | Parcial — 4J-P1 |
| DT-4G-004B | Zombies `<defunct>` por PID1/reaper | Baja | Abierta, confirmada P4-B |
| DT-4J-001 | Full native traceability | Media | Abierta |

---

## Anti-Patterns Clave (acumulados)

| # | Anti-pattern |
|---|---|
| 54–78 | Ver v28 |
| 79 | Asignar método logger dinámicamente en ROS2 |
| 80 | Asumir campo de mensaje sin verificar .msg file |
| 81 | kill $PID no mata procesos dentro del contenedor |
| 82 | clear_observation() no resetea estado del runtime |
| **83** | **Publicar solo /g1/imu asumiendo que observer también lo recibe** |

---

## Criterios de éxito (actualizados)

```
4J-P0 through P3   ✅  (ver v28)
4J-P4-A            ✅  threshold inventory — 20+ constantes, H1–H5
4J-P4-B            ✅  negative control PASS — 0 critical, 0 terminal, 60s
DT-4G-004B         🔲  reaper/PID1 boring_noether
DT-4J-001          🔲  full native traceability
4J-P4-C            🔲  positive controls
4J-P4-D            🔲  boundary sweep
4J-P4-E            🔲  false positive matrix (incluye FREEZE IMU frozen)
4J-P4-F            🔲  reporte final y deuda
4J-P5              🔲  assurance case + paper package
```

---

*G1 Deterministic Safety Runtime — Tesis de Etapas v29*
*Actualizado: 2026-06-25*
*3C ✅ | 4A–4I ✅ | 4J 🔄 (P0✅ P1✅ P2-prep✅ P2-A✅ P3✅ P4-A✅ P4-B✅) | 5A 🔒*
