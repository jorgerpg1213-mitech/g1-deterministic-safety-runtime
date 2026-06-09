import omni.ext
import carb


class Extension(omni.ext.IExt):
    def on_startup(self, ext_id):
        print("=== STARTUP EXTENSION OK ===", flush=True)
        carb.log_warn("=== STARTUP EXTENSION OK ===")
        try:
            import isaacsim.sensors.physics as sp
            print("=== SENSORS.PHYSICS IMPORT OK ===", flush=True)
            carb.log_warn("=== SENSORS.PHYSICS IMPORT OK ===")
            from isaacsim.sensors.physics import IMUSensor, ContactSensor
            print("=== IMU + CONTACT CLASSES AVAILABLE ===", flush=True)
            carb.log_warn("=== IMU + CONTACT CLASSES AVAILABLE ===")
        except Exception as e:
            print(f"=== SENSORS IMPORT FAILED: {type(e).__name__}: {e} ===", flush=True)
            import traceback
            traceback.print_exc()

    def on_shutdown(self):
        print("=== EXTENSION SHUTDOWN ===", flush=True)
