"""
cross_consistency_observer.py
G1 ROS2 Pipeline — Cross-Consistency Observer Skeleton

Responsabilidad (ADR-003):
  - Detectar incoherencia entre fuentes de autoridad PRIMARY simultáneamente activas
  - Publicar SafetyEvent en /safety_events cuando se detecta incoherencia
  - Publicar heartbeat propio en /diagnostics

Estado: SKELETON — Capa 4
  - Suscribe a /imu y /joint_states (topics PRIMARY)
  - Lógica real de coherencia: TBD — pending SDK G1 + thresholds reales
  - Este skeleton verifica que los topics llegan y publica mock event controlado
  - Anti-flood por par de fuentes: implementado via rate limiting

NO hace:
  - Decidir transiciones (eso es safety_orchestrator_g1)
  - Ejecutar acciones de seguridad (eso es safety_orchestrator_g1)
  - Modificar /system_state (eso es safety_orchestrator_g1)
  - Detectar timeouts de topics individuales (eso es watchdog_g1)

Pares monitoreados (ADR-003 Sección 3):
  - /imu <-> /joint_states       — ACTIVO skeleton
  - /imu <-> /foot_contact       — TBD pending SDK G1
  - /joint_states <-> /foot_contact — TBD pending SDK G1
"""

import uuid

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy, HistoryPolicy

from diagnostic_msgs.msg import DiagnosticArray, DiagnosticStatus, KeyValue
from sensor_msgs.msg import Imu, JointState
from g1_msgs.msg import SafetyEvent

# ---------------------------------------------------------------------------
# QoS profiles — ADR-003 + RESILIENCE_MODEL_G1.md
# ---------------------------------------------------------------------------

QOS_SAFETY_EVENTS = QoSProfile(
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

QOS_SENSOR = QoSProfile(
    reliability=ReliabilityPolicy.BEST_EFFORT,
    durability=DurabilityPolicy.VOLATILE,
    history=HistoryPolicy.KEEP_LAST,
    depth=10,
)

# ---------------------------------------------------------------------------
# Constantes — TBD hasta SDK G1
# ---------------------------------------------------------------------------

OBSERVER_HEARTBEAT_HZ = 1.0       # TBD — RESILIENCE_MODEL_G1.md Sección 6.2
OBSERVER_MAX_PUBLISH_HZ = 1.0     # Anti-flood — ADR-003 Sección 6
MOCK_EVENT_INTERVAL_S = 15.0      # Solo skeleton — mock event controlado
HARDWARE_ID = 'g1_ros2_pipeline'


class CrossConsistencyObserver(Node):
    """
    Cross-consistency observer skeleton para G1 ROS2 Pipeline.

    Skeleton Capa 4:
      - Suscribe a /imu y /joint_states
      - Registra timestamps de último mensaje por topic
      - Publica heartbeat en /diagnostics
      - Publica SafetyEvent mock controlado
      - Lógica real de coherencia: TBD pending SDK G1
    """

    def __init__(self):
        super().__init__('cross_consistency_observer')

        # Estado interno — timestamps de última recepción por topic
        # Usado por lógica futura de coherencia — no por skeleton mock
        self._last_imu_stamp = None
        self._last_joint_states_stamp = None

        # Anti-flood — timestamp de último evento publicado por par
        self._last_event_published = {}

        # Publishers
        self._pub_safety_events = self.create_publisher(
            SafetyEvent,
            '/safety_events',
            QOS_SAFETY_EVENTS,
        )

        self._pub_diagnostics = self.create_publisher(
            DiagnosticArray,
            '/diagnostics',
            QOS_DIAGNOSTICS,
        )

        # Subscribers — fuentes PRIMARY (ADR-003 Sección 3)
        # /imu — PRIMARY: balance y postura
        self._sub_imu = self.create_subscription(
            Imu,
            '/imu',
            self._on_imu,
            QOS_SENSOR,
        )

        # /joint_states — PRIMARY: integridad articular
        self._sub_joint_states = self.create_subscription(
            JointState,
            '/joint_states',
            self._on_joint_states,
            QOS_SENSOR,
        )

        # Timer — heartbeat propio
        self._heartbeat_timer = self.create_timer(
            1.0 / OBSERVER_HEARTBEAT_HZ,
            self._publish_heartbeat,
        )

        # Timer — mock event controlado (solo skeleton)
        self._mock_event_timer = self.create_timer(
            MOCK_EVENT_INTERVAL_S,
            self._publish_mock_safety_event,
        )

        self.get_logger().info(
            'cross_consistency_observer skeleton iniciado. '
            'Suscrito a /imu y /joint_states. '
            'Lógica real de coherencia TBD — pending SDK G1.'
        )

    # -----------------------------------------------------------------------
    # Callbacks de sensores — solo ingest, sin lógica pesada
    # -----------------------------------------------------------------------

    def _on_imu(self, msg):
        """Ingest /imu — registra timestamp. Sin lógica de coherencia todavía."""
        self._last_imu_stamp = self.get_clock().now()

    def _on_joint_states(self, msg):
        """Ingest /joint_states — registra timestamp. Sin lógica de coherencia todavía."""
        self._last_joint_states_stamp = self.get_clock().now()

    # -----------------------------------------------------------------------
    # Heartbeat — /diagnostics
    # -----------------------------------------------------------------------

    def _publish_heartbeat(self):
        """
        Publica DiagnosticArray con estado propio del observer.
        Detectable externamente via ausencia de heartbeat.
        Ver ADR-003 Sección 4 — observer publica /diagnostics propio.
        """
        now = self.get_clock().now().to_msg()

        imu_seen = 'YES' if self._last_imu_stamp is not None else 'NO'
        joint_seen = 'YES' if self._last_joint_states_stamp is not None else 'NO'

        status = DiagnosticStatus()
        status.level = DiagnosticStatus.OK
        status.name = 'cross_consistency_observer'
        status.message = 'SKELETON — heartbeat activo. Coherencia real TBD.'
        status.hardware_id = HARDWARE_ID
        status.values = [
            KeyValue(key='state', value='SKELETON'),
            KeyValue(key='imu_seen', value=imu_seen),
            KeyValue(key='joint_states_seen', value=joint_seen),
            KeyValue(key='sdk_required', value='true'),
        ]

        msg = DiagnosticArray()
        msg.header.stamp = now
        msg.status = [status]

        self._pub_diagnostics.publish(msg)

    # -----------------------------------------------------------------------
    # Mock SafetyEvent — solo skeleton
    # -----------------------------------------------------------------------

    def _publish_mock_safety_event(self):
        """
        Publica SafetyEvent mock para validar pipeline.
        SKELETON ONLY — reemplazar con detección real de incoherencia.
        Anti-flood aplicado por par: imu_joint_states.
        """
        pair_key = 'imu_joint_states'
        now = self.get_clock().now()

        # Anti-flood — no publicar más de OBSERVER_MAX_PUBLISH_HZ por par
        last = self._last_event_published.get(pair_key)
        if last is not None:
            elapsed = (now - last).nanoseconds / 1e9
            if elapsed < (1.0 / OBSERVER_MAX_PUBLISH_HZ):
                return

        self._last_event_published[pair_key] = now

        msg = SafetyEvent()
        msg.event_id = str(uuid.uuid4())
        msg.event_type = 'CONDITION_DETECTED'
        msg.source = 'cross_consistency_observer'
        msg.source_authority = 'SECONDARY'
        msg.authority_effectiveness = 'EFFECTIVE'
        msg.target = 'imu_joint_states_pair'
        msg.risk_level = 'SAFE'
        msg.restriction_level = 'NONE'
        msg.transition_id = ''
        msg.transition_priority = 'NORMAL'
        msg.execution_confidence = 'VERIFIED'
        msg.timestamp = now.to_msg()
        msg.notes = (
            'SKELETON MOCK EVENT — cross_consistency_observer Capa 4. '
            'Coherencia real TBD pending SDK G1 + thresholds.'
        )

        self._pub_safety_events.publish(msg)
        self.get_logger().info(
            f'[MOCK] SafetyEvent publicado — par: {pair_key} '
            f'event_id: {msg.event_id}'
        )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main(args=None):
    rclpy.init(args=args)
    node = CrossConsistencyObserver()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
