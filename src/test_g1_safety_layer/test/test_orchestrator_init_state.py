# test_orchestrator_init_state.py
# G1 ROS2 Pipeline — Level 4 Integration Test: Orchestrator Init State
#
# SCOPE EXPLÍCITO:
#   - Valida que safety_orchestrator_g1 publica heartbeat INIT al arrancar
#   - Valida compound state inicial: risk_level=SAFE, restriction_level=NONE
#   - Launch aislado: solo orchestrator — sin observer/watchdog/recovery
#
# Metodología: launch aislado garantiza que no hay eventos safety externos
# que puedan transicionar el estado antes de capturar INIT.
# ADR-002 Sección 4.2.
import time
import unittest
import launch
import launch_ros.actions
import launch_testing
import launch_testing.actions
import launch_testing.markers
import pytest
import rclpy
from rclpy.qos import (
    DurabilityPolicy,
    HistoryPolicy,
    QoSProfile,
    ReliabilityPolicy,
)
from g1_msgs.msg import SystemState

TIMEOUT_S = 15.0

QOS_SYSTEM_STATE = QoSProfile(
    reliability=ReliabilityPolicy.RELIABLE,
    durability=DurabilityPolicy.TRANSIENT_LOCAL,
    history=HistoryPolicy.KEEP_LAST,
    depth=1,
)

@pytest.mark.launch_test
@launch_testing.markers.keep_alive
def generate_test_description():
    orchestrator_node = launch_ros.actions.Node(
        package='safety_orchestrator_g1',
        executable='safety_orchestrator_g1',
        name='safety_orchestrator_g1',
        output='screen',
    )
    return launch.LaunchDescription([
        orchestrator_node,
        launch_testing.actions.ReadyToTest(),
    ])


class TestOrchestratorInitState(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        rclpy.init()
        cls.node = rclpy.create_node('test_orchestrator_init_node')

    @classmethod
    def tearDownClass(cls):
        cls.node.destroy_node()
        rclpy.shutdown()

    def test_orchestrator_publishes_init_state(self):
        """
        El orchestrator publica heartbeat INIT con SAFE/NONE al arrancar.
        Launch aislado sin observer/watchdog/recovery garantiza que no hay
        eventos safety externos que transicionen el estado antes de INIT.
        """
        received = []
        sub = self.node.create_subscription(
            SystemState,
            '/system_state',
            lambda msg: received.append(msg),
            QOS_SYSTEM_STATE,
        )
        init_msg = None
        deadline = time.time() + TIMEOUT_S
        while time.time() < deadline and init_msg is None:
            rclpy.spin_once(self.node, timeout_sec=0.5)
            for msg in received:
                if msg.last_transition_id == 'INIT':
                    init_msg = msg
                    break
        self.node.destroy_subscription(sub)
        self.assertIsNotNone(
            init_msg,
            f'/system_state INIT no recibido en {TIMEOUT_S}s — '
            'verificar heartbeat inicial en safety_orchestrator_g1'
        )
        self.assertEqual(init_msg.risk_level, 'SAFE')
        self.assertEqual(init_msg.restriction_level, 'NONE')
        self.assertFalse(init_msg.r5_committed)
        self.assertFalse(init_msg.arbitration_pending)
