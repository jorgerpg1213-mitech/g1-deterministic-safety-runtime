#!/usr/bin/env python3
"""
safety_orchestrator_g1.py — G1 ROS2 Pipeline
Etapa 3C — Transition Logic Real + Scheduler con Priority Buckets + T8 Arbitration DRAFT

Responsabilidades (ADR-002):
  - Evaluar Transition Matrix del SAFETY_MODEL_G1
  - Scheduling con 4 buckets de prioridad
  - Arbitration T8 DRAFT (PH-001 abierto)
  - Ejecución de transiciones con preemption
  - Publicar evidencia observable en 4 topics

NO responsabilidad de este componente:
  - Detectar condiciones (watchdog_g1)
  - Observar cross-consistency (cross_consistency_observer)
  - Ejecutar RecoveryActions (recovery_g1)
  - Thresholds reales (pending SDK G1)

Autores: GPT-4 (arquitecto) + Claude Sonnet 4.6 (implementador) + Padilla (operador)
Versión: 3C-real — 2026-05-24
"""

import threading
import time
import uuid
from collections import deque, defaultdict
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional

import rclpy
from rclpy.node import Node
from rclpy.qos import (
    QoSProfile, ReliabilityPolicy, DurabilityPolicy, HistoryPolicy
)
from diagnostic_msgs.msg import DiagnosticArray, DiagnosticStatus, KeyValue

# g1_msgs — compilados en el workspace como parte de Etapa 3B
from g1_msgs.msg import SafetyEvent, SystemState, SafetyAction


# ---------------------------------------------------------------------------
# Constantes — todas TBD hasta SDK G1 real
# ---------------------------------------------------------------------------

# Thresholds provisionales — RECOVERY_WINDOW_TBD
EVALUATION_LOOP_HZ = 20.0          # Hz — frecuencia de evaluación del scheduler
EVALUATION_TIMEOUT_S = 1.0 / EVALUATION_LOOP_HZ
HEARTBEAT_HZ = 1.0                 # Hz — heartbeat del orchestrator

# Buffer
EVENT_BUFFER_MAXLEN = 100          # eventos en deque — overflow con log
ARBITRATION_PENDING_TIMEOUT_S = 5.0  # segundos antes de escalar ARBITRATION_PENDING

# Scheduler — nombre de los 4 buckets (orden de prioridad descendente)
BUCKET_CRITICAL_INTERRUPT = 0
BUCKET_COMMIT_TERMINAL = 1
BUCKET_NORMAL = 2
BUCKET_RECOVERY = 3
BUCKET_NAMES = {
    BUCKET_CRITICAL_INTERRUPT: 'CRITICAL_INTERRUPT',
    BUCKET_COMMIT_TERMINAL:    'COMMIT_TERMINAL',
    BUCKET_NORMAL:             'NORMAL',
    BUCKET_RECOVERY:           'RECOVERY',
}

# Risk levels — orden para comparación numérica
RISK_LEVEL_ORDER = {
    'SAFE': 0,
    'CAUTION': 1,
    'DANGER': 2,
    'STABILITY_RISK': 3,
    'FAULT_CRITICAL': 4,
}

# Restriction levels — orden para comparación numérica
RESTRICTION_LEVEL_ORDER = {
    'NONE':     0,
    'R1':       1,
    'R2':       2,
    'R3':       3,
    'R4-halt':  4,
    'R4-sit':   5,
    'R5':       6,
}

# Estados desde los cuales R5 ya está committed e irreversible
R5_COMMITTED_STATES = {('FAULT_CRITICAL', 'R5')}

# Self-source guard — ADR-002 Sección 8
SELF_SOURCE = 'safety_orchestrator_g1'


# ---------------------------------------------------------------------------
# Compound State — propiedad exclusiva del Thread 2 (evaluation loop)
# ---------------------------------------------------------------------------

@dataclass
class CompoundState:
    """
    Par (Risk Level, Restriction Level) — unidad de estado del sistema.
    Propiedad exclusiva de Thread 2.
    Thread 1 solo lee via snapshot bajo mutex.
    """
    risk_level: str = 'SAFE'
    restriction_level: str = 'NONE'
    last_transition_id: str = 'INIT'
    execution_confidence: str = 'VERIFIED'
    arbitration_pending: bool = False
    r5_committed: bool = False
    timestamp: float = field(default_factory=time.time)

    def is_r5_committed(self) -> bool:
        return self.r5_committed

    def compound_key(self) -> tuple:
        return (self.risk_level, self.restriction_level)

    def risk_order(self) -> int:
        return RISK_LEVEL_ORDER.get(self.risk_level, -1)

    def restriction_order(self) -> int:
        return RESTRICTION_LEVEL_ORDER.get(self.restriction_level, -1)

    def to_snapshot(self) -> dict:
        return {
            'risk_level': self.risk_level,
            'restriction_level': self.restriction_level,
            'last_transition_id': self.last_transition_id,
            'execution_confidence': self.execution_confidence,
            'arbitration_pending': self.arbitration_pending,
            'r5_committed': self.r5_committed,
            'timestamp': self.timestamp,
        }


# ---------------------------------------------------------------------------
# Scheduled Event — evento con bucket de prioridad asignado
# ---------------------------------------------------------------------------

@dataclass(order=True)
class ScheduledEvent:
    """Wrapper de SafetyEvent con bucket y timestamp de enqueue."""
    bucket: int
    enqueue_time: float
    msg: object = field(compare=False)  # SafetyEvent — no comparable
    event_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])


# ---------------------------------------------------------------------------
# Transition Matrix — evaluador basado en SAFETY_MODEL_G1
# ---------------------------------------------------------------------------

class TransitionEvaluator:
    """
    Evalúa qué transición de la Transition Matrix aplica dado un SafetyEvent
    y el CompoundState actual.

    Fidelidad: cada método `_eval_TX_NNN` replica exactamente los campos
    de la fila TX correspondiente del SAFETY_MODEL_G1.md.

    Limitaciones declaradas (SAFETY_MODEL_G1 Sección 14):
    - RECOVERY_WINDOW_TBD en todos los thresholds temporales
    - T8 es DRAFT — PH-001 abierto
    - R4 subestados parciales — PH-003 abierto
    """

    def evaluate(
        self,
        event: object,  # SafetyEvent
        state: CompoundState,
    ) -> Optional[dict]:
        """
        Retorna un dict con la transición aplicable, o None si ninguna aplica.

        El dict tiene campos:
          transition_id, transition_priority, runtime_action,
          target_risk_level, target_restriction_level,
          execution_confidence, execution_authority, notes
        """
        # Guard: R5 committed — COMMIT_TERMINAL irreversible (T5)
        if state.is_r5_committed():
            return None

        event_type = getattr(event, 'event_type', '')
        source_authority = getattr(event, 'source_authority', '')
        authority_eff = getattr(event, 'authority_effectiveness', '')
        transition_priority_in = getattr(event, 'transition_priority', '')

        # Evaluación en orden de prioridad conceptual
        # TX-001 — CRITICAL_INTERRUPT global (cross-cutting)
        result = self._eval_TX001(event_type, source_authority, authority_eff, state)
        if result:
            return result

        # TX-008 — SAFE → STABILITY_RISK directo (CRITICAL_INTERRUPT)
        result = self._eval_TX008(event_type, source_authority, authority_eff, state)
        if result:
            return result

        # TX-005 — FAULT_CRITICAL → torque_release (COMMIT_TERMINAL — HUMAN_REQUIRED)
        result = self._eval_TX005(event_type, state)
        if result:
            return result

        # ESCALATION paths (NORMAL)
        result = self._eval_TX002(event_type, source_authority, authority_eff, state)
        if result:
            return result

        result = self._eval_TX007(event_type, source_authority, authority_eff, state)
        if result:
            return result

        result = self._eval_TX003(event_type, source_authority, authority_eff, state)
        if result:
            return result

        result = self._eval_TX004(event_type, source_authority, authority_eff, state)
        if result:
            return result

        # TX-009 — emergency_sit (POLICY_GATED)
        result = self._eval_TX009(event_type, state)
        if result:
            return result

        # RECOVERY paths
        result = self._eval_TX006a(event_type, source_authority, authority_eff, state)
        if result:
            return result

        result = self._eval_TX006b(event_type, source_authority, authority_eff, state)
        if result:
            return result

        result = self._eval_TX006c(event_type, source_authority, authority_eff, state)
        if result:
            return result

        result = self._eval_TX010(event_type, source_authority, authority_eff, state)
        if result:
            return result

        return None

    # -----------------------------------------------------------------------
    # TX-001 — ANY → stabilization_mode (CRITICAL_INTERRUPT)
    # -----------------------------------------------------------------------
    def _eval_TX001(self, event_type, source_authority, authority_eff, state):
        """
        Trigger: IMU o joint_states reportan inestabilidad.
        Precondición: PRIMARY con authority_effectiveness >= DEGRADED_EFFECTIVE.
        No aplica si R5 ya committed (verificado por caller).
        No aplica si ya en (FAULT_CRITICAL, R5) — lo que equivale a R5 committed.
        """
        if event_type not in ('STABILITY_ANOMALY', 'JOINT_OSCILLATION', 'IMU_OUT_OF_RANGE'):
            return None
        if source_authority not in ('PRIMARY_IMU', 'PRIMARY_JOINT_STATES'):
            return None
        if authority_eff not in ('EFFECTIVE', 'DEGRADED_EFFECTIVE'):
            return None

        # Estado target: max(current_risk_level, STABILITY_RISK)
        current_risk_order = state.risk_order()
        stability_risk_order = RISK_LEVEL_ORDER['STABILITY_RISK']
        target_risk = 'STABILITY_RISK' if current_risk_order < stability_risk_order else state.risk_level

        # execution_confidence: VERIFIED si PRIMARY EFFECTIVE, BEST_EFFORT si FAULT_CRITICAL
        exec_conf = 'VERIFIED' if authority_eff == 'EFFECTIVE' else 'BEST_EFFORT'

        return {
            'transition_id': 'TX-001',
            'transition_priority': 'CRITICAL_INTERRUPT',
            'execution_authority': 'AUTONOMOUS',
            'runtime_action': 'stabilization_mode',
            'target_risk_level': target_risk,
            'target_restriction_level': 'R3',
            'execution_confidence': exec_conf,
            'notes': f'TX-001: stabilization_mode por {event_type} desde {source_authority}',
        }

    # -----------------------------------------------------------------------
    # TX-002 — SAFE → CAUTION (NORMAL)
    # -----------------------------------------------------------------------
    def _eval_TX002(self, event_type, source_authority, authority_eff, state):
        if state.compound_key() != ('SAFE', 'NONE'):
            return None
        if event_type not in ('SENSOR_DEGRADED', 'OBSTACLE_DETECTED'):
            return None
        # Fuente ADVISORY sola no puede disparar TX-002 (escalation_guard)
        if source_authority == 'ADVISORY' and authority_eff not in ('EFFECTIVE', 'DEGRADED_EFFECTIVE'):
            return None

        # branching: riesgo de entorno vs locomotor
        if event_type == 'OBSTACLE_DETECTED':
            action = 'velocity_clamp'
        else:
            action = 'gait_slowdown'

        return {
            'transition_id': 'TX-002',
            'transition_priority': 'NORMAL',
            'execution_authority': 'AUTONOMOUS',
            'runtime_action': action,
            'target_risk_level': 'CAUTION',
            'target_restriction_level': 'R1',
            'execution_confidence': 'VERIFIED',
            'notes': f'TX-002: SAFE→CAUTION por {event_type}',
        }

    # -----------------------------------------------------------------------
    # TX-003 — DANGER → STABILITY_RISK (NORMAL)
    # -----------------------------------------------------------------------
    def _eval_TX003(self, event_type, source_authority, authority_eff, state):
        if state.risk_level != 'DANGER':
            return None
        if event_type not in ('STABILITY_ANOMALY', 'JOINT_OSCILLATION', 'IMU_OUT_OF_RANGE'):
            return None
        if source_authority not in ('PRIMARY_IMU', 'PRIMARY_JOINT_STATES'):
            return None
        if authority_eff not in ('EFFECTIVE', 'DEGRADED_EFFECTIVE'):
            return None

        return {
            'transition_id': 'TX-003',
            'transition_priority': 'NORMAL',
            'execution_authority': 'AUTONOMOUS',
            'runtime_action': 'stabilization_mode',
            'target_risk_level': 'STABILITY_RISK',
            'target_restriction_level': 'R3',
            'execution_confidence': 'VERIFIED',
            'notes': f'TX-003: DANGER→STABILITY_RISK por {event_type}',
        }

    # -----------------------------------------------------------------------
    # TX-004 — STABILITY_RISK → FAULT_CRITICAL (NORMAL — AUTHORITY_LOSS)
    # -----------------------------------------------------------------------
    def _eval_TX004(self, event_type, source_authority, authority_eff, state):
        if state.risk_level != 'STABILITY_RISK':
            return None
        if event_type not in ('PRIMARY_TIMEOUT', 'PRIMARY_INCOHERENT', 'AUTHORITY_LOSS'):
            return None
        # PRIMARY debe estar INEFFECTIVE o UNRELIABLE (T6b)
        if authority_eff not in ('INEFFECTIVE', 'UNRELIABLE'):
            return None

        return {
            'transition_id': 'TX-004',
            'transition_priority': 'NORMAL',
            'execution_authority': 'AUTONOMOUS',
            'runtime_action': 'controlled_halt',
            'target_risk_level': 'FAULT_CRITICAL',
            'target_restriction_level': 'R4-halt',
            'execution_confidence': 'BEST_EFFORT',  # T3: FAULT_CRITICAL siempre BEST_EFFORT
            'notes': f'TX-004: STABILITY_RISK→FAULT_CRITICAL AUTHORITY_LOSS {source_authority} {authority_eff}',
        }

    # -----------------------------------------------------------------------
    # TX-005 — FAULT_CRITICAL → torque_release (COMMIT_TERMINAL — HUMAN_REQUIRED)
    # -----------------------------------------------------------------------
    def _eval_TX005(self, event_type, state):
        """
        Solo ejecutable si HUMAN_REQUIRED.
        En x86 sin SDK: registra el intent, no ejecuta acción real sobre hardware.
        """
        if state.compound_key() not in (('FAULT_CRITICAL', 'R4-halt'), ('FAULT_CRITICAL', 'R4-sit')):
            return None
        if event_type != 'POLICY_GATE_AUTHORIZED_R5':
            return None

        return {
            'transition_id': 'TX-005',
            'transition_priority': 'COMMIT_TERMINAL',
            'execution_authority': 'HUMAN_REQUIRED',
            'runtime_action': 'torque_release',
            'target_risk_level': 'FAULT_CRITICAL',
            'target_restriction_level': 'R5',
            'execution_confidence': 'BEST_EFFORT',
            'notes': 'TX-005: COMMIT_TERMINAL torque_release — HUMAN_REQUIRED — irreversible post-commit',
        }

    # -----------------------------------------------------------------------
    # TX-006a — Recovery desde (FAULT_CRITICAL, R4-halt) (RECOVERY)
    # -----------------------------------------------------------------------
    def _eval_TX006a(self, event_type, source_authority, authority_eff, state):
        if state.compound_key() != ('FAULT_CRITICAL', 'R4-halt'):
            return None
        if event_type != 'PRIMARY_RESTORED':
            return None
        if authority_eff != 'EFFECTIVE':
            return None

        return {
            'transition_id': 'TX-006a',
            'transition_priority': 'RECOVERY',
            'execution_authority': 'AUTONOMOUS',
            'runtime_action': 'release_controlled_halt',
            'target_risk_level': 'DANGER',   # T1: reducción un nivel
            'target_restriction_level': 'R3',
            'execution_confidence': 'VERIFIED',
            'notes': f'TX-006a: recovery FAULT_CRITICAL→DANGER PRIMARY restaurada {source_authority}',
        }

    # -----------------------------------------------------------------------
    # TX-006b — Recovery desde (STABILITY_RISK, R3) (RECOVERY)
    # -----------------------------------------------------------------------
    def _eval_TX006b(self, event_type, source_authority, authority_eff, state):
        if state.compound_key() != ('STABILITY_RISK', 'R3'):
            return None
        if event_type != 'PRIMARY_STABLE':
            return None
        if authority_eff not in ('EFFECTIVE', 'DEGRADED_EFFECTIVE'):
            return None

        return {
            'transition_id': 'TX-006b',
            'transition_priority': 'RECOVERY',
            'execution_authority': 'AUTONOMOUS',
            'runtime_action': 'reduce_stabilization_to_locomotion_hold',
            'target_risk_level': 'DANGER',   # T1: reducción un nivel
            'target_restriction_level': 'R2',
            'execution_confidence': 'VERIFIED',
            'notes': f'TX-006b: recovery STABILITY_RISK→DANGER PRIMARY estable',
        }

    # -----------------------------------------------------------------------
    # TX-006c — Recovery desde (DANGER, R2) (RECOVERY)
    # -----------------------------------------------------------------------
    def _eval_TX006c(self, event_type, source_authority, authority_eff, state):
        if state.compound_key() != ('DANGER', 'R2'):
            return None
        if event_type != 'PRIMARY_STABLE':
            return None
        if authority_eff not in ('EFFECTIVE',):
            return None

        return {
            'transition_id': 'TX-006c',
            'transition_priority': 'RECOVERY',
            'execution_authority': 'AUTONOMOUS',
            'runtime_action': 'release_locomotion_hold',
            'target_risk_level': 'CAUTION',  # T1: reducción un nivel
            'target_restriction_level': 'R1',
            'execution_confidence': 'VERIFIED',
            'notes': f'TX-006c: recovery DANGER→CAUTION locomotion_hold liberado',
        }

    # -----------------------------------------------------------------------
    # TX-007 — CAUTION → DANGER (NORMAL)
    # -----------------------------------------------------------------------
    def _eval_TX007(self, event_type, source_authority, authority_eff, state):
        if state.risk_level != 'CAUTION':
            return None
        if event_type not in ('OBSTACLE_IN_PATH', 'SENSOR_CRITICAL_LATENCY', 'SECONDARY_DOMAIN_ESCALATION'):
            return None
        # ADVISORY sola no puede disparar TX-007 (escalation_guard)
        if source_authority == 'ADVISORY':
            return None

        return {
            'transition_id': 'TX-007',
            'transition_priority': 'NORMAL',
            'execution_authority': 'AUTONOMOUS',
            'runtime_action': 'freeze_navigation',
            'target_risk_level': 'DANGER',
            'target_restriction_level': 'R1',  # R-Level permanece R1 — SAFETY_MODEL nota
            'execution_confidence': 'VERIFIED',
            'notes': f'TX-007: CAUTION→DANGER por {event_type}',
        }

    # -----------------------------------------------------------------------
    # TX-008 — SAFE → STABILITY_RISK directo (CRITICAL_INTERRUPT)
    # -----------------------------------------------------------------------
    def _eval_TX008(self, event_type, source_authority, authority_eff, state):
        """
        Excepción a T1: ESCALATION de emergencia puede saltar niveles cuando
        source authority = PRIMARY, trigger confirmado no transitorio,
        transition_priority = CRITICAL_INTERRUPT.

        SAFE → STABILITY_RISK directamente — salta CAUTION y DANGER.
        """
        if state.compound_key() != ('SAFE', 'NONE'):
            return None
        if event_type not in ('STABILITY_ANOMALY_SEVERE', 'SUDDEN_IMPACT', 'JOINT_STATES_SUDDEN_FAILURE'):
            return None
        if source_authority not in ('PRIMARY_IMU', 'PRIMARY_JOINT_STATES'):
            return None
        # SECONDARY o ADVISORY solos no pueden disparar TX-008 (escalation_guard)
        if authority_eff not in ('EFFECTIVE',):
            return None

        return {
            'transition_id': 'TX-008',
            'transition_priority': 'CRITICAL_INTERRUPT',
            'execution_authority': 'AUTONOMOUS',
            'runtime_action': 'stabilization_mode',
            'target_risk_level': 'STABILITY_RISK',
            'target_restriction_level': 'R3',
            'execution_confidence': 'VERIFIED',
            'notes': f'TX-008: SAFE→STABILITY_RISK CRITICAL_INTERRUPT salto directo {event_type}',
        }

    # -----------------------------------------------------------------------
    # TX-009 — emergency_sit (POLICY_GATED)
    # -----------------------------------------------------------------------
    def _eval_TX009(self, event_type, state):
        if state.restriction_level != 'R4-halt':
            return None
        if event_type != 'POLICY_GATE_AUTHORIZED_EMERGENCY_SIT':
            return None

        exec_conf = 'VERIFIED' if state.risk_level == 'STABILITY_RISK' else 'BEST_EFFORT'

        return {
            'transition_id': 'TX-009',
            'transition_priority': 'NORMAL',
            'execution_authority': 'POLICY_GATED',
            'runtime_action': 'emergency_sit',
            'target_risk_level': state.risk_level,   # Risk Level no cambia
            'target_restriction_level': 'R4-sit',
            'execution_confidence': exec_conf,
            'notes': f'TX-009: emergency_sit POLICY_GATED desde {state.risk_level}',
        }

    # -----------------------------------------------------------------------
    # TX-010 — CAUTION → SAFE (RECOVERY)
    # -----------------------------------------------------------------------
    def _eval_TX010(self, event_type, source_authority, authority_eff, state):
        if state.compound_key() != ('CAUTION', 'R1'):
            return None
        if event_type != 'ALL_CLEAR':
            return None
        # Todas las fuentes deben ser EFFECTIVE para SAFE
        if authority_eff != 'EFFECTIVE':
            return None

        return {
            'transition_id': 'TX-010',
            'transition_priority': 'RECOVERY',
            'execution_authority': 'AUTONOMOUS',
            'runtime_action': 'release_all_constraints',
            'target_risk_level': 'SAFE',
            'target_restriction_level': 'NONE',
            'execution_confidence': 'VERIFIED',
            'notes': 'TX-010: CAUTION→SAFE — todos los constraints liberados',
        }


# ---------------------------------------------------------------------------
# Scheduler — 4 buckets de prioridad
# ---------------------------------------------------------------------------

class PriorityScheduler:
    """
    Scheduler con 4 buckets de prioridad.

    Bucket 0 — CRITICAL_INTERRUPT: vacía primero. Preempta cualquier evaluación
               en curso excepto COMMIT_TERMINAL post-commit (T5).
    Bucket 1 — COMMIT_TERMINAL: irreversible una vez iniciado.
    Bucket 2 — NORMAL: ejecuta en orden de llegada si no hay superior activo.
    Bucket 3 — RECOVERY: ejecuta solo si no hay escalation activa.

    Thread-safety: los buckets son deques internos protegidos por el lock
    del caller. El scheduler es stateless respecto al lock — lo gestiona
    SafetyOrchestratorG1.
    """

    def __init__(self):
        self._buckets: list[deque] = [
            deque(),  # 0 CRITICAL_INTERRUPT
            deque(),  # 1 COMMIT_TERMINAL
            deque(),  # 2 NORMAL
            deque(),  # 3 RECOVERY
        ]
        self._priority_map = {
            'CRITICAL_INTERRUPT': BUCKET_CRITICAL_INTERRUPT,
            'COMMIT_TERMINAL':    BUCKET_COMMIT_TERMINAL,
            'NORMAL':             BUCKET_NORMAL,
            'RECOVERY':           BUCKET_RECOVERY,
        }

    def enqueue(self, event, priority: str) -> ScheduledEvent:
        """Añade un evento al bucket correspondiente."""
        bucket = self._priority_map.get(priority, BUCKET_NORMAL)
        scheduled = ScheduledEvent(
            bucket=bucket,
            enqueue_time=time.monotonic(),
            msg=event,
        )
        self._buckets[bucket].append(scheduled)
        return scheduled

    def drain_all(self) -> list:
        """
        Extrae todos los eventos de todos los buckets en orden de prioridad.
        Llamado exclusivamente desde Thread 2.

        Retorna lista de ScheduledEvent ordenada por bucket (menor = mayor prioridad).
        Dentro de un bucket, orden FIFO.
        """
        result = []
        for bucket_idx in range(len(self._buckets)):
            while self._buckets[bucket_idx]:
                result.append(self._buckets[bucket_idx].popleft())
        return result

    def has_critical_interrupt(self) -> bool:
        """True si hay algún CRITICAL_INTERRUPT pendiente."""
        return len(self._buckets[BUCKET_CRITICAL_INTERRUPT]) > 0

    def has_commit_terminal(self) -> bool:
        """True si hay algún COMMIT_TERMINAL pendiente."""
        return len(self._buckets[BUCKET_COMMIT_TERMINAL]) > 0

    def total_pending(self) -> int:
        return sum(len(b) for b in self._buckets)

    def pending_by_bucket(self) -> dict:
        return {BUCKET_NAMES[i]: len(self._buckets[i]) for i in range(len(self._buckets))}


# ---------------------------------------------------------------------------
# T8 Arbitration — DRAFT (PH-001)
# ---------------------------------------------------------------------------

class T8Arbitrator:
    """
    T8 DRAFT — conflict resolution entre transiciones de igual transition_priority.

    Reglas (SAFETY_MODEL_G1 Sección 9.2, T8):
    1. Si ambas CRITICAL_INTERRUPT: prevalece la que involucra fuente PRIMARY
       de mayor authority_effectiveness (EFFECTIVE > DEGRADED_EFFECTIVE > CONTESTED).
    2. Si ambas NORMAL simultáneas: prevalece la que tiene target_risk_level mayor.
    3. Si ambas RECOVERY simultáneas: prevalece la más conservadora (menor reducción).
    4. Empate no resuelto → ARBITRATION_PENDING.

    Estado: DRAFT — PH-001 abierto. Implementación testeable pero no certificada.
    """

    # Orden de authority_effectiveness para regla 1
    AUTH_EFF_ORDER = {
        'EFFECTIVE':           3,
        'DEGRADED_EFFECTIVE':  2,
        'CONTESTED':           1,
        'UNRELIABLE':          0,
        'INEFFECTIVE':         0,
        '':                    -1,
    }

    def arbitrate(
        self,
        tx_a: dict,
        tx_b: dict,
        event_a,
        event_b,
        state: CompoundState,
    ) -> tuple:
        """
        Retorna (winner: dict, loser: dict, reason: str, pending: bool).
        Si pending=True: no se puede resolver — ARBITRATION_PENDING.
        """
        priority = tx_a.get('transition_priority', 'NORMAL')

        if priority == 'CRITICAL_INTERRUPT':
            return self._arbitrate_critical_interrupt(tx_a, tx_b, event_a, event_b)
        elif priority == 'NORMAL':
            return self._arbitrate_normal(tx_a, tx_b)
        elif priority == 'RECOVERY':
            return self._arbitrate_recovery(tx_a, tx_b, state)
        else:
            # COMMIT_TERMINAL — no debería haber dos simultáneos: primera gana
            return tx_a, tx_b, 'COMMIT_TERMINAL first-wins', False

    def _arbitrate_critical_interrupt(self, tx_a, tx_b, event_a, event_b):
        eff_a = self.AUTH_EFF_ORDER.get(
            getattr(event_a, 'authority_effectiveness', ''), -1
        )
        eff_b = self.AUTH_EFF_ORDER.get(
            getattr(event_b, 'authority_effectiveness', ''), -1
        )
        if eff_a > eff_b:
            return tx_a, tx_b, f'T8-R1: CRITICAL_INTERRUPT {eff_a}>{eff_b}', False
        elif eff_b > eff_a:
            return tx_b, tx_a, f'T8-R1: CRITICAL_INTERRUPT {eff_b}>{eff_a}', False
        else:
            # Empate → ARBITRATION_PENDING
            return tx_a, tx_b, 'T8-R1: empate CRITICAL_INTERRUPT', True

    def _arbitrate_normal(self, tx_a, tx_b):
        risk_a = RISK_LEVEL_ORDER.get(tx_a.get('target_risk_level', 'SAFE'), 0)
        risk_b = RISK_LEVEL_ORDER.get(tx_b.get('target_risk_level', 'SAFE'), 0)
        if risk_a >= risk_b:
            reason = f'T8-R2: NORMAL target_risk {tx_a["target_risk_level"]}>={tx_b["target_risk_level"]}'
            return tx_a, tx_b, reason, False
        else:
            reason = f'T8-R2: NORMAL target_risk {tx_b["target_risk_level"]}>{tx_a["target_risk_level"]}'
            return tx_b, tx_a, reason, False

    def _arbitrate_recovery(self, tx_a, tx_b, state: CompoundState):
        """
        RECOVERY: gana la más conservadora (menor reducción de R-Level).
        Menor reducción = target restriction level más alto (más cercano al actual).
        """
        current_r = state.restriction_order()
        target_r_a = RESTRICTION_LEVEL_ORDER.get(tx_a.get('target_restriction_level', 'NONE'), 0)
        target_r_b = RESTRICTION_LEVEL_ORDER.get(tx_b.get('target_restriction_level', 'NONE'), 0)
        # La más conservadora es la que reduce menos (target más alto)
        if target_r_a >= target_r_b:
            reason = f'T8-R3: RECOVERY conservadora target_r {tx_a["target_restriction_level"]}>={tx_b["target_restriction_level"]}'
            return tx_a, tx_b, reason, False
        else:
            reason = f'T8-R3: RECOVERY conservadora target_r {tx_b["target_restriction_level"]}>{tx_a["target_restriction_level"]}'
            return tx_b, tx_a, reason, False


# ---------------------------------------------------------------------------
# Nodo principal
# ---------------------------------------------------------------------------

class SafetyOrchestratorG1(Node):
    """
    safety_orchestrator_g1 — Etapa 3C implementación real.

    Threading model (ADR-002):
      Thread 1 (ROS2 executor): callbacks de topic → ingest al buffer
      Thread 2 (evaluation loop): drain buffer → evaluate → execute → publish
      Thread 3 (heartbeat): publica diagnostics periódicamente

    Candados:
      _buffer_lock + _buffer_condition: acceso al deque de ingesta
      _state_lock: snapshot de CompoundState para Thread 3 y publish
    """

    def __init__(self):
        super().__init__('safety_orchestrator_g1')

        # QoS profiles
        reliable_qos = QoSProfile(
            reliability=ReliabilityPolicy.RELIABLE,
            history=HistoryPolicy.KEEP_LAST,
            depth=50,
        )
        transient_local_qos = QoSProfile(
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.TRANSIENT_LOCAL,
            history=HistoryPolicy.KEEP_LAST,
            depth=1,
        )
        actions_qos = QoSProfile(
            reliability=ReliabilityPolicy.RELIABLE,
            history=HistoryPolicy.KEEP_LAST,
            depth=10,
        )
        diag_qos = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            history=HistoryPolicy.KEEP_LAST,
            depth=10,
        )

        # Publishers
        self._pub_system_state = self.create_publisher(SystemState, '/system_state', transient_local_qos)
        self._pub_safety_events = self.create_publisher(SafetyEvent, '/safety_events', reliable_qos)
        self._pub_safety_actions = self.create_publisher(SafetyAction, '/safety_actions', actions_qos)
        self._pub_diagnostics = self.create_publisher(DiagnosticArray, '/diagnostics', diag_qos)

        # Subscriber — self-feedback guard crítico (ADR-002)
        self._sub_safety_events = self.create_subscription(
            SafetyEvent,
            '/safety_events',
            self._on_safety_event,
            reliable_qos,
        )

        # Estado del sistema — propiedad exclusiva de Thread 2
        self._compound_state = CompoundState()

        # Thread-safety
        self._buffer_lock = threading.Lock()
        self._buffer_condition = threading.Condition(self._buffer_lock)
        self._ingest_buffer: deque = deque(maxlen=EVENT_BUFFER_MAXLEN)
        self._ingest_overflow_count = 0

        self._state_lock = threading.Lock()  # para snapshots externos

        # Scheduler + Evaluator + Arbitrator
        self._scheduler = PriorityScheduler()
        self._evaluator = TransitionEvaluator()
        self._arbitrator = T8Arbitrator()

        # Tracking de transición en curso
        self._active_transition_priority: Optional[str] = None
        self._arbitration_pending_since: Optional[float] = None

        # Shutdown
        self._shutdown_event = threading.Event()

        # Contadores de auditoría
        self._transition_count: int = 0
        self._arbitration_count: int = 0
        self._overflow_count: int = 0

        # --- Threads ---
        self._eval_thread = threading.Thread(
            target=self._evaluation_loop,
            name='safety_orchestrator_eval',
            daemon=True,
        )
        self._heartbeat_timer = self.create_timer(
            1.0 / HEARTBEAT_HZ,
            self._publish_heartbeat,
        )

        self._eval_thread.start()

        # Publicar estado inicial — Transient Local para late joiners
        self._publish_system_state('INIT')
        self.get_logger().info(
            '[safety_orchestrator_g1] Iniciado — 3C transition logic real activa. '
            'Estado inicial: (SAFE, NONE). T8 DRAFT activo.'
        )

    # -----------------------------------------------------------------------
    # Thread 1 — ROS2 executor: ingesta de eventos
    # -----------------------------------------------------------------------

    def _on_safety_event(self, msg: SafetyEvent):
        """
        Callback Thread 1.
        Solo ingest + notify. No evalúa, no modifica estado.

        Self-feedback guard: ignora eventos propios (ADR-002 corrección sesión anterior).
        """
        # Guard: no procesar eventos propios
        if getattr(msg, 'source', '') == SELF_SOURCE:
            return

        with self._buffer_condition:
            if len(self._ingest_buffer) >= EVENT_BUFFER_MAXLEN:
                self._ingest_overflow_count += 1
                self._overflow_count += 1
                self.get_logger().warn(
                    f'[orchestrator] Buffer overflow — evento descartado. '
                    f'Total overflows: {self._overflow_count}. '
                    f'event_type={getattr(msg, "event_type", "?")}'
                )
                return
            self._ingest_buffer.append(msg)
            self._buffer_condition.notify()

    # -----------------------------------------------------------------------
    # Thread 2 — Evaluation loop
    # -----------------------------------------------------------------------

    def _evaluation_loop(self):
        """
        Loop dedicado de evaluación — Thread 2.
        Propiedad exclusiva de _compound_state.
        """
        self.get_logger().debug('[orchestrator eval_loop] Iniciado')

        while not self._shutdown_event.is_set():
            # Esperar con timeout para no quemar CPU
            with self._buffer_condition:
                self._buffer_condition.wait(timeout=EVALUATION_TIMEOUT_S)
                # Drain del buffer al scheduler
                batch = list(self._ingest_buffer)
                self._ingest_buffer.clear()

            if not batch:
                # Verificar ARBITRATION_PENDING timeout
                self._check_arbitration_timeout()
                continue

            # Enqueue al scheduler con prioridad del evento
            for msg in batch:
                priority = getattr(msg, 'transition_priority', 'NORMAL')
                # Mapear priority string a bucket name correcto
                bucket_priority = self._map_priority(priority)
                scheduled = self._scheduler.enqueue(msg, bucket_priority)
                # ACK observable (P7 — toda transición produce evidencia)
                self._publish_ack(msg, scheduled.event_id)

            # Procesar batch del scheduler en orden de prioridad
            scheduled_events = self._scheduler.drain_all()
            self._process_scheduled_batch(scheduled_events)

    def _map_priority(self, priority_str: str) -> str:
        """Normaliza el priority string del SafetyEvent al nombre de bucket."""
        mapping = {
            'CRITICAL_INTERRUPT': 'CRITICAL_INTERRUPT',
            'COMMIT_TERMINAL':    'COMMIT_TERMINAL',
            'NORMAL':             'NORMAL',
            'RECOVERY':           'RECOVERY',
        }
        return mapping.get(priority_str, 'NORMAL')

    def _process_scheduled_batch(self, scheduled_events: list):
        """
        Procesa un batch de ScheduledEvents en orden de prioridad.

        Reglas de preemption (ADR-002 + T5):
        - CRITICAL_INTERRUPT preempta cualquier transición NORMAL o RECOVERY en curso.
        - COMMIT_TERMINAL es irreversible post-commit — no interrumpible.
        - RECOVERY solo ejecuta si no hay escalation activa.

        T8 arbitration: si dos eventos del mismo bucket producen transiciones
        aplicables simultáneamente, usa T8Arbitrator.
        """
        # Agrupar por bucket para detectar conflictos dentro del mismo bucket
        by_bucket: dict[int, list] = defaultdict(list)
        for se in scheduled_events:
            by_bucket[se.bucket].append(se)

        # Procesar en orden de bucket (0=CRITICAL_INTERRUPT primero)
        for bucket_idx in sorted(by_bucket.keys()):
            bucket_name = BUCKET_NAMES[bucket_idx]
            events_in_bucket = by_bucket[bucket_idx]

            # RECOVERY: no ejecutar si hay escalation activa (CRITICAL_INTERRUPT o NORMAL en estado riesgo)
            if bucket_idx == BUCKET_RECOVERY:
                if self._compound_state.risk_order() > RISK_LEVEL_ORDER['CAUTION']:
                    self.get_logger().debug(
                        '[orchestrator] RECOVERY inhibido — escalation activa en curso'
                    )
                    continue

            # Evaluar cada evento del bucket contra el estado actual
            applicable: list[tuple] = []  # (transition_dict, scheduled_event)
            for se in events_in_bucket:
                tx = self._evaluator.evaluate(se.msg, self._compound_state)
                if tx is not None:
                    applicable.append((tx, se))

            if not applicable:
                continue

            if len(applicable) == 1:
                tx, se = applicable[0]
                self._execute_transition(tx, se.msg)
            else:
                # Conflicto dentro del bucket — T8 arbitration
                self._arbitration_count += 1
                winner = self._arbitrate_batch(applicable)
                if winner:
                    tx, se = winner
                    self._execute_transition(tx, se.msg)
                else:
                    # ARBITRATION_PENDING
                    self._set_arbitration_pending()

    def _arbitrate_batch(self, applicable: list) -> Optional[tuple]:
        """
        Aplica T8 iterativamente sobre múltiples candidatos.
        Retorna (tx, scheduled_event) ganador, o None si ARBITRATION_PENDING.
        """
        winner_tx, winner_se = applicable[0]
        for tx_b, se_b in applicable[1:]:
            w, _, reason, pending = self._arbitrator.arbitrate(
                winner_tx, tx_b, winner_se.msg, se_b.msg, self._compound_state
            )
            self.get_logger().info(f'[orchestrator T8] {reason} — pending={pending}')
            if pending:
                return None
            # winner_tx es el ganador de esta iteración
            if w is tx_b:
                winner_tx, winner_se = tx_b, se_b
        return (winner_tx, winner_se)

    def _execute_transition(self, tx: dict, triggering_event):
        """
        Ejecuta una transición validada.

        1. Verifica precondiciones finales (R5 committed, tipo de autoridad)
        2. Actualiza CompoundState
        3. Publica SafetyAction
        4. Publica SystemState actualizado
        5. Publica SafetyEvent de resultado
        """
        transition_id = tx['transition_id']
        execution_authority = tx.get('execution_authority', 'AUTONOMOUS')
        runtime_action = tx['runtime_action']

        # HUMAN_REQUIRED: registrar intent sin ejecutar acción real sobre hardware
        if execution_authority == 'HUMAN_REQUIRED':
            self.get_logger().warn(
                f'[orchestrator] {transition_id} HUMAN_REQUIRED — '
                f'acción {runtime_action} requiere autorización explícita. '
                f'Sin SDK G1: log de intent solamente.'
            )
            # Continúa la actualización de estado para reflejar intent

        # Actualizar estado — propiedad exclusiva Thread 2
        prev_state = self._compound_state.compound_key()
        self._compound_state.risk_level = tx['target_risk_level']
        self._compound_state.restriction_level = tx['target_restriction_level']
        self._compound_state.last_transition_id = transition_id
        self._compound_state.execution_confidence = tx.get('execution_confidence', 'BEST_EFFORT')
        self._compound_state.timestamp = time.time()

        # Marcar R5 committed si aplica (T5 — irreversible)
        if tx['transition_priority'] == 'COMMIT_TERMINAL' and tx['target_restriction_level'] == 'R5':
            self._compound_state.r5_committed = True
            self.get_logger().warn(
                '[orchestrator] R5 COMMITTED — estado terminal irreversible. '
                'Solo recovery manual posible.'
            )

        # Reset arbitration_pending si la transición resuelve el estado
        if self._compound_state.arbitration_pending:
            self._compound_state.arbitration_pending = False
            self._arbitration_pending_since = None

        self._transition_count += 1

        new_state = self._compound_state.compound_key()
        self.get_logger().info(
            f'[orchestrator] TRANSICIÓN {transition_id}: '
            f'{prev_state} → {new_state} | '
            f'action={runtime_action} | '
            f'priority={tx["transition_priority"]} | '
            f'confidence={tx["execution_confidence"]}'
        )

        # Publicar — P7: toda transición produce evidencia observable
        self._publish_safety_action(tx, triggering_event)
        self._publish_system_state(transition_id)
        self._publish_transition_event(tx, triggering_event, prev_state)

    def _set_arbitration_pending(self):
        """Marca ARBITRATION_PENDING y publica evento observable (T4, T8)."""
        self._compound_state.arbitration_pending = True
        self._arbitration_pending_since = time.monotonic()

        self.get_logger().warn(
            '[orchestrator T8] ARBITRATION_PENDING — conflicto no resuelto. '
            'Estado mantenido hasta resolución.'
        )

        event = SafetyEvent()
        event.event_type = 'ARBITRATION_PENDING'
        event.source = SELF_SOURCE
        event.source_authority = 'ORCHESTRATOR'
        event.authority_effectiveness = 'CONTESTED'
        event.risk_level = self._compound_state.risk_level
        event.restriction_level = self._compound_state.restriction_level
        event.transition_id = 'T8-PENDING'
        event.transition_priority = 'NORMAL'
        event.execution_confidence = 'BEST_EFFORT'
        event.notes = 'T8 DRAFT: conflicto no resuelto — ARBITRATION_PENDING'
        self._pub_safety_events.publish(event)

    def _check_arbitration_timeout(self):
        """
        Si ARBITRATION_PENDING supera ARBITRATION_PENDING_TIMEOUT_S,
        publica warning. No escala automáticamente — requiere intervención.
        """
        if not self._compound_state.arbitration_pending:
            return
        if self._arbitration_pending_since is None:
            return
        elapsed = time.monotonic() - self._arbitration_pending_since
        if elapsed > ARBITRATION_PENDING_TIMEOUT_S:
            self.get_logger().warn(
                f'[orchestrator] ARBITRATION_PENDING sin resolver por {elapsed:.1f}s '
                f'(umbral {ARBITRATION_PENDING_TIMEOUT_S}s). '
                f'Estado actual: {self._compound_state.compound_key()}'
            )

    # -----------------------------------------------------------------------
    # Publishers
    # -----------------------------------------------------------------------

    def _publish_ack(self, msg, event_id: str):
        """Publica ACK observable por cada evento recibido (P7)."""
        ack = SafetyEvent()
        ack.event_type = 'SCHEDULED'
        ack.source = SELF_SOURCE
        ack.source_authority = 'ORCHESTRATOR'
        ack.authority_effectiveness = ''
        ack.transition_id = getattr(msg, 'transition_id', '')
        ack.transition_priority = getattr(msg, 'transition_priority', 'NORMAL')
        ack.risk_level = self._compound_state.risk_level
        ack.restriction_level = self._compound_state.restriction_level
        ack.execution_confidence = 'VERIFIED'
        ack.notes = f'ACK event_id={event_id} enqueued'
        self._pub_safety_events.publish(ack)

    def _publish_safety_action(self, tx: dict, triggering_event):
        """Publica SafetyAction — acción primitiva ejecutada."""
        action = SafetyAction()
        action.action_name = tx['runtime_action']
        action.execution_authority = tx.get('execution_authority', 'AUTONOMOUS')
        action.transition_id = tx['transition_id']
        self._pub_safety_actions.publish(action)

    def _publish_system_state(self, last_transition_id: str):
        """Publica SystemState — estado actual del sistema."""
        msg = SystemState()
        msg.risk_level = self._compound_state.risk_level
        msg.restriction_level = self._compound_state.restriction_level
        msg.last_transition_id = last_transition_id
        msg.execution_confidence = self._compound_state.execution_confidence
        msg.arbitration_pending = self._compound_state.arbitration_pending
        msg.r5_committed = self._compound_state.r5_committed
        self._pub_system_state.publish(msg)

    def _publish_transition_event(self, tx: dict, triggering_event, prev_state: tuple):
        """Publica SafetyEvent describiendo la transición ejecutada."""
        event = SafetyEvent()
        event.event_type = f'TRANSITION_EXECUTED:{tx["transition_id"]}'
        event.source = SELF_SOURCE
        event.source_authority = 'ORCHESTRATOR'
        event.authority_effectiveness = tx.get('execution_confidence', 'VERIFIED')
        event.transition_id = tx['transition_id']
        event.transition_priority = tx['transition_priority']
        event.risk_level = self._compound_state.risk_level
        event.restriction_level = self._compound_state.restriction_level
        event.execution_confidence = tx.get('execution_confidence', 'VERIFIED')
        event.notes = tx.get('notes', '')
        self._pub_safety_events.publish(event)

    def _publish_heartbeat(self):
        """Thread 3 — heartbeat periódico en /diagnostics (P7)."""
        diag_array = DiagnosticArray()
        status = DiagnosticStatus()
        status.name = 'safety_orchestrator_g1'
        status.hardware_id = 'g1_ros2_pipeline'
        status.level = DiagnosticStatus.OK

        with self._state_lock:
            # Snapshot para Thread 3 — no accede directamente al CompoundState de Thread 2
            snapshot = self._compound_state.to_snapshot()

        status.values = [
            KeyValue(key='eval_thread_alive', value=str(self._eval_thread.is_alive())),
            KeyValue(key='risk_level', value=snapshot['risk_level']),
            KeyValue(key='restriction_level', value=snapshot['restriction_level']),
            KeyValue(key='last_transition_id', value=snapshot['last_transition_id']),
            KeyValue(key='execution_confidence', value=snapshot['execution_confidence']),
            KeyValue(key='arbitration_pending', value=str(snapshot['arbitration_pending'])),
            KeyValue(key='r5_committed', value=str(snapshot['r5_committed'])),
            KeyValue(key='transition_count', value=str(self._transition_count)),
            KeyValue(key='arbitration_count', value=str(self._arbitration_count)),
            KeyValue(key='overflow_count', value=str(self._overflow_count)),
        ]

        if not self._eval_thread.is_alive():
            status.level = DiagnosticStatus.ERROR
            status.message = 'CRITICAL: eval_thread no está vivo'

        if snapshot['arbitration_pending']:
            status.level = DiagnosticStatus.WARN

        if snapshot['r5_committed']:
            status.level = DiagnosticStatus.ERROR
            status.message = 'R5 COMMITTED — estado terminal'

        diag_array.status = [status]
        self._pub_diagnostics.publish(diag_array)

    # -----------------------------------------------------------------------
    # Lifecycle
    # -----------------------------------------------------------------------

    def destroy_node(self):
        """Shutdown limpio — join del eval_thread con timeout."""
        self.get_logger().info('[orchestrator] Shutdown iniciado')
        self._shutdown_event.set()
        with self._buffer_condition:
            self._buffer_condition.notify_all()
        self._eval_thread.join(timeout=2.0)
        if self._eval_thread.is_alive():
            self.get_logger().warn('[orchestrator] eval_thread no terminó en 2s')
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
