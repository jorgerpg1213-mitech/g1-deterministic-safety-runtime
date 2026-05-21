"""
watchdog_g1.py
G1 ROS2 Pipeline — Watchdog Node Skeleton

Responsabilidad (RESILIENCE_MODEL_G1.md Sección 4.1):
  - Detectar ausencia/timeout de topics críticos
  - Detectar ausencia de heartbeat de nodos críticos
  - Publicar SafetyEvent en /safety_events
  - Publicar heartbeat propio en /diagnostics

Estado: SKELETON — Capa 4
  - Lógica real de thresholds: TBD — pending SDK G1
  - Topics monitoreados reales: TBD — pending SDK G1
  - Este skeleton publica heartbeat y un SafetyEvent mock controlado
  - Zero lógica de arbitration, recovery, ni SDK

NO toca:
  - /system_state (eso es safety_orchestrator_g1)
  - /safety_actions (eso es safety_orchestrator_g1)
  - Lógica de recovery (eso es recovery_g1)
"""

import uuid

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy, HistoryPolicy

from diagnostic_msgs.msg import DiagnosticArray, DiagnosticStatus, KeyValue
from g1_msgs.msg import SafetyEvent


# ---------------------------------------------------------------------------
# QoS profiles — definidos por ADR-002 y RESILIENCE_MODEL_G1.md
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

# ---------------------------------------------------------------------------
# Constantes — valores provisionales, todos TBD hasta SDK G1
# ---------------------------------------------------------------------------

WATCHDOG_HEARTBEAT_HZ = 1.0       # TBD — RESILIENCE_MODEL_G1.md Sección 6.2
MOCK_EVENT_INTERVAL_S = 10.0      # Solo para skeleton — emite SafetyEvent mock cada N segundos
HARDWARE_ID = 'g1_ros2_pipeline'  # Constante para todos los nodos del sistema


class WatchdogG1(Node):
    """
    Watchdog skeleton para G1 ROS2 Pipeline.

    Skeleton Capa 4:
      - Publica heartbeat en /diagnostics
      - Publica SafetyEvent mock en /safety_events cada MOCK_EVENT_INTERVAL_S
      - Lógica real de monitoreo: TBD pending SDK G1
    """

    def __init__(self):
        super().__init__('watchdog_g1')

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

        # Timer — heartbeat propio
        self._heartbeat_timer = self.create_timer(
            1.0 / WATCHDOG_HEARTBEAT_HZ,
            self._publish_heartbeat,
        )

        # Timer — SafetyEvent mock (solo skeleton — reemplazar con lógica real)
        self._mock_event_timer = self.create_timer(
            MOCK_EVENT_INTERVAL_S,
            self._publish_mock_safety_event,
        )

        self.get_logger().info(
            'watchdog_g1 skeleton iniciado. '
            'Heartbeat activo. Mock SafetyEvent cada '
            f'{MOCK_EVENT_INTERVAL_S}s. '
            'Thresholds reales TBD — pending SDK G1.'
        )

    # -----------------------------------------------------------------------
    # Heartbeat — /diagnostics
    # -----------------------------------------------------------------------

    def _publish_heartbeat(self):
        """
        Publica DiagnosticArray con estado propio del watchdog.
        Detectable externamente via ausencia de heartbeat — supervisor externo (systemd).
        Ver RESILIENCE_MODEL_G1.md Sección 6.2 — watchdog no puede observarse a sí mismo.
        """
        now = self.get_clock().now().to_msg()

        status = DiagnosticStatus()
        status.level = DiagnosticStatus.OK
        status.name = 'watchdog_g1'
        status.message = 'SKELETON — heartbeat activo. Monitoreo real TBD.'
        status.hardware_id = HARDWARE_ID
        status.values = [
            KeyValue(key='state', value='SKELETON'),
            KeyValue(key='heartbeat_hz', value=str(WATCHDOG_HEARTBEAT_HZ)),
            KeyValue(key='sdk_required', value='true'),
        ]

        msg = DiagnosticArray()
        msg.header.stamp = now
        msg.status = [status]

        self._pub_diagnostics.publish(msg)

    # -----------------------------------------------------------------------
    # Mock SafetyEvent — solo skeleton, reemplazar con detección real
    # -----------------------------------------------------------------------

    def _publish_mock_safety_event(self):
        """
        Publica SafetyEvent mock para validar pipeline de mensajes.
        SKELETON ONLY — reemplazar con detección real de timeouts/heartbeats.
        """
        msg = SafetyEvent()
        msg.event_id = str(uuid.uuid4())
        msg.event_type = 'CONDITION_DETECTED'
        msg.source = 'watchdog_g1'
        msg.source_authority = 'SECONDARY'
        msg.authority_effectiveness = 'EFFECTIVE'
        msg.target = 'MOCK_TARGET'
        msg.risk_level = 'SAFE'
        msg.restriction_level = 'NONE'
        msg.transition_id = ''
        msg.transition_priority = 'NORMAL'
        msg.execution_confidence = 'VERIFIED'
        msg.timestamp = self.get_clock().now().to_msg()
        msg.notes = (
            'SKELETON MOCK EVENT — watchdog_g1 Capa 4. '
            'Lógica real TBD pending SDK G1.'
        )

        self._pub_safety_events.publish(msg)
        self.get_logger().info(
            f'[MOCK] SafetyEvent publicado — event_id: {msg.event_id}'
        )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main(args=None):
    rclpy.init(args=args)
    node = WatchdogG1()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
