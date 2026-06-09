import sys
sys.path.append("/isaac-sim/exts/isaacsim.ros2.bridge/humble/rclpy")
import rclpy
from sensor_msgs.msg import JointState

rclpy.init()
node = rclpy.create_node("g1_sub_check")
got = {"n": 0}

def cb(msg):
    got["n"] += 1
    if got["n"] == 1:
        print(f"=== RECEIVED 1st msg: names={len(msg.name)} pos={len(msg.position)} vel={len(msg.velocity)} ===", flush=True)
        print(f"  name[0:3]={list(msg.name[0:3])}", flush=True)
        print(f"  pos[0:3]={[round(x,4) for x in msg.position[0:3]]}", flush=True)
    if got["n"] % 50 == 0:
        print(f"=== RECEIVED {got['n']} msgs ===", flush=True)

node.create_subscription(JointState, "/joint_states", cb, 10)
print("=== SUBSCRIBER LISTENING on /joint_states ===", flush=True)
import time
t_end = time.time() + 120.0
while rclpy.ok() and time.time() < t_end:
    rclpy.spin_once(node, timeout_sec=1.0)
    if got["n"] >= 100:
        break
print(f"=== SUB DONE: total received {got['n']} msgs ===", flush=True)
node.destroy_node()
rclpy.shutdown()
