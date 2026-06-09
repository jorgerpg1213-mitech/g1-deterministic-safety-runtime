import sys, time
sys.path.append("/isaac-sim/exts/isaacsim.ros2.bridge/humble/rclpy")
import rclpy
from sensor_msgs.msg import JointState

rclpy.init()
node = rclpy.create_node("g1_sub_trace")
got = {"n": 0, "first_fid": None}

def cb(msg):
    got["n"] += 1
    fid = msg.header.frame_id
    if got["first_fid"] is None:
        got["first_fid"] = fid
        print(f"=== FIRST RECEIVED: publisher_frame_id={fid} (yo entre cuando T1 iba en ese msg) ===", flush=True)
    if got["n"] % 25 == 0:
        print(f"[{time.strftime('%H:%M:%S')}] recv#{got['n']} publisher_frame_id={fid} pos0={round(msg.position[0],4)}", flush=True)

node.create_subscription(JointState, "/joint_states", cb, 10)
print("=== TRACE SUBSCRIBER LISTENING ===", flush=True)
t_end = time.time() + 200.0
while rclpy.ok() and time.time() < t_end:
    rclpy.spin_once(node, timeout_sec=1.0)
print(f"=== TRACE DONE: total {got['n']} msgs, first_frame_id={got['first_fid']} ===", flush=True)
node.destroy_node()
rclpy.shutdown()
