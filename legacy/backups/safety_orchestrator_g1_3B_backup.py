"""
safety_orchestrator_g1.py
G1 ROS2 Pipeline — Safety Orchestrator Skeleton

Responsabilidad (ADR-002):
  - Owner exclusivo del compound state (Risk Level, Restriction Level)
  - Consume SafetyEvents desde /safety_events via event buffer
  - Evaluation loop dedicado — separado de callbacks ROS2
  - Publica /system_state, /safety_events, /safety_actions, /diagnostics

Estado: SKELETON — Capa 4
  - Threading architecture: IMPLEMENTADA (candado central ADR-002)
  - Compound state inicial: (SAFE, NONE)
  - Transition logic: NO — mock controlado únicamente
  - Arbitration (T8): NO — pendiente Capa 4 completa
  - Preemption real: NO — pendiente
  - Scheduler multi-priority: NO — pendiente
  - SDK / locomotion: NO — bloqueado

Arquitectura de threads (ADR-002 Sección 10):
  Thread 1 — ROS2 executor:
    - _on_safety_event(): ingest al buffer + notify — NADA MÁS
    - _on_heartbeat_timer(): publish diagnostics + notify
  Thread 2 — Evaluation loop (dedicado):
    - Drena event buffer
    - Procesa mock event
    - Publica /system_state, /safety_events, /safety_actions

NO hace desde callbacks:
  - Evaluación de transiciones
  - Modificación de compound state
  - Publishing de /system_state o /safety_actions
"""

import threading
import uuid
from collections import deque

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy, HistoryPolicy

from diagnostic_msgs.msg import DiagnosticArray, DiagnosticStatus, KeyValue
from g1_msgs.msg import SafetyEvent, SystemState, SafetyAction

# ---------------------------------------------------------------------------
# QoS profiles — ADR-002 Sección 4
# ---------------------------------------------------------------------------

QOS_SAFETY_EVENTS = QoSProfile(
    reliability=ReliabilityPolicy.RELIABLE,
    durability=DurabilityPolicy.VOLATILE,
    history=HistoryPolicy.KEEP_LAST,
    depth=50,
)

QOS_SYSTEM_STATE = QoSProfile(
    reliability=ReliabilityPolicy.RELIABLE,
    durability=DurabilityPolicy.TRANSIENT_LOCAL,
    history=HistoryPolicy.KEEP_LAST,
    depth=1,
)

QOS_SAFETY_ACTIONS = QoSProfile(
    reliability=ReliabilityPolicy.RELIABLE,
    durability=DurabilityPolicy.VOLATILE,
    history=HistoryPolicy.KEEP_LAST,
    depth=10,
)

QOS_DIAGNOSTICS = QoSProfile(
    reliability=ReliabilityPolicy.BEST_EFFORT,
    durability=DurabilityPolicy.VOLATILE,
    history=HistoryPolicy.KEEP_LAST,
    depth=10,
)

# ---------------------------------------------------------------------------
# Constantes — TBD hasta SDK G1
# ---------------------------------------------------------------------------

ORCHESTRATOR_HEARTBEAT_HZ = 1.0   # TBD — RESILIENCE_MODEL_G1.md Sección 6.2
EVENT_BUFFER_MAX = 100             # TBD — ADR-002 Sección 6.1
HARDWARE_ID = 'g1_ros2_pipeline'

# ---------------------------------------------------------------------------
# Compound state inicial — ADR-002 Sección 11.2
# ---------------------------------------------------------------------------

INITIAL_RISK_LEVEL = 'SAFE'
INITIAL_RESTRICTION_LEVEL = 'NONE'


class CompoundState:
    """
    Estado compuesto del sistema — ADR-002 Sección 11.1.
    Propiedad exclusiva del evaluation loop (Thread 2).
    Thread 1 nunca lee ni escribe este objeto directamente.
    """

    def __init__(self):
        self.risk_level = INITIAL_RISK_LEVEL
        self.restriction_level = INITIAL_RESTRICTION_LEVEL
        self.last_transition_id = ''
        self.execution_confidence = 'VERIFIED'
        self.arbitration_pending = False
        self.r5_committed = False

    def to_ros_msg(self, stamp):
        msg = SystemState()
        msg.risk_level = self.risk_level
        msg.restriction_level = self.restriction_level
        msg.last_transition_id = self.last_transition_id
        msg.execution_confidence = self.execution_confidence
        msg.timestamp = stamp
        msg.arbitration_pending = self.arbitration_pending
        msg.r5_committed = self.r5_committed
        return msg


class SafetyOrchestratorG1(Node):
    """
    Safety orchestrator skeleton para G1 ROS2 Pipeline.

    Skeleton Capa 4:
      - Threading architecture per ADR-002 implementada
      - Compound state inicial (SAFE, NONE)
      - Event buffer thread-safe con capacidad máxima
      - Evaluation loop en thread dedicado
      - Publishers /system_state (Transient Local), /safety_events,
        /safety_actions, /diagnostics
      - Subscriber /safety_events — ingest-only
      - Transition logic: mock controlado únicamente
    """

    def __init__(self):
        super().__init__('safety_orchestrator_g1')

        # Compound state — propiedad exclusiva de Thread 2
        self._state = CompoundState()

        # Event buffer — thread-safe (ADR-002 Sección 6.1)
        self._event_buffer = deque(maxlen=EVENT_BUFFER_MAX)
        self._buffer_lock = threading.Lock()
        self._evaluation_trigger = threading.Condition(self._buffer_lock)

        # Flag de shutdown para evaluation loop
        self._shutdown = False

        # Publishers
        self._pub_system_state = self.create_publisher(
            SystemState,
            '/system_state',
            QOS_SYSTEM_STATE,
        )

        self._pub_safety_events = self.create_publisher(
            SafetyEvent,
            '/safety_events',
            QOS_SAFETY_EVENTS,
        )

        self._pub_safety_actions = self.create_publisher(
            SafetyAction,
            '/safety_actions',
            QOS_SAFETY_ACTIONS,
        )

        self._pub_diagnostics = self.create_publisher(
            DiagnosticArray,
            '/diagnostics',
            QOS_DIAGNOSTICS,
        )

        # Subscriber — ingest-only (ADR-002 Sección 10 Candado C1)
        self._sub_safety_events = self.create_subscription(
            SafetyEvent,
            '/safety_events',
            self._on_safety_event,
            QOS_SAFETY_EVENTS,
        )

        # Timer — heartbeat + notify evaluation loop
        self._heartbeat_timer = self.create_timer(
            1.0 / ORCHESTRATOR_HEARTBEAT_HZ,
            self._on_heartbeat_timer,
        )

        # Publicar estado inicial en /system_state (Transient Local)
        self._publish_system_state()

        # Arrancar evaluation loop en thread dedicado (Thread 2)
        self._eval_thread = threading.Thread(
            target=self._evaluation_loop,
            name='orchestrator_eval_loop',
            daemon=True,
        )
        self._eval_thread.start()

        self.get_logger().info(
            'safety_orchestrator_g1 skeleton iniciado. '
            f'Compound state inicial: ({INITIAL_RISK_LEVEL}, {INITIAL_RESTRICTION_LEVEL}). '
            'Evaluation loop activo. Transition logic TBD.'
        )

    # -----------------------------------------------------------------------
    # Thread 1 — Callbacks ROS2 — INGEST ONLY
    # -----------------------------------------------------------------------

    def _on_safety_event(self, msg):
        """
        Callback de /safety_events — INGEST ONLY.
        ADR-002 Sección 10 Candado C1: ninguna lógica de evaluación aquí.
        Solo ingesta al buffer y notifica evaluation loop.

        Self-feedback guard: ignora eventos publicados por el orchestrator mismo
        para evitar loop infinito (ACK → buffer → ACK → buffer → ...).
        """
        if msg.source == 'safety_orchestrator_g1':
            return

        with self._evaluation_trigger:
            # Si buffer lleno, deque con maxlen descarta el oldest automáticamente
            dropped = len(self._event_buffer) >= EVENT_BUFFER_MAX
            self._event_buffer.append(msg)
            if dropped:
                self.get_logger().warn(
                    '[BUFFER] Event buffer al límite — oldest descartado. '
                    'ADR-002 Sección 6.1.'
                )
            self._evaluation_trigger.notify()

    def _on_heartbeat_timer(self):
        """
        Timer callback — publica diagnostics y notifica evaluation loop.
        ADR-002 Sección 5.3 — timer de watchdog interno del orchestrator.
        """
        self._publish_heartbeat()
        with self._evaluation_trigger:
            self._evaluation_trigger.notify()

    # -----------------------------------------------------------------------
    # Thread 2 — Evaluation loop dedicado
    # -----------------------------------------------------------------------

    def _evaluation_loop(self):
        """
        Loop de evaluación dedicado — ADR-002 Sección 5.2.
        Corre en thread separado del executor ROS2.
        Drena event buffer, procesa eventos, ejecuta transiciones.

        Skeleton: procesa mock event — transition logic real TBD.
        """
        self.get_logger().info('[EVAL LOOP] Iniciado en thread dedicado.')

        while not self._shutdown:
            # Esperar notificación (event o timer tick)
            with self._evaluation_trigger:
                self._evaluation_trigger.wait(timeout=2.0)

                # Drenar buffer — copiar eventos pendientes
                batch = []
                while self._event_buffer:
                    batch.append(self._event_buffer.popleft())

            if self._shutdown:
                break

            if not batch:
                # Timer tick sin eventos — solo confirmar que el loop sigue vivo
                continue

            # Procesar batch
            self._process_batch(batch)

    def _process_batch(self, batch):
        """
        Procesa un batch de SafetyEvents.
        SKELETON: log del evento recibido + publicar evidencia observable.
        Transition logic real: TBD — pendiente Capa 4 completa.
        """
        for event in batch:
            self.get_logger().info(
                f'[EVAL] Evento recibido — source: {event.source} '
                f'type: {event.event_type} '
                f'risk: {event.risk_level} '
                f'target: {event.target}'
            )

            # SKELETON: publicar SCHEDULED como evidencia observable
            # En runtime real: evaluar preconditions, clasificar por priority,
            # ejecutar transición ganadora, manejar T8.
            self._publish_event_ack(event)

        # Publicar compound state actual después de procesar batch
        self._publish_system_state()

    def _publish_event_ack(self, original_event):
        """
        Publica SafetyEvent SCHEDULED como ACK del evento recibido.
        SKELETON — en runtime real esto sería TRANSITION_EXECUTED, REJECTED, etc.
        """
        msg = SafetyEvent()
        msg.event_id = str(uuid.uuid4())
        msg.event_type = 'SCHEDULED'
        msg.source = 'safety_orchestrator_g1'
        msg.source_authority = 'PRIMARY'
        msg.authority_effectiveness = 'EFFECTIVE'
        msg.target = original_event.source
        msg.risk_level = self._state.risk_level
        msg.restriction_level = self._state.restriction_level
        msg.transition_id = ''
        msg.transition_priority = 'NORMAL'
        msg.execution_confidence = 'VERIFIED'
        msg.timestamp = self.get_clock().now().to_msg()
        msg.notes = (
            f'SKELETON ACK — evento recibido de {original_event.source}. '
            f'Transition logic TBD. original_event_id: {original_event.event_id}'
        )
        self._pub_safety_events.publish(msg)

    # -----------------------------------------------------------------------
    # Publishers — llamados desde Thread 2
    # -----------------------------------------------------------------------

    def _publish_system_state(self):
        """Publica compound state actual en /system_state (Transient Local)."""
        msg = self._state.to_ros_msg(self.get_clock().now().to_msg())
        self._pub_system_state.publish(msg)

    def _publish_heartbeat(self):
        """
        Publica DiagnosticArray con estado propio del orchestrator.
        Llamado desde Thread 1 (timer callback) — solo diagnostics, no state.
        """
        now = self.get_clock().now().to_msg()

        status = DiagnosticStatus()
        status.level = DiagnosticStatus.OK
        status.name = 'safety_orchestrator_g1'
        status.message = (
            f'SKELETON — compound state: '
            f'({self._state.risk_level}, {self._state.restriction_level})'
        )
        status.hardware_id = HARDWARE_ID
        status.values = [
            KeyValue(key='state', value='SKELETON'),
            KeyValue(key='risk_level', value=self._state.risk_level),
            KeyValue(key='restriction_level', value=self._state.restriction_level),
            KeyValue(key='arbitration_pending', value=str(self._state.arbitration_pending)),
            KeyValue(key='r5_committed', value=str(self._state.r5_committed)),
            KeyValue(key='eval_thread_alive', value=str(self._eval_thread.is_alive())),
        ]

        msg = DiagnosticArray()
        msg.header.stamp = now
        msg.status = [status]
        self._pub_diagnostics.publish(msg)

    # -----------------------------------------------------------------------
    # Shutdown
    # -----------------------------------------------------------------------

    def destroy_node(self):
        self._shutdown = True
        with self._evaluation_trigger:
            self._evaluation_trigger.notify_all()
        self._eval_thread.join(timeout=2.0)
        super().destroy_node()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main(args=None):
    rclpy.init(args=args)
    node = SafetyOrchestratorG1()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
