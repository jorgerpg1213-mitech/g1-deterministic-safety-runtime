# G1 ROS2 Pipeline — CHAT BOOTSTRAP PROTOCOL
## Guía de Arranque para Nuevas Sesiones / Nuevos LLMs
## Versión 15 — Actualizada 2026-06-16 (4E cerrada + 4F P1→P5)

**Objetivo:** garantizar continuidad técnica, rigor operacional y preservación del criterio arquitectónico del proyecto G1 ROS2 Pipeline.

> **Cambios v15 vs v14:**
> - **4E CERRADA**: baseline sano pasivo, observer sin falsos positivos, transición capturada. 4E-P5 (PD activo) diferido.
> - **4F abierta y avanzada (P1→P5)**: observer con severidad ✅, watchdog ✅, transition matrix ✅, recovery integrado ✅, latencia medida ✅.
> - Deudas nuevas DT-4F-001…005. Anti-patterns #60–#62.
> - Próximo: 4F-P6 (fault injection), launcher unificado, reproducibilidad.

---

# Estado Actual del Proyecto

```
Etapa 3C  — Deterministic Safety Runtime Framework     ✅ CERRADA
Etapa 4A  — Infrastructure & DDS                       ✅ CERRADA
Etapa 4B  — Isaac Headless Bring-up (4.2.0)            ✅ CERRADA
Etapa 4C  — Caracterización Física y de Control        ✅ CERRADA
Etapa 4D  — ROS2 Feasibility + Observabilidad + Lazo   ✅ CERRADA
Etapa 4E  — Baseline sano + validación                 ✅ CERRADA
  P2 pose geométrica                                   ✅
  P3 control PD (vías simples)                         ❌ NEGATIVO
  P4E baseline sano PASIVO (P2+z0.720)                 ✅
  P4F observer sin falsos positivos                    ✅
  P4G transición sano→caída capturada                  ✅
  P5 control activo PD                                 🔲 DIFERIDO
Etapa 4F  — Safety Runtime Enrichment                  🔄 EN PROGRESO
  P1 observer con severidad INFO/WARN/CRITICAL         ✅
  P2 watchdog STALE/FREEZE/NANINF/TIMESTAMP/RATE       ✅
  P3 TRANSITION_MATRIX_G1.md audit artifact            ✅
  P4 recovery integrado — pipeline 4 terminales        ✅
  P5 latencia t1→t2 0.68–8.2ms en T4                  ✅
  P6 fault injection matrix                            🔲 PENDIENTE
Etapa 5A  — Isaac Lab                                  🔒 FUERA DE RUTA / T4
```

**Repositorio:** github.com/jorgerpg1213-mitech/g1-ros2-pipeline
**Commits recientes:** `f34d95b` (4F-P1) | `562c9ba` (4F-P2) | `875838b` (watchdog grace) | `9eef532` (umbral) | fix severity | recovery latency — todos en `origin/main`.
**VM:** Ubuntu 22.04.5 LTS | Tesla T4 16GB | Docker 29.1.3 | CUDA 13.0

---

# INSTRUCCIÓN CRÍTICA PARA EL PRIMER MENSAJE

**4F tiene P1→P5 completas.** El pipeline end-to-end funciona con 4 componentes simultáneos: Isaac (robot) + observer (detecta caída) + watchdog (detecta degradación de señal) + recovery (reacciona). Latencia t1→t2 medida: 0.68–8.2ms en T4.

**LO QUE FALTA:**
- **4F-P6:** fault injection matrix — una falla sintética por corrida (IMU congelada, NaN, etc.) para validar robustez del watchdog.
- **Launcher unificado:** script que levante las 4 terminales en orden correcto.
- **Reproducibilidad:** N≥5 corridas con estadísticas de latencia.
- **DT-4F-005:** t0→t1 sync de clocks Isaac↔ROS2.

**Primero: leer, auditar, planear. OK del PM antes de cualquier corrida o cambio.**

---

# Filosofía Operacional

Estándar MIT / NASA / Boston Dynamics. Toda propuesta diferencia: evidencia observada vs hipótesis. El objetivo NO es "parecer robusto" sino que el sistema sea exactamente tan robusto como afirma.

**Anti-patrón supremo:** creer que el sistema está más validado de lo que está.

**Lección dura de la sesión 4F:** auditar el umbral/lógica ANTES de correr — `w=0.714 > 0.75` era visible en logs anteriores y se quemaron corridas por no revisarlo. Inspeccionar antes de ejecutar siempre.

---

# Estructura del Equipo

| Rol | Responsable |
|---|---|
| PM Técnico | ChatGPT |
| Implementador / Auditor | Claude |
| Operador | Jorge Padilla |

---

# Reglas de Operación

1. **Máximo 2 comandos por mensaje.**
2. **Esperar output real.** No asumir estado.
3. **No sobredeclarar validación.**
4. **Una variable nueva por experimento.**
5. **No parchear componentes bloqueados** sin definir contratos.
6. **Auditar antes de correr** — revisar logs anteriores, umbrales, lógica.
7. **Orden de arranque:** A (Isaac) primero → esperar `P2+z0.720 SET` → luego B+C+D.
8. **Verificar estado VM:** `docker ps && df -h / && nvidia-smi`.
9. **Carpeta `~/runs/<fase>/` autocontenida.**
10. **Solo afirmar lo que el log demuestra.**
11. **No reconstruir docker run de memoria** (DT-4D-017).
12. **Inspeccionar USD/modelo ANTES de tunear control.**
13. **Reescribir bloques inyectados autocontenidos** + `ast.parse` + grep.

---

# CAMINO OPERATIVO CONFIRMADO — ISAAC SIM 4.5 (T4)

## Comando de lanzamiento CONFIRMADO (Terminal A)
```bash
cd ~/g1-ros2-pipeline && timeout 600 docker run --rm --gpus all --network=host \
  -e ACCEPT_EULA=Y -e PRIVACY_CONSENT=Y -e OMNI_KIT_ALLOW_ROOT=1 \
  -e RMW_IMPLEMENTATION=rmw_fastrtps_cpp \
  -e FASTRTPS_DEFAULT_PROFILES_FILE=/fastdds_udp.xml \
  -e PYTHONPATH=/g1msgs/local/lib/python3.10/dist-packages \
  -e LD_LIBRARY_PATH=/isaac-sim/exts/isaacsim.ros2.bridge/humble/lib:/g1msgs/lib \
  -v ~/runs/4d3b2/fastdds_udp.xml:/fastdds_udp.xml:ro \
  -v ~/g1-deterministic-safety-runtime/install/g1_msgs:/g1msgs:ro \
  -v ~/docker/isaac-sim/cache/kit:/isaac-sim/kit/cache:rw \
  -v ~/docker/isaac-sim/cache/ov:/root/.cache/ov:rw \
  -v ~/docker/isaac-sim/cache/pip:/root/.cache/pip:rw \
  -v ~/docker/isaac-sim/cache/glcache:/root/.cache/nvidia/GLCache:rw \
  -v ~/docker/isaac-sim/cache/computecache:/root/.nv/ComputeCache:rw \
  -v ~/runs/4d3c2a/combo_single.kit:/isaac-sim/apps/combo_single.kit:ro \
  -v ~/runs/4d3c2a/g1ext_combo:/g1ext:ro \
  --entrypoint /isaac-sim/kit/kit nvcr.io/nvidia/isaac-sim:4.5.0 \
  /isaac-sim/apps/combo_single.kit --no-window --allow-root \
  --ext-folder /isaac-sim/apps --ext-folder /g1ext \
  2>&1 | tee ~/runs/4d3c2b/<fase>_A_isaac.log
```

## Terminal B — observer
```bash
docker exec -it boring_noether bash -c "source /opt/ros/humble/setup.bash && \
  source /ws/install/setup.bash && \
  export RMW_IMPLEMENTATION=rmw_fastrtps_cpp && \
  export FASTRTPS_DEFAULT_PROFILES_FILE=/fastdds_udp.xml && \
  ros2 run cross_consistency_observer cross_consistency_observer \
  --ros-args -r /imu:=/g1/imu 2>&1 | tee /ws/runs/4d3c2b/<fase>_B_observer.log"
```

## Terminal C — watchdog
```bash
docker exec -it boring_noether bash -c "source /opt/ros/humble/setup.bash && \
  source /ws/install/setup.bash && \
  export RMW_IMPLEMENTATION=rmw_fastrtps_cpp && \
  export FASTRTPS_DEFAULT_PROFILES_FILE=/fastdds_udp.xml && \
  ros2 run watchdog_g1 watchdog_g1 2>&1 | tee /ws/runs/4d3c2b/<fase>_C_watchdog.log"
```

## Terminal D — recovery
```bash
docker exec -it boring_noether bash -c "source /opt/ros/humble/setup.bash && \
  source /ws/install/setup.bash && \
  export RMW_IMPLEMENTATION=rmw_fastrtps_cpp && \
  export FASTRTPS_DEFAULT_PROFILES_FILE=/fastdds_udp.xml && \
  ros2 run recovery_g1 recovery_g1 2>&1 | tee /ws/runs/4d3c2b/<fase>_D_recovery.log"
```

**ORDEN OBLIGATORIO:** A primero → esperar `=== 4F-P1: P2+z0.720 SET ===` → lanzar B+C+D.

---

# CAMINO ROS2 CONFIRMADO

Bridge oficial descartado (RTX duro). Mini-bridge propio. DDS cross-container: `fastdds_udp.xml`.

## Topics confirmados
```
/joint_states     sensor_msgs/JointState
/g1/base_pose     geometry_msgs/PoseStamped
/g1/base_velocity geometry_msgs/TwistStamped
/g1/imu           sensor_msgs/Imu
/g1/contact/left  g1_msgs/FootContact
/g1/contact/right g1_msgs/FootContact
/safety_events    g1_msgs/SafetyEvent
/recovery_events  g1_msgs/RecoveryEvent
/diagnostics      diagnostic_msgs/DiagnosticArray
```

---

# Qué Está Validado Realmente

## Runtime Framework (3C) + lazo (4D-3D) — sí validado
86 tests Level 4, CI green. TX-001→TX-010 auditables en `TRANSITION_MATRIX_G1.md`.

## Pipeline end-to-end (4F) — sí validado
Baseline sano → silencio; caída → observer alarma (CRITICAL abs_w<0.80), watchdog callado, recovery reacciona; Isaac muerto → watchdog STALE CRITICAL, recovery reacciona.

## Latencia t1→t2 — sí validada
0.68–8.2ms en Tesla T4 (2 corridas). Instrumentación en recovery y extensión Isaac.

## NO validado todavía
- Fault injection sintética (4F-P6)
- t0→t1 latencia física→observer (DT-4F-005)
- Reproducibilidad estadística (N≥5)
- Control activo PD (4E-P5 diferido)
- Thresholds definitivos (todos pragmáticos)

---

# Observer — estado real

```
FALLEN_W_CRITICAL = 0.80   # CRITICAL: abs_w < 0.80 O ambos pies perdidos
FALLEN_W_WARN     = 0.85   # WARN: inclinación moderada O un pie perdido
FALLEN_CONSECUTIVE_N = 3   # muestras frescas consecutivas para CRITICAL

Severidad evaluada en orden: CRITICAL primero, luego WARN, luego INFO.
CRITICAL dispara aunque un pie siga en contacto (contacto residual ≠ soporte sano).
```

# Watchdog — estado real

```
STALE_TIMEOUT_S  = 1.0     # sin mensaje → STALE
STALE_CRITICAL_S = 3.0     # STALE sostenido → escala a CRITICAL
STARTUP_GRACE_S  = 15.0    # no evaluar STALE al arrancar
FREEZE_N         = 5       # muestras idénticas → FREEZE (no aplica a contactos)
MIN_RATE_HZ      = 3.0     # frecuencia mínima esperada
RATE_WARMUP_N    = 5       # mensajes mínimos antes de evaluar rate

CRITICAL_STALE_TOPICS = {'/g1/imu', '/g1/contact/left', '/g1/contact/right'}
NO_FREEZE_TOPICS      = {'/g1/contact/left', '/g1/contact/right'}
```

---

# Anti-Patterns Acumulados (selección + nuevos)

| # | Anti-pattern | Corrección |
|---|---|---|
| 54 | Reconstruir docker run de Isaac de memoria | Usar comando confirmado / guardarlo como script |
| 55 | Subir gains a ciegas sin inspeccionar el modelo | Inspeccionar USD/DriveAPI ANTES |
| 56 | Usar API sin verificar firma | `inspect.signature` antes de usarla |
| 57 | Parchear variable por variable a través de scopes | Reescribir bloque autocontenido + `ast.parse` + grep |
| 58 | Probar control desde estado inicial inválido | Auditar geometría de soporte ANTES |
| 59 | Declarar "el observer alarma" sin confirmar qué binario corre | Grep de la regla; esqueleto solo hace SNAPSHOT |
| **60** | **Lanzar B/C/D antes de que Isaac esté listo** | **A primero → esperar `P2+z0.720 SET` → luego B+C+D** |
| **61** | **No auditar el umbral antes de correr** | **Revisar logs anteriores antes de cada corrida** |
| **62** | **Kill masivo mata el contenedor ROS2** | **Reconstruir `boring_noether` + rebuild 3 paquetes tras kill** |

---

# Deuda Técnica Activa (consolidada)

| ID | Deuda | Prioridad | Estado |
|---|---|---|---|
| DT-4D-017 | Lanzadores Isaac no versionados | Media | Vigente |
| DT-4E-001 | `SAFETY_MODEL_G1.md` ausente en VM | Alta | Recrear/localizar |
| DT-4E-006 | Control activo PD no logrado por vías simples | Alta | 4E-P5 diferido |
| DT-4F-001 | Thresholds watchdog pragmáticos | Media | Calibrar |
| DT-4F-002 | TX-006b/c sin test nombrado explícito | Media | Verificar |
| DT-4F-003 | TX-009 POLICY_GATED condición exacta | Baja | Leer líneas 507-525 |
| DT-4F-004 | FREEZE en IMU posible falso positivo | Media | Vigilar |
| DT-4F-005 | t0→t1 latencia física→observer | Alta | Sync clocks |

---

# Próximo Paso Inmediato

**4F-P6 — Fault injection matrix:** probar fallas sintéticas una por corrida:
1. IMU congelada (freeze artificialmente el topic)
2. Contacto congelado en False
3. NaN en joint positions
4. Timestamp regresivo
5. Topic `/g1/imu` perdido completamente

Criterio PASS: watchdog emite el evento correcto (rule_id correcto, severidad correcta). Criterio FAIL: falso positivo, evento incorrecto, o silencio ante falla.

**Antes de ejecutar:** OK del PM. Una falla por corrida. Sin tocar orchestrator ni recovery.

---

# Objetivo Final

Pipeline reproducible, observable, auditado, portable, ROS2-native, Isaac-compatible, operacionalmente honesto. Objetivo inmediato: **cerrar 4F-P6 y preparar el paper con evidencia completa**.

---

*G1 ROS2 Pipeline — CHAT_BOOTSTRAP_PROTOCOL.md v15*
*Actualizado: 2026-06-16*
*4E ✅ | 4F 🔄 (P1✅ P2✅ P3✅ P4✅ P5✅ P6🔲) | 5A 🔒*
