# 4E-P4 — Physical Baseline & Observer Transition Audit

Fecha: 2026-06-15  
Robot: Unitree G1 USD en Isaac Sim 4.5  
Contexto: auditoría previa a control/PD para validar que el modelo físico, contactos, baseline sano y observer reciben telemetría coherente.

## Motivo de la auditoría

Durante P3/P3L se intentó avanzar hacia control por torque/PD, pero aparecieron resultados incoherentes: el robot arrancaba colapsado, flotaba con `z=0.8`, o quedaba sin soporte cuando se anulaba stiffness. Se decidió detener tuning de control y abrir auditoría física previa.

## P4A — Physics / Articulation Audit

Objetivo: revisar joints, drives, rigid bodies, masas, CoM y colliders.

Hallazgos:
- Joints principales de piernas existen y están conectados.
- `hip_pitch`, `knee`, `ankle_pitch` usan eje Y.
- `ankle_roll` usa eje X.
- Drives default: `stiffness=10000000`, `damping=0`, `targetPos=0`.
- Dos links con CoM inválido:
  - `/World/G1/pelvis_contour_link`
  - `/World/G1/imu_link`
- Spawn default no usable: `base_z≈0.100`.

Conclusión: articulación principal usable, pero el modelo no queda declarado “limpio” por CoM inválido y spawn default bajo.

## P4B — Mass / Collider / Foot Audit

Objetivo: verificar masa total, colliders y soporte físico en pies.

Hallazgos:
- Masa total aproximada: `32.238927 kg`.
- Rigid bodies: 44.
- Colliders: 40.
- Bodies sin collider:
  - `pelvis_contour_link`
  - `imu_link`
  - `left_zero_link`
  - `right_zero_link`
- Pies/tobillos sí tienen colliders:
  - `left_ankle_roll_link/collisions`
  - `right_ankle_roll_link/collisions`
- Sensores de contacto están ubicados en:
  - `left_ankle_roll_link/contact_left`
  - `right_ankle_roll_link/contact_right`

Conclusión: los pies sí tienen colisión y sensores bien ubicados. El problema no era ausencia de colliders en pies.

## P4C — Support Geometry / Contact Audit

Objetivo: validar P2 con `z=0.8`.

Pose P2:
- `hip_pitch=-0.10`
- `knee=+0.30`
- `ankle_pitch=-0.20`

Resultado:
- Base: `z≈0.792`, `W≈1`.
- Joints aplicados correctamente.
- Pero pies flotaban:
  - `left_ankle_roll_link z≈0.094`
  - `right_ankle_roll_link z≈0.094`
- Contactos:
  - `left=False`
  - `right=False`
  - fuerza 0.

Conclusión: P2 con `z=0.8` no es baseline físico; deja pies flotando.

## P4D — Height / Contact Calibration

Objetivo: buscar altura `base_z` para contacto bilateral real.

Alturas probadas:
- `z_cmd=0.800`: sin contacto.
- `z_cmd=0.760`: contacto detectado pero fuerza 0.
- `z_cmd=0.720`: contacto bilateral con fuerza real.
- alturas menores: rebote/inestabilidad/pérdida de contacto.

Resultado ganador:
- `z_cmd=0.720`
- `base_z≈0.732`
- `W≈0.999974`
- `left=True`, fuerza ≈120.69
- `right=True`, fuerza ≈320.77

Conclusión: `P2 + z_cmd=0.720` es el baseline geométrico de contacto inicial.

## P4E — Zero-Control Contact Persistence

Objetivo: verificar si `P2 + z_cmd=0.720` mantiene contacto sin PD/custom control.

Resultado:
- Step 000: L/R true.
- Step 250: L/R true.
- `base_z≈0.732` estable.
- `W≈0.9997`.
- error articular bajo.
- Sin `apply_action`, sin `set_gains`, sin torque custom.

Conclusión: `P2 + z_cmd=0.720` es baseline sano pasivo. El robot no necesita PD para permanecer coherente en esa ventana si se inicia correctamente.

## P4G — Healthy-to-Fall Observer Transition

Objetivo: probar transición:
1. baseline sano;
2. caída programada;
3. observer debe ver transición.

Diseño:
- Terminal A: Isaac combo publica baseline sano.
- Terminal B: `cross_consistency_observer` escucha IMU, joints y contactos.
- Trigger: en `it=450`, teleport + tilt 45° + reset de velocidades.
- Orchestrator/recovery no se usaron.

Resultado Isaac:
- Antes de trigger: `z≈0.732`, `W≈0.97–1.0`, L/R true.
- Trigger `it=450`: `z≈1.097`, contactos false.
- Después: `z≈0.18`, `W≈0.714`, left false, right true.

Resultado observer:
- Antes: IMU sana y contactos L/R true.
- Trigger: quaternion cambia a `w≈0.924`, `x≈0.383`, contactos false.
- Después: `w≈0.714`, left false, right true.

Conclusión:
- PASS en telemetría: el observer recibe claramente sano → caída.
- PENDING en alarma: no emitió `SafetyEvent` porque el observer todavía opera como skeleton/snapshot:
  `Lógica real de coherencia TBD — pending SDK G1`.

## Resolución final de la sesión

P4 cerró la parte física previa:

- El modelo no debe arrancar desde default `z≈0.10`.
- `z=0.8` no sirve porque deja pies flotando.
- `P2 + z_cmd=0.720` es baseline sano pasivo validado.
- La transición sano→caída se observa correctamente por el observer.
- Lo pendiente no es otra simulación: falta implementar regla de decisión en `cross_consistency_observer`.

## Siguiente microfase recomendada

P4H — Observer Decision Rule

Implementar regla mínima:

- sano: `W≈1` y contactos L/R true;
- caída/anomalía: tilt alto o `W` bajo + pérdida bilateral/unilateral persistente de contacto;
- salida esperada: `g1_msgs/SafetyEvent`.

Criterio de éxito:
- antes del trigger P4G: no `SafetyEvent`;
- después del trigger P4G: sí `SafetyEvent`.

