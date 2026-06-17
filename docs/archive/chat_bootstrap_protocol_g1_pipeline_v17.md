# G1 Deterministic Safety Runtime — CHAT BOOTSTRAP PROTOCOL
## Versión 17 — Actualizada 2026-06-17 (4G-P0+P1+P2-A CERRADAS)

> **Cambios v17 vs v16:**
> - **4G-P0 CERRADA**: repo viejo eliminado, build portable sin symlinks, CI hardening.
> - **4G-P1 CERRADA**: launcher unificado `sim_runtime/4G/launch_pipeline.py`.
> - **4G-P2-A CERRADA**: N=10 PASS, 0 FP, estadística reproducible.
> - `boring_noether` recreado: `/ws` → repo nuevo, build sin `--symlink-install`.
> - PYTHONPATH Isaac corregido con bridge rclpy.
> - Shutdown idempotente en extensión Isaac.
> - Anti-pattern #64 añadido.
> - DT-4D-017: CERRADA.
> - Próximo: 4G-P2-B (caída inducida + t1→t2).

---

# Estado Actual del Proyecto

```
Etapa 4E  — Baseline sano + validación                 ✅ CERRADA
Etapa 4F  — Safety Runtime Enrichment                  ✅ CERRADA
Etapa 4G  — Pipeline Hardening                         🔄 EN PROGRESO
  P0 repo nuevo / runtime paths                        ✅ CERRADA
  P1 launcher unificado                                ✅ CERRADA
  P2-A reproducibilidad baseline sano N=10             ✅ CERRADA
  P2-B reproducibilidad caída inducida + t1→t2         🔲 PENDIENTE
  P3 t0→t1 sync clocks Isaac↔ROS2                      🔲 PENDIENTE
Etapa 5A  — Isaac Lab                                  🔒 FUERA DE RUTA / T4
```

**Repositorio:** github.com/jorgerpg1213-mitech/g1-deterministic-safety-runtime
**Commits recientes:** `ce9b715` (analyze_runs --since) | `7a604ab` (isaac_ok + shutdown) | `715d362` (launcher) — `origin/main`
**VM:** ~/g1-deterministic-safety-runtime | boring_noether activo | CI Build ✅ CI Audit ✅

---

# INSTRUCCIÓN CRÍTICA PARA EL PRIMER MENSAJE

**4G-P0, P1 y P2-A cerradas.** Pipeline reproducible N=10, 0 FP, tiempos estables.

**LO QUE FALTA (4G):**
- **4G-P2-B**: reproducibilidad con caída inducida. Diseñar protocolo antes de correr. Medir t1→t2 con N≥10.
- **4G-P3**: t0→t1 sync clocks Isaac↔ROS2. Definir t0 antes de medir.

**Primero: leer, auditar, planear. OK del PM antes de cualquier corrida.**

---

# CAMINO OPERATIVO CONFIRMADO — ISAAC SIM 4.5 (T4)

## Launcher unificado (RECOMENDADO desde 4G-P1)
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

**CAMBIO vs v16:** `g1_msgs` ahora desde `~/g1-deterministic-safety-runtime/install/g1_msgs` (repo nuevo).
**CAMBIO vs v16:** PYTHONPATH incluye `/isaac-sim/exts/isaacsim.ros2.bridge/humble/rclpy` (fix FootContact).

## Terminal B — observer
```bash
docker exec -it boring_noether bash -c "source /opt/ros/humble/setup.bash && \
  source /ws/install/setup.bash && \
  export RMW_IMPLEMENTATION=rmw_fastrtps_cpp && \
  export FASTRTPS_DEFAULT_PROFILES_FILE=/fastdds_udp.xml && \
  ros2 run cross_consistency_observer cross_consistency_observer \
  --ros-args -r /imu:=/g1/imu 2>&1 | tee /ws/runs/<fase>/<fase>_B_observer.log"
```

## Terminal C — watchdog
```bash
docker exec -it boring_noether bash -c "source /opt/ros/humble/setup.bash && \
  source /ws/install/setup.bash && \
  export RMW_IMPLEMENTATION=rmw_fastrtps_cpp && \
  export FASTRTPS_DEFAULT_PROFILES_FILE=/fastdds_udp.xml && \
  ros2 run watchdog_g1 watchdog_g1 2>&1 | tee /ws/runs/<fase>/<fase>_C_watchdog.log"
```

## Terminal D — recovery
```bash
docker exec -it boring_noether bash -c "source /opt/ros/humble/setup.bash && \
  source /ws/install/setup.bash && \
  export RMW_IMPLEMENTATION=rmw_fastrtps_cpp && \
  export FASTRTPS_DEFAULT_PROFILES_FILE=/fastdds_udp.xml && \
  ros2 run recovery_g1 recovery_g1 2>&1 | tee /ws/runs/<fase>/<fase>_D_recovery.log"
```

**ORDEN OBLIGATORIO:** A primero → esperar `=== P2+z0.720 SET ===` → lanzar B+C+D.
**RECOMENDADO:** usar `launch_pipeline.py` en lugar de las 4 terminales manuales.

## Analizador de corridas (4G-P2)
```bash
python3 sim_runtime/4G/analyze_runs.py --since YYYYMMDD_HHMMSS
```

---

# Contenedor boring_noether — estado confirmado

```
Imagen:       g1-ros-phase-b:humble
Network:      host
/ws mount:    ~/g1-deterministic-safety-runtime (repo nuevo)
fastdds:      ~/g1-deterministic-safety-runtime/sim_runtime/common/fastdds_udp.xml
Build:        sin --symlink-install (portabilidad cross-container)
Paquetes:     cross_consistency_observer, g1_msgs, recovery_g1,
              safety_orchestrator_g1, watchdog_g1 — todos operativos
```

**CRÍTICO:** Si `boring_noether` muere o se recrea, debe montarse con `/ws` → repo nuevo
y rebuildearse SIN `--symlink-install`. Con symlinks Isaac no puede importar FootContact.

---

# Observer — estado real

```
FALLEN_W_CRITICAL    = 0.80   # CRITICAL: abs_w < 0.80 O ambos pies perdidos
FALLEN_W_WARN        = 0.85   # WARN: inclinación moderada O un pie perdido
FALLEN_CONSECUTIVE_N = 3      # muestras frescas consecutivas para CRITICAL
```

# Watchdog — estado real

```
STALE_TIMEOUT_S       = 1.0
STALE_CRITICAL_S      = 3.0
STARTUP_GRACE_S       = 15.0
FREEZE_N              = 5
MIN_RATE_HZ           = 3.0
RATE_WARMUP_N         = 5
CRITICAL_STALE_TOPICS = {'/g1/imu', '/g1/contact/left', '/g1/contact/right'}
NO_FREEZE_TOPICS      = {'/g1/contact/left', '/g1/contact/right'}
```

# Estadística 4G-P2-A (N=10, baseline sano)

```
t Isaac→marker:    min=34s  media=35.4s  std=1.0s  max=36s  p95=36s
t marker→B/C/D:   min=12s  media=12.5s  std=0.5s  max=13s  p95=13s
t total→PASS:     min=47s  media=48.4s  std=1.0s  max=49s  p95=49s
FP observer:      0
FP watchdog:      0
Recovery react:   0
PASS rate:        100%
```

---

# Anti-Patterns Acumulados (selección)

| # | Anti-pattern | Corrección |
|---|---|---|
| 54 | Reconstruir docker run de memoria | Usar comando confirmado en bootstrap |
| 57 | Parchear variable por variable | Reescribir bloque autocontenido + ast.parse |
| 60 | Lanzar B/C/D antes de que Isaac esté listo | A primero → esperar SET → luego B+C+D |
| 61 | No auditar umbral antes de correr | Revisar logs anteriores antes de cada corrida |
| 62 | Kill masivo mata contenedor ROS2 | Reconstruir boring_noether + rebuild tras kill |
| 63 | No verificar sintaxis antes de copiar al contenedor | ast.parse antes de docker cp |
| **64** | **`colcon build --symlink-install` para build portable** | **Usar `colcon build` sin `--symlink-install` cuando el install/ se monta en otro contenedor** |

---

# Deuda Técnica Activa

| ID | Deuda | Prioridad |
|---|---|---|
| ~~DT-4D-017~~ | ~~Launcher no unificado; g1_msgs en repo viejo~~ | ~~Media~~ CERRADA |
| DT-4E-001 | SAFETY_MODEL_G1.md ausente | Alta |
| DT-4E-006 | Control PD diferido | Alta |
| DT-4F-001 | Thresholds pragmáticos | Media |
| DT-4F-002 | TX-006b/c sin test explícito | Media |
| DT-4F-003 | TX-009 POLICY_GATED exacta | Baja |
| DT-4F-004 | FREEZE IMU falso positivo potencial | Media |
| DT-4F-005 | t0→t1 no medido | Alta |

---

# Qué Está Validado Realmente

**Sí validado:**
- Runtime 3C: 86 tests Level 4, CI green.
- Pipeline end-to-end (4F): baseline sano→silencio; caída→alarma; Isaac muerto→STALE→recovery.
- Latencia t1→t2: 0.68–8.2ms en T4 (2 corridas 4F).
- Fault injection (4F-P6): 5/5 PASS con control negativo limpio.
- Launcher unificado (4G-P1): arranque reproducible, preflight, señal objetiva, teardown robusto.
- Reproducibilidad baseline sano (4G-P2-A): N=10, 100% PASS, 0 FP.
- Portabilidad cross-container g1_msgs: sin symlinks, FootContact importable en Isaac.

**NO validado:**
- t0→t1 latencia física→observer.
- Reproducibilidad con caída inducida (4G-P2-B).
- Thresholds definitivos.
- Reproducibilidad estadística t1→t2 con N≥10.
- Control activo PD.
- Isaac Lab en T4.

---

*G1 Deterministic Safety Runtime — CHAT_BOOTSTRAP_PROTOCOL v17*
*Actualizado: 2026-06-17*
*4E ✅ | 4F ✅ | 4G-P0 ✅ | 4G-P1 ✅ | 4G-P2-A ✅ | 4G-P2-B 🔲 | 5A 🔒*
