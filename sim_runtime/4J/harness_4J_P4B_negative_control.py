#!/usr/bin/env python3
"""
harness_4J_P4B_negative_control.py
4J-P4-B — Negative Control: healthy/baseline synthetic data.

PASS: 0 SafetyEvents with risk_level in {STABILITY_RISK, FAULT_CRITICAL},
      0 terminal RecoveryEvents, 0 request_operator_intervention.
INFO/WARN-severity events (CAUTION risk_level) are logged and classified.

APPROXIMATION DECLARED:
  SafetyEvent has no native severity field. CRITICAL is approximated as
  risk_level in {STABILITY_RISK, FAULT_CRITICAL}. CAUTION = WARN-severity.
  This is consistent with watchdog_g1._emit() mapping.

LIMITATION DECLARED:
  Jittered IMU (JITTER_MAG) and jittered base_pose prevent FREEZE false-positive
  test with truly frozen sensors. That case is deferred to P4-E.
  P4-B tests "healthy active baseline" only.

QoS NOTE:
  Harness publishers use BEST_EFFORT — matches runtime subscriber QoS
  (watchdog_g1 QOS_SUB=BEST_EFFORT, observer QOS_SENSOR=BEST_EFFORT).
  Harness /safety_events and /recovery_events subscribers use RELIABLE
  — matches runtime publisher QoS (QOS_SAFETY_EVENTS=RELIABLE).

HEAD: 9777103
"""
import csv
import os
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path

import rclpy
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, HistoryPolicy, QoSProfile, ReliabilityPolicy

from geometry_msgs.msg import PoseStamped
from sensor_msgs.msg import Imu, JointState

from g1_msgs.msg import FootContact, RecoveryEvent, SafetyEvent

# ── Timing ────────────────────────────────────────────────────────────────────
STARTUP_GRACE_S      = 15.0
POST_GRACE_SETTLE_S  =  5.0
OBSERVATION_WINDOW_S = 60.0
NAME_SETTLE_S        =  3.0   # DDS node-name resolution (anti-pattern #74/#75)

# ── Publish rates ─────────────────────────────────────────────────────────────
PUBLISH_HZ  = 50.0
CONTACT_DIV =  5              # contacts every 5th tick → 10 Hz

# ── Anti-FREEZE jitter ────────────────────────────────────────────────────────
JITTER_MAG = 0.0001           # per-tick increment — prevents 5 identical samples

# ── QoS ───────────────────────────────────────────────────────────────────────
# BEST_EFFORT: matches runtime subscriber QoS for sensor topics
QOS_PUB_SENSOR = QoSProfile(
    reliability=ReliabilityPolicy.BEST_EFFORT,
    durability=DurabilityPolicy.VOLATILE,
    history=HistoryPolicy.KEEP_LAST, depth=10,
)
# RELIABLE: matches runtime publisher QoS for /safety_events and /recovery_events
QOS_SUB_EVENTS = QoSProfile(
    reliability=ReliabilityPolicy.RELIABLE,
    durability=DurabilityPolicy.VOLATILE,
    history=HistoryPolicy.KEEP_LAST, depth=50,
)

CRITICAL_RISK_LEVELS = {'STABILITY_RISK', 'FAULT_CRITICAL'}

# Minimum expected subscribers per published topic (fail-closed if not met)
TOPO_MIN_SUBS = {
    '/g1/imu':           1,   # watchdog_g1 only (/g1/imu)
    '/imu':              1,   # cross_consistency_observer only (/imu)
    '/safety_events':    1,   # watchdog_g1 or observer must publish
    '/recovery_events':  1,   # recovery_g1 must publish
}


# ── Node ──────────────────────────────────────────────────────────────────────
class P4BHarness(Node):
    def __init__(self):
        super().__init__('p4b_negative_control')
        self.safety_events   = []
        self.recovery_events = []
        self._tick = 0

        # Sensor publishers — BEST_EFFORT matches runtime subscriber QoS
        self._pub_imu    = self.create_publisher(Imu,         '/g1/imu',           QOS_PUB_SENSOR)
        self._pub_imu_obs= self.create_publisher(Imu,         '/imu',              QOS_PUB_SENSOR)
        self._pub_cl     = self.create_publisher(FootContact, '/g1/contact/left',  QOS_PUB_SENSOR)
        self._pub_cr     = self.create_publisher(FootContact, '/g1/contact/right', QOS_PUB_SENSOR)
        self._pub_joints = self.create_publisher(JointState,  '/joint_states',     QOS_PUB_SENSOR)
        self._pub_pose   = self.create_publisher(PoseStamped, '/g1/base_pose',     QOS_PUB_SENSOR)

        # Event subscribers — RELIABLE matches runtime publisher QoS
        self.create_subscription(SafetyEvent,   '/safety_events',   self._on_safety,   QOS_SUB_EVENTS)
        self.create_subscription(RecoveryEvent, '/recovery_events', self._on_recovery, QOS_SUB_EVENTS)

        self.create_timer(1.0 / PUBLISH_HZ, self._tick_cb)
        self.get_logger().info('[P4B] harness started.')

    # ── Topology check ────────────────────────────────────────────────────────
    def check_topology(self) -> bool:
        """Verify runtime nodes are present before observation.
        Returns True if topology is resolved, False → fail closed."""
        self.get_logger().info('[P4B] topology check — NAME_SETTLE_S={}'.format(NAME_SETTLE_S))
        t0 = time.monotonic()
        while time.monotonic() - t0 < NAME_SETTLE_S:
            rclpy.spin_once(self, timeout_sec=0.1)

        ok = True
        # Check subscribers on /g1/imu (runtime nodes must be listening)
        imu_subs = self.get_subscriptions_info_by_topic('/g1/imu')
        imu_names = [i.node_name for i in imu_subs]
        if any('UNKNOWN' in n for n in imu_names) or len(imu_subs) < TOPO_MIN_SUBS['/g1/imu']:
            self.get_logger().error(
                f'[P4B] TOPO_FAIL /g1/imu: subs={imu_names} required≥{TOPO_MIN_SUBS["/g1/imu"]}')
            ok = False
        else:
            self.get_logger().info(f'[P4B] /g1/imu subscribers: {imu_names} ✓')

        # Check subscribers on /imu (cross_consistency_observer)
        imu_obs_subs  = self.get_subscriptions_info_by_topic('/imu')
        imu_obs_names = [i.node_name for i in imu_obs_subs]
        if any('UNKNOWN' in n for n in imu_obs_names) or len(imu_obs_subs) < TOPO_MIN_SUBS['/imu']:
            self.get_logger().error(
                f'[P4B] TOPO_FAIL /imu: subs={imu_obs_names} required≥{TOPO_MIN_SUBS["/imu"]}')
            ok = False
        else:
            self.get_logger().info(f'[P4B] /imu subscribers: {imu_obs_names} ✓')

        # Check publishers on /safety_events
        se_pubs = self.get_publishers_info_by_topic('/safety_events')
        se_names = [i.node_name for i in se_pubs]
        if len(se_pubs) < TOPO_MIN_SUBS['/safety_events']:
            self.get_logger().error(
                f'[P4B] TOPO_FAIL /safety_events: publishers={se_names} required≥1')
            ok = False
        else:
            self.get_logger().info(f'[P4B] /safety_events publishers: {se_names} ✓')

        # Check publishers on /recovery_events
        re_pubs = self.get_publishers_info_by_topic('/recovery_events')
        re_names = [i.node_name for i in re_pubs]
        if len(re_pubs) < TOPO_MIN_SUBS['/recovery_events']:
            self.get_logger().error(
                f'[P4B] TOPO_FAIL /recovery_events: publishers={re_names} required≥1')
            ok = False
        else:
            self.get_logger().info(f'[P4B] /recovery_events publishers: {re_names} ✓')

        return ok

    # ── Event callbacks ───────────────────────────────────────────────────────
    def _on_safety(self, msg: SafetyEvent):
        # APPROXIMATION: no native severity field; CRITICAL ≈ risk_level in CRITICAL_RISK_LEVELS
        is_crit = msg.risk_level in CRITICAL_RISK_LEVELS
        entry = {
            'ts':           time.time(),
            'event_id':     msg.event_id,
            'source':       msg.source,
            'risk_level':   msg.risk_level,
            'is_crit_risk': is_crit,
            'notes':        msg.notes[:120],
        }
        self.safety_events.append(entry)
        if is_crit:
            self.get_logger().error(f'[P4B] SafetyEvent risk={msg.risk_level} src={msg.source} crit={is_crit}')
        else:
            self.get_logger().warn(f'[P4B] SafetyEvent risk={msg.risk_level} src={msg.source} crit={is_crit}')

    def _on_recovery(self, msg: RecoveryEvent):
        # FIX: use action_name (correct RecoveryEvent field); check both action_name and notes
        is_terminal = (
            msg.action_name == 'request_operator_intervention'
            or 'request_operator_intervention' in msg.notes
            or 'terminal' in msg.notes.lower()
        )
        entry = {
            'ts':          time.time(),
            'action_name': msg.action_name,
            'is_terminal': is_terminal,
            'notes':       msg.notes[:120],
        }
        self.recovery_events.append(entry)
        if is_terminal:
            self.get_logger().error(f'[P4B] RecoveryEvent action_name={msg.action_name} terminal={is_terminal}')
        else:
            self.get_logger().info(f'[P4B] RecoveryEvent action_name={msg.action_name} terminal={is_terminal}')

    # ── Publish tick ──────────────────────────────────────────────────────────
    def _tick_cb(self):
        now  = self.get_clock().now().to_msg()
        tick = self._tick

        # IMU — abs_w >= 0.995 >> FALLEN_W_WARN=0.85; modular jitter prevents FREEZE_N=5
        # w cycles: 0.995/0.996/0.997/0.998 — always >> 0.85
        imu = Imu()
        imu.header.stamp    = now
        imu.header.frame_id = 'imu'
        imu.orientation.w   = 0.995 + 0.001 * (tick % 4)
        imu.orientation.x   = 0.001 * (tick % 3)
        imu.orientation.y   = 0.001
        imu.orientation.z   = 0.001
        self._pub_imu.publish(imu)
        self._pub_imu_obs.publish(imu)  # same msg → cross_consistency_observer

        # Contacts at 10 Hz
        if tick % CONTACT_DIV == 0:
            for pub in (self._pub_cl, self._pub_cr):
                fc = FootContact()
                fc.header.stamp = now
                fc.in_contact   = True
                fc.force        = 200.0
                pub.publish(fc)

        # JointState — modular jitter prevents FREEZE; no NaN/Inf; rates unchanged
        js = JointState()
        js.header.stamp = now
        js.name         = ['j0', 'j1', 'j2', 'j3', 'j4', 'j5']
        js.position     = [0.1 + 0.001 * ((tick + i) % 7) for i in range(6)]
        js.velocity     = [0.0] * 6
        js.effort       = [0.0] * 6
        self._pub_joints.publish(js)

        # BasePose — modular jitter on z prevents FREEZE; z cycles 0.720-0.724
        ps = PoseStamped()
        ps.header.stamp       = now
        ps.header.frame_id    = 'world'
        ps.pose.position.x    = 0.0
        ps.pose.position.y    = 0.0
        ps.pose.position.z    = 0.720 + 0.001 * (tick % 5)
        ps.pose.orientation.w = 1.0
        self._pub_pose.publish(ps)

        self._tick += 1

    def clear_observation(self):
        self.safety_events.clear()
        self.recovery_events.clear()


# ── Evidence writers ──────────────────────────────────────────────────────────
def write_environment(d: Path, run_id: str):
    import subprocess
    try:
        commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
    except Exception:
        commit = 'UNKNOWN'
    lines = [
        f'run_id={run_id}',
        f'timestamp={datetime.utcnow().isoformat()}Z',
        f'commit={commit}',
        f'harness=harness_4J_P4B_negative_control.py',
        f'startup_grace_s={STARTUP_GRACE_S}',
        f'post_grace_settle_s={POST_GRACE_SETTLE_S}',
        f'observation_window_s={OBSERVATION_WINDOW_S}',
        f'name_settle_s={NAME_SETTLE_S}',
        f'publish_hz={PUBLISH_HZ}  contact_div={CONTACT_DIV}',
        f'modular_jitter_step=0.001 (IMU w: tick%4, joints: (tick+i)%7, pose_z: tick%5)',
        'qos_pub=BEST_EFFORT (matches runtime sensor subscriber QoS)',
        'qos_sub=RELIABLE (matches runtime safety_events/recovery_events publisher QoS)',
        'limitation=Jittered_sensors — does_NOT_test_frozen_sensor_FREEZE_false_positive (P4-E)',
        'critical_approx=risk_level_in_{STABILITY_RISK,FAULT_CRITICAL} (no native severity field)',
    ]
    (d / 'p4b_environment.txt').write_text('\n'.join(lines) + '\n')


def write_csv(d: Path, rows: list, filename: str):
    p = d / filename
    if not rows:
        p.write_text('')
        return
    with open(p, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys())
        w.writeheader()
        w.writerows(rows)


def write_summary(d: Path, run_id: str, verdict: str,
                  safety_events: list, recovery_events: list,
                  topo_ok: bool):
    crit    = [e for e in safety_events   if e['is_crit_risk']]
    caution = [e for e in safety_events   if not e['is_crit_risk']]
    term    = [e for e in recovery_events if e['is_terminal']]

    lines = [
        '# P4-B Negative Control — Summary',
        f'run_id:       {run_id}',
        f'date:         {datetime.utcnow().isoformat()}Z',
        f'verdict:      {verdict}',
        f'topology_ok:  {topo_ok}',
        '',
        '## SafetyEvents',
        f'critical_risk (STABILITY_RISK/FAULT_CRITICAL): {len(crit)}',
        f'caution_risk  (CAUTION):                       {len(caution)}',
        '',
        '## RecoveryEvents',
        f'total:    {len(recovery_events)}',
        f'terminal: {len(term)}',
        '',
        '## Approximations',
        '- CRITICAL approximated as risk_level in {STABILITY_RISK, FAULT_CRITICAL}.',
        '  SafetyEvent has no native severity field.',
        '',
        '## Limitations',
        f'- Modular jitter step=0.001 — healthy active baseline only.',
        '- Frozen-sensor FREEZE false positive NOT tested — deferred to P4-E.',
        f'- Watchdog STARTUP_GRACE_S={STARTUP_GRACE_S}s excluded from observation.',
    ]
    if caution:
        lines += ['', '## CAUTION events (classified, not FAIL)']
        for e in caution:
            lines.append(f'  src={e["source"]} risk={e["risk_level"]} | {e["notes"][:80]}')

    (d / 'p4b_summary.md').write_text('\n'.join(lines) + '\n')
    print(f'[P4B] summary written — verdict={verdict}')


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    run_id = (f'P4B-{datetime.utcnow().strftime("%Y%m%d_%H%M%S")}'
              f'-{str(uuid.uuid4())[:8]}')
    evidence_dir = Path(
        os.environ.get('ROS_EVIDENCE_DIR',
                       'evidence/4J/P4_THRESHOLDS/negative_control'))
    evidence_dir.mkdir(parents=True, exist_ok=True)

    write_environment(evidence_dir, run_id)

    rclpy.init()
    node = P4BHarness()

    topo_ok = False
    verdict  = 'UNSET'
    try:
        # Pre-flight: topology check — fail closed
        print(f'[P4B] Topology check (NAME_SETTLE_S={NAME_SETTLE_S}s)...')
        t_topo = time.monotonic()
        while time.monotonic() - t_topo < NAME_SETTLE_S:
            rclpy.spin_once(node, timeout_sec=0.1)
        topo_ok = node.check_topology()
        if not topo_ok:
            verdict = 'TOPO_FAIL'
            print('[P4B] TOPO_UNRESOLVED — aborting. Start runtime nodes first.')
            sys.exit(2)

        # Phase 1 — watchdog startup grace
        print(f'[P4B] Phase 1: startup grace {STARTUP_GRACE_S}s ...')
        t0 = time.monotonic()
        while time.monotonic() - t0 < STARTUP_GRACE_S:
            rclpy.spin_once(node, timeout_sec=0.1)

        # Phase 2 — post-grace settle
        print(f'[P4B] Phase 2: post-grace settle {POST_GRACE_SETTLE_S}s ...')
        t1 = time.monotonic()
        while time.monotonic() - t1 < POST_GRACE_SETTLE_S:
            rclpy.spin_once(node, timeout_sec=0.1)

        # Pre-Phase-3 cleanliness gate
        # Abort if runtime is still contaminated (orchestrator stuck in STABILITY_RISK)
        CLEANLINESS_WINDOW_S = 5.0
        print(f'[P4B] Cleanliness gate: {CLEANLINESS_WINDOW_S}s window before Phase 3...')
        node.clear_observation()
        t_gate = time.monotonic()
        while time.monotonic() - t_gate < CLEANLINESS_WINDOW_S:
            rclpy.spin_once(node, timeout_sec=0.1)
        gate_crit     = [e for e in node.safety_events   if e['is_crit_risk']]
        gate_terminal = [e for e in node.recovery_events if e['is_terminal']]
        if gate_crit or gate_terminal:
            verdict = 'STARTUP_CONTAMINATED'
            print(f'[P4B] STARTUP_CONTAMINATED: {len(gate_crit)} crit events, '
                  f'{len(gate_terminal)} terminal events in cleanliness window.')
            print('[P4B] Runtime state not clean. Abort — run docker restart and retry.')
            sys.exit(3)
        print('[P4B] Cleanliness gate: CLEAN — proceeding to Phase 3.')

        # Phase 3 — formal observation window
        node.clear_observation()
        print(f'[P4B] Phase 3: observation window {OBSERVATION_WINDOW_S}s — START')
        t2 = time.monotonic()
        while time.monotonic() - t2 < OBSERVATION_WINDOW_S:
            rclpy.spin_once(node, timeout_sec=0.1)
        print('[P4B] Phase 3: observation window — END')

    finally:
        crit_events = [e for e in node.safety_events   if e['is_crit_risk']]
        term_events = [e for e in node.recovery_events if e['is_terminal']]
        # Only assign PASS/FAIL if observation window completed (verdict still UNSET)
        # TOPO_FAIL and other abort verdicts are never overwritten
        if verdict == 'UNSET':
            verdict = 'PASS' if (not crit_events and not term_events) else 'FAIL'

        write_csv(evidence_dir, node.safety_events,   'p4b_events.csv')
        write_csv(evidence_dir, node.recovery_events, 'p4b_recovery.csv')
        write_summary(evidence_dir, run_id, verdict,
                      node.safety_events, node.recovery_events, topo_ok)

        rclpy.shutdown()

    print(f'\n[P4B] ══ VERDICT: {verdict} ══')
    print(f'       critical_risk SafetyEvents : {len(crit_events)}')
    print(f'       terminal RecoveryEvents    : {len(term_events)}')
    sys.exit(0 if verdict == 'PASS' else 1)


if __name__ == '__main__':
    main()
