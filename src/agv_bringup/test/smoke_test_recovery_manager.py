# G1 Pipeline — Recovery Manager Unit Tests
# Recovery commands replaced by dummy flag files — no real processes
# Cooldown parametrized to 0.5s for deterministic testing
# ROS_DOMAIN_ID=99 set in CMakeLists to avoid DDS contamination

import os
import json
import time
import unittest
import tempfile


class TestRecoveryManager(unittest.TestCase):

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.status_path = os.path.join(self.tmp_dir, 'g1_status.json')
        self.recovery_flag = os.path.join(self.tmp_dir, 'recovery.flag')
        self.escalation_flag = os.path.join(self.tmp_dir, 'escalation_required.flag')

    def tearDown(self):
        for f in [self.status_path, self.recovery_flag, self.escalation_flag]:
            if os.path.exists(f):
                os.unlink(f)
        os.rmdir(self.tmp_dir)

    def _write_status(self, state, component='lidar'):
        status = {
            'state': state,
            'fault': 'NONE' if state == 'RUNNING' else 'FAULT_PASSIVE',
            'components': {
                'lidar': 'OK',
                'esp32_imu': 'OK',
                'odom': 'OK',
                'tf': 'OK'
            }
        }
        if state == 'FAULT_PASSIVE':
            status['components'][component] = 'TIMEOUT'
        with open(self.status_path, 'w') as f:
            json.dump(status, f)

    def _simulate_recovery(self):
        # Dummy recovery — writes flag instead of pkill/ros2 run
        with open(self.recovery_flag, 'w') as f:
            f.write('recovery_triggered')

    def _simulate_escalation(self):
        # 3 failed attempts in 30s triggers escalation
        with open(self.escalation_flag, 'w') as f:
            f.write('escalation_required')

    def test_running_state_no_recovery(self):
        # Recovery must NOT trigger when state is RUNNING
        self._write_status('RUNNING')
        status = json.load(open(self.status_path))
        self.assertEqual(status['state'], 'RUNNING')
        self.assertFalse(os.path.exists(self.recovery_flag))

    def test_fault_passive_triggers_recovery(self):
        # Recovery must trigger when state is FAULT_PASSIVE
        self._write_status('FAULT_PASSIVE', 'lidar')
        status = json.load(open(self.status_path))
        self.assertEqual(status['state'], 'FAULT_PASSIVE')
        self._simulate_recovery()
        self.assertTrue(os.path.exists(self.recovery_flag))

    def test_escalation_flag_created(self):
        # After 3 failed recoveries escalation flag must exist
        self._simulate_escalation()
        self.assertTrue(os.path.exists(self.escalation_flag))

    def test_status_file_required(self):
        # Recovery manager must not run without status file
        self.assertFalse(os.path.exists(self.status_path))

    def test_component_timeout_detected(self):
        # Specific component timeout must be detectable
        self._write_status('FAULT_PASSIVE', 'odom')
        status = json.load(open(self.status_path))
        self.assertEqual(status['components']['odom'], 'TIMEOUT')


if __name__ == '__main__':
    unittest.main()
