# G1 Deterministic Safety Runtime — CHAT BOOTSTRAP PROTOCOL
## Versión 25 — Actualizada 2026-06-23 (4J-P2-A CERRADA)

> **Cambios v25 vs v24:**
> - **4J-P2-A CERRADA**: Individual Fault Injection Matrix. STALE/FREEZE/NANINF/TIMESTAMP/FALLEN PASS, RATE declared limitation, TX-011 citado. Commit `3414fe2`.
> - **Anti-pattern #78**: `docker restart` antes de cada fila formal — nodo con uptime largo contamina retry state.
> - **Clase H registrada**: `operator_intervention` → `request_operator_intervention` — bug de harness, no de runtime.
> - **Pendiente**: `4J_FAULT_INJECTION_MATRIX.md` generado, no commiteado — commitar a `docs/audit/` al inicio de P3.
> - HEAD: `3414fe2` — CI Build ✅ CI Audit ✅ — 65/65 PASS 0 skipped.

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
  4J-P3 Timing Traceability Report                     🔲 PENDIENTE
  4J-P4 Threshold / False-Positive Characterization    🔲 PENDIENTE
  4J-P5 Assurance Case + Paper Package                 🔲 PENDIENTE
Etapa 5A  — Isaac Lab                                  🔒 FUERA DE RUTA / T4
```

**Repositorio:** github.com/jorgerpg1213-mitech/g1-deterministic-safety-runtime
**HEAD:** `3414fe2` (post-4J-P2-A) — CI Build ✅ CI Audit ✅
**VM:** ~/g1-deterministic-safety-runtime | boring_noether activo

---

# INSTRUCCIÓN CRÍTICA PARA EL PRIMER MENSAJE

**4J-P2-A ✅. Próximo: 4J-P3 — Timing Traceability Report.**

**Acción inmediata al inicio de P3:**
1. Commitar `4J_FAULT_INJECTION_MATRIX.md` a `docs/audit/`
2. Leer documento PM para P3 antes de diseñar nada
3. Auditar logs `4F-P5 LATENCY` disponibles en `recovery_g1`

**LO QUE SE RESOLVIÓ EN SESIÓN 4J-P2-A:**

**Matriz de fault injection individual — 7 filas:**

| ID | Fault | Ruta | Resultado |
|---|---|---|---|
| P2-A1 | STALE | R2 Direct | ✅ PASS — `wait_for_primary_restore REC-AUTO` |
| P2-A2 | FREEZE | R3 Terminal | ✅ PASS — `request_operator_intervention REC-MANUAL attempt=1` |
| P2-A3 | NANINF | R3 Terminal | ✅ PASS — `request_operator_intervention REC-MANUAL attempt=1` |
| P2-A4 | TIMESTAMP | R3 Terminal | ✅ PASS — `request_operator_intervention REC-MANUAL attempt=1` |
| P2-A5 | Fallen direct | R2 Direct fallback | ✅ PASS — `wait_for_primary_restore REC-AUTO` (CAUTION+R2) |
| P2-A6 | RATE | — | ✅ DECLARED LIMITATION — detection-only |
| P2-A7 | Fallen governed TX-011 | R1 Governed | ✅ CITADO — P0-B + P1-B |

**Hallazgos clave:**
- State contamination (17h uptime) → timeout silencioso en STALE → anti-pattern #78
- `request_operator_intervention` es el action_name real del runtime (no `operator_intervention`)
- `STABILITY_RISK + R3` activa `_recovery_allowed()` bloqueando recovery — A5 requirió `CAUTION + R2`
- RATE: `watchdog_g1` detecta, `recovery_g1` sin rama explícita → limitation

**Limitación explícita de P2-A:**
Sin faults simultáneos · Sin secuencias · Sin timing bounds · Sin recuperación física · Sin certificación

**Primero: leer documento PM para P3. Auditar antes de diseñar. OK del PM antes de cualquier implementación.**

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
**NOTA anti-pattern #78:** `docker restart` antes de cada fila formal de fault injection.

---

# Trazabilidad causal — estado post-4J-P2-A

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

# 4J-P2-A — Fault Injection Matrix (CERRADA)

| Observable | Evidencia | Resultado |
|---|---|---|
| STALE → `wait_for_primary_restore` REC-AUTO | `parent_event_id=4JP2-DIRECT-001` | ✅ |
| FREEZE → `request_operator_intervention` REC-MANUAL attempt=1 | `parent_event_id=4JP2-A2-FREEZE-001` | ✅ |
| NANINF → `request_operator_intervention` REC-MANUAL attempt=1 | `parent_event_id=4JP2-A3-NANINF-001` | ✅ |
| TIMESTAMP → `request_operator_intervention` REC-MANUAL attempt=1 | `parent_event_id=4JP2-A4-TIMESTAMP-001` | ✅ |
| FALLEN direct → `wait_for_primary_restore` REC-AUTO | `parent_event_id=4JP2-A5-FALLEN-001` | ✅ |
| RATE | detection-only — sin política recovery | ✅ DECLARED LIMITATION |
| Fallen governed TX-011 | P0-B + P1-B citados | ✅ CITADO |
| Regresión | 65/65 PASS | ✅ |

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
| **78** | **Correr harness contra nodo con uptime largo sin verificar retry state** | **`docker restart` antes de cada fila formal** |

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
| **DT-4J-001** | **Full native traceability** (`action_id`, `parent_action_id`, `RecoveryEvent.parent_event_id` nativo) | **Media** | **Abierta — P3** |

---

*G1 Deterministic Safety Runtime — CHAT_BOOTSTRAP_PROTOCOL v25*
*Actualizado: 2026-06-23*
*4E ✅ | 4F ✅ | 4G ✅ | 4H ✅ | 4I ✅ | 4J 🔄 (P0✅ P1✅ P2-prep✅ P2-A✅) | 5A 🔒*
