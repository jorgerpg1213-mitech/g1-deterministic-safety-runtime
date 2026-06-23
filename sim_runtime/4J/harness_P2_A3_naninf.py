"""
Harness 4J-P2-A3 -- NANINF (Terminal Manual Path)
Workstream: B / F2 / R3 / E3 / C1 / P3

Hipotesis: SafetyEvent(rule_id=4F-P2-NANINF, event_id=FIXED_ID)
           via ruta terminal R3 -> recovery_g1
           -> RecoveryEvent action_name=request_operator_intervention,
             recovery_type=REC-MANUAL, attempt_number=1,
             notes contiene parent_event_id=FIXED_ID

PASS:
  action_name=request_operator_intervention
  recovery_type=REC-MANUAL
  attempt_number=1
  notes contiene parent_event_id=4JP2-A3-NANINF-001

FAIL:
  timeout, wait_for_primary_restore, cooldown suppression,
  attempt_number>1, missing parent_event_id, recovery_type!=REC-MANUAL
"""
import rclpy, time, sys
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy, HistoryPolicy
from g1_msgs.msg import SafetyEvent, RecoveryEvent

FIXED_ID  = '4JP2-A3-NANINF-001'
WARMUP_S  = 5.0
TIMEOUT_S = 10.0

reliable_qos = QoSProfile(
    reliability=ReliabilityPolicy.RELIABLE,
    durability=DurabilityPolicy.VOLATILE,
    history=HistoryPolicy.KEEP_LAST,
    depth=10,
)

class HarnessP2A3Naninf(Node):
    def __init__(self):
        super().__init__('harness_p2_a3_naninf')
        self._pub_time = None
        self._events   = []
        self._pub = self.create_publisher(SafetyEvent, '/safety_events', reliable_qos)
        self.create_subscription(RecoveryEvent, '/recovery_events', self._on_rec, reliable_qos)
        self.get_logger().info('[P2-A3-NANINF] Harness iniciado')

    def _on_rec(self, msg: RecoveryEvent):
        if self._pub_time is not None:
            if f'parent_event_id={FIXED_ID}' in (msg.notes or ''):
                self._events.append(msg)
                self.get_logger().info(
                    f'[P2-A3-NANINF] RecoveryEvent: action={msg.action_name} '
                    f'type={msg.recovery_type} attempt={msg.attempt_number} '
                    f'notes={msg.notes!r}')

def main():
    rclpy.init()
    node = HarnessP2A3Naninf()

    node.get_logger().info(f'[P2-A3-NANINF] Warmup {WARMUP_S}s...')
    t0 = time.monotonic()
    rec_ready = False
    while time.monotonic() - t0 < WARMUP_S:
        rclpy.spin_once(node, timeout_sec=0.1)
        if node.count_subscribers('/safety_events') > 0:
            rec_ready = True
            break

    if not rec_ready:
        print('FAIL -- recovery_g1 no detectado en /safety_events tras warmup')
        node.destroy_node(); rclpy.shutdown(); sys.exit(1)

    subs = node.count_subscribers('/safety_events')
    if subs != 1:
        print(f'FAIL -- topologia sucia: {subs} subscribers (esperado 1)')
        node.destroy_node(); rclpy.shutdown(); sys.exit(1)

    node.get_logger().info('[P2-A3-NANINF] [Iniciado] -- 1 subscriber en /safety_events')

    msg = SafetyEvent()
    msg.event_id                = FIXED_ID
    msg.event_type              = 'CONDITION_DETECTED'
    msg.source                  = 'watchdog_g1'
    msg.source_authority        = 'PRIMARY'
    msg.authority_effectiveness = 'EFFECTIVE'
    msg.target                  = '/g1/imu'
    msg.risk_level              = 'FAULT_CRITICAL'
    msg.restriction_level       = 'R3'
    msg.transition_id           = ''
    msg.transition_priority     = 'CRITICAL_INTERRUPT'
    msg.execution_confidence    = 'VERIFIED'
    msg.notes                   = f'rule_id=4F-P2-NANINF 4J-P2-A3 harness event_id={FIXED_ID}'
    msg.timestamp               = node.get_clock().now().to_msg()

    node._pub_time = time.monotonic()
    node.get_logger().warn(
        f'[P2-A3-NANINF] Publicando SafetyEvent NANINF event_id={FIXED_ID}')
    node._pub.publish(msg)

    t1 = time.monotonic()
    while not node._events and (time.monotonic() - t1) < TIMEOUT_S:
        rclpy.spin_once(node, timeout_sec=0.1)

    node.destroy_node(); rclpy.shutdown()

    if not node._events:
        print(f'FAIL -- timeout: no RecoveryEvent con parent_event_id={FIXED_ID}')
        sys.exit(1)

    rec = node._events[0]
    failures = []
    if rec.action_name != 'request_operator_intervention':
        failures.append(
            f'  action_name={rec.action_name!r} (esperado "request_operator_intervention")')
    if rec.recovery_type != 'REC-MANUAL':
        failures.append(
            f'  recovery_type={rec.recovery_type!r} (esperado "REC-MANUAL")')
    if rec.attempt_number != 1:
        failures.append(
            f'  attempt_number={rec.attempt_number} (esperado 1)')
    if f'parent_event_id={FIXED_ID}' not in (rec.notes or ''):
        failures.append(
            f'  notes no contiene "parent_event_id={FIXED_ID}": {rec.notes!r}')

    if failures:
        print('FAIL -- RecoveryEvent incorrecto:')
        for f in failures: print(f)
        sys.exit(1)

    print('PASS -- NANINF terminal manual verificado')
    print(f'  SafetyEvent.event_id:        {FIXED_ID}')
    print(f'  RecoveryEvent.action_name:   {rec.action_name}')
    print(f'  RecoveryEvent.recovery_type: {rec.recovery_type}')
    print(f'  RecoveryEvent.attempt_number:{rec.attempt_number}')
    print(f'  RecoveryEvent.notes:         {rec.notes}')
    sys.exit(0)

if __name__ == '__main__':
    main()
