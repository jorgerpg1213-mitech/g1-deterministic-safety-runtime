import omni.ext
import carb
import sys
import asyncio
import time


class Extension(omni.ext.IExt):
    def on_startup(self, ext_id):
        print("=== STARTUP EXTENSION OK ===", flush=True)
        carb.log_warn("=== STARTUP EXTENSION OK ===")
        self._task = asyncio.ensure_future(self._run_async())

    async def _run_async(self):
        try:
            sys.path.append("/isaac-sim/exts/isaacsim.ros2.bridge/humble/rclpy")
            import rclpy
            from sensor_msgs.msg import JointState
            rclpy.init()
            node = rclpy.create_node("g1_bridge_node")
            pub = node.create_publisher(JointState, "/joint_states", 10)
            print("=== RCLPY + PUBLISHER OK: /joint_states ===", flush=True)
            carb.log_warn("=== RCLPY + PUBLISHER OK ===")
        except Exception as e:
            print(f"=== RCLPY/PUB FAILED: {type(e).__name__}: {e} ===", flush=True)
            import traceback
            traceback.print_exc()
            return
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
            names = list(robot.dof_names)
            print(f"=== G1 LOADED === num_dof: {robot.num_dof} dof_names_len: {len(names)}", flush=True)
            carb.log_warn(f"=== G1 LOADED === num_dof: {robot.num_dof} names: {len(names)}")
        except Exception as e:
            print(f"=== G1 LOAD FAILED: {type(e).__name__}: {e} ===", flush=True)
            import traceback
            traceback.print_exc()
            return
        try:
            for i in range(151):
                world.step(render=False)
            print("=== G1 AT REST (150 steps) ===", flush=True)
        except Exception as e:
            print(f"=== STEP FAILED: {type(e).__name__}: {e} ===", flush=True)
            return
        try:
            count = 0
            t_end = time.time() + 180.0
            while rclpy.ok() and time.time() < t_end:
                world.step(render=False)
                jp = robot.get_joint_positions()[0]
                jv = robot.get_joint_velocities()[0]
                msg = JointState()
                _t = time.time()
                msg.header.stamp.sec = int(_t)
                msg.header.stamp.nanosec = int((_t - int(_t)) * 1e9)
                msg.header.frame_id = str(count)
                msg.name = names
                msg.position = [float(x) for x in jp]
                msg.velocity = [float(x) for x in jv]
                pub.publish(msg)
                count += 1
                if count % 50 == 0:
                    print(f"=== PUBLISHED {count} msgs (name={len(msg.name)} pos={len(msg.position)} vel={len(msg.velocity)}) ===", flush=True)
                    carb.log_warn(f"PUBLISHED {count} msgs")
                await asyncio.sleep(0.1)
            print(f"=== PUBLISH WINDOW DONE: total {count} msgs ===", flush=True)
            carb.log_warn(f"=== PUBLISH WINDOW DONE: {count} msgs ===")
            node.destroy_node()
            rclpy.shutdown()
            print("=== RCLPY SHUTDOWN CLEAN ===", flush=True)
        except Exception as e:
            print(f"=== PUBLISH FAILED: {type(e).__name__}: {e} ===", flush=True)
            import traceback
            traceback.print_exc()

    def on_shutdown(self):
        print("=== EXTENSION SHUTDOWN ===", flush=True)
