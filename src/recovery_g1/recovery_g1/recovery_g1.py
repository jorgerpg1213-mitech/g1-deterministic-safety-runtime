"""
recovery_g1.py
G1 ROS2 Pipeline — Recovery Node Skeleton

Responsabilidad (RECOVERY_MODEL_G1.md):
  - Consumir SafetyEvents y SystemState para evaluar RecoveryActions
  - Publicar RecoveryEvent en /recovery_events
  - Publicar heartbeat propio en /diagnostics

Estado: SKELETON — Capa 4
  - Suscribe a /safety_events y /system_state
  - Registra compound state actual
  - Lógica real de recovery: TBD — pending SDK G1
  - Este skeleton publica RecoveryEvent mock controlado
  - Retry counter por target: implementado — lógica de escalation TBD

Precondición universal (RECOVERY_MODEL_G1.md Sección 2.2):
  NO ejecutar RecoveryAction si compound state es STABILITY_RISK o
  FAULT_CRITICAL con R3 o superior activo.
  Esta precondición está implementada como guard en el skeleton.

NO hace:
  - Modificar /system_state (eso es safety_orchestrator_g1)
  - Ejecutar transiciones de safety (eso es safety_orchestrator_g1)
  - Reiniciar nodos reales (TBD — pending SDK G1)
  - Recovery destructivo de cualquier tipo
"""

import uuid
from collections import defaultdict

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy, HistoryPolicy

from diagnostic_msgs.msg import DiagnosticArray, DiagnosticStatus, KeyValue
from g1_msgs.msg import SafetyEvent, SystemState, RecoveryEvent

# ---------------------------------------------------------------------------
# QoS profiles — RECOVERY_MODEL_G1.md + ADR-002
# ---------------------------------------------------------------------------

QOS_SAFETY_EVENTS = QoSProfile(
    reliability=ReliabilityPolicy.RELIABLE,
    durability=DurabilityPolicy.VOLATILE,
    history=HistoryPolicy.KEEP_LAST,
    depth=50,
)

QOS_SYSTEM_STATE = QoSProfile(
    reliability=ReliabilityPolicy.RELIABLE,
    durability=DurabilityPolicy.TRANSIENT_LOCAL,
    history=HistoryPolicy.KEEP_LAST,
    depth=1,
)

QOS_RECOVERY_EVENTS = QoSProfile(
    reliability=ReliabilityPolicy.RELIABLE,
    durability=DurabilityPolicy.VOLATILE,
    history=HistoryPolicy.KEEP_LAST,
    depth=50,
)

QOS_DIAGNOSTICS = QoSProfile(
    reliability=ReliabilityPolicy.BEST_EFFORT,
    durability=DurabilityPolicy.VOLATILE,
    history=HistoryPolicy.KEEP_LAST,
    depth=10,
)

# ---------------------------------------------------------------------------
# Constantes — TBD hasta SDK G1
# ---------------------------------------------------------------------------

RECOVERY_HEARTBEAT_HZ = 1.0    # TBD — RESILIENCE_MODEL_G1.md Sección 6.2
MAX_AUTO_RETRIES = 3            # TBD — RECOVERY_MODEL_G1.md Sección 5.2
HARDWARE_ID = 'g1_ros2_pipeline'

# Compound states que bloquean recovery — precondición universal
# RECOVERY_MODEL_G1.md Sección 2.2
BLOCKED_RISK_LEVELS = {'STABILITY_RISK', 'FAULT_CRITICAL'}
BLOCKED_RESTRICTION_LEVELS = {'R3', 'R4-halt', 'R4-sit', 'R5'}


class RecoveryG1(Node):
    """
    Recovery node skeleton para G1 ROS2 Pipeline.

    Skeleton Capa 4:
      - Suscribe a /safety_events y /system_state
      - Mantiene compound state actual (read-only — owner es orchestrator)
      - Precondición universal de recovery implementada como guard
      - Retry counter por target en memoria
      - Publica RecoveryEvent mock en /recovery_events
      - Publica heartbeat en /diagnostics
      - Lógica real de RecoveryActions: TBD pending SDK G1
    """

    def __init__(self):
        super().__init__('recovery_g1')

        # Compound state actual — read-only, recibido desde /system_state
        # Owner exclusivo: safety_orchestrator_g1
        self._current_risk_level = 'SAFE'
        self._current_restriction_level = 'NONE'

        # Retry counter por target — reseteado cuando Resilience State vuelve a NOMINAL
        # RECOVERY_MODEL_G1.md Sección 5.4
        self._retry_counters = defaultdict(int)

        # Publishers
        self._pub_recovery_events = self.create_publisher(
            RecoveryEvent,
            '/recovery_events',
            QOS_RECOVERY_EVENTS,
        )

        self._pub_diagnostics = self.create_publisher(
            DiagnosticArray,
            '/diagnostics',
            QOS_DIAGNOSTICS,
        )

        # Subscribers
        self._sub_system_state = self.create_subscription(
            SystemState,
            '/system_state',
            self._on_system_state,
            QOS_SYSTEM_STATE,
        )

        self._sub_safety_events = self.create_subscription(
            SafetyEvent,
            '/safety_events',
            self._on_safety_event,
            QOS_SAFETY_EVENTS,
        )

        # Timer — heartbeat
        self._heartbeat_timer = self.create_timer(
            1.0 / RECOVERY_HEARTBEAT_HZ,
            self._publish_heartbeat,
        )

        self.get_logger().info(
            'recovery_g1 skeleton iniciado. '
            'Suscrito a /system_state y /safety_events. '
            'Recovery logic TBD — pending SDK G1.'
        )

    # -----------------------------------------------------------------------
    # Callbacks — ingest only
    # -----------------------------------------------------------------------

    def _on_system_state(self, msg):
        """
        Ingest /system_state — actualiza compound state local (read-only).
        recovery_g1 NO modifica /system_state — solo lo observa.
        """
        self._current_risk_level = msg.risk_level
        self._current_restriction_level = msg.restriction_level

        # Reset retry counters si sistema vuelve a NOMINAL
        # RECOVERY_MODEL_G1.md Sección 5.4
        if msg.risk_level == 'SAFE' and msg.restriction_level == 'NONE':
            if self._retry_counters:
                self.get_logger().info(
                    '[RECOVERY] Compound state NOMINAL — reseteando retry counters.'
                )
                self._retry_counters.clear()

    def _on_safety_event(self, msg):
        """
        Ingest /safety_events — evalúa si corresponde iniciar recovery.
        SKELETON: solo verifica precondición universal y publica mock event.
        Lógica real de RecoveryAction selection: TBD.
        """
        # Solo procesar eventos de condición detectada por watchdog/observer
        if msg.source not in ('watchdog_g1', 'cross_consistency_observer'):
            return

        # Precondición universal — RECOVERY_MODEL_G1.md Sección 2.2
        if not self._recovery_allowed():
            self.get_logger().warn(
                f'[RECOVERY] Recovery bloqueado — compound state: '
                f'({self._current_risk_level}, {self._current_restriction_level}). '
                'Precondición universal activa.'
            )
            self._publish_recovery_event(
                action_name='wait_for_primary_restore',
                recovery_type='REC-AUTO',
                target=msg.target,
                result='FAILED',
                notes='Precondición universal activa — compound state bloquea recovery.',
            )
            return

        # SKELETON: publicar mock recovery event
        # En runtime real: seleccionar RecoveryAction según Resilience State,
        # evaluar retry counter, ejecutar o escalar.
        self._publish_mock_recovery(target=msg.target)

    # -----------------------------------------------------------------------
    # Precondición universal
    # -----------------------------------------------------------------------

    def _recovery_allowed(self):
        """
        Verifica precondición universal de recovery.
        RECOVERY_MODEL_G1.md Sección 2.2:
        NO ejecutar si compound state es STABILITY_RISK/FAULT_CRITICAL con R3+.
        """
        risk_blocked = self._current_risk_level in BLOCKED_RISK_LEVELS
        restriction_blocked = self._current_restriction_level in BLOCKED_RESTRICTION_LEVELS
        return not (risk_blocked and restriction_blocked)

    # -----------------------------------------------------------------------
    # Mock recovery — solo skeleton
    # -----------------------------------------------------------------------

    def _publish_mock_recovery(self, target):
        """
        Publica RecoveryEvent mock para validar pipeline.
        SKELETON ONLY — reemplazar con RecoveryAction real.
        Incrementa retry counter por target.
        """
        self._retry_counters[target] += 1
        attempt = self._retry_counters[target]

        # Escalation guard — RECOVERY_MODEL_G1.md Sección 5.3
        if attempt > MAX_AUTO_RETRIES:
            self.get_logger().warn(
                f'[RECOVERY] MAX_AUTO_RETRIES alcanzado para target: {target}. '
                f'Intentos: {attempt}. Escalando.'
            )
            self._publish_recovery_event(
                action_name='request_operator_intervention',
                recovery_type='REC-MANUAL',
                target=target,
                result='ESCALATED',
                notes=f'SKELETON — MAX_AUTO_RETRIES ({MAX_AUTO_RETRIES}) alcanzado.',
            )
            return

        self._publish_recovery_event(
            action_name='wait_for_primary_restore',
            recovery_type='REC-AUTO',
            target=target,
            result='SUCCESS',
            notes=f'SKELETON MOCK — intento {attempt}/{MAX_AUTO_RETRIES}. '
                  'Lógica real TBD pending SDK G1.',
        )

    # -----------------------------------------------------------------------
    # Publisher helpers
    # -----------------------------------------------------------------------

    def _publish_recovery_event(
        self, action_name, recovery_type, target, result, notes
    ):
        msg = RecoveryEvent()
        msg.event_id = str(uuid.uuid4())
        msg.event_type = (
            'RECOVERY_SUCCESS' if result == 'SUCCESS'
            else 'ESCALATION' if result == 'ESCALATED'
            else 'RECOVERY_FAILED'
        )
        msg.action_name = action_name
        msg.recovery_type = recovery_type
        msg.target = target
        msg.compound_state_at_trigger = (
            f'({self._current_risk_level}, {self._current_restriction_level})'
        )
        msg.attempt_number = self._retry_counters[target]
        msg.result = result
        msg.timestamp = self.get_clock().now().to_msg()
        msg.notes = notes

        self._pub_recovery_events.publish(msg)
        self.get_logger().info(
            f'[RECOVERY] RecoveryEvent publicado — action: {action_name} '
            f'target: {target} result: {result} attempt: {msg.attempt_number}'
        )

    def _publish_heartbeat(self):
        """Publica DiagnosticArray con estado propio del recovery node."""
        now = self.get_clock().now().to_msg()

        status = DiagnosticStatus()
        status.level = DiagnosticStatus.OK
        status.name = 'recovery_g1'
        status.message = (
            f'SKELETON — compound state observado: '
            f'({self._current_risk_level}, {self._current_restriction_level})'
        )
        status.hardware_id = HARDWARE_ID
        status.values = [
            KeyValue(key='state', value='SKELETON'),
            KeyValue(key='risk_level', value=self._current_risk_level),
            KeyValue(key='restriction_level', value=self._current_restriction_level),
            KeyValue(key='active_retry_targets', value=str(len(self._retry_counters))),
            KeyValue(key='sdk_required', value='true'),
        ]

        msg = DiagnosticArray()
        msg.header.stamp = now
        msg.status = [status]
        self._pub_diagnostics.publish(msg)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main(args=None):
    rclpy.init(args=args)
    node = RecoveryG1()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
