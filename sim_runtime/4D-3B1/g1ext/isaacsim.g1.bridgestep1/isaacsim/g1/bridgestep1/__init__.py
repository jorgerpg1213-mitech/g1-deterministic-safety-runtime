import omni.ext
import carb
import sys
import asyncio
class Extension(omni.ext.IExt):
    def on_startup(self, ext_id):
        print("=== STARTUP EXTENSION OK ===", flush=True)
        carb.log_warn("=== STARTUP EXTENSION OK ===")
        self._task = asyncio.ensure_future(self._run_async())
    async def _run_async(self):
        # --- Paso A: rclpy (sin publicar) ---
        try:
            sys.path.append("/isaac-sim/exts/isaacsim.ros2.bridge/humble/rclpy")
            import rclpy
            rclpy.init()
            self._node = rclpy.create_node("g1_bridge_node")
            print(f"=== RCLPY NODE OK: {self._node.get_name()} ===", flush=True)
            carb.log_warn(f"=== RCLPY NODE OK: {self._node.get_name()} ===")
        except Exception as e:
            print(f"=== RCLPY FAILED: {type(e).__name__}: {e} ===", flush=True)
            import traceback; traceback.print_exc()
            return
        # --- Paso B: cargar G1 ---
        try:
            from isaacsim.core.api import World
            from isaacsim.core.utils.stage import create_new_stage_async, add_reference_to_stage, is_stage_loading
            from isaacsim.core.prims import Articulation
            await create_new_stage_async()
            world = World()
            await world.initialize_simulation_context_async()
            world.scene.add_default_ground_plane()
            usd_path = "http://omniverse-content-production.s3-us-west-2.amazonaws.com/Assets/Isaac/4.5/Isaac/Robots/Unitree/G1/g1.usd"
            add_reference_to_stage(usd_path=usd_path, prim_path="/World/G1")
            while is_stage_loading():
                await asyncio.sleep(0.5)
            robot = Articulation(prim_paths_expr="/World/G1", name="g1")
            world.scene.add(robot)
            await world.reset_async()
            print("=== G1 LOADED ===", flush=True)
            print("num_dof:", robot.num_dof, flush=True)
            carb.log_warn(f"=== G1 LOADED === num_dof: {robot.num_dof}")
        except Exception as e:
            print(f"=== G1 LOAD FAILED: {type(e).__name__}: {e} ===", flush=True)
            import traceback; traceback.print_exc()
            return
        # --- Paso C: confirmar coexistencia (sin publicar) ---
        print("=== G1 + RCLPY COEXIST OK (no publish) ===", flush=True)
        carb.log_warn("=== G1 + RCLPY COEXIST OK (no publish) ===")
        try:
            self._node.destroy_node()
            rclpy.shutdown()
            print("=== RCLPY SHUTDOWN CLEAN ===", flush=True)
        except Exception as e:
            print(f"=== SHUTDOWN WARN: {e} ===", flush=True)
    def on_shutdown(self):
        print("=== EXTENSION SHUTDOWN ===", flush=True)
