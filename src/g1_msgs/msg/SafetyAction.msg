# SafetyAction.msg
# G1 ROS2 Pipeline — g1_msgs
# Acción de seguridad resultante de una transición — publicado por safety_orchestrator_g1
# QoS: Reliable, depth 10

# Primitiva del Vocabulario Operacional (SAFETY_MODEL_G1.md Sección 8)
# velocity_clamp | gait_slowdown | freeze_navigation | freeze_upper_body |
# locomotion_hold | stabilization_mode | controlled_halt | emergency_sit | torque_release
string action_name

# Autoridad de ejecución requerida
# AUTONOMOUS | POLICY_GATED | HUMAN_REQUIRED
string execution_authority

# ID de la transición que originó esta acción
string transition_id

# Timestamp
builtin_interfaces/Time timestamp
