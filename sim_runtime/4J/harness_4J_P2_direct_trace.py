#!/usr/bin/env python3
"""
Harness 4J-P2 — Trazabilidad directa ruta STALE
Workstream: B / F2 / R2 / E2 / C1 / P3

Hipótesis: SafetyEvent(STALE, event_id=FIXED_ID)
           via ruta directa recovery_g1
           → RecoveryEvent con action_name=wait_for_primary_restore,
             recovery_type=REC-AUTO, notes contiene parent_event_id=FIXED_ID

Aislamiento: solo recovery_g1 corriendo.
Topología verificada: subscriber único en /safety_events = recovery_g1.
Filtro: RecoveryEvent filtrado por parent_event_id=FIXED_ID exacto.

PASS:
  action_name=wait_for_primary_restore
  recovery_type=REC-AUTO
  notes contiene parent_event_id=4JP2-DIRECT-001

FAIL:
  timeout, action incorrecta, notes sin parent_event_id, topología sucia
"""
import rclpy, time, sys
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy, HistoryPolicy
from g1_msgs.msg import SafetyEvent, RecoveryEvent

FIXED_ID       = '4JP2-DIRECT-001'
WARMUP_S       = 5.0
TIMEOUT_S      = 10.0

reliable_qos = QoSProfile(
    reliability=ReliabilityPolicy.RELIABLE,
    durability=DurabilityPolicy.VOLATILE,
    history=HistoryPolicy.KEEP_LAST,
    depth=10,
)

class Harness4JP2Direct(Node):
    def __init__(self):
        super().__init__('harness_4j_p2_direct')
        self._pub_time = None
        self._events   = []
        self._pub = self.create_publisher(SafetyEvent, '/safety_events', reliable_qos)
        self.create_subscription(RecoveryEvent, '/recovery_events', self._on_rec, reliable_qos)
        self.get_logger().info('[4J-P2-DIRECT] Harness iniciado')

    def _on_rec(self, msg: RecoveryEvent):
        if self._pub_time is not None:
            # Filtrar por parent_event_id exacto — no agarrar eventos no relacionados
            if f'parent_event_id={FIXED_ID}' in (msg.notes or ''):
                self._events.append(msg)
                self.get_logger().info(
                    f'[4J-P2-DIRECT] RecoveryEvent: action={msg.action_name} '
                    f'recovery_type={msg.recovery_type} '
                    f'notes={msg.notes!r}')

def main():
    rclpy.init()
    node = Harness4JP2Direct()

    # Warmup — verificar subscriber único en /safety_events
    node.get_logger().info(f'[4J-P2-DIRECT] Warmup {WARMUP_S}s...')
    t0 = time.monotonic()
    rec_ready = False
    while time.monotonic() - t0 < WARMUP_S:
        rclpy.spin_once(node, timeout_sec=0.1)
        if node.count_subscribers('/safety_events') > 0:
            rec_ready = True
            break

    if not rec_ready:
        print('FAIL — recovery_g1 no detectado en /safety_events tras warmup')
        node.destroy_node(); rclpy.shutdown(); sys.exit(1)

    # Verificar topología: exactamente 1 subscriber en /safety_events
    subs = node.count_subscribers('/safety_events')
    if subs != 1:
        print(f'FAIL — topología sucia: {subs} subscribers en /safety_events (esperado 1)')
        node.destroy_node(); rclpy.shutdown(); sys.exit(1)

    node.get_logger().info(f'[4J-P2-DIRECT] [Iniciado] — 1 subscriber en /safety_events')

    # Publicar SafetyEvent STALE con event_id fijo
    msg = SafetyEvent()
    msg.event_id                = FIXED_ID
    msg.event_type              = 'CONDITION_DETECTED'
    msg.source                  = 'watchdog_g1'
    msg.source_authority        = 'PRIMARY'
    msg.authority_effectiveness = 'EFFECTIVE'
    msg.target                  = '/g1/imu'
    msg.notes                   = f'rule_id=4F-P2-STALE 4J-P2-DIRECT harness event_id={FIXED_ID}'
    msg.timestamp               = node.get_clock().now().to_msg()

    node._pub_time = time.monotonic()
    node.get_logger().warn(
        f'[4J-P2-DIRECT] Publicando SafetyEvent STALE event_id={FIXED_ID}')
    node._pub.publish(msg)

    # Esperar RecoveryEvent filtrado por FIXED_ID
    t1 = time.monotonic()
    while not node._events and (time.monotonic() - t1) < TIMEOUT_S:
        rclpy.spin_once(node, timeout_sec=0.1)

    node.destroy_node(); rclpy.shutdown()

    if not node._events:
        print(f'FAIL — timeout: no RecoveryEvent con parent_event_id={FIXED_ID}')
        sys.exit(1)

    rec = node._events[0]
    failures = []
    if rec.action_name != 'wait_for_primary_restore':
        failures.append(
            f'  action_name={rec.action_name!r} (esperado "wait_for_primary_restore")')
    if rec.recovery_type != 'REC-AUTO':
        failures.append(
            f'  recovery_type={rec.recovery_type!r} (esperado "REC-AUTO")')
    if f'parent_event_id={FIXED_ID}' not in rec.notes:
        failures.append(
            f'  notes no contiene "parent_event_id={FIXED_ID}": {rec.notes!r}')

    if failures:
        print('FAIL — RecoveryEvent incorrecto:')
        for f in failures: print(f)
        sys.exit(1)

    print('PASS — trazabilidad directa STALE verificada')
    print(f'  SafetyEvent.event_id:      {FIXED_ID}')
    print(f'  RecoveryEvent.action_name: {rec.action_name}')
    print(f'  RecoveryEvent.recovery_type: {rec.recovery_type}')
    print(f'  RecoveryEvent.notes:       {rec.notes}')
    sys.exit(0)

if __name__ == '__main__':
    main()
