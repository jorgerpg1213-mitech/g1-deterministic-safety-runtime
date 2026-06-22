#!/usr/bin/env python3
"""
Harness 4J-P0-B — Integración mínima cadena gobernada TX-011
Workstream: A / F3+F4 / R1 / E3 / C0 / P4

Diseño de aislamiento (Opción A):
  recovery_g1 lanzado con --remap /safety_events:=/safety_events_null
  Solo puede reaccionar a /safety_actions — ruta directa bloqueada.
  Un solo consumidor de /safety_events: orchestrator.
  Una sola variable causal.

Precondición de topología verificada manualmente antes de ejecutar:
  /safety_events   → subscriber: safety_orchestrator_g1 SOLAMENTE
  /safety_actions  → subscriber: recovery_g1

Cadena validada:
  SafetyEvent(CONDITION_DETECTED + SECONDARY + EFFECTIVE)
  → orchestrator emite SafetyAction(stabilization_mode, TX-011, AUTONOMOUS)
  → recovery_g1 publica RecoveryEvent(stabilization_mode, REC-AUTO, SUCCESS)

PASS:
  SafetyAction: action_name=stabilization_mode, transition_id=TX-011, authority=AUTONOMOUS
  RecoveryEvent: action_name=stabilization_mode, recovery_type=REC-AUTO,
                 result=SUCCESS, attempt_number=1,
                 notes contiene governed_TX011 + physical recovery not claimed

FAIL:
  timeout en SafetyAction o RecoveryEvent
  action_name incorrecto en cualquier eslabón
  recovery cae a operator_intervention
"""
import rclpy, time, sys
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy, HistoryPolicy
from g1_msgs.msg import SafetyEvent, SafetyAction, RecoveryEvent

WARMUP_S           = 5.0
TIMEOUT_ACTION_S   = 8.0
TIMEOUT_RECOVERY_S = 8.0

reliable_qos = QoSProfile(
    reliability=ReliabilityPolicy.RELIABLE,
    durability=DurabilityPolicy.VOLATILE,
    history=HistoryPolicy.KEEP_LAST,
    depth=10,
)

class Harness4JP0B(Node):
    def __init__(self):
        super().__init__('harness_4j_p0b')
        self._pub_time        = None
        self._safety_actions  = []
        self._recovery_events = []

        self._pub = self.create_publisher(SafetyEvent, '/safety_events', reliable_qos)
        self._sub_action = self.create_subscription(
            SafetyAction, '/safety_actions', self._on_safety_action, reliable_qos)
        self._sub_recovery = self.create_subscription(
            RecoveryEvent, '/recovery_events', self._on_recovery_event, reliable_qos)
        self.get_logger().info('[4J-P0-B] Harness iniciado')

    def _on_safety_action(self, msg: SafetyAction):
        if self._pub_time is not None:
            self._safety_actions.append(msg)
            self.get_logger().warn(
                f'[4J-P0-B] SafetyAction: action={msg.action_name} '
                f'tx={msg.transition_id} authority={msg.execution_authority}')

    def _on_recovery_event(self, msg: RecoveryEvent):
        if self._pub_time is not None:
            self._recovery_events.append(msg)
            self.get_logger().info(
                f'[4J-P0-B] RecoveryEvent: action={msg.action_name} '
                f'recovery_type={msg.recovery_type} result={msg.result}')

def main():
    rclpy.init()
    node = Harness4JP0B()

    # Warmup — verificar orchestrator en /safety_events Y recovery_g1 en /safety_actions
    # Topología ya verificada manualmente con ros2 topic info -v antes de ejecutar
    node.get_logger().info(f'[4J-P0-B] Warmup {WARMUP_S}s — esperando ambos nodos...')
    t0 = time.monotonic()
    orch_ready = False
    rec_ready  = False
    while time.monotonic() - t0 < WARMUP_S:
        rclpy.spin_once(node, timeout_sec=0.1)
        if node.count_subscribers('/safety_events') > 0:
            orch_ready = True
        if node.count_subscribers('/safety_actions') > 0:
            rec_ready = True
        if orch_ready and rec_ready:
            node.get_logger().info('[4J-P0-B] [Iniciado] — orchestrator y recovery_g1 activos')
            break

    if not orch_ready:
        print('FAIL — orchestrator no detectado en /safety_events tras warmup')
        node.destroy_node(); rclpy.shutdown(); sys.exit(1)
    if not rec_ready:
        print('FAIL — recovery_g1 no detectado en /safety_actions tras warmup')
        node.destroy_node(); rclpy.shutdown(); sys.exit(1)

    # Publicar SafetyEvent que dispara TX-011
    # Sin event_id — correlación por event_id pertenece a 4J-P1
    msg = SafetyEvent()
    msg.event_type              = 'CONDITION_DETECTED'
    msg.source                  = 'cross_consistency_observer'
    msg.source_authority        = 'SECONDARY'
    msg.authority_effectiveness = 'EFFECTIVE'
    msg.target                  = 'imu_contact_support'
    msg.risk_level              = 'SAFE'
    msg.restriction_level       = 'NONE'
    msg.execution_confidence    = 'BEST_EFFORT'
    msg.timestamp               = node.get_clock().now().to_msg()
    msg.notes                   = '4J-P0-B harness injection TX-011'

    node._pub_time = time.monotonic()
    node.get_logger().warn(
        '[4J-P0-B] Publicando SafetyEvent: CONDITION_DETECTED/SECONDARY/EFFECTIVE')
    node._pub.publish(msg)

    # Esperar SafetyAction del orchestrator
    t1 = time.monotonic()
    while not node._safety_actions and (time.monotonic() - t1) < TIMEOUT_ACTION_S:
        rclpy.spin_once(node, timeout_sec=0.1)

    if not node._safety_actions:
        print('FAIL — timeout: orchestrator no emitió SafetyAction')
        node.destroy_node(); rclpy.shutdown(); sys.exit(1)

    # Esperar RecoveryEvent de recovery_g1
    t2 = time.monotonic()
    while not node._recovery_events and (time.monotonic() - t2) < TIMEOUT_RECOVERY_S:
        rclpy.spin_once(node, timeout_sec=0.1)

    node.destroy_node(); rclpy.shutdown()

    if not node._recovery_events:
        print('FAIL — timeout: recovery_g1 no publicó RecoveryEvent')
        sys.exit(1)

    # Validar SafetyAction
    act = node._safety_actions[0]
    failures = []
    if act.action_name != 'stabilization_mode':
        failures.append(
            f'  SafetyAction.action_name={act.action_name!r} (esperado "stabilization_mode")')
    if act.transition_id != 'TX-011':
        failures.append(
            f'  SafetyAction.transition_id={act.transition_id!r} (esperado "TX-011")')
    if act.execution_authority != 'AUTONOMOUS':
        failures.append(
            f'  SafetyAction.execution_authority={act.execution_authority!r} (esperado "AUTONOMOUS")')

    # Validar RecoveryEvent — filtrar por stabilization_mode
    rec_candidates = [r for r in node._recovery_events if r.action_name == 'stabilization_mode']
    if not rec_candidates:
        failures.append(
            f'  No RecoveryEvent con action_name=stabilization_mode '
            f'(recibidos: {[r.action_name for r in node._recovery_events]})')
    else:
        rec = rec_candidates[0]
        if rec.recovery_type != 'REC-AUTO':
            failures.append(
                f'  RecoveryEvent.recovery_type={rec.recovery_type!r} (esperado "REC-AUTO")')
        if rec.result != 'SUCCESS':
            failures.append(
                f'  RecoveryEvent.result={rec.result!r} (esperado "SUCCESS")')
        if rec.attempt_number != 1:
            failures.append(
                f'  RecoveryEvent.attempt_number={rec.attempt_number} (esperado 1)')
        if 'governed_TX011' not in rec.notes:
            failures.append(
                f'  RecoveryEvent.notes no contiene "governed_TX011": {rec.notes!r}')
        if 'physical recovery not claimed' not in rec.notes:
            failures.append(
                f'  RecoveryEvent.notes no contiene "physical recovery not claimed": {rec.notes!r}')

    if failures:
        print('FAIL — cadena gobernada TX-011 incompleta o incorrecta:')
        for f in failures: print(f)
        sys.exit(1)

    rec = rec_candidates[0]
    print('PASS — cadena gobernada TX-011 completa y correcta')
    print(f'  SafetyAction.action_name:         {act.action_name}')
    print(f'  SafetyAction.transition_id:       {act.transition_id}')
    print(f'  SafetyAction.execution_authority: {act.execution_authority}')
    print(f'  RecoveryEvent.action_name:        {rec.action_name}')
    print(f'  RecoveryEvent.recovery_type:      {rec.recovery_type}')
    print(f'  RecoveryEvent.result:             {rec.result}')
    print(f'  RecoveryEvent.attempt_number:     {rec.attempt_number}')
    print(f'  RecoveryEvent.notes:              {rec.notes}')
    sys.exit(0)

if __name__ == '__main__':
    main()
