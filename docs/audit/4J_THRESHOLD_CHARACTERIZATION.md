# 4J-P4-A — Threshold Characterization
## G1 Deterministic Safety Runtime

**Fase:** 4J-P4-A (Inventory-First)
**Fecha:** 2026-06-23
**HEAD:** 9777103
**Principio PM:** No threshold claim without falsification
**Workstream:** P4-A — Inventory (pre-harness)
**Estado:** INVENTORY COMPLETE — pendiente P4-B approval

---

## 1. Objetivo

Inventariar los thresholds activos en el runtime G1 extraídos directamente del código fuente. Sin modificar runtime. Sin cambiar valores. Sin ejecutar sweeps.

Primera pregunta científica respondida:
> ¿Cuáles son exactamente los thresholds activos hoy y qué claim sostiene cada uno?

Fuentes auditadas:
- `src/cross_consistency_observer/cross_consistency_observer/cross_consistency_observer.py`
- `src/watchdog_g1/watchdog_g1/watchdog_g1.py`
- `src/safety_orchestrator_g1/safety_orchestrator_g1/safety_orchestrator_g1.py`
- `src/recovery_g1/recovery_g1/recovery_g1.py`

---

## 2. Evidence Level Reference

| Nivel | Significado |
|---|---|
| E0 | Claim sin evidencia |
| E1 | Inspección de código |
| E2 | Harness simple |
| E3 | Harness focal con PASS/FAIL |
| E4 | N controlado |
| E5 | Matriz reproducible |
| E6 | Evidencia archivada paper-grade |

---

## 3. Threshold Inventory Table

### F1 — Observer: orientación IMU (abs_w)

| Rule | Node | Constant | Value | Source Line | Current Claim | Evidence Level | Related Debt |
|---|---|---|---|---|---|---|---|
| F1-FALLEN CRITICAL | cross_consistency_observer | `FALLEN_W_CRITICAL` | 0.80 | L80 | `abs_w < 0.80` → severidad CRITICAL (inclinación fuerte) | E3 (P2-A5 implicit) | DT-4F-001, DT-4D-016 |
| F1-FALLEN WARN | cross_consistency_observer | `FALLEN_W_WARN` | 0.85 | L81 | `0.80 <= abs_w < 0.85` → WARN; `abs_w >= 0.85` → INFO | **E1** (sin harness directo) | DT-4F-001, DT-4D-016 |

### F2 — Observer: consistencia de contacto

| Rule | Node | Constant | Value | Source Line | Current Claim | Evidence Level | Related Debt |
|---|---|---|---|---|---|---|---|
| F2-FALLEN both_lost | cross_consistency_observer | (boolean) | both feet lost | L345 | `both_lost` → CRITICAL inmediato | E3 (P2-A5) | DT-4F-001 |
| F2-FALLEN one_lost | cross_consistency_observer | (boolean) | one foot lost | L346 | `one_lost` → WARN; sin harness directo | **E1** | DT-4F-001 |
| F1/F2 debounce | cross_consistency_observer | `FALLEN_CONSECUTIVE_N` | 3 samples | L82 | SafetyEvent requiere 3 frames CRITICAL frescos consecutivos; WARN/INFO resetean contador | E3 (P2-A5 implicit) | DT-4F-001 |
| F1/F2 freshness gate | cross_consistency_observer | `FRESH_MAX_AGE_S` | 0.5 s | L78 | IMU + left + right deben tener age <= 0.5s; si no → contador = 0, sin evento | E1 | — |
| F2 anti-flood | cross_consistency_observer | `OBSERVER_MAX_PUBLISH_HZ` | 1.0 Hz | L74 | Máximo 1 SafetyEvent/s por par `imu_contact_support` | E1 | — |
| Observer rule_id | cross_consistency_observer | `rule_id` en notes | `'4F-P1'` | L382 (notes string) | No hay campo `msg.rule_id` dedicado — rule_id embebido en notas | E1 | DT-4J-001 |
| Observer authority | cross_consistency_observer | `source_authority` | `'SECONDARY'` | L370 | Observer no escala a orchestrator directamente | E1 | — |
| Observer risk hardcoded | cross_consistency_observer | `risk_level` | `'STABILITY_RISK'` | L377 | Siempre STABILITY_RISK independiente de severidad interna | E1 | DT-4F-001 |
| Observer restriction | cross_consistency_observer | `restriction_level` | `'NONE'` | L378 | Siempre NONE — routing no forzado por restriction | E1 | — |

### F3 — Watchdog: STALE

| Rule | Node | Constant | Value | Source Line | Current Claim | Evidence Level | Related Debt |
|---|---|---|---|---|---|---|---|
| F3-STALE onset | watchdog_g1 | `STALE_TIMEOUT_S` | 1.0 s | L39 | Topic sin mensaje > 1s → inicia evaluación STALE | E4 (P2-A1 N=3, P3 timing) | DT-4F-001 |
| F3-STALE CRITICAL inmediato | watchdog_g1 | `CRITICAL_STALE_TOPICS` | `{/g1/imu, /g1/contact/left, /g1/contact/right}` | L49 | IMU o cualquier contacto STALE → CRITICAL en primer ciclo de detección | E4 (P2-A1) | DT-4F-001 |
| F3-STALE escalation | watchdog_g1 | `STALE_CRITICAL_S` | 3.0 s | L40 | Tópicos no-críticos: WARN inicial → CRITICAL si `dur >= 3s` | **E3** (escalation path no aislada) | DT-4F-001 |
| F3 startup grace | watchdog_g1 | `STARTUP_GRACE_S` | 15.0 s | L45 | Sin evaluación STALE/FREEZE/RATE durante primeros 15s de arranque | E1 | — |

### F4 — Watchdog: FREEZE

| Rule | Node | Constant | Value | Source Line | Current Claim | Evidence Level | Related Debt |
|---|---|---|---|---|---|---|---|
| F4-FREEZE threshold | watchdog_g1 | `FREEZE_N` | 5 samples | L41 | Valor idéntico en 5 muestras consecutivas → WARN | E4 (P2-A2 N=10, P3 timing) | DT-4F-001, **DT-4F-004** |
| F4-FREEZE exclusión | watchdog_g1 | `NO_FREEZE_TOPICS` | `{/g1/contact/left, /g1/contact/right}` | L50 | Contactos excluidos de FREEZE check (binarios esperan repetición) | E1 | DT-4F-004 |

### F5 — Watchdog: NANINF

| Rule | Node | Constant | Value | Source Line | Current Claim | Evidence Level | Related Debt |
|---|---|---|---|---|---|---|---|
| F5-NANINF | watchdog_g1 | (boolean) | `isnan(v) or isinf(v)` | L56, L117, L141 | Cualquier NaN/inf en campos numéricos → CRITICAL inmediato | E4 (P2-A3 N=10, P3 timing) | — |

### F6 — Watchdog: TIMESTAMP

| Rule | Node | Constant | Value | Source Line | Current Claim | Evidence Level | Related Debt |
|---|---|---|---|---|---|---|---|
| F6-TIMESTAMP | watchdog_g1 | (boolean) | `stamp < prev_stamp` | L120 | Timestamp regresivo → WARN inmediato | E4 (P2-A4 N=10, P3 timing) | DT-4F-001 |

### F7 — Watchdog: RATE

| Rule | Node | Constant | Value | Source Line | Current Claim | Evidence Level | Related Debt |
|---|---|---|---|---|---|---|---|
| F7-RATE threshold | watchdog_g1 | `MIN_RATE_HZ` | 3.0 Hz | L42 | Tasa efectiva < 3Hz → WARN | **E2** (P2-A6 declared limitation) | DT-4F-001, DT-4F-002 |
| F7-RATE window | watchdog_g1 | `RATE_WINDOW_S` | 2.0 s | L43 | Ventana de cálculo de tasa efectiva | E1 | DT-4F-001 |
| F7-RATE warmup | watchdog_g1 | `RATE_WARMUP_N` | 5 msgs | L44 | Evaluación de RATE diferida hasta 5 mensajes recibidos | E1 | — |

### Orchestrator — thresholds de routing

| Rule | Node | Constant | Value | Source Line | Current Claim | Evidence Level | Related Debt |
|---|---|---|---|---|---|---|---|
| Arbitration timeout | safety_orchestrator_g1 | `ARBITRATION_PENDING_TIMEOUT_S` | 5.0 s | L53 | Sin resolución en 5s → escala ARBITRATION_PENDING | E1 | — |

> Nota: el orchestrator no tiene thresholds de detección propios. Enruta por `risk_level`/`restriction_level` provenientes de detectores upstream (watchdog_g1, cross_consistency_observer).

### Recovery — thresholds que afectan rutas R2/R3

| Rule | Node | Constant | Value | Source Line | Current Claim | Evidence Level | Related Debt |
|---|---|---|---|---|---|---|---|
| R2 retry limit | recovery_g1 | `MAX_AUTO_RETRIES` | 3 | L50 | Tras 3 intentos auto-recovery → `request_operator_intervention` | E4 (P3: STALE N=3, FALLEN_DIRECT N=3) | DT-4F-001 |
| R2 cooldown | recovery_g1 | `RETRY_COOLDOWN_S` | 5.0 s | L51 | Cooldown entre reintentos; bypaseado por `TERMINAL_MANUAL_RULE_IDS` | E4 (P3 INTER_RUN_S=6s constraint) | DT-4F-001 |
| R3 terminal bypass | recovery_g1 | `TERMINAL_MANUAL_RULE_IDS` | `{4F-P2-FREEZE, 4F-P2-NANINF, 4F-P2-TIMESTAMP}` | L57 | Estas rule_ids bypasean cooldown/retry → `operator_intervention` en attempt=1 | E4 (P2-A2/A3/A4) | — |
| R2 max wait | recovery_g1 | `WAIT_FOR_PRIMARY_MAX_S` | 30.0 s | L61 | R2 espera hasta 30s antes de escalar | E3 (P3 ~1005ms observado, techo no alcanzado) | DT-4F-001 |

---

## 4. Hallazgos Estructurales

### H1 — WARN e INFO del observer nunca publican SafetyEvent

`_publish_fallen_safety_event` se llama únicamente cuando `severity == 'CRITICAL'` AND `_fallen_consecutive >= FALLEN_CONSECUTIVE_N`. WARN e INFO solo resetean `_fallen_consecutive = 0`. El claim de severidad multi-nivel es interno únicamente — no se propaga al bus de mensajes.

### H2 — FALLEN_CONSECUTIVE_N=3 actúa como gate de debounce exclusivo de CRITICAL

Un solo frame con `abs_w < 0.80` no dispara SafetyEvent. Se requieren 3 frames frescos consecutivos (`FRESH_MAX_AGE_S=0.5s` por frame). Relevante para P4-B (baseline sano) y P4-E (false positive con robot inmóvil).

### H3 — Observer emite `risk_level='STABILITY_RISK'` + `restriction_level='NONE'` hardcodeados

La severidad interna (WARN/CRITICAL) no se refleja en los campos del mensaje — aparece solo en `notes`. El routing downstream depende del `risk_level` del mensaje (`STABILITY_RISK`), no de la severidad de detección interna. Consecuencia: un WARN interno que eventualmente llega a publicar SafetyEvent (si se modificara el código) sería enrutado igual que un CRITICAL.

### H4 — STALE tiene dos caminos de severidad con evidencia asimétrica

- `CRITICAL_STALE_TOPICS` → CRITICAL inmediato — evidencia **E4** (P2-A1, P3 timing)
- Tópicos no-críticos: WARN → CRITICAL si `dur >= STALE_CRITICAL_S=3s` — evidencia **E3** (path de escalación no fue aislada experimentalmente)

El camino de escalación WARN→CRITICAL para tópicos no-críticos es claim E3, no E4.

### H5 — WAIT_FOR_PRIMARY_MAX_S=30s nunca fue alcanzado experimentalmente

P3 midió ~1005ms en R2 (por `wait_for_primary_restore` simulada ~1s). El techo de 30s es claim **E1** (código solamente). No se produjo escalación por timeout máximo en ningún experimento.

---

## 5. Impacto en Deuda Técnica

### DT-4F-001 — Thresholds pragmáticos

**Estado post-P4-A:** `partially characterized`

- Todos los thresholds inventariados con source lines y evidencia honesta.
- Thresholds con evidencia más débil: F1-WARN (E1), F2-one_lost (E1), F3-STALE escalation (E3), F7-RATE (E2).
- No cerrada: ningún sweep formal ejecutado. Boundary tests pendientes (P4-D).
- Decisión formal sobre cierre o reducción: pendiente P4-D + P4-F.

### DT-4F-004 — FREEZE IMU falso positivo potencial

**Estado post-P4-A:** `characterized, not resolved`

- `FREEZE_N=5` samples — evidencia E4 para detección positiva (P2-A2, P3 timing).
- `NO_FREEZE_TOPICS` excluye contactos correctamente (E1) — justificación: valores binarios esperan repetición.
- Falso positivo con robot inmóvil (IMU sin movimiento real, valores repetidos legítimos): **no evaluado todavía**.
- Requiere P4-B (baseline sano sin movimiento inducido).
- Permanece abierta hasta P4-B ejecutada con evidencia E3+.

---

## 6. Alcance y Limitaciones

- Este documento cubre P4-A únicamente (inventory-first).
- No se modificó runtime.
- No se cambiaron thresholds.
- No se ejecutaron harnesses nuevos en esta fase.
- Valores extraídos del código en commit HEAD `9777103`.
- Evidence levels asignados conservadoramente — nunca inflados.
- Boundary sweep (P4-D) y false positive matrix (P4-E) pendientes de aprobación PM.

---

## 7. Próximo paso

**P4-B — Negative Controls:** baseline sano sin faults, verificar que no se producen SafetyEvents CRITICAL.
Pendiente aprobación PM antes de ejecutar.

---

*G1 Deterministic Safety Runtime — 4J_THRESHOLD_CHARACTERIZATION.md*
*Generado: 2026-06-23*
*HEAD: 9777103 | P4-A inventory complete | pre-harness*
*PM: ChatGPT | Implementador/Auditor: Claude | Operador: Jorge Padilla*
