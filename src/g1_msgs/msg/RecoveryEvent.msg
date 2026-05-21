# RecoveryEvent.msg
# G1 ROS2 Pipeline — g1_msgs
# Evento de recovery — publicado por recovery_g1 en /recovery_events
# QoS: Reliable, depth 50

# Identificador único
string event_id

# Tipo de evento
# RECOVERY_STARTED | RECOVERY_SUCCESS | RECOVERY_FAILED |
# ESCALATION | REINIT | RETRY
string event_type

# RecoveryAction ejecutada (RECOVERY_MODEL_G1.md Sección 4.2)
# restart_noncritical_node | restart_critical_node | request_operator_intervention |
# reinitialize_system | restore_nav_stack | restore_localization | wait_for_primary_restore
string action_name

# Tipo de recovery
# REC-AUTO | REC-ASSISTED | REC-MANUAL | REC-REINIT
string recovery_type

# Nodo o topic afectado
string target

# Compound state en el momento del trigger
string compound_state_at_trigger

# Número de intento actual (1-based)
int32 attempt_number

# Resultado
# SUCCESS | FAILED | TIMEOUT | ESCALATED
string result

# Timestamp
builtin_interfaces/Time timestamp

# Notas para debugging y auditoría
string notes
