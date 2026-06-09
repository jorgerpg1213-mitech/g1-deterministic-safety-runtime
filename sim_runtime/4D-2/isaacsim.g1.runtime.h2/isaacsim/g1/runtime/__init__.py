import omni.ext
import carb
import asyncio


class Extension(omni.ext.IExt):
    def on_startup(self, ext_id):
        print("=== STARTUP EXTENSION OK ===", flush=True)
        carb.log_warn("=== STARTUP EXTENSION OK ===")
        self._task = asyncio.ensure_future(self._run_async())

    async def _run_async(self):
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
            import traceback
            traceback.print_exc()
            return

        try:
            for i in range(601):
                world.step(render=False)
                if i in [0, 60, 150, 300, 450, 600]:
                    jp = robot.get_joint_positions()
                    jv = robot.get_joint_velocities()
                    pos, quat = robot.get_world_poses()
                    print(f"--- STEP {i} ---", flush=True)
                    print(f"  world_position: {pos[0]}", flush=True)
                    print(f"  world_orientation(WXYZ): {quat[0]}", flush=True)
                    print(f"  joint_pos[:3]: {jp[0][:3]}", flush=True)
                    print(f"  joint_vel[:3]: {jv[0][:3]}", flush=True)
                    carb.log_warn(f"STEP {i} pos={pos[0]} quat={quat[0]}")
            print("=== PHYS STEPPING DONE ===", flush=True)
            carb.log_warn("=== PHYS STEPPING DONE ===")

        except Exception as e:
            print(f"=== G1 STEP FAILED: {type(e).__name__}: {e} ===", flush=True)
            import traceback
            traceback.print_exc()

    def on_shutdown(self):
        print("=== EXTENSION SHUTDOWN ===", flush=True)
