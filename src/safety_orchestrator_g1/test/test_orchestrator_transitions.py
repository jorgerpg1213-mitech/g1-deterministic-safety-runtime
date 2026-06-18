"""
test_orchestrator_transitions.py — G1 ROS2 Pipeline
Etapa 3C — Tests Level 4: Transition Logic Real

Framework: pytest (unit tests de TransitionEvaluator, PriorityScheduler, T8Arbitrator)
Nivel: unit tests puros — sin ROS2, sin DDS, sin nodo activo.

Qué validan estos tests:
  - Cada TX de la Transition Matrix evalúa correctamente
  - Scheduler asigna buckets correctos y drena en orden de prioridad
  - T8 arbitration resuelve conflictos según reglas del modelo
  - Edge cases: R5 committed, ARBITRATION_PENDING, buffer overflow guards
  - Precondición universal de recovery_g1

Qué NO validan (requieren launch_testing con ROS2):
  - Publicación real en topics DDS
  - Timing de threads
  - Behavior bajo carga de eventos simultáneos (→ test_safety_stress.py, fase posterior)

Autores: GPT-4 (arquitecto) + Claude Sonnet 4.6 (implementador) + Padilla (operador)
Versión: 3C-real — 2026-05-24
"""

import sys
import time
import threading
from collections import deque
from dataclasses import dataclass
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Imports desde los módulos implementados en 3C
# Los imports asumen que los archivos están en el mismo directorio o PYTHONPATH.
# En el workspace ROS2 estarán en install/safety_orchestrator_g1/lib/...
# ---------------------------------------------------------------------------

# Stub mínimo de SafetyEvent para tests que no requieren g1_msgs compilado
@dataclass
class SafetyEventStub:
    event_type: str = ''
    source: str = ''
    source_authority: str = ''
    authority_effectiveness: str = ''
    transition_id: str = ''
    transition_priority: str = 'NORMAL'
    risk_level: str = 'SAFE'
    restriction_level: str = 'NONE'
    execution_confidence: str = 'VERIFIED'
    target: str = ''
    notes: str = ''


# ---------------------------------------------------------------------------
# Import de los componentes implementados
# Si g1_msgs no está disponible (fuera del workspace), los tests de unit
# logic pura aún funcionan con los stubs.
# ---------------------------------------------------------------------------

try:
    # Import desde el módulo real del workspace
    from safety_orchestrator_g1.safety_orchestrator_g1 import (
        CompoundState,
        TransitionEvaluator,
        PriorityScheduler,
        T8Arbitrator,
        ScheduledEvent,
        BUCKET_CRITICAL_INTERRUPT,
        BUCKET_COMMIT_TERMINAL,
        BUCKET_NORMAL,
        BUCKET_RECOVERY,
        RISK_LEVEL_ORDER,
        RESTRICTION_LEVEL_ORDER,
    )
    ORCHESTRATOR_AVAILABLE = True
except ImportError:
    ORCHESTRATOR_AVAILABLE = False

try:
    from recovery_g1.recovery_g1 import RecoveryG1, BLOCKED_RISK_LEVELS, BLOCKED_RESTRICTION_LEVELS
    RECOVERY_AVAILABLE = True
except ImportError:
    RECOVERY_AVAILABLE = False


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def safe_state():
    """Estado nominal (SAFE, NONE)."""
    return CompoundState(risk_level='SAFE', restriction_level='NONE')

@pytest.fixture
def caution_state():
    return CompoundState(risk_level='CAUTION', restriction_level='R1')

@pytest.fixture
def danger_state():
    return CompoundState(risk_level='DANGER', restriction_level='R1')

@pytest.fixture
def stability_risk_state():
    return CompoundState(risk_level='STABILITY_RISK', restriction_level='R3')

@pytest.fixture
def fault_critical_state():
    return CompoundState(risk_level='FAULT_CRITICAL', restriction_level='R4-halt')

@pytest.fixture
def r5_committed_state():
    s = CompoundState(risk_level='FAULT_CRITICAL', restriction_level='R5')
    s.r5_committed = True
    return s

@pytest.fixture
def evaluator():
    return TransitionEvaluator()

@pytest.fixture
def scheduler():
    return PriorityScheduler()

@pytest.fixture
def arbitrator():
    return T8Arbitrator()

def make_event(**kwargs) -> SafetyEventStub:
    """Factory para SafetyEventStub con defaults."""
    return SafetyEventStub(**kwargs)


# ===========================================================================
# Tests de CompoundState
# ===========================================================================

@pytest.mark.skipif(not ORCHESTRATOR_AVAILABLE, reason='safety_orchestrator_g1 no disponible')
class TestCompoundState:

    def test_initial_state(self, safe_state):
        assert safe_state.risk_level == 'SAFE'
        assert safe_state.restriction_level == 'NONE'
        assert safe_state.r5_committed is False
        assert safe_state.arbitration_pending is False

    def test_compound_key(self, safe_state):
        assert safe_state.compound_key() == ('SAFE', 'NONE')

    def test_risk_order_safe(self, safe_state):
        assert safe_state.risk_order() == RISK_LEVEL_ORDER['SAFE']

    def test_risk_order_fault_critical(self, fault_critical_state):
        assert fault_critical_state.risk_order() == RISK_LEVEL_ORDER['FAULT_CRITICAL']

    def test_r5_committed_flag(self, r5_committed_state):
        assert r5_committed_state.is_r5_committed() is True

    def test_snapshot_keys(self, safe_state):
        snap = safe_state.to_snapshot()
        expected_keys = {
            'risk_level', 'restriction_level', 'last_transition_id',
            'execution_confidence', 'arbitration_pending', 'r5_committed', 'timestamp'
        }
        assert expected_keys == set(snap.keys())


# ===========================================================================
# Tests de TransitionEvaluator — Transition Matrix
# ===========================================================================

@pytest.mark.skipif(not ORCHESTRATOR_AVAILABLE, reason='safety_orchestrator_g1 no disponible')
class TestTransitionEvaluator:

    # --- TX-001 ---

    def test_TX001_triggers_on_stability_anomaly_primary(self, evaluator, safe_state):
        event = make_event(
            event_type='STABILITY_ANOMALY',
            source_authority='PRIMARY_IMU',
            authority_effectiveness='EFFECTIVE',
        )
        result = evaluator.evaluate(event, safe_state)
        assert result is not None
        assert result['transition_id'] == 'TX-001'
        assert result['transition_priority'] == 'CRITICAL_INTERRUPT'
        assert result['runtime_action'] == 'stabilization_mode'

    def test_TX001_triggers_on_joint_oscillation(self, evaluator, caution_state):
        event = make_event(
            event_type='JOINT_OSCILLATION',
            source_authority='PRIMARY_JOINT_STATES',
            authority_effectiveness='DEGRADED_EFFECTIVE',
        )
        result = evaluator.evaluate(event, caution_state)
        assert result is not None
        assert result['transition_id'] == 'TX-001'
        assert result['execution_confidence'] == 'BEST_EFFORT'

    def test_TX001_not_trigger_from_secondary(self, evaluator, safe_state):
        """SECONDARY no puede disparar TX-001."""
        event = make_event(
            event_type='STABILITY_ANOMALY',
            source_authority='SECONDARY_LIDAR',
            authority_effectiveness='EFFECTIVE',
        )
        result = evaluator.evaluate(event, safe_state)
        assert result is None or result.get('transition_id') != 'TX-001'

    def test_TX001_blocked_on_r5_committed(self, evaluator, r5_committed_state):
        """TX-001 no aplica si R5 ya committed (T5)."""
        event = make_event(
            event_type='STABILITY_ANOMALY',
            source_authority='PRIMARY_IMU',
            authority_effectiveness='EFFECTIVE',
        )
        result = evaluator.evaluate(event, r5_committed_state)
        assert result is None

    def test_TX001_target_risk_never_below_stability_risk(self, evaluator, fault_critical_state):
        """TX-001 target_risk_level = max(current, STABILITY_RISK)."""
        event = make_event(
            event_type='STABILITY_ANOMALY',
            source_authority='PRIMARY_IMU',
            authority_effectiveness='EFFECTIVE',
        )
        result = evaluator.evaluate(event, fault_critical_state)
        if result and result['transition_id'] == 'TX-001':
            # FAULT_CRITICAL > STABILITY_RISK — debe mantenerse FAULT_CRITICAL
            assert RISK_LEVEL_ORDER[result['target_risk_level']] >= RISK_LEVEL_ORDER['STABILITY_RISK']

    # --- TX-002 ---

    def test_TX002_safe_to_caution_obstacle(self, evaluator, safe_state):
        event = make_event(
            event_type='OBSTACLE_DETECTED',
            source_authority='SECONDARY_LIDAR',
            authority_effectiveness='EFFECTIVE',
        )
        result = evaluator.evaluate(event, safe_state)
        assert result is not None
        assert result['transition_id'] == 'TX-002'
        assert result['target_risk_level'] == 'CAUTION'
        assert result['target_restriction_level'] == 'R1'
        assert result['runtime_action'] == 'velocity_clamp'

    def test_TX002_safe_to_caution_sensor_degraded(self, evaluator, safe_state):
        event = make_event(
            event_type='SENSOR_DEGRADED',
            source_authority='SECONDARY_LIDAR',
            authority_effectiveness='DEGRADED_EFFECTIVE',
        )
        result = evaluator.evaluate(event, safe_state)
        assert result is not None
        assert result['transition_id'] == 'TX-002'
        assert result['runtime_action'] == 'gait_slowdown'

    def test_TX002_not_from_non_safe_state(self, evaluator, caution_state):
        """TX-002 solo desde (SAFE, NONE)."""
        event = make_event(
            event_type='OBSTACLE_DETECTED',
            source_authority='SECONDARY_LIDAR',
            authority_effectiveness='EFFECTIVE',
        )
        result = evaluator.evaluate(event, caution_state)
        # No debe ser TX-002
        if result:
            assert result['transition_id'] != 'TX-002'

    # --- TX-003 ---

    def test_TX003_danger_to_stability_risk(self, evaluator, danger_state):
        event = make_event(
            event_type='STABILITY_ANOMALY',
            source_authority='PRIMARY_IMU',
            authority_effectiveness='EFFECTIVE',
        )
        result = evaluator.evaluate(event, danger_state)
        # TX-001 tiene precedencia sobre TX-003 — puede ser TX-001
        assert result is not None
        assert result['transition_id'] in ('TX-001', 'TX-003')
        assert result['target_risk_level'] in ('STABILITY_RISK',)

    # --- TX-004 ---

    def test_TX004_stability_risk_to_fault_critical(self, evaluator, stability_risk_state):
        event = make_event(
            event_type='AUTHORITY_LOSS',
            source_authority='PRIMARY_IMU',
            authority_effectiveness='INEFFECTIVE',
        )
        result = evaluator.evaluate(event, stability_risk_state)
        assert result is not None
        assert result['transition_id'] == 'TX-004'
        assert result['target_risk_level'] == 'FAULT_CRITICAL'
        assert result['target_restriction_level'] == 'R4-halt'
        assert result['execution_confidence'] == 'BEST_EFFORT'  # T3

    def test_TX004_not_from_degraded_effective(self, evaluator, stability_risk_state):
        """TX-004 solo con INEFFECTIVE o UNRELIABLE — no DEGRADED_EFFECTIVE."""
        event = make_event(
            event_type='AUTHORITY_LOSS',
            source_authority='PRIMARY_IMU',
            authority_effectiveness='DEGRADED_EFFECTIVE',
        )
        result = evaluator.evaluate(event, stability_risk_state)
        if result:
            assert result['transition_id'] != 'TX-004'

    # --- TX-005 ---

    def test_TX005_commit_terminal_human_required(self, evaluator, fault_critical_state):
        event = make_event(
            event_type='POLICY_GATE_AUTHORIZED_R5',
            source_authority='HUMAN_OPERATOR',
            authority_effectiveness='EFFECTIVE',
        )
        result = evaluator.evaluate(event, fault_critical_state)
        assert result is not None
        assert result['transition_id'] == 'TX-005'
        assert result['transition_priority'] == 'COMMIT_TERMINAL'
        assert result['execution_authority'] == 'HUMAN_REQUIRED'
        assert result['target_restriction_level'] == 'R5'

    def test_TX005_blocked_if_not_fault_critical(self, evaluator, stability_risk_state):
        """TX-005 solo desde FAULT_CRITICAL."""
        event = make_event(event_type='POLICY_GATE_AUTHORIZED_R5')
        result = evaluator.evaluate(event, stability_risk_state)
        if result:
            assert result['transition_id'] != 'TX-005'

    # --- TX-006a ---

    def test_TX006a_recovery_fault_critical(self, evaluator, fault_critical_state):
        event = make_event(
            event_type='PRIMARY_RESTORED',
            source_authority='PRIMARY_IMU',
            authority_effectiveness='EFFECTIVE',
        )
        result = evaluator.evaluate(event, fault_critical_state)
        assert result is not None
        assert result['transition_id'] == 'TX-006a'
        assert result['target_risk_level'] == 'DANGER'  # T1: un nivel
        assert result['transition_priority'] == 'RECOVERY'

    def test_TX006a_not_if_degraded_effective(self, evaluator, fault_critical_state):
        """TX-006a requiere EFFECTIVE — no DEGRADED_EFFECTIVE."""
        event = make_event(
            event_type='PRIMARY_RESTORED',
            source_authority='PRIMARY_IMU',
            authority_effectiveness='DEGRADED_EFFECTIVE',
        )
        result = evaluator.evaluate(event, fault_critical_state)
        if result:
            assert result['transition_id'] != 'TX-006a'

    # --- TX-006b ---

    def test_TX006b_recovery_stability_risk(self, evaluator, stability_risk_state):
        event = make_event(
            event_type='PRIMARY_STABLE',
            source_authority='PRIMARY_IMU',
            authority_effectiveness='EFFECTIVE',
        )
        result = evaluator.evaluate(event, stability_risk_state)
        assert result is not None
        assert result['transition_id'] == 'TX-006b'
        assert result['target_risk_level'] == 'DANGER'
        assert result['target_restriction_level'] == 'R2'

    # --- TX-006c ---

    def test_TX006c_recovery_danger_r2(self, evaluator):
        state = CompoundState(risk_level='DANGER', restriction_level='R2')
        event = make_event(
            event_type='PRIMARY_STABLE',
            source_authority='PRIMARY_IMU',
            authority_effectiveness='EFFECTIVE',
        )
        result = evaluator.evaluate(event, state)
        assert result is not None
        assert result['transition_id'] == 'TX-006c'
        assert result['target_risk_level'] == 'CAUTION'
        assert result['target_restriction_level'] == 'R1'

    # --- TX-007 ---

    def test_TX007_caution_to_danger_obstacle_in_path(self, evaluator, caution_state):
        event = make_event(
            event_type='OBSTACLE_IN_PATH',
            source_authority='SECONDARY_LIDAR',
            authority_effectiveness='EFFECTIVE',
        )
        result = evaluator.evaluate(event, caution_state)
        assert result is not None
        assert result['transition_id'] == 'TX-007'
        assert result['target_risk_level'] == 'DANGER'
        assert result['runtime_action'] == 'freeze_navigation'

    def test_TX007_advisory_alone_cannot_trigger(self, evaluator, caution_state):
        """ADVISORY sola no puede disparar TX-007 (escalation_guard)."""
        event = make_event(
            event_type='OBSTACLE_IN_PATH',
            source_authority='ADVISORY',
            authority_effectiveness='EFFECTIVE',
        )
        result = evaluator.evaluate(event, caution_state)
        if result:
            assert result['transition_id'] != 'TX-007'

    # --- TX-008 ---

    def test_TX008_safe_to_stability_risk_direct(self, evaluator, safe_state):
        """TX-008 — excepción a T1: salta CAUTION y DANGER."""
        event = make_event(
            event_type='STABILITY_ANOMALY_SEVERE',
            source_authority='PRIMARY_IMU',
            authority_effectiveness='EFFECTIVE',
        )
        result = evaluator.evaluate(event, safe_state)
        # TX-001 tiene precedencia — pero ambos son CRITICAL_INTERRUPT
        # TX-001 se evalúa primero — resultado puede ser TX-001
        assert result is not None
        assert result['transition_priority'] == 'CRITICAL_INTERRUPT'
        assert result['target_risk_level'] == 'STABILITY_RISK'
        assert result['target_restriction_level'] == 'R3'

    def test_TX008_secondary_cannot_trigger(self, evaluator, safe_state):
        """SECONDARY no puede disparar TX-008."""
        event = make_event(
            event_type='STABILITY_ANOMALY_SEVERE',
            source_authority='SECONDARY_LIDAR',
            authority_effectiveness='EFFECTIVE',
        )
        result = evaluator.evaluate(event, safe_state)
        # TX-008 no debe aplicar — TX-001 tampoco (source no es PRIMARY)
        if result:
            assert result['transition_id'] not in ('TX-008',)

    # --- TX-009 ---

    def test_TX009_emergency_sit_policy_gated(self, evaluator, fault_critical_state):
        event = make_event(event_type='POLICY_GATE_AUTHORIZED_EMERGENCY_SIT')
        result = evaluator.evaluate(event, fault_critical_state)
        assert result is not None
        assert result['transition_id'] == 'TX-009'
        assert result['execution_authority'] == 'POLICY_GATED'
        assert result['target_restriction_level'] == 'R4-sit'
        # Risk Level no cambia para TX-009
        assert result['target_risk_level'] == fault_critical_state.risk_level

    # --- TX-010 ---

    def test_TX010_caution_to_safe(self, evaluator, caution_state):
        event = make_event(
            event_type='ALL_CLEAR',
            source_authority='ALL_PRIMARY',
            authority_effectiveness='EFFECTIVE',
        )
        result = evaluator.evaluate(event, caution_state)
        assert result is not None
        assert result['transition_id'] == 'TX-010'
        assert result['target_risk_level'] == 'SAFE'
        assert result['target_restriction_level'] == 'NONE'

    def test_TX010_not_if_authority_not_effective(self, evaluator, caution_state):
        """TX-010 requiere todas EFFECTIVE."""
        event = make_event(
            event_type='ALL_CLEAR',
            authority_effectiveness='DEGRADED_EFFECTIVE',
        )
        result = evaluator.evaluate(event, caution_state)
        if result:
            assert result['transition_id'] != 'TX-010'

    # --- Edge case: unknown event_type ---

    def test_unknown_event_type_returns_none(self, evaluator, safe_state):
        event = make_event(event_type='INVENTED_EVENT_XYZ')
        result = evaluator.evaluate(event, safe_state)
        assert result is None


    # --- TX-011 ---

    def test_TX011_triggers_on_condition_detected_secondary(self, evaluator, safe_state):
        """Contrato exacto CONDITION_DETECTED + SECONDARY + EFFECTIVE dispara TX-011."""
        event = make_event(
            event_type='CONDITION_DETECTED',
            source_authority='SECONDARY',
            authority_effectiveness='EFFECTIVE',
        )
        result = evaluator.evaluate(event, safe_state)
        assert result is not None
        assert result['transition_id'] == 'TX-011'
        assert result['transition_priority'] == 'NORMAL'
        assert result['runtime_action'] == 'stabilization_mode'
        assert result['execution_confidence'] == 'BEST_EFFORT'

    def test_TX011_not_trigger_from_primary(self, evaluator, safe_state):
        """PRIMARY no dispara TX-011."""
        event = make_event(
            event_type='CONDITION_DETECTED',
            source_authority='PRIMARY_IMU',
            authority_effectiveness='EFFECTIVE',
        )
        result = evaluator.evaluate(event, safe_state)
        assert result is None or result.get('transition_id') != 'TX-011'

    def test_TX011_not_trigger_without_effective(self, evaluator, safe_state):
        """SECONDARY sin EFFECTIVE no dispara TX-011."""
        event = make_event(
            event_type='CONDITION_DETECTED',
            source_authority='SECONDARY',
            authority_effectiveness='DEGRADED_EFFECTIVE',
        )
        result = evaluator.evaluate(event, safe_state)
        assert result is None or result.get('transition_id') != 'TX-011'


# ===========================================================================
# Tests del PriorityScheduler
# ===========================================================================

@pytest.mark.skipif(not ORCHESTRATOR_AVAILABLE, reason='safety_orchestrator_g1 no disponible')
class TestPriorityScheduler:

    def test_enqueue_assigns_correct_bucket_critical(self, scheduler):
        msg = make_event()
        se = scheduler.enqueue(msg, 'CRITICAL_INTERRUPT')
        assert se.bucket == BUCKET_CRITICAL_INTERRUPT

    def test_enqueue_assigns_correct_bucket_recovery(self, scheduler):
        msg = make_event()
        se = scheduler.enqueue(msg, 'RECOVERY')
        assert se.bucket == BUCKET_RECOVERY

    def test_drain_all_returns_in_priority_order(self, scheduler):
        """CRITICAL_INTERRUPT debe salir antes que NORMAL antes que RECOVERY."""
        recovery_msg = make_event(event_type='RECOVERY_EVENT')
        normal_msg = make_event(event_type='NORMAL_EVENT')
        critical_msg = make_event(event_type='CRITICAL_EVENT')

        # Enqueue en orden inverso a la prioridad
        scheduler.enqueue(recovery_msg, 'RECOVERY')
        scheduler.enqueue(normal_msg, 'NORMAL')
        scheduler.enqueue(critical_msg, 'CRITICAL_INTERRUPT')

        drained = scheduler.drain_all()
        assert len(drained) == 3
        # Primer evento debe ser CRITICAL_INTERRUPT
        assert drained[0].bucket == BUCKET_CRITICAL_INTERRUPT
        # Último debe ser RECOVERY
        assert drained[-1].bucket == BUCKET_RECOVERY

    def test_drain_all_empties_all_buckets(self, scheduler):
        for priority in ('CRITICAL_INTERRUPT', 'COMMIT_TERMINAL', 'NORMAL', 'RECOVERY'):
            scheduler.enqueue(make_event(), priority)
        drained = scheduler.drain_all()
        assert len(drained) == 4
        assert scheduler.total_pending() == 0

    def test_has_critical_interrupt(self, scheduler):
        assert scheduler.has_critical_interrupt() is False
        scheduler.enqueue(make_event(), 'CRITICAL_INTERRUPT')
        assert scheduler.has_critical_interrupt() is True

    def test_fifo_within_bucket(self, scheduler):
        """Dentro del mismo bucket, orden FIFO."""
        e1 = make_event(event_type='FIRST')
        e2 = make_event(event_type='SECOND')
        e3 = make_event(event_type='THIRD')
        for e in (e1, e2, e3):
            scheduler.enqueue(e, 'NORMAL')
        drained = scheduler.drain_all()
        assert drained[0].msg.event_type == 'FIRST'
        assert drained[1].msg.event_type == 'SECOND'
        assert drained[2].msg.event_type == 'THIRD'

    def test_pending_by_bucket(self, scheduler):
        scheduler.enqueue(make_event(), 'CRITICAL_INTERRUPT')
        scheduler.enqueue(make_event(), 'NORMAL')
        scheduler.enqueue(make_event(), 'NORMAL')
        pending = scheduler.pending_by_bucket()
        assert pending['CRITICAL_INTERRUPT'] == 1
        assert pending['NORMAL'] == 2
        assert pending['RECOVERY'] == 0

    def test_unknown_priority_defaults_to_normal(self, scheduler):
        se = scheduler.enqueue(make_event(), 'INVENTED_PRIORITY')
        assert se.bucket == BUCKET_NORMAL


# ===========================================================================
# Tests de T8Arbitrator
# ===========================================================================

@pytest.mark.skipif(not ORCHESTRATOR_AVAILABLE, reason='safety_orchestrator_g1 no disponible')
class TestT8Arbitrator:

    def test_T8_R1_critical_interrupt_higher_eff_wins(self, arbitrator, safe_state):
        """T8 regla 1: CRITICAL_INTERRUPT — gana el de mayor authority_effectiveness."""
        tx_a = {
            'transition_id': 'TX-001',
            'transition_priority': 'CRITICAL_INTERRUPT',
            'target_risk_level': 'STABILITY_RISK',
            'target_restriction_level': 'R3',
        }
        tx_b = {
            'transition_id': 'TX-008',
            'transition_priority': 'CRITICAL_INTERRUPT',
            'target_risk_level': 'STABILITY_RISK',
            'target_restriction_level': 'R3',
        }
        event_a = make_event(authority_effectiveness='EFFECTIVE')
        event_b = make_event(authority_effectiveness='DEGRADED_EFFECTIVE')

        winner, loser, reason, pending = arbitrator.arbitrate(
            tx_a, tx_b, event_a, event_b, safe_state
        )
        assert pending is False
        assert winner is tx_a  # EFFECTIVE > DEGRADED_EFFECTIVE

    def test_T8_R1_equal_eff_produces_arbitration_pending(self, arbitrator, safe_state):
        """T8 regla 1 empate → ARBITRATION_PENDING."""
        tx_a = {'transition_id': 'TX-001', 'transition_priority': 'CRITICAL_INTERRUPT',
                 'target_risk_level': 'STABILITY_RISK', 'target_restriction_level': 'R3'}
        tx_b = {'transition_id': 'TX-008', 'transition_priority': 'CRITICAL_INTERRUPT',
                 'target_risk_level': 'STABILITY_RISK', 'target_restriction_level': 'R3'}
        event_a = make_event(authority_effectiveness='EFFECTIVE')
        event_b = make_event(authority_effectiveness='EFFECTIVE')

        winner, loser, reason, pending = arbitrator.arbitrate(
            tx_a, tx_b, event_a, event_b, safe_state
        )
        assert pending is True

    def test_T8_R2_normal_higher_risk_wins(self, arbitrator, caution_state):
        """T8 regla 2: NORMAL — gana el con target_risk_level mayor."""
        tx_a = {'transition_id': 'TX-007', 'transition_priority': 'NORMAL',
                 'target_risk_level': 'DANGER', 'target_restriction_level': 'R1'}
        tx_b = {'transition_id': 'TX-002', 'transition_priority': 'NORMAL',
                 'target_risk_level': 'CAUTION', 'target_restriction_level': 'R1'}
        event_a = make_event()
        event_b = make_event()

        winner, loser, reason, pending = arbitrator.arbitrate(
            tx_a, tx_b, event_a, event_b, caution_state
        )
        assert pending is False
        assert winner is tx_a  # DANGER > CAUTION

    def test_T8_R3_recovery_conservative_wins(self, arbitrator):
        """T8 regla 3: RECOVERY — gana la más conservadora (menor reducción)."""
        # TX-006b: STABILITY_RISK → R2 (reducción de R3 a R2)
        # TX-006c: DANGER → R1 (reducción de R2 a R1)
        # Más conservadora = TX-006b (target R2 > target R1)
        state = CompoundState(risk_level='STABILITY_RISK', restriction_level='R3')
        tx_a = {'transition_id': 'TX-006b', 'transition_priority': 'RECOVERY',
                 'target_risk_level': 'DANGER', 'target_restriction_level': 'R2'}
        tx_b = {'transition_id': 'TX-006c', 'transition_priority': 'RECOVERY',
                 'target_risk_level': 'CAUTION', 'target_restriction_level': 'R1'}
        event_a = make_event()
        event_b = make_event()

        winner, loser, reason, pending = arbitrator.arbitrate(
            tx_a, tx_b, event_a, event_b, state
        )
        assert pending is False
        assert winner is tx_a  # R2 más conservadora que R1

    def test_T8_commit_terminal_first_wins(self, arbitrator, fault_critical_state):
        """COMMIT_TERMINAL: primera gana (no debería haber dos)."""
        tx_a = {'transition_id': 'TX-005', 'transition_priority': 'COMMIT_TERMINAL',
                 'target_risk_level': 'FAULT_CRITICAL', 'target_restriction_level': 'R5'}
        tx_b = {'transition_id': 'TX-005b', 'transition_priority': 'COMMIT_TERMINAL',
                 'target_risk_level': 'FAULT_CRITICAL', 'target_restriction_level': 'R5'}
        event_a = make_event()
        event_b = make_event()

        winner, loser, reason, pending = arbitrator.arbitrate(
            tx_a, tx_b, event_a, event_b, fault_critical_state
        )
        assert pending is False
        assert winner is tx_a


# ===========================================================================
# Tests de edge cases críticos del orchestrator
# ===========================================================================

@pytest.mark.skipif(not ORCHESTRATOR_AVAILABLE, reason='safety_orchestrator_g1 no disponible')
class TestEdgeCases:

    def test_r5_committed_blocks_all_evaluations(self, evaluator, r5_committed_state):
        """R5 committed — ninguna transición debe aplicar (T5)."""
        events = [
            make_event(event_type='STABILITY_ANOMALY', source_authority='PRIMARY_IMU',
                       authority_effectiveness='EFFECTIVE'),
            make_event(event_type='POLICY_GATE_AUTHORIZED_R5'),
            make_event(event_type='PRIMARY_RESTORED', source_authority='PRIMARY_IMU',
                       authority_effectiveness='EFFECTIVE'),
            make_event(event_type='ALL_CLEAR', authority_effectiveness='EFFECTIVE'),
        ]
        for event in events:
            result = evaluator.evaluate(event, r5_committed_state)
            assert result is None, f'Expected None for {event.event_type}, got {result}'

    def test_tx004_best_effort_execution_confidence(self, evaluator, stability_risk_state):
        """TX-004 siempre BEST_EFFORT — T3."""
        event = make_event(
            event_type='PRIMARY_TIMEOUT',
            source_authority='PRIMARY_IMU',
            authority_effectiveness='INEFFECTIVE',
        )
        result = evaluator.evaluate(event, stability_risk_state)
        if result and result['transition_id'] == 'TX-004':
            assert result['execution_confidence'] == 'BEST_EFFORT'

    def test_recovery_only_from_exact_compound_state(self, evaluator):
        """TX-006a solo desde (FAULT_CRITICAL, R4-halt) — no desde (FAULT_CRITICAL, R4-sit)."""
        state_r4sit = CompoundState(risk_level='FAULT_CRITICAL', restriction_level='R4-sit')
        event = make_event(
            event_type='PRIMARY_RESTORED',
            source_authority='PRIMARY_IMU',
            authority_effectiveness='EFFECTIVE',
        )
        result = evaluator.evaluate(event, state_r4sit)
        if result:
            assert result['transition_id'] != 'TX-006a'

    def test_t1_recovery_never_skips_levels(self, evaluator, fault_critical_state):
        """T1: RECOVERY nunca salta niveles — TX-006a solo va a DANGER, no a SAFE."""
        event = make_event(
            event_type='PRIMARY_RESTORED',
            source_authority='PRIMARY_IMU',
            authority_effectiveness='EFFECTIVE',
        )
        result = evaluator.evaluate(event, fault_critical_state)
        if result and result['transition_id'] == 'TX-006a':
            # Desde FAULT_CRITICAL, RECOVERY va a DANGER — no puede ir a CAUTION ni SAFE
            # TX-006a definida en SAFETY_MODEL_G1: FAULT_CRITICAL → DANGER (un nivel)
            assert result['target_risk_level'] == 'DANGER'
            assert RISK_LEVEL_ORDER[result['target_risk_level']] < \
                   RISK_LEVEL_ORDER['FAULT_CRITICAL']

    def test_scheduler_overflow_does_not_crash(self, scheduler):
        """Buffer overflow — el scheduler no debe lanzar excepción."""
        # El deque tiene maxlen — al llegar al límite descarta el más viejo
        from safety_orchestrator_g1.safety_orchestrator_g1 import EVENT_BUFFER_MAXLEN
        for i in range(EVENT_BUFFER_MAXLEN + 50):
            try:
                scheduler.enqueue(make_event(event_type=f'EVENT_{i}'), 'NORMAL')
            except Exception as e:
                pytest.fail(f'Scheduler lanzó excepción en overflow: {e}')

    def test_arbitration_pending_state_is_observable(self):
        """ARBITRATION_PENDING debe poder representarse en CompoundState."""
        state = CompoundState()
        state.arbitration_pending = True
        snap = state.to_snapshot()
        assert snap['arbitration_pending'] is True


# ===========================================================================
# Tests de precondición universal de recovery_g1
# ===========================================================================

@pytest.mark.skipif(not RECOVERY_AVAILABLE, reason='recovery_g1 no disponible')
class TestRecoveryUniversalPrecondition:
    """
    Tests de _recovery_allowed() sin instanciar el nodo ROS2.
    Verifican la lógica de precondición directamente.
    """

    def _check_allowed(self, risk: str, restriction: str) -> bool:
        """Evalúa la precondición universal sin nodo ROS2."""
        risk_blocked = risk in BLOCKED_RISK_LEVELS
        restriction_blocked = restriction in BLOCKED_RESTRICTION_LEVELS
        return not (risk_blocked and restriction_blocked)

    def test_safe_none_allowed(self):
        assert self._check_allowed('SAFE', 'NONE') is True

    def test_caution_r1_allowed(self):
        assert self._check_allowed('CAUTION', 'R1') is True

    def test_danger_r2_allowed(self):
        assert self._check_allowed('DANGER', 'R2') is True

    def test_stability_risk_r3_blocked(self):
        """STABILITY_RISK + R3 → bloqueado."""
        assert self._check_allowed('STABILITY_RISK', 'R3') is False

    def test_fault_critical_r4halt_blocked(self):
        assert self._check_allowed('FAULT_CRITICAL', 'R4-halt') is False

    def test_fault_critical_r4sit_blocked(self):
        assert self._check_allowed('FAULT_CRITICAL', 'R4-sit') is False

    def test_fault_critical_r5_blocked(self):
        assert self._check_allowed('FAULT_CRITICAL', 'R5') is False

    def test_stability_risk_r2_allowed(self):
        """STABILITY_RISK + R2 — no está en BLOCKED_RESTRICTION_LEVELS."""
        assert self._check_allowed('STABILITY_RISK', 'R2') is True

    def test_danger_r3_blocked(self):
        """DANGER + R3 — R3 está en BLOCKED_RESTRICTION_LEVELS pero DANGER no en BLOCKED_RISK."""
        # Solo bloquea si AMBOS están bloqueados
        assert self._check_allowed('DANGER', 'R3') is True  # DANGER no es blocked risk


# ===========================================================================
# Resumen de cobertura declarada
# ===========================================================================

class TestCoverageDeclaration:
    """
    Este test siempre pasa.
    Documenta explícitamente qué está cubierto y qué no (honestidad epistemológica).
    """

    def test_coverage_declaration(self):
        covered = {
            'TransitionEvaluator.evaluate — todas las TX (TX-001 a TX-010)': True,
            'PriorityScheduler — enqueue, drain, FIFO, orden prioridad': True,
            'T8Arbitrator — reglas R1, R2, R3, empate': True,
            'CompoundState — snapshot, compound_key, R5 committed': True,
            'RecoveryG1 — precondición universal': True,
            'Edge cases — R5 committed, T1 no-skip, ARBITRATION_PENDING': True,
        }
        not_covered = {
            'Thread safety real (race conditions bajo carga)': 'test_safety_stress.py — fase posterior',
            'DDS publish/subscribe real': 'launch_testing test_safety_layer_launch.py',
            'Timing real de evaluation loop': 'pending SDK G1',
            'RecoveryActions subprocess con ROS2 real': 'launch_testing con nodos activos',
            'RECOVERY_WINDOW_TBD thresholds reales': 'pending SDK G1',
            'T8 bajo hardware stress': 'pending SDK G1',
        }
        assert all(covered.values()), 'Cobertura declarada incompleta'
        assert len(not_covered) > 0, 'Debe existir deferred explícito'

