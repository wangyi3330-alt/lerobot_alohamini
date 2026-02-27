import argparse
import time
from lerobot.teleoperators.openarm_leader import OpenArmLeader, OpenArmLeaderConfig
from lerobot.teleoperators.keyboard.teleop_keyboard import KeyboardTeleop, KeyboardTeleopConfig
from lerobot.robots.alohamini import LeKiwiClient, LeKiwiClientConfig
from lerobot.utils.robot_utils import precise_sleep


def build_motor_cfg(arm_profile: str, motor_type: str) -> dict[str, tuple[int, int, str]]:
    if arm_profile == "am-arm-6dof":
        return {
            "shoulder_pan":  (0x01, 0x11, motor_type),
            "shoulder_lift": (0x02, 0x12, motor_type),
            "elbow_flex":    (0x03, 0x13, motor_type),
            "wrist_flex":    (0x04, 0x14, motor_type),
            "wrist_yaw":     (0x05, 0x15, motor_type),
            "wrist_roll":    (0x06, 0x16, motor_type),
            "gripper":       (0x07, 0x17, motor_type),
        }
    return {
        "shoulder_pan":  (0x01, 0x11, motor_type),
        "shoulder_lift": (0x02, 0x12, motor_type),
        "elbow_flex":    (0x03, 0x13, motor_type),
        "wrist_flex":    (0x04, 0x14, motor_type),
        "wrist_roll":    (0x05, 0x15, motor_type),
        "gripper":       (0x06, 0x16, motor_type),
    }


def parse_args():
    p = argparse.ArgumentParser("Single-arm teleop client (send left/right arm over ZMQ)")
    p.add_argument("--remote_ip", type=str, default="127.0.0.1")
    p.add_argument("--side", type=str, default="left", choices=["left", "right"])
    p.add_argument("--port", type=str, default="can0")
    p.add_argument("--can_fd", action="store_true", default=False)
    p.add_argument("--can_bitrate", type=int, default=1_000_000)
    p.add_argument("--can_data_bitrate", type=int, default=5_000_000)
    p.add_argument("--arm_profile", type=str, default="so-arm-5dof", choices=["so-arm-5dof", "am-arm-6dof"]) 
    p.add_argument("--damiao_motor_type", type=str, default="dm4340", choices=["dm4310", "dm4340", "dm8009"]) 
    p.add_argument("--enable_torque", action="store_true")
    p.add_argument("--no_calib", action="store_true")
    p.add_argument("--fps", type=int, default=30)
    return p.parse_args()


def main():
    args = parse_args()

    # 1) 连接 Host（树莓派）
    robot_cfg = LeKiwiClientConfig(remote_ip=args.remote_ip, id="alohamini_single_client")
    robot = LeKiwiClient(robot_cfg)
    robot.connect()

    # 2) 连接主臂（OpenArm 左/右）
    motor_cfg = build_motor_cfg(args.arm_profile, args.damiao_motor_type)
    manual = not args.enable_torque
    leader_cfg = OpenArmLeaderConfig(
        id=f"openarm_{args.side}",
        port=args.port,
        can_interface="socketcan",
        use_can_fd=args.can_fd,
        can_bitrate=args.can_bitrate,
        can_data_bitrate=args.can_data_bitrate,
        motor_config=motor_cfg,
        manual_control=manual,
    )
    leader = OpenArmLeader(leader_cfg)
    leader.connect(calibrate=not args.no_calib)
    if args.enable_torque:
        try:
            leader.bus.enable_torque()
            print("✓ 主臂已上扭矩（注意安全）")
        except Exception as e:
            print(f"✗ 上扭矩失败：{e}")

    # 3) 键盘（底盘/升降）
    kb = KeyboardTeleop(KeyboardTeleopConfig(id="teleop_keyboard"))
    kb.connect()

    print(f"连接完成：Host@{args.remote_ip} | side={args.side} | port={args.port} | can_fd={args.can_fd}")
    prefix = f"arm_{args.side}_"

    try:
        while True:
            t0 = time.perf_counter()

            # 读取主臂动作（关节 pos/vel/torque）
            arm_action = leader.get_action()           # e.g. "shoulder_pan.pos": v
            arm_action = {f"{prefix}{k}": v for k, v in arm_action.items()}

            # 键盘 → 底盘/升降
            keys = kb.get_action()
            base = robot._from_keyboard_to_base_action(keys)
            lift = robot._from_keyboard_to_lift_action(keys)

            # 合并并发送
            action = {**arm_action, **base, **lift}
            robot.send_action(action)

            precise_sleep(max(1.0 / args.fps - (time.perf_counter() - t0), 0.0))
    except KeyboardInterrupt:
        pass
    finally:
        try:
            leader.disconnect()
        except Exception:
            pass
        try:
            kb.disconnect()
        except Exception:
            pass
        try:
            robot.disconnect()
        except Exception:
            pass
        print("✓ 已断开")


if __name__ == "__main__":
    main()
