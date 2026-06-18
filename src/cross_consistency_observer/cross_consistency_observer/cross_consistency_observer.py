"""
cross_consistency_observer.py
G1 ROS2 Pipeline — Cross-Consistency Observer Skeleton

Responsabilidad (ADR-003):
  - Detectar incoherencia entre fuentes de autoridad PRIMARY simultáneamente activas
  - Publicar SafetyEvent en /safety_events cuando se detecta incoherencia
  - Publicar heartbeat propio en /diagnostics

Estado: SKELETON — Capa 4
  - Suscribe a /imu y /joint_states (topics PRIMARY)
  - Lógica real de coherencia: TBD — pending SDK G1 + thresholds reales
  - Este skeleton verifica que los topics llegan y publica mock event controlado
  - Anti-flood por par de fuentes: implementado via rate limiting

  4D-3C2a (input readiness, NO detección):
  - Suscribe además /g1/contact/left y /g1/contact/right (g1_msgs/FootContact)
  - Guarda orientación IMU real (wxyz) y estado de contacto por pie
  - Loguea snapshot conjunto a ~1 Hz (solo lectura/log)
  - NO evalúa coherencia, NO emite SafetyEvent real, NO toca el mock

NO hace:
  - Decidir transiciones (eso es safety_orchestrator_g1)
  - Ejecutar acciones de seguridad (eso es safety_orchestrator_g1)
  - Modificar /system_state (eso es safety_orchestrator_g1)
  - Detectar timeouts de topics individuales (eso es watchdog_g1)

Pares monitoreados (ADR-003 Sección 3):
  - /imu <-> /joint_states       — ACTIVO skeleton
  - /imu <-> /foot_contact       — input readiness activo (3C2a); coherencia TBD
  - /joint_states <-> /foot_contact — TBD pending SDK G1
"""

import uuid

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy, HistoryPolicy

from diagnostic_msgs.msg import DiagnosticArray, DiagnosticStatus, KeyValue
from sensor_msgs.msg import Imu, JointState
from g1_msgs.msg import SafetyEvent, FootContact

# ---------------------------------------------------------------------------
# QoS profiles — ADR-003 + RESILIENCE_MODEL_G1.md
# ---------------------------------------------------------------------------

QOS_SAFETY_EVENTS = QoSProfile(
    reliability=ReliabilityPolicy.RELIABLE,
    durability=DurabilityPolicy.VOLATILE,
    history=HistoryPolicy.KEEP_LAST,
    depth=50,
)

QOS_DIAGNOSTICS = QoSProfile(
    reliability=ReliabilityPolicy.BEST_EFFORT,
    durability=DurabilityPolicy.VOLATILE,
    history=HistoryPolicy.KEEP_LAST,
    depth=10,
)

QOS_SENSOR = QoSProfile(
    reliability=ReliabilityPolicy.BEST_EFFORT,
    durability=DurabilityPolicy.VOLATILE,
    history=HistoryPolicy.KEEP_LAST,
    depth=10,
)

# ---------------------------------------------------------------------------
# Constantes — TBD hasta SDK G1
# ---------------------------------------------------------------------------

OBSERVER_HEARTBEAT_HZ = 1.0       # TBD — RESILIENCE_MODEL_G1.md Sección 6.2
OBSERVER_MAX_PUBLISH_HZ = 1.0     # Anti-flood — ADR-003 Sección 6
MOCK_EVENT_INTERVAL_S = 15.0      # Solo skeleton — mock event controlado
SNAPSHOT_LOG_HZ = 1.0             # 4D-3C2a — log de input readiness (solo lectura)
# 4D-3C2b - umbrales regla fallen/no-support (pragmaticos, declarados)
FRESH_MAX_AGE_S = 0.5          # frescura obligatoria (ages vivos 0.02-0.11s)
# 4F-P1: umbrales con severidad (pragmaticos, calibrables — DT-4D-016)
FALLEN_W_CRITICAL = 0.80       # CRITICAL: inclinacion fuerte sostenida
FALLEN_W_WARN     = 0.85       # WARN: inclinacion moderada
FALLEN_CONSECUTIVE_N = 3       # muestras frescas consecutivas (~3s a 1Hz)
HARDWARE_ID = 'g1_ros2_pipeline'


class CrossConsistencyObserver(Node):
    """
    Cross-consistency observer skeleton para G1 ROS2 Pipeline.

    Skeleton Capa 4:
      - Suscribe a /imu y /joint_states
      - Registra timestamps de último mensaje por topic
      - Publica heartbeat en /diagnostics
      - Publica SafetyEvent mock controlado
      - Lógica real de coherencia: TBD pending SDK G1

    4D-3C2a (input readiness):
      - Suscribe /g1/contact/left y /g1/contact/right
      - Guarda orientación IMU real + estado de contacto por pie
      - Loguea snapshot conjunto a ~1 Hz (sin evaluar coherencia)
    """

    def __init__(self):
        super().__init__('cross_consistency_observer')

        # Estado interno — timestamps de última recepción por topic
        # Usado por lógica futura de coherencia — no por skeleton mock
        self._last_imu_stamp = None
        self._last_joint_states_stamp = None

        # 4D-3C2a — input readiness: datos reales para la futura regla
        self._last_imu_orientation = None      # tuple (w, x, y, z) o None
        self._last_left_contact = None         # dict {in_contact, force, number_of_contacts} o None
        self._last_right_contact = None        # dict {in_contact, force, number_of_contacts} o None
        self._last_left_contact_stamp = None
        self._last_right_contact_stamp = None
        # 4D-3C2b - estado de la regla fallen/no-support
        self._fallen_consecutive = 0
        self._fallen_latched = False

        # Anti-flood — timestamp de último evento publicado por par
        self._last_event_published = {}

        # Publishers
        self._pub_safety_events = self.create_publisher(
            SafetyEvent,
            '/safety_events',
            QOS_SAFETY_EVENTS,
        )

        self._pub_diagnostics = self.create_publisher(
            DiagnosticArray,
            '/diagnostics',
            QOS_DIAGNOSTICS,
        )

        # Subscribers — fuentes PRIMARY (ADR-003 Sección 3)
        # /imu — PRIMARY: balance y postura
        self._sub_imu = self.create_subscription(
            Imu,
            '/imu',
            self._on_imu,
            QOS_SENSOR,
        )

        # /joint_states — PRIMARY: integridad articular
        self._sub_joint_states = self.create_subscription(
            JointState,
            '/joint_states',
            self._on_joint_states,
            QOS_SENSOR,
        )

        # 4D-3C2a — senales fisicas observadas para futura coherencia
        # (g1_msgs/FootContact, contrato 3B4B). NO declaradas PRIMARY hasta 3C2b.
        self._sub_contact_left = self.create_subscription(
            FootContact,
            '/g1/contact/left',
            self._on_contact_left,
            QOS_SENSOR,
        )

        self._sub_contact_right = self.create_subscription(
            FootContact,
            '/g1/contact/right',
            self._on_contact_right,
            QOS_SENSOR,
        )

        # Timer — heartbeat propio
        self._heartbeat_timer = self.create_timer(
            1.0 / OBSERVER_HEARTBEAT_HZ,
            self._publish_heartbeat,
        )

        # Timer — mock event controlado (solo skeleton)
        # 4D-3C2b: mock DESACTIVADO - la regla real lo reemplaza (no contaminar evidencia)
        # self._mock_event_timer = self.create_timer(MOCK_EVENT_INTERVAL_S, ...)  # OFF

        # Timer — 4D-3C2a snapshot de input readiness (solo log, sin lógica)
        self._input_snapshot_timer = self.create_timer(
            1.0 / SNAPSHOT_LOG_HZ,
            self._log_input_snapshot,
        )

        self.get_logger().info(
            'cross_consistency_observer skeleton iniciado. '
            'Suscrito a /imu, /joint_states, /g1/contact/left, /g1/contact/right. '
            'Lógica real de coherencia TBD — pending SDK G1.'
        )

    # -----------------------------------------------------------------------
    # Callbacks de sensores — solo ingest, sin lógica pesada
    # -----------------------------------------------------------------------

    def _on_imu(self, msg):
        """Ingest /imu — registra timestamp y orientación (wxyz). Sin lógica de coherencia."""
        self._last_imu_stamp = self.get_clock().now()
        q = msg.orientation
        self._last_imu_orientation = (q.w, q.x, q.y, q.z)

    def _on_joint_states(self, msg):
        """Ingest /joint_states — registra timestamp. Sin lógica de coherencia todavía."""
        self._last_joint_states_stamp = self.get_clock().now()

    def _on_contact_left(self, msg):
        """Ingest /g1/contact/left — guarda estado tipado. Sin lógica de coherencia (3C2a)."""
        self._last_left_contact_stamp = self.get_clock().now()
        self._last_left_contact = {
            'in_contact': msg.in_contact,
            'force': msg.force,
            'number_of_contacts': msg.number_of_contacts,
        }

    def _on_contact_right(self, msg):
        """Ingest /g1/contact/right — guarda estado tipado. Sin lógica de coherencia (3C2a)."""
        self._last_right_contact_stamp = self.get_clock().now()
        self._last_right_contact = {
            'in_contact': msg.in_contact,
            'force': msg.force,
            'number_of_contacts': msg.number_of_contacts,
        }

    # -----------------------------------------------------------------------
    # Heartbeat — /diagnostics
    # -----------------------------------------------------------------------

    def _publish_heartbeat(self):
        """
        Publica DiagnosticArray con estado propio del observer.
        Detectable externamente via ausencia de heartbeat.
        Ver ADR-003 Sección 4 — observer publica /diagnostics propio.
        """
        now = self.get_clock().now().to_msg()

        imu_seen = 'YES' if self._last_imu_stamp is not None else 'NO'
        joint_seen = 'YES' if self._last_joint_states_stamp is not None else 'NO'
        left_seen = 'YES' if self._last_left_contact is not None else 'NO'
        right_seen = 'YES' if self._last_right_contact is not None else 'NO'

        status = DiagnosticStatus()
        status.level = DiagnosticStatus.OK
        status.name = 'cross_consistency_observer'
        status.message = 'SKELETON — heartbeat activo. Coherencia real TBD.'
        status.hardware_id = HARDWARE_ID
        status.values = [
            KeyValue(key='state', value='SKELETON'),
            KeyValue(key='imu_seen', value=imu_seen),
            KeyValue(key='joint_states_seen', value=joint_seen),
            KeyValue(key='left_contact_seen', value=left_seen),
            KeyValue(key='right_contact_seen', value=right_seen),
            KeyValue(key='sdk_required', value='true'),
        ]

        msg = DiagnosticArray()
        msg.header.stamp = now
        msg.status = [status]

        self._pub_diagnostics.publish(msg)

    # -----------------------------------------------------------------------
    # 4D-3C2a — Snapshot de input readiness (solo log, sin lógica)
    # -----------------------------------------------------------------------

    def _log_input_snapshot(self):
        """
        Loguea un snapshot conjunto de las entradas reales para la futura regla.
        SOLO LECTURA — no evalúa coherencia, no emite SafetyEvent.
        """
        now = self.get_clock().now()

        def _age_s(stamp):
            """Edad en segundos desde el último mensaje, o None si nunca llegó."""
            if stamp is None:
                return None
            return (now - stamp).nanoseconds / 1e9

        ori = self._last_imu_orientation
        imu_age = _age_s(self._last_imu_stamp)
        if ori is not None:
            ori_str = (
                f'w={ori[0]:.3f} x={ori[1]:.3f} y={ori[2]:.3f} z={ori[3]:.3f} '
                f'age={imu_age:.2f}s'
            )
        else:
            ori_str = 'NONE'

        left = self._last_left_contact
        left_age = _age_s(self._last_left_contact_stamp)
        if left is not None:
            left_str = (
                f"in={left['in_contact']} f={left['force']:.3f} "
                f"n={left['number_of_contacts']} age={left_age:.2f}s"
            )
        else:
            left_str = 'NONE'

        right = self._last_right_contact
        right_age = _age_s(self._last_right_contact_stamp)
        if right is not None:
            right_str = (
                f"in={right['in_contact']} f={right['force']:.3f} "
                f"n={right['number_of_contacts']} age={right_age:.2f}s"
            )
        else:
            right_str = 'NONE'

        self.get_logger().info(
            f'[3C2a SNAPSHOT] imu_wxyz: {ori_str} | '
            f'left: {left_str} | right: {right_str}'
        )

        # 4D-3C2b - evaluar regla con las entradas ya calculadas
        self._evaluate_fallen_rule(ori, imu_age, left, left_age, right, right_age)

    # -----------------------------------------------------------------------
    # Mock SafetyEvent — solo skeleton
    # -----------------------------------------------------------------------

    # -----------------------------------------------------------------------
    # 4D-3C2b - Regla real fallen/no-support (reemplaza el mock)
    # -----------------------------------------------------------------------

    def _evaluate_fallen_rule(self, ori, imu_age, left, left_age, right, right_age):
        """4F-P1: regla con severidad INFO/WARN/CRITICAL.
        INFO  = abs_w>=FALLEN_W_WARN (0.85) + ambos pies en contacto.
        WARN  = inclinacion moderada (FALLEN_W_CRITICAL<=abs_w<FALLEN_W_WARN, 0.80<=abs_w<0.85) O un pie perdido.
        CRITICAL = inclinacion fuerte (abs_w<FALLEN_W_CRITICAL, 0.80) O ambos pies perdidos.
        CRITICAL dispara aunque un pie siga en contacto (contacto residual != soporte sano).
        Freshness obligatorio. Umbrales pragmaticos calibrables (DT-4D-016)."""
        fresh = (
            ori is not None and imu_age is not None and imu_age <= FRESH_MAX_AGE_S
            and left is not None and left_age is not None and left_age <= FRESH_MAX_AGE_S
            and right is not None and right_age is not None and right_age <= FRESH_MAX_AGE_S
        )
        if not fresh:
            self._fallen_consecutive = 0
            return
        w_raw = ori[0]
        abs_w = abs(w_raw)
        both_lost = (not left['in_contact']) and (not right['in_contact'])
        one_lost  = (not left['in_contact']) ^ (not right['in_contact'])

        if abs_w < FALLEN_W_CRITICAL or both_lost:
            severity = 'CRITICAL'  # inclinacion fuerte O ambos pies perdidos
        elif (FALLEN_W_CRITICAL <= abs_w < FALLEN_W_WARN) or one_lost:
            severity = 'WARN'      # inclinacion moderada O un pie perdido
        else:
            severity = 'INFO'      # abs_w >= FALLEN_W_WARN y ambos pies en contacto

        if severity == 'CRITICAL':
            self._fallen_consecutive += 1
            if self._fallen_consecutive >= FALLEN_CONSECUTIVE_N and not self._fallen_latched:
                self._publish_fallen_safety_event(w_raw, abs_w, left, right, severity)
                self._fallen_latched = True
        else:
            self._fallen_consecutive = 0
            self._fallen_latched = False

    def _publish_fallen_safety_event(self, w_raw, abs_w, left, right, severity='CRITICAL'):
        """SafetyEvent REAL 3C2b (SECONDARY, no escala PRIMARY)."""
        pair_key = 'imu_contact_support'
        now = self.get_clock().now()
        last = self._last_event_published.get(pair_key)
        if last is not None and (now - last).nanoseconds / 1e9 < (1.0 / OBSERVER_MAX_PUBLISH_HZ):
            return
        self._last_event_published[pair_key] = now
        msg = SafetyEvent()
        msg.event_id = str(uuid.uuid4())
        msg.event_type = 'CONDITION_DETECTED'
        msg.source = 'cross_consistency_observer'
        msg.source_authority = 'SECONDARY'
        msg.authority_effectiveness = 'EFFECTIVE'
        msg.target = 'imu_contact_support'
        msg.risk_level = 'STABILITY_RISK'
        msg.restriction_level = 'NONE'
        msg.transition_id = ''
        msg.transition_priority = 'NORMAL'
        msg.execution_confidence = 'BEST_EFFORT'
        msg.timestamp = now.to_msg()
        msg.notes = (
            f'rule_id=4F-P1 severity={severity} abs_w={abs_w:.3f} '
            f'(CRITICAL<{FALLEN_W_CRITICAL} WARN<{FALLEN_W_WARN}) w_raw={w_raw:.3f} '
            f'L={left["in_contact"]} R={right["in_contact"]} '
            f'{FALLEN_CONSECUTIVE_N} muestras frescas. '
            f'CRITICAL puede ser caida/salto/teleport/perdida total soporte. '
            f'Umbral pragmatico calibrable (DT-4D-016).'
        )
        import time as _tm, json as _json
        _t1_ns = _tm.monotonic_ns()
        self._pub_safety_events.publish(msg)
        _obs_evt = _json.dumps({"schema": "g1_observer_event_time_v1", "event_id": msg.event_id, "host_time_ns": _t1_ns, "event_type": msg.event_type, "source": msg.source})
        print(f"=== G1_OBSERVER_EVENT_TIME {_obs_evt} ===", flush=True)
        self.get_logger().warn(f"=== G1_OBSERVER_EVENT_TIME {_obs_evt} ===")
        self.get_logger().warn(
            f'[3C2b] SafetyEvent REAL - fallen/no-support abs_w={abs_w:.3f} '
            f'(w_raw={w_raw:.3f}) L={left["in_contact"]} R={right["in_contact"]} id: {msg.event_id}'
        )

    def _publish_mock_safety_event(self):
        """
        Publica SafetyEvent mock para validar pipeline.
        SKELETON ONLY — reemplazar con detección real de incoherencia.
        Anti-flood aplicado por par: imu_joint_states.
        """
        pair_key = 'imu_joint_states'
        now = self.get_clock().now()

        # Anti-flood — no publicar más de OBSERVER_MAX_PUBLISH_HZ por par
        last = self._last_event_published.get(pair_key)
        if last is not None:
            elapsed = (now - last).nanoseconds / 1e9
            if elapsed < (1.0 / OBSERVER_MAX_PUBLISH_HZ):
                return

        self._last_event_published[pair_key] = now

        msg = SafetyEvent()
        msg.event_id = str(uuid.uuid4())
        msg.event_type = 'CONDITION_DETECTED'
        msg.source = 'cross_consistency_observer'
        msg.source_authority = 'SECONDARY'
        msg.authority_effectiveness = 'EFFECTIVE'
        msg.target = 'imu_joint_states_pair'
        msg.risk_level = 'SAFE'
        msg.restriction_level = 'NONE'
        msg.transition_id = ''
        msg.transition_priority = 'NORMAL'
        msg.execution_confidence = 'VERIFIED'
        msg.timestamp = now.to_msg()
        msg.notes = (
            'SKELETON MOCK EVENT — cross_consistency_observer Capa 4. '
            'Coherencia real TBD pending SDK G1 + thresholds.'
        )

        self._pub_safety_events.publish(msg)
        self.get_logger().info(
            f'[MOCK] SafetyEvent publicado — par: {pair_key} '
            f'event_id: {msg.event_id}'
        )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main(args=None):
    rclpy.init(args=args)
    node = CrossConsistencyObserver()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
