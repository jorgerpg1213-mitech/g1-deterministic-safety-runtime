#!/usr/bin/env python3
"""
Harness 4J-P3 — Timing Traceability Matrix
G1 Deterministic Safety Runtime — Microfase 4J-P3

Mide la latencia interna del runtime safety para rutas validadas en 4J-P2.
P3 es una fase de medicion, no de descubrimiento.
Principio PM: same behavior as P2, now with time.

PM approval: P3-A0 aprobado con 4+5 ajustes — 2026-06-23

Uso:
    python3 harness_4J_P3_timing_matrix.py --case <case> --n 10

Cases:
    stale          R2 Direct
    freeze         R3 Terminal
    naninf         R3 Terminal
    timestamp      R3 Terminal
    fallen_direct  R2 Direct fallback
    tx011_governed R1 Governed

RATE: excluido — declared limitation (detection-only, sin politica recovery).

PREFLIGHT (operador, antes de cada case group):
    docker restart boring_noether
    source /ws/install/setup.bash
    Verificar topologia segun case (ver mensajes [P3-PREFLIGHT]).
    El tiempo de docker restart NO es parte de la latencia medida.
    El restart NO se ejecuta dentro de este harness.

TIMING (ajuste PM #1):
    t0 = harness publish timestamp, medido inmediatamente antes de node._pub.publish(msg).
         No es el tiempo exacto de emision DDS. Es el reloj monotono local del harness
         capturado antes del publish call. Valido para medicion relativa interna.
    t1 (R2/R3) = tiempo capturado como primera linea del callback RecoveryEvent.
    t1 (R1)    = tiempo capturado como primera linea del callback SafetyAction.
    t2 (R1)    = tiempo capturado como primera linea del callback RecoveryEvent.

RCLPY LIFECYCLE (fix PM #1):
    rclpy.init()     — una vez por case group, en main().
    node create/destroy — por cada run, en _run_single().
    rclpy.shutdown() — una vez al final del batch, en main().
    No se llama init/shutdown dentro de _run_single().

TOPOLOGY DIRECT/TERMINAL (fix PM #2):
    subscriber unico en /safety_events debe ser recovery_g1 por nombre.
    Solo len==1 no es suficiente — se verifica node_name.

AISLAMIENTO GOVERNED (fix PM #3 — ajuste PM original #2):
    /safety_events  -> safety_orchestrator_g1 UNICAMENTE.
    /safety_actions -> recovery_g1 UNICAMENTE.
    recovery_g1 NO debe suscribirse a /safety_events.
    Launch requerido (mismo patron P0-B):
      ros2 run recovery_g1 recovery_g1 --ros-args \\
           --remap /safety_events:=/safety_events_null

CSV POR RUN (fix PM #4):
    Archivo por case+timestamp — sin mezcla de runs anteriores.
    p3_timing_raw_{case}_{timestamp}.csv

ENVIRONMENT PRE-RUN (fix PM #5):
    _write_environment llamado al inicio, antes del loop.
    Captura estado limpio antes de cualquier inyeccion.

P95 (ajuste PM #4):
    Etiquetado como p95_ms_exploratory en todos los outputs.
    N=10 no es suficiente para p95 estadistico fuerte.
"""

import argparse
import csv
import statistics
import subprocess
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path

import rclpy
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, HistoryPolicy, QoSProfile, ReliabilityPolicy

from g1_msgs.msg import RecoveryEvent, SafetyAction, SafetyEvent

# ── Constants ─────────────────────────────────────────────────────────────────

WARMUP_S         = 5.0
TIMEOUT_ACTION_S = 8.0
TIMEOUT_RECOV_S  = 10.0
INTER_RUN_S      = 6.0

RELIABLE_QOS = QoSProfile(
    reliability=ReliabilityPolicy.RELIABLE,
    durability=DurabilityPolicy.VOLATILE,
    history=HistoryPolicy.KEEP_LAST,
    depth=10,
)

EVIDENCE_BASE = Path('/ws/evidence/4J/P3_TIMING')

# ── Case configuration ────────────────────────────────────────────────────────
# Extraido de harnesses P2 validados. No modificar sin nueva aprobacion PM.

CASE_CFG = {
    'stale': dict(
        route='R2', expected_action='wait_for_primary_restore', expected_rtype='REC-AUTO',
        source='watchdog_g1', source_authority='PRIMARY',
        authority_effectiveness='EFFECTIVE',
        risk_level='', restriction_level='', transition_priority='',
        execution_confidence='', rule_id='4F-P2-STALE',
    ),
    'freeze': dict(
        route='R3', expected_action='request_operator_intervention', expected_rtype='REC-MANUAL',
        source='watchdog_g1', source_authority='PRIMARY',
        authority_effectiveness='EFFECTIVE',
        risk_level='FAULT_CRITICAL', restriction_level='R3',
        transition_priority='CRITICAL_INTERRUPT', execution_confidence='VERIFIED',
        rule_id='4F-P2-FREEZE',
    ),
    'naninf': dict(
        route='R3', expected_action='request_operator_intervention', expected_rtype='REC-MANUAL',
        source='watchdog_g1', source_authority='PRIMARY',
        authority_effectiveness='EFFECTIVE',
        risk_level='FAULT_CRITICAL', restriction_level='R3',
        transition_priority='CRITICAL_INTERRUPT', execution_confidence='VERIFIED',
        rule_id='4F-P2-NANINF',
    ),
    'timestamp': dict(
        route='R3', expected_action='request_operator_intervention', expected_rtype='REC-MANUAL',
        source='watchdog_g1', source_authority='PRIMARY',
        authority_effectiveness='EFFECTIVE',
        risk_level='FAULT_CRITICAL', restriction_level='R3',
        transition_priority='CRITICAL_INTERRUPT', execution_confidence='VERIFIED',
        rule_id='4F-P2-TIMESTAMP',
    ),
    'fallen_direct': dict(
        route='R2', expected_action='wait_for_primary_restore', expected_rtype='REC-AUTO',
        source='cross_consistency_observer', source_authority='SECONDARY',
        authority_effectiveness='EFFECTIVE',
        risk_level='CAUTION', restriction_level='R2',
        transition_priority='NORMAL', execution_confidence='BEST_EFFORT',
        rule_id='',
    ),
    'tx011_governed': dict(
        route='R1', expected_action='stabilization_mode', expected_rtype='REC-AUTO',
        source='cross_consistency_observer', source_authority='SECONDARY',
        authority_effectiveness='EFFECTIVE',
        risk_level='SAFE', restriction_level='NONE',
        transition_priority='', execution_confidence='BEST_EFFORT',
        rule_id='',
    ),
}

CSV_HEADER = [
    'CASE', 'RUN', 'EVENT_ID', 'ROUTE', 'ACTION', 'RECOVERY_TYPE',
    'LATENCY_MS',
    'T_EVENT_TO_ACTION_MS', 'T_ACTION_TO_RECOVERY_MS', 'T_EVENT_TO_RECOVERY_MS',
    'RESULT',
]

# ── Timing node ───────────────────────────────────────────────────────────────

class TimingNode(Node):
    """
    Nodo de medicion. Una instancia por run.
    rclpy debe estar inicializado antes de crear este nodo.
    Llamar destroy_node() al terminar el run.
    No llama rclpy.init() ni rclpy.shutdown().
    """

    def __init__(self, case, event_id):
        # UUID suffix para evitar conflictos si el grafo DDS no limpia a tiempo
        super().__init__('harness_p3_{}_{}'.format(case, uuid.uuid4().hex[:6]))
        self._case    = case
        self._event_id = event_id
        # t0: harness publish timestamp immediately before publish (ajuste PM #1)
        self._t0      = None
        # t1: primera linea de callback SafetyAction (governed)
        self._t1      = None
        self._act_msg = None   # SafetyAction recibido (governed)
        self._rec_msg = None   # RecoveryEvent recibido
        self.timing   = {}     # metricas calculadas en callback

        self._pub = self.create_publisher(SafetyEvent, '/safety_events', RELIABLE_QOS)
        self.create_subscription(RecoveryEvent, '/recovery_events',
                                 self._on_recovery, RELIABLE_QOS)
        if case == 'tx011_governed':
            self.create_subscription(SafetyAction, '/safety_actions',
                                     self._on_action, RELIABLE_QOS)

    def _on_action(self, msg):
        # t1: primera linea — antes de cualquier condicion
        t1 = time.monotonic()
        if self._t0 is None or self._act_msg is not None:
            return
        if msg.parent_event_id != self._event_id:
            return
        self._t1      = t1
        self._act_msg = msg

    def _on_recovery(self, msg):
        # t_recv: primera linea — antes de cualquier condicion
        t_recv = time.monotonic()
        if self._t0 is None or self._rec_msg is not None:
            return
        if 'parent_event_id={}'.format(self._event_id) not in (msg.notes or ''):
            return
        self._rec_msg = msg

        if self._case == 'tx011_governed':
            t2 = t_recv
            t1 = self._t1 if self._t1 is not None else t2
            self.timing = {
                'latency_ms':              None,
                't_event_to_action_ms':    round((t1 - self._t0) * 1000, 3) if self._t1 else None,
                't_action_to_recovery_ms': round((t2 - t1) * 1000, 3)       if self._t1 else None,
                't_event_to_recovery_ms':  round((t2 - self._t0) * 1000, 3),
            }
        else:
            self.timing = {
                'latency_ms':              round((t_recv - self._t0) * 1000, 3),
                't_event_to_action_ms':    None,
                't_action_to_recovery_ms': None,
                't_event_to_recovery_ms':  None,
            }

# ── Helpers ───────────────────────────────────────────────────────────────────

def _build_event(node, case, event_id):
    cfg = CASE_CFG[case]
    msg = SafetyEvent()
    msg.event_id                = event_id
    msg.event_type              = 'CONDITION_DETECTED'
    msg.source                  = cfg['source']
    msg.source_authority        = cfg['source_authority']
    msg.authority_effectiveness = cfg['authority_effectiveness']
    msg.target                  = '/g1/imu'
    if cfg['risk_level']:           msg.risk_level           = cfg['risk_level']
    if cfg['restriction_level']:    msg.restriction_level    = cfg['restriction_level']
    if cfg['transition_priority']:  msg.transition_priority  = cfg['transition_priority']
    if cfg['execution_confidence']: msg.execution_confidence = cfg['execution_confidence']
    rule_part = ' rule_id={}'.format(cfg['rule_id']) if cfg['rule_id'] else ''
    msg.notes     = '4JP3-{}{} harness event_id={}'.format(case.upper(), rule_part, event_id)
    msg.timestamp = node.get_clock().now().to_msg()
    return msg


def _check_topology(node, case):
    """
    Verifica topologia por nombre de nodo — no solo por conteo.
    Fix PM #2: direct/terminal exige subscriber=recovery_g1, no solo len==1.
    Fix PM #3 (original #2): governed exige orchestrator en /safety_events,
    recovery_g1 en /safety_actions, recovery_g1 FUERA de /safety_events.
    Retorna True si OK.
    """
    se_infos = node.get_subscriptions_info_by_topic('/safety_events')
    se_names = [i.node_name for i in se_infos]

    if case == 'tx011_governed':
        sa_infos = node.get_subscriptions_info_by_topic('/safety_actions')
        sa_names = [i.node_name for i in sa_infos]
        print('  [TOPOLOGY] /safety_events  subscribers: {}'.format(se_names))
        print('  [TOPOLOGY] /safety_actions subscribers: {}'.format(sa_names))

        ok = True
        if len(se_infos) != 1 or not any('safety_orchestrator_g1' in n for n in se_names):
            print('  TOPO-FAIL /safety_events: esperado [safety_orchestrator_g1],'
                  ' encontrado {}'.format(se_names))
            ok = False
        if any('recovery_g1' in n for n in se_names):
            print('  TOPO-FAIL recovery_g1 NO debe suscribirse a /safety_events'
                  ' — verificar remap --remap /safety_events:=/safety_events_null')
            ok = False
        if not any('recovery_g1' in n for n in sa_names):
            print('  TOPO-FAIL /safety_actions: esperado recovery_g1,'
                  ' encontrado {}'.format(sa_names))
            ok = False
        return ok
    else:
        # fix PM #2: verificar nombre recovery_g1, no solo conteo
        print('  [TOPOLOGY] /safety_events subscribers: {}'.format(se_names))
        if len(se_infos) != 1:
            print('  TOPO-FAIL /safety_events: esperado 1 subscriber (recovery_g1),'
                  ' encontrado {}: {}'.format(len(se_infos), se_names))
            return False
        if not any('recovery_g1' in n for n in se_names):
            print('  TOPO-FAIL /safety_events: subscriber unico no es recovery_g1:'
                  ' {}'.format(se_names))
            return False
        return True


def _fail_row(case, run_idx, event_id, reason):
    cfg = CASE_CFG[case]
    return {
        'CASE': case.upper(), 'RUN': '{:03d}'.format(run_idx), 'EVENT_ID': event_id,
        'ROUTE': cfg['route'], 'ACTION': '', 'RECOVERY_TYPE': '',
        'LATENCY_MS': '', 'T_EVENT_TO_ACTION_MS': '',
        'T_ACTION_TO_RECOVERY_MS': '', 'T_EVENT_TO_RECOVERY_MS': '',
        'RESULT': 'FAIL-{}'.format(reason),
    }


def _run_single(case, run_idx):
    """
    Ejecuta una sola muestra de timing.
    PRECONDICION: rclpy ya inicializado por main().
    Solo crea/destruye el nodo. No toca rclpy lifecycle. (fix PM #1)
    """
    cfg      = CASE_CFG[case]
    event_id = '4JP3-{}-{:03d}-{}'.format(case.upper(), run_idx, str(uuid.uuid4())[:4])

    # Crear nodo — rclpy ya esta inicializado
    node = TimingNode(case, event_id)

    # Warmup — anti-pattern #74: confirmar subscriber antes de publicar
    t_warm = time.monotonic()
    ready  = False
    while time.monotonic() - t_warm < WARMUP_S:
        rclpy.spin_once(node, timeout_sec=0.05)
        if node.count_subscribers('/safety_events') > 0:
            ready = True
            break

    if not ready:
        print('  FAIL — no subscriber en /safety_events tras {}s warmup'.format(WARMUP_S))
        node.destroy_node()
        return _fail_row(case, run_idx, event_id, 'TIMEOUT_WARMUP')

    # Fase 2 warmup: esperar resolucion DDS de node names. Aprobado PM.
    NAME_SETTLE_S = 3.0
    t_settle = time.monotonic()
    while time.monotonic() - t_settle < NAME_SETTLE_S:
        rclpy.spin_once(node, timeout_sec=0.1)
        infos = node.get_subscriptions_info_by_topic("/safety_events")
        names = [i.node_name for i in infos]
        if infos and all("UNKNOWN" not in n for n in names):
            break
    infos = node.get_subscriptions_info_by_topic("/safety_events")
    names = [i.node_name for i in infos]
    if any("UNKNOWN" in n for n in names):
        print("  FAIL -- DDS node names sin resolver tras {}s: {}".format(NAME_SETTLE_S, names))
        node.destroy_node()
        return _fail_row(case, run_idx, event_id, "TOPO_UNRESOLVED")

    # Topology check por nombre (fix PM #2 y #3)
    if not _check_topology(node, case):
        node.destroy_node()
        return _fail_row(case, run_idx, event_id, 'TOPO_FAIL')

    # Publicar — t0 capturado inmediatamente antes del publish call (ajuste PM #1)
    msg      = _build_event(node, case, event_id)
    node._t0 = time.monotonic()   # harness publish timestamp immediately before publish
    node._pub.publish(msg)
    print('  published event_id={}'.format(event_id))

    # Esperar SafetyAction (solo governed)
    if case == 'tx011_governed':
        t_wait = time.monotonic()
        while node._act_msg is None and (time.monotonic() - t_wait) < TIMEOUT_ACTION_S:
            rclpy.spin_once(node, timeout_sec=0.05)
        if node._act_msg is None:
            print('  FAIL — timeout: SafetyAction parent_event_id={} no recibido'.format(event_id))
            node.destroy_node()
            return _fail_row(case, run_idx, event_id, 'TIMEOUT_ACTION')

    # Esperar RecoveryEvent
    t_wait = time.monotonic()
    while node._rec_msg is None and (time.monotonic() - t_wait) < TIMEOUT_RECOV_S:
        rclpy.spin_once(node, timeout_sec=0.05)

    if node._rec_msg is None:
        print('  FAIL — timeout: RecoveryEvent parent_event_id={} no recibido'.format(event_id))
        node.destroy_node()
        return _fail_row(case, run_idx, event_id, 'TIMEOUT_RECOVERY')

    # Nodo destruido — datos ya capturados en node.timing
    node.destroy_node()

    # Validacion — falla aqui puede indicar Clase B (runtime bug) — detener P3
    rec      = node._rec_msg
    failures = []
    if rec.action_name != cfg['expected_action']:
        failures.append('action_name={!r} esperado {!r}'.format(
            rec.action_name, cfg['expected_action']))
    if rec.recovery_type != cfg['expected_rtype']:
        failures.append('recovery_type={!r} esperado {!r}'.format(
            rec.recovery_type, cfg['expected_rtype']))
    if 'parent_event_id={}'.format(event_id) not in (rec.notes or ''):
        failures.append('notes sin parent_event_id={}'.format(event_id))
    if case == 'tx011_governed' and node._act_msg:
        if node._act_msg.transition_id != 'TX-011':
            failures.append('SafetyAction.transition_id={!r} esperado TX-011'.format(
                node._act_msg.transition_id))

    if failures:
        print('  FAIL — {}'.format('; '.join(failures)))
        print('  ATENCION: VALIDATION_FAIL puede ser Clase B. Detener P3 y auditar runtime.')
        row = _fail_row(case, run_idx, event_id, 'VALIDATION_FAIL')
        t = node.timing
        if t:
            def _s(v): return '' if v is None else str(v)
            row.update({
                'LATENCY_MS':              _s(t.get('latency_ms')),
                'T_EVENT_TO_ACTION_MS':    _s(t.get('t_event_to_action_ms')),
                'T_ACTION_TO_RECOVERY_MS': _s(t.get('t_action_to_recovery_ms')),
                'T_EVENT_TO_RECOVERY_MS':  _s(t.get('t_event_to_recovery_ms')),
            })
        return row

    t           = node.timing
    lat_display = t.get('latency_ms') or t.get('t_event_to_recovery_ms')
    print('  PASS — latency={}ms  action={}  rtype={}'.format(
        lat_display, rec.action_name, rec.recovery_type))

    def _fmt(v): return '' if v is None else str(v)

    return {
        'CASE':                    case.upper(),
        'RUN':                     '{:03d}'.format(run_idx),
        'EVENT_ID':                event_id,
        'ROUTE':                   cfg['route'],
        'ACTION':                  rec.action_name,
        'RECOVERY_TYPE':           rec.recovery_type,
        'LATENCY_MS':              _fmt(t.get('latency_ms')),
        'T_EVENT_TO_ACTION_MS':    _fmt(t.get('t_event_to_action_ms')),
        'T_ACTION_TO_RECOVERY_MS': _fmt(t.get('t_action_to_recovery_ms')),
        'T_EVENT_TO_RECOVERY_MS':  _fmt(t.get('t_event_to_recovery_ms')),
        'RESULT': 'PASS',
    }


def _compute_stats(samples, case):
    """p95_ms_exploratory — N=10 no es estadistico fuerte (ajuste PM #4)."""
    key       = 'T_EVENT_TO_RECOVERY_MS' if case == 'tx011_governed' else 'LATENCY_MS'
    pass_lats = [float(s[key]) for s in samples if s['RESULT'] == 'PASS' and s[key] != '']
    timeouts  = sum(1 for s in samples if 'TIMEOUT' in s['RESULT'])
    passes    = len(pass_lats)
    fails     = sum(1 for s in samples if s['RESULT'] != 'PASS')

    if not pass_lats:
        return dict(n=len(samples), pass_=passes, fail=fails,
                    min_ms=None, mean_ms=None, max_ms=None,
                    p95_ms_exploratory=None, timeouts=timeouts)

    sorted_l = sorted(pass_lats)
    p95_idx  = max(0, int(len(sorted_l) * 0.95) - 1)

    return dict(
        n=len(samples), pass_=passes, fail=fails,
        min_ms=round(min(pass_lats), 3),
        mean_ms=round(statistics.mean(pass_lats), 3),
        max_ms=round(max(pass_lats), 3),
        p95_ms_exploratory=round(sorted_l[p95_idx], 3),
        timeouts=timeouts,
    )


def _write_csv(rows, raw_csv_path):
    """CSV por case+timestamp — sin mezcla de runs anteriores (fix PM #4)."""
    raw_csv_path.parent.mkdir(parents=True, exist_ok=True)
    needs_header = not raw_csv_path.exists()
    with open(raw_csv_path, 'a', newline='') as f:
        w = csv.DictWriter(f, fieldnames=CSV_HEADER)
        if needs_header:
            w.writeheader()
        w.writerows(rows)


def _write_summary(case, stats, start_time, raw_csv_path):
    """p95_ms_exploratory en el documento de summary (ajuste PM #4)."""
    summary_path = EVIDENCE_BASE / 'summaries' / 'p3_timing_summary.md'
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    cfg  = CASE_CFG[case]
    text = (
        '\n## {} — {} — {}\n\n'.format(case.upper(), cfg['route'], start_time) +
        '| metric | value |\n|---|---|\n' +
        '| N | {} |\n'.format(stats['n']) +
        '| pass | {} |\n'.format(stats['pass_']) +
        '| fail | {} |\n'.format(stats['fail']) +
        '| min_ms | {} |\n'.format(stats['min_ms']) +
        '| mean_ms | {} |\n'.format(stats['mean_ms']) +
        '| max_ms | {} |\n'.format(stats['max_ms']) +
        '| p95_ms_exploratory | {} |\n'.format(stats['p95_ms_exploratory']) +
        '| timeouts | {} |\n'.format(stats['timeouts']) +
        '| evidence_file | {} |\n'.format(raw_csv_path)
    )
    with open(summary_path, 'a') as f:
        f.write(text)


def _write_environment(case, n, start_time, raw_csv_path, label='PRE-RUN'):
    """
    Escribe environment file con node names y topic info -v (fix PM #5 + punto vigilancia PM).
    Llamar al INICIO (PRE-RUN) para capturar estado limpio antes de inyecciones.
    """
    env_path = EVIDENCE_BASE / 'logs' / 'p3_env_{}_{}.txt'.format(
        case, start_time.replace(':', '').replace('.', ''))
    env_path.parent.mkdir(parents=True, exist_ok=True)

    def _cmd(args):
        try:
            return subprocess.check_output(args, stderr=subprocess.DEVNULL).decode().strip()
        except Exception:
            return 'UNAVAILABLE'

    git_commit = _cmd(['git', '-C', '/ws', 'rev-parse', 'HEAD'])
    node_list  = _cmd(['ros2', 'node', 'list'])
    topo_se    = _cmd(['ros2', 'topic', 'info', '-v', '/safety_events'])
    topo_sa    = _cmd(['ros2', 'topic', 'info', '-v', '/safety_actions'])
    topo_re    = _cmd(['ros2', 'topic', 'info', '-v', '/recovery_events'])

    block = '\n'.join([
        '[{}]'.format(label),
        'case:         {}'.format(case),
        'n:            {}'.format(n),
        'git_commit:   {}'.format(git_commit),
        'container:    boring_noether',
        'ros_distro:   humble',
        'date_time:    {}'.format(start_time),
        'raw_csv:      {}'.format(raw_csv_path),
        'test_command: python3 harness_4J_P3_timing_matrix.py --case {} --n {}'.format(case, n),
        '',
        '--- ros2 node list ---',
        node_list,
        '',
        '--- /safety_events topic info -v ---',
        topo_se,
        '',
        '--- /safety_actions topic info -v ---',
        topo_sa,
        '',
        '--- /recovery_events topic info -v ---',
        topo_re,
        '',
        '=' * 60,
        '',
    ])
    with open(env_path, 'a') as f:
        f.write(block)
    return env_path


def _print_table(case, stats):
    """p95_ms(exp) como abreviatura de p95_ms_exploratory en tabla impresa (ajuste PM #4)."""
    cfg = CASE_CFG[case]
    hdr = ('{:<20} {:<6} {:>4} {:>5} {:>5}'
           ' {:>8} {:>9} {:>8} {:>12} {:>9}'.format(
        'case', 'route', 'N', 'pass', 'fail',
        'min_ms', 'mean_ms', 'max_ms', 'p95_ms(exp)', 'timeouts'))
    row = ('{:<20} {:<6} {:>4} {:>5} {:>5}'
           ' {:>8} {:>9} {:>8} {:>12} {:>9}'.format(
        case.upper(), cfg['route'],
        stats['n'], stats['pass_'], stats['fail'],
        str(stats['min_ms']), str(stats['mean_ms']), str(stats['max_ms']),
        str(stats['p95_ms_exploratory']), stats['timeouts']))
    print()
    print(hdr)
    print('-' * len(hdr))
    print(row)
    print()
    print('NOTE: p95_ms_exploratory — N=10 no es estadisticamente fuerte.')
    print()

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description='4J-P3 Timing Traceability Matrix')
    parser.add_argument('--case', required=True, choices=list(CASE_CFG.keys()))
    parser.add_argument('--n', type=int, default=10)
    args = parser.parse_args()
    case = args.case
    n    = args.n

    start_time    = datetime.now().isoformat()
    run_timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    # CSV por case+timestamp — sin mezcla de runs anteriores (fix PM #4)
    raw_csv_path  = EVIDENCE_BASE / 'raw' / 'p3_timing_raw_{}_{}.csv'.format(case, run_timestamp)

    print()
    print('=' * 62)
    print(' 4J-P3 TIMING MATRIX   case={}   n={}'.format(case.upper(), n))
    print('=' * 62)
    print()
    # docker restart como precondicion del operador (ajuste PM #3)
    print('[P3-PREFLIGHT] Operador debe ejecutar docker restart antes de este case group.')
    print('[P3-PREFLIGHT] El tiempo de restart NO es parte de la latencia medida.')
    print('[P3-PREFLIGHT] El restart NO se ejecuta dentro de este harness.')
    if case == 'tx011_governed':
        # fix PM #3: documenta remap explicito — mismo patron P0-B
        print('[P3-PREFLIGHT] GOVERNED — launch requerido (patron P0-B):')
        print('[P3-PREFLIGHT]   Terminal A: ros2 run safety_orchestrator_g1 ...')
        print('[P3-PREFLIGHT]   Terminal B: ros2 run recovery_g1 recovery_g1 --ros-args \\')
        print('[P3-PREFLIGHT]              --remap /safety_events:=/safety_events_null')
        print('[P3-PREFLIGHT] Verificar antes de correr:')
        print('[P3-PREFLIGHT]   ros2 topic info -v /safety_events  '
              '→ debe mostrar SOLO safety_orchestrator_g1')
        print('[P3-PREFLIGHT]   ros2 topic info -v /safety_actions '
              '→ debe mostrar recovery_g1')
        print('[P3-PREFLIGHT] Si topology check falla, corregir launch antes de reintentar.')
    else:
        print('[P3-PREFLIGHT] Topologia requerida:')
        print('[P3-PREFLIGHT]   /safety_events → recovery_g1 UNICAMENTE (1 subscriber)')
        print('[P3-PREFLIGHT]   Verificar: ros2 topic info -v /safety_events')
    print()

    # fix PM #5: environment PRE-RUN al inicio — captura estado limpio antes de inyecciones
    print('[P3-ENV] Escribiendo environment PRE-RUN...')
    env_path = _write_environment(case, n, start_time, raw_csv_path, label='PRE-RUN')
    print('[P3-ENV] {}'.format(env_path))
    print()

    samples = []

    # fix PM #1: rclpy.init() una vez por case group
    rclpy.init()
    try:
        for run_idx in range(1, n + 1):
            print('--- Run {}/{} ---'.format(run_idx, n))
            row = _run_single(case, run_idx)
            samples.append(row)
            _write_csv([row], raw_csv_path)
            if run_idx < n:
                print('[INTER-RUN] {}s...'.format(INTER_RUN_S))
                time.sleep(INTER_RUN_S)
    finally:
        # fix PM #1: rclpy.shutdown() una vez al final del batch
        rclpy.shutdown()

    stats = _compute_stats(samples, case)
    _write_summary(case, stats, start_time, raw_csv_path)
    _print_table(case, stats)

    print('Evidence:')
    print('  {}'.format(raw_csv_path))
    print('  {}'.format(EVIDENCE_BASE / 'summaries' / 'p3_timing_summary.md'))
    print('  {}'.format(env_path))
    print()

    if stats['fail'] > 0:
        print('WARNING: {} falla(s) detectadas.'.format(stats['fail']))
        print('  VALIDATION_FAIL → posible Clase B (runtime bug) — detener P3 y auditar.')
        print('  TIMEOUT         → posible Clase T (timing anomaly) — repetir estado limpio.')
        sys.exit(1)

    sys.exit(0)


if __name__ == '__main__':
    main()
