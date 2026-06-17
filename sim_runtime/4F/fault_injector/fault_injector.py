#!/usr/bin/env python3
"""
4F-P6 Fault Injector — G1 Deterministic Safety Runtime
Publica mensajes sintéticos en lugar de Isaac para probar watchdog_g1.
Uso: python3 fault_injector.py --fault <modo> [--topic left|right]
"""

import argparse
import math
import random
import time

import rclpy
from rclpy.node import Node
from builtin_interfaces.msg import Time
from sensor_msgs.msg import Imu, JointState
from geometry_msgs.msg import PoseStamped
from g1_msgs.msg import FootContact

WARMUP_S   = 15.0
PUBLISH_HZ = 10.0
FAULT_MSGS = 10

FAULT_MODES = [
    'imu_freeze',
    'imu_stale',
    'joint_nan',
    'contact_freeze_false',
    'timestamp_regression',
]

def wall():
    return time.time()

def log(tag, msg):
    print(f'[{time.strftime("%H:%M:%S")}] [{tag}] {msg}', flush=True)


class FaultInjector(Node):
    def __init__(self, fault, contact_side):
        super().__init__('fault_injector_g1')
        self.fault = fault
        self.contact_side = contact_side
        self._tick_count = 0

        if fault in ('imu_freeze', 'imu_stale', 'timestamp_regression'):
            self.pub = self.create_publisher(Imu, '/g1/imu', 10)
        elif fault == 'joint_nan':
            self.pub = self.create_publisher(JointState, '/joint_states', 10)
        elif fault == 'contact_freeze_false':
            self.pub = self.create_publisher(FootContact, f'/g1/contact/{contact_side}', 10)

        self.pub_imu       = self.create_publisher(Imu,         '/g1/imu',            10)
        self.pub_joints    = self.create_publisher(JointState,  '/joint_states',       10)
        self.pub_contact_l = self.create_publisher(FootContact, '/g1/contact/left',    10)
        self.pub_contact_r = self.create_publisher(FootContact, '/g1/contact/right',   10)
        self.pub_base_pose = self.create_publisher(PoseStamped, '/g1/base_pose',       10)

        self._last_stamp_sec = None
        self._phase = 'warmup'
        self._fault_count = 0
        self._warmup_start = wall()
        self._frozen_imu = None

        self.timer = self.create_timer(1.0 / PUBLISH_HZ, self.tick)
        log('WARMUP_START', f'fault={fault} warmup={WARMUP_S}s hz={PUBLISH_HZ}')

    def _now_stamp(self):
        return self.get_clock().now().to_msg()

    def _make_imu_sano(self, stamp=None):
        msg = Imu()
        msg.header.stamp = stamp if stamp else self._now_stamp()
        msg.header.frame_id = 'imu_link'
        msg.orientation.w = 0.99 + random.uniform(-0.005, 0.005)
        msg.orientation.x = random.uniform(-0.01, 0.01)
        msg.orientation.y = random.uniform(-0.01, 0.01)
        msg.orientation.z = random.uniform(-0.01, 0.01)
        msg.angular_velocity.x = random.uniform(-0.02, 0.02)
        msg.angular_velocity.y = random.uniform(-0.02, 0.02)
        msg.angular_velocity.z = random.uniform(-0.02, 0.02)
        msg.linear_acceleration.x = random.uniform(-0.05, 0.05)
        msg.linear_acceleration.y = random.uniform(-0.05, 0.05)
        msg.linear_acceleration.z = 9.81 + random.uniform(-0.05, 0.05)
        return msg

    def _make_joint_sano(self):
        # epsilon senoidal para evitar FREEZE
        t = self._tick_count / PUBLISH_HZ
        msg = JointState()
        msg.header.stamp = self._now_stamp()
        msg.name = [f'joint_{i}' for i in range(12)]
        msg.position = [0.01 * math.sin(t + i * 0.5) for i in range(12)]
        msg.velocity = [0.001 * math.cos(t + i * 0.5) for i in range(12)]
        msg.effort   = [0.0] * 12
        return msg

    def _make_contact_sano(self):
        # contactos pueden ser constantes — excluidos de FREEZE por diseño
        msg = FootContact()
        msg.header.stamp = self._now_stamp()
        msg.in_contact = True
        msg.force = 150.0
        msg.number_of_contacts = 1
        return msg

    def _make_pose_sano(self):
        # variar z con seno pequeño para evitar FREEZE
        t = self._tick_count / PUBLISH_HZ
        msg = PoseStamped()
        msg.header.stamp = self._now_stamp()
        msg.header.frame_id = 'world'
        msg.pose.position.z = 0.720 + 0.001 * math.sin(t)
        msg.pose.position.x = 0.0
        msg.pose.position.y = 0.0
        msg.pose.orientation.w = 1.0
        return msg

    def _publish_all_sano(self):
        imu = self._make_imu_sano()
        self._frozen_imu = imu
        s = imu.header.stamp
        self._last_stamp_sec = s.sec + s.nanosec * 1e-9
        self.pub_imu.publish(imu)
        self.pub_joints.publish(self._make_joint_sano())
        self.pub_contact_l.publish(self._make_contact_sano())
        self.pub_contact_r.publish(self._make_contact_sano())
        self.pub_base_pose.publish(self._make_pose_sano())

    def _publish_support_sano(self):
        fault = self.fault
        if fault not in ('imu_freeze', 'imu_stale', 'timestamp_regression'):
            self.pub_imu.publish(self._make_imu_sano())
        if fault != 'joint_nan':
            self.pub_joints.publish(self._make_joint_sano())
        if fault != 'contact_freeze_false' or self.contact_side != 'left':
            self.pub_contact_l.publish(self._make_contact_sano())
        if fault != 'contact_freeze_false' or self.contact_side != 'right':
            self.pub_contact_r.publish(self._make_contact_sano())
        self.pub_base_pose.publish(self._make_pose_sano())

    def tick(self):
        self._tick_count += 1
        elapsed = wall() - self._warmup_start

        if self._phase == 'warmup':
            self._publish_all_sano()
            if elapsed >= WARMUP_S:
                self._phase = 'fault'
                log('FAULT_ARMED', f'warmup completo ({elapsed:.1f}s) → inyectando {self.fault}')
            return

        if self._phase == 'fault':
            self._publish_support_sano()
            self._publish_fault()

    def _publish_fault(self):
        fault = self.fault

        if fault == 'imu_freeze':
            msg = self._frozen_imu
            msg.header.stamp = self._now_stamp()
            self.pub_imu.publish(msg)
            self._fault_count += 1
            log('FAULT_INJECTED', f'imu_freeze msg#{self._fault_count} valores congelados')
            if self._fault_count >= FAULT_MSGS:
                log('FAULT_DONE', 'imu_freeze completado')
                self._shutdown()

        elif fault == 'imu_stale':
            if self._fault_count == 0:
                log('LAST_GOOD_MSG', f'stamp={self._last_stamp_sec:.3f}')
                log('PUBLISH_STOPPED', 'dejando de publicar /g1/imu')
                self._fault_count = 1
            elapsed_fault = wall() - self._warmup_start - WARMUP_S
            if elapsed_fault > 5.0:
                log('FAULT_DONE', 'imu_stale completado (5s sin publicar)')
                self._shutdown()

        elif fault == 'joint_nan':
            msg = JointState()
            msg.header.stamp = self._now_stamp()
            msg.name = [f'joint_{i}' for i in range(12)]
            msg.position = [float('nan')] * 12
            msg.velocity = [0.0] * 12
            msg.effort   = [0.0] * 12
            self.pub_joints.publish(msg)
            self._fault_count += 1
            log('FAULT_INJECTED', f'joint_nan msg#{self._fault_count}')
            if self._fault_count >= 3:
                log('FAULT_DONE', 'joint_nan completado')
                self._shutdown()

        elif fault == 'contact_freeze_false':
            msg = FootContact()
            msg.header.stamp = self._now_stamp()
            msg.in_contact = False
            msg.force = 0.0
            msg.number_of_contacts = 0
            self.pub.publish(msg)
            self._fault_count += 1
            log('FAULT_INJECTED', f'contact_freeze_false msg#{self._fault_count}')
            if self._fault_count >= FAULT_MSGS:
                log('FAULT_DONE', 'contact_freeze_false completado — watchdog debe estar en SILENCIO')
                self._shutdown()

        elif fault == 'timestamp_regression':
            if self._fault_count == 0:
                regressed = self._last_stamp_sec - 2.0
                stamp = Time()
                stamp.sec = int(regressed)
                stamp.nanosec = int((regressed - int(regressed)) * 1e9)
                msg = self._make_imu_sano(stamp=stamp)
                self.pub_imu.publish(msg)
                log('FAULT_INJECTED', f'timestamp_regression stamp={regressed:.3f} < last={self._last_stamp_sec:.3f}')
                self._fault_count = 1
            else:
                self.pub_imu.publish(self._make_imu_sano())
                self._fault_count += 1
                if self._fault_count >= 5:
                    log('FAULT_DONE', 'timestamp_regression completado')
                    self._shutdown()

    def _shutdown(self):
        self.timer.cancel()
        rclpy.shutdown()


def main():
    parser = argparse.ArgumentParser(description='4F-P6 Fault Injector')
    parser.add_argument('--fault', required=True, choices=FAULT_MODES)
    parser.add_argument('--topic', default='left', choices=['left', 'right'])
    args = parser.parse_args()

    rclpy.init()
    node = FaultInjector(fault=args.fault, contact_side=args.topic)
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        log('ABORT', 'interrumpido')
    finally:
        node.destroy_node()

if __name__ == '__main__':
    main()
