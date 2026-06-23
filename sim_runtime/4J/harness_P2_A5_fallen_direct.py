"""
Harness 4J-P2-A5 — Fallen direct fallback (R2 Direct)
Workstream: B / F3 / R2 / E3 / C1 / P3

Hipotesis: SafetyEvent(source=cross_consistency_observer, event_id=FIXED_ID)
           via ruta directa R2 -> recovery_g1
           -> RecoveryEvent action_name=wait_for_primary_restore,
             recovery_type=REC-AUTO,
             notes contiene parent_event_id=FIXED_ID

Limitacion declarada: weak fallback. risk_level=CAUTION restriction_level=R2 para aislar ruta fallback directa y evitar bloqueo por precondicion universal.
No reclama recuperacion fisica. Ruta primaria es R1/TX-011.

PASS:
  action_name=wait_for_primary_restore
  recovery_type=REC-AUTO
  notes contiene parent_event_id=4JP2-A5-FALLEN-001

FAIL:
  timeout, operator_intervention, missing parent_event_id,
  recovery_type!=REC-AUTO, topologia sucia
"""
import rclpy, time, sys
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy, HistoryPolicy
from g1_msgs.msg import SafetyEvent, RecoveryEvent

FIXED_ID  = '4JP2-A5-FALLEN-001'
WARMUP_S  = 5.0
TIMEOUT_S = 10.0

reliable_qos = QoSProfile(
    reliability=ReliabilityPolicy.RELIABLE,
    durability=DurabilityPolicy.VOLATILE,
    history=HistoryPolicy.KEEP_LAST,
    depth=10,
)

class HarnessP2A5FallenDirect(Node):
    def __init__(self):
        super().__init__('harness_p2_a5_fallen_direct')
        self._pub_time = None
        self._events   = []
        self._pub = self.create_publisher(SafetyEvent, '/safety_events', reliable_qos)
        self.create_subscription(RecoveryEvent, '/recovery_events', self._on_rec, reliable_qos)
        self.get_logger().info('[P2-A5-FALLEN] Harness iniciado')

    def _on_rec(self, msg: RecoveryEvent):
        if self._pub_time is not None:
            if f'parent_event_id={FIXED_ID}' in (msg.notes or ''):
                self._events.append(msg)
                self.get_logger().info(
                    f'[P2-A5-FALLEN] RecoveryEvent: action={msg.action_name} '
                    f'type={msg.recovery_type} attempt={msg.attempt_number} '
                    f'notes={msg.notes!r}')

def main():
    rclpy.init()
    node = HarnessP2A5FallenDirect()

    node.get_logger().info(f'[P2-A5-FALLEN] Warmup {WARMUP_S}s...')
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

    node.get_logger().info('[P2-A5-FALLEN] [Iniciado] -- 1 subscriber en /safety_events')

    msg = SafetyEvent()
    msg.event_id                = FIXED_ID
    msg.event_type              = 'CONDITION_DETECTED'
    msg.source                  = 'cross_consistency_observer'
    msg.source_authority        = 'SECONDARY'
    msg.authority_effectiveness = 'EFFECTIVE'
    msg.target                  = '/g1/imu'
    msg.risk_level              = 'CAUTION'
    msg.restriction_level       = 'R2'
    msg.transition_id           = ''
    msg.transition_priority     = 'NORMAL'
    msg.execution_confidence    = 'BEST_EFFORT'
    msg.notes                   = f'4J-P2-A5 fallen direct fallback harness event_id={FIXED_ID}'
    msg.timestamp               = node.get_clock().now().to_msg()

    node._pub_time = time.monotonic()
    node.get_logger().warn(
        f'[P2-A5-FALLEN] Publicando SafetyEvent fallen direct event_id={FIXED_ID}')
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
    if rec.action_name != 'wait_for_primary_restore':
        failures.append(
            f'  action_name={rec.action_name!r} (esperado "wait_for_primary_restore")')
    if rec.recovery_type != 'REC-AUTO':
        failures.append(
            f'  recovery_type={rec.recovery_type!r} (esperado "REC-AUTO")')
    if f'parent_event_id={FIXED_ID}' not in (rec.notes or ''):
        failures.append(
            f'  notes no contiene "parent_event_id={FIXED_ID}": {rec.notes!r}')

    if failures:
        print('FAIL -- RecoveryEvent incorrecto:')
        for f in failures: print(f)
        sys.exit(1)

    print('PASS -- Fallen direct fallback verificado (weak fallback)')
    print('  LIMITACION: no reclama recuperacion fisica. Ruta primaria es R1/TX-011.')
    print(f'  SafetyEvent.event_id:        {FIXED_ID}')
    print(f'  RecoveryEvent.action_name:   {rec.action_name}')
    print(f'  RecoveryEvent.recovery_type: {rec.recovery_type}')
    print(f'  RecoveryEvent.notes:         {rec.notes}')
    sys.exit(0)

if __name__ == '__main__':
    main()
