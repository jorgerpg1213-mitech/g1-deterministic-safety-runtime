#!/usr/bin/env python3
"""
Harness 4J-P1-B — Trazabilidad causal event_id
Workstream: B / All / All / E3 / C1 / P2

Hipótesis: SafetyEvent.event_id=FIXED_ID
           → SafetyAction.parent_event_id=FIXED_ID
           → RecoveryEvent.notes contiene parent_event_id=FIXED_ID

PASS:
  SafetyAction.parent_event_id == FIXED_ID exacto
  RecoveryEvent.notes contiene parent_event_id=FIXED_ID exacto

FAIL:
  parent_event_id vacío o distinto al ID fijo
  timeout
  notas ambiguas
"""
import rclpy, time, sys
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy, HistoryPolicy
from g1_msgs.msg import SafetyEvent, SafetyAction, RecoveryEvent

FIXED_EVENT_ID  = '4JP1B-TEST-001'
WARMUP_S        = 5.0
TIMEOUT_ACTION_S  = 8.0
TIMEOUT_RECOVERY_S = 8.0

reliable_qos = QoSProfile(
    reliability=ReliabilityPolicy.RELIABLE,
    durability=DurabilityPolicy.VOLATILE,
    history=HistoryPolicy.KEEP_LAST,
    depth=10,
)

class Harness4JP1B(Node):
    def __init__(self):
        super().__init__('harness_4j_p1b')
        self._pub_time        = None
        self._safety_actions  = []
        self._recovery_events = []

        self._pub = self.create_publisher(SafetyEvent, '/safety_events', reliable_qos)
        self._sub_action = self.create_subscription(
            SafetyAction, '/safety_actions', self._on_safety_action, reliable_qos)
        self._sub_recovery = self.create_subscription(
            RecoveryEvent, '/recovery_events', self._on_recovery_event, reliable_qos)
        self.get_logger().info('[4J-P1-B] Harness iniciado')

    def _on_safety_action(self, msg: SafetyAction):
        if self._pub_time is not None:
            self._safety_actions.append(msg)
            self.get_logger().warn(
                f'[4J-P1-B] SafetyAction: action={msg.action_name} '
                f'tx={msg.transition_id} '
                f'parent_event_id={msg.parent_event_id!r}')

    def _on_recovery_event(self, msg: RecoveryEvent):
        if self._pub_time is not None:
            self._recovery_events.append(msg)
            self.get_logger().info(
                f'[4J-P1-B] RecoveryEvent: action={msg.action_name} '
                f'notes={msg.notes!r}')

def main():
    rclpy.init()
    node = Harness4JP1B()

    # Warmup — orchestrator en /safety_events, recovery en /safety_actions
    node.get_logger().info(f'[4J-P1-B] Warmup {WARMUP_S}s...')
    t0 = time.monotonic()
    orch_ready = rec_ready = False
    while time.monotonic() - t0 < WARMUP_S:
        rclpy.spin_once(node, timeout_sec=0.1)
        if node.count_subscribers('/safety_events') > 0:
            orch_ready = True
        if node.count_subscribers('/safety_actions') > 0:
            rec_ready = True
        if orch_ready and rec_ready:
            node.get_logger().info('[4J-P1-B] [Iniciado] — orchestrator y recovery_g1 activos')
            break

    if not orch_ready:
        print('FAIL — orchestrator no detectado en /safety_events')
        node.destroy_node(); rclpy.shutdown(); sys.exit(1)
    if not rec_ready:
        print('FAIL — recovery_g1 no detectado en /safety_actions')
        node.destroy_node(); rclpy.shutdown(); sys.exit(1)

    # Publicar SafetyEvent con event_id fijo conocido
    msg = SafetyEvent()
    msg.event_id                = FIXED_EVENT_ID
    msg.event_type              = 'CONDITION_DETECTED'
    msg.source                  = 'cross_consistency_observer'
    msg.source_authority        = 'SECONDARY'
    msg.authority_effectiveness = 'EFFECTIVE'
    msg.target                  = 'imu_contact_support'
    msg.risk_level              = 'SAFE'
    msg.restriction_level       = 'NONE'
    msg.execution_confidence    = 'BEST_EFFORT'
    msg.timestamp               = node.get_clock().now().to_msg()
    msg.notes                   = f'4J-P1-B harness event_id={FIXED_EVENT_ID}'

    node._pub_time = time.monotonic()
    node.get_logger().warn(
        f'[4J-P1-B] Publicando SafetyEvent event_id={FIXED_EVENT_ID}')
    node._pub.publish(msg)

    # Esperar SafetyAction
    t1 = time.monotonic()
    while not node._safety_actions and (time.monotonic() - t1) < TIMEOUT_ACTION_S:
        rclpy.spin_once(node, timeout_sec=0.1)

    if not node._safety_actions:
        print('FAIL — timeout: orchestrator no emitió SafetyAction')
        node.destroy_node(); rclpy.shutdown(); sys.exit(1)

    # Esperar RecoveryEvent
    t2 = time.monotonic()
    while not node._recovery_events and (time.monotonic() - t2) < TIMEOUT_RECOVERY_S:
        rclpy.spin_once(node, timeout_sec=0.1)

    node.destroy_node(); rclpy.shutdown()

    if not node._recovery_events:
        print('FAIL — timeout: recovery_g1 no publicó RecoveryEvent')
        sys.exit(1)

    failures = []

    # Validar SafetyAction.parent_event_id == FIXED_EVENT_ID exacto
    act = node._safety_actions[0]
    if act.parent_event_id != FIXED_EVENT_ID:
        failures.append(
            f'  SafetyAction.parent_event_id={act.parent_event_id!r} '
            f'(esperado {FIXED_EVENT_ID!r})')

    # Validar RecoveryEvent.notes contiene parent_event_id=FIXED_EVENT_ID exacto
    rec_candidates = [r for r in node._recovery_events if r.action_name == 'stabilization_mode']
    if not rec_candidates:
        failures.append(
            f'  No RecoveryEvent con action_name=stabilization_mode '
            f'(recibidos: {[r.action_name for r in node._recovery_events]})')
    else:
        rec = rec_candidates[0]
        expected_trace = f'parent_event_id={FIXED_EVENT_ID}'
        if expected_trace not in rec.notes:
            failures.append(
                f'  RecoveryEvent.notes no contiene {expected_trace!r}: {rec.notes!r}')

    if failures:
        print('FAIL — trazabilidad event_id incompleta:')
        for f in failures: print(f)
        sys.exit(1)

    rec = rec_candidates[0]
    print('PASS — trazabilidad causal event_id verificada')
    print(f'  SafetyEvent.event_id:          {FIXED_EVENT_ID}')
    print(f'  SafetyAction.parent_event_id:  {act.parent_event_id}')
    print(f'  RecoveryEvent.notes:           {rec.notes}')
    sys.exit(0)

if __name__ == '__main__':
    main()
