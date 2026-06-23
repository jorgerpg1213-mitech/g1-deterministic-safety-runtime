# G1 Deterministic Safety Runtime — CHAT BOOTSTRAP PROTOCOL
## Versión 26 — Actualizada 2026-06-23 (4J-P3 CERRADA)

> **Cambios v26 vs v25:**
> - **4J-P3 CERRADA**: Timing Traceability Report. 6 rutas medidas. Commits `edfef80` → `53c3b12` → `f9cbdcf` → `9777103`.
> - **Harness timing:** `sim_runtime/4J/harness_4J_P3_timing_matrix.py` — INTER_RUN_S=6.0, NAME_SETTLE_S=3.0, rclpy init/shutdown una vez por case group.
> - **Limitaciones documentadas:** STALE/FALLEN_DIRECT N=3 (MAX_AUTO_RETRIES=3), TX-011 N=1 (one-shot orchestrator).
> - **Métricas duales R2:** ~1005ms harness (incluye wait_for_primary_restore) vs ~0.86ms dispatch interno 4F-P5.
> - **_NODE_NAME_UNKNOWN_ hallazgo:** DDS resuelve count>0 antes que node names — NAME_SETTLE_S fase 2 warmup requerida.
> - HEAD: `9777103` — CI Build ✅ CI Audit ✅ — 65/65 PASS 0 skipped.

---

# Estado Actual del Proyecto

```
Etapa 4E  — Baseline sano + validación                 ✅ CERRADA
Etapa 4F  — Safety Runtime Enrichment                  ✅ CERRADA
Etapa 4G  — Pipeline Hardening                         ✅ CERRADA
Etapa 4H  — Recovery Inteligente                       ✅ CERRADA
Etapa 4I  — Formalización                              ✅ CERRADA
Etapa 4J  — Paper Prep                                 🔄 EN PROGRESO
  4J-P0 Runtime Alignment / cierre DT-4I-001           ✅ CERRADA
  4J-P1 Causal Traceability (minimum)                  ✅ CERRADA
  4J-P2-prep Direct path traceability                  ✅ CERRADA
  4J-P2-A Extended Fault Injection Matrix               ✅ CERRADA
  4J-P3 Timing Traceability Report                     ✅ CERRADA
  4J-P4 Threshold / False-Positive Characterization    🔲 PENDIENTE
  4J-P5 Assurance Case + Paper Package                 🔲 PENDIENTE
Etapa 5A  — Isaac Lab                                  🔒 FUERA DE RUTA / T4
```

**Repositorio:** github.com/jorgerpg1213-mitech/g1-deterministic-safety-runtime
**HEAD:** `9777103` (post-4J-P3) — CI Build ✅ CI Audit ✅
**VM:** ~/g1-deterministic-safety-runtime | boring_noether activo

---

# INSTRUCCIÓN CRÍTICA PARA EL PRIMER MENSAJE

**4J-P3 ✅. Próximo: 4J-P4 — Threshold / False-Positive Characterization.**

**Acción inmediata al inicio de P4:**
1. Leer documento PM para P4 antes de diseñar nada
2. No tocar runtime
3. No asumir scope — esperar documento PM

**LO QUE SE RESOLVIÓ EN SESIÓN 4J-P3:**

**Timing Traceability Matrix — 6 rutas:**

| Case | Route | N válidas | mean_ms | Limitación |
|---|---|---|---|---|
| STALE | R2 | 3 | 1005.696 | MAX_AUTO_RETRIES=3 |
| FREEZE | R3 | 10 | 3.725 | — |
| NANINF | R3 | 10 | 3.777 | — |
| TIMESTAMP | R3 | 10 | 3.861 | — |
| FALLEN_DIRECT | R2 | 3 | 1005.846 | MAX_AUTO_RETRIES=3 |
| TX-011 governed | R1 | 1 | 6.130 (e2e) | one-shot orchestrator |

**Hallazgos clave:**
- R3 terminal routes: ~3.5–4.6ms dispatch puro
- R2 direct routes: ~1005ms (incluye wait_for_primary_restore ~1s)
- dispatch interno 4F-P5: ~0.86ms (logs, no harness)
- TX-011: T_event_to_action=3.503ms · T_action_to_recovery=2.627ms · T_e2e=6.130ms
- `_NODE_NAME_UNKNOWN_`: DDS propaga count antes que node names → NAME_SETTLE_S=3.0s requerida
- MAX_AUTO_RETRIES=3 limita runs de STALE y FALLEN_DIRECT a N=3 por sesión
- One-shot orchestrator state machine limita TX-011 a N=1 por sesión

**Limitaciones P3:**
- STALE/FALLEN_DIRECT N=3, TX-011 N=1 — aprobados PM
- p95_ms_exploratory — N pequeño, no estadístico fuerte
- t0 = harness publish timestamp, no DDS emission exacto
- ~1005ms R2 ≠ dispatch puro

**Primero: leer documento PM para P4. No diseñar nada sin él.**

---

# CAMINO OPERATIVO CONFIRMADO

## Launcher unificado
```bash
cd ~/g1-deterministic-safety-runtime && python3 sim_runtime/4G/launch_pipeline.py 2>&1 | tee /tmp/<fase>_run.log
```

---

# Contenedor boring_noether — estado confirmado

```
Imagen:       g1-ros-phase-b:humble
Network:      host
/ws mount:    ~/g1-deterministic-safety-runtime
fastdds:      sim_runtime/common/fastdds_udp.xml
Build:        sin --symlink-install
Estado:       activo
Paquetes:     cross_consistency_observer, g1_msgs, recovery_g1,
              safety_orchestrator_g1, watchdog_g1 — todos operativos
```

**NOTA DT-4G-004B:** zombies `<defunct>` ~2 por corrida. Para N≥10 formales: `docker restart boring_noether`.
**NOTA anti-pattern #78:** `docker restart` antes de cada case group de fault injection/timing.
**NOTA _NODE_NAME_UNKNOWN_:** DDS puede no resolver node names aunque count>0. Harness P3 incluye NAME_SETTLE_S=3.0s para esto.

---

# Trazabilidad causal — estado post-4J-P3

## Ruta gobernada (R1 / TX-011)
```
SafetyEvent[event_id=A]
  → safety_orchestrator_g1
    → SafetyAction[parent_event_id=A]
      → recovery_g1
        → RecoveryEvent.notes[parent_event_id=A]
```

## Ruta directa/terminal (R2/R3)
```
SafetyEvent[event_id=A]
  → recovery_g1
    → RecoveryEvent.notes[parent_event_id=A]
```

## No implementado todavía (DT-4J-001)
```
action_id nativo
parent_action_id nativo
RecoveryEvent.parent_event_id nativo
```

---

# 4J-P3 — Timing Traceability (CERRADA)

| Case | Route | N | min_ms | mean_ms | max_ms | p95_exp | Límite |
|---|---|---|---|---|---|---|---|
| STALE | R2 | 3 | 1005.513 | 1005.696 | 1005.890 | 1005.685 | MAX_AUTO_RETRIES |
| FREEZE | R3 | 10 | 3.527 | 3.725 | 3.957 | 3.811 | — |
| NANINF | R3 | 10 | 3.485 | 3.777 | 4.212 | 4.018 | — |
| TIMESTAMP | R3 | 10 | 3.596 | 3.861 | 4.628 | 4.012 | — |
| FALLEN_DIRECT | R2 | 3 | 1005.620 | 1005.846 | 1006.206 | 1005.711 | MAX_AUTO_RETRIES |
| TX-011 R1 | e2e | 1 | — | — | 6.130 | — | one-shot |

Harness: `sim_runtime/4J/harness_4J_P3_timing_matrix.py`
Reporte: `docs/audit/4J_TIMING_TRACEABILITY_REPORT.md`
Evidencia: `evidence/4J/P3_TIMING/`

---

# Tests — estado al cierre

```
safety_orchestrator_g1:     63/63 PASS (0 skipped)
test_g1_safety_layer:        2/2 PASS
CI Build:                   ✅ GREEN
CI Audit:                   ✅ GREEN
Total:                      65 tests PASS, 0 skipped
```

---

# Anti-Patterns Acumulados (selección)

| # | Anti-pattern | Corrección |
|---|---|---|
| 54 | Reconstruir docker run de memoria | Usar comando confirmado en bootstrap |
| 63 | No verificar sintaxis antes de copiar al contenedor | ast.parse antes de docker cp |
| 66 | Diseñar TX desde texto de informe, no código real | Auditar código antes de proponer |
| 70 | Corridas formales sin preflight limpio | Preflight bloqueante |
| 71 | N≥10 sin limpiar contenedor | docker restart antes de batería formal |
| 72 | Editar archivos críticos sin verificar encoding | sed -n antes de cualquier reemplazo |
| 73 | Mezclar dos causas en un solo harness | Una causa por harness |
| 74 | Correr harness antes de que subscriber esté activo | Confirmar "[Iniciado]" antes de publicar |
| 75 | Ejecutar harness sin verificar topología exacta | `ros2 topic info -v` antes de publicar |
| 76 | Asumir `colcon test` tiene mismo entorno que import directo | Declarar `test_depend` en `package.xml` |
| 77 | Tomar `node._events[0]` sin filtrar por ID conocido | Filtrar por `parent_event_id=FIXED_ID` exacto |
| 78 | Correr harness contra nodo con uptime largo sin verificar retry state | `docker restart` antes de cada fila formal |

---

# Deuda Técnica Activa

| ID | Deuda | Prioridad | Estado |
|---|---|---|---|
| DT-4E-006 | Control PD diferido | Alta | Abierta |
| DT-4F-001 | Thresholds pragmáticos | Media | Abierta |
| DT-4F-002 | TX-006b/c sin test explícito | Media | Abierta |
| DT-4F-004 | FREEZE IMU falso positivo potencial | Media | Abierta |
| DT-4G-002 | t1→t2 correlación UUID (paper) | Media | Parcial — P1-B |
| DT-4G-004B | Zombies `<defunct>` por PID1/reaper | Baja | Abierta, no bloqueante |
| **DT-4J-001** | **Full native traceability** (`action_id`, `parent_action_id`, `RecoveryEvent.parent_event_id` nativo) | **Media** | **Abierta** |

---

*G1 Deterministic Safety Runtime — CHAT_BOOTSTRAP_PROTOCOL v26*
*Actualizado: 2026-06-23*
*4E ✅ | 4F ✅ | 4G ✅ | 4H ✅ | 4I ✅ | 4J 🔄 (P0✅ P1✅ P2-prep✅ P2-A✅ P3✅) | 5A 🔒*
