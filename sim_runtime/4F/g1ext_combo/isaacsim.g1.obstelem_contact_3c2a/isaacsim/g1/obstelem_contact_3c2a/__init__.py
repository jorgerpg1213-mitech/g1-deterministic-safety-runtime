import omni.ext, carb, sys, asyncio, time
G1MSGS = "/g1msgs/local/lib/python3.10/dist-packages"
RCLPY = "/isaac-sim/exts/isaacsim.ros2.bridge/humble/rclpy"
class Extension(omni.ext.IExt):
    def on_startup(self, ext_id):
        print("=== OBSTELEM_CONTACT_3C2A STARTUP OK ===", flush=True)
        self._task = asyncio.ensure_future(self._run_async())
    async def _run_async(self):
        try:
            for p in (RCLPY, G1MSGS):
                if p not in sys.path: sys.path.append(p)
            import rclpy
            from sensor_msgs.msg import JointState, Imu
            from geometry_msgs.msg import PoseStamped, TwistStamped
            from g1_msgs.msg import FootContact
            from std_msgs.msg import String as StringMsg
            rclpy.init() if not rclpy.ok() else None
            node = rclpy.create_node("g1_obstelem_contact_node")
            pub_marker = node.create_publisher(StringMsg, "/g1/fall_marker", 10)
            pub_js = node.create_publisher(JointState, "/joint_states", 10)
            pub_pose = node.create_publisher(PoseStamped, "/g1/base_pose", 10)
            pub_vel = node.create_publisher(TwistStamped, "/g1/base_velocity", 10)
            pub_imu = node.create_publisher(Imu, "/g1/imu", 10)
            pub_cl = node.create_publisher(FootContact, "/g1/contact/left", 10)
            pub_cr = node.create_publisher(FootContact, "/g1/contact/right", 10)
            print("=== RCLPY + 6 PUBLISHERS OK ===", flush=True)
        except Exception as e:
            print(f"=== RCLPY/PUB FAILED: {type(e).__name__}: {e} ===", flush=True)
            import traceback; traceback.print_exc(); return
        try:
            from isaacsim.core.api import World
            from isaacsim.core.utils.stage import create_new_stage_async, add_reference_to_stage, is_stage_loading
            from isaacsim.core.prims import Articulation
            from isaacsim.sensors.physics import IMUSensor, ContactSensor
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
            imu = IMUSensor(prim_path="/World/G1/torso_link/imu_sensor", name="g1_imu", frequency=60, translation=[0,0,0])
            cl = ContactSensor(prim_path="/World/G1/left_ankle_roll_link/contact_left", name="contact_left", frequency=60, translation=[0,0,0])
            cr = ContactSensor(prim_path="/World/G1/right_ankle_roll_link/contact_right", name="contact_right", frequency=60, translation=[0,0,0])
            await world.reset_async()
            imu.initialize()
            cl.initialize()
            cr.initialize()
            names = list(robot.dof_names)
            print(f"=== G1 + IMU + CONTACTS READY === num_dof: {robot.num_dof}", flush=True)
        except Exception as e:
            print(f"=== G1/SENSORS LOAD FAILED: {type(e).__name__}: {e} ===", flush=True)
            import traceback; traceback.print_exc(); return
        await self._publish(world, robot, node, names, pub_js, pub_pose, pub_vel, pub_imu, imu, cl, cr, pub_cl, pub_cr, rclpy)
    def on_shutdown(self):
        print("=== OBSTELEM_CONTACT_3C2A SHUTDOWN ===", flush=True)
    async def _publish(self, world, robot, node, names, pub_js, pub_pose, pub_vel, pub_imu, imu, cl, cr, pub_cl, pub_cr, rclpy):
        from sensor_msgs.msg import JointState, Imu
        from geometry_msgs.msg import PoseStamped, TwistStamped
        from g1_msgs.msg import FootContact
        import numpy as _np
        _ji = {n: i for i, n in enumerate(names)}
        # 4F-P1: baseline sano P2 + z=0.720 antes de warm-up
        _pose = _np.zeros((1, robot.num_dof), dtype=_np.float32)
        for _jn, _v in [("left_hip_pitch_joint", -0.1), ("right_hip_pitch_joint", -0.1),
                        ("left_knee_joint", 0.3), ("right_knee_joint", 0.3),
                        ("left_ankle_pitch_joint", -0.2), ("right_ankle_pitch_joint", -0.2)]:
            _pose[0, _ji[_jn]] = _v
        robot.set_world_poses(positions=_np.array([[0.0, 0.0, 0.720]], dtype=_np.float32),
                              orientations=_np.array([[1.0, 0.0, 0.0, 0.0]], dtype=_np.float32))
        robot.set_joint_positions(_pose)
        print("=== 4F-P1: P2+z0.720 SET ===", flush=True)
        try:
            for i in range(10):
                world.step(render=False)
            print("=== G1 AT REST (10 steps warm-up) ===", flush=True)
        except Exception as e:
            print(f"=== STEP FAILED: {type(e).__name__}: {e} ===", flush=True); return
        _fell = False
        try:
            count = 0
            t_end = time.time() + 180.0
            while rclpy.ok() and time.time() < t_end:
                # 4F-P1: estimulo de caida en it=450
                if count == 450 and not _fell:
                    import time as _tm, json as _json
                    from std_msgs.msg import String as StringMsg
                    _t0_ns = _tm.monotonic_ns()
                    _marker = _json.dumps({"schema": "g1_fall_marker_v1", "iteration": 450, "host_time_ns": _t0_ns, "reason": "FALL_TRIGGER"})
                    print(f"=== 4F-P1 FALL TRIGGER it=450 t0_wall={_tm.time():.6f} t0_ns={_t0_ns} ===", flush=True)
                    print(f"=== G1_FALL_MARKER {_marker} ===", flush=True)
                    # P3-B: marker por log, no por ROS topic; evita scope/pub_marker en Isaac
                    # _sm = StringMsg(); _sm.data = _marker; pub_marker.publish(_sm)
                    robot.set_world_poses(
                        positions=_np.array([[0.0, 0.0, 1.10]], dtype=_np.float32),
                        orientations=_np.array([[0.9238795, 0.3826834, 0.0, 0.0]], dtype=_np.float32))
                    robot.set_velocities(_np.zeros((1, 6), dtype=_np.float32))
                    robot.set_joint_velocities(_np.zeros((1, robot.num_dof), dtype=_np.float32))
                    _fell = True
                world.step(render=False)
                jp = robot.get_joint_positions()[0]; jv = robot.get_joint_velocities()[0]
                pos, quat = robot.get_world_poses(); pos = pos[0]; quat = quat[0]
                linv = robot.get_linear_velocities()[0]; angv = robot.get_angular_velocities()[0]
                imuf = imu.get_current_frame()
                lf = cl.get_current_frame(); rf = cr.get_current_frame()
                _t = time.time(); sec = int(_t); nsec = int((_t-int(_t))*1e9)
                js = JointState(); js.header.stamp.sec=sec; js.header.stamp.nanosec=nsec; js.header.frame_id=str(count)
                js.name=names; js.position=[float(x) for x in jp]; js.velocity=[float(x) for x in jv]; pub_js.publish(js)
                ps = PoseStamped(); ps.header.stamp.sec=sec; ps.header.stamp.nanosec=nsec; ps.header.frame_id="world"
                ps.pose.position.x=float(pos[0]); ps.pose.position.y=float(pos[1]); ps.pose.position.z=float(pos[2])
                ps.pose.orientation.w=float(quat[0]); ps.pose.orientation.x=float(quat[1]); ps.pose.orientation.y=float(quat[2]); ps.pose.orientation.z=float(quat[3]); pub_pose.publish(ps)
                tw = TwistStamped(); tw.header.stamp.sec=sec; tw.header.stamp.nanosec=nsec; tw.header.frame_id="world"
                tw.twist.linear.x=float(linv[0]); tw.twist.linear.y=float(linv[1]); tw.twist.linear.z=float(linv[2])
                tw.twist.angular.x=float(angv[0]); tw.twist.angular.y=float(angv[1]); tw.twist.angular.z=float(angv[2]); pub_vel.publish(tw)
                imsg = Imu(); imsg.header.stamp.sec=sec; imsg.header.stamp.nanosec=nsec; imsg.header.frame_id="torso_link"
                ori = imuf["orientation"]; la = imuf["lin_acc"]; av = imuf["ang_vel"]
                imsg.orientation.w=float(ori[0]); imsg.orientation.x=float(ori[1]); imsg.orientation.y=float(ori[2]); imsg.orientation.z=float(ori[3])
                imsg.linear_acceleration.x=float(la[0]); imsg.linear_acceleration.y=float(la[1]); imsg.linear_acceleration.z=float(la[2])
                imsg.angular_velocity.x=float(av[0]); imsg.angular_velocity.y=float(av[1]); imsg.angular_velocity.z=float(av[2]); pub_imu.publish(imsg)
                cml = FootContact(); cml.header.stamp.sec=sec; cml.header.stamp.nanosec=nsec; cml.header.frame_id="left_ankle_roll_link"
                cml.in_contact=bool(lf["in_contact"]); cml.force=float(lf["force"]); cml.number_of_contacts=int(lf["number_of_contacts"]); pub_cl.publish(cml)
                cmr = FootContact(); cmr.header.stamp.sec=sec; cmr.header.stamp.nanosec=nsec; cmr.header.frame_id="right_ankle_roll_link"
                cmr.in_contact=bool(rf["in_contact"]); cmr.force=float(rf["force"]); cmr.number_of_contacts=int(rf["number_of_contacts"]); pub_cr.publish(cmr)
                count += 1
                if count % 50 == 0:
                    print(f"=== PUBLISHED {count} (js+pose+vel+imu+contactLR) z={round(float(pos[2]),4)} W={round(float(ori[0]),3)} L={lf['in_contact']} R={rf['in_contact']} ===", flush=True)
                await asyncio.sleep(0.1)
            print(f"=== PUBLISH WINDOW DONE: total {count} x6 topics ===", flush=True)
            node.destroy_node()
            if rclpy.ok(): rclpy.shutdown()
            print("=== RCLPY SHUTDOWN CLEAN ===", flush=True)
        except Exception as e:
            print(f"=== PUBLISH FAILED: {type(e).__name__}: {e} ===", flush=True)
            import traceback; traceback.print_exc()
