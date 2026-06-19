# Tesis de Etapas del Proyecto — Runtime Architecture para Humanoide G1
## Versión 23 — Actualizada 2026-06-18 (4G cerrada técnicamente)

> **Nota de versión (v23):** cambios respecto a v22 —
> (1) **4G-P3-C CERRADA**: t0→t1 N=10, 100% PASS, media=2474.60ms.
> (2) **4G-P3-D CERRADA**: t1→t2 ruta gobernada N=10, 100% PASS, media=1.19ms.
> (3) **4G-P4-A/B/C/D CERRADAS**: ruta gobernada orchestrator→recovery validada N=10. DT-4G-003 cerrada.
> (4) **4G-P5 CERRADA**: preflight bloqueante + post-teardown hygiene detector.
> (5) DT-4G-004 añadida: teardown activo dentro del contenedor.
> (6) Anti-patterns #69, #70, #71 documentados.
> (7) Errata P2-C: disparador real = umbral de orientación abs_w=0.713 < 0.80, no both_lost.
> (8) Próximo: 4H-P1 (recovery inteligente por causa).

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

---

### Etapa 4G — Pipeline Hardening — ✅ CERRADA TÉCNICAMENTE

#### 4G-P0 — Sanity Repo Nuevo / Runtime Paths — ✅ CERRADA
#### 4G-P1 — Launcher Unificado — ✅ CERRADA
#### 4G-P2-A — Reproducibilidad Baseline Sano — ✅ CERRADA
#### 4G-P2-B — Reproducibilidad Caída Inducida + t1→t2 — ✅ CERRADA
#### 4G-P2-C — TX-011 Escalación Gobernada SECONDARY/fallen — ✅ CERRADA (N=13)

**Errata P2-C (documentada en esta sesión):**
El piloto 20260618_081905 fue disparado por rama CRITICAL de umbral de orientación: `abs(q.w)=0.713 < FALLEN_W_CRITICAL=0.80`. Los contactos `L=False, R=True` (`one_lost`) son condición concurrente pero no disparadora — `one_lost` solo califica WARN. No debe describirse como `both_lost`.

---

#### 4G-P3 — Instrumentación Temporal t0→t1→t2 — ✅ CERRADA

##### 4G-P3-A — Diseño Instrumentación — ✅ CERRADA
Sub-prueba de reloj común confirmada: `CLOCK_MONOTONIC` compartido entre contenedor Isaac y `boring_noether` bajo `--network=host`. Delta observado = tiempo real entre comandos, no divergencia de base.

Definición de timestamps:
- `t0_trigger`: `time.monotonic_ns()` en Isaac en `FALL TRIGGER it=450`, antes de inyectar la caída
- `t1`: `time.monotonic_ns()` en observer al inicio de `_publish_fallen_safety_event`, antes de `publish(msg)`

Mecanismo: marcador `G1_FALL_MARKER` en `A_isaac.log` + `G1_OBSERVER_EVENT_TIME` en `B_observer.log`. Schema congelado. No se usó publisher ROS por scope issue resuelto dejando marcador en log.

##### 4G-P3-B — Piloto t0→t1 — ✅ CERRADA
Corrida `20260618_131606`: `t0→t1 = 2860.62ms`. Primer PASS limpio tras resolver bugs de instrumentación (pub_marker scope, nodos huérfanos, build install stale).

##### 4G-P3-C — t0→t1 N=10 — ✅ CERRADA (2026-06-18)

**Clasificación:** PASS completo — latencia física→SafetyEvent reproducible.

**Resultados N=10:**
| Métrica | Valor |
|---|---|
| N total | 10 |
| PASS rate | 100% |
| media t0→t1 | 2474.60ms |
| min t0→t1 | 2046.47ms |
| max t0→t1 | 3511.02ms |

**Interpretación:** t0→t1 mide desde la orden de inyección de caída en Isaac hasta la publicación del SafetyEvent. Incluye dinámica física, actualización de sensores, transporte ROS2/DDS, y 3 snapshots consecutivos requeridos por regla 3C2b.

**Validado:** latencia física→SafetyEvent reproducible ✅

##### 4G-P3-D — t1→t2 Ruta Gobernada — ✅ CERRADA (2026-06-18)

**Bloqueado inicialmente por DT-4G-003:** t1→t2 por ruta directa solo presente en 5/10 corridas — race condition entre SafetyEvent directo y `/system_state` actualizado por TX-011.

**Cerrado con ruta gobernada (P4-D):** t1→t2 presente en 10/10 corridas P4-D vía `ORCH_ACTION→RECOVERY`.

**Resultados N=10 (ruta gobernada):**
| Métrica | Valor |
|---|---|
| N total | 10 |
| PASS rate | 100% |
| media t1→t2 | 1.19ms |
| min t1→t2 | 0.83ms |
| max t1→t2 | 2.02ms |

---

#### 4G-P4 — Ruta Gobernada Orchestrator→Recovery — ✅ CERRADA (2026-06-18)

##### 4G-P4-A — Auditoría — ✅ CERRADA

**Gap confirmado en código:**
- Orchestrator publica `/safety_actions` (línea 803) ✅
- TX-011 genera SafetyAction (línea 1065) ✅
- Recovery NO tenía subscriber a `/safety_actions` ❌
- `_recovery_allowed()` bloqueaba recovery cuando state=`STABILITY_RISK/R3` (exactamente el estado post-TX-011)

**Race condition documentada:**
```
Caso A: SafetyEvent llega ANTES de TX-011/system_state
  → state=SAFE/NONE → _recovery_allowed()=True → recovery actúa ✅

Caso B: SafetyEvent llega DESPUÉS de TX-011/system_state
  → state=STABILITY_RISK/R3 → _recovery_allowed()=False → recovery bloqueado ❌
```
Explica el 5/10 de t1→t2 en corridas P3-C.

##### 4G-P4-B — Diseño — ✅ CERRADA

Subscriber aditivo en recovery: `/safety_actions → _on_safety_action()`. Ruta directa SafetyEvent preservada como fallback. Guard anti-doble ejecución por ventana temporal 5s. Log `ORCH_ACTION→RECOVERY` con `latency_ms`, `t1_ns`, `t2_ns`.

Fix orchestrator: `action.timestamp = self.get_clock().now().to_msg()` en `_publish_safety_action`.

##### 4G-P4-C — Piloto — ✅ CERRADA

Corrida `20260618_144007`: `ORCH_ACTION→RECOVERY latency_ms=2.388, t1_ns>0` ✅. Sin doble ejecución. Ruta directa fallback también activa.

##### 4G-P4-D — N=10 Ruta Gobernada — ✅ CERRADA (2026-06-18)

**Clasificación:** PASS completo — ruta gobernada orchestrator→recovery determinista N=10.

**Resultados N=10 (corridas 20260618_160555 → 20260618_164129):**
| Métrica | Valor |
|---|---|
| N total | 10 |
| PASS rate | 100% |
| ORCH_ACTION→RECOVERY presente | 10/10 |
| media t0→t1 | 2583.61ms |
| media t1→t2 gobernada | 1.19ms |

**Validado:**
- Ruta gobernada orchestrator→recovery: N=10, 100% PASS ✅
- t1→t2 trazable al orchestrator 10/10 ✅
- Sin doble ejecución ✅
- DT-4G-003 CERRADA ✅

---

#### 4G-P5 — Higiene Operacional — ✅ CERRADA (2026-06-18)

**Causa raíz de nodos huérfanos confirmada:**
El launcher mata sus subprocesos (`subprocess.Popen`) pero los procesos dentro de `boring_noether` persisten — son hijos del entrypoint `ros2 run` dentro del contenedor, no del proceso Python del launcher en el host.

**Evidencia:** post-teardown de corrida `20260618_152445` mostró ~80 procesos residuales + 33 publishers en `/safety_events` acumulados de N10 previas.

**Implementación:**

P5-A: verificación post-teardown observacional — loguea residuos sin bloquear exit code.

P5-B: preflight bloqueante — verifica antes de cada corrida:
- 0 procesos safety en contenedor
- 0 publishers en `/safety_events`
- Si hay residuos → `FAIL preflight` → abort antes de lanzar Isaac

**Validación:** N=10 P4-D con preflight limpio — todas las corridas mostraron `LABORATORIO LIMPIO` en preflight.

**DT-4G-004 abierta:** teardown activo dentro del contenedor (pkill de procesos safety) para eliminar necesidad de `docker restart` entre corridas. Diferido.

---

### Etapa 4H — Recovery Inteligente — 🔲 Pendiente
### Etapa 4I — Formalización — 🔲 Pendiente
### Etapa 4J — Paper Prep — 🔲 Pendiente
### Etapa 5A — Isaac Lab — 🔒 Bloqueada (GPU ≥ RTX 4080)

---

## Roadmap Aprobado Post-4G

```
4H-P1   Recovery inteligente por causa
        Pregunta: ¿recovery diferencia causa?
        caída física → stabilization/fall action
        STALE → comms degradation action
        FREEZE → sensor fault action
        NaN → invalid telemetry action

4I-P1   Contrato semántico formal
        event_type + source_authority + rule_id + severity → TX → action

4I-P2   Assurance case
        claim→evidence→limitation→mitigation

4J-P1   Fault injection matrix extendida
        freeze, stale, NaN, contact inconsistency, DDS latency, duplicates
```

---

## Criterios de éxito (actualizados)

```
4F-P1→P6  ✅  cerrados
4G-P0     ✅  repo nuevo, build portable, CI hardening
4G-P1     ✅  launcher unificado
4G-P2-A   ✅  reproducibilidad baseline sano N=10
4G-P2-B   ✅  reproducibilidad caída inducida N=10
4G-P2-C   ✅  TX-011 ruta gobernada N=13
4G-P3-C   ✅  t0→t1 medido N=10, media=2474ms
4G-P3-D   ✅  t1→t2 ruta gobernada N=10, media=1.19ms
4G-P4-D   ✅  ruta gobernada orchestrator→recovery N=10
4G-P5     ✅  preflight bloqueante + hygiene
4H-P1     🔲  recovery inteligente
4I-P1     🔲  SAFETY_MODEL_G1.md recreado
4E-P5     🔲  control activo PD (diferido)
5A        🔒  Isaac Lab fuera del T4
```

---

## Matriz de Transiciones — Estado al Cierre 4G

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
| TX-011 | NORMAL | SECONDARY/fallen→STABILITY_RISK/R3 | ✅ N=13 P2-C + N=10 P4-D |

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
| DT-4G-001 | TX-011 escalación gobernada SECONDARY/fallen | ✅ CERRADA |
| DT-4G-002 | t1→t2 correlación por UUID/event_id (paper) | Media |
| DT-4G-003 | Ruta gobernada orchestrator→recovery | ✅ CERRADA |
| **DT-4G-004** | **Teardown activo contenedor** | **Media** |

---

## Anti-Patterns Clave (acumulados)

| # | Anti-pattern |
|---|---|
| 54 | Reconstruir docker run de memoria |
| 60 | Lanzar B/C/D antes de que Isaac esté listo |
| 63 | No verificar sintaxis antes de copiar al contenedor |
| 64 | `colcon build --symlink-install` para build portable |
| 65 | Cambiar `event_type` sin verificar `source_authority` en TX destino |
| 66 | Diseñar TX desde texto de informe, no código real |
| 67 | Tocar runtime safety para que pase un test de CI |
| 68 | Test de estado inicial con launch completo (4 nodos) |
| **69** | **Dedup de safety action por transition_id permanente** |
| **70** | **Correr corridas formales sin verificar laboratorio limpio** |
| **71** | **N≥10 en loop sin limpiar contenedor entre corridas** |

---

*G1 Deterministic Safety Runtime — Tesis de Etapas v23*
*Actualizado: 2026-06-18*
*3C ✅ | 4A–4F ✅ | 4G ✅ | 4H 🔲 | 4I 🔲 | 4J 🔲 | 5A 🔒*
