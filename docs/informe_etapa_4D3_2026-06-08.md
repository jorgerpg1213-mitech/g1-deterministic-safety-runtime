# Informe de Sesión — Bloque 4D-3 (ROS2 Feasibility + Observabilidad Sensorial del G1 en Tesla T4)
## G1 ROS2 Pipeline — Proyecto Humanoide Unitree G1
**Fecha:** 2026-06-08 (sesión vespertina, continuación de la sesión 4D-2)
**Estado al cierre:**
- 4D-2G ✅ | 4D-2H ✅ | 4D-3A ✅ | 4D-3B1 ✅ | 4D-3B2 ✅ | 4D-3B3 ✅ | 4D-3B4 (probe) ✅ | 4D-3B4A ✅
- 4D-3B4B 🔲 Pendiente — Publicar IMU + contactos por ROS2 con tipos dedicados
- 4D-3C 🔲 Pendiente — Runtime determinístico en modo OBSERVADOR
- 4D-3D 🔲 Pendiente — Primer cierre runtime → G1 (eventos/safety, sin control físico)
- 4E 🔲 Propuesta nueva (pendiente decisión PM) — Standing policy plug-and-play + validación de estado del runtime
- 5A 🔒 Bloqueada — Isaac Lab (riesgo T4/RTX, DT-4D-003)

**Roles:** PM: ChatGPT | Implementador/Auditor: Claude | Operador: Jorge Padilla
**Referencia previa:** `informe_etapa_4D2_2026-06-08.md`

---

## 0. Resumen Ejecutivo

Esta sesión completó el bloque 4D-2 (estabilidad y readout sostenido) y abrió y avanzó sustancialmente el bloque 4D-3 (ROS2 + observabilidad), logrando el **primer flujo de telemetría del G1 simulado hacia un proceso externo vía ROS2 real, sin RTX, en el Tesla T4**.

Hallazgos centrales de la sesión:

1. **El ROS2 bridge oficial fue descartado con evidencia, no por suposición.** `isaacsim.ros2.bridge` (v4.1.15) depende de forma dura de `isaacsim.sensors.rtx` → `omni.hydra.rtx`, el stack RTX que el T4 no soporta. No hay flag para desactivarlo y NO está ligado a Isaac Lab. La decisión fue construir un **mini-bridge propio** usando el `rclpy` interno de Isaac.

2. **El `rclpy` interno de Isaac es viable en el camino ligero.** Vive en `/isaac-sim/exts/isaacsim.ros2.bridge/humble/rclpy` y se carga inyectando esa ruta en `sys.path` dentro de `on_startup` (Kit no hereda `PYTHONPATH`). Confirma que el runtime determinístico puede usar ROS2 sobre la capa ligera del T4.

3. **El G1 publica su estado por ROS2 real y un proceso externo lo recibe en vivo.** Se publicaron `/joint_states`, `/g1/base_pose`, `/g1/base_velocity`, y posteriormente IMU + contactos. Un subscriber en un **contenedor separado** recibió la telemetría con datos coherentes, sincronía 1:1 frame-por-frame y sin pérdida — validado con trazabilidad temporal explícita.

4. **DT-4A-003 (cross-container DDS characterization, abierta desde 4A) quedó RESUELTA.** Causa raíz: FastDDS por defecto usa shared memory, que no cruza entre contenedores Docker distintos aunque compartan `--network=host`. Solución: forzar transporte UDPv4 vía perfil XML (`FASTRTPS_DEFAULT_PROFILES_FILE`) en ambos contenedores.

5. **Los sensores físicos (IMU + ContactSensor) son viables en T4 con matiz "RTX tolerado".** `isaacsim.sensors.physics` carga, instancia sensores y los lee sin crash. Arrastra un plugin RTX (`rtx.neuraylib`, vía `omni.replicator.core`) que emite warnings ECC pero **no crashea** — distinto al fallo duro de 4D-2A. Se leyó IMU (orientación, lin_acc, ang_vel) y contactos de ambos pies (in_contact, force) durante la caída completa del G1, con datos físicamente coherentes.

**Naturaleza del resultado — declarada con precisión epistemológica:**
- Esto es un **positivo de feasibility de observabilidad**: el G1 es totalmente observable por ROS2 (joints + pose + velocidad + IMU + contactos) hacia procesos externos, sin RTX pesado, en T4.
- NO significa "control" — todo lo logrado es lectura/observación; no se envió ningún comando al robot.
- NO significa "embodiment estable" — el G1 sigue cayéndose sin policy (esperado).
- NO significa "RTX resuelto" — los sensores arrastran un plugin RTX tolerado, no es un camino cero-RTX absoluto.
- El streaming en vivo de la última prueba (4D-3B4A-live) fue interrumpido por una caída de red de la VM (evento externo); la evidencia esencial ya estaba capturada antes del corte.

**Punto estratégico abierto al cierre:** se clarificó que el objetivo real del operador NO es entrenar locomoción, sino **validar el Deterministic Safety Runtime Framework** contra estados del G1, lo que requiere como mínimo un robot **parado/estable** (estado "sano" de fábrica) mediante una **policy de standing plug-and-play** (no entrenada localmente). Esto reorienta el roadmap: 5A (Isaac Lab para entrenar) deja de ser ruta crítica; se propone una nueva microfase **4E** para buscar/ejecutar una standing policy lista.

---

## 1. Contexto y Objetivo de Sesión

El trabajo partió del cierre de 4D-2A–2F (camino ligero validado: el G1 carga y steppea en Isaac Sim 4.5 sobre T4, reproducible bit-idéntico). Quedaban pendientes 4D-2G, 4D-2H y la apertura de 4D-3 (ROS2 feasibility).

La pregunta que guió la sesión fue progresiva:

> ¿Es consistente la dinámica del G1 entre 4.5 y 4.2? ¿Aguanta readout sostenido (300–600 steps) sin degradación? ¿Puede ROS2 cargarse sobre el camino ligero sin traer el stack pesado? Si el bridge oficial no sirve, ¿hay alternativa? ¿Puede un proceso externo recibir el estado del G1 por ROS2 real? ¿Son viables los sensores físicos (IMU/contactos) en el T4?

La sesión respondió todas con evidencia observable. No resolvió control ni estabilidad física — esos objetivos pertenecen a microfases posteriores (y, según la clarificación del cierre, a la propuesta 4E vía policy plug-and-play).

---

## 2. Estado del Entorno al Inicio de Sesión

**VM:** Ubuntu 22.04.5 LTS | Tesla T4 16GB (15606 MB) | Docker 29.1.3 | CUDA 13.0 | NVIDIA Driver 580.159.03
**CPU:** Intel Xeon Gold 6152 @ 2.10GHz | 2 cores / 4 lógicos | 32GB RAM (~30GB libres)
**Imagen Isaac:** `nvcr.io/nvidia/isaac-sim:4.5.0`
**Imágenes ROS intactas:** `g1-ros-phase-a:humble`, `g1-ros-phase-b:humble`
**Backup:** `~/backup_4c/` — 44 archivos (scripts/logs 4C) intacto
**Baseline 4.5:** extensión `isaacsim.g1.runtime` (4D-2) intacta; logs `output_g1_step_v2.log`/`output_g1_step_repeat.log` (7776 B c/u, bit-idénticos)

**Disciplina de carpetas adoptada en esta sesión:** cada microfase recibió su propia carpeta autocontenida `~/runs/4dXXX/` (extensión + `.kit` + logs + subscriber), de modo que el baseline nunca se edita y cada experimento es reversible y auditable de forma aislada.

---

## 3. Estructura de la Sesión — Microfases Ejecutadas

```
4D-2G   Serie reducida estabilidad 4.5 vs 4.2          ✅ Cerrada — análisis documental (sin corrida nueva)
4D-2H   Sustained readout 600 steps (+ repeat)         ✅ Cerrada — bit-idéntico, sin degradación
4D-3A   ROS2 bridge feasibility → mini-bridge propio    ✅ Cerrada — rclpy interno en kit ligero
4D-3B1  G1 + rclpy coexisten (+ step version)           ✅ Cerrada — rclpy_ok durante 300 steps
4D-3B2  Publisher /joint_states + recepción externa     ✅ Cerrada — DT-4A-003 resuelto (+ trazabilidad 3B2-T)
4D-3B3  Estado mínimo (joints + pose + velocidad)       ✅ Cerrada — 3 topics, datos coherentes
4D-3B4  Probe sensores físicos (sin crash, RTX tolerado)✅ Cerrada — IMU + Contact classes disponibles
4D-3B4A IMU + 2 ContactSensor leídos (+ live-stream)    ✅ Cerrada — caída instrumentada coherente
```

---

## 4. Etapa 4D-2G — Serie Reducida de Estabilidad 4.5 vs 4.2

### Pregunta central
¿La dinámica del G1 en 4.5 (camino ligero) es consistente con el baseline de 4C en 4.2, o aparece una divergencia/bug nuevo en 4.5?

### Método (sin corrida nueva — criterio de no gastar corridas)
Ambos lados de la comparación ya existían en disco. Se cerró por **análisis documental** de logs existentes (Regla 9 — no regenerar datos guardados e intactos), bajo criterio explícito del PM que exigió entregar la tabla comparada antes de declarar cierre.

- **Lado 4.5:** `~/output_g1_step_v2.log` (corrida 2E/2F, defaults sin policy).
- **Lado 4.2:** `~/backup_4c/output_4c5a.log` (4C, stepping sin control, KD=0), con apoyo de la familia `4c5a–5d` y `4c3d` (misma tendencia).

### Tabla comparada (Z, XY_NORM, W en cortes 0/10/30/60)

| step | Z 4.2 | Z 4.5 | XY_NORM 4.2 | XY_NORM 4.5 | W 4.2 | W 4.5 | interpretación |
|---|---|---|---|---|---|---|---|
| 0 | 0.1005 | 0.1508 | 0.0000 | 0.0001 | 1.0000 | 1.0000 | en piso, vertical, quieto |
| 10 | 0.5893 | 0.6317 | 0.0505 | 0.0677 | 0.9995 | 0.9971 | impulso del controller, sube |
| 30 | 0.8335 | 0.8717 | 0.3370 | 0.3691 | 0.9621 | 0.9402 | pico de altura, empieza a inclinar |
| 60 | 0.1440 | 0.2092 | 0.7386 | 0.8191 | 0.6574 | 0.7217 | desplomado, lejos del origen, sin verticalidad |

*Z/XY_NORM/W del 4.5 calculados desde XYZ/WXYZ del log: `XY_NORM=√(X²+Y²)`, `W`=primer componente del cuaternión.*

### Diferencia cualitativa declarada (rigor)
El 4.5 arranca ~5 cm más alto (0.15 vs 0.10) y cae un poco menos pronunciado (W 0.72 vs 0.66, Z 0.21 vs 0.14). Posible causa: distinto link de referencia en `get_world_poses()` 4.5 vs el cómputo de 4C, o altura de spawn — **no validado, etiquetado como hipótesis no confirmada**. No rompe la tendencia.

### Conclusión
Misma física en ambas versiones — arranque bajo → elevación/transitorio hacia step 30 → toppling hacia step 60 (W cae de ~1.0 a ~0.7). 4.5 reproduce la dinámica de 4.2. Sin divergencia inexplicada, sin bug nuevo. La robustez no depende de cuál log 4C se elija (los cinco muestran la misma tendencia).

**Estado:** ✅ Cerrada por evidencia documental (declarada por el PM) — no requirió corrida nueva de Isaac

---

## 5. Etapa 4D-2H — Sustained Readout (600 steps) + Repetibilidad

### Pregunta central
¿Isaac 4.5 + camino ligero sostiene el stepping físico durante 600 steps (horizonte 10× mayor que 2E) sin crash, degradación numérica ni pérdida de readout? ¿El G1 ya tumbado sigue siendo legible?

### Disciplina aplicada (copia reversible, una variable)
La única variable fue el horizonte (60→600). Se trabajó sobre **copia** del baseline validado, nunca sobre el original. La extensión de fase quedó como `isaacsim.g1.runtime.h2` en `~/runs/4d2h/`, con su `.kit` propio (`4d2h.kit`). Diff mínimo verificado antes de correr: solo dos líneas (`range(61)`→`range(601)`; cortes `[0,10,30,60]`→`[0,60,150,300,450,600]`).

**Nota de disciplina (incidente de estructura, resuelto):** la creación de la copia generó momentáneamente confusión de namespacing (intermediarios `__init__.py`, colisión potencial del nombre de extensión con el baseline en la misma `--ext-folder`). Se saneó volviendo al patrón probado: nombre de extensión único, sin huérfanos, baseline original intacto, verificación explícita de que el `.kit` apunta a la copia y no al baseline viejo de 60 pasos. Riesgo de "gastar la corrida cargando el baseline equivocado" mitigado por verificación previa (solo lectura).

### Resultados (corrida real, log en vivo con `tee`)

```
STARTUP EXTENSION OK → G1 LOADED → num_dof: 37
STEP 60  pos=[0.81788075 -0.04528854 0.2092318]   quat=[0.72170717 0.2955109 0.6259022 0.00764688]
STEP 150 pos=[0.87987673 -0.09674464 0.16183127]  quat=[0.67142034 0.38127184 0.6247256 0.11638101]
STEP 300 pos=[0.8798413  -0.09684135 0.16182469]  quat=[0.6714461  0.38138148 0.62467664 0.11613536]
STEP 450 pos=[0.87984204 -0.0968433  0.1618251 ]  quat=[0.67144465 0.3813857  0.62467474 0.11614003]
STEP 600 pos=[0.8798319  -0.09682868 0.16183853]  quat=[0.6714651  0.38133323 0.6246908  0.11610712]
=== PHYS STEPPING DONE ===
```

### Interpretación (declarada con cuidado)
El G1 cae hasta ~step 60, y **desde ~step 150 alcanza un estado de reposo estable**: la pose Z se congela en ~0.1618 y el cuaternión en W≈0.671 hasta el step 600 (variación solo en los últimos decimales, atribuible a micro-asentamiento físico). No hay NaN, no hay explosión numérica, no hay degradación, no hay crash. El robot tumbado **sigue siendo perfectamente legible** durante todo el horizonte largo.

### Repetibilidad (2H-repeat)
Repetición exacta de la corrida → resultado **bit-idéntico** a 2H (poses y cuaterniones iguales hasta el último decimal). Confirma que el determinismo del camino ligero (ya visto en 2F a 60 steps) se mantiene en horizonte largo (600 steps).

**Estado:** ✅ Cerrada — readout sostenido 600 steps sin degradación, reproducible bit-idéntico

---

## 6. Etapa 4D-3A — ROS2 Bridge Feasibility → Decisión de Mini-Bridge Propio

### Pregunta central
¿Puede cargarse ROS2 sobre el `.kit` mínimo sin traer el stack pesado RTX que crashea en el T4?

### Exploración del bridge oficial (offline, inspección de dependencias)
El bridge oficial `isaacsim.ros2.bridge` (v4.1.15, en `/isaac-sim/exts/`) fue inspeccionado. Hallazgo:

```
isaacsim.ros2.bridge → depende de isaacsim.sensors.rtx → omni.hydra.rtx (RTX, NO opcional)
```

- El bridge oficial arrastra de forma **dura** el stack RTX que el T4 no soporta (el mismo que causó el crash de 4D-2A).
- **NO existe flag** para desactivar RTX en el bridge oficial.
- **El bridge oficial NO está ligado a Isaac Lab** — es independiente; su dependencia RTX es propia.

### Decisión arquitectónica (con aprobación PM)
Descartar el bridge oficial y construir un **mini-bridge propio** usando el `rclpy` interno de Isaac.

### Hallazgo — `rclpy` interno de Isaac
El `rclpy` interno vive en:
```
/isaac-sim/exts/isaacsim.ros2.bridge/humble/rclpy
```
Esa carpeta trae `rclpy`, `rpyutils`, `ament_index_python`, `sensor_msgs`, `std_msgs`, `geometry_msgs`, `builtin_interfaces` — todo lo necesario para publicar/suscribir. NO trae `local_setup.bash` (no es un overlay ROS completo, solo las libs Python).

### Corrección clave (Kit no hereda PYTHONPATH)
- **Probe standalone** (Python directo): `import rclpy` OK.
- **Probe dentro de Kit**: falló con `ModuleNotFoundError` — Kit no hereda el `PYTHONPATH` del entorno.
- **Fix confirmado:** inyectar la ruta en `sys.path` **dentro de `on_startup`**:
  ```python
  sys.path.append("/isaac-sim/exts/isaacsim.ros2.bridge/humble/rclpy")
  import rclpy
  ```
  Resultado: `RCLPY IN KIT OK`.

**Estado:** ✅ Cerrada — ROS2 viable sobre el camino ligero vía rclpy interno; bridge oficial descartado con evidencia (RTX duro)

---

## 7. Etapa 4D-3B1 — G1 + rclpy Coexisten

### Pregunta central
¿Pueden el G1 (carga + stepping físico) y `rclpy` (init + nodo) coexistir en el mismo proceso Kit sin conflicto?

### Resultado
El G1 cargó (37 DOF) y `rclpy` quedó inicializado y vivo en el mismo proceso. En la **versión step** (4D-3B1-step), `rclpy` se mantuvo vivo durante 300 steps físicos, con `rclpy_ok=True` en todos los cortes, sin conflicto entre el loop de física y el contexto ROS2.

**Artefactos:** `~/runs/4d3b1/`, `~/runs/4d3b1step/`

**Estado:** ✅ Cerrada — coexistencia G1 + rclpy confirmada en horizonte de stepping

---

## 8. Etapa 4D-3B2 — Publisher `/joint_states` + Recepción Externa + DT-4A-003

### Pregunta central
¿Puede el G1 publicar `/joint_states` por ROS2 real y un proceso externo (otro contenedor) recibirlo?

### Publisher interno (confirmado)
Extensión `isaacsim.g1.jointpub` (`~/runs/4d3b2/`). Publicó **1542 mensajes** de `/joint_states` con longitudes correctas: `name=37 / pos=37 / vel=37`, cierre limpio (`PUBLISH WINDOW DONE` + `RCLPY SHUTDOWN CLEAN`). El publisher interno quedó plenamente validado.

### Cuello detectado — recepción externa = 0 mensajes
Un subscriber Python (rclpy) en un **contenedor separado** (`--network=host`) arrancó, escuchó durante toda la ventana de 180s, y recibió **0 mensajes**, pese a que el publisher emitía 1542. Diagnóstico firme: **no es fallo del publisher ni del subscriber** — es discovery DDS cross-container.

### DT-4A-003 RESUELTO — causa raíz y fix
- **Causa raíz:** FastDDS por defecto prioriza **shared memory** para procesos del mismo host. Dos contenedores Docker distintos **no comparten** el segmento `/dev/shm`, aunque usen `--network=host`. Se "ven" en red pero no por el transporte que FastDDS eligió.
- **Fix (variable única: transporte shm→UDP):** perfil XML `fastdds_udp.xml` forzando transporte UDPv4 (`<useBuiltinTransports>false</useBuiltinTransports>`), aplicado en **ambos** contenedores vía la env var `FASTRTPS_DEFAULT_PROFILES_FILE=/fastdds_udp.xml`.
- **Resultado tras el fix:**
  ```
  === RECEIVED 1st msg: names=37 pos=37 vel=37 ===
    name[0:3]=['torso_joint', 'left_shoulder_pitch_joint', 'right_shoulder_pitch_joint']
    pos[0:3]=[-0.0001, 0.0001, 0.6781]
  === SUB DONE: total received 100 msgs ===
  ```
  Nombres reales del G1, posiciones de reposo coherentes. Recepción cross-container confirmada.

Esto promueve **DT-4A-003** (cross-container DDS characterization, abierta desde Etapa 4A) de "inconclusa" a **RESUELTA**.

### Detalle de plomería de dependencias (subscriber externo)
El subscriber corre con `/isaac-sim/kit/python/bin/python3` "pelón", que NO trae numpy. `sensor_msgs` lo requiere para deserializar. Fix: añadir al `PYTHONPATH` la ruta del numpy interno de Isaac:
```
/isaac-sim/extscache/omni.kit.pip_archive-0.0.0+d02c707b.lx64.cp310/pip_prebundle
```
Nota: el CLI `ros2` NO existe en la imagen Isaac — toda verificación externa se hizo con subscriber Python rclpy, no con `ros2 topic`.

### 4D-3B2-T — Trazabilidad temporal (freshness)
A petición del operador (validar que el subscriber sigue al publisher **en vivo**, no caché), se instrumentó un contador incremental en `header.frame_id` (publisher) y un subscriber que imprime `frame_id` recibido + hora local. Resultado contundente:

```
[21:52:05] recv#25  publisher_frame_id=183   (entró tarde — capturó el msg del momento, no caché)
[21:52:32] recv#250 publisher_frame_id=408
[21:53:30] recv#750 publisher_frame_id=908
=== TRACE DONE: total 1383 msgs, first_frame_id=159 ===
```

Evidencia de seguimiento en vivo:
- **Entró tarde y capturó el frame del momento** (first_frame_id=159, no 0) → no es caché.
- **Diferencia constante recv# vs frame_id ≈ 158–159** durante toda la corrida → cero pérdida de mensajes desde que empezó a escuchar.
- **Correlación cruzada T1↔T2 al segundo:** publisher `PUBLISHED 700` @ 21:53:41 ↔ subscriber `frame=699` @ 21:53:41.
- **Conteo coherente:** 1542 publicados − 159 previos al arranque del subscriber ≈ 1383 recibidos.

**Artefactos:** `~/runs/4d3b2/` (`fastdds_udp.xml`, `sub_check.py`, `sub_trace.py`, logs pub/sub/trace)

**Estado:** ✅ Cerrada — recepción externa cross-container confirmada, en vivo, sin pérdida; DT-4A-003 resuelto

---

## 9. Etapa 4D-3B3 — Estado Mínimo del G1 (joints + base pose + base velocity)

### Pregunta central
¿Puede el G1 publicar su paquete de estado mínimo observable (articulaciones + posición/orientación global + velocidad de base) por ROS2, usando solo APIs verificadas?

### Verificación previa de API (Regla 12 — no inventar base_velocity)
Inspección de `/isaac-sim/exts/isaacsim.core.prims/.../articulation.py`:
```
def get_world_poses(        línea 1832
def get_velocities(         línea 2103
def get_linear_velocities(  línea 2213
def get_angular_velocities( línea 2321
```
Confirmó que la velocidad de base existe en la API 4.5. **Decisión de diseño (criterio PM):** para evitar ambigüedad en el orden del array de 6 de `get_velocities()`, se usaron `get_linear_velocities()` y `get_angular_velocities()` **por separado**, mapeando cada uno a su campo del `Twist` sin riesgo de cruce.

### Topics publicados
| Topic | Tipo ROS2 | Fuente API |
|---|---|---|
| `/joint_states` | `sensor_msgs/JointState` | `dof_names` + `get_joint_positions/velocities` |
| `/g1/base_pose` | `geometry_msgs/PoseStamped` | `get_world_poses()` |
| `/g1/base_velocity` | `geometry_msgs/TwistStamped` | `get_linear_velocities()` + `get_angular_velocities()` (separados) |

**Decisión declarada:** se dejó fuera `/g1/state_summary` (cayó/estable). Es interpretación derivada; corresponde al runtime observador, no al publisher (mantiene el publisher como emisor de estado crudo, una preocupación por capa).

### Resultado (subscriber externo, 3 topics)
```
JOINT_STATES OK: names=37 pos=37 vel=37
BASE_POSE OK: xyz=[0.88,-0.097,0.162] wxyz=[0.672,0.383,0.623,0.114]
BASE_VELOCITY OK: lin=[-0.0083,-0.0092,-0.0003] ang=[0.0383,0.0125,0.0041]
SUB DONE: js=50 pose=50 vel=50
```
La pose Z=0.162 coincide exactamente con el reposo de 2H; las velocidades ≈0 confirman robot quieto en el piso. Lineal y angular bien separados (sin cruce). Corrida full posterior (180s) confirmó publicación sostenida a ~8.5 Hz sin degradación, robot estable en Z=0.1618.

**Artefactos:** `~/runs/4d3b3/` (extensión `isaacsim.g1.statepub`, `4d3b3.kit`, `sub_3topics.py`, `sub_3topics_full.py`)

**Estado:** ✅ Cerrada — paquete de estado mínimo observable completo, datos coherentes cross-container

---

## 10. Etapa 4D-3B4 (probe) — Viabilidad de Sensores Físicos

### Pregunta central
¿Puede `isaacsim.sensors.physics` (IMU + ContactSensor) cargar en el `.kit` mínimo sin reproducir el crash RTX de 4D-2A?

### Exploración previa (offline)
- `isaacsim.sensors.physics` expone las clases `IMUSensor` y `ContactSensor`, ambas con `get_current_frame()`.
- Su `extension.toml` depende de `omni.replicator.core` (sospechoso de arrastrar RTX), pero **NO** de `hydra.rtx` ni `sensors.rtx` directamente.

### Probe (cargar la extensión sola, sin G1, sin sensores, sin publicar)
```
SENSORS.PHYSICS IMPORT OK
IMU + CONTACT CLASSES AVAILABLE
[16.561s] app ready
[rtx.neuraylib.plugin] [IRAY:RENDER] CUDA device 0 (Tesla T4): ECC is enabled... (warning, NO crash)
```

### Veredicto — "RTX tolerado" (declarado con precisión)
La extensión carga, las clases están disponibles, se alcanza `app ready`, **sin crash, sin DescriptorSet**. PERO aparece un warning de `rtx.neuraylib.plugin` (iray) sobre ECC del T4 — significa que `sensors.physics` (vía `replicator.core`) carga un plugin RTX en background que el T4 **tolera** (solo advierte rendimiento, no crashea). Esto es **distinto** a 4D-2A, donde el stack RTX crasheaba con errores `DescriptorSet`.

Conclusión: IMU/contactos **viables** en el camino ligero, con la nota de que ya **no es "cero RTX absoluto"** — es "RTX tolerado". Declarado y aceptado por PM con cautela.

**Artefactos:** `~/runs/4d3b4probe/`

**Estado:** ✅ Cerrada — sensores físicos viables en T4 con matiz "RTX tolerado"

---

## 11. Etapa 4D-3B4A — IMU + 2 ContactSensor Leídos (caída instrumentada)

### Pregunta central
¿Pueden instanciarse y leerse sensores físicos reales (IMU en torso + ContactSensor en cada pie) durante el stepping, con datos coherentes con la física observada?

### Inspección previa de links del G1 (no inventar prim_paths)
Corrida de inventario (`isaacsim.g1.linklist`) que cargó el G1 e imprimió sus prims. Resultado:
- 37 `dof_names` confirmados (torso_joint, shoulder/hip/knee/ankle pitch/roll/yaw, dedos).
- **Pies:** `/World/G1/left_ankle_roll_link` y `/World/G1/right_ankle_roll_link` (el último link de cada pierna, el que toca el suelo).
- **Torso (IMU):** `/World/G1/torso_link`.

### Verificación de campos de `get_current_frame()` (no asumir nombres)
Inspección del fuente de `imu_sensor.py` y `contact_sensor.py`:
- **IMU:** `lin_acc` [x,y,z], `ang_vel` [x,y,z], `orientation` [w,x,y,z].
- **Contacto:** `in_contact` (bool), `force` (float), `time`, `number_of_contacts`.

Sensores creados con `prim_path` hijo del link (ej. `/World/G1/torso_link/imu_sensor`), `frequency=60`, luego `world.reset_async()` → `.initialize()`.

### Resultado — caída completa instrumentada (300 steps)

| Step | IMU orientación (W) | IMU ang_vel | Pie L (in_contact / force) | Pie R (in_contact / force) | Estado físico |
|---|---|---|---|---|---|
| 0 | 1.000 (vertical) | bajo | True / 13.96 N | True / 3.84 N | de pie, ambos pies tocan |
| 60 | 0.727 (inclinado) | pico (avZ≈5.0) | False / 0 | True / 34.77 N | cayendo, peso en un pie |
| 150 | 0.671 (volteado) | ≈0 (quieto) | False / 0 | False / 0 | tumbado, ningún pie toca |
| 300 | 0.671 (idéntico) | ≈0 | False / 0 | False / 0 | tumbado estable |

### Interpretación
Los sensores cuentan la física real de la caída, coherente con la pose de 2H/3B3: arranca con los dos pies en el suelo, el izquierdo despega primero, el derecho aguanta un instante con más fuerza (34 N, el peso pasando a un pie), y al final ningún pie toca (robot tumbado de lado). El IMU captó el giro (ang_vel disparado en step 60, ~0 al final). `lin_acc` ~11 en Z al inicio = gravedad, normal. Sin crash, hasta `SENSOR READ DONE`.

**Nota técnica:** `get_contact_sensor_raw_data` está marcada como deprecada (funciona en 4.5, pero conviene migrar antes de producción) → nueva deuda técnica DT-4D-006.

### 4D-3B4A-live-stream-validation (parcial — exitoso en lo esencial)
Prueba de streaming en vivo de IMU + contactos por ROS2: T2 (subscriber) lanzado primero, esperó sin morir, capturó desde frame=0 la secuencia DE_PIE → cayendo → tumbado, sincronizado con T1 al segundo (T1 `PUBLISHED 700` @ 23:09:41 ↔ T2 `frame=699` @ 23:09:41), durante 1383+ frames, sin caché. Publicó `/g1/imu` (`sensor_msgs/Imu`) y `/g1/feet` (`std_msgs/Float32MultiArray` = `[count, L_contact, L_force, R_contact, R_force]`).

- **Resultado:** streaming en vivo cross-container confirmado, correlación frame-por-frame al segundo, sin lag ni caché.
- **Defecto conocido (cosmético, no de datos):** la función `estado()` del subscriber `sub_live.py` tiene un umbral mal calibrado — marca `CAYENDO` permanente porque la condición incluye `0.67 < w < 0.95` y el robot en reposo tiene W=0.672. Los **datos** son correctos; solo la **etiqueta** interpretada miente. Fix = 3 líneas en el subscriber (no toca publisher ni sensores) → nueva deuda DT-4D-007.
- **Interrupción externa:** la corrida fue cortada por una caída de red de la VM (evento externo, ajeno al proyecto). La evidencia esencial ya estaba capturada. El contenedor T1 quedó huérfano y se limpió con `docker stop` tras reconectar (lección: el `docker run` sobrevive a la caída de SSH; verificar entorno limpio tras corte de red).

**Artefactos:** `~/runs/4d3b4a/` (inventario de links, extensión `isaacsim.g1.sensorread`), `~/runs/4d3b4live/` (extensión `isaacsim.g1.livesensor`, `live.kit`, `sub_live.py`)

**Estado:** ✅ Cerrada (4D-3B4A) — IMU + contactos leídos con datos coherentes; live-stream validado en lo esencial (etiqueta pendiente de fix)

---

## 12. Tabla de Hipótesis del Bloque 4D-3

| Hipótesis | Estado | Eliminada/resuelta en |
|---|---|---|
| "La dinámica del G1 difiere entre 4.5 y 4.2 (bug nuevo en 4.5)" | ❌ Eliminada | 4D-2G — misma tendencia |
| "El stepping largo (600) degrada o crashea en 4.5/T4" | ❌ Eliminada | 4D-2H — bit-idéntico, sin degradación |
| "El ROS2 bridge oficial puede usarse sin RTX en T4" | ❌ Eliminada | 4D-3A — depende duro de sensors.rtx/hydra.rtx |
| "El bridge oficial está atado a Isaac Lab" | ❌ Eliminada | 4D-3A — es independiente |
| "rclpy interno de Isaac carga en el .kit ligero" | ✅ Confirmada | 4D-3A — `RCLPY IN KIT OK` (con sys.path fix) |
| "G1 + rclpy coexisten sin conflicto" | ✅ Confirmada | 4D-3B1 — rclpy_ok durante 300 steps |
| "El G1 publica /joint_states por ROS2 real" | ✅ Confirmada | 4D-3B2 — 1542 msgs, 37/37/37 |
| "Un proceso externo recibe el estado del G1 cross-container" | ✅ Confirmada | 4D-3B2 — tras fix UDP |
| "FastDDS shm cruza entre contenedores con --network=host" | ❌ Eliminada | 4D-3B2 — shm no cruza; requiere UDP |
| "El subscriber sigue al publisher en vivo (no caché)" | ✅ Confirmada | 4D-3B2-T — first_frame_id=159, sincronía 1:1 |
| "base_velocity existe en la API 4.5" | ✅ Confirmada | 4D-3B3 — get_linear/angular_velocities |
| "Los sensores físicos cargan en T4 sin crash" | ✅ Confirmada (con matiz) | 4D-3B4 — RTX tolerado, no crash |
| "IMU + contactos producen datos coherentes con la física" | ✅ Confirmada | 4D-3B4A — caída instrumentada coherente |
| "El T4 sirve para Isaac Lab completo / RL / RTX" | 🔲 No probada | Fuera de alcance — riesgo alto documentado |

---

## 13. Artefactos Producidos en Esta Sesión

| Artefacto | Microfase | Propósito |
|---|---|---|
| `~/runs/4d2h/g1ext/isaacsim.g1.runtime.h2/` | 4D-2H | extensión copia 600 steps (baseline intacto) |
| `~/runs/4d2h/4d2h.kit` + `4d2h_output.log` + `4d2h_repeat_output.log` | 4D-2H | corrida sostenida + repeat bit-idéntico |
| `~/runs/4d3a/` | 4D-3A | probes rclpy (standalone + en kit) |
| `~/runs/4d3b1/`, `~/runs/4d3b1step/` | 4D-3B1 | coexistencia G1 + rclpy |
| `~/runs/4d3b2/fastdds_udp.xml` | 4D-3B2 | perfil FastDDS UDP (fix DT-4A-003) |
| `~/runs/4d3b2/` (ext `isaacsim.g1.jointpub`, `sub_check.py`, `sub_trace.py`) | 4D-3B2 | publisher /joint_states + subscribers externos |
| `~/runs/4d3b3/` (ext `isaacsim.g1.statepub`, `4d3b3.kit`, `sub_3topics*.py`) | 4D-3B3 | estado mínimo 3 topics |
| `~/runs/4d3b4probe/` (ext `isaacsim.g1.sensorprobe`) | 4D-3B4 | probe carga sensores físicos |
| `~/runs/4d3b4a/` (ext `isaacsim.g1.linklist` + `isaacsim.g1.sensorread`) | 4D-3B4A | inventario links + lectura IMU/contactos |
| `~/runs/4d3b4live/` (ext `isaacsim.g1.livesensor`, `live.kit`, `sub_live.py`) | 4D-3B4A | streaming en vivo IMU + contactos |

**Logs clave:** `4d2h_output.log`, `4d2h_repeat_output.log`, `4d3b2_pub_udp.log`, `4d3b2_sub_udp.log`, `4d3b2_pub_trace.log`, `4d3b2_sub_trace.log`, `4d3b3_pub.log`, `4d3b3_sub.log`, `4d3b4probe.log`, `4d3b4a/sensorread.log`, `4d3b4live/pub_live.log`, `4d3b4live/sub_live.log`.

---

## 14. API y Patrones Confirmados para Uso Futuro (Isaac Sim 4.5 — ROS2 + Sensores)

| Método / Patrón | Detalle | Notas 4.5 |
|---|---|---|
| `rclpy` interno | `/isaac-sim/exts/isaacsim.ros2.bridge/humble/rclpy` | trae rclpy + sensor_msgs/std_msgs/geometry_msgs/builtin_interfaces |
| Cargar rclpy en Kit | `sys.path.append(".../humble/rclpy")` **dentro de `on_startup`** | Kit NO hereda PYTHONPATH |
| numpy para subscriber externo | `/isaac-sim/extscache/omni.kit.pip_archive-0.0.0+d02c707b.lx64.cp310/pip_prebundle` | el python pelón de Kit no trae numpy; sensor_msgs lo requiere |
| CLI `ros2` | **NO existe en la imagen Isaac** | usar subscriber Python rclpy, no `ros2 topic` |
| `get_velocities()` | array de 6 (lin+ang) | orden ambiguo → preferir los separados |
| `get_linear_velocities()` / `get_angular_velocities()` | arrays de 3 c/u | sin ambigüedad — usar estos para Twist |
| `IMUSensor.get_current_frame()` | dict | claves: `lin_acc`, `ang_vel`, `orientation` (wxyz) |
| `ContactSensor.get_current_frame()` | dict | claves: `in_contact`, `force`, `time`, `number_of_contacts` |
| Creación de sensor | `prim_path` hijo del link + `frequency=60` + `world.reset_async()` → `.initialize()` | instanciar antes del reset; inicializar después |
| `get_contact_sensor_raw_data` | funciona | **deprecada en 4.5** (DT-4D-006) |
| `isaacsim.sensors.physics` | carga en .kit ligero | arrastra `omni.replicator.core` → warning RTX tolerado (no crash) |
| Frecuencia real de publicación | ~7–8.5 Hz | limitada por el costo del step físico por ciclo, no por DDS |

### Fix DDS cross-container (perfil FastDDS UDP)
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
Montar el XML en ambos contenedores + env `FASTRTPS_DEFAULT_PROFILES_FILE=/fastdds_udp.xml`.

---

## 15. Comando Operativo de Referencia (publisher ROS2 + subscriber externo)

### Publisher (contenedor Isaac, --gpus all)
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

### Subscriber externo (otro contenedor Isaac, sin GPU, proceso separado)
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

**Protocolo de coordinación de 2 terminales:** lanzar el subscriber primero (espera sin morir), luego el publisher; o lanzar el publisher y, al ver `=== G1 AT REST ===`, lanzar el subscriber. Ambos `--network=host`.

---

## 16. Lo que Este Bloque NO Validó

| Elemento | Estado | Pertenece a |
|---|---|---|
| Control del G1 (envío de comandos) | ❌ Solo observación/lectura | 4D-3D+ / 4E |
| Estabilidad física real (robot parado) | ❌ Se cae sin policy (esperado) | 4E (policy plug-and-play) / 5A+ |
| IMU + contactos publicados con tipos ROS2 dedicados | ❌ Solo array crudo (Float32MultiArray) | 4D-3B4B |
| Runtime determinístico conectado (modo observador) | ❌ No conectado | 4D-3C |
| Cierre runtime → G1 (eventos/safety) | ❌ No ejecutado | 4D-3D |
| Etiqueta interpretada DE_PIE/CAYENDO/EN_PISO calibrada | ❌ Umbral mal calibrado (datos OK) | DT-4D-007 |
| Standing policy plug-and-play (existencia + ejecución en T4) | ❌ No investigada | 4E (propuesta) |
| Isaac Lab operativo en T4 | ❌ Riesgo alto documentado | 5A (bloqueada) |
| FastDDS vs CycloneDDS con Unitree SDK2 | ❌ No probado | DT-4A-004 |
| Profiling del grafo GPU (uso real RTX de sensores) | ❌ Solo log observable | DT-4D-005 |

---

## 17. Deuda Técnica al Cierre del Bloque 4D-3

| ID | Deuda | Prioridad | Estado |
|---|---|---|---|
| DT-4A-003 | Cross-container DDS characterization | — | ✅ **RESUELTA** — FastDDS shm no cruza contenedores; fix = transporte UDP forzado |
| DT-4A-004 | FastDDS vs CycloneDDS — divergencia con Unitree SDK2 | Alta | Abierta — para robot físico |
| DT-4D-001 | Causa exacta de `SimulationApp` → `full.streaming` | Media | Congelada — se evita con `kit` directo |
| DT-4D-003 | Viabilidad T4 para render RTX / Isaac Lab / RL | Alta | Abierta — pero matizada: el T4 **toleró** RTX en sensores sin crash (no es muro absoluto) |
| DT-4D-005 | "Sin RTX pesado" es inferencia del log, no profiling GPU | Baja | Abierta — no bloqueante |
| DT-4D-006 | `get_contact_sensor_raw_data` deprecada en 4.5 (funciona) | Baja | Nueva — migrar antes de producción |
| DT-4D-007 | Etiqueta `estado()` de `sub_live.py` mal calibrada (CAYENDO permanente; datos correctos) | Baja | Nueva — fix 3 líneas, no toca publisher/sensores |
| DT-4D-008 | Contactos publicados como `Float32MultiArray` crudo, no tipo ROS2 dedicado | Media | Nueva — formalizar en 4D-3B4B antes del runtime |

*Deudas heredadas no bloqueantes (DT-4C-004/005, DT-4D-002/004) permanecen abiertas sin cambio.*

---

## 18. Anti-Patterns Nuevos Documentados en Esta Sesión

| # | Anti-pattern | Corrección |
|---|---|---|
| 38 | Asumir que un nombre de extensión nuevo dentro de la misma `--ext-folder` no colisiona con el baseline | Verificar qué nombre carga el `.kit`; usar nombre único y confirmar que apunta a la copia, no al baseline viejo |
| 39 | Asumir que `--network=host` basta para discovery DDS cross-container | FastDDS usa shm por defecto, que no cruza contenedores; forzar UDP por XML |
| 40 | Asumir que el python de Kit trae numpy / que Kit hereda PYTHONPATH | Inyectar rutas (rclpy, numpy interno) explícitamente; Kit no hereda el entorno |
| 41 | Declarar "recepción confirmada" tras una sola lectura (foto) | Validar streaming sostenido + trazabilidad temporal (frame_id + timestamp) para descartar caché |
| 42 | Asumir nombres de campos de `get_current_frame()` (lin_acc/in_contact/force) | Verificar en el fuente del sensor antes de leer (no "defensivo a ciegas") |
| 43 | Inventar prim_paths de links del robot | Inventariar los prims reales del G1 (ankle_roll_link, torso_link) antes de crear sensores |
| 44 | Declarar "sin RTX" tras cargar sensores | Es "RTX tolerado" — el plugin RTX se carga y advierte ECC, solo que no crashea |
| 45 | Tras caída de red, asumir que la corrida murió con el SSH | El `docker run` sobrevive; verificar entorno y limpiar contenedores huérfanos (`docker stop`) |

---

## 19. Conocimiento Consolidado del Bloque 4D-3

```
ROS2 en camino ligero:   rclpy interno (/isaac-sim/exts/isaacsim.ros2.bridge/humble/rclpy)
                         cargado con sys.path.append DENTRO de on_startup
Bridge oficial:          DESCARTADO — depende duro de sensors.rtx/hydra.rtx (RTX, sin flag off)
                         NO está ligado a Isaac Lab
CLI ros2:                NO existe en la imagen — usar subscriber Python rclpy
numpy (subscriber):      /isaac-sim/extscache/omni.kit.pip_archive-0.0.0+d02c707b.lx64.cp310/pip_prebundle
DDS cross-container:     FastDDS shm NO cruza contenedores; forzar UDPv4 vía XML + FASTRTPS_DEFAULT_PROFILES_FILE
                         (esto RESOLVIÓ DT-4A-003)
Estado mínimo publicado: /joint_states (JointState) + /g1/base_pose (PoseStamped) + /g1/base_velocity (TwistStamped)
Velocidad de base:       get_linear_velocities() + get_angular_velocities() SEPARADOS (evita ambigüedad de orden)
Sensores físicos:        IMUSensor + ContactSensor de isaacsim.sensors.physics — viables, "RTX tolerado"
IMU frame:               lin_acc / ang_vel / orientation(wxyz)
Contact frame:           in_contact / force / time / number_of_contacts
Links G1:                pies = left/right_ankle_roll_link ; IMU = torso_link
Frecuencia publicación:  ~7-8.5 Hz (limitada por step físico, no por DDS)
Determinismo:            2H bit-idéntico a 600 steps (extiende el de 2F a 60 steps)
Reposo estable G1:       desde ~step 150, Z≈0.1618, W≈0.671, ~1.5-2s tras spawn
```

---

## 20. Reorientación Estratégica al Cierre (clarificación del operador)

Al cierre de sesión, el operador clarificó el objetivo real del proyecto a corto plazo, lo que reordena el roadmap:

**Objetivo real:** validar el **Deterministic Safety Runtime Framework** (Etapa 3C) contra estados del G1 simulado. Para ello se necesita, como mínimo, el robot **parado/estable** (estado "sano" de fábrica) para tener una línea base contra la cual contrastar estados anómalos (perturbaciones). Con el robot permanentemente tumbado NO hay contraste "sano vs malo" → no se puede validar el runtime.

**Restricción declarada:** el operador NO va a entrenar locomoción (no RL). Quiere una **standing/balance policy plug-and-play** (ya entrenada, ejecutable) que mantenga al G1 de pie y lo recupere ante perturbaciones pequeñas.

**Implicación para el roadmap:**
- **Isaac Lab (5A) deja de ser ruta crítica** — solo sería necesario como *entorno de ejecución* de una policy lista, no para entrenar. Esto baja el riesgo del T4 (ejecutar << entrenar).
- Se **propone microfase nueva 4E** (pendiente decisión PM): "Standing policy plug-and-play + validación de estado del runtime" — buscar/verificar la existencia de una standing policy pública para el G1, confirmar que ejecuta en el camino ligero del T4, y usarla como baseline "sano" para validar el runtime con perturbaciones controladas.
- Pregunta abierta a resolver en 4E: ¿existe una standing policy publicada (Unitree u otra) lista para usar, y corre en T4 sin Isaac Lab completo? (No verificado — investigación de diseño pendiente.)

**Nota de matiz sobre DT-4D-003:** esta sesión aportó evidencia *a favor* de revisar el riesgo T4/RTX — el T4 **toleró** el plugin RTX de los sensores sin crashear. No demuestra que Isaac Lab corra, pero debilita la premisa de "RTX en T4 = muro absoluto".

---

## 21. Estado del Roadmap al Cierre de Sesión

```
Etapa 3C   — Deterministic Safety Runtime Framework     ✅ CERRADA
Etapa 4A   — Infrastructure & DDS Characterization      ✅ CERRADA (DT-4A-003 ahora resuelta en 4D-3)
Etapa 4B   — Isaac Headless Bring-up (4.2.0)            ✅ CERRADA
Etapa 4C   — Characterización Física y de Control       ✅ CERRADA
Etapa 4D-1 — Disk / Baseline Preservation Audit         ✅ CERRADA
Etapa 4D-2A–2F — Feasibility 4.5 + carga/stepping       ✅ CERRADA
Etapa 4D-2G — Serie estabilidad 4.5 vs 4.2             ✅ CERRADA — análisis documental
Etapa 4D-2H — Sustained readout 600 steps (+repeat)    ✅ CERRADA — bit-idéntico
Etapa 4D-3A — ROS2 feasibility → mini-bridge propio    ✅ CERRADA — rclpy interno
Etapa 4D-3B1 — G1 + rclpy coexisten                    ✅ CERRADA
Etapa 4D-3B2 — Publisher /joint_states + recepción ext ✅ CERRADA — DT-4A-003 resuelto
Etapa 4D-3B3 — Estado mínimo (joints+pose+velocidad)   ✅ CERRADA
Etapa 4D-3B4 — Probe sensores físicos                  ✅ CERRADA — RTX tolerado
Etapa 4D-3B4A — IMU + contactos leídos (+ live-stream) ✅ CERRADA

Etapa 4D-3B4B — Publicar IMU+contactos (tipos dedicados) 🔲 PENDIENTE
Etapa 4D-3C — Runtime determinístico OBSERVADOR         🔲 PENDIENTE
Etapa 4D-3D — Cierre runtime → G1 (eventos/safety)      🔲 PENDIENTE
Etapa 4E   — Standing policy plug-and-play + validación 🔲 PROPUESTA (pendiente decisión PM)
Etapa 5A   — Isaac Lab Bring-up / G1 Validation         🔒 BLOQUEADA (ya no ruta crítica si 4E plug-and-play)
```

---

## 22. Estado de la VM al Cierre de Sesión

```
Contenedor Isaac     → NO corriendo — verificado limpio (contenedor huérfano de live-stream limpiado con docker stop)
GPU                  → libre (~14912 MiB) — sana tras corte de red e incidente de contenedor huérfano
Imagen Isaac         → isaac-sim:4.5.0 (4.2.0 reconstruible por re-pull NGC)
Imágenes ROS         → g1-ros-phase-a + g1-ros-phase-b intactas
Baseline 4D-2        → ~/g1ext/isaacsim.g1.runtime/ intacto
Artefactos nuevos    → ~/runs/4d2h, 4d3a, 4d3b1, 4d3b1step, 4d3b2, 4d3b3, 4d3b4probe, 4d3b4a, 4d3b4live
Backup 4C            → ~/backup_4c/ (44 archivos) intacto
tmux                 → sesiones históricas: 4d2h, 4d3a, g1_4d (algunas viejas, no estorban)
```

**Incidente externo de la sesión:** caída de red de la VM durante la prueba 4D-3B4A-live (evento externo). El `docker run` del publisher sobrevivió a la desconexión SSH y quedó huérfano; se detectó al verificar entorno y se limpió con `docker stop`. Lección incorporada al protocolo (Anti-pattern 45).

---

## LLAVE DEL SIGUIENTE CHAT

```
4D-3 POSITIVO — El G1 es totalmente OBSERVABLE por ROS2 real (joints + pose + velocidad + IMU + contactos)
hacia procesos externos, cross-container, sin RTX pesado, en T4. Streaming en vivo validado (trazabilidad 1:1).
NO declarar "control" (todo es lectura) ni "embodiment estable" (se cae sin policy).

LOGROS CLAVE:
  - Mini-bridge ROS2 propio (rclpy interno) — bridge oficial descartado (RTX duro)
  - DT-4A-003 RESUELTO — fix DDS cross-container = UDP forzado por XML
  - Estado mínimo + sensores físicos (IMU/contactos) leídos y publicados
  - 2H sustained readout 600 steps bit-idéntico

CAMINO ROS2 CONFIRMADO:
  rclpy interno = /isaac-sim/exts/isaacsim.ros2.bridge/humble/rclpy (sys.path.append en on_startup)
  numpy subscriber = .../omni.kit.pip_archive-.../pip_prebundle
  DDS cross-container = fastdds_udp.xml + FASTRTPS_DEFAULT_PROFILES_FILE (ambos contenedores)
  CLI ros2 NO existe → subscriber Python rclpy
  velocidad base = get_linear_velocities() + get_angular_velocities() (separados)
  sensores = isaacsim.sensors.physics (RTX tolerado, no crash)

REORIENTACIÓN ESTRATÉGICA (clarificada por el operador):
  Objetivo real = VALIDAR el Deterministic Runtime Framework contra estados del G1.
  Necesita robot PARADO (estado sano de fábrica) vía STANDING POLICY PLUG-AND-PLAY (NO entrenar RL).
  Isaac Lab (5A) deja de ser ruta crítica. Se propone microfase 4E (pendiente decisión PM).

NO HACER en el próximo chat:
  - Reabrir el bridge oficial (descartado — RTX duro)
  - Asumir DDS cross-container sin el XML UDP (DT-4A-003 resuelto así)
  - Editar baselines validados (trabajar en ~/runs/<fase>/ con copia + backup)
  - Asumir que el operador quiere entrenar (quiere plug-and-play)
  - Declarar "control" o "estable" sin evidencia

SIGUIENTE PASO (a decidir con PM):
  Opción A — 4D-3B4B: publicar IMU+contactos con tipos ROS2 dedicados (calcado de 3B3)
  Opción B — 4D-3C: conectar el runtime observador a la telemetría (leer + evaluar estado, sin control)
  Opción C — 4E (propuesta): investigar standing policy plug-and-play para el baseline "sano"

DEUDAS NUEVAS: DT-4D-006 (raw_data deprecada), DT-4D-007 (etiqueta estado() mal calibrada),
DT-4D-008 (contactos como array crudo, formalizar). DT-4A-003 RESUELTA.

Documentos llave para el siguiente chat:
  - Este informe (informe_etapa_4D3_2026-06-08.md)
  - tesis_etapas_proyecto_g1_runtime_architecture (actualizada a v12)
  - chat_bootstrap_protocol (actualizado a v9)
```

---

*G1 ROS2 Pipeline — Informe Bloque 4D-3 (ROS2 Feasibility + Observabilidad Sensorial del G1 en T4)*
*Generado: 2026-06-08*
*PM: ChatGPT | Implementador/Auditor: Claude | Operador: Jorge Padilla*
*Repositorio: github.com/jorgerpg1213-mitech/g1-ros2-pipeline*
