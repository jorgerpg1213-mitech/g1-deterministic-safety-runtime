# G1 Deterministic Safety Runtime — CHAT BOOTSTRAP PROTOCOL
## Versión 24 — Actualizada 2026-06-22 (4J-P0 + 4J-P1 + 4J-P2-prep CERRADAS)

> **Cambios v24 vs v23:**
> - **4J-P0 CERRADA**: DT-4I-001 resuelta. `_on_safety_action()` autosuficiente. Commits `779821f` + `cb3f777`.
> - **4J-P1 CERRADA**: `SafetyAction.msg` +`parent_event_id`. Trazabilidad mínima gobernada. Commit `bbcc097`.
> - **4J-P2-prep CERRADA**: trazabilidad ruta directa en `_dispatch_recovery()`. Bug `test_depend` corregido. Commit `cf4e835`.
> - **DT-4I-001 ✅ CERRADA**. **DT-4J-001 🔲 ABIERTA** (full native traceability).
> - HEAD: post-4J-P2-prep — CI Build ✅ CI Audit ✅ — 65/65 PASS 0 skipped.

---

# Estado Actual del Proyecto

```
Etapa 4E  — Baseline sano + validación                 ✅ CERRADA
Etapa 4F  — Safety Runtime Enrichment                  ✅ CERRADA
Etapa 4G  — Pipeline Hardening                         ✅ CERRADA
Etapa 4H  — Recovery Inteligente                       ✅ CERRADA
  4H-P1 recovery inteligente por causa                 ✅ CERRADA
  4H-P2 recovery policy hardening                      ✅ CERRADA
Etapa 4I  — Formalización                              ✅ CERRADA
  4I-P1 SAFETY_MODEL_G1.md                             ✅ CERRADA
  4I-P2 TRACEABILITY_MATRIX_G1.md                      ✅ CERRADA
  4I-P3 POLICY_CLARIFICATION_G1.md                     ✅ CERRADA
Etapa 4J  — Paper Prep                                 🔄 EN PROGRESO
  4J-P0 Runtime Alignment / cierre DT-4I-001           ✅ CERRADA
  4J-P1 Causal Traceability (minimum)                  ✅ CERRADA
  4J-P2-prep Direct path traceability                  ✅ CERRADA
  4J-P2 Extended Fault Injection Matrix                 🔲 PENDIENTE
  4J-P3 Timing Traceability Report                     🔲 PENDIENTE
  4J-P4 Threshold / False-Positive Characterization    🔲 PENDIENTE
  4J-P5 Assurance Case + Paper Package                 🔲 PENDIENTE
Etapa 5A  — Isaac Lab                                  🔒 FUERA DE RUTA / T4
```

**Repositorio:** github.com/jorgerpg1213-mitech/g1-deterministic-safety-runtime
**HEAD:** post-4J-P2-prep (cf4e835) — CI Build ✅ CI Audit ✅
**VM:** ~/g1-deterministic-safety-runtime | boring_noether activo

---

# INSTRUCCIÓN CRÍTICA PARA EL PRIMER MENSAJE

**4J-P0 ✅ 4J-P1 ✅ 4J-P2-prep ✅. Próximo: 4J-P2 — Extended Fault Injection Matrix.**

**LO QUE SE RESOLVIÓ EN ESTA SESIÓN:**

**4J-P0 — DT-4I-001:**
- Bug: `_on_safety_action()` pasaba TX-011 gobernada por `_dispatch_recovery()` — router causal de ruta directa — caía en `else → operator_intervention`.
- Fix: `_action_stabilization_mode()` creado. `_on_safety_action()` autosuficiente — ejecuta directamente sin pasar por router.
- Evidencia: P0-A focal PASS + P0-B integración PASS (cadena completa con topología aislada verificada).
- `recovery_type=REC-AUTO` respeta contrato `RecoveryEvent.msg`. `notes` declara `governed_TX011` y `physical recovery not claimed`.

**4J-P1 — Trazabilidad causal mínima:**
- Gap: `SafetyEvent.event_id` populado por observer/watchdog pero perdido en orchestrator → SafetyAction.
- Fix: `SafetyAction.msg` +`string parent_event_id`. Orchestrator propaga `triggering_event.event_id`. Recovery lo mete en `RecoveryEvent.notes`.
- Cadena: `SafetyEvent.event_id=A → SafetyAction.parent_event_id=A → RecoveryEvent.notes parent_event_id=A`.
- No declarado: `action_id`, `parent_action_id`, `RecoveryEvent.parent_event_id` nativo → DT-4J-001.

**4J-P2-prep — Trazabilidad ruta directa:**
- Gap: `_dispatch_recovery()` no propagaba `SafetyEvent.event_id` en rutas directas/terminales.
- Fix: `parent_event_id` como parámetro en `_dispatch_recovery()`, propagado en 3 call sites.
- Bug corregido: `package.xml` de `safety_orchestrator_g1` sin `test_depend recovery_g1` → 9 skips en `colcon test`.

**Política de recovery (sin cambios):** igual que 4H-P2.

**Primero: leer, auditar, diseñar. OK del PM antes de cualquier cambio de lógica safety.**

---

# CAMINO OPERATIVO CONFIRMADO

## Launcher unificado
```bash
cd ~/g1-deterministic-safety-runtime && python3 sim_runtime/4G/launch_pipeline.py 2>&1 | tee /tmp/<fase>_run.log
```

**Preflight verifica:**
1. Paths requeridos
2. Repo limpio (o --allow-dirty)
3. boring_noether corriendo
4. /ws/install/setup.bash presente
5. **0 procesos safety ACTIVE en contenedor** (ignora `<defunct>`)
6. **0 publishers en /safety_events**

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

---

# Trazabilidad causal — estado post-4J-P1

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

# 4J-P0 — Runtime Alignment (CERRADA)

| Observable | Evidencia | Resultado |
|---|---|---|
| `_on_safety_action()` autosuficiente | P0-A: `action_name=stabilization_mode` | ✅ |
| TX-011 cadena completa | P0-B: `SafetyEvent → SafetyAction TX-011 → RecoveryEvent` | ✅ |
| `recovery_type=REC-AUTO` | respeta contrato `RecoveryEvent.msg` | ✅ |
| `notes` semántica | `governed_TX011 execution acknowledged — physical recovery not claimed` | ✅ |
| Topología aislada P0-B | `/safety_events`: solo `safety_orchestrator_g1` | ✅ |
| Regresión | 65/65 PASS | ✅ |

---

# 4J-P1 — Causal Traceability (CERRADA — minimum scope)

| Campo | Estado |
|---|---|
| `SafetyAction.msg` +`parent_event_id` | ✅ instalado y verificado `ros2 interface show` |
| Orchestrator propaga `event_id` | ✅ `triggering_event.event_id → action.parent_event_id` |
| Recovery propaga en `notes` | ✅ ruta gobernada y directa |
| Harness P1-B PASS | ✅ `event_id=4JP1B-TEST-001` trazado end-to-end |
| Harness directo STALE PASS | ✅ `event_id=4JP2-DIRECT-001` en `RecoveryEvent.notes` |

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
| 67 | Tocar runtime safety para CI | Fix en el test |
| 70 | Corridas formales sin preflight limpio | Preflight bloqueante |
| 71 | N≥10 sin limpiar contenedor | docker restart antes de batería formal |
| 72 | Editar archivos críticos sin verificar encoding | sed -n antes de cualquier reemplazo |
| 73 | Mezclar dos causas en un solo harness | Una causa por harness |
| 74 | Correr harness antes de que subscriber esté activo | Confirmar "[Iniciado]" antes de publicar |
| **75** | **Ejecutar harness sin verificar topología exacta** | **`ros2 topic info -v` antes de publicar** |
| **76** | **Asumir `colcon test` tiene mismo entorno que import directo** | **Declarar `test_depend` en `package.xml`** |
| **77** | **Tomar `node._events[0]` sin filtrar por ID conocido** | **Filtrar por `parent_event_id=FIXED_ID` exacto** |

---

# Deuda Técnica Activa

| ID | Deuda | Prioridad | Estado |
|---|---|---|---|
| DT-4E-001 | SAFETY_MODEL_G1.md ausente | Alta | ✅ CERRADA 4I-P1 |
| DT-4E-006 | Control PD diferido | Alta | Abierta |
| DT-4F-001 | Thresholds pragmáticos | Media | Abierta |
| DT-4F-002 | TX-006b/c sin test explícito | Media | Abierta |
| DT-4F-003 | TX-009 POLICY_GATED exacta | Baja | ✅ CERRADA 4I-P3 |
| DT-4F-004 | FREEZE IMU falso positivo potencial | Media | Abierta |
| DT-4G-002 | t1→t2 correlación UUID (paper) | Media | Parcial — P1-B |
| DT-4G-004B | Zombies `<defunct>` por PID1/reaper | Baja | Abierta, no bloqueante |
| DT-4I-001 | Discrepancia TX-011 governed recovery | Alta | ✅ CERRADA 4J-P0 |
| **DT-4J-001** | **Full native traceability** (`action_id`, `parent_action_id`, `RecoveryEvent.parent_event_id` nativo) | **Media** | **Abierta — P1-C o P3** |

---

*G1 Deterministic Safety Runtime — CHAT_BOOTSTRAP_PROTOCOL v24*
*Actualizado: 2026-06-22*
*4E ✅ | 4F ✅ | 4G ✅ | 4H ✅ | 4I ✅ | 4J 🔄 (P0✅ P1✅ P2-prep✅) | 5A 🔒*
