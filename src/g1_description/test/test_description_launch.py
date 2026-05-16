# G1 Pipeline — Integration Test: description.launch.py
# Level 3 — Launch Integration Validation
#
# SCOPE EXPLÍCITO:
#   - Valida que description.launch.py arranca sin errores
#   - Valida que robot_state_publisher existe en el ROS graph
#   - Valida que /tf_static topic está activo (joints fijos — XACRO Phase 4A)
#
# NO VALIDA:
#   - Contenido del TF tree (pendiente Phase 4B USD oficiales)
#   - Parámetros físicos del XACRO (ultraconservador Phase 4A)
#   - Integración con SLAM, Nav2, o Isaac Sim

import unittest
import launch
import launch_testing
import launch_testing.actions
import launch_testing.markers
import pytest
import rclpy
from tf2_msgs.msg import TFMessage
from rclpy.qos import QoSProfile, DurabilityPolicy, ReliabilityPolicy


@pytest.mark.launch_test
@launch_testing.markers.keep_alive
def generate_test_description():
    from ament_index_python.packages import get_package_share_directory
    import os
    pkg = get_package_share_directory('g1_description')
    description_launch = launch.actions.IncludeLaunchDescription(
        launch.launch_description_sources.PythonLaunchDescriptionSource(
            os.path.join(pkg, 'launch', 'description.launch.py')
        )
    )
    return launch.LaunchDescription([
        description_launch,
        launch_testing.actions.ReadyToTest(),
    ])


class TestDescriptionLaunch(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        rclpy.init()
        cls.node = rclpy.create_node('test_description_launch_node')

    @classmethod
    def tearDownClass(cls):
        cls.node.destroy_node()
        rclpy.shutdown()

    def test_robot_state_publisher_exists(self):
        # robot_state_publisher debe existir en el ROS graph
        import time
        deadline = time.time() + 10.0
        node_found = False
        while time.time() < deadline:
            nodes = self.node.get_node_names()
            if 'robot_state_publisher' in nodes:
                node_found = True
                break
            time.sleep(0.5)
        self.assertTrue(
            node_found,
            'robot_state_publisher not found in ROS graph after 10s'
        )

    def test_tf_static_active(self):
        # /tf_static usa QoS transient_local — subscriber debe ser compatible
        # para recibir mensajes latched publicados antes de la suscripción
        import time
        tf_received = []

        qos = QoSProfile(
            depth=10,
            durability=DurabilityPolicy.TRANSIENT_LOCAL,
            reliability=ReliabilityPolicy.RELIABLE
        )

        sub = self.node.create_subscription(
            TFMessage,
            '/tf_static',
            lambda msg: tf_received.append(msg),
            qos
        )

        deadline = time.time() + 10.0
        while time.time() < deadline and len(tf_received) == 0:
            rclpy.spin_once(self.node, timeout_sec=0.5)

        self.node.destroy_subscription(sub)
        self.assertGreater(
            len(tf_received), 0,
            '/tf_static received no messages after 10s — QoS transient_local required'
        )
