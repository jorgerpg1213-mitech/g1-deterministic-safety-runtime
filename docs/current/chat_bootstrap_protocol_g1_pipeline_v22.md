# G1 Deterministic Safety Runtime — CHAT BOOTSTRAP PROTOCOL
## Versión 22 — Actualizada 2026-06-19 (4H-P2 CERRADA)

> **Cambios v22 vs v21:**
> - **4H-P2 CERRADA**: policy hardening — causas terminales (FREEZE/NANINF/TIMESTAMP) bypassean cooldown/retry. Constante global `TERMINAL_MANUAL_RULE_IDS`. Validado focalmente.
> - **4H CERRADA**: P1 + P2 completas.
> - Anti-pattern #74 añadido: correr harness antes de que el subscriber esté activo.
> - HEAD: pendiente commit 4H-P2.

---

# Estado Actual del Proyecto

```
Etapa 4E  — Baseline sano + validación                 ✅ CERRADA
Etapa 4F  — Safety Runtime Enrichment                  ✅ CERRADA
Etapa 4G  — Pipeline Hardening                         ✅ CERRADA
Etapa 4H  — Recovery Inteligente                       ✅ CERRADA
  4H-P1 recovery inteligente por causa                 ✅ CERRADA
  4H-P2 recovery policy hardening                      ✅ CERRADA
Etapa 4I  — Formalización                              🔲 PENDIENTE
  4I-P1 SAFETY_MODEL_G1.md                             🔲 PENDIENTE
  4I-P2 Assurance case                                 🔲 PENDIENTE
Etapa 4J  — Paper Prep                                 🔲 PENDIENTE
Etapa 5A  — Isaac Lab                                  🔒 FUERA DE RUTA / T4
```

**Repositorio:** github.com/jorgerpg1213-mitech/g1-deterministic-safety-runtime
**HEAD:** pendiente commit 4H-P2
**VM:** ~/g1-deterministic-safety-runtime | boring_noether activo

---

# INSTRUCCIÓN CRÍTICA PARA EL PRIMER MENSAJE

**4H-P2 cerrada. 4H completa. Próximo: 4I-P1 — SAFETY_MODEL_G1.md.**

**LO QUE SE VALIDÓ EN ESTA SESIÓN:**
- Auditoría completa de política de recovery: cooldown, retry, escalación, simultaneidad, fallback
- Gap identificado: causas terminales consumían retry/cooldown incorrectamente
- Fix: `TERMINAL_MANUAL_RULE_IDS` + bypass antes de cooldown/escalation en `_dispatch_recovery()`
- Validación focal: FREEZE ×2 <5s sin cooldown ✅, STALE post-terminal sin contaminación ✅
- 65/65 tests PASS

**Política de recovery post-4H-P2:**
- FREEZE/NANINF/TIMESTAMP: terminal, bypass cooldown/retry, REC-MANUAL inmediato, attempt=1 fijo
- STALE/fallen directa: recuperables, retry/cooldown/escalation normal
- TX-011 gobernada: intacta
- Simultaneidad: single-flight `_recovery_active`, first accepted wins — documentado

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

# 4H-P2 — Recovery Policy Hardening (CERRADA)

## Política mínima validada

| Causa | Acción | Tipo | Cooldown | Escalación |
|---|---|---|---|---|
| Caída física (TX-011) | stabilization_mode | REC-AUTO | dedup 5s | N/A |
| Caída directa fallback | wait_for_primary_restore | REC-AUTO | RETRY_COOLDOWN_S | MAX_AUTO_RETRIES |
| STALE | wait_for_primary_restore | REC-AUTO | RETRY_COOLDOWN_S | MAX_AUTO_RETRIES |
| FREEZE | operator_intervention | REC-MANUAL | **ninguno** | **ninguna** |
| NANINF | operator_intervention | REC-MANUAL | **ninguno** | **ninguna** |
| TIMESTAMP | operator_intervention | REC-MANUAL | **ninguno** | **ninguna** |

**Simultaneidad:** single-flight `_recovery_active` — first accepted wins.

## Implementación
**Archivo:** `src/recovery_g1/recovery_g1/recovery_g1.py`
- `TERMINAL_MANUAL_RULE_IDS = {'4F-P2-FREEZE', '4F-P2-NANINF', '4F-P2-TIMESTAMP'}` — constante global
- Bypass antes de cooldown/escalation en `_dispatch_recovery()`
- attempt=1 fijo para terminales — no auto-retry

---

# DT-4G-004 — Estado

| Sub-deuda | Estado | Descripción |
|---|---|---|
| DT-4G-004A | ✅ CERRADA | Teardown activo. No requiere restart entre corridas normales. |
| DT-4G-004B | 🔲 ABIERTA | Zombies `<defunct>` por PID1/reaper. No bloqueante. Solución: `--init` flag Docker. |

---

# Tests — estado al cierre

```
safety_orchestrator_g1:     63/63 PASS
test_g1_safety_layer:        2/2 PASS
CI Build:                   ✅ GREEN
CI Audit:                   ✅ GREEN
Total:                      65 tests PASS
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
| **74** | **Correr harness antes de que subscriber esté activo** | **Confirmar "[Iniciado]" antes de publicar** |

---

# Deuda Técnica Activa

| ID | Deuda | Prioridad |
|---|---|---|
| DT-4E-001 | SAFETY_MODEL_G1.md ausente | Alta |
| DT-4E-006 | Control PD diferido | Alta |
| DT-4F-001 | Thresholds pragmáticos | Media |
| DT-4F-002 | TX-006b/c sin test explícito | Media |
| DT-4F-003 | TX-009 POLICY_GATED exacta | Baja |
| DT-4F-004 | FREEZE IMU falso positivo potencial | Media |
| DT-4G-002 | t1→t2 correlación por UUID/event_id | Media |
| DT-4G-004B | Zombies `<defunct>` por PID1/reaper | Baja |

---

*G1 Deterministic Safety Runtime — CHAT_BOOTSTRAP_PROTOCOL v22*
*Actualizado: 2026-06-19*
*4E ✅ | 4F ✅ | 4G ✅ | 4H ✅ | 4I 🔲 | 4J 🔲 | 5A 🔒*
