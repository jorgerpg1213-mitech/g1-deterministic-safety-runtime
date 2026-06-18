# G1 Deterministic Safety Runtime — CHAT BOOTSTRAP PROTOCOL
## Versión 19 — Actualizada 2026-06-18 (4G-P2-C CERRADA)

> **Cambios v19 vs v18:**
> - **4G-P2-C CERRADA**: TX-011 implementada, ruta gobernada observer→orchestrator→STABILITY_RISK/R3, N=13 100% PASS.
> - TX-011 contrato: `CONDITION_DETECTED + SECONDARY + EFFECTIVE + no (STABILITY_RISK,R3)`.
> - Fix CI: separación test estado inicial (orchestrator-only) vs visibilidad sistema completo.
> - Anti-patterns #66, #67, #68 añadidos.
> - DT-4G-001 cerrada. DT-4G-002, DT-4G-003 añadidas.
> - Próximo: 4G-P3 (t0→t1 clock sync Isaac↔ROS2).

---

# Estado Actual del Proyecto

```
Etapa 4E  — Baseline sano + validación                 ✅ CERRADA
Etapa 4F  — Safety Runtime Enrichment                  ✅ CERRADA
Etapa 4G  — Pipeline Hardening                         🔄 EN PROGRESO
  P0 repo nuevo / runtime paths                        ✅ CERRADA
  P1 launcher unificado                                ✅ CERRADA
  P2-A reproducibilidad baseline sano N=10             ✅ CERRADA
  P2-B reproducibilidad caída inducida + t1→t2         ✅ CERRADA (PASS parcial)
  P2-C TX-011 escalación gobernada SECONDARY/fallen    ✅ CERRADA (PASS completo)
  P3 t0→t1 sync clocks Isaac↔ROS2                      🔲 PENDIENTE
Etapa 5A  — Isaac Lab                                  🔒 FUERA DE RUTA / T4
```

**Repositorio:** github.com/jorgerpg1213-mitech/g1-deterministic-safety-runtime
**Commits recientes:** cierre N=13 | `07f9912` (fix tests) | `b4064ea` (TX-011) — `origin/main`
**VM:** ~/g1-deterministic-safety-runtime | boring_noether activo | CI Build ✅ CI Audit ✅

---

# INSTRUCCIÓN CRÍTICA PARA EL PRIMER MENSAJE

**4G-P2-C cerrada con PASS completo.**
- TX-011 implementada y validada: N=13, 100% PASS.
- Ruta gobernada observer→orchestrator→STABILITY_RISK/R3: operativa.
- CI: Build ✅ Audit ✅ — 65 tests total PASS.

**LO QUE FALTA (4G):**
- **4G-P3**: t0→t1 sync clocks Isaac↔ROS2. Diseño antes de implementar, aprobación PM antes de corridas.

**Primero: leer, auditar, diseñar. OK del PM antes de cualquier cambio de lógica safety.**

---

# CAMINO OPERATIVO CONFIRMADO — ISAAC SIM 4.5 (T4)

## Launcher unificado (RECOMENDADO desde 4G-P1, extendido en P2-B)
```bash
cd ~/g1-deterministic-safety-runtime && python3 sim_runtime/4G/launch_pipeline.py 2>&1 | tee /tmp/<fase>_run.log
```

**Precondición obligatoria:** `boring_noether` corriendo con `/ws` → repo nuevo.

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

## Terminal E — orchestrator (P2-B en adelante)
```bash
docker exec -it boring_noether bash -c "source /opt/ros/humble/setup.bash && \
  source /ws/install/setup.bash && \
  export RMW_IMPLEMENTATION=rmw_fastrtps_cpp && \
  export FASTRTPS_DEFAULT_PROFILES_FILE=/fastdds_udp.xml && \
  ros2 run safety_orchestrator_g1 safety_orchestrator_g1 \
  2>&1 | tee /ws/runs/<fase>/<fase>_E_orchestrator.log"
```

**ORDEN OBLIGATORIO:** A → esperar `P2+z0.720 SET` → B+C+D+E.
**RECOMENDADO:** usar `launch_pipeline.py`.

## Monitor de corridas P2-C
```bash
R=~/runs/4G && for d in $(ls -d $R/20260618_*/); do
  run=$(basename $d)
  fall=$(grep -l "FALL TRIGGER" $d/A_isaac.log 2>/dev/null | wc -l)
  obs=$(grep -l "SafetyEvent REAL" $d/B_observer.log 2>/dev/null | wc -l)
  tx=$(grep -l "TRANSICIÓN TX-011" $d/E_orchestrator.log 2>/dev/null | wc -l)
  echo "$run | FALL:$([ $fall -eq 1 ] && echo ✅ || echo ❌) | OBS:$([ $obs -eq 1 ] && echo ✅ || echo ❌) | TX011:$([ $tx -eq 1 ] && echo ✅ || echo ❌)"
done
```

---

# Contenedor boring_noether — estado confirmado

```
Imagen:       g1-ros-phase-b:humble
Network:      host
/ws mount:    ~/g1-deterministic-safety-runtime (repo nuevo)
fastdds:      ~/g1-deterministic-safety-runtime/sim_runtime/common/fastdds_udp.xml
Build:        sin --symlink-install (portabilidad cross-container)
Estado:       activo al cierre de sesión P2-C
Paquetes:     cross_consistency_observer, g1_msgs, recovery_g1,
              safety_orchestrator_g1, watchdog_g1 — todos operativos
```

**CRÍTICO:** Si `boring_noether` lleva muchas horas activo, los nodos ROS2 pueden tardar más de 10s en registrarse. Reiniciar el contenedor si aparecen corridas INVALID/INFRA por NODO FALTANTE.

---

# Launcher — estado P2-C

```
RUN_WINDOW_S      = 90
NODE_VERIFY_WAIT  = 10
EXPECTED_NODES    = [/cross_consistency_observer, /watchdog_g1,
                     /recovery_g1, /safety_orchestrator_g1]
EXPECTED_TOPICS   = [/g1/imu, /g1/contact/left, /g1/contact/right,
                     /joint_states, /safety_events, /system_state,
                     /safety_actions, /recovery_events]
```

---

# TX-011 — Implementación Completa

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

## Posición en evaluador
Después de TX-007, antes de TX-003 — en bloque ESCALATION paths.

## Guard anti-redisparo
```python
if state.compound_key() == ('STABILITY_RISK', 'R3'):
    return None
```

---

# Observer — estado real

```
FALLEN_W_CRITICAL    = 0.80
FALLEN_W_WARN        = 0.85
FALLEN_CONSECUTIVE_N = 3
event_type           = 'CONDITION_DETECTED'
source_authority     = 'SECONDARY'
authority_effectiveness = 'EFFECTIVE'  ← confirmado en código
```

---

# Estadística 4G-P2-C (N=13, ruta gobernada TX-011)

```
FALL_TRIGGER:          it=450, t=54.67s desde SET — determinista
Detection rate:        100% (13/13)
TX-011 rate:           100% (13/13)
t1→t2 ruta directa:   ~1ms (medición P2-B)
FP antes del trigger:  0
INVALID/INFRA:         1 corrida (081655, preflight timeout contenedor 16h+)
PASS rate formal:      100%
```

---

# Tests — estado al cierre P2-C

```
safety_orchestrator_g1:     63/63 PASS
test_g1_safety_layer:        2/2 PASS
  test_safety_layer_launch         — visibilidad sistema completo
  test_orchestrator_init_state     — INIT/SAFE/NONE orchestrator aislado
CI Build:                   ✅ GREEN
CI Audit:                   ✅ GREEN
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
| **66** | **Diseñar TX desde texto de informe, no desde código real** | **Auditar `_publish_fallen_safety_event` y `_eval_TX*` antes de cualquier propuesta** |
| **67** | **Tocar runtime safety para que pase un test de CI** | **Fix siempre en el test; runtime no se toca para satisfacer fixtures** |
| **68** | **Test de estado inicial con launch completo (4 nodos)** | **Aislar: orchestrator-only para INIT; launch completo para visibilidad** |

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
| DT-4F-005 | t0→t1 no medido | Alta |
| DT-4G-001 | TX-011 escalación gobernada SECONDARY/fallen | ✅ CERRADA |
| **DT-4G-002** | **t1→t2 correlación por UUID/event_id (paper)** | **Media** |
| **DT-4G-003** | **Ruta gobernada orchestrator→recovery no validada** | **Alta** |

---

# Qué Está Validado Realmente

**Sí validado:**
- Runtime 3C: 63 tests Level 4, CI green.
- Pipeline end-to-end (4F): baseline sano→silencio; caída→alarma; Isaac muerto→STALE→recovery.
- Launcher unificado (4G-P1): arranque reproducible, preflight, señal objetiva, teardown robusto.
- Reproducibilidad baseline sano (4G-P2-A): N=10, 100% PASS, 0 FP.
- Caída inducida determinista (4G-P2-B): it=450, t=54.67s, reproducible.
- Ruta directa observer→recovery (4G-P2-B): N=10, 100% PASS, latencia 1–156ms.
- **TX-011 ruta gobernada (4G-P2-C): N=13, 100% PASS, SAFE/NONE→STABILITY_RISK/R3.**

**NO validado:**
- Ruta gobernada orchestrator→recovery (DT-4G-003).
- t0→t1 latencia física→observer (4G-P3 pendiente).
- Thresholds definitivos.
- Control activo PD.
- UUID trazabilidad t1→t2 end-to-end.

---

*G1 Deterministic Safety Runtime — CHAT_BOOTSTRAP_PROTOCOL v19*
*Actualizado: 2026-06-18*
*4E ✅ | 4F ✅ | 4G-P0 ✅ | 4G-P1 ✅ | 4G-P2-A ✅ | 4G-P2-B ✅ | 4G-P2-C ✅ | 4G-P3 🔲 | 5A 🔒*
