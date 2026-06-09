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
            from geometry_msgs.msg import PoseStamped, TwistStamped
            rclpy.init()
            node = rclpy.create_node("g1_state_node")
            pub_js = node.create_publisher(JointState, "/joint_states", 10)
            pub_pose = node.create_publisher(PoseStamped, "/g1/base_pose", 10)
            pub_vel = node.create_publisher(TwistStamped, "/g1/base_velocity", 10)
            print("=== RCLPY + 3 PUBLISHERS OK ===", flush=True)
            carb.log_warn("=== RCLPY + 3 PUBLISHERS OK ===")
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
            print(f"=== G1 LOADED === num_dof: {robot.num_dof} names: {len(names)}", flush=True)
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
                pos, quat = robot.get_world_poses()
                pos = pos[0]
                quat = quat[0]
                linv = robot.get_linear_velocities()[0]
                angv = robot.get_angular_velocities()[0]
                _t = time.time()
                sec = int(_t)
                nsec = int((_t - int(_t)) * 1e9)

                js = JointState()
                js.header.stamp.sec = sec
                js.header.stamp.nanosec = nsec
                js.header.frame_id = str(count)
                js.name = names
                js.position = [float(x) for x in jp]
                js.velocity = [float(x) for x in jv]
                pub_js.publish(js)

                ps = PoseStamped()
                ps.header.stamp.sec = sec
                ps.header.stamp.nanosec = nsec
                ps.header.frame_id = "world"
                ps.pose.position.x = float(pos[0])
                ps.pose.position.y = float(pos[1])
                ps.pose.position.z = float(pos[2])
                ps.pose.orientation.w = float(quat[0])
                ps.pose.orientation.x = float(quat[1])
                ps.pose.orientation.y = float(quat[2])
                ps.pose.orientation.z = float(quat[3])
                pub_pose.publish(ps)

                tw = TwistStamped()
                tw.header.stamp.sec = sec
                tw.header.stamp.nanosec = nsec
                tw.header.frame_id = "world"
                tw.twist.linear.x = float(linv[0])
                tw.twist.linear.y = float(linv[1])
                tw.twist.linear.z = float(linv[2])
                tw.twist.angular.x = float(angv[0])
                tw.twist.angular.y = float(angv[1])
                tw.twist.angular.z = float(angv[2])
                pub_vel.publish(tw)

                count += 1
                if count % 50 == 0:
                    print(f"=== PUBLISHED {count} (js+pose+vel) z={round(float(pos[2]),4)} ===", flush=True)
                    carb.log_warn(f"PUBLISHED {count} z={round(float(pos[2]),4)}")
                await asyncio.sleep(0.1)
            print(f"=== PUBLISH WINDOW DONE: total {count} msgs x3 topics ===", flush=True)
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
