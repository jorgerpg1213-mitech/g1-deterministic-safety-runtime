import omni.ext, carb, asyncio, sys, time
class Extension(omni.ext.IExt):
    def on_startup(self, ext_id):
        print("=== STARTUP EXTENSION OK ===", flush=True)
        carb.log_warn("=== STARTUP EXTENSION OK ===")
        self._t = asyncio.ensure_future(self._run())
    async def _run(self):
        try:
            sys.path.append("/isaac-sim/exts/isaacsim.ros2.bridge/humble/rclpy")
            import rclpy
            from sensor_msgs.msg import Imu
            from std_msgs.msg import Float32MultiArray
            rclpy.init()
            self.node = rclpy.create_node("g1_live_node")
            self.pub_imu = self.node.create_publisher(Imu, "/g1/imu", 10)
            self.pub_feet = self.node.create_publisher(Float32MultiArray, "/g1/feet", 10)
            self.Imu = Imu
            self.Float32MultiArray = Float32MultiArray
            print("=== RCLPY + PUBLISHERS OK (imu+feet) ===", flush=True)
            carb.log_warn("=== RCLPY + PUBLISHERS OK ===")
        except Exception as e:
            print(f"=== RCLPY FAILED: {type(e).__name__}: {e} ===", flush=True)
            import traceback; traceback.print_exc(); return
        await self._load()
    async def _load(self):
        try:
            from isaacsim.core.api import World
            from isaacsim.core.utils.stage import create_new_stage_async, add_reference_to_stage, is_stage_loading
            from isaacsim.core.prims import Articulation
            from isaacsim.sensors.physics import IMUSensor, ContactSensor
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
            self.imu = IMUSensor(prim_path="/World/G1/torso_link/imu_sensor", name="g1_imu", frequency=60, translation=[0,0,0])
            self.cl = ContactSensor(prim_path="/World/G1/left_ankle_roll_link/contact_left", name="cl", frequency=60, translation=[0,0,0])
            self.cr = ContactSensor(prim_path="/World/G1/right_ankle_roll_link/contact_right", name="cr", frequency=60, translation=[0,0,0])
            await world.reset_async()
            self.imu.initialize(); self.cl.initialize(); self.cr.initialize()
            print("=== G1 + SENSORS READY ===", flush=True)
            carb.log_warn("=== G1 + SENSORS READY ===")
        except Exception as e:
            print(f"=== LOAD FAILED: {type(e).__name__}: {e} ===", flush=True)
            import traceback; traceback.print_exc(); return
        await self._loop()
    async def _loop(self):
        import rclpy
        try:
            count = 0
            t_end = time.time() + 120.0
            while rclpy.ok() and time.time() < t_end:
                self.world.step(render=False)
                imuf = self.imu.get_current_frame()
                lf = self.cl.get_current_frame()
                rf = self.cr.get_current_frame()
                ori = [float(x) for x in imuf["orientation"]]
                av = [float(x) for x in imuf["ang_vel"]]
                la = [float(x) for x in imuf["lin_acc"]]

                m = self.Imu()
                m.header.frame_id = str(count)
                _t = time.time()
                m.header.stamp.sec = int(_t); m.header.stamp.nanosec = int((_t-int(_t))*1e9)
                m.orientation.w = ori[0]; m.orientation.x = ori[1]; m.orientation.y = ori[2]; m.orientation.z = ori[3]
                m.angular_velocity.x = av[0]; m.angular_velocity.y = av[1]; m.angular_velocity.z = av[2]
                m.linear_acceleration.x = la[0]; m.linear_acceleration.y = la[1]; m.linear_acceleration.z = la[2]
                self.pub_imu.publish(m)

                fa = self.Float32MultiArray()
                fa.data = [float(count), 1.0 if lf["in_contact"] else 0.0, float(lf["force"]), 1.0 if rf["in_contact"] else 0.0, float(rf["force"])]
                self.pub_feet.publish(fa)

                count += 1
                if count % 50 == 0:
                    print(f"=== PUBLISHED {count} W={round(ori[0],3)} L={lf['in_contact']} R={rf['in_contact']} ===", flush=True)
                    carb.log_warn(f"PUBLISHED {count} W={round(ori[0],3)}")
                await asyncio.sleep(0.05)
            print(f"=== PUBLISH DONE: {count} msgs ===", flush=True)
            carb.log_warn(f"=== PUBLISH DONE: {count} ===")
            self.node.destroy_node(); rclpy.shutdown()
            print("=== RCLPY SHUTDOWN CLEAN ===", flush=True)
        except Exception as e:
            print(f"=== LOOP FAILED: {type(e).__name__}: {e} ===", flush=True)
            import traceback; traceback.print_exc()
    def on_shutdown(self):
        print("=== EXTENSION SHUTDOWN ===", flush=True)
