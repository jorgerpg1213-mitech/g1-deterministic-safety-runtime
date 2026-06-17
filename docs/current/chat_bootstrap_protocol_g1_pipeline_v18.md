# G1 Deterministic Safety Runtime — CHAT BOOTSTRAP PROTOCOL
## Versión 18 — Actualizada 2026-06-17 (4G-P2-B CERRADA)

> **Cambios v18 vs v17:**
> - **4G-P2-B CERRADA**: ruta directa observer→recovery N=10, 100% PASS, latencia 1–156ms.
> - Launcher extendido: Terminal E orchestrator, `RUN_WINDOW_S=90`, 4 nodos, 8 topics.
> - Hallazgo arquitectónico: mismatch doble `event_type` + `source_authority` bloquea ruta gobernada.
> - Deuda formal añadida: DT-4G-001 / TX-011.
> - Anti-pattern #65 añadido.
> - Próximo: 4G-P2-C (TX-011 diseño + implementación).

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
  P2-C TX-011 escalación gobernada SECONDARY/fallen    🔲 PENDIENTE
  P3 t0→t1 sync clocks Isaac↔ROS2                      🔲 PENDIENTE
Etapa 5A  — Isaac Lab                                  🔒 FUERA DE RUTA / T4
```

**Repositorio:** github.com/jorgerpg1213-mitech/g1-deterministic-safety-runtime
**Commits recientes:** `86a32c6` (Terminal E + topics gobernados) | `497f0a4` (RUN_WINDOW_S=90) — `origin/main`
**VM:** ~/g1-deterministic-safety-runtime | boring_noether activo (reiniciado) | CI Build ✅ CI Audit ✅

---

# INSTRUCCIÓN CRÍTICA PARA EL PRIMER MENSAJE

**4G-P2-B cerrada con PASS parcial.**
- Ruta directa observer→recovery: probada, reproducible, N=10.
- Ruta gobernada observer→orchestrator→recovery: BLOQUEADA por mismatch doble de contrato.

**LO QUE FALTA (4G):**
- **4G-P2-C**: TX-011 — escalación gobernada para SECONDARY/fallen. **Diseño antes de implementar.** No tocar lógica safety sin propuesta aprobada por PM.
- **4G-P3**: t0→t1 sync clocks Isaac↔ROS2.

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

## Terminal E — orchestrator (4G-P2-B)
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

## Monitor de corridas P2-B
```bash
R=~/runs/4G && for d in $(ls -d $R/20260617_*/); do
  run=$(basename $d)
  fall=$(grep -l "FALL TRIGGER" $d/A_isaac.log 2>/dev/null | wc -l)
  obs=$(grep -l "SafetyEvent REAL" $d/B_observer.log 2>/dev/null | wc -l)
  rec=$(grep -l "source=cross_consistency_observer" $d/D_recovery.log 2>/dev/null | wc -l)
  echo "$run | FALL:$([ $fall -eq 1 ] && echo ✅ || echo ❌) | OBS:$([ $obs -eq 1 ] && echo ✅ || echo ❌) | REC:$([ $rec -eq 1 ] && echo ✅ || echo ❌)"
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
Estado:       reiniciado al cierre de sesión P2-B
Paquetes:     cross_consistency_observer, g1_msgs, recovery_g1,
              safety_orchestrator_g1, watchdog_g1 — todos operativos
```

---

# Launcher — estado P2-B

```
RUN_WINDOW_S      = 90       (caída a t=54.67s desde SET, ventana cubre ~42s+margen)
NODE_VERIFY_WAIT  = 10
EXPECTED_NODES    = [/cross_consistency_observer, /watchdog_g1,
                     /recovery_g1, /safety_orchestrator_g1]
EXPECTED_TOPICS   = [/g1/imu, /g1/contact/left, /g1/contact/right,
                     /joint_states, /safety_events, /system_state,
                     /safety_actions, /recovery_events]
```

**CRÍTICO:** Si `boring_noether` lleva muchas horas activo, los nodos ROS2 pueden tardar más de 10s en registrarse. Reiniciar el contenedor si aparecen corridas INVALID/INFRA por NODO FALTANTE.

---

# Hallazgo Arquitectónico P2-B — Mismatch de Contrato

## Contrato actual (observer → orchestrator)
```
Observer emite:
  event_type        = 'CONDITION_DETECTED'
  source_authority  = 'SECONDARY'

TX-001 del orchestrator exige:
  event_type        in ('STABILITY_ANOMALY', 'JOINT_OSCILLATION', 'IMU_OUT_OF_RANGE')
  source_authority  in ('PRIMARY_IMU', 'PRIMARY_JOINT_STATES')
```

## Consecuencia
El orchestrator recibe el evento, publica ACK (`SCHEDULED`) a `/safety_events`, pero el evaluador retorna None → no hay transición → no hay `/system_state` nuevo → no hay escalación gobernada.

## Deuda formal: DT-4G-001 / TX-011
Crear transición explícita para `SECONDARY + STABILITY_ANOMALY/fallen/no-support`. Diseño antes de implementar. No es un bug de infraestructura — es una decisión de política de severidad pendiente.

---

# Observer — estado real

```
FALLEN_W_CRITICAL    = 0.80   # CRITICAL: abs_w < 0.80 O ambos pies perdidos
FALLEN_W_WARN        = 0.85   # WARN: inclinación moderada O un pie perdido
FALLEN_CONSECUTIVE_N = 3      # muestras frescas consecutivas para CRITICAL
event_type           = 'CONDITION_DETECTED'   ← mismatch con TX-001
source_authority     = 'SECONDARY'            ← mismatch con TX-001
```

# Estadística 4G-P2-B (N=10, caída inducida)

```
FALL_TRIGGER:          it=450, t=54.67s desde SET — determinista
Detection rate:        100% (10/10)
Recovery react rate:   100% (10/10) — ruta directa /safety_events
t1→t2 ruta directa:   1.3 – 156ms (típico 3–60ms)
FP antes del trigger:  0
INVALID/INFRA:         4 corridas (timeout nodos, contenedor 7h+)
PASS rate formal:      100%
```

---

# Anti-Patterns Acumulados (selección)

| # | Anti-pattern | Corrección |
|---|---|---|
| 54 | Reconstruir docker run de memoria | Usar comando confirmado en bootstrap |
| 60 | Lanzar B/C/D antes de que Isaac esté listo | A primero → esperar SET → luego B+C+D+E |
| 62 | Kill masivo mata contenedor ROS2 | Reconstruir boring_noether + rebuild tras kill |
| 63 | No verificar sintaxis antes de copiar al contenedor | ast.parse antes de docker cp |
| 64 | `colcon build --symlink-install` para build portable | Usar sin `--symlink-install` para mounts cross-container |
| **65** | **Cambiar `event_type` sin verificar `source_authority` en la TX destino** | **Auditar todos los campos requeridos por la TX antes de proponer diff** |

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
| **DT-4G-001** | **TX-011: escalación gobernada SECONDARY/fallen pendiente** | **Alta** |

---

# Qué Está Validado Realmente

**Sí validado:**
- Runtime 3C: 86 tests Level 4, CI green.
- Pipeline end-to-end (4F): baseline sano→silencio; caída→alarma; Isaac muerto→STALE→recovery.
- Launcher unificado (4G-P1): arranque reproducible, preflight, señal objetiva, teardown robusto.
- Reproducibilidad baseline sano (4G-P2-A): N=10, 100% PASS, 0 FP.
- Caída inducida determinista (4G-P2-B): it=450, t=54.67s, reproducible.
- Ruta directa observer→recovery (4G-P2-B): N=10, 100% PASS, latencia 1–156ms.
- Orchestrator vivo y conectado: recibe eventos, publica ACK al topic.

**NO validado:**
- Ruta gobernada observer→orchestrator→recovery (TX-011 pendiente).
- t0→t1 latencia física→observer.
- Thresholds definitivos.
- Control activo PD.
- Isaac Lab en T4.

---

*G1 Deterministic Safety Runtime — CHAT_BOOTSTRAP_PROTOCOL v18*
*Actualizado: 2026-06-17*
*4E ✅ | 4F ✅ | 4G-P0 ✅ | 4G-P1 ✅ | 4G-P2-A ✅ | 4G-P2-B ✅ | 4G-P2-C 🔲 | 5A 🔒*
