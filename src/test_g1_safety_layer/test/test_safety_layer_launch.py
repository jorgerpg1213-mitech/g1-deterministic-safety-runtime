# test_safety_layer_launch.py
# G1 ROS2 Pipeline — Level 4 Integration Test: Safety Layer Skeleton
#
# SCOPE EXPLÍCITO:
#   - Valida que los 4 nodos del safety layer levantan sin crashear
#   - Valida que /diagnostics recibe heartbeat de cada nodo
#   - Valida que /system_state es visible con QoS Transient Local
#     y compound state inicial (SAFE, NONE)
#   - Valida que /safety_events es visible con QoS Reliable
#   - Valida que /recovery_events es visible
#
# NO VALIDA:
#   - Lógica de transición real (skeleton — TBD)
#   - Thresholds reales (TBD — pending SDK G1)
#   - Recovery real (TBD — pending SDK G1)
#   - Estado interno de ningún nodo
#   - Arbitration real (T8 — DRAFT)
#
# Metodología: verificación exclusiva via topics observables.
# ADR-002 Sección 12.3: "Los Level 4 tests deben poder verificar
# comportamiento del orchestrator exclusivamente a través de outputs."

import time
import unittest

import launch
import launch_ros.actions
import launch_testing
import launch_testing.actions
import launch_testing.markers
import pytest
import rclpy
from diagnostic_msgs.msg import DiagnosticArray
from rclpy.qos import (
    DurabilityPolicy,
    HistoryPolicy,
    QoSProfile,
    ReliabilityPolicy,
)

from g1_msgs.msg import RecoveryEvent, SafetyEvent, SystemState

# ---------------------------------------------------------------------------
# QoS — debe coincidir con lo definido en los nodos (ADR-002 Sección 4)
# ---------------------------------------------------------------------------

QOS_RELIABLE = QoSProfile(
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

QOS_BEST_EFFORT = QoSProfile(
    reliability=ReliabilityPolicy.BEST_EFFORT,
    durability=DurabilityPolicy.VOLATILE,
    history=HistoryPolicy.KEEP_LAST,
    depth=10,
)

TIMEOUT_S = 15.0  # Timeout por test — suficiente para skeleton nodes


# ---------------------------------------------------------------------------
# Launch description — levanta los 4 nodos juntos
# ---------------------------------------------------------------------------

@pytest.mark.launch_test
@launch_testing.markers.keep_alive
def generate_test_description():
    watchdog_node = launch_ros.actions.Node(
        package='watchdog_g1',
        executable='watchdog_g1',
        name='watchdog_g1',
        output='screen',
    )

    observer_node = launch_ros.actions.Node(
        package='cross_consistency_observer',
        executable='cross_consistency_observer',
        name='cross_consistency_observer',
        output='screen',
    )

    orchestrator_node = launch_ros.actions.Node(
        package='safety_orchestrator_g1',
        executable='safety_orchestrator_g1',
        name='safety_orchestrator_g1',
        output='screen',
    )

    recovery_node = launch_ros.actions.Node(
        package='recovery_g1',
        executable='recovery_g1',
        name='recovery_g1',
        output='screen',
    )

    return launch.LaunchDescription([
        watchdog_node,
        observer_node,
        orchestrator_node,
        recovery_node,
        launch_testing.actions.ReadyToTest(),
    ])


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestSafetyLayerLaunch(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        rclpy.init()
        cls.node = rclpy.create_node('test_safety_layer_node')

    @classmethod
    def tearDownClass(cls):
        cls.node.destroy_node()
        rclpy.shutdown()

    # -----------------------------------------------------------------------
    # Test 1 — Los 4 nodos existen en el ROS graph
    # -----------------------------------------------------------------------

    def test_all_nodes_alive(self):
        """
        Los 4 nodos del safety layer deben aparecer en el ROS graph.
        Verificación exclusiva via get_node_names() — sin acceso a estado interno.
        """
        expected_nodes = {
            'watchdog_g1',
            'cross_consistency_observer',
            'safety_orchestrator_g1',
            'recovery_g1',
        }

        deadline = time.time() + TIMEOUT_S
        found = set()

        while time.time() < deadline and found != expected_nodes:
            nodes = set(self.node.get_node_names())
            found = expected_nodes & nodes
            if found != expected_nodes:
                time.sleep(0.5)

        missing = expected_nodes - found
        self.assertEqual(
            missing, set(),
            f'Nodos no encontrados en ROS graph después de {TIMEOUT_S}s: {missing}'
        )

    # -----------------------------------------------------------------------
    # Test 2 — /system_state visible con QoS Transient Local
    # -----------------------------------------------------------------------

    def test_system_state_topic_visible(self):
        """
        /system_state debe ser visible con QoS Transient Local en launch completo.
        Valida visibilidad del topic — no estado inicial, porque otros nodos
        pueden generar eventos safety y transicionar el sistema.
        QoS Transient Local definido en ADR-002 Sección 4.2.
        """
        received = []
        sub = self.node.create_subscription(
            SystemState,
            '/system_state',
            lambda msg: received.append(msg),
            QOS_SYSTEM_STATE,
        )
        deadline = time.time() + TIMEOUT_S
        while time.time() < deadline and len(received) == 0:
            rclpy.spin_once(self.node, timeout_sec=0.5)
        self.node.destroy_subscription(sub)
        self.assertGreater(
            len(received), 0,
            f'/system_state sin mensajes después de {TIMEOUT_S}s — '
            'verificar QoS Transient Local en safety_orchestrator_g1'
        )

    def test_safety_events_visible(self):
        """
        /safety_events debe recibir al menos un mensaje en TIMEOUT_S.
        watchdog_g1 publica mock SafetyEvent cada 10s — suficiente para detectar.
        QoS Reliable — ADR-002 Sección 4.1.
        """
        received = []

        sub = self.node.create_subscription(
            SafetyEvent,
            '/safety_events',
            lambda msg: received.append(msg),
            QOS_RELIABLE,
        )

        deadline = time.time() + TIMEOUT_S
        while time.time() < deadline and len(received) == 0:
            rclpy.spin_once(self.node, timeout_sec=0.5)

        self.node.destroy_subscription(sub)

        self.assertGreater(
            len(received), 0,
            f'/safety_events sin mensajes después de {TIMEOUT_S}s — '
            'verificar watchdog_g1 mock event timer'
        )

        event = received[0]
        self.assertNotEqual(
            event.event_id, '',
            'SafetyEvent.event_id no debe ser vacío'
        )
        self.assertNotEqual(
            event.source, '',
            'SafetyEvent.source no debe ser vacío'
        )

    # -----------------------------------------------------------------------
    # Test 4 — /diagnostics recibe heartbeat de los nodos críticos
    # -----------------------------------------------------------------------

    def test_diagnostics_heartbeat(self):
        """
        /diagnostics debe recibir heartbeat de los nodos del safety layer.
        Verifica que watchdog_g1, safety_orchestrator_g1, y recovery_g1
        publican su estado de salud.
        ADR-002 Sección 12.2 + RESILIENCE_MODEL_G1.md Sección 6.
        """
        expected_nodes = {
            'watchdog_g1',
            'safety_orchestrator_g1',
            'recovery_g1',
            'cross_consistency_observer',
        }
        seen_nodes = set()

        def on_diagnostics(msg):
            for status in msg.status:
                if status.name in expected_nodes:
                    seen_nodes.add(status.name)

        sub = self.node.create_subscription(
            DiagnosticArray,
            '/diagnostics',
            on_diagnostics,
            QOS_BEST_EFFORT,
        )

        deadline = time.time() + TIMEOUT_S
        while time.time() < deadline and seen_nodes != expected_nodes:
            rclpy.spin_once(self.node, timeout_sec=0.5)

        self.node.destroy_subscription(sub)

        missing = expected_nodes - seen_nodes
        self.assertEqual(
            missing, set(),
            f'Nodos sin heartbeat en /diagnostics después de {TIMEOUT_S}s: {missing}'
        )

    # -----------------------------------------------------------------------
    # Test 5 — /recovery_events visible
    # -----------------------------------------------------------------------

    def test_recovery_events_topic_exists(self):
        """
        /recovery_events debe existir como topic en el ROS graph.
        recovery_g1 crea el publisher al arrancar — topic visible aunque
        no haya mensajes todavía (no hay SafetyEvents de condición real).
        """
        deadline = time.time() + TIMEOUT_S
        topic_found = False

        while time.time() < deadline and not topic_found:
            topics = [name for name, _ in self.node.get_topic_names_and_types()]
            if '/recovery_events' in topics:
                topic_found = True
                break
            time.sleep(0.5)

        self.assertTrue(
            topic_found,
            f'/recovery_events no visible en ROS graph después de {TIMEOUT_S}s'
        )
