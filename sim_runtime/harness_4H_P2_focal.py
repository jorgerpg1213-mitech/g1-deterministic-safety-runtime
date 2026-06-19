#!/usr/bin/env python3
"""
harness_4H_P2_focal.py — Prueba focal 4H-P2-A
Publica SafetyEvent directamente a recovery_g1 (sin watchdog ni stack).

Criterios PASS:
  1. Dos FREEZE consecutivos (mismo target, sep=0.5s) →
       dos logs [4H-P2] cause=FREEZE
       sin "Cooldown activo" entre ellos
  2. Después de FREEZE terminal, un STALE mismo target →
       log [4H-P1] cause=STALE (flujo recuperable, sin contaminación counter)

Uso:
  python3 harness_4H_P2_focal.py
"""

import time
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy
from g1_msgs.msg import SafetyEvent


RELIABLE_QOS = QoSProfile(
    reliability=ReliabilityPolicy.RELIABLE,
    history=HistoryPolicy.KEEP_LAST,
    depth=50,
)

TARGET = '/g1/imu'


def make_safety_event(node: Node, event_type: str, source: str, notes: str) -> SafetyEvent:
    msg = SafetyEvent()
    msg.event_type = event_type
    msg.target = TARGET
    msg.source = source
    msg.notes = notes
    msg.timestamp = node.get_clock().now().to_msg()
    return msg


def main():
    rclpy.init()
    node = Node('harness_4H_P2_focal')
    pub = node.create_publisher(SafetyEvent, '/safety_events', RELIABLE_QOS)

    # Dar tiempo a recovery_g1 para suscribirse
    time.sleep(2.0)

    print('[HARNESS] === 4H-P2 FOCAL TEST ===', flush=True)

    # --- Criterio 1: dos FREEZE consecutivos, sep=0.5s ---
    print('[HARNESS] Paso 1a: FREEZE #1', flush=True)
    pub.publish(make_safety_event(
        node,
        event_type='CONDITION_DETECTED',
        source='watchdog_g1',
        notes='rule_id=4F-P2-FREEZE target=/g1/imu valores_repetidos=True',
    ))
    time.sleep(0.5)

    print('[HARNESS] Paso 1b: FREEZE #2 (mismo target, <5s)', flush=True)
    pub.publish(make_safety_event(
        node,
        event_type='CONDITION_DETECTED',
        source='watchdog_g1',
        notes='rule_id=4F-P2-FREEZE target=/g1/imu valores_repetidos=True',
    ))
    time.sleep(1.0)

    # --- Criterio 2: STALE del mismo target post-terminal ---
    print('[HARNESS] Paso 2: STALE mismo target post-FREEZE', flush=True)
    pub.publish(make_safety_event(
        node,
        event_type='CONDITION_DETECTED',
        source='watchdog_g1',
        notes='rule_id=4F-P2-STALE target=/g1/imu elapsed_s=1.39',
    ))
    time.sleep(2.0)  # margen para wait_for_primary_restore y publicación RecoveryEvent

    print('[HARNESS] Secuencia publicada. Revisar logs de recovery_g1.', flush=True)
    print('[HARNESS] PASS si:', flush=True)
    print('  - Dos "[4H-P2] cause=FREEZE" sin "Cooldown activo" entre ellos', flush=True)
    print('  - Un "[4H-P1] cause=STALE action=wait_for_primary_restore"', flush=True)

    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
