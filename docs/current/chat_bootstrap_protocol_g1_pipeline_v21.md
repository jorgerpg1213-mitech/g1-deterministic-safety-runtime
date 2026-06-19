# G1 Deterministic Safety Runtime — CHAT BOOTSTRAP PROTOCOL
## Versión 21 — Actualizada 2026-06-19 (DT-4G-004A CERRADA + 4H-P1 CERRADA)

> **Cambios v21 vs v20:**
> - **DT-4G-004A CERRADA**: teardown activo dentro del contenedor; ya no se requiere `docker restart` entre corridas normales.
> - **DT-4G-004B ABIERTA**: zombies `<defunct>` por PID1/reaper de `boring_noether`. No bloqueante (~2 por corrida).
> - **4H-P1 CERRADA**: recovery inteligente por causa validado (fallen, STALE, FREEZE, NANINF, TIMESTAMP).
> - `SAFETY_PROC_PATTERN` como constante global única en launcher.
> - `teardown_container()` con SIGTERM + re-verificación + SIGKILL.
> - Preflight e hygiene ignoran `<defunct>` (fix mínimo `grep -v '<defunct>'`).
> - `_extract_rule_id()` + bloque causal en `_dispatch_recovery()`.
> - Anti-patterns #72, #73 añadidos.
> - HEAD: `5005788`.

---

# Estado Actual del Proyecto

```
Etapa 4E  — Baseline sano + validación                 ✅ CERRADA
Etapa 4F  — Safety Runtime Enrichment                  ✅ CERRADA
Etapa 4G  — Pipeline Hardening                         ✅ CERRADA
Etapa 4H  — Recovery Inteligente                       🔄 En progreso
  4H-P1 recovery inteligente por causa                 ✅ CERRADA
  4H-P2 TBD                                            🔲 PENDIENTE
Etapa 4I  — Formalización                              🔲 PENDIENTE
Etapa 4J  — Paper Prep                                 🔲 PENDIENTE
Etapa 5A  — Isaac Lab                                  🔒 FUERA DE RUTA / T4
```

**Repositorio:** github.com/jorgerpg1213-mitech/g1-deterministic-safety-runtime
**HEAD:** `5005788` — CI Build ✅ CI Audit ✅
**VM:** ~/g1-deterministic-safety-runtime | boring_noether activo

---

# INSTRUCCIÓN CRÍTICA PARA EL PRIMER MENSAJE

**DT-4G-004A cerrada. 4H-P1 cerrada. Próximo: definir 4H-P2 con PM o resolver DT-4G-004B.**

**LO QUE SE VALIDÓ EN ESTA SESIÓN:**
- Teardown activo dentro del contenedor: SIGTERM → re-verificación → SIGKILL por PID explícito
- Preflight e hygiene ignoran `<defunct>` — zombies no bloquean corridas
- Recovery inteligente por causa: fallen/STALE/FREEZE/NANINF/TIMESTAMP → acción diferenciada
- Cadena validada: `topic → watchdog → SafetyEvent → recovery → [4H-P1] cause=...`
- TX-011 ruta gobernada intacta

**DEUDA NUEVA DT-4G-004B:**
Zombies `<defunct>` se acumulan ~2 por corrida porque PID 1 de `boring_noether` no hace `wait()`. No ejecutan ni publican. Para corridas N≥10 formales: monitorear conteo. Solución real: `--init` flag de Docker al lanzar `boring_noether`.

**TIMESTAMP pendiente de validación formal** — harness en curso al cierre de sesión.

**Primero: leer, auditar, diseñar. OK del PM antes de cualquier cambio de lógica safety.**

---

# CAMINO OPERATIVO CONFIRMADO — ISAAC SIM 4.5 (T4)

## Launcher unificado (con teardown activo desde DT-4G-004A)
```bash
cd ~/g1-deterministic-safety-runtime && python3 sim_runtime/4G/launch_pipeline.py 2>&1 | tee /tmp/<fase>_run.log
```

**Precondición DT-4G-004B:** para N≥10 formales, verificar conteo de zombies antes de arrancar. `docker restart boring_noether` como limpieza controlada si el conteo crece sin límite.

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
Estado:       activo al cierre de sesión
Paquetes:     cross_consistency_observer, g1_msgs, recovery_g1,
              safety_orchestrator_g1, watchdog_g1 — todos operativos
```

**NOTA DT-4G-004B:** zombies `<defunct>` se acumulan en el contenedor. Para corridas largas N≥10, hacer `docker restart boring_noether` antes de la batería formal.

---

# 4H-P1 — Recovery Inteligente por Causa (CERRADA)

## Mapa causal validado

| Causa | Ruta | Señal | Acción | Validado |
|---|---|---|---|---|
| Caída física | gobernada `_on_safety_action()` | TX-011, stabilization_mode | sin cambio | ✅ |
| Caída física fallback | directa `_on_safety_event()` | source=cross_consistency_observer | wait_for_primary_restore | ✅ |
| STALE | directa | rule_id=4F-P2-STALE en notes | wait_for_primary_restore | ✅ |
| FREEZE | directa | rule_id=4F-P2-FREEZE en notes | operator_intervention | ✅ |
| NANINF | directa | rule_id=4F-P2-NANINF en notes | operator_intervention | ✅ |
| TIMESTAMP | directa | rule_id=4F-P2-TIMESTAMP en notes | operator_intervention | ⚠️ pendiente formal |

## Implementación
**Archivo:** `src/recovery_g1/recovery_g1/recovery_g1.py`
- `_extract_rule_id(notes)` — defensivo, tolera None y vacío
- `_dispatch_recovery(..., notes: str = '')` — firma extendida con default
- Bloque causal insertado después de `attempt` definido, antes del mapeo `event_type`
- `_on_safety_action()` intacto — TX-011 gobernada sin cambio

## Evidencia
```
[4H-P1] cause=fallen route=direct_fallback action=wait_for_primary_restore
[4G-P4] ORCH_ACTION→RECOVERY tx=TX-011 latency_ms=1007.371  ← gobernada intacta
[4H-P1] cause=STALE target=/g1/imu action=wait_for_primary_restore
[4H-P1] cause=FREEZE target=/g1/imu action=operator_intervention
[4H-P1] cause=NANINF target=/g1/imu action=operator_intervention
```

---

# DT-4G-004 — Estado

| Sub-deuda | Estado | Descripción |
|---|---|---|
| DT-4G-004A | ✅ CERRADA | Teardown activo mata ACTIVE + publishers. No requiere restart entre corridas normales. |
| DT-4G-004B | 🔲 ABIERTA | Zombies `<defunct>` por PID1/reaper. ~2 por corrida. No bloqueante. Solución: `--init` flag Docker. |

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
| 64 | `colcon build --symlink-install` para build portable | Sin `--symlink-install` |
| 66 | Diseñar TX desde texto de informe, no código real | Auditar código antes de proponer |
| 67 | Tocar runtime safety para CI | Fix en el test |
| 68 | Test de estado inicial con launch completo | Aislar responsabilidades |
| 69 | Dedup por transition_id permanente | Ventana temporal 5s |
| 70 | Corridas formales sin preflight limpio | Preflight bloqueante |
| 71 | N≥10 sin limpiar contenedor | docker restart antes de batería formal |
| **72** | **Editar archivos con str.replace/heredoc sin verificar encoding** | **Leer texto exacto con `sed -n` antes de cualquier script de reemplazo** |
| **73** | **Mezclar dos causas en un solo harness** | **Una causa por harness, una variable por corrida** |

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
| DT-4G-002 | t1→t2 correlación por UUID/event_id (paper) | Media |
| DT-4G-004A | Teardown activo contenedor | ✅ CERRADA |
| **DT-4G-004B** | **Zombies `<defunct>` por PID1/reaper** | **Baja** |

---

# Qué Está Validado Realmente

**Sí validado:**
- Runtime 3C: 65 tests, CI green.
- Pipeline end-to-end (4F-4G): baseline sano→silencio; caída→alarma.
- Launcher unificado (4G-P1): arranque reproducible, preflight, teardown activo.
- Reproducibilidad caída inducida (4G-P2): N=10, 100% PASS.
- TX-011 ruta gobernada (4G-P2-C): N=13, 100% PASS.
- t0→t1 latencia (4G-P3-C): N=10, media=2474ms.
- t1→t2 ruta gobernada (4G-P4-D): N=10, media=1.19ms.
- Preflight bloqueante (4G-P5): laboratorio limpio garantizado.
- Teardown activo (DT-4G-004A): ya no requiere docker restart entre corridas normales.
- Recovery inteligente por causa (4H-P1): fallen/STALE/FREEZE/NANINF validados.

**NO validado:**
- TIMESTAMP en harness formal (pendiente).
- Thresholds definitivos.
- Control activo PD.
- UUID trazabilidad end-to-end t1→t2 (DT-4G-002).
- Reaper/PID1 boring_noether (DT-4G-004B).
- Recovery inteligente 4H-P2+ (TBD).

---

*G1 Deterministic Safety Runtime — CHAT_BOOTSTRAP_PROTOCOL v21*
*Actualizado: 2026-06-19*
*4E ✅ | 4F ✅ | 4G ✅ | 4H 🔄 | 4I 🔲 | 4J 🔲 | 5A 🔒*
