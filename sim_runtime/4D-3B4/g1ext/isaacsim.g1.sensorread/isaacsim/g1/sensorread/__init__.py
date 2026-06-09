import omni.ext, carb, asyncio
class Extension(omni.ext.IExt):
    def on_startup(self, ext_id):
        print("=== STARTUP EXTENSION OK ===", flush=True)
        carb.log_warn("=== STARTUP EXTENSION OK ===")
        self._t = asyncio.ensure_future(self._run())
    async def _run(self):
        try:
            from isaacsim.core.api import World
            from isaacsim.core.utils.stage import create_new_stage_async, add_reference_to_stage, is_stage_loading
            from isaacsim.core.prims import Articulation
            from isaacsim.sensors.physics import IMUSensor, ContactSensor
            self.IMUSensor = IMUSensor
            self.ContactSensor = ContactSensor
            await create_new_stage_async()
            world = World()
            await world.initialize_simulation_context_async()
            world.scene.add_default_ground_plane()
            add_reference_to_stage(usd_path="http://omniverse-content-production.s3-us-west-2.amazonaws.com/Assets/Isaac/4.5/Isaac/Robots/Unitree/G1/g1.usd", prim_path="/World/G1")
            while is_stage_loading():
                await asyncio.sleep(0.5)
            self.robot = Articulation(prim_paths_expr="/World/G1", name="g1")
            world.scene.add(self.robot)
            self.world = world
            print("=== G1 LOADED ===", flush=True)
        except Exception as e:
            print(f"=== G1 LOAD FAILED: {type(e).__name__}: {e} ===", flush=True)
            import traceback; traceback.print_exc(); return
        await self._setup_sensors()
    async def _setup_sensors(self):
        try:
            self.imu = self.IMUSensor(
                prim_path="/World/G1/torso_link/imu_sensor",
                name="g1_imu",
                frequency=60,
                translation=[0, 0, 0],
            )
            print("=== IMU CREATED ===", flush=True)
            carb.log_warn("=== IMU CREATED ===")
        except Exception as e:
            print(f"=== IMU FAILED: {type(e).__name__}: {e} ===", flush=True)
            import traceback; traceback.print_exc()
        try:
            self.cl = self.ContactSensor(
                prim_path="/World/G1/left_ankle_roll_link/contact_left",
                name="contact_left",
                frequency=60,
                translation=[0, 0, 0],
            )
            self.cr = self.ContactSensor(
                prim_path="/World/G1/right_ankle_roll_link/contact_right",
                name="contact_right",
                frequency=60,
                translation=[0, 0, 0],
            )
            print("=== CONTACT SENSORS CREATED (L+R) ===", flush=True)
            carb.log_warn("=== CONTACT SENSORS CREATED ===")
        except Exception as e:
            print(f"=== CONTACT FAILED: {type(e).__name__}: {e} ===", flush=True)
            import traceback; traceback.print_exc()
        try:
            await self.world.reset_async()
            self.imu.initialize()
            self.cl.initialize()
            self.cr.initialize()
            print("=== SENSORS INITIALIZED ===", flush=True)
            carb.log_warn("=== SENSORS INITIALIZED ===")
        except Exception as e:
            print(f"=== SENSOR INIT FAILED: {type(e).__name__}: {e} ===", flush=True)
            import traceback; traceback.print_exc(); return
        await self._loop()
    async def _loop(self):
        try:
            for i in range(301):
                self.world.step(render=False)
                if i in [0, 60, 150, 300]:
                    imuf = self.imu.get_current_frame()
                    lf = self.cl.get_current_frame()
                    rf = self.cr.get_current_frame()
                    la = [round(float(x), 3) for x in imuf["lin_acc"]]
                    av = [round(float(x), 3) for x in imuf["ang_vel"]]
                    ori = [round(float(x), 3) for x in imuf["orientation"]]
                    print(f"--- STEP {i} ---", flush=True)
                    print(f"  IMU lin_acc={la} ang_vel={av} ori(wxyz)={ori}", flush=True)
                    print(f"  FOOT_L in_contact={lf['in_contact']} force={round(lf['force'],2)}", flush=True)
                    print(f"  FOOT_R in_contact={rf['in_contact']} force={round(rf['force'],2)}", flush=True)
                    carb.log_warn(f"STEP {i} IMU ori={ori} L={lf['in_contact']}/{round(lf['force'],1)} R={rf['in_contact']}/{round(rf['force'],1)}")
            print("=== SENSOR READ DONE ===", flush=True)
            carb.log_warn("=== SENSOR READ DONE ===")
        except Exception as e:
            print(f"=== LOOP FAILED: {type(e).__name__}: {e} ===", flush=True)
            import traceback; traceback.print_exc()
    def on_shutdown(self):
        print("=== EXTENSION SHUTDOWN ===", flush=True)
