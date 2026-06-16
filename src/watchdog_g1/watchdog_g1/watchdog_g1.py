"""
watchdog_g1.py
G1 ROS2 Pipeline — 4F-P2: Watchdog de salud del sistema

Responsabilidad: detectar si la telemetría usada por el runtime es confiable,
fresca y temporalmente válida. NO detecta incoherencia física (eso es el observer).

Detecta:
  - STALE:     topic sin mensaje en ventana configurable
  - FREEZE:    valores idénticos N muestras seguidas (excluye contactos)
  - NANINF:    NaN o inf en campos numéricos (position+velocity+effort completos)
  - TIMESTAMP: timestamp regresivo o fuera de orden
  - RATE:      frecuencia efectiva por debajo del mínimo esperado (con warm-up)

Severidad STALE:
  - IMU o ambos contactos: CRITICAL inmediato
  - Resto: WARN primero; CRITICAL si persiste >STALE_CRITICAL_S

Thresholds pragmáticos calibrables (DT-4F-001).
"""

import math
import time
import uuid

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy, HistoryPolicy

from diagnostic_msgs.msg import DiagnosticArray, DiagnosticStatus, KeyValue
from g1_msgs.msg import SafetyEvent, FootContact
from sensor_msgs.msg import Imu, JointState
from geometry_msgs.msg import PoseStamped

QOS_SAFETY_EVENTS = QoSProfile(reliability=ReliabilityPolicy.RELIABLE, durability=DurabilityPolicy.VOLATILE, history=HistoryPolicy.KEEP_LAST, depth=50)
QOS_DIAGNOSTICS   = QoSProfile(reliability=ReliabilityPolicy.BEST_EFFORT, durability=DurabilityPolicy.VOLATILE, history=HistoryPolicy.KEEP_LAST, depth=10)
QOS_SUB           = QoSProfile(reliability=ReliabilityPolicy.BEST_EFFORT, durability=DurabilityPolicy.VOLATILE, history=HistoryPolicy.KEEP_LAST, depth=10)

STALE_TIMEOUT_S      = 1.0
STALE_CRITICAL_S     = 3.0
FREEZE_N             = 5
MIN_RATE_HZ          = 3.0
RATE_WINDOW_S        = 2.0
RATE_WARMUP_N        = 5
STARTUP_GRACE_S      = 15.0   # gracia al arrancar antes de evaluar STALE
WATCHDOG_HZ          = 2.0
WATCHDOG_HEARTBEAT_HZ= 1.0
HARDWARE_ID          = 'g1_ros2_pipeline'
CRITICAL_STALE_TOPICS= {'/g1/imu', '/g1/contact/left', '/g1/contact/right'}
NO_FREEZE_TOPICS     = {'/g1/contact/left', '/g1/contact/right'}
MONITORED_TOPICS     = ['/g1/imu','/g1/contact/left','/g1/contact/right','/joint_states','/g1/base_pose']

def _has_naninf(values):
    for v in values:
        try:
            if math.isnan(float(v)) or math.isinf(float(v)):
                return True
        except (TypeError, ValueError):
            pass
    return False

class TopicMonitor:
    def __init__(self, topic):
        self.topic=topic; self.last_recv_wall=None; self.last_stamp_sec=None
        self.stale_since=None; self.freeze_buf=[]; self.recv_times=[]
        self.recv_count=0; self.latched={}
    def record(self, wall_now, stamp_sec, key_values):
        was_stale=self.is_stale(wall_now); self.last_recv_wall=wall_now; self.recv_count+=1
        if was_stale: self.stale_since=None
        ts_reg=(self.last_stamp_sec is not None and stamp_sec < self.last_stamp_sec-1e-6)
        self.last_stamp_sec=stamp_sec
        self.freeze_buf.append(tuple(round(v,6) for v in key_values))
        if len(self.freeze_buf)>FREEZE_N: self.freeze_buf.pop(0)
        self.recv_times.append(wall_now)
        self.recv_times=[t for t in self.recv_times if wall_now-t<=RATE_WINDOW_S]
        return ts_reg
    def age(self, wall_now):
        return None if self.last_recv_wall is None else wall_now-self.last_recv_wall
    def is_stale(self, wall_now):
        a=self.age(wall_now); return a is None or a>STALE_TIMEOUT_S
    def stale_duration(self, wall_now):
        if not self.is_stale(wall_now): return 0.0
        if self.stale_since is None: self.stale_since=wall_now
        return wall_now-self.stale_since
    def is_frozen(self):
        if len(self.freeze_buf)<FREEZE_N: return False
        return all(v==self.freeze_buf[0] for v in self.freeze_buf)
    def effective_rate(self, wall_now):
        self.recv_times=[t for t in self.recv_times if wall_now-t<=RATE_WINDOW_S]
        if len(self.recv_times)<2: return None
        span=self.recv_times[-1]-self.recv_times[0]
        return (len(self.recv_times)-1)/span if span>0 else 0.0
    def warmed_up(self): return self.recv_count>=RATE_WARMUP_N
    def try_latch(self, rule_id):
        if rule_id not in self.latched: self.latched[rule_id]=True; return True
        return False
    def reset_latch(self, rule_id): self.latched.pop(rule_id,None)

class WatchdogG1(Node):
    def __init__(self):
        super().__init__('watchdog_g1')
        self._pub_safety=self.create_publisher(SafetyEvent,'/safety_events',QOS_SAFETY_EVENTS)
        self._pub_diag=self.create_publisher(DiagnosticArray,'/diagnostics',QOS_DIAGNOSTICS)
        self._monitors={t:TopicMonitor(t) for t in MONITORED_TOPICS}
        self.create_subscription(Imu,'/g1/imu',self._cb_imu,QOS_SUB)
        self.create_subscription(FootContact,'/g1/contact/left',self._cb_cl,QOS_SUB)
        self.create_subscription(FootContact,'/g1/contact/right',self._cb_cr,QOS_SUB)
        self.create_subscription(JointState,'/joint_states',self._cb_js,QOS_SUB)
        self.create_subscription(PoseStamped,'/g1/base_pose',self._cb_pose,QOS_SUB)
        self._start_time = time.time()
        self.create_timer(1.0/WATCHDOG_HZ,self._check)
        self.create_timer(1.0/WATCHDOG_HEARTBEAT_HZ,self._heartbeat)
        self.get_logger().info('4F-P2 watchdog_g1 iniciado. STALE>{}s FREEZE>{} RATE<{}Hz warmup={}msgs (DT-4F-001).'.format(STALE_TIMEOUT_S,FREEZE_N,MIN_RATE_HZ,RATE_WARMUP_N))

    def _recv(self,topic,stamp_sec,key_values):
        wall=time.time(); m=self._monitors[topic]; ts_reg=m.record(wall,stamp_sec,key_values)
        if _has_naninf(key_values):
            self._emit('4F-P2-NANINF','CRITICAL',topic,'NaN/inf en {} valores={}'.format(topic,list(key_values)[:8]))
        if ts_reg:
            self._emit('4F-P2-TIMESTAMP','WARN',topic,'Timestamp regresivo en {} stamp={:.3f}'.format(topic,stamp_sec))
        else:
            m.reset_latch('4F-P2-TIMESTAMP')

    def _cb_imu(self,msg):
        s=msg.header.stamp
        vals=[msg.orientation.w,msg.orientation.x,msg.orientation.y,msg.orientation.z,msg.linear_acceleration.x,msg.linear_acceleration.y,msg.linear_acceleration.z,msg.angular_velocity.x,msg.angular_velocity.y,msg.angular_velocity.z]
        self._recv('/g1/imu',s.sec+s.nanosec*1e-9,vals)

    def _cb_cl(self,msg):
        s=msg.header.stamp
        self._recv('/g1/contact/left',s.sec+s.nanosec*1e-9,[float(msg.in_contact),msg.force])

    def _cb_cr(self,msg):
        s=msg.header.stamp
        self._recv('/g1/contact/right',s.sec+s.nanosec*1e-9,[float(msg.in_contact),msg.force])

    def _cb_js(self,msg):
        s=msg.header.stamp
        all_vals=list(msg.position)+list(msg.velocity)+list(msg.effort)
        self._recv('/joint_states',s.sec+s.nanosec*1e-9,list(msg.position[:6]) if msg.position else [0.0])
        if _has_naninf(all_vals):
            self._emit('4F-P2-NANINF','CRITICAL','/joint_states','NaN/inf en joint_states pos/vel/eff ({} valores)'.format(len(all_vals)))

    def _cb_pose(self,msg):
        s=msg.header.stamp
        vals=[msg.pose.position.x,msg.pose.position.y,msg.pose.position.z,msg.pose.orientation.w,msg.pose.orientation.x,msg.pose.orientation.y,msg.pose.orientation.z]
        self._recv('/g1/base_pose',s.sec+s.nanosec*1e-9,vals)

    def _check(self):
        wall=time.time()
        if wall - self._start_time < STARTUP_GRACE_S:
            return
        for topic,m in self._monitors.items():
            if m.is_stale(wall):
                dur=m.stale_duration(wall); age=m.age(wall)
                age_str='{:.2f}s'.format(age) if age is not None else 'nunca recibido'
                sev='CRITICAL' if (topic in CRITICAL_STALE_TOPICS or dur>=STALE_CRITICAL_S) else 'WARN'
                self._emit('4F-P2-STALE',sev,topic,'STALE {} sin mensaje {} dur={:.1f}s'.format(topic,age_str,dur))
            else:
                m.reset_latch('4F-P2-STALE'); m.stale_since=None
                if topic not in NO_FREEZE_TOPICS:
                    if m.is_frozen():
                        self._emit('4F-P2-FREEZE','WARN',topic,'FREEZE {} valor identico {} muestras'.format(topic,FREEZE_N))
                    else:
                        m.reset_latch('4F-P2-FREEZE')
                if m.warmed_up():
                    rate=m.effective_rate(wall)
                    if rate is not None and rate<MIN_RATE_HZ:
                        self._emit('4F-P2-RATE','WARN',topic,'RATE bajo {} medido={:.2f}Hz min={}Hz'.format(topic,rate,MIN_RATE_HZ))
                    elif rate is not None:
                        m.reset_latch('4F-P2-RATE')

    def _emit(self,rule_id,severity,topic,notes):
        m=self._monitors[topic]
        if not m.try_latch(rule_id): return
        msg=SafetyEvent()
        msg.event_id=str(uuid.uuid4()); msg.event_type='CONDITION_DETECTED'
        msg.source='watchdog_g1'; msg.source_authority='SECONDARY'
        msg.authority_effectiveness='EFFECTIVE'; msg.target=topic
        msg.risk_level='STABILITY_RISK' if severity=='CRITICAL' else 'CAUTION'
        msg.restriction_level='NONE'; msg.transition_id=''
        msg.transition_priority='NORMAL'; msg.execution_confidence='BEST_EFFORT'
        msg.timestamp=self.get_clock().now().to_msg()
        msg.notes='rule_id={} severity={} topic={} | {} | Threshold pragmatico calibrable (DT-4F-001).'.format(rule_id,severity,topic,notes)
        self._pub_safety.publish(msg)
        if severity=='CRITICAL':
            self.get_logger().error('[{}] SafetyEvent CRITICAL — {} | {} | id={}'.format(rule_id,topic,notes,msg.event_id))
        else:
            self.get_logger().warn('[{}] SafetyEvent WARN — {} | {} | id={}'.format(rule_id,topic,notes,msg.event_id))

    def _heartbeat(self):
        wall=time.time(); stale=[t for t,m in self._monitors.items() if m.is_stale(wall)]
        level=DiagnosticStatus.WARN if stale else DiagnosticStatus.OK
        status=DiagnosticStatus(); status.level=level; status.name='watchdog_g1'
        status.message='4F-P2 activo stale={}'.format(stale if stale else 'ninguno')
        status.hardware_id=HARDWARE_ID
        status.values=[KeyValue(key='monitored_topics',value=str(len(MONITORED_TOPICS))),KeyValue(key='stale_topics',value=str(stale)),KeyValue(key='stale_timeout_s',value=str(STALE_TIMEOUT_S)),KeyValue(key='freeze_n',value=str(FREEZE_N)),KeyValue(key='min_rate_hz',value=str(MIN_RATE_HZ)),KeyValue(key='rate_warmup_n',value=str(RATE_WARMUP_N))]
        arr=DiagnosticArray(); arr.header.stamp=self.get_clock().now().to_msg(); arr.status=[status]
        self._pub_diag.publish(arr)

def main(args=None):
    rclpy.init(args=args)
    node=WatchdogG1()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node(); rclpy.shutdown()

if __name__=='__main__':
    main()
