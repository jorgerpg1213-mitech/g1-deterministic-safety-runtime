#!/usr/bin/env python3
"""
recovery_g1.py — G1 ROS2 Pipeline
Etapa 3C — Recovery Runtime Más Profundo que Mock

Responsabilidades (RECOVERY_MODEL_G1):
  - Ejecutar RecoveryActions reales ejecutables en x86 sin SDK
  - Precondición universal: no ejecutar en STABILITY_RISK/FAULT_CRITICAL con R3+
  - Retry policy: MAX_AUTO_RETRIES → RETRY_COOLDOWN_S → escalation obligatoria
  - Publicar RecoveryEvent observable por cada acción (P7)
  - Aislamiento de subprocess — no dejar procesos huérfanos

RecoveryActions ejecutables en x86 (5 de 7 — RECOVERY_MODEL_G1):
  - restart_noncritical_node: subprocess kill + relaunch via ros2 run
  - restart_critical_node: idem, con cooldown extendido y log obligatorio
  - request_operator_intervention: publica evento MANUAL_REQUIRED
  - restore_nav_stack: cancel Nav2 goal + restart nav2 nodes
  - wait_for_primary_restore: hold activo esperando PRIMARY recovery

RecoveryActions bloqueadas sin SDK:
  - reinitialize_system: requiere SDK G1 + hardware
  - restore_localization: requiere hardware sensors reales

Autores: GPT-4 (arquitecto) + Claude Sonnet 4.6 (implementador) + Padilla (operador)
Versión: 3C-real — 2026-05-24
"""

import subprocess
import threading
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Optional

import rclpy
from rclpy.node import Node
from rclpy.qos import (
    QoSProfile, ReliabilityPolicy, DurabilityPolicy, HistoryPolicy
)
from diagnostic_msgs.msg import DiagnosticArray, DiagnosticStatus, KeyValue

from g1_msgs.msg import RecoveryEvent, SafetyAction, SafetyEvent, SystemState


# ---------------------------------------------------------------------------
# Constantes — RECOVERY_MODEL_G1
# ---------------------------------------------------------------------------

MAX_AUTO_RETRIES = 3                    # TBD — RECOVERY_MODEL_G1
RETRY_COOLDOWN_S = 5.0                  # TBD — antes de segundo intento

# 4H-P2 — Causas terminales/manuales: bypass cooldown y retry counter
# Estas causas requieren intervención del operador desde la primera ocurrencia.
# No son recuperables automáticamente — no deben consumir attempts ni quedar
# bloqueadas por cooldown entre notificaciones consecutivas.
TERMINAL_MANUAL_RULE_IDS = {'4F-P2-FREEZE', '4F-P2-NANINF', '4F-P2-TIMESTAMP'}
EXTENDED_COOLDOWN_S = 15.0             # Para nodos críticos
SUBPROCESS_TIMEOUT_S = 10.0            # Timeout para subprocess de recovery
WAIT_FOR_PRIMARY_POLL_S = 1.0          # Polling interval en wait_for_primary_restore
WAIT_FOR_PRIMARY_MAX_S = 30.0          # Máximo tiempo de espera antes de escalar

# Niveles bloqueados para recovery (precondición universal)
BLOCKED_RISK_LEVELS = {'STABILITY_RISK', 'FAULT_CRITICAL'}
BLOCKED_RESTRICTION_LEVELS = {'R3', 'R4-halt', 'R4-sit', 'R5'}

# Nodos que puede reiniciar recovery_g1 en x86
# Formato: nombre_lógico → (package, executable)
RESTARTABLE_NONCRITICAL_NODES = {
    'slam_toolbox':           ('slam_toolbox', 'async_slam_toolbox_node'),
    'cross_consistency_observer': ('cross_consistency_observer', 'cross_consistency_observer'),
}

RESTARTABLE_CRITICAL_NODES = {
    # watchdog_g1 NO se reinicia desde recovery_g1 — supervisado por systemd (RESILIENCE_MODEL)
    # safety_orchestrator_g1 tampoco — su fallo requiere intervención manual
    # Solo nodos críticos que recovery puede manejar:
    'ekf_filter_node': ('robot_localization', 'ekf_node'),
}

# Nodos de Nav2 que se pueden reiniciar para restore_nav_stack
NAV2_NODES = [
    ('nav2_controller', 'controller_server'),
    ('nav2_planner', 'planner_server'),
    ('nav2_bt_navigator', 'bt_navigator'),
]


# ---------------------------------------------------------------------------
# RecoveryResult
# ---------------------------------------------------------------------------

@dataclass
class RecoveryResult:
    action_name: str
    target: str
    success: bool
    attempt_number: int
    notes: str
    elapsed_s: float
    event_id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])


# ---------------------------------------------------------------------------
# Nodo principal
# ---------------------------------------------------------------------------

class RecoveryG1(Node):
    """
    recovery_g1 — Etapa 3C implementación real.

    Diferencia con skeleton 3B:
    - RecoveryActions reales via subprocess (noncritical y critical nodes)
    - wait_for_primary_restore con polling real
    - restore_nav_stack con subprocess kill + relaunch
    - Subprocess isolation: proceso hijo se termina limpiamente en timeout
    - Retry policy con cooldown real entre intentos
    - RecoveryEvent publicado con resultado real de la acción
    """

    def __init__(self):
        super().__init__('recovery_g1')

        reliable_qos = QoSProfile(
            reliability=ReliabilityPolicy.RELIABLE,
            history=HistoryPolicy.KEEP_LAST,
            depth=50,
        )
        transient_local_sub_qos = QoSProfile(
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.TRANSIENT_LOCAL,
            history=HistoryPolicy.KEEP_LAST,
            depth=1,
        )
        diag_qos = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            history=HistoryPolicy.KEEP_LAST,
            depth=10,
        )

        # Publishers
        self._pub_recovery_events = self.create_publisher(RecoveryEvent, '/recovery_events', reliable_qos)
        self._pub_diagnostics = self.create_publisher(DiagnosticArray, '/diagnostics', diag_qos)

        # Subscribers
        self._sub_system_state = self.create_subscription(
            SystemState,
            '/system_state',
            self._on_system_state,
            transient_local_sub_qos,
        )
        self._sub_safety_events = self.create_subscription(
            SafetyEvent,
            '/safety_events',
            self._on_safety_event,
            reliable_qos,
        )

        # Subscriber ruta gobernada orchestrator→recovery (4G-P4-C)
        self._sub_safety_actions = self.create_subscription(
            SafetyAction,
            '/safety_actions',
            self._on_safety_action,
            reliable_qos,
        )

        # Estado interno
        self._current_risk_level: str = 'SAFE'
        self._current_restriction_level: str = 'NONE'
        self._state_lock = threading.Lock()

        # Retry counters — {target: count}
        self._retry_counters: dict = defaultdict(int)
        self._last_attempt_time: dict = defaultdict(float)
        self._retry_lock = threading.Lock()

        # Subprocess tracking — para cleanup en shutdown
        self._active_subprocesses: list = []
        self._subprocess_lock = threading.Lock()

        # Recovery en curso — evita re-entrancy
        self._recovery_active: bool = False
        self._recovery_lock = threading.Lock()
        # Guard ruta gobernada — anti-doble ejecución por ventana temporal (4G-P4-C)
        self._last_governed_key: tuple = ('', '')
        self._last_governed_time: float = 0.0
        self._governed_dedup_window_s: float = 5.0

        # Estadísticas
        self._total_actions: int = 0
        self._total_successes: int = 0
        self._total_failures: int = 0
        self._total_escalations: int = 0

        # Heartbeat
        self._heartbeat_timer = self.create_timer(1.0, self._publish_heartbeat)

        self.get_logger().info(
            '[recovery_g1] Iniciado — 3C recovery runtime real. '
            f'MAX_AUTO_RETRIES={MAX_AUTO_RETRIES} COOLDOWN={RETRY_COOLDOWN_S}s'
        )

    # -----------------------------------------------------------------------
    # Callbacks
    # -----------------------------------------------------------------------

    def _on_safety_action(self, msg: SafetyAction):
        """Ruta gobernada orchestrator→recovery (4G-P4-C).
        Actúa solo ante stabilization_mode TX-011 AUTONOMOUS.
        Guard temporal evita doble ejecución dentro de ventana 5s.
        Ruta directa SafetyEvent sigue activa como fallback.
        """
        if msg.action_name != 'stabilization_mode':
            return
        if msg.transition_id != 'TX-011':
            return
        if msg.execution_authority != 'AUTONOMOUS':
            return
        # Re-entrancy guard primero
        with self._recovery_lock:
            if self._recovery_active:
                self.get_logger().debug('[4G-P4] ORCH_ACTION→RECOVERY ignorado — recovery en curso')
                return
            # Dedup por ventana temporal — después de confirmar ejecución
            key = (msg.transition_id, msg.action_name)
            now = time.monotonic()
            if key == self._last_governed_key and (now - self._last_governed_time) < self._governed_dedup_window_s:
                self.get_logger().debug('[4G-P4] ORCH_ACTION→RECOVERY duplicado ignorado (ventana 5s)')
                return
            self._last_governed_key = key
            self._last_governed_time = now
            self._recovery_active = True
        t2_ns = self.get_clock().now().nanoseconds
        t1_ns = msg.timestamp.sec * 1_000_000_000 + msg.timestamp.nanosec
        latency_ms = (t2_ns - t1_ns) / 1e6
        self.get_logger().warn(
            f'[4G-P4] ORCH_ACTION→RECOVERY route=orchestrator_safety_action '
            f'action={msg.action_name} tx={msg.transition_id} '
            f'latency_ms={latency_ms:.3f} t1_ns={t1_ns} t2_ns={t2_ns}'
        )
        try:
            result = self._action_stabilization_mode('imu_contact_support', 1)
            self._publish_recovery_event(result, 'CONDITION_DETECTED', 'orchestrator', 'REC-AUTO')
        finally:
            with self._recovery_lock:
                self._recovery_active = False

    def _on_system_state(self, msg: SystemState):
        """Actualiza compound state local. Reset retry counters si vuelve a SAFE."""
        with self._state_lock:
            prev_risk = self._current_risk_level
            self._current_risk_level = msg.risk_level
            self._current_restriction_level = msg.restriction_level

        # Reset retry counters cuando compound state vuelve a (SAFE, NONE)
        if msg.risk_level == 'SAFE' and msg.restriction_level == 'NONE':
            with self._retry_lock:
                self._retry_counters.clear()
                self._last_attempt_time.clear()
            if prev_risk != 'SAFE':
                self.get_logger().info(
                    '[recovery_g1] Estado regresó a (SAFE, NONE) — retry counters reseteados'
                )

    def _on_safety_event(self, msg: SafetyEvent):
        """
        Filtra eventos de watchdog_g1 y cross_consistency_observer.
        Solo actúa si precondición universal se cumple.
        No actúa si recovery ya está en curso (re-entrancy guard).
        """
        source = getattr(msg, 'source', '')
        if source not in ('watchdog_g1', 'cross_consistency_observer'):
            return

        event_type = getattr(msg, 'event_type', '')
        target = getattr(msg, 'target', '')

        # Precondición universal
        if not self._recovery_allowed():
            self.get_logger().debug(
                f'[recovery_g1] Recovery bloqueado — compound state: '
                f'({self._current_risk_level}, {self._current_restriction_level})'
            )
            return

        # Re-entrancy guard
        with self._recovery_lock:
            if self._recovery_active:
                self.get_logger().debug('[recovery_g1] Recovery ya en curso — evento ignorado')
                return
            self._recovery_active = True

        try:
            # 4F-P5: log de latencia t1→t2
            recv_time = self.get_clock().now()
            event_stamp = getattr(msg, 'timestamp', None)
            if event_stamp is not None:
                t1_ns = event_stamp.sec * 1_000_000_000 + event_stamp.nanosec
                t2_ns = recv_time.nanoseconds
                latency_ms = (t2_ns - t1_ns) / 1_000_000
                self.get_logger().info(
                    f'[4F-P5] LATENCY t1→t2 source={source} target={target} '
                    f'latency_ms={latency_ms:.3f} '
                    f't1_ns={t1_ns} t2_ns={t2_ns}'
                )
            notes = getattr(msg, 'notes', '') or ''
            self._dispatch_recovery(event_type, target, source, notes=notes)
        finally:
            with self._recovery_lock:
                self._recovery_active = False

    # -----------------------------------------------------------------------
    # Precondición universal
    # -----------------------------------------------------------------------

    def _recovery_allowed(self) -> bool:
        """
        Precondición universal (RECOVERY_MODEL_G1):
        No ejecutar RecoveryActions que involucren nodo crítico si
        compound state es STABILITY_RISK o FAULT_CRITICAL con R3+.
        """
        with self._state_lock:
            risk_blocked = self._current_risk_level in BLOCKED_RISK_LEVELS
            restriction_blocked = self._current_restriction_level in BLOCKED_RESTRICTION_LEVELS
        return not (risk_blocked and restriction_blocked)

    # -----------------------------------------------------------------------
    # Helper 4H-P1
    # -----------------------------------------------------------------------

    def _extract_rule_id(self, notes: str) -> str:
        """4H-P1: extrae rule_id de msg.notes. Defensivo: tolera None y vacio."""
        notes = notes or ''
        for token in notes.split():
            if token.startswith('rule_id='):
                return token.split('=', 1)[1]
        return ''

    # -----------------------------------------------------------------------
    # Dispatcher
    # -----------------------------------------------------------------------

    def _dispatch_recovery(self, event_type: str, target: str, source: str, notes: str = ''):
        """Selecciona y ejecuta la RecoveryAction apropiada."""
        self._total_actions += 1

        # 4H-P2 — Bypass para causas terminales/manuales (FREEZE, NANINF, TIMESTAMP)
        # Estas causas no son recuperables automáticamente: se notifica al operador
        # inmediatamente, sin consumir retry attempts ni quedar bloqueadas por cooldown.
        rule_id = self._extract_rule_id(notes)
        if rule_id in TERMINAL_MANUAL_RULE_IDS:
            cause = rule_id.split('-')[-1]
            self.get_logger().warn(
                f'[4H-P2] cause={cause} target={target} terminal=True '
                f'action=operator_intervention (bypass cooldown/retry)'
            )
            # Terminal manual causes are not auto-retries;
            # attempt=1 denotes first terminal manual notification.
            result = self._action_request_operator_intervention(target, 1)
            self._publish_recovery_event(result, event_type, source, 'REC-MANUAL')
            return

        # Verificar cooldown antes de retry
        with self._retry_lock:
            attempt = self._retry_counters[target]
            last_attempt = self._last_attempt_time[target]

        elapsed_since_last = time.monotonic() - last_attempt if last_attempt > 0 else float('inf')
        cooldown = EXTENDED_COOLDOWN_S if target in RESTARTABLE_CRITICAL_NODES else RETRY_COOLDOWN_S

        if attempt > 0 and elapsed_since_last < cooldown:
            self.get_logger().info(
                f'[recovery_g1] Cooldown activo para {target}: '
                f'{elapsed_since_last:.1f}s / {cooldown}s'
            )
            return

        # Escalation guard — MAX_AUTO_RETRIES
        if attempt >= MAX_AUTO_RETRIES:
            self.get_logger().warn(
                f'[recovery_g1] {target} alcanzó MAX_AUTO_RETRIES ({MAX_AUTO_RETRIES}) — '
                f'escalando a request_operator_intervention'
            )
            self._total_escalations += 1
            result = self._action_request_operator_intervention(target, attempt)
            self._publish_recovery_event(result, event_type, source, 'REC-MANUAL')
            return

        # 4H-P1 — Mapeo causal por source + rule_id (ruta directa — causas recuperables)
        # FREEZE/NANINF/TIMESTAMP ya fueron manejadas arriba (4H-P2 bypass).
        if source == 'cross_consistency_observer':
            self.get_logger().warn(
                '[4H-P1] cause=fallen route=direct_fallback action=wait_for_primary_restore'
            )
            result = self._action_wait_for_primary_restore(target, attempt + 1)
            recovery_type = 'REC-AUTO'
        elif rule_id == '4F-P2-STALE':
            self.get_logger().warn(
                f'[4H-P1] cause=STALE target={target} action=wait_for_primary_restore'
            )
            result = self._action_wait_for_primary_restore(target, attempt + 1)
            recovery_type = 'REC-AUTO'
        # Mapear event_type a RecoveryAction (rutas previas sin cambio)
        elif event_type in ('NODE_TIMEOUT', 'NONCRITICAL_NODE_DEAD'):
            if target in RESTARTABLE_NONCRITICAL_NODES:
                result = self._action_restart_noncritical_node(target, attempt + 1)
                recovery_type = 'REC-AUTO'
            else:
                result = self._action_request_operator_intervention(target, attempt + 1)
                recovery_type = 'REC-MANUAL'

        elif event_type == 'CRITICAL_NODE_DEAD':
            if target in RESTARTABLE_CRITICAL_NODES:
                result = self._action_restart_critical_node(target, attempt + 1)
                recovery_type = 'REC-ASSISTED'
            else:
                result = self._action_request_operator_intervention(target, attempt + 1)
                recovery_type = 'REC-MANUAL'

        elif event_type in ('PRIMARY_TIMEOUT', 'PRIMARY_DEGRADED'):
            result = self._action_wait_for_primary_restore(target, attempt + 1)
            recovery_type = 'REC-AUTO'

        elif event_type in ('NAV_STACK_FAULT', 'NAV2_TIMEOUT'):
            result = self._action_restore_nav_stack(target, attempt + 1)
            recovery_type = 'REC-AUTO'

        else:
            self.get_logger().debug(
                f'[recovery_g1] event_type {event_type} no mapeado — '
                f'request_operator_intervention'
            )
            result = self._action_request_operator_intervention(target, attempt + 1)
            recovery_type = 'REC-MANUAL'

        # Actualizar retry counter
        with self._retry_lock:
            self._retry_counters[target] = attempt + 1
            self._last_attempt_time[target] = time.monotonic()

        if result.success:
            self._total_successes += 1
        else:
            self._total_failures += 1

        self._publish_recovery_event(result, event_type, source, recovery_type)

    # -----------------------------------------------------------------------
    # RecoveryActions — implementación real x86
    # -----------------------------------------------------------------------

    def _action_stabilization_mode(self, target: str, attempt: int) -> RecoveryResult:
        """
        Governed recovery TX-011: physical instability / fallen.
        Orchestrator ya tomó la decisión de gobernanza.
        success=True = ejecución de stabilization_mode aceptada y registrada.
        No se reclama recuperación física — intervención del operador requerida.
        """
        t0 = time.monotonic()
        self.get_logger().warn(
            f'[4J-P0] stabilization_mode target={target} attempt={attempt} '
            f'route=governed_TX011 — '
            f'execution acknowledged, physical recovery not claimed'
        )
        elapsed_s = time.monotonic() - t0
        return RecoveryResult(
            action_name='stabilization_mode',
            target=target,
            success=True,
            attempt_number=attempt,
            notes='governed_TX011 execution acknowledged — physical recovery not claimed',
            elapsed_s=elapsed_s,
        )

    def _action_restart_noncritical_node(self, target: str, attempt: int) -> RecoveryResult:
        """
        restart_noncritical_node — RECOVERY_MODEL_G1.
        Ejecuta: ros2 lifecycle set <node> shutdown → ros2 run <package> <executable>.

        En x86 sin hardware: subprocess real que puede fallar si el nodo no está
        corriendo. El resultado es observable y honesto.
        """
        t0 = time.monotonic()
        package, executable = RESTARTABLE_NONCRITICAL_NODES.get(target, (None, None))
        if not package:
            return RecoveryResult(
                action_name='restart_noncritical_node',
                target=target,
                success=False,
                attempt_number=attempt,
                notes=f'target {target} no está en RESTARTABLE_NONCRITICAL_NODES',
                elapsed_s=0.0,
            )

        self.get_logger().info(
            f'[recovery_g1] restart_noncritical_node: target={target} attempt={attempt}'
        )

        # Step 1: kill node process (best-effort)
        kill_result = self._subprocess_kill_node(target)
        time.sleep(0.5)  # breve pausa antes de relaunch

        # Step 2: relaunch via ros2 run (best-effort en x86 sin launch system completo)
        relaunch_success = self._subprocess_ros2_run(package, executable)

        elapsed = time.monotonic() - t0
        success = relaunch_success
        notes = (
            f'kill={kill_result} relaunch={relaunch_success} '
            f'package={package} executable={executable}'
        )

        self.get_logger().info(
            f'[recovery_g1] restart_noncritical_node complete: '
            f'target={target} success={success} {notes}'
        )
        return RecoveryResult(
            action_name='restart_noncritical_node',
            target=target,
            success=success,
            attempt_number=attempt,
            notes=notes,
            elapsed_s=elapsed,
        )

    def _action_restart_critical_node(self, target: str, attempt: int) -> RecoveryResult:
        """
        restart_critical_node — RECOVERY_MODEL_G1.
        Similar a noncritical pero con logging obligatorio más detallado
        y cooldown extendido (EXTENDED_COOLDOWN_S).

        ADVERTENCIA: watchdog_g1 y safety_orchestrator_g1 NO están en
        RESTARTABLE_CRITICAL_NODES — su recovery es responsabilidad de systemd.
        """
        t0 = time.monotonic()
        package, executable = RESTARTABLE_CRITICAL_NODES.get(target, (None, None))
        if not package:
            return RecoveryResult(
                action_name='restart_critical_node',
                target=target,
                success=False,
                attempt_number=attempt,
                notes=f'target {target} no está en RESTARTABLE_CRITICAL_NODES',
                elapsed_s=0.0,
            )

        self.get_logger().warn(
            f'[recovery_g1] restart_critical_node: target={target} attempt={attempt} '
            f'— acción de recovery crítica, logging obligatorio'
        )

        kill_result = self._subprocess_kill_node(target)
        time.sleep(1.0)  # cooldown más largo para nodo crítico
        relaunch_success = self._subprocess_ros2_run(package, executable)

        elapsed = time.monotonic() - t0
        success = relaunch_success
        notes = (
            f'CRITICAL NODE RESTART: kill={kill_result} relaunch={relaunch_success} '
            f'package={package} executable={executable} attempt={attempt}'
        )

        self.get_logger().warn(
            f'[recovery_g1] restart_critical_node result: '
            f'target={target} success={success} elapsed={elapsed:.2f}s'
        )
        return RecoveryResult(
            action_name='restart_critical_node',
            target=target,
            success=success,
            attempt_number=attempt,
            notes=notes,
            elapsed_s=elapsed,
        )

    def _action_request_operator_intervention(self, target: str, attempt: int) -> RecoveryResult:
        """
        request_operator_intervention — siempre ejecutable (no subprocess).
        Publica evento MANUAL_REQUIRED observable.
        """
        t0 = time.monotonic()
        self.get_logger().warn(
            f'[recovery_g1] OPERATOR INTERVENTION REQUIRED: target={target} attempt={attempt}'
        )
        # El evento RecoveryEvent lleva la señal — no hay subprocess
        elapsed = time.monotonic() - t0
        return RecoveryResult(
            action_name='request_operator_intervention',
            target=target,
            success=True,  # éxito = publicado correctamente, no que el operador respondió
            attempt_number=attempt,
            notes=f'MANUAL_REQUIRED publicado — target={target}',
            elapsed_s=elapsed,
        )

    def _action_restore_nav_stack(self, target: str, attempt: int) -> RecoveryResult:
        """
        restore_nav_stack — cancel Nav2 goal activo + restart Nav2 nodes si es necesario.
        Ejecutable en x86 sin SDK.
        """
        t0 = time.monotonic()
        self.get_logger().info(
            f'[recovery_g1] restore_nav_stack: target={target} attempt={attempt}'
        )

        # Step 1: cancel Nav2 goal activo via ros2 action
        cancel_success = self._subprocess_cancel_nav2_goal()

        # Step 2: si cancel falló, intentar restart Nav2 nodes
        restart_success = True
        if not cancel_success:
            self.get_logger().info('[recovery_g1] Nav2 cancel falló — intentando restart nodes')
            for package, executable in NAV2_NODES:
                kill = self._subprocess_kill_node(executable)
                time.sleep(0.3)
                launch = self._subprocess_ros2_run(package, executable)
                if not launch:
                    restart_success = False
                    self.get_logger().warn(
                        f'[recovery_g1] Nav2 node restart falló: {package}/{executable}'
                    )

        elapsed = time.monotonic() - t0
        success = cancel_success or restart_success
        notes = f'cancel={cancel_success} nav2_restart={restart_success}'

        return RecoveryResult(
            action_name='restore_nav_stack',
            target=target,
            success=success,
            attempt_number=attempt,
            notes=notes,
            elapsed_s=elapsed,
        )

    def _action_wait_for_primary_restore(self, target: str, attempt: int) -> RecoveryResult:
        """
        wait_for_primary_restore — hold activo esperando que la fuente PRIMARY
        sea restaurada por el sistema o por intervención externa.

        Polling real con timeout. No hace subprocess — observa el estado.
        Si PRIMARY no se restaura en WAIT_FOR_PRIMARY_MAX_S: escalación.
        """
        t0 = time.monotonic()
        self.get_logger().info(
            f'[recovery_g1] wait_for_primary_restore: target={target} attempt={attempt} '
            f'max_wait={WAIT_FOR_PRIMARY_MAX_S}s'
        )

        elapsed = 0.0
        restored = False

        while elapsed < WAIT_FOR_PRIMARY_MAX_S:
            time.sleep(WAIT_FOR_PRIMARY_POLL_S)
            elapsed = time.monotonic() - t0

            # Check si el compound state mejoró (PRIMARY restaurada)
            with self._state_lock:
                current_risk = self._current_risk_level
                current_restriction = self._current_restriction_level

            if current_risk not in ('FAULT_CRITICAL', 'STABILITY_RISK'):
                restored = True
                self.get_logger().info(
                    f'[recovery_g1] wait_for_primary_restore: PRIMARY restaurada '
                    f'en {elapsed:.1f}s — risk_level={current_risk}'
                )
                break

            self.get_logger().debug(
                f'[recovery_g1] wait_for_primary_restore: esperando... '
                f'{elapsed:.1f}s/{WAIT_FOR_PRIMARY_MAX_S}s risk={current_risk}'
            )

        total_elapsed = time.monotonic() - t0
        notes = (
            f'restored={restored} waited={total_elapsed:.1f}s '
            f'final_risk={self._current_risk_level}'
        )

        if not restored:
            self.get_logger().warn(
                f'[recovery_g1] wait_for_primary_restore timeout '
                f'({WAIT_FOR_PRIMARY_MAX_S}s) — PRIMARY no restaurada'
            )

        return RecoveryResult(
            action_name='wait_for_primary_restore',
            target=target,
            success=restored,
            attempt_number=attempt,
            notes=notes,
            elapsed_s=total_elapsed,
        )

    # -----------------------------------------------------------------------
    # Subprocess helpers — isolation real
    # -----------------------------------------------------------------------

    def _subprocess_kill_node(self, node_name: str) -> bool:
        """
        Kill de un nodo ROS2 via pkill.
        Isolation: si el proceso no existe, no falla.
        Retorna True si el kill tuvo éxito o el proceso ya no existía.
        """
        try:
            result = subprocess.run(
                ['pkill', '-f', node_name],
                timeout=SUBPROCESS_TIMEOUT_S,
                capture_output=True,
                text=True,
            )
            # pkill retorna 0 si mató algo, 1 si no encontró nada
            success = result.returncode in (0, 1)
            self.get_logger().debug(
                f'[recovery_g1] pkill {node_name}: returncode={result.returncode}'
            )
            return success
        except subprocess.TimeoutExpired:
            self.get_logger().warn(
                f'[recovery_g1] pkill {node_name}: timeout ({SUBPROCESS_TIMEOUT_S}s)'
            )
            return False
        except Exception as e:
            self.get_logger().error(f'[recovery_g1] pkill {node_name}: error {e}')
            return False

    def _subprocess_ros2_run(self, package: str, executable: str) -> bool:
        """
        Lanza un nodo ROS2 en background via ros2 run.
        El proceso se trackea para cleanup en shutdown.

        NOTA: en x86 sin launch completo, esto puede no conectarse al ROS graph
        si el sistema no está corriendo. El resultado es honesto — no se asume éxito.
        """
        try:
            proc = subprocess.Popen(
                ['ros2', 'run', package, executable],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            with self._subprocess_lock:
                self._active_subprocesses.append(proc)

            # Esperar brevemente para detectar fallo inmediato
            time.sleep(0.5)
            if proc.poll() is not None:
                # Proceso terminó inmediatamente — fallo
                self.get_logger().warn(
                    f'[recovery_g1] ros2 run {package}/{executable} terminó inmediatamente '
                    f'(returncode={proc.poll()})'
                )
                return False

            self.get_logger().info(
                f'[recovery_g1] ros2 run {package}/{executable}: lanzado pid={proc.pid}'
            )
            return True

        except FileNotFoundError:
            # ros2 no está en PATH — entorno x86 sin ROS2 sourced
            self.get_logger().warn(
                f'[recovery_g1] ros2 run {package}/{executable}: '
                f'ros2 no encontrado en PATH — entorno no sourced'
            )
            return False
        except Exception as e:
            self.get_logger().error(
                f'[recovery_g1] ros2 run {package}/{executable}: error {e}'
            )
            return False

    def _subprocess_cancel_nav2_goal(self) -> bool:
        """
        Cancela el Nav2 goal activo via ros2 action send_goal (cancel).
        En x86 sin Nav2 corriendo: retorna False honestamente.
        """
        try:
            # No existe un comando directo de cancel en CLI sin action server
            # Usamos ros2 lifecycle set para bajar el action server
            result = subprocess.run(
                [
                    'ros2', 'action', 'send_goal',
                    '/navigate_to_pose',
                    'nav2_msgs/action/NavigateToPose',
                    '{}',
                    '--cancel-time', '0.0',
                ],
                timeout=SUBPROCESS_TIMEOUT_S,
                capture_output=True,
                text=True,
            )
            success = result.returncode == 0
            self.get_logger().debug(
                f'[recovery_g1] Nav2 cancel: returncode={result.returncode}'
            )
            return success
        except subprocess.TimeoutExpired:
            self.get_logger().warn('[recovery_g1] Nav2 cancel: timeout')
            return False
        except FileNotFoundError:
            self.get_logger().warn('[recovery_g1] Nav2 cancel: ros2 no en PATH')
            return False
        except Exception as e:
            self.get_logger().error(f'[recovery_g1] Nav2 cancel: error {e}')
            return False

    # -----------------------------------------------------------------------
    # Publisher
    # -----------------------------------------------------------------------

    def _publish_recovery_event(
        self,
        result: RecoveryResult,
        trigger_event_type: str,
        source: str,
        recovery_type: str,
    ):
        """Publica RecoveryEvent observable — P7."""
        msg = RecoveryEvent()
        msg.event_id = result.event_id
        msg.event_type = 'RECOVERY_SUCCESS' if result.success else 'RECOVERY_FAILURE'
        msg.action_name = result.action_name
        msg.recovery_type = recovery_type
        msg.target = result.target
        msg.compound_state_at_trigger = (
            f'({self._current_risk_level},{self._current_restriction_level})'
        )
        msg.attempt_number = result.attempt_number
        msg.result = 'SUCCESS' if result.success else 'FAILURE'
        msg.notes = (
            f'elapsed={result.elapsed_s:.2f}s trigger={trigger_event_type} '
            f'source={source} {result.notes}'
        )
        self._pub_recovery_events.publish(msg)

        level = 'info' if result.success else 'warn'
        getattr(self.get_logger(), level)(
            f'[recovery_g1] RecoveryEvent: {msg.event_type} '
            f'action={result.action_name} target={result.target} '
            f'attempt={result.attempt_number}'
        )

    def _publish_heartbeat(self):
        """Heartbeat periódico en /diagnostics."""
        diag_array = DiagnosticArray()
        status = DiagnosticStatus()
        status.name = 'recovery_g1'
        status.hardware_id = 'g1_ros2_pipeline'
        status.level = DiagnosticStatus.OK

        with self._state_lock:
            risk = self._current_risk_level
            restriction = self._current_restriction_level

        with self._retry_lock:
            max_retries_reached = any(
                v >= MAX_AUTO_RETRIES for v in self._retry_counters.values()
            )

        if max_retries_reached:
            status.level = DiagnosticStatus.WARN

        with self._subprocess_lock:
            n_subproc = len(self._active_subprocesses)

        status.values = [
            KeyValue(key='risk_level', value=risk),
            KeyValue(key='restriction_level', value=restriction),
            KeyValue(key='recovery_allowed', value=str(self._recovery_allowed())),
            KeyValue(key='total_actions', value=str(self._total_actions)),
            KeyValue(key='total_successes', value=str(self._total_successes)),
            KeyValue(key='total_failures', value=str(self._total_failures)),
            KeyValue(key='total_escalations', value=str(self._total_escalations)),
            KeyValue(key='active_subprocesses', value=str(n_subproc)),
        ]
        diag_array.status = [status]
        self._pub_diagnostics.publish(diag_array)

    # -----------------------------------------------------------------------
    # Lifecycle
    # -----------------------------------------------------------------------

    def destroy_node(self):
        """Shutdown limpio — terminar subprocesses activos."""
        self.get_logger().info('[recovery_g1] Shutdown — terminando subprocesses activos')
        with self._subprocess_lock:
            for proc in self._active_subprocesses:
                try:
                    if proc.poll() is None:
                        proc.terminate()
                        proc.wait(timeout=2.0)
                except Exception as e:
                    self.get_logger().warn(f'[recovery_g1] Error terminando subprocess: {e}')
            self._active_subprocesses.clear()
        super().destroy_node()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main(args=None):
    rclpy.init(args=args)
    node = RecoveryG1()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
