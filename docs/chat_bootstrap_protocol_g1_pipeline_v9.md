# G1 ROS2 Pipeline — CHAT BOOTSTRAP PROTOCOL
## Guía de Arranque para Nuevas Sesiones / Nuevos LLMs
## Versión 9 — Actualizada 2026-06-08 (cierre de sesión 4D-3)

**Objetivo:**
Garantizar continuidad técnica, rigor operacional y preservación del criterio arquitectónico del proyecto G1 ROS2 Pipeline.

---

# Estado Actual del Proyecto

```
Etapa 3C  — Deterministic Safety Runtime Framework     ✅ CERRADA
Etapa 4A  — Infrastructure & DDS Characterization      ✅ CERRADA (DT-4A-003 RESUELTA en 4D-3)
Etapa 4B  — Isaac Headless Bring-up (4.2.0)            ✅ CERRADA
Etapa 4C  — Characterización Física y de Control       ✅ CERRADA (bloque completo, 4.2.0)
Etapa 4D  — Isaac Lab / Unitree RL Lab Feasibility     🔄 EN PROGRESO
  4D-1    — Disk / Baseline Preservation Audit         ✅
  4D-2A–2F — Feasibility 4.5 + carga/stepping          ✅
  4D-2G   — Serie estabilidad 4.5 vs 4.2               ✅ análisis documental
  4D-2H   — Sustained readout 600 steps (+repeat)      ✅ bit-idéntico
  4D-3A   — ROS2 feasibility → mini-bridge propio      ✅ rclpy interno
  4D-3B1  — G1 + rclpy coexisten                       ✅
  4D-3B2  — Publisher /joint_states + recepción ext    ✅ DT-4A-003 resuelto (+ trazabilidad)
  4D-3B3  — Estado mínimo (joints+pose+velocidad)      ✅ 3 topics
  4D-3B4  — Probe sensores físicos                     ✅ RTX tolerado, no crash
  4D-3B4A — IMU + contactos leídos (+ live-stream)     ✅ caída instrumentada coherente
  4D-3B4B — Publicar IMU+contactos (tipos dedicados)   🔲 PENDIENTE
  4D-3C   — Runtime determinístico OBSERVADOR          🔲 PENDIENTE
  4D-3D   — Cierre runtime → G1 (eventos/safety)       🔲 PENDIENTE
  4E      — Standing policy plug-and-play + validación 🔲 PROPUESTA (pendiente decisión PM)
Etapa 5A  — Isaac Lab Bring-up / G1 Validation         🔒 BLOQUEADA — ya NO ruta crítica si 4E plug-and-play
```

**Repositorio:** github.com/jorgerpg1213-mitech/g1-ros2-pipeline
**Commit base 3C:** `861a8b6` | Branch: main
**VM activa:** Ubuntu 22.04.5 LTS | Tesla T4 16GB | Docker 29.1.3 | CUDA 13.0 | Driver 580.159.03

### Estado exacto de la VM al cierre de sesión 2026-06-08 (4D-3)

- Imagen `nvcr.io/nvidia/isaac-sim:4.5.0` presente
- Isaac Sim 4.2.0 NO presente — reconstruible por re-pull NGC
- Contenedor Isaac NO está corriendo — verificado limpio (un contenedor huérfano de la prueba live-stream fue limpiado con `docker stop` tras una caída de red)
- GPU: libre (~14912 MiB), sana
- Baseline Docker ROS intacto: `g1-ros-phase-a:humble` y `g1-ros-phase-b:humble`
- Backup 4C: `~/backup_4c/` (44 archivos) intacto
- Baseline 4D-2: `~/g1ext/isaacsim.g1.runtime/` intacto
- Artefactos 4D-3 nuevos: `~/runs/{4d2h,4d3a,4d3b1,4d3b1step,4d3b2,4d3b3,4d3b4probe,4d3b4a,4d3b4live}/`
- tmux: sesiones históricas `4d2h`, `4d3a`, `g1_4d` (viejas, no estorban)

---

# INSTRUCCIÓN CRÍTICA PARA EL PRIMER MENSAJE

**La etapa activa es 4D-3 (muy avanzada). El G1 ya es totalmente observable por ROS2 — falta conectar el runtime.**
**Primero: leer, auditar, planear. Obtener OK del PM antes de cualquier corrida.**

Hay **tres caminos posibles** para el siguiente paso (a decidir con el PM):
```
Opción A — 4D-3B4B: publicar IMU+contactos con tipos ROS2 dedicados (calcado de 3B3)
Opción B — 4D-3C:   conectar el runtime observador (leer + evaluar estado, SIN control)
Opción C — 4E:      investigar standing policy plug-and-play para baseline "sano" (validar runtime)
```

**Clarificación estratégica clave (sesión 4D-3):** el objetivo real del operador es **validar el Deterministic Safety Runtime Framework** contra estados del G1. Necesita el robot **parado/estable** (estado sano de fábrica) vía **standing policy plug-and-play** (NO entrenar RL). Isaac Lab (5A) deja de ser ruta crítica. NO asumir que el operador quiere entrenar locomoción.

**NO reabrir:**
- `SimulationApp` (congelado — DT-4D-001)
- El **bridge ROS2 oficial** (descartado — depende duro de RTX, DT-4D-003 relacionado)

---

# Filosofía Operacional

Este proyecto NO debe tratarse como demo, playground ni repositorio de features.

Debe tratarse como:
> una plataforma robótica reproducible, auditada y operacionalmente honesta.

El estándar esperado es equivalente a laboratorio MIT / NASA / Boston Dynamics.

Toda propuesta debe diferenciar explícitamente: evidencia observada, deuda transicional, placeholders y comportamiento realmente validado.

El objetivo NO es "parecer robusto". El objetivo es que el sistema sea exactamente tan robusto como afirma ser.

---

# Estructura del Equipo

| Rol | Responsable |
|---|---|
| PM Técnico | ChatGPT |
| Implementador / Auditor | Claude |
| Operador | Jorge Padilla |

**Importante:** Cada modelo debe mantener criterio independiente. El PM valida, no dicta. El implementador puede y debe disentir con evidencia. En esta sesión el PM corrigió/encauzó múltiples decisiones (separar publisher de interpretación, exigir tabla antes de cerrar 2G, exigir trazabilidad temporal antes de declarar recepción confiable, exigir prueba aislada de sensores antes de mezclar). Esas correcciones son parte del registro.

---

# Orden Correcto de Lectura para un Nuevo Chat

## 1. Este archivo — CHAT_BOOTSTRAP_PROTOCOL.md v9
Leer primero para orientación general y estado actual.

## 2. Tesis de Etapas — `tesis_etapas_proyecto_g1_runtime_architecture_v12.md`
Estado completo de todas las etapas, decisiones congeladas, deuda declarada.

## 3. Informe de Sesión más reciente
**Informe actual:** `informe_etapa_4D3_2026-06-08.md` (bloque 4D-3: ROS2 feasibility, mini-bridge, DDS cross-container, estado mínimo, sensores físicos).
**Informe anterior:** `informe_etapa_4D2_2026-06-08.md` (bloque 4D-2: camino ligero 4.5, carga/stepping).

## 4. SAFETY_MODEL_G1.md
Leer cuando el trabajo involucre runtime safety, transitions, authority o recovery — relevante de inmediato porque la siguiente fase (4D-3C) conecta el runtime.

## 5. Documentos de referencia profunda
Solo cuando sea necesario: `RESILIENCE_MODEL_G1.md`, `RECOVERY_MODEL_G1.md`, `ADR-002`, `ADR-003`, `TECHNICAL_DEBT_3C.md`.

---

# Reglas de Operación para Nuevas Sesiones

## Regla 1 — Máximo 2 comandos por mensaje
Cada comando debe incluir propósito explícito, qué valida y qué resultado se espera.

## Regla 2 — Esperar output real
No asumir runtime, paths, nodos, build status, DDS state, ni resultados de CI.

## Regla 3 — No sobredeclarar validación
Smoke tests ≠ integration tests. CI verde ≠ runtime validado. `app ready` ≠ embodiment estable. "Carga" ≠ "estable". "Suficiente para microcapa" ≠ "suficiente para Isaac Lab". **"Una lectura/foto" ≠ "streaming confiable" (exigir trazabilidad temporal).** **"Observación" ≠ "control".**

## Regla 4 — Una variable nueva por experimento
Cada prueba debe cambiar exactamente una variable respecto a la anterior.

## Regla 5 — No parchear componentes bloqueados
Si un componente depende de SDK G1, Isaac Lab, USD oficiales o modelos no definidos: NO improvisar. Primero definir contratos.

## Regla 6 — Regla de decisión arquitectónica
Ninguna instalación, Dockerfile, versión o configuración se acepta si puede cerrar el camino futuro sin justificación explícita.

## Regla 7 — Characterization antes de integración
Siempre caracterizar antes de integrar. (Lección 4D-3B4: probar la carga aislada de los sensores ANTES de instanciarlos y mezclarlos con el publisher.)

## Regla 8 — Verificar estado VM antes de ejecutar cualquier cosa
```bash
docker ps && df -h / && docker images | grep -E "isaac|g1-ros"
```
**Tras una caída de red:** verificar también contenedores huérfanos — el `docker run` sobrevive a la desconexión SSH (`pgrep -af "isaac-sim/kit/kit"`; limpiar con `docker stop`).

## Regla 9 — tmux antes de procesos largos
```bash
tmux new -s nombre_sesion
```
Reconectar con: `tmux attach -t nombre_sesion`. Estructura de fase: una carpeta `~/runs/<fase>/` autocontenida por microfase.

## Regla 10 — Solo afirmar lo que el log demuestra
No diagnosticar más allá de la evidencia. "No aparece en el log" ≠ "no ocurre en el grafo GPU interno".

## Regla 11 — Exploración antes de hipótesis
Antes de proponer cualquier script, explorar documentación oficial, ejemplos, foros, GitHub, ADRs, deuda técnica. Solo después fijar hipótesis.

## Regla 12 — No asumir API sin verificar
Cualquier método, atributo o función debe verificarse en la instalación real antes de depender de él. (Lecciones 4D: `step_async` no awaitable; `get_velocities()` orden ambiguo → usar `get_linear/angular_velocities()`; campos de `get_current_frame()` verificados en fuente — NO "defensivo a ciegas".)

## Regla 13 — Valores de gains en unidades runtime (4.2)
`set_gains()` recibe valores en unidades runtime (radianes), NO USD (grados). KP runtime ≈ KP_USD × (180/π). Verificar con `get_gains()`.

## Regla 14 — Separar hallazgo local de decisión arquitectónica
Un hallazgo experimental local no autoriza declarar producción ni causalidad.

## Regla 15 — Exit code de timeout no es veredicto
`kit` directo queda vivo tras `app ready`; `timeout` lo corta con código 124. El veredicto está en el log (presencia de marcadores), NO en el código de salida.

## Regla 16 — Trabajar sobre copia, preservar baseline validado
No editar el `.kit`/extensión/script ya validados para iterar. Crear copia nueva y backup antes de modificar. Cada microfase en su propia carpeta `~/runs/<fase>/`.

## Regla 17 — Construir archivos por bloques cortos (nueva, 4D-3)
Pegar 80+ líneas de una vez en un here-doc desordena/cuelga la terminal. Crear extensiones/scripts grandes por bloques cortos con `cat >>` y validar sintaxis con `python3 -c "import ast; ast.parse(...)"` tras cada bloque.

## Regla 18 — Verificación externa con subscriber Python, no CLI ros2 (nueva, 4D-3)
El CLI `ros2` NO existe en la imagen Isaac. Toda verificación de recepción externa se hace con un subscriber Python rclpy en un contenedor separado.

---

# CAMINO OPERATIVO CONFIRMADO PARA ISAAC SIM 4.5 (T4)

**Reemplaza el workflow `SimulationApp`. El de `python.sh`+`SimulationApp` queda solo como referencia histórica de 4.2.**

## Por qué `SimulationApp` no sirve en 4.5 sobre T4
`SimulationApp({"headless": True})` carga `isaacsim.exp.full.streaming.kit` (renderer RTX + ROS2), que crashea en T4 (`DescriptorSet`). Causa exacta no demostrada (DT-4D-001). NO perseguir — usar el camino ligero.

## El camino ligero (validado, reproducible, sostenido a 600 steps)
```
kit directo (--entrypoint /isaac-sim/kit/kit)
  + .kit mínimo (sin exp.base, sin kit/community, con omni.kit.loop-isaac)
  + extensión Python propia con on_startup async
```

## `.kit` mínimo — estructura validada
```toml
[package]
title = "Isaac Sim Minimal Loop Python G1"
version = "4.5.0"
[dependencies]
"isaacsim.core.api" = {}
"isaacsim.core.utils" = {}
"isaacsim.core.prims" = {}
"isaacsim.storage.native" = {}
"omni.kit.loop-isaac" = {}        # REQUERIDO para alcanzar app ready
"isaacsim.g1.<fase>" = {}          # extensión propia de la fase
# para sensores físicos, añadir: "isaacsim.sensors.physics" = {}  (carga con RTX tolerado)
[settings.app]
vulkan = true
[settings.app.exts.folders]
'++' = ["${app}/../exts","${app}/../extscache","${app}/../extsPhysics","${app}/../extsUser","${app}/../extsDeprecated"]
[settings.exts."omni.kit.registry.nucleus"]
registries = [ {kit/default}, {kit/sdk} ]   # SIN kit/community (evita 403)
```

## API y patrones confirmados (4.5)
```
Carga G1 (async):  create_new_stage_async / World() / initialize_simulation_context_async /
                   add_default_ground_plane / add_reference_to_stage / Articulation(prim_paths_expr=) / reset_async
Stepping:          world.step(render=False)   # SÍNCRONO — step_async NO es awaitable
Pose:              get_world_poses()  PLURAL — singular no existe; leer [0]
Velocidad base:    get_linear_velocities() + get_angular_velocities()  (SEPARADOS, evita ambigüedad)
Asset G1 4.5:      http://omniverse-content-production.s3-us-west-2.amazonaws.com/Assets/Isaac/4.5/Isaac/Robots/Unitree/G1/g1.usd
DOF:               37
Links clave G1:    pies = /World/G1/left_ankle_roll_link + right_ankle_roll_link ; IMU = /World/G1/torso_link
```

---

# CAMINO ROS2 CONFIRMADO (mini-bridge propio — nuevo en 4D-3)

**El bridge oficial `isaacsim.ros2.bridge` está DESCARTADO** — depende duro de `isaacsim.sensors.rtx` → `omni.hydra.rtx` (RTX, sin flag off). NO está ligado a Isaac Lab. NO reabrir.

## rclpy interno de Isaac
```
Ruta:  /isaac-sim/exts/isaacsim.ros2.bridge/humble/rclpy
Trae:  rclpy, rpyutils, ament_index_python, sensor_msgs, std_msgs, geometry_msgs, builtin_interfaces
Carga: sys.path.append(".../humble/rclpy")  DENTRO de on_startup  (Kit NO hereda PYTHONPATH)
```

## numpy para subscriber externo (python pelón de Kit no lo trae)
```
/isaac-sim/extscache/omni.kit.pip_archive-0.0.0+d02c707b.lx64.cp310/pip_prebundle
```

## DDS cross-container (DT-4A-003 RESUELTO)
FastDDS por defecto usa shared memory → NO cruza entre contenedores Docker distintos aunque usen `--network=host`. Fix: forzar UDPv4 vía perfil XML en ambos contenedores.
```xml
<?xml version="1.0" encoding="UTF-8" ?>
<dds xmlns="http://www.eprosima.com/XMLSchemas/fastRTPS_Profiles">
  <profiles>
    <transport_descriptors>
      <transport_descriptor>
        <transport_id>udp_transport</transport_id>
        <type>UDPv4</type>
      </transport_descriptor>
    </transport_descriptors>
    <participant profile_name="udp_participant" is_default_profile="true">
      <rtps>
        <userTransports><transport_id>udp_transport</transport_id></userTransports>
        <useBuiltinTransports>false</useBuiltinTransports>
      </rtps>
    </participant>
  </profiles>
</dds>
```
Montar el XML en ambos contenedores + env `FASTRTPS_DEFAULT_PROFILES_FILE=/fastdds_udp.xml`. CLI `ros2` NO existe — usar subscriber Python rclpy.

## Comando publisher ROS2 (contenedor Isaac)
```bash
timeout 600 docker run --rm --gpus all --network=host \
  -e "ACCEPT_EULA=Y" -e "PRIVACY_CONSENT=Y" \
  -e "PYTHONPATH=/isaac-sim/exts/isaacsim.ros2.bridge/humble/rclpy" \
  -e "LD_LIBRARY_PATH=/isaac-sim/exts/isaacsim.ros2.bridge/humble/lib:$LD_LIBRARY_PATH" \
  -e "RMW_IMPLEMENTATION=rmw_fastrtps_cpp" \
  -e "FASTRTPS_DEFAULT_PROFILES_FILE=/fastdds_udp.xml" \
  -v ~/runs/<fase>/fastdds_udp.xml:/fastdds_udp.xml:ro \
  -v ~/docker/isaac-sim/cache/kit:/isaac-sim/kit/cache:rw \
  -v ~/docker/isaac-sim/cache/ov:/root/.cache/ov:rw \
  -v ~/docker/isaac-sim/cache/pip:/root/.cache/pip:rw \
  -v ~/docker/isaac-sim/cache/glcache:/root/.cache/nvidia/GLCache:rw \
  -v ~/docker/isaac-sim/cache/computecache:/root/.nv/ComputeCache:rw \
  -v ~/runs/<fase>/<fase>.kit:/isaac-sim/apps/<fase>.kit:ro \
  -v ~/runs/<fase>/g1ext:/g1ext:ro \
  --entrypoint /isaac-sim/kit/kit \
  nvcr.io/nvidia/isaac-sim:4.5.0 \
  /isaac-sim/apps/<fase>.kit --no-window --allow-root \
  --ext-folder /isaac-sim/apps --ext-folder /g1ext \
  2>&1 | tee ~/runs/<fase>/<fase>_pub.log
```

## Comando subscriber externo (otro contenedor Isaac, sin GPU)
```bash
docker run --rm --network=host \
  -e "PYTHONPATH=/isaac-sim/exts/isaacsim.ros2.bridge/humble/rclpy:/isaac-sim/extscache/omni.kit.pip_archive-0.0.0+d02c707b.lx64.cp310/pip_prebundle" \
  -e "LD_LIBRARY_PATH=/isaac-sim/exts/isaacsim.ros2.bridge/humble/lib" \
  -e "RMW_IMPLEMENTATION=rmw_fastrtps_cpp" \
  -e "FASTRTPS_DEFAULT_PROFILES_FILE=/fastdds_udp.xml" \
  -v ~/runs/<fase>/fastdds_udp.xml:/fastdds_udp.xml:ro \
  -v ~/runs/<fase>/<subscriber>.py:/<subscriber>.py:ro \
  --entrypoint /isaac-sim/kit/python/bin/python3 \
  nvcr.io/nvidia/isaac-sim:4.5.0 /<subscriber>.py \
  2>&1 | tee ~/runs/<fase>/<fase>_sub.log
```

## Sensores físicos (4D-3B4)
```
Extensión:   isaacsim.sensors.physics  (carga con RTX tolerado — warning ECC, NO crash)
Clases:      IMUSensor, ContactSensor   (ambas con get_current_frame())
IMU frame:   lin_acc / ang_vel / orientation(wxyz)
Contact frame: in_contact / force / time / number_of_contacts
Creación:    prim_path hijo del link + frequency=60 → world.reset_async() → .initialize()
Deprecado:   get_contact_sensor_raw_data (funciona, DT-4D-006)
```

---

# Qué Está Validado Realmente

## Sí validado — Runtime Framework (3C)
- Deterministic Safety Runtime Framework operativo en x86
- Transition Matrix TX-001→TX-010 implementada y testeada
- 86 tests Level 4 — 0 failures | CI green

## Sí validado — VM e Infraestructura (4A)
- Ubuntu 22.04.5 + Docker 29.1.3 + Driver 580.x + CUDA 13.0 | Tesla T4 16GB
- FastDDS (`rmw_fastrtps_cpp` 6.2.10) activo
- **DDS cross-container con UDP forzado (DT-4A-003 resuelto en 4D-3)**

## Sí validado — Isaac Sim 4.2.0 Standalone (4B/4C)
- `python.sh` + `SimulationApp` operativo EN 4.2.0
- G1: 37 DOF, 176 prims, 44 rigid bodies, 40 colliders
- KP runtime ≈ 572,957,824 | KD runtime 0.0 | KD=5.7M mejor punto local

## Sí validado — Isaac Sim 4.5 Camino Ligero en T4 (4D-2)
- `.kit` mínimo sin `exp.base` → `app ready` vía `kit` directo
- Extensión Python propia ejecuta `on_startup` sin `SimulationApp`
- G1 carga (37 DOF), stepping físico, readout sostenido 600 steps
- Reproducible bit-idéntico (60 y 600 steps)

## Sí validado — ROS2 + Observabilidad en T4 (4D-3)
- Mini-bridge propio: rclpy interno carga en el .kit ligero
- G1 publica /joint_states + /g1/base_pose + /g1/base_velocity + IMU + contactos
- Recepción cross-container (otro contenedor) con UDP forzado
- Streaming en vivo con trazabilidad temporal 1:1 (no caché)
- Sensores físicos (IMU + ContactSensor) leídos durante la caída, datos coherentes

## NO validado todavía
- **Control del G1** — todo lo logrado es lectura/observación, sin comandos
- Estabilidad física (robot parado) — se cae sin policy
- IMU+contactos con tipos ROS2 dedicados — pendiente 4D-3B4B
- Runtime determinístico conectado (observador) — pendiente 4D-3C
- Cierre runtime→G1 (eventos/safety) — pendiente 4D-3D
- Standing policy plug-and-play (existencia + ejecución en T4) — pendiente 4E
- Isaac Lab operativo en T4 — riesgo alto (DT-4D-003), matizado
- FastDDS vs CycloneDDS con Unitree SDK2 — pendiente (DT-4A-004)

---

# Hallazgos Críticos Acumulados

| Hallazgo | Valor | Evidencia |
|---|---|---|
| ARTICULATION ROOT | `/World/G1` | output_4c2a.log |
| DOF COUNT | 37 (4.2 y 4.5) | output_4c2b2.log / output_g1_load_ext.log |
| Pies G1 | left/right_ankle_roll_link | 4d3b4a/linklist.log |
| IMU link G1 | torso_link | 4d3b4a/linklist.log |
| Camino ligero T4 → app ready | kit directo + .kit mínimo + loop-isaac | output_g1ext_test.log |
| G1 stepping 600 (4.5/T4) | reproducible bit-idéntico | 4d2h_output.log / 4d2h_repeat_output.log |
| Reposo estable G1 | desde ~step 150, Z≈0.1618, W≈0.671 | 4d2h_output.log |
| `step_async()` en 4.5 | NO awaitable | inspect_step.log |
| rclpy interno Isaac | /isaac-sim/exts/isaacsim.ros2.bridge/humble/rclpy | 4d3a |
| numpy interno (subscriber) | omni.kit.pip_archive/pip_prebundle | 4d3b2 |
| Bridge oficial ROS2 | depende de sensors.rtx → hydra.rtx (RTX) | 4d3a inspección |
| DDS cross-container | shm no cruza; UDP forzado lo resuelve | 4d3b2_sub_udp.log |
| /joint_states publicados+recibidos ext | name=37/pos=37/vel=37, 1542 pub / 1383 recv | 4d3b2 |
| Sensores físicos en T4 | RTX tolerado (warning ECC, no crash) | 4d3b4probe.log |
| IMU/Contact campos | lin_acc/ang_vel/orientation ; in_contact/force | imu_sensor.py / contact_sensor.py |
| Frecuencia publicación real | ~7-8.5 Hz | 4d3b2/4d3b3 logs |
| GPU mínima oficial Isaac 4.5 | RTX 3070 (T4 sin clase RTX) | doc oficial NVIDIA |

---

# Hipótesis Eliminadas con Evidencia

| Hipótesis | Eliminada en |
|---|---|
| "Solo falta pose-hold cinemático" | 4C-3D |
| "Más KD siempre mejora" | 4C-5C, 4C-5D |
| "El T4 no puede arrancar Isaac 4.5 de ninguna forma" | 4D-2B/2D |
| "Existe un experience de fábrica ligero en 4.5" | 4D-2A |
| "`step_async()` es awaitable" | 4D-2E |
| "Volver a Isaac 4.2 resuelve el problema de Isaac Lab" | 4D-2A |
| "La dinámica del G1 difiere entre 4.5 y 4.2" | 4D-2G |
| "El stepping largo (600) degrada/crashea" | 4D-2H |
| "El ROS2 bridge oficial puede usarse sin RTX en T4" | 4D-3A |
| "El bridge oficial está atado a Isaac Lab" | 4D-3A |
| "FastDDS shm cruza entre contenedores con --network=host" | 4D-3B2 |
| "Una sola lectura confirma recepción confiable (no caché)" | 4D-3B2-T |

---

# Decisiones Arquitectónicas Congeladas

| Decisión | Resolución |
|---|---|
| Instalación ROS2 | Docker-first — NO contaminar host |
| ROS2 distro | Humble (22.04 Jammy) |
| DDS vendor standalone | FastRTPS (`rmw_fastrtps_cpp`) |
| **DDS cross-container** | **transporte UDPv4 forzado por XML (shm no cruza contenedores) — DT-4A-003 resuelto** |
| Python version | 3.10 |
| GPU strategy | `--gpus all` (publisher); subscriber externo sin GPU |
| Isaac version activa | 4.5.0 (4.2.0 reconstruible por NGC) |
| **Isaac workflow 4.5** | **`kit` directo + `.kit` mínimo + extensión Python async** |
| **SimulationApp en 4.5** | **CONGELADO — carga full.streaming, crashea en T4 (DT-4D-001)** |
| **ROS2 bridge** | **mini-bridge propio (rclpy interno) — bridge oficial DESCARTADO (RTX duro)** |
| **rclpy en Kit** | **sys.path.append(".../humble/rclpy") dentro de on_startup** |
| **Verificación externa ROS2** | **subscriber Python rclpy (CLI ros2 no existe en la imagen)** |
| **Velocidad de base** | **get_linear_velocities() + get_angular_velocities() separados** |
| Stepping 4.5 | `world.step(render=False)` síncrono |
| Pose 4.5 | `get_world_poses()` plural |
| Sensores físicos | `isaacsim.sensors.physics` (RTX tolerado) |
| Generación de scripts | `cat > ... << 'EOF'` por bloques cortos; validar con ast.parse |
| Iteración sobre validado | copia nueva + backup; carpeta `~/runs/<fase>/` por microfase |

---

# Anti-Patterns Acumulados del Proyecto

## Anti-patrón supremo
> creer que el sistema está más validado de lo que realmente está.

## Anti-patterns específicos (selección + nuevos de 4D-3)

| # | Anti-pattern | Corrección |
|---|---|---|
| 11 | Interpretar silencio de terminal como falla | Startup largo es normal — respetar la ventana |
| 12 | Usar `echo '...'` para generar scripts | `cat > ... << 'EOF'` por bloques cortos |
| 16 | Mezclar múltiples variables en un experimento | Una variable nueva por iteración |
| 17 | Asumir métodos de API sin verificar | Inspeccionar fuente antes de usar |
| 30 | Asumir que `step_async()` es awaitable | Verificar `async def`; usar `world.step(render=False)` |
| 31 | Patrón standalone síncrono dentro de extensión | Patrón async dentro de `on_startup` |
| 32 | Declarar "embodiment estable" tras carga+stepping | "Cargado y observable inicialmente" |
| 33 | Declarar "el T4 sirve" de forma absoluta | Suficiencia solo para la microcapa probada |
| 34 | Declarar "sin RTX pesado" como hecho de hardware | "No observado en el log" — no es profiling GPU |
| 35 | Interpretar exit 124 (timeout) como fallo | `kit` queda vivo tras `app ready`; veredicto = log |
| 36 | Editar el `.kit`/script validado para iterar | Copia nueva + backup; carpeta de fase |
| 37 | Asumir que el default vacío de SimulationApp es ligero | En 4.5 cae a `exp.base.python` (pesado) |
| 38 | Asumir que un nombre de extensión nuevo en la misma `--ext-folder` no colisiona | Verificar qué nombre carga el `.kit`; nombre único, confirmar que apunta a la copia |
| 39 | Asumir que `--network=host` basta para discovery DDS cross-container | FastDDS usa shm por defecto; forzar UDP por XML |
| 40 | Asumir que el python de Kit trae numpy / que Kit hereda PYTHONPATH | Inyectar rutas (rclpy, numpy) explícitamente |
| 41 | Declarar "recepción confirmada" tras una sola lectura (foto) | Validar streaming + trazabilidad (frame_id + timestamp) |
| 42 | Asumir nombres de campos de `get_current_frame()` | Verificar en el fuente del sensor (no "defensivo a ciegas") |
| 43 | Inventar prim_paths de links del robot | Inventariar los prims reales antes de crear sensores |
| 44 | Declarar "sin RTX" tras cargar sensores | Es "RTX tolerado" — plugin RTX carga y advierte, no crashea |
| 45 | Tras caída de red, asumir que la corrida murió con el SSH | El `docker run` sobrevive; limpiar huérfanos con `docker stop` |

---

# Deuda Técnica Activa

| ID | Deuda | Prioridad | Estado |
|---|---|---|---|
| DT-4A-003 | Cross-container DDS characterization | — | ✅ **RESUELTA** (4D-3B2 — UDP forzado) |
| DT-4A-004 | FastDDS vs CycloneDDS — divergencia con Unitree SDK2 | Alta | Abierta — para robot físico |
| DT-4B-003 | Compatibilidad CycloneDDS vs FastRTPS en SDK Unitree | Alta | Abierta |
| DT-4C-004 | `physics_dt` default de `World()` no caracterizado | Baja | Abierta |
| DT-4C-005 | Defaults de `add_default_ground_plane()` no caracterizados | Baja | Abierta |
| DT-4D-001 | Causa exacta de `SimulationApp` → `full.streaming` en 4.5 | Media | Congelada — se evita con `kit` directo |
| DT-4D-002 | `app ready` requiere `omni.kit.loop-isaac`; lifecycle mínimo no caracterizado | Baja | Abierta |
| DT-4D-003 | Viabilidad T4 para render RTX / Isaac Lab / RL | Alta | Abierta — matizada (T4 toleró RTX de sensores sin crash) |
| DT-4D-004 | `add_default_ground_plane()`/`World()` defaults en extensión async | Baja | Abierta |
| DT-4D-005 | "Sin RTX pesado" es inferencia del log, no profiling GPU | Baja | Abierta |
| DT-4D-006 | `get_contact_sensor_raw_data` deprecada en 4.5 (funciona) | Baja | Nueva |
| DT-4D-007 | Etiqueta `estado()` de `sub_live.py` mal calibrada (datos correctos) | Baja | Nueva — fix 3 líneas |
| DT-4D-008 | Contactos publicados como `Float32MultiArray` crudo, no tipo dedicado | Media | Nueva — formalizar en 4D-3B4B |

---

# Conocimiento de Infraestructura Crítico

## NGC y Isaac Sim
- **Registry:** `nvcr.io` | **Auth:** `docker login nvcr.io`, user `$oauthtoken`, pass = API Key NGC
- **Imagen activa:** `nvcr.io/nvidia/isaac-sim:4.5.0`
- **4.2.0:** reconstruible por re-pull NGC (no presente)

## Contexto hardware (doc oficial NVIDIA)
- GPU mínima Isaac Sim 4.5: GeForce RTX 3070, 8GB VRAM. "GPUs sin RT Cores no soportadas". T4 (Turing/Tesla) fuera de clase RTX.
- NVIDIA: el mínimo es límite de soporte/testing, NO bloqueo técnico duro.
- **Matiz nuevo (4D-3B4):** el T4 **toleró** el plugin RTX de los sensores físicos sin crashear — debilita "RTX en T4 = muro absoluto", aunque NO demuestra que Isaac Lab corra.
- Isaac Lab 2.0+ requiere Isaac Sim 4.5+. El requisito RTX aplica igual a 4.2 y 4.5.

## Constraint de disco
```
Total VM: 58GB | ~21-23GB libres | sin LVM | sin segundo disco
No caben dos imágenes Isaac simultáneas → 4.2.0 reconstruible, 4.5.0 presente
```

## Caches persistentes (montar en corridas)
```
~/docker/isaac-sim/cache/{kit,ov,pip,glcache,computecache}
```

---

# Próximo Paso Inmediato — a decidir con el PM

El G1 ya es totalmente observable por ROS2. Hay tres caminos posibles; el PM decide cuál:

**Opción A — 4D-3B4B:** publicar IMU+contactos con tipos ROS2 dedicados (formalizar `Float32MultiArray`→tipo limpio; DT-4D-008). Calcado de 3B3.

**Opción B — 4D-3C:** conectar el Deterministic Runtime Framework como **observador** — suscribirse a la telemetría y evaluar estado (sano/anómalo), **sin control**. Primer contacto runtime↔simulación.

**Opción C — 4E (propuesta):** investigar/verificar una **standing policy plug-and-play** para el G1 que lo mantenga parado (baseline "sano"), requisito para validar el runtime con perturbaciones. NO entrenar.

**Antes de ejecutar cualquier comando:**
1. Leer este bootstrap + `informe_etapa_4D3_2026-06-08.md` + tesis v12
2. Verificar estado VM (Regla 8, incluyendo huérfanos si hubo corte de red)
3. Obtener aprobación explícita del PM
4. Usar el camino ligero + mini-bridge propio validados
5. Trabajar en `~/runs/<fase>/` con copia; preservar baselines

**Restricciones activas:**
- Sin `SimulationApp`, sin bridge oficial, sin RTX pesado
- Sin control (todo observación) hasta que el PM lo autorice formalmente
- Una variable nueva por corrida; máximo 2 comandos por mensaje
- NO asumir que el operador quiere entrenar — quiere plug-and-play

---

# Objetivo Final

Construir un pipeline: reproducible, observable, auditado, portable, ROS2-native, Isaac-compatible, y operacionalmente honesto.

El objetivo inmediato concreto: **validar el Deterministic Safety Runtime Framework** contra estados del G1 — para lo cual se necesita un baseline "sano" (robot parado vía policy plug-and-play) contra el cual contrastar estados anómalos.

No optimizar por velocidad narrativa. Optimizar por evidencia, trazabilidad y robustez verificable.

---

*G1 ROS2 Pipeline — CHAT_BOOTSTRAP_PROTOCOL.md v9*
*Actualizado: 2026-06-08*
*4C ✅ | 4D-1 ✅ | 4D-2A–2H ✅ | 4D-3A–3B4A ✅ | 4D-3B4B/3C/3D 🔲 | 4E 🔲 propuesta | 5A 🔒 | DT-4A-003 RESUELTA*
