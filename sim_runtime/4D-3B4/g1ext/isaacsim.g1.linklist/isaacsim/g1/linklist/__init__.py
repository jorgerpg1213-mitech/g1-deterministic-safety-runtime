import omni.ext, carb, asyncio
class Extension(omni.ext.IExt):
    def on_startup(self, ext_id):
        self._t = asyncio.ensure_future(self._run())
    async def _run(self):
        from isaacsim.core.api import World
        from isaacsim.core.utils.stage import create_new_stage_async, add_reference_to_stage, is_stage_loading
        from isaacsim.core.prims import Articulation
        from pxr import Usd
        import omni.usd
        await create_new_stage_async()
        world = World()
        await world.initialize_simulation_context_async()
        world.scene.add_default_ground_plane()
        add_reference_to_stage(usd_path="http://omniverse-content-production.s3-us-west-2.amazonaws.com/Assets/Isaac/4.5/Isaac/Robots/Unitree/G1/g1.usd", prim_path="/World/G1")
        while is_stage_loading():
            await asyncio.sleep(0.5)
        robot = Articulation(prim_paths_expr="/World/G1", name="g1")
        world.scene.add(robot)
        await world.reset_async()
        print("=== DOF NAMES ===", flush=True)
        print(list(robot.dof_names), flush=True)
        carb.log_warn("DOF: " + str(list(robot.dof_names)))
        print("=== LINK PRIMS (ankle/foot) ===", flush=True)
        st = omni.usd.get_context().get_stage()
        for p in st.Traverse():
            n = p.GetName().lower()
            if "ankle" in n or "foot" in n:
                print(str(p.GetPath()), flush=True)
                carb.log_warn("LINK: " + str(p.GetPath()))
        print("=== LINK LIST DONE ===", flush=True)
    def on_shutdown(self): pass
