import sys, time
sys.path.append("/isaac-sim/exts/isaacsim.ros2.bridge/humble/rclpy")
import rclpy
from sensor_msgs.msg import JointState
from geometry_msgs.msg import PoseStamped, TwistStamped

rclpy.init()
node = rclpy.create_node("g1_state_sub")
got = {"js": 0, "pose": 0, "vel": 0}

def cb_js(m):
    got["js"] += 1
    if got["js"] == 1:
        print(f"=== JOINT_STATES OK: names={len(m.name)} pos={len(m.position)} vel={len(m.velocity)} ===", flush=True)

def cb_pose(m):
    got["pose"] += 1
    if got["pose"] == 1:
        p = m.pose.position
        q = m.pose.orientation
        print(f"=== BASE_POSE OK: xyz=[{round(p.x,3)},{round(p.y,3)},{round(p.z,3)}] wxyz=[{round(q.w,3)},{round(q.x,3)},{round(q.y,3)},{round(q.z,3)}] ===", flush=True)

def cb_vel(m):
    got["vel"] += 1
    if got["vel"] == 1:
        l = m.twist.linear
        a = m.twist.angular
        print(f"=== BASE_VELOCITY OK: lin=[{round(l.x,4)},{round(l.y,4)},{round(l.z,4)}] ang=[{round(a.x,4)},{round(a.y,4)},{round(a.z,4)}] ===", flush=True)

node.create_subscription(JointState, "/joint_states", cb_js, 10)
node.create_subscription(PoseStamped, "/g1/base_pose", cb_pose, 10)
node.create_subscription(TwistStamped, "/g1/base_velocity", cb_vel, 10)
print("=== SUB LISTENING on 3 topics ===", flush=True)
t_end = time.time() + 120.0
while rclpy.ok() and time.time() < t_end:
    rclpy.spin_once(node, timeout_sec=1.0)
    if got["js"] >= 50 and got["pose"] >= 50 and got["vel"] >= 50:
        break
print(f"=== SUB DONE: js={got['js']} pose={got['pose']} vel={got['vel']} ===", flush=True)
node.destroy_node()
rclpy.shutdown()
