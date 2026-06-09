import sys, time
sys.path.append("/isaac-sim/exts/isaacsim.ros2.bridge/humble/rclpy")
import rclpy
from sensor_msgs.msg import Imu
from std_msgs.msg import Float32MultiArray

rclpy.init()
node = rclpy.create_node("g1_live_sub")
st = {"imu": None, "feet": None, "n": 0}

def estado(w, avz, lc, rc):
    import math
    avmag = abs(avz)
    if w > 0.95 and (lc or rc):
        return "DE_PIE"
    if avmag > 0.5 or (0.67 < w < 0.95):
        return "CAYENDO"
    return "EN_PISO"

def cb_imu(m):
    st["imu"] = m
def cb_feet(m):
    st["feet"] = m
    st["n"] += 1
    imu = st["imu"]
    if imu is None:
        return
    cnt = int(m.data[0]); lc = m.data[1] > 0.5; lf = m.data[2]; rc = m.data[3] > 0.5; rf = m.data[4]
    w = imu.orientation.w; avz = imu.angular_velocity.z
    e = estado(w, avz, lc, rc)
    if st["n"] == 1 or st["n"] % 20 == 0:
        print(f"[{time.strftime('%H:%M:%S')}] frame={cnt} W={round(w,3)} angZ={round(avz,3)} | L={lc}/{round(lf,1)} R={rc}/{round(rf,1)} | {e}", flush=True)

node.create_subscription(Imu, "/g1/imu", cb_imu, 10)
node.create_subscription(Float32MultiArray, "/g1/feet", cb_feet, 10)
print("=== T2 ESCUCHANDO (esperando a T1)... ===", flush=True)
t_end = time.time() + 240.0
while rclpy.ok() and time.time() < t_end:
    rclpy.spin_once(node, timeout_sec=1.0)
print(f"=== T2 DONE: recibidos {st['n']} ===", flush=True)
node.destroy_node()
rclpy.shutdown()
