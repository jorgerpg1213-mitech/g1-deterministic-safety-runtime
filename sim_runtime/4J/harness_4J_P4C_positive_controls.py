#!/usr/bin/env python3
"""
G1 Deterministic Safety Runtime — 4J-P4-C Positive Controls Harness
Route: R0 detection-only via /safety_events.
No runtime modification. No threshold tuning. No recovery claim.

PM-approved scope (2026-06-25):
  Blocking  (N=3): stale, freeze, naninf, timestamp, fallen
  Informational (N=1): rate
  docker restart boring_noether required between repetitions.

Expected outcomes derived from source audit — NOT from memory.
  watchdog_g1.py         L39-44, L118-171
  cross_consistency_observer.py  L77-385
  g1_msgs/msg/SafetyEvent.msg  (fields: event_id, source, risk_level, notes)

Patch v2 corrections (PM-mandated):
  [P1] callback uses real SafetyEvent fields: risk_level, source — not msg.risk
  [P2] injection_wall_start tracked; _classify enforces timing window
  [P3] FALLEN inter-sample sleep reduced 0.5s → 0.25s (< FRESH_MAX_AGE_S margin)
  [P4] watchdog cases inject fault on /g1/imu only; /imu stays healthy
       FALLEN injects on /imu only; /g1/imu stays healthy
  [P5] topology check moved to launcher (node-only) — no harness-published topics required

Usage:
  python3 harness_4J_P4C_positive_controls.py \\
      --case <case> --run-id <1|2|3> \\
      --output-dir evidence/4J/P4_THRESHOLDS/positive_controls [--dry-run]
"""

import argparse, json, os, threading, time
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Imu, JointState
from geometry_msgs.msg import PoseStamped
from g1_msgs.msg import SafetyEvent, FootContact

# ----------------------------------------------------------------
# THRESHOLDS — extracted from source. DO NOT MODIFY.
# ----------------------------------------------------------------
STALE_TIMEOUT_S      = 1.0    # watchdog_g1.py L39
STALE_CRITICAL_S     = 3.0    # watchdog_g1.py L40
FREEZE_N             = 5      # watchdog_g1.py L41
MIN_RATE_HZ          = 3.0    # watchdog_g1.py L42
RATE_WINDOW_S        = 2.0    # watchdog_g1.py L43
RATE_WARMUP_N        = 5      # watchdog_g1.py L44
STARTUP_GRACE_S      = 15.0   # watchdog_g1.py L45
FALLEN_W_CRITICAL    = 0.80   # cross_consistency_observer.py L80
FALLEN_CONSECUTIVE_N = 3      # cross_consistency_observer.py L82
FRESH_MAX_AGE_S      = 0.5    # cross_consistency_observer.py L78

# ----------------------------------------------------------------
# EXPECTED OUTCOMES — derived from source audit. DO NOT INFER.
#
# Case       Detector                    rule_id          Severity  Source line
# --------   --------------------------  ---------------  --------  -----------
# STALE      watchdog_g1                 4F-P2-STALE      CRITICAL  L158
# FREEZE     watchdog_g1                 4F-P2-FREEZE     WARN      L163
# NANINF     watchdog_g1                 4F-P2-NANINF     CRITICAL  L118
# TIMESTAMP  watchdog_g1                 4F-P2-TIMESTAMP  WARN      L120
# FALLEN     cross_consistency_observer  4F-P1            CRITICAL  L382
# RATE       watchdog_g1                 4F-P2-RATE       WARN      L169
#
# STALE /g1/imu → CRITICAL immediate (CRITICAL_STALE_TOPICS L49).
# FREEZE → always WARN (L163). NO_FREEZE_TOPICS excludes contacts (L50).
# FALLEN uses rule_id=4F-P1 — NOT 4F-P2 (separate emit path, L382).
# Severity extracted from notes field: format "severity={CRITICAL|WARN}"
# Detector validated via msg.source field.
# ----------------------------------------------------------------
EXPECTED = {
    'stale':     {'rule_id': '4F-P2-STALE',     'severity': 'CRITICAL',
                  'detector': 'watchdog_g1',                'blocking': True},
    'freeze':    {'rule_id': '4F-P2-FREEZE',     'severity': 'WARN',
                  'detector': 'watchdog_g1',                'blocking': True},
    'naninf':    {'rule_id': '4F-P2-NANINF',     'severity': 'CRITICAL',
                  'detector': 'watchdog_g1',                'blocking': True},
    'timestamp': {'rule_id': '4F-P2-TIMESTAMP',  'severity': 'WARN',
                  'detector': 'watchdog_g1',                'blocking': True},
    'fallen':    {'rule_id': '4F-P1',            'severity': 'CRITICAL',
                  'detector': 'cross_consistency_observer', 'blocking': True},
    'rate':      {'rule_id': '4F-P2-RATE',       'severity': 'WARN',
                  'detector': 'watchdog_g1',                'blocking': False},
}

# Detection windows — PM-approved
DETECT_WINDOW = {
    'stale':     STALE_TIMEOUT_S + 2.0,                       # 3.0s
    'freeze':    (FREEZE_N + 3) * 0.15 + 2.0,                 # ~3.2s
    'naninf':    2.0,
    'timestamp': 2.0,
    'fallen':    FALLEN_CONSECUTIVE_N * 2.0 + 4.0,            # ~10s — observer timer rate desconocido
    'rate':      RATE_WARMUP_N / MIN_RATE_HZ + RATE_WINDOW_S + 3.0,  # ~6.7s
}

WARMUP_S = 6.0
PUB_HZ   = 10.0


class P4CHarness(Node):

    def __init__(self, case, run_id, out_dir, dry_run=False):
        super().__init__(f'p4c_{case}_{run_id}')
        self.case    = case
        self.run_id  = run_id
        self.out_dir = out_dir
        self.dry_run = dry_run

        self.pub_imu_g1 = self.create_publisher(Imu,        '/g1/imu',           10)
        self.pub_imu    = self.create_publisher(Imu,        '/imu',              10)
        self.pub_cl     = self.create_publisher(FootContact, '/g1/contact/left',  10)
        self.pub_cr     = self.create_publisher(FootContact, '/g1/contact/right', 10)
        self.pub_joints = self.create_publisher(JointState,  '/joint_states',     10)
        self.pub_pose   = self.create_publisher(PoseStamped, '/g1/base_pose',     10)

        # [P1] Use real SafetyEvent fields: risk_level, source — NOT msg.risk
        self.sub = self.create_subscription(
            SafetyEvent, '/safety_events', self._cb, 10)

        self.events = []
        self.phase  = 'INIT'

    def _cb(self, msg):
        self.events.append({
            'phase':      self.phase,
            'event_id':   getattr(msg, 'event_id', ''),
            'risk_level': getattr(msg, 'risk_level', ''),   # [P1]
            'source':     getattr(msg, 'source', ''),       # [P1]
            'notes':      getattr(msg, 'notes', ''),
            'wall':       time.time(),
        })

    # ---- healthy data helpers ----
    def _imu_healthy(self, tick=0):
        m = Imu()
        m.header.stamp = self.get_clock().now().to_msg()
        m.orientation.w = 0.999 - (tick % 7) * 0.001   # abs_w > 0.85, modular jitter
        m.orientation.x = 0.0
        m.orientation.y = 0.0
        m.orientation.z = 0.0
        m.linear_acceleration.z = 9.81 + (tick % 5) * 0.001  # jitter prevents FREEZE
        return m

    def _contact(self, val=True):
        m = FootContact()
        m.header.stamp = self.get_clock().now().to_msg()
        m.in_contact = val
        return m

    def _joints(self, tick=0):
        m = JointState()
        m.header.stamp = self.get_clock().now().to_msg()
        m.name     = ['j1', 'j2']
        m.position = [0.1 + (tick % 100) * 0.001, 0.2 + (tick % 100) * 0.001]
        m.velocity = [0.0, 0.0]
        m.effort   = [0.0, 0.0]
        return m

    def _pose(self, tick=0):
        m = PoseStamped()
        m.header.stamp = self.get_clock().now().to_msg()
        m.pose.position.z    = 1.0 + 0.001 * (tick % 5)  # jitter previene FREEZE
        m.pose.orientation.w = 1.0
        return m

    def _pub_all_healthy(self, tick=0):
        """All topics healthy — used during warmup."""
        imu = self._imu_healthy(tick)
        self.pub_imu_g1.publish(imu)
        self.pub_imu.publish(imu)
        self.pub_cl.publish(self._contact(True))
        self.pub_cr.publish(self._contact(True))
        self.pub_joints.publish(self._joints(tick))
        self.pub_pose.publish(self._pose(tick))

    def _pub_no_imu_g1(self, tick=0):
        """All topics healthy EXCEPT /g1/imu. Used during STALE injection."""
        self.pub_imu.publish(self._imu_healthy(tick))  # [P4] observer stays healthy
        self.pub_cl.publish(self._contact(True))
        self.pub_cr.publish(self._contact(True))
        self.pub_joints.publish(self._joints(tick))
        self.pub_pose.publish(self._pose(tick))

    def _pub_watchdog_healthy(self, tick=0):
        """[P4] Healthy /g1/imu + support. Used when /imu carries FALLEN fault."""
        self.pub_imu_g1.publish(self._imu_healthy(tick))
        self.pub_cl.publish(self._contact(True))
        self.pub_cr.publish(self._contact(True))
        self.pub_joints.publish(self._joints(tick))
        self.pub_pose.publish(self._pose(tick))

    # ---- main execution ----
    def execute(self):
        os.makedirs(self.out_dir, exist_ok=True)
        exp    = EXPECTED[self.case]
        window = DETECT_WINDOW[self.case]
        summary = {
            'case':               self.case,
            'run_id':             self.run_id,
            'dry_run':            self.dry_run,
            'expected':           exp,
            'detection_window_s': window,
            'result':             None,
            'fail_reason':        None,
            'invalid_reason':     None,
            'injection_wall_start': None,   # [P2]
            'events':             [],
            'wall_start':         time.time(),
        }

        # ---- WARMUP ----
        self.phase = 'WARMUP'
        self.get_logger().info(f'[P4-C:{self.case}:{self.run_id}] WARMUP {WARMUP_S}s')
        t0   = time.time()
        tick = 0
        while time.time() - t0 < WARMUP_S:
            self._pub_all_healthy(tick)
            tick += 1
            time.sleep(1.0 / PUB_HZ)

        # Startup contamination gate
        crit_wu = [e for e in self.events
                   if e['phase'] == 'WARMUP' and 'FAULT_CRITICAL' in e.get('risk_level', '')]
        if crit_wu:
            summary['result']         = 'INVALID'
            summary['invalid_reason'] = f'startup contamination: {len(crit_wu)} FAULT_CRITICAL events during warmup'
            summary['events']         = self.events
            return self._save(summary)

        self.events.clear()

        if self.dry_run:
            self.get_logger().info('[P4-C] --dry-run: warmup PASS, skip injection.')
            summary['result'] = 'DRY_RUN_OK'
            return self._save(summary)

        # ---- INJECTION ----
        self.phase = 'INJECTION'
        inject_wall = time.time()
        summary['injection_wall_start'] = inject_wall   # [P2]
        self.get_logger().info(f'[P4-C:{self.case}:{self.run_id}] INJECT')
        frozen_imu = self._build_frozen_imu()
        self._do_inject(tick, frozen_imu)

        # ---- OBSERVATION ----
        self.phase = 'OBSERVATION'
        self.get_logger().info(
            f'[P4-C:{self.case}:{self.run_id}] OBS window={window:.1f}s')
        t_obs = time.time()

        while time.time() - t_obs < window:
            if self.case == 'stale':
                # [P4] no /g1/imu — watchdog detects absence; /imu healthy
                self._pub_no_imu_g1(tick)
                tick += 1
                time.sleep(0.2)
            elif self.case == 'freeze':
                frozen_imu.header.stamp = self.get_clock().now().to_msg()
                self.pub_imu_g1.publish(frozen_imu)
                self.pub_imu.publish(self._imu_healthy(tick))
                self.pub_cl.publish(self._contact(True))
                self.pub_cr.publish(self._contact(True))
                self.pub_joints.publish(self._joints(tick))
                self.pub_pose.publish(self._pose(tick))
                tick += 1
                time.sleep(0.15)
            elif self.case == 'rate':
                # /g1/imu a 1Hz (< MIN_RATE_HZ=3.0Hz): cada 5to ciclo de 0.2s
                # Soporte topics a 5Hz para evitar STALE contaminacion
                self.pub_imu.publish(self._imu_healthy(tick))
                self.pub_cl.publish(self._contact(True))
                self.pub_cr.publish(self._contact(True))
                self.pub_joints.publish(self._joints(tick))
                self.pub_pose.publish(self._pose(tick))
                if tick % 5 == 0:  # 5 x 0.2s = 1.0Hz en /g1/imu
                    self.pub_imu_g1.publish(self._imu_healthy(tick))
                tick += 1
                time.sleep(0.2)
            elif self.case == 'fallen':
                # Observer evalúa en timer — necesita fallen IMU fresca en cada tick
                # Publicar fallen en /imu cada 0.2s < FRESH_MAX_AGE_S=0.5s
                fallen_obs = Imu()
                fallen_obs.header.stamp = self.get_clock().now().to_msg()
                fallen_obs.orientation.w = 0.70
                fallen_obs.orientation.y = 0.714
                fallen_obs.linear_acceleration.z = 9.81
                self.pub_imu.publish(fallen_obs)
                self.pub_cl.publish(self._contact(True))
                self.pub_cr.publish(self._contact(True))
                self._pub_watchdog_healthy(tick)  # /g1/imu healthy
                tick += 1
                time.sleep(0.2)
            else:
                # naninf / timestamp: injected; keep all healthy to avoid STALE
                self._pub_all_healthy(tick)
                tick += 1
                time.sleep(0.1)

        # ---- CLASSIFY ----
        inj = [e for e in self.events
               if e['phase'] in ('INJECTION', 'OBSERVATION')]
        summary['events'] = inj
        result, reason = self._classify(inj, exp, inject_wall)  # [P2]
        summary['result']      = result
        summary['fail_reason'] = reason
        summary['wall_end']    = time.time()
        return self._save(summary)

    def _build_frozen_imu(self):
        """Frozen IMU — identical payload across publications for FREEZE detection.
        abs_w=0.950 > FALLEN_W_WARN=0.85 — no FALLEN cross-trigger on observer."""
        m = Imu()
        m.orientation.w           = 0.950
        m.orientation.x           = 0.0
        m.orientation.y           = 0.0
        m.orientation.z           = 0.0
        m.linear_acceleration.x   = 0.0
        m.linear_acceleration.y   = 0.0
        m.linear_acceleration.z   = 9.81
        return m

    def _do_inject(self, base_tick, frozen_imu):
        case = self.case

        if case == 'stale':
            # Stop /g1/imu (/g1/imu ∈ CRITICAL_STALE_TOPICS L49 → CRITICAL immediate).
            # [P4] Observation loop keeps /imu and all other topics healthy.
            self.get_logger().warn('[P4-C] STALE: /g1/imu stopped')

        elif case == 'freeze':
            # [P4] Inject frozen value on /g1/imu ONLY.
            # /imu gets healthy jitter — observer isolated from fault.
            self.get_logger().warn(f'[P4-C] FREEZE: {FREEZE_N+2} frozen samples → /g1/imu')
            for i in range(FREEZE_N + 2):
                frozen_imu.header.stamp = self.get_clock().now().to_msg()
                self.pub_imu_g1.publish(frozen_imu)
                self.pub_imu.publish(self._imu_healthy(base_tick + i))
                self.pub_cl.publish(self._contact(True))
                self.pub_cr.publish(self._contact(True))
                self.pub_joints.publish(self._joints(base_tick + i))
                self.pub_pose.publish(self._pose(base_tick + i))
                time.sleep(0.1)

        elif case == 'naninf':
            # [P4] NaN on /g1/imu ONLY. watchdog_g1 path L118.
            self.get_logger().warn('[P4-C] NANINF: NaN linear_acceleration → /g1/imu')
            m = Imu()
            m.header.stamp = self.get_clock().now().to_msg()
            m.orientation.w           = 1.0
            m.linear_acceleration.x   = float('nan')
            m.linear_acceleration.y   = float('nan')
            m.linear_acceleration.z   = float('nan')
            self.pub_imu_g1.publish(m)                         # [P4] /g1/imu only
            # /imu stays healthy via observation loop

        elif case == 'timestamp':
            # [P4] Regressive stamp on /g1/imu ONLY. watchdog_g1 path L120.
            self.get_logger().warn('[P4-C] TIMESTAMP: regressed stamp → /g1/imu')
            m = self._imu_healthy(base_tick)
            m.header.stamp.sec    = max(0, m.header.stamp.sec - 30)
            m.header.stamp.nanosec = 0
            self.pub_imu_g1.publish(m)                         # [P4] /g1/imu only

        elif case == 'fallen':
            # [P4] abs_w=0.70 on /imu ONLY. Observer path L382.
            # /g1/imu stays healthy via _pub_watchdog_healthy in observation loop.
            # [P3] sleep=0.25s < FRESH_MAX_AGE_S=0.5s margin.
            # Contacts healthy (True) → isolates orientation path, avoids both_lost.
            self.get_logger().warn(
                f'[P4-C] FALLEN: abs_w=0.70 × {FALLEN_CONSECUTIVE_N+1} → /imu')
            for i in range(FALLEN_CONSECUTIVE_N + 1):
                m = Imu()
                m.header.stamp    = self.get_clock().now().to_msg()
                m.orientation.w   = 0.70     # abs_w < FALLEN_W_CRITICAL=0.80
                m.orientation.x   = 0.0
                m.orientation.y   = 0.714    # |q|≈1
                m.orientation.z   = 0.0
                m.linear_acceleration.z = 9.81
                self.pub_imu.publish(m)                        # [P4] /imu only
                self.pub_cl.publish(self._contact(True))
                self.pub_cr.publish(self._contact(True))
                self.pub_imu_g1.publish(self._imu_healthy(base_tick + i))  # [P4] watchdog healthy
                self.get_logger().info(f'[P4-C] FALLEN sample {i+1}/{FALLEN_CONSECUTIVE_N+1}')
                time.sleep(0.25)   # [P3] < FRESH_MAX_AGE_S=0.5s margin

        elif case == 'rate':
            # Warmup delivered N≥5 msgs at 10Hz (RATE_WARMUP_N=5 satisfied).
            # Observation loop publishes /g1/imu at 1.0Hz < MIN_RATE_HZ=3.0Hz.
            # [P4] /imu stays healthy in observation loop.
            self.get_logger().warn('[P4-C] RATE: switching to 1.0Hz (< 3.0Hz)')

    def _classify(self, events, exp, inject_wall):
        """[P2] Classify with timing enforcement.
        Returns (result_str, fail_reason_str_or_None)."""
        rule_id  = exp['rule_id']
        severity = exp['severity']   # 'CRITICAL' or 'WARN'
        detector = exp['detector']
        window   = DETECT_WINDOW[self.case]

        # Match by rule_id embedded in notes (format: "rule_id=4F-P2-STALE ...")
        matched = [e for e in events if rule_id in e.get('notes', '')]
        if not matched:
            return 'FAIL', f'no SafetyEvent with rule_id={rule_id} in notes'

        # Contamination guard: mismo detector emitió rule_id inesperado
        unexpected = [
            e for e in events
            if rule_id not in e.get('notes', '')
            and e.get('source') == detector
            and 'rule_id=' in e.get('notes', '')
        ]
        if unexpected:
            return 'INVALID', (
                f'unrelated {detector} event(s) during run: '
                f'{[e["notes"][:60] for e in unexpected[:3]]}'
            )

        ev = matched[0]

        if not ev.get('event_id'):
            return 'FAIL', 'missing event_id'

        # [P1] Validate detector via msg.source
        src = ev.get('source', '')
        if detector not in src:
            return 'FAIL', f'wrong detector: got source="{src}", expected "{detector}"'

        # Validate severity via notes (format: "severity=CRITICAL" or "severity=WARN")
        notes = ev.get('notes', '')
        if f'severity={severity}' not in notes:
            return 'FAIL', f'severity mismatch: expected severity={severity} in notes; got: {notes[:80]}'

        # [P2] Detection within approved window
        dt = ev['wall'] - inject_wall
        if dt > window:
            return 'FAIL', f'outside window: dt={dt:.3f}s > window={window:.1f}s'

        return 'PASS', None

    def _save(self, summary):
        path = os.path.join(self.out_dir,
                            f'p4c_{self.case}_run{self.run_id}.json')
        with open(path, 'w') as f:
            json.dump(summary, f, indent=2, default=str)
        self.get_logger().info(
            f'[P4-C] RESULT={summary["result"]} → {path}')
        return summary


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--case', required=True,
                    choices=['stale','freeze','naninf','timestamp','fallen','rate'])
    ap.add_argument('--run-id', type=int, default=1)
    ap.add_argument('--output-dir',
                    default='evidence/4J/P4_THRESHOLDS/positive_controls')
    ap.add_argument('--dry-run', action='store_true',
                    help='Topology + warmup only — no fault injection')
    args = ap.parse_args()

    out = os.path.join(args.output_dir, args.case)
    rclpy.init()
    node = P4CHarness(args.case, args.run_id, out, dry_run=args.dry_run)

    spin_t = threading.Thread(target=rclpy.spin, args=(node,), daemon=True)
    spin_t.start()

    summary = node.execute()
    print(f'\n[P4-C] case={args.case} run_id={args.run_id} → {summary["result"]}')
    if summary.get('fail_reason'):
        print(f'[P4-C] FAIL reason: {summary["fail_reason"]}')
    if summary.get('invalid_reason'):
        print(f'[P4-C] INVALID: {summary["invalid_reason"]}')

    node.destroy_node()
    rclpy.shutdown()
    spin_t.join(timeout=2.0)


if __name__ == '__main__':
    main()
