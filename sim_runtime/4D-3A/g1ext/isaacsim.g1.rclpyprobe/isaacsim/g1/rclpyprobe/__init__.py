import omni.ext
import carb
import sys
class Extension(omni.ext.IExt):
    def on_startup(self, ext_id):
        print("=== STARTUP EXTENSION OK ===", flush=True)
        carb.log_warn("=== STARTUP EXTENSION OK ===")
        sys.path.append("/isaac-sim/exts/isaacsim.ros2.bridge/humble/rclpy")
        try:
            import rclpy
            rclpy.init()
            n = rclpy.create_node("g1_kit_probe")
            msg = f"=== RCLPY IN KIT OK: {n.get_name()} ==="
            print(msg, flush=True)
            carb.log_warn(msg)
            n.destroy_node()
            rclpy.shutdown()
            print("=== RCLPY SHUTDOWN CLEAN ===", flush=True)
        except Exception as e:
            print(f"=== RCLPY IN KIT FAILED: {type(e).__name__}: {e} ===", flush=True)
            import traceback; traceback.print_exc()
    def on_shutdown(self):
        print("=== EXTENSION SHUTDOWN ===", flush=True)
