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
        # --- rclpy (sin publicar) ---
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
        # --- cargar G1 ---
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
        # --- stepping fisico, rclpy vivo todo el loop ---
        try:
            for i in range(301):
                world.step(render=False)
                if i in [0, 60, 150, 300]:
                    pos, quat = robot.get_world_poses()
                    alive = rclpy.ok()
                    print(f"--- STEP {i} --- rclpy_ok={alive}", flush=True)
                    print(f"  world_position: {pos[0]}", flush=True)
                    print(f"  world_orientation(WXYZ): {quat[0]}", flush=True)
                    carb.log_warn(f"STEP {i} pos={pos[0]} quat={quat[0]} rclpy_ok={alive}")
            print("=== PHYS STEPPING DONE ===", flush=True)
        except Exception as e:
            print(f"=== STEP FAILED: {type(e).__name__}: {e} ===", flush=True)
            import traceback; traceback.print_exc()
            return
        # --- confirmar rclpy sigue vivo y cerrar ---
        try:
            if rclpy.ok():
                print(f"=== RCLPY STILL ALIVE: {self._node.get_name()} ===", flush=True)
                carb.log_warn("=== RCLPY STILL ALIVE ===")
            self._node.destroy_node()
            rclpy.shutdown()
            print("=== RCLPY SHUTDOWN CLEAN ===", flush=True)
        except Exception as e:
            print(f"=== SHUTDOWN WARN: {e} ===", flush=True)
    def on_shutdown(self):
        print("=== EXTENSION SHUTDOWN ===", flush=True)
