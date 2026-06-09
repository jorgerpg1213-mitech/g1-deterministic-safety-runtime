# Tesis de Etapas del Proyecto — Runtime Architecture para Humanoide G1
## Versión 12 — Actualizada 2026-06-08 (cierre de sesión 4D-3)

---

## Etapa 1 — Infraestructura Base
**Estado:** ✅ Cerrada

Construcción del entorno operativo reproducible:
- ROS2, Docker, runtime topology, CI/runtime discipline, pipelines observables, logging, recovery básico, watchdog philosophy, separación host/runtime.

### Objetivo logrado
Crear una base reproducible y gobernable para robotics avanzada.

---

## Etapa 2 — Disciplina Operacional
**Estado:** ✅ Cerrada

Formalización de metodología de laboratorio: anti-patterns, ownership operacional, runtime discipline, cleanup determinístico, recovery philosophy, observabilidad, arquitectura reproducible, separación simulación/runtime real.

### Objetivo logrado
Evitar crecimiento caótico del sistema.

---

## Etapa 3 — Safety Runtime Architecture + Runtime Components
**Estado General:** ✅ Cerrada

### Etapa 3A — Modelos Semánticos + ADRs
**Estado:** ✅ Cerrada

`SAFETY_MODEL_G1.md`, `RESILIENCE_MODEL_G1.md`, `RECOVERY_MODEL_G1.md`, `ADR-002`, `ADR-003`. Principles P1–P7, Transition Matrix TX-001→TX-010, Sensor Confidence Semantics, arbitration placeholders, scheduler semantics, preemption model, event bus.

### Etapa 3B — Skeleton Runtime ROS2
**Estado:** ✅ Cerrada

`g1_msgs`, `watchdog_g1`, `cross_consistency_observer`, `safety_orchestrator_g1`, `recovery_g1`. ROSIDL contracts, QoS explícito, threading architecture, diagnostics heartbeat, retry semantics.

### Etapa 3C — Level 4 Runtime Validation + Runtime Integration
**Estado:** ✅ Cerrada
**Commit final:** `861a8b6` | Branch: main | **Fecha:** 2026-05-24

- Transition Matrix TX-001→TX-010 implementada y validada
- Scheduler determinista 4 priority buckets
- T8 arbitration DRAFT con ARBITRATION_PENDING observable
- Recovery runtime real — 5 RecoveryActions
- 86 tests Level 4 — 0 failures
- CI GitHub Actions — green en clean runner
- Build determinista — 12 packages, 0 failures

**Denominación técnica:** Deterministic Safety Runtime Framework — framework de supervisión semántica determinista y agnóstico al hardware.

**Deferred explícitos:** thresholds experimentales, timing físico real, arbitration y locomotion semantics reales → pending SDK G1.

> **Nota de continuidad (sesión 4D-3, 2026-06-08):** se clarificó que el objetivo a corto plazo es **validar este framework** contra estados del G1 simulado. Esto requiere como mínimo un robot **parado/estable** (estado "sano" de fábrica) para tener una línea base contra la cual contrastar estados anómalos. Ver Etapa 4E (propuesta).

---

## Validación Arquitectónica Externa

Coexistencia por desacoplamiento:

| Capa | Responsabilidad |
|---|---|
| Training RL/VLA | rendimiento GPU/tensores |
| Runtime ROS2 | gobierno operacional |
| Safety Model | autoridad y restricciones |
| VLA / GR00T / LeRobot | policy/intelligence layer |
| Orchestrator | arbitraje y ejecución final |

**Resolución crítica:** Los modelos VLA NO gobiernan directamente el humanoide. La autoridad operacional permanece en `safety_orchestrator_g1`, `watchdog_g1`, `cross_consistency_observer`.

---

## Etapa 4 — Simulación e Integración Runtime
**Estado General:** 🔄 En progreso

### Etapa 4A — Infrastructure & DDS Characterization
**Estado:** ✅ Cerrada | **Fecha:** 2026-05-26

- VM MIT — Ubuntu 22.04.5 LTS, Docker 29.1.3, NVIDIA Driver 580.x, CUDA 13.0, Tesla T4 16GB
- Estrategia Docker-first confirmada — NO contaminar host
- `g1-ros-phase-a:humble` (651MB), `g1-ros-phase-b:humble` (1.02GB)
- FastDDS confirmado como RMW activo (`rmw_fastrtps_cpp` 6.2.10)
- DDS intra-container: operativo y observable

#### Decisiones arquitectónicas congeladas en 4A

- Docker-first — NO contaminar host
- ROS2 distro: Humble (22.04 Jammy)
- DDS vendor actual: FastDDS
- Python version: 3.10 — NO mezclar con 3.12
- GPU strategy: `--gpus all`
- Disco real: 58GB total — 21GB disponibles post-Isaac

#### Deuda técnica declarada 4A

| ID | Deuda | Prioridad | Estado |
|---|---|---|---|
| DT-4A-001 | `data_files` incompletos en package test | Baja | Abierta |
| DT-4A-002 | packages.ros.org apt real no probado | Media | Abierta |
| DT-4A-003 | Cross-container DDS characterization | — | ✅ **RESUELTA en 4D-3B2** (2026-06-08) |
| DT-4A-004 | FastDDS vs CycloneDDS — divergencia con Unitree SDK2 | Alta | Abierta — para robot físico |
| DT-4A-006 | colcon-parallel-executor desactualizado | Baja | Abierta |

> **DT-4A-003 — Resolución (4D-3B2):** la caracterización cross-container quedó completada. Causa raíz: FastDDS por defecto usa shared memory, que NO cruza entre contenedores Docker distintos aunque compartan `--network=host`. Fix confirmado: forzar transporte UDPv4 vía perfil XML (`FASTRTPS_DEFAULT_PROFILES_FILE`) en ambos contenedores. Recepción cross-container validada con datos reales del G1 y trazabilidad temporal 1:1.

---

### Etapa 4B — Isaac Headless Bring-up (Isaac Sim 4.2.0)
**Estado:** ✅ Cerrada | **Fecha:** 2026-05-29

- Isaac Sim 4.2.0 headless operativo en VM
- `python.sh` standalone workflow congelado y funcional
- `SimulationApp({"headless": True})` operativo
- Asset `G1/g1.usd` cargado desde S3 — `open_stage()` completa correctamente
- Isaac headless lifecycle completo validado

**Workflow correcto (4.2.0):** `python.sh` standalone — NO `runheadless.native.sh` para scripts Python
**RMW obligatorio:** FastRTPS — CycloneDDS causa fallo del bridge en 4.2.0

#### Deuda técnica declarada 4B

| ID | Deuda | Prioridad |
|---|---|---|
| DT-4B-001 | Migración Local-First del asset G1 | Media |
| DT-4B-002 | Validación de texturas, payloads y referencias USD del G1 | Media |
| DT-4B-003 | Compatibilidad CycloneDDS vs FastRTPS en SDK Unitree | Alta |
| DT-4B-004 | DDS cross-container characterization | ✅ Resuelta (ver DT-4A-003) |

---

### Etapa 4C — Characterización Física y de Control Isaac Sim 4.2.0
**Estado General:** ✅ Cerrada | **Fecha de cierre:** 2026-06-01
**Referencia:** `informe_etapa_4C_4D_2026-06-01.md`

Bloque completo de caracterización local en Isaac Sim 4.2.0. Resumen:
- G1 confirmado como articulación válida: 37 DOF, 176 prims, 44 rigid bodies, 40 colliders, 43 joints (37 con DriveAPI:angular)
- KP runtime ≈ 572,957,824 = KP_USD × (180/π); el controller opera en radianes. KD runtime = 0.0
- KD tiene efecto físico observable; curva {0, 5.7M, 10M, 20M} no monótona; KD=5.7M mejor punto local — NO aprobado como producción
- Hipótesis eliminadas: pose-hold cinemático, "basta ArticulationController", "más KD siempre mejora"
- Hipótesis viva (evidencia externa, no validada localmente): la estabilidad requiere policy/control activo (Isaac Lab issue #2682)

#### Deuda técnica heredada de 4C (activa)

| ID | Deuda | Prioridad | Estado |
|---|---|---|---|
| DT-4C-001 | UsdStage reference count warning | Baja | Abierta — no bloqueante |
| DT-4C-002 | Migración local asset G1 | Media | Diferida |
| DT-4C-003 | PhysX/TGS velocity iteration warning | Baja | Abierta — no bloqueante |
| DT-4C-004 | `physics_dt` default de `World()` no caracterizado | Baja | Abierta — no bloqueante |
| DT-4C-005 | Defaults de `add_default_ground_plane()` no caracterizados | Baja | Abierta — no bloqueante |
| DT-4C-006 | Causa del offset Z -8.17mm Isaac Core vs USD authored | Baja | Abierta — no bloqueante |

---

### Etapa 4D — Isaac Lab / Unitree RL Lab Feasibility
**Estado General:** 🔄 En progreso (4D-1, 4D-2 completos; 4D-3 muy avanzado)
**Desbloqueada por:** cierre de 4C — 2026-06-01

#### Pregunta central
¿Puede Isaac Lab (o, como prerequisito, Isaac Sim 4.5) operar sobre la VM actual (Tesla T4) preservando el baseline, y cargar/simular/observar el G1 sin el stack pesado que la T4 no soporta?

---

#### Etapa 4D-1 — Disk / Baseline Preservation Audit
**Estado:** ✅ Cerrada

- Confirmado: un solo disco 58GB, ~21–23GB libres, sin LVM, sin segundo disco
- Plan B aprobado y ejecutado: reemplazo de imagen Isaac Sim 4.2.0 por 4.5.0 (4.2.0 reconstruible por re-pull NGC)
- Backup de 44 scripts/logs de 4C en `~/backup_4c/`
- Incidente externo resuelto: GPU `RmInitAdapter failed` tras force-reboot del admin (NAS/iSCSI) → Stop/Start completo de VM restauró la GPU

---

#### Etapa 4D-2 — Feasibility Isaac Sim 4.5 + Carga/Stepping del G1 en T4
**Estado General:** ✅ Cerrada (2A–2H)
**Fecha:** 2026-06-08
**Referencia:** `informe_etapa_4D2_2026-06-08.md`

##### 4D-2A — Isaac Sim 4.5 Feasibility en T4 (Diagnóstico de Bloqueo)
**Estado:** ✅ Cerrada

`SimulationApp({"headless": True})` en 4.5 carga, en la práctica de esta imagen, el experience pesado `isaacsim.exp.full.streaming.kit`, que arranca renderer RTX + ROS2 y se cuelga/crashea en el T4 (errores `DescriptorSet`). Hallazgos:
- **Hallazgo A (DT-4D-001):** el `commandLine` real muestra `full.streaming.kit` pese a pasar `experience=`; el fuente de `simulation_app.py` sugiere que debería respetarse. Contradicción no resuelta — congelada.
- **Hallazgo B:** los 3 experiences de fábrica (`base`, `base.python`, `zero_delay`) heredan `isaacsim.exp.base`, que carga `omni.hydra.rtx`, replicator, sensors.rtx, physx.tensors de forma no opcional. ROS2 bridge NO está en `exp.base` (venía de `full.streaming`).
- El experience ligero de 4.2 (`omni.isaac.sim.python.kit`) NO existe en 4.5; el default vacío cae a `exp.base.python.kit` (pesado).
- Contexto hardware (doc oficial NVIDIA): mínimo RTX 3070; "GPUs sin RT Cores no soportadas". T4 fuera de clase RTX. Calificado como **límite de soporte/testing, no bloqueo técnico duro**. Riesgo alto, no causa única demostrada.

##### 4D-2B — `.kit` Mínimo sin `exp.base` → `app ready`
**Estado:** ✅ Cerrada

`isaacsim.core.api` no arrastra RTX/replicator/ROS2 (verificado en su `extension.toml`). Se creó `.kit` mínimo (`core.api` + `core.utils` + `core.prims` + `storage.native`, sin `exp.base`, sin `kit/community`). Arranca vía `kit` directo en ~10s sin stack pesado. `app ready` se alcanza al agregar `omni.kit.loop-isaac` (aislado como única variable).

##### 4D-2C — Extensión Python Ejecuta `on_startup`
**Estado:** ✅ Cerrada

Extensión propia `isaacsim.g1.runtime` (`class Extension(omni.ext.IExt)` con `on_startup`) ejecuta código dentro del arranque `kit` directo. Resultado: `STARTUP EXTENSION OK` + `app ready`. Mecanismo de ejecución de Python sin `SimulationApp` confirmado.

##### 4D-2D — G1 Carga en 4.5 con `num_dof = 37`
**Estado:** ✅ Cerrada

Patrón async confirmado (NO standalone síncrono): `create_new_stage_async` → `World()` → `initialize_simulation_context_async` → ground plane → `add_reference_to_stage` (asset G1 4.5) → `Articulation(prim_paths_expr=...)` → `reset_async`. Resultado: `G1 LOADED`, `num_dof: 37`. API 4.5: `get_world_poses()` plural (singular no existe).

##### 4D-2E — Physical Stepping Smoke Test (60 steps)
**Estado:** ✅ Cerrada

Corrección de API: `step_async()` NO es awaitable en 4.5 (devuelve None) → método correcto `world.step(render=False)` síncrono. 61 steps, lectura pose/orientación/joints en 0/10/30/60, terminando en `PHYS STEPPING DONE`. El G1 se desestabiliza sin policy (esperado, igual que 4C — NO es fallo).

##### 4D-2F — Repetibilidad Básica
**Estado:** ✅ Cerrada

Repetición exacta → resultado **bit-idéntico** entre dos corridas independientes (poses iguales hasta el último decimal). Reproducible y determinista en este camino/configuración.

##### 4D-2G — Serie Reducida de Estabilidad 4.5 vs 4.2
**Estado:** ✅ Cerrada (2026-06-08) — análisis documental, sin corrida nueva

Comparación de los cortes 0/10/30/60 entre `output_g1_step_v2.log` (4.5) y `output_4c5a.log` (4.2, KD=0, apoyo familia 4c5a–5d/4c3d). Misma dinámica en ambas versiones: arranque bajo (Z≈0.10–0.15) → pico ~0.83–0.87 (step 30) → toppling hacia step 60 (W cae de 1.0 a ~0.66–0.72; XY_NORM crece a ~0.74–0.82). 4.5 reproduce la dinámica de 4.2; sin divergencia ni bug nuevo. Diferencia menor (4.5 arranca ~5 cm más alto, cae algo menos pronunciado) etiquetada como hipótesis no confirmada (posible distinto link de referencia/spawn).

##### 4D-2H — Sustained Readout (600 steps) + Repetibilidad
**Estado:** ✅ Cerrada (2026-06-08)

Horizonte 60→600 steps (única variable), copia reversible del baseline (`isaacsim.g1.runtime.h2` en `~/runs/4d2h/`). El G1 cae hasta ~step 60 y alcanza reposo estable desde ~step 150 (Z≈0.1618, W≈0.671 congelado hasta step 600, sin NaN/explosión/degradación). Robot tumbado plenamente legible. Repeat → **bit-idéntico** (extiende el determinismo de 2F a horizonte largo). Saneamiento de namespacing resuelto antes de correr (Anti-pattern 38).

##### Resultado declarable de 4D-2 (epistemología cuidada)
- **Positivo:** Isaac Sim 4.5 carga, simula y sostiene el G1 en el T4 mediante el camino ligero propio (`kit` directo + `.kit` mínimo + extensión async), reproducible y bit-idéntico hasta 600 steps.
- NO "embodiment estable" — se desestabiliza sin policy.
- NO "T4 suficiente para Isaac Lab/RL/RTX" — solo suficiente para esta microcapa.

##### Deuda técnica declarada 4D-2 — activa

| ID | Deuda | Prioridad | Estado |
|---|---|---|---|
| DT-4D-001 | Causa exacta de `SimulationApp` → `full.streaming` pese al `experience=` | Media | Congelada — se evita con `kit` directo |
| DT-4D-002 | `app ready` no se emite sin `omni.kit.loop-isaac`; lifecycle mínimo no caracterizado en detalle | Baja | Abierta — no bloqueante |
| DT-4D-003 | Viabilidad T4 para render RTX / Isaac Lab / RL no demostrada (RTX 3070 mínimo; T4 sin clase RTX) | Alta | Abierta — matizada en 4D-3B4 (T4 toleró RTX de sensores sin crash) |
| DT-4D-004 | `add_default_ground_plane()` / `World()` defaults dentro de extensión async no caracterizados | Baja | Abierta — no bloqueante |
| DT-4D-005 | "Sin RTX pesado" es inferencia del log, no profiling del grafo GPU | Baja | Abierta — no bloqueante |

---

#### Etapa 4D-3 — ROS2 Feasibility + Observabilidad Sensorial del G1
**Estado General:** ✅ Mayoritariamente cerrada (3A, 3B1, 3B2, 3B3, 3B4, 3B4A); pendientes 3B4B, 3C, 3D
**Fecha:** 2026-06-08
**Referencia:** `informe_etapa_4D3_2026-06-08.md`

##### 4D-3A — ROS2 Bridge Feasibility → Mini-Bridge Propio
**Estado:** ✅ Cerrada

El bridge oficial `isaacsim.ros2.bridge` (v4.1.15) fue **descartado con evidencia**: depende de forma dura de `isaacsim.sensors.rtx` → `omni.hydra.rtx` (RTX que el T4 no soporta, sin flag para desactivar). NO está ligado a Isaac Lab. Decisión (aprobada por PM): **mini-bridge propio** con el `rclpy` interno de Isaac (`/isaac-sim/exts/isaacsim.ros2.bridge/humble/rclpy`). Carga en el `.kit` ligero inyectando esa ruta en `sys.path` **dentro de `on_startup`** (Kit no hereda PYTHONPATH). Confirmado: `RCLPY IN KIT OK`.

##### 4D-3B1 — G1 + rclpy Coexisten
**Estado:** ✅ Cerrada

El G1 (carga + stepping) y `rclpy` (init + nodo) coexisten en el mismo proceso Kit sin conflicto. Versión step: `rclpy_ok=True` durante 300 steps físicos.

##### 4D-3B2 — Publisher `/joint_states` + Recepción Externa (DT-4A-003)
**Estado:** ✅ Cerrada

Extensión `isaacsim.g1.jointpub` publicó 1542 mensajes de `/joint_states` (name=37/pos=37/vel=37). Recepción externa inicial = 0 (cuello DDS). **DT-4A-003 resuelto:** FastDDS shm no cruza contenedores; fix = transporte UDPv4 forzado por `fastdds_udp.xml` + `FASTRTPS_DEFAULT_PROFILES_FILE` en ambos contenedores. Tras el fix, subscriber externo (otro contenedor, `--network=host`) recibió datos reales del G1.
**Plomería confirmada:** numpy del subscriber externo desde `omni.kit.pip_archive/pip_prebundle`; CLI `ros2` NO existe en la imagen (usar subscriber Python rclpy).
**4D-3B2-T (trazabilidad):** subscriber sigue al publisher en vivo — `first_frame_id=159` (entró tarde, capturó el momento, no caché), diferencia recv#/frame_id constante (sin pérdida), correlación 1:1 al segundo, 1383 msgs recibidos coherentes con 1542 publicados.

##### 4D-3B3 — Estado Mínimo (joints + base pose + base velocity)
**Estado:** ✅ Cerrada

Extensión `isaacsim.g1.statepub` publica 3 topics: `/joint_states` (JointState), `/g1/base_pose` (PoseStamped, `get_world_poses()`), `/g1/base_velocity` (TwistStamped). Velocidad de base con `get_linear_velocities()` + `get_angular_velocities()` **separados** (evita ambigüedad de orden — verificado en `articulation.py`). Subscriber externo recibió los 3 con datos coherentes (pose Z=0.162 = reposo, vel≈0). `state_summary` dejado fuera a propósito (interpretación → corresponde al runtime).

##### 4D-3B4 — Probe Sensores Físicos
**Estado:** ✅ Cerrada

`isaacsim.sensors.physics` expone `IMUSensor` y `ContactSensor` (`get_current_frame()`). Carga en el `.kit` ligero **sin crash** (a diferencia de 4D-2A): `SENSORS.PHYSICS IMPORT OK` + `IMU + CONTACT CLASSES AVAILABLE` + `app ready`. PERO arrastra `omni.replicator.core` → warning `rtx.neuraylib.plugin` (ECC del T4). Veredicto: **"RTX tolerado"** — viable, pero ya no es "cero RTX absoluto".

##### 4D-3B4A — IMU + 2 ContactSensor Leídos (caída instrumentada)
**Estado:** ✅ Cerrada

Inventario previo de links: pies = `/World/G1/left_ankle_roll_link` + `/World/G1/right_ankle_roll_link`; IMU = `/World/G1/torso_link`. Campos de `get_current_frame()` verificados en fuente: IMU → `lin_acc`/`ang_vel`/`orientation(wxyz)`; Contact → `in_contact`/`force`/`time`/`number_of_contacts`. Extensión `isaacsim.g1.sensorread` leyó la caída completa (300 steps): step 0 ambos pies tocan (14N/3.8N) → step 60 izq despega, der aguanta 34N, IMU W=0.727 con pico de ang_vel → step 150-300 ningún pie toca, W=0.671 quieto. Datos físicamente coherentes con 2H/3B3, sin crash.
**4D-3B4A-live (parcial):** streaming en vivo de `/g1/imu` (Imu) + `/g1/feet` (Float32MultiArray), T2 lanzado primero capturó desde frame=0 la secuencia DE_PIE→cae→tumbado, sincronía 1:1 al segundo, 1383+ frames sin caché. Cortado por caída de red externa (evidencia esencial ya capturada). Defecto cosmético: etiqueta `estado()` mal calibrada (DT-4D-007) — datos correctos, solo la palabra miente.

##### 4D-3B4B — Publicar IMU + Contactos con Tipos ROS2 Dedicados
**Estado:** 🔲 Pendiente

Casi calcado de 3B3, pero formalizando los contactos con un tipo ROS2 dedicado (en vez de `Float32MultiArray` crudo). Para que el runtime reciba sensores con estructura limpia. (DT-4D-008.)

##### 4D-3C — Runtime Determinístico en Modo OBSERVADOR
**Estado:** 🔲 Pendiente

Conectar el Deterministic Safety Runtime Framework como suscriptor: lee `/joint_states` + pose + velocidad + IMU + contactos, y **evalúa** el estado (sano/anómalo) **sin enviar comandos**. Primer contacto runtime↔simulación. Núcleo de la validación que busca el operador.

##### 4D-3D — Primer Cierre Runtime → G1 (eventos/safety, sin control físico)
**Estado:** 🔲 Pendiente

El runtime emite de vuelta eventos/system_state/safety messages (cierra el lazo a nivel de señales), todavía sin mover físicamente al robot.

##### Hipótesis del bloque 4D-3

| Hipótesis | Estado |
|---|---|
| "La dinámica del G1 difiere entre 4.5 y 4.2" | ❌ Eliminada — 4D-2G |
| "El stepping largo (600) degrada/crashea" | ❌ Eliminada — 4D-2H bit-idéntico |
| "El ROS2 bridge oficial puede usarse sin RTX en T4" | ❌ Eliminada — 4D-3A (RTX duro) |
| "rclpy interno carga en el .kit ligero" | ✅ Confirmada — 4D-3A |
| "El G1 publica /joint_states por ROS2 real" | ✅ Confirmada — 4D-3B2 |
| "Un proceso externo recibe el estado cross-container" | ✅ Confirmada — 4D-3B2 (tras fix UDP) |
| "FastDDS shm cruza entre contenedores con --network=host" | ❌ Eliminada — requiere UDP |
| "El subscriber sigue al publisher en vivo (no caché)" | ✅ Confirmada — 4D-3B2-T |
| "base_velocity existe en API 4.5" | ✅ Confirmada — 4D-3B3 |
| "Los sensores físicos cargan en T4 sin crash" | ✅ Confirmada (RTX tolerado) — 4D-3B4 |
| "IMU + contactos producen datos coherentes" | ✅ Confirmada — 4D-3B4A |
| "El T4 sirve para Isaac Lab completo / RL / RTX" | 🔲 No probada — riesgo alto, matizado |

##### Resultado declarable de 4D-3 (epistemología cuidada)
- **Positivo:** el G1 es totalmente **observable** por ROS2 real (joints + pose + velocidad + IMU + contactos) hacia procesos externos, cross-container, sin RTX pesado, en T4, con streaming en vivo validado (trazabilidad 1:1).
- NO "control" — todo es lectura/observación; no se envió ningún comando.
- NO "embodiment estable" — se cae sin policy.
- NO "RTX resuelto" — sensores arrastran RTX tolerado, no cero-RTX absoluto.

##### Deuda técnica declarada 4D-3 — activa

| ID | Deuda | Prioridad | Estado |
|---|---|---|---|
| DT-4D-006 | `get_contact_sensor_raw_data` deprecada en 4.5 (funciona) | Baja | Nueva — migrar antes de producción |
| DT-4D-007 | Etiqueta `estado()` de `sub_live.py` mal calibrada (CAYENDO permanente; datos correctos) | Baja | Nueva — fix 3 líneas |
| DT-4D-008 | Contactos publicados como `Float32MultiArray` crudo, no tipo ROS2 dedicado | Media | Nueva — formalizar en 4D-3B4B |

#### Compatibilidad G1 / Isaac Lab (referencia, doc oficial)

| Fuente | Soporte G1 | Requiere |
|---|---|---|
| Isaac Lab 2.x oficial | ✅ ambiente G1 oficial | Isaac Sim 4.5.0+ |
| unitree_sim_isaaclab | ✅ tareas específicas G1 | Isaac Sim 4.5.0 |
| Isaac Lab 1.4.1 (última 1.x) | última compatible con Isaac Sim 4.2 | Isaac Sim 4.2.0 |
| Isaac Lab 2.0+ | refactor — incompatible con < 4.5 | Isaac Sim 4.5.0 |

Nota: Isaac Lab oficialmente dejó de dar soporte a Isaac Sim ≤ 4.2.0. El requisito de GPU (RTX 3070 mínimo, sin RT Cores no soportado) aplica igual a 4.2 y 4.5 — volver a 4.2 no resuelve el riesgo de hardware del T4 para Isaac Lab.

#### Criterios de éxito graduales (actualizados)

```
4D-2 éxito (logrado):   G1 carga + steppea + sostiene 600 steps en 4.5 sobre T4, reproducible
4D-3 éxito (logrado):   runtime puede LEER el estado del G1 vía ROS2 (joints+pose+vel+IMU+contactos) cross-container
4D-3C/3D éxito:         runtime observador conectado + cierre de lazo a nivel señales (sin control físico)
4E éxito (propuesto):   G1 PARADO/estable vía standing policy plug-and-play → baseline "sano" para validar runtime
5A éxito mínimo:        G1 cargado en Isaac Lab environment (pendiente viabilidad GPU — ya no ruta crítica si 4E plug-and-play)
```

---

#### Etapa 4E — Standing Policy Plug-and-Play + Validación de Estado del Runtime
**Estado:** 🔲 PROPUESTA (pendiente decisión PM) — abierta en sesión 4D-3 (2026-06-08)

**Motivación (clarificada por el operador):** el objetivo real a corto plazo es **validar el Deterministic Safety Runtime Framework** (3C) contra estados del G1. Para ello se necesita el robot **parado/estable** (estado "sano" de fábrica) como línea base, contra la cual contrastar estados anómalos inducidos por perturbaciones controladas. Con el robot permanentemente tumbado NO hay contraste "sano vs malo" → no se puede validar el runtime.

**Restricción declarada:** NO se entrenará locomoción (no RL local). Se busca una **standing/balance policy plug-and-play** (ya entrenada, ejecutable) que mantenga al G1 de pie y lo recupere ante perturbaciones pequeñas.

**Alcance propuesto:**
- Investigar (con evidencia, sin asumir) si existe una standing policy pública para el G1 (Unitree u otra fuente) lista para usar.
- Verificar si ejecuta en el camino ligero del T4 (ejecución de policy, NO entrenamiento — carga mucho menor).
- Usar la policy como baseline "sano" e inyectar perturbaciones controladas para validar la detección del runtime (estado bueno → "OK"; perturbado/caído → detección).

**Implicación de roadmap:** Isaac Lab (5A) deja de ser ruta crítica. Solo sería necesario como *entorno de ejecución* de una policy lista, no para entrenar — lo que reduce el riesgo del T4. Pregunta abierta a resolver al inicio de 4E: ¿existe esa policy y corre en T4 sin Isaac Lab completo?

---

### Etapa 5A — Isaac Lab Bring-up / G1 Environment Validation
**Estado:** 🔒 Bloqueada — y reclasificada: ya NO es ruta crítica si 4E resuelve el baseline "sano" vía plug-and-play

Nota de riesgo: la viabilidad de Isaac Lab en el T4 NO está demostrada (DT-4D-003). El camino ligero de 4D sirve para carga/stepping/observación; Isaac Lab (RL, sensores RTX, replicator, training) es sospechoso de requerir hardware RTX.
**Matiz nuevo (4D-3B4):** el T4 **toleró** el plugin RTX de los sensores físicos sin crashear — no demuestra que Isaac Lab corra, pero debilita la premisa "RTX en T4 = muro absoluto". La decisión de GPU sigue pendiente; si el objetivo es ejecutar una policy lista (no entrenar), el riesgo baja sustancialmente.

---

## Etapa 5 — Integración VLA / GR00T / LeRobot
**Estado:** Futura

Integración de GR00T, LeRobot, Gemini Robotics, policy layers, embodied AI. Estos modelos NO gobiernan el sistema completo. La arquitectura define authority boundaries, safety governance, arbitration y epistemic containment.

Nota de hardware: GR00T y dexterous manipulation son cargas pesadas (foundation model + render/percepción RTX). Probable requisito de GPU clase RTX por encima del T4 — a confirmar con feasibility dedicada (relacionado con DT-4D-003).

---

## Etapa 6 — Behaviors Embodied Reales
**Estado:** Futura

Locomoción compleja, behaviors autónomos, manipulation, navigation, recovery real, interacción entorno/humano.

---

## Etapa 7 — Refinamiento y Autonomía
**Estado:** Futura

Adaptación, autonomy refinement, policy tuning, runtime optimization, long-horizon behaviors, aprendizaje continuo controlado.

---

## Resolución General

El proyecto dejó de ser "poner IA en un robot". Ahora se está construyendo:

> una arquitectura/runtime donde sistemas tipo GR00T puedan operar de forma gobernable, reproducible y segura.

El foco es: authority, safety, arbitration, runtime semantics, observabilidad, recuperación, epistemología operacional, control sistémico del humanoide.

> El runtime del humanoide y el entrenamiento de políticas VLA son dominios distintos pero complementarios. El entrenamiento optimiza inteligencia. La arquitectura runtime gobierna comportamiento operacional real.

**Aprendizaje de la sesión 4D-3:** la validación del runtime es el objetivo inmediato, y requiere un baseline "sano" (robot parado). El camino no es entrenar (Isaac Lab/RL) sino ejecutar una policy lista (plug-and-play) — lo que mantiene al T4 como hardware suficiente para la fase de validación de runtime, separando claramente "validar gobierno operacional" (factible ahora) de "entrenar inteligencia" (pesado, diferido).

---

*G1 ROS2 Pipeline — Tesis de Etapas v12*
*Actualizado: 2026-06-08*
*Etapa 3C ✅ | 4A ✅ (DT-4A-003 resuelta) | 4B ✅ | 4C ✅ | 4D-1 ✅ | 4D-2A–2H ✅ | 4D-3A/3B1/3B2/3B3/3B4/3B4A ✅ | 4D-3B4B/3C/3D 🔲 | 4E 🔲 propuesta | 5A 🔒*
