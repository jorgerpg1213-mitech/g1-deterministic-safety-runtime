# SafetyEvent.msg
# G1 ROS2 Pipeline — g1_msgs
# Evento de seguridad — publicado por watchdog_g1, cross_consistency_observer,
# y safety_orchestrator_g1 en /safety_events
# QoS: Reliable, depth 50

# Identificador único del evento
string event_id

# Tipo de evento
# CONDITION_DETECTED | TRANSITION_EXECUTED | PREEMPTED |
# ARBITRATION_PENDING | ARBITRATION_RESOLVED |
# SCHEDULED | REJECTED
string event_type

# Nodo que origina el evento
# watchdog_g1 | cross_consistency_observer | safety_orchestrator_g1
string source

# Nivel de autoridad de la fuente
# PRIMARY | SECONDARY | ADVISORY
string source_authority

# Estado operacional de efectividad de autoridad (SAFETY_MODEL_G1.md Sección 7.5)
# EFFECTIVE | DEGRADED_EFFECTIVE | CONTESTED | UNRELIABLE | INEFFECTIVE
string authority_effectiveness

# Nodo, topic o dominio afectado por este evento
string target

# Risk Level asociado
# SAFE | CAUTION | DANGER | STABILITY_RISK | FAULT_CRITICAL
string risk_level

# Restriction Level asociado
# NONE | R1 | R2 | R3 | R4-halt | R4-sit | R5
string restriction_level

# ID de transición del SAFETY_MODEL_G1 — vacío si no aplica
string transition_id

# Prioridad de transición
# CRITICAL_INTERRUPT | COMMIT_TERMINAL | NORMAL | RECOVERY
string transition_priority

# Confianza de ejecución
# VERIFIED | BEST_EFFORT
string execution_confidence

# Timestamp ROS
builtin_interfaces/Time timestamp

# Notas libres para debugging y auditoría
string notes
