#!/usr/bin/env python3
"""
Harness 4J-P0 — Validación focal DT-4I-001
Workstream: A / F3+F4 / R1 / E2 / C0 / P1+P4

Hipótesis: TX-011 gobernada ejecuta stabilization_mode en recovery_g1
           sin caer a operator_intervention.

PASS:
  action_name=stabilization_mode
  recovery_type=REC-AUTO
  result=SUCCESS
  attempt_number=1
  notes contiene 'governed_TX011' y 'physical recovery not claimed'

FAIL:
  operator_intervention
  recovery_type fuera de contrato
  timeout
  notes ambiguas
  attempt != 1
"""
import rclpy, time, sys
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy, HistoryPolicy
from g1_msgs.msg import SafetyAction, RecoveryEvent

WARMUP_S  = 3.0
TIMEOUT_S = 10.0

reliable_qos = QoSProfile(
    reliability=ReliabilityPolicy.RELIABLE,
    durability=DurabilityPolicy.VOLATILE,
    history=HistoryPolicy.KEEP_LAST,
    depth=10,
)

class Harness4JP0(Node):
    def __init__(self):
        super().__init__('harness_4j_p0')
        self._events_post_pub = []
        self._pub_time = None
        self._pub = self.create_publisher(SafetyAction, '/safety_actions', reliable_qos)
        self._sub = self.create_subscription(
            RecoveryEvent, '/recovery_events', self._on_recovery_event, reliable_qos)
        self.get_logger().info('[4J-P0] Harness iniciado')

    def _on_recovery_event(self, msg: RecoveryEvent):
        if self._pub_time is not None:
            self._events_post_pub.append(msg)
            self.get_logger().info(
                f'[4J-P0] RecoveryEvent recibido: '
                f'action={msg.action_name} '
                f'recovery_type={msg.recovery_type} '
                f'result={msg.result} '
                f'attempt={msg.attempt_number}')

def main():
    rclpy.init()
    node = Harness4JP0()

    # Warmup — esperar subscriber activo en /safety_actions (anti-pattern #74)
    node.get_logger().info(f'[4J-P0] Warmup {WARMUP_S}s...')
    t0 = time.monotonic()
    while time.monotonic() - t0 < WARMUP_S:
        rclpy.spin_once(node, timeout_sec=0.1)
        if node.count_subscribers('/safety_actions') > 0:
            node.get_logger().info('[4J-P0] [Iniciado] — subscriber activo en /safety_actions')
            break
    else:
        print('FAIL — no se detectó subscriber en /safety_actions tras warmup')
        node.destroy_node(); rclpy.shutdown(); sys.exit(1)

    # Publicar SafetyAction gobernada TX-011
    msg = SafetyAction()
    msg.action_name         = 'stabilization_mode'
    msg.transition_id       = 'TX-011'
    msg.execution_authority = 'AUTONOMOUS'
    msg.timestamp           = node.get_clock().now().to_msg()
    node._pub_time = time.monotonic()
    node.get_logger().warn(
        '[4J-P0] Publicando SafetyAction: stabilization_mode / TX-011 / AUTONOMOUS')
    node._pub.publish(msg)

    # Esperar RecoveryEvent con timeout
    t1 = time.monotonic()
    while not node._events_post_pub and (time.monotonic() - t1) < TIMEOUT_S:
        rclpy.spin_once(node, timeout_sec=0.1)

    node.destroy_node(); rclpy.shutdown()

    if not node._events_post_pub:
        print('FAIL — timeout: no se recibió RecoveryEvent tras publicación TX-011')
        sys.exit(1)

    evt = node._events_post_pub[0]
    failures = []
    if evt.action_name != 'stabilization_mode':
        failures.append(f'  action_name={evt.action_name!r} (esperado "stabilization_mode")')
    if evt.recovery_type != 'REC-AUTO':
        failures.append(f'  recovery_type={evt.recovery_type!r} (esperado "REC-AUTO")')
    if evt.result != 'SUCCESS':
        failures.append(f'  result={evt.result!r} (esperado "SUCCESS")')
    if evt.attempt_number != 1:
        failures.append(f'  attempt_number={evt.attempt_number} (esperado 1)')
    if 'governed_TX011' not in evt.notes:
        failures.append(f'  notes no contiene "governed_TX011": {evt.notes!r}')
    if 'physical recovery not claimed' not in evt.notes:
        failures.append(f'  notes no contiene "physical recovery not claimed": {evt.notes!r}')

    if failures:
        print('FAIL — RecoveryEvent recibido pero campos incorrectos:')
        for f in failures: print(f)
        sys.exit(1)

    print('PASS — TX-011 gobernada ejecuta stabilization_mode en recovery_g1')
    print(f'  action_name:    {evt.action_name}')
    print(f'  recovery_type:  {evt.recovery_type}')
    print(f'  result:         {evt.result}')
    print(f'  attempt_number: {evt.attempt_number}')
    print(f'  notes:          {evt.notes}')
    sys.exit(0)

if __name__ == '__main__':
    main()
