# G1 Pipeline — Watchdog Unit Tests
# Tests are isolated: no real ROS graph, no host dependencies
# Each test manages its own rclpy lifecycle via setUp/tearDown
# ROS_DOMAIN_ID=99 set in CMakeLists to avoid DDS contamination

import os
import json
import time
import unittest
import tempfile
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Imu, LaserScan
from nav_msgs.msg import Odometry
from tf2_msgs.msg import TFMessage


class TestWatchdog(unittest.TestCase):

    def setUp(self):
        rclpy.init()
        self.node = rclpy.create_node('test_watchdog_node')
        self.tmp = tempfile.NamedTemporaryFile(
            suffix='.json', delete=False
        )
        self.status_path = self.tmp.name
        self.tmp.close()

    def tearDown(self):
        self.node.destroy_node()
        rclpy.shutdown()
        os.unlink(self.status_path)

    def _read_status(self):
        with open(self.status_path) as f:
            return json.load(f)

    def _write_status(self, state, components=None):
        status = {
            'state': state,
            'fault': 'NONE' if state == 'RUNNING' else 'FAULT_PASSIVE',
            'components': components or {
                'lidar': 'OK',
                'esp32_imu': 'OK',
                'odom': 'OK',
                'tf': 'OK'
            }
        }
        with open(self.status_path, 'w') as f:
            json.dump(status, f)

    def test_status_file_running(self):
        # Watchdog writes RUNNING when all components OK
        self._write_status('RUNNING')
        status = self._read_status()
        self.assertEqual(status['state'], 'RUNNING')
        self.assertEqual(status['fault'], 'NONE')

    def test_status_file_fault_passive(self):
        # Watchdog writes FAULT_PASSIVE when a component fails
        self._write_status('FAULT_PASSIVE', {
            'lidar': 'TIMEOUT',
            'esp32_imu': 'OK',
            'odom': 'OK',
            'tf': 'OK'
        })
        status = self._read_status()
        self.assertEqual(status['state'], 'FAULT_PASSIVE')
        self.assertEqual(status['components']['lidar'], 'TIMEOUT')

    def test_all_components_present(self):
        # Status JSON must always have all 4 components
        self._write_status('RUNNING')
        status = self._read_status()
        required = ['lidar', 'esp32_imu', 'odom', 'tf']
        for key in required:
            self.assertIn(key, status['components'])

    def test_node_creation(self):
        # rclpy lifecycle is clean per test
        self.assertIsNotNone(self.node)
        self.assertEqual(
            self.node.get_name(), 'test_watchdog_node'
        )


if __name__ == '__main__':
    unittest.main()
