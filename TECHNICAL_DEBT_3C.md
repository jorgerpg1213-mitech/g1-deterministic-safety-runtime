# Technical Debt Register — Post 3C
## G1 ROS2 Pipeline — 2026-05-24

### Deuda 1 — _state_lock no garantiza thread-safety formal
Thread 2 muta CompoundState sin adquirir _state_lock. Thread 3 sí lo adquiere para leer. Funciona hoy por GIL. Solución futura: immutable snapshot swap pattern.

### Deuda 2 — recovery_g1 no usa process groups
subprocess.Popen sin os.setsid() — riesgo de orphan processes si nodo lanzado tiene hijos. Solución futura: os.setsid() + killpg.

### Deuda 3 — _execute_transition() requiere ActionExecutor antes de SDK
Concentra mutation + logging + publishing. Manejable hoy. Antes de integrar locomotion semantics del SDK: separar en ActionExecutor.

### Deuda 4 — wait_for_primary_restore mezcla poller y reactor
Único método en recovery_g1 con semántica de polling. Asimetría arquitectónica. Refactor post-SDK.

### Deuda 5 — launch_testing real pendiente
Unit tests validan lógica pura. Behavior bajo carga DDS real y timing físico pendiente SDK G1.

## Condición de cierre de cada deuda
Todas: SDK Unitree G1 disponible + hardware real.
