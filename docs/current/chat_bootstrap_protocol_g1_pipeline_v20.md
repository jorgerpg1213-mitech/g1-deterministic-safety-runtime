# G1 Deterministic Safety Runtime — CHAT BOOTSTRAP PROTOCOL
## Versión 20 — Actualizada 2026-06-18 (4G CERRADA TÉCNICAMENTE)

> **Cambios v20 vs v19:**
> - **4G-P3-C CERRADA**: t0→t1 N=10, 100% PASS, media=2474.60ms.
> - **4G-P3-D CERRADA**: t1→t2 N=10, 100% PASS, media=1.19ms, ruta gobernada.
> - **4G-P4-A/B/C/D CERRADAS**: ruta gobernada orchestrator→recovery validada N=10.
> - **4G-P5 CERRADA**: preflight bloqueante + post-teardown hygiene.
> - **DT-4G-003 CERRADA**. DT-4G-004 añadida.
> - Anti-patterns #69, #70, #71 añadidos.
> - Errata P2-C documentada: disparador real abs_w=0.713 < 0.80 por orientación, no por both_lost.
> - Próximo: 4H-P1 (recovery inteligente por causa).

---

# Estado Actual del Proyecto

```
Etapa 4E  — Baseline sano + validación                 ✅ CERRADA
Etapa 4F  — Safety Runtime Enrichment                  ✅ CERRADA
Etapa 4G  — Pipeline Hardening                         ✅ CERRADA TÉCNICAMENTE
  P0 repo nuevo / runtime paths                        ✅ CERRADA
  P1 launcher unificado                                ✅ CERRADA
  P2-A reproducibilidad baseline sano N=10             ✅ CERRADA
  P2-B reproducibilidad caída inducida + t1→t2         ✅ CERRADA
  P2-C TX-011 escalación gobernada SECONDARY/fallen    ✅ CERRADA N=13
  P3-A diseño instrumentación t0→t1                    ✅ CERRADA
  P3-B piloto t0→t1                                    ✅ CERRADA
  P3-C t0→t1 N=10                                      ✅ CERRADA media=2474.60ms
  P3-D t1→t2 ruta gobernada N=10                       ✅ CERRADA media=1.19ms
  P4-A auditoría orchestrator→recovery                 ✅ CERRADA
  P4-B diseño subscriber /safety_actions               ✅ CERRADA
  P4-C piloto ruta gobernada                           ✅ CERRADA
  P4-D N=10 ruta gobernada                             ✅ CERRADA 100% PASS
  P5 preflight bloqueante + hygiene                    ✅ CERRADA
Etapa 4H  — Recovery Inteligente                       🔲 PENDIENTE
Etapa 4I  — Formalización                              🔲 PENDIENTE
Etapa 4J  — Paper Prep                                 🔲 PENDIENTE
Etapa 5A  — Isaac Lab                                  🔒 FUERA DE RUTA / T4
```

**Repositorio:** github.com/jorgerpg1213-mitech/g1-deterministic-safety-runtime
**HEAD:** `0c25f38` — CI Build ✅ CI Audit ✅
**VM:** ~/g1-deterministic-safety-runtime | boring_noether activo

---

# INSTRUCCIÓN CRÍTICA PARA EL PRIMER MENSAJE

**4G cerrada técnicamente. Próximo: 4H-P1.**

**LO QUE SE VALIDÓ EN ESTA SESIÓN:**
- t0→t1 físico→SafetyEvent: N=10, 100% PASS, media=2474ms
- t1→t2 ruta gobernada orchestrator→recovery: N=10, 100% PASS, media=1.19ms
- Preflight bloqueante: laboratorio limpio garantizado antes de cada corrida
- DT-4G-003 cerrada: ruta gobernada orchestrator→recovery operativa

**DEUDA NUEVA DT-4G-004:**
`docker restart boring_noether` requerido entre corridas — teardown no limpia procesos dentro del contenedor. Diferido, no bloquea 4H.

**Primero: leer, auditar, diseñar. OK del PM antes de cualquier cambio de lógica safety.**

---

# CAMINO OPERATIVO CONFIRMADO — ISAAC SIM 4.5 (T4)

## Launcher unificado (con preflight bloqueante desde P5)
```bash
cd ~/g1-deterministic-safety-runtime && python3 sim_runtime/4G/launch_pipeline.py 2>&1 | tee /tmp/<fase>_run.log
```

**Precondición obligatoria P5:** `docker restart boring_noether && sleep 15` antes de cada corrida hasta que DT-4G-004 esté resuelta.

**Preflight verifica:**
1. Paths requeridos
2. Repo limpio (o --allow-dirty)
3. boring_noether corriendo
4. /ws/install/setup.bash presente
5. **0 procesos safety residuales en contenedor** ← NUEVO P5
6. **0 publishers en /safety_events** ← NUEVO P5

## Comando de lanzamiento MANUAL — Terminal A (solo si launcher no aplica)
```bash
cd ~/g1-deterministic-safety-runtime && timeout 600 docker run --rm --gpus all --network=host \
  -e ACCEPT_EULA=Y -e PRIVACY_CONSENT=Y -e OMNI_KIT_ALLOW_ROOT=1 \
  -e RMW_IMPLEMENTATION=rmw_fastrtps_cpp \
  -e FASTRTPS_DEFAULT_PROFILES_FILE=/fastdds_udp.xml \
  -e PYTHONPATH=/g1msgs/local/lib/python3.10/dist-packages:/isaac-sim/exts/isaacsim.ros2.bridge/humble/rclpy \
  -e LD_LIBRARY_PATH=/isaac-sim/exts/isaacsim.ros2.bridge/humble/lib:/g1msgs/lib \
  -v ~/g1-deterministic-safety-runtime/sim_runtime/common/fastdds_udp.xml:/fastdds_udp.xml:ro \
  -v ~/g1-deterministic-safety-runtime/install/g1_msgs:/g1msgs:ro \
  -v ~/docker/isaac-sim/cache/kit:/isaac-sim/kit/cache:rw \
  -v ~/docker/isaac-sim/cache/ov:/root/.cache/ov:rw \
  -v ~/docker/isaac-sim/cache/pip:/root/.cache/pip:rw \
  -v ~/docker/isaac-sim/cache/glcache:/root/.cache/nvidia/GLCache:rw \
  -v ~/docker/isaac-sim/cache/computecache:/root/.nv/ComputeCache:rw \
  -v ~/g1-deterministic-safety-runtime/sim_runtime/4F/combo_single.kit:/isaac-sim/apps/combo_single.kit:ro \
  -v ~/g1-deterministic-safety-runtime/sim_runtime/4F/g1ext_combo:/g1ext:ro \
  --entrypoint /isaac-sim/kit/kit nvcr.io/nvidia/isaac-sim:4.5.0 \
  /isaac-sim/apps/combo_single.kit --no-window --allow-root \
  --ext-folder /isaac-sim/apps --ext-folder /g1ext \
  2>&1 | tee ~/runs/<fase>/<fase>_A_isaac.log
```

## Monitor de corridas P3/P4
```bash
python3 ~/g1-deterministic-safety-runtime/sim_runtime/4G/analyze_runs.py --phase p3b --since <TIMESTAMP> 2>/dev/null
```

---

# Contenedor boring_noether — estado confirmado

```
Imagen:       g1-ros-phase-b:humble
Network:      host
/ws mount:    ~/g1-deterministic-safety-runtime (repo nuevo)
fastdds:      ~/g1-deterministic-safety-runtime/sim_runtime/common/fastdds_udp.xml
Build:        sin --symlink-install (portabilidad cross-container)
Estado:       activo al cierre de sesión
Paquetes:     cross_consistency_observer, g1_msgs, recovery_g1,
              safety_orchestrator_g1, watchdog_g1 — todos operativos
```

**CRÍTICO:** `docker restart boring_noether` requerido entre corridas formales hasta que DT-4G-004 esté resuelta. El preflight bloqueante abortará si hay residuos.

---

# Launcher — estado P5

```
RUN_WINDOW_S      = 90
NODE_VERIFY_WAIT  = 10
EXPECTED_NODES    = [/cross_consistency_observer, /watchdog_g1,
                     /recovery_g1, /safety_orchestrator_g1]
EXPECTED_TOPICS   = [/g1/imu, /g1/contact/left, /g1/contact/right,
                     /joint_states, /safety_events, /system_state,
                     /safety_actions, /recovery_events]
PREFLIGHT_BLOCKS  = [0 procesos safety residuales, 0 publishers /safety_events]
POST_TEARDOWN     = hygiene check observacional (no bloquea exit code)
```

---

# TX-011 — Implementación Completa (desde P2-C)

## Contrato
```
event_type           = 'CONDITION_DETECTED'
source_authority     = 'SECONDARY'
authority_effectiveness = 'EFFECTIVE'
estado_origen        = cualquiera excepto ('STABILITY_RISK', 'R3')
```

## Resultado
```
transition_id        = 'TX-011'
runtime_action       = 'stabilization_mode'
target_risk_level    = 'STABILITY_RISK'
target_restriction_level = 'R3'
execution_confidence = 'BEST_EFFORT'
transition_priority  = 'NORMAL'
```

---

# Ruta Gobernada Orchestrator→Recovery (desde P4-C)

## Flujo validado
```
Observer → SafetyEvent → Orchestrator → TX-011 → SafetyAction(/safety_actions)
                                                        ↓
                                              recovery_g1._on_safety_action()
                                                        ↓
                                              ORCH_ACTION→RECOVERY log
                                                        ↓
                                              _dispatch_recovery()
```

## Contrato _on_safety_action
```
action_name          = 'stabilization_mode'
transition_id        = 'TX-011'
execution_authority  = 'AUTONOMOUS'
guard                = ventana temporal 5s anti-doble ejecución
log                  = ORCH_ACTION→RECOVERY route=orchestrator_safety_action ...
```

## Ruta directa (fallback activo)
Observer → SafetyEvent → recovery_g1._on_safety_event() — sigue activa como fallback no determinista.

---

# Métricas de Latencia Validadas

```
t0→t1  evento físico → SafetyEvent
       P3-C N=10: media=2474.60ms, min=2046.47ms, max=3511.02ms
       P4-D N=10: media=2583.61ms, min=2055.00ms, max=3009.17ms
       Incluye: dinámica física + sensores + DDS + 3 snapshots 3C2b

t1→t2  SafetyEvent → recovery action (ruta gobernada)
       P4-D N=10: media=1.19ms, min=0.83ms, max=2.02ms
       Fuente: orchestrator SafetyAction timestamp → recovery t2
```

---

# Observer — estado real

```
FALLEN_W_CRITICAL    = 0.80
FALLEN_W_WARN        = 0.85
FALLEN_CONSECUTIVE_N = 3
event_type           = 'CONDITION_DETECTED'
source_authority     = 'SECONDARY'
authority_effectiveness = 'EFFECTIVE'
Docstring:           alineado con código real (commit dde0ea3)
```

---

# Tests — estado al cierre P5

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
| 60 | Lanzar B/C/D antes de que Isaac esté listo | A primero → esperar SET → luego B+C+D+E |
| 62 | Kill masivo mata contenedor ROS2 | Reconstruir boring_noether + rebuild tras kill |
| 63 | No verificar sintaxis antes de copiar al contenedor | ast.parse antes de docker cp |
| 64 | `colcon build --symlink-install` para build portable | Usar sin `--symlink-install` |
| 65 | Cambiar `event_type` sin verificar `source_authority` en TX destino | Auditar todos los campos requeridos antes de proponer diff |
| 66 | Diseñar TX desde texto de informe, no desde código real | Auditar `_publish_fallen_safety_event` y `_eval_TX*` antes de cualquier propuesta |
| 67 | Tocar runtime safety para que pase un test de CI | Fix siempre en el test |
| 68 | Test de estado inicial con launch completo (4 nodos) | Aislar: orchestrator-only para INIT; launch completo para visibilidad |
| **69** | **Dedup de safety action por transition_id permanente** | **Usar ventana temporal 5s — transition_id se repite entre corridas** |
| **70** | **Correr corridas formales sin verificar laboratorio limpio** | **Preflight bloqueante: 0 procesos + 0 publishers antes de arrancar** |
| **71** | **N≥10 en loop sin limpiar contenedor entre corridas** | **docker restart boring_noether antes de cada corrida hasta DT-4G-004** |

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
| DT-4G-001 | TX-011 escalación gobernada SECONDARY/fallen | ✅ CERRADA |
| DT-4G-002 | t1→t2 correlación por UUID/event_id (paper) | Media |
| DT-4G-003 | Ruta gobernada orchestrator→recovery | ✅ CERRADA |
| **DT-4G-004** | **Teardown activo contenedor (docker restart requerido)** | **Media** |

---

# Qué Está Validado Realmente

**Sí validado:**
- Runtime 3C: 65 tests, CI green.
- Pipeline end-to-end (4F): baseline sano→silencio; caída→alarma; Isaac muerto→STALE→recovery.
- Launcher unificado (4G-P1): arranque reproducible, preflight, señal objetiva, teardown robusto.
- Reproducibilidad baseline sano (4G-P2-A): N=10, 100% PASS, 0 FP.
- Caída inducida determinista (4G-P2-B): it=450, t=54.67s, reproducible.
- Ruta directa observer→recovery (4G-P2-B): N=10, 100% PASS.
- TX-011 ruta gobernada (4G-P2-C): N=13, 100% PASS.
- t0→t1 latencia física→SafetyEvent (4G-P3-C): N=10, media=2474ms.
- t1→t2 ruta gobernada orchestrator→recovery (4G-P4-D): N=10, media=1.19ms.
- Preflight bloqueante laboratorio limpio (4G-P5): validado N=10.

**NO validado:**
- Thresholds definitivos.
- Control activo PD.
- UUID trazabilidad end-to-end t1→t2 (DT-4G-002).
- Teardown activo dentro del contenedor (DT-4G-004).
- Recovery inteligente por causa (4H pendiente).

---

*G1 Deterministic Safety Runtime — CHAT_BOOTSTRAP_PROTOCOL v20*
*Actualizado: 2026-06-18*
*4E ✅ | 4F ✅ | 4G ✅ | 4H 🔲 | 4I 🔲 | 4J 🔲 | 5A 🔒*
