import argparse
from lerobot.teleoperators.openarm_leader import OpenArmLeader, OpenArmLeaderConfig
from lerobot.utils.robot_utils import precise_sleep


def build_motor_cfg(arm_profile: str, motor_type: str) -> dict[str, tuple[int, int, str]]:
    """Return a motor configuration dict for a single OpenArm,
    matching the IDs used in the bimanual example.
    """
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
    # so-arm-5dof
    return {
        "shoulder_pan":  (0x01, 0x11, motor_type),
        "shoulder_lift": (0x02, 0x12, motor_type),
        "elbow_flex":    (0x03, 0x13, motor_type),
        "wrist_flex":    (0x04, 0x14, motor_type),
        "wrist_roll":    (0x05, 0x15, motor_type),
        "gripper":       (0x06, 0x16, motor_type),
    }


def parse_args():
    p = argparse.ArgumentParser("Single-arm OpenArm reader over CAN (no Host)")
    p.add_argument("--port", type=str, default="can0", help="CAN 接口名")
    p.add_argument("--can_fd", action="store_true", default=False, help="启用 CAN FD 模式")
    p.add_argument("--can_bitrate", type=int, default=1_000_000, help="经典 CAN 速率")
    p.add_argument("--can_data_bitrate", type=int, default=5_000_000, help="CAN FD 数据速率")
    p.add_argument("--arm_profile", type=str, default="so-arm-5dof", choices=["so-arm-5dof", "am-arm-6dof"], help="臂型")
    p.add_argument("--damiao_motor_type", type=str, default="dm4340", choices=["dm4310", "dm4340", "dm8009"], help="电机型号")
    p.add_argument("--fps", type=int, default=30, help="读取频率")
    p.add_argument("--enable_torque", action="store_true", help="连接后使能力矩（小心关节瞬间受力）")
    p.add_argument("--no_calib", action="store_true", help="跳过校准流程")
    return p.parse_args()


def main():
    args = parse_args()
    motor_cfg = build_motor_cfg(args.arm_profile, args.damiao_motor_type)

    # 需要扭矩 → manual_control 设为 False；仅读数 → True
    manual = not args.enable_torque

    cfg = OpenArmLeaderConfig(
        id="openarm_single",
        port=args.port,
        can_interface="socketcan",
        use_can_fd=args.can_fd,
        can_bitrate=args.can_bitrate,
        can_data_bitrate=args.can_data_bitrate,
        motor_config=motor_cfg,
        manual_control=manual,
    )

    arm = OpenArmLeader(cfg)
    print(f"连接单臂：port={args.port} can_fd={args.can_fd} profile={args.arm_profile} motor={args.damiao_motor_type}")

    arm.connect(calibrate=not args.no_calib)

    # 可选：再次显式使能力矩（有些配置下能避免红灯）
    if args.enable_torque:
        try:
            arm.bus.enable_torque()
            print("✓ 已使能力矩（注意安全）")
        except Exception as e:
            print(f"✗ 使能力矩失败：{e}")

    state = "手动模式(力矩关闭)" if manual else "力矩开启"
    print(f"✓ 已连接，当前：{state}。Ctrl+C 退出。")

    try:
        while True:
            action = arm.get_action()
            compact = {k: v for k, v in action.items() if k.endswith(".pos")}
            print(compact)
            precise_sleep(1.0 / args.fps)
    except KeyboardInterrupt:
        pass
    finally:
        arm.disconnect()
        print("✓ 已断开")


if __name__ == "__main__":
    main()
