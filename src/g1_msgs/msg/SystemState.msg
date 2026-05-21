# SystemState.msg
# G1 ROS2 Pipeline — g1_msgs
# Estado compuesto del sistema — publicado por safety_orchestrator_g1
# QoS: Transient Local, depth 1 — garantiza que nuevos subscriptores reciben último estado

# Risk Level actual
# SAFE | CAUTION | DANGER | STABILITY_RISK | FAULT_CRITICAL
string risk_level

# Restriction Level actual
# NONE | R1 | R2 | R3 | R4-halt | R4-sit | R5
string restriction_level

# ID de la última transición ejecutada
string last_transition_id

# Confianza de ejecución de la última transición
# VERIFIED | BEST_EFFORT
string execution_confidence

# Timestamp de la última transición
builtin_interfaces/Time timestamp

# True si T8 arbitration está activo y sin resolver
bool arbitration_pending

# True si R5 post-commit — torque_release irreversible comprometido
bool r5_committed
