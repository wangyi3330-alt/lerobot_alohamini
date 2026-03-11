import argparse
import time
import evdev
from evdev import ecodes

from lerobot.robots.alohamini import LeKiwiClient, LeKiwiClientConfig
from lerobot.teleoperators.keyboard.teleop_keyboard import KeyboardTeleop, KeyboardTeleopConfig
from lerobot.teleoperators.bi_so_leader import BiSOLeader, BiSOLeaderConfig
from lerobot.teleoperators.so_leader import SOLeaderConfig
from lerobot.teleoperators.bi_openarm_leader import BiOpenArmLeader, BiOpenArmLeaderConfig
from lerobot.teleoperators.openarm_leader import OpenArmLeaderConfigBase
from lerobot.utils.robot_utils import precise_sleep
from lerobot.utils.visualization_utils import init_rerun, log_rerun_data

# ============ Parameter Section ============ #
parser = argparse.ArgumentParser()
parser.add_argument("--no_robot", action="store_true", help="Do not connect robot, only print actions")
parser.add_argument("--no_leader", action="store_true", help="Do not connect leader arm, only perform keyboard-controlled actions.")
parser.add_argument("--fps", type=int, default=30, help="Main loop frequency (frames per second)")
parser.add_argument("--remote_ip", type=str, default="127.0.0.1", help="LeKiwi host IP address")
parser.add_argument("--leader_id", type=str, default="so101_leader_bi", help="Leader arm device ID")
parser.add_argument(
    "--arm_profile",
    type=str,
    default="so-arm-5dof",
    choices=["so-arm-5dof", "am-arm-6dof"],
    help="Arm profile selector used for both leader and follower consistency.",
)
parser.add_argument(
    "--leader_type",
    type=str,
    default="feetech",
    choices=["feetech", "damiao"],
    help="Leader arm motor type: 'feetech' (serial, SO-ARM) or 'damiao' (CAN bus).",
)
# Damiao-specific options (only used when --leader_type damiao)
parser.add_argument("--left_can", type=str, default="can0", help="CAN interface for left arm (damiao only)")
parser.add_argument("--right_can", type=str, default="can1", help="CAN interface for right arm (damiao only)")
parser.add_argument("--can_fd", action="store_true", default=False, help="Use CAN FD (damiao only)")
parser.add_argument(
    "--damiao_motor_type",
    type=str,
    default="dm4340",
    choices=["dm4310", "dm4340", "dm8009"],
    help="Damiao motor model (damiao only)",
)

args = parser.parse_args()

# Gamepad setup
gamepad = None
gamepad_mode = 0
try:
    devices = [evdev.InputDevice(path) for path in evdev.list_devices()]
    for d in devices:
        if "magicsee r1" in d.name.lower() and "consumer control" in d.name.lower():
            gamepad = d
            d.set_blocking(False)
            d.grab()
            print(f"✓ Gamepad connected: {d.name}")
            break
except:
    pass

NO_ROBOT = args.no_robot
NO_LEADER = args.no_leader
FPS = args.fps
# ========================================== #

if NO_ROBOT:
    print("🧪 NO_ROBOT mode enabled: robot will not connect, only print actions.")

if NO_LEADER:
    print("🧪 NO_LEADER mode enabled: leader arm will not connect, only print actions.")

# Create configs
robot_config = LeKiwiClientConfig(remote_ip=args.remote_ip, id="my_alohamini")

if args.leader_type == "damiao":
    # Build motor config based on arm_profile
    if args.arm_profile == "am-arm-6dof":
        motor_cfg = {
            "shoulder_pan":  (0x01, 0x11, args.damiao_motor_type),
            "shoulder_lift": (0x02, 0x12, args.damiao_motor_type),
            "elbow_flex":    (0x03, 0x13, args.damiao_motor_type),
            "wrist_flex":    (0x04, 0x14, args.damiao_motor_type),
            "wrist_yaw":     (0x05, 0x15, args.damiao_motor_type),
            "wrist_roll":    (0x06, 0x16, args.damiao_motor_type),
            "gripper":       (0x07, 0x17, args.damiao_motor_type),
        }
    else:  # so-arm-5dof
        motor_cfg = {
            "shoulder_pan":  (0x01, 0x11, args.damiao_motor_type),
            "shoulder_lift": (0x02, 0x12, args.damiao_motor_type),
            "elbow_flex":    (0x03, 0x13, args.damiao_motor_type),
            "wrist_flex":    (0x04, 0x14, args.damiao_motor_type),
            "wrist_roll":    (0x05, 0x15, args.damiao_motor_type),
            "gripper":       (0x06, 0x16, args.damiao_motor_type),
        }
    bi_cfg = BiOpenArmLeaderConfig(
        left_arm_config=OpenArmLeaderConfigBase(
            port=args.left_can,
            use_can_fd=args.can_fd,
            motor_config=motor_cfg,
        ),
        right_arm_config=OpenArmLeaderConfigBase(
            port=args.right_can,
            use_can_fd=args.can_fd,
            motor_config=motor_cfg,
        ),
        id=args.leader_id,
    )
    leader = BiOpenArmLeader(bi_cfg)
    print(f"Leader type: damiao | left={args.left_can} right={args.right_can} motor={args.damiao_motor_type}")
else:
    bi_cfg = BiSOLeaderConfig(
        left_arm_config=SOLeaderConfig(
            port="/dev/am_arm_leader_left",
            arm_profile=args.arm_profile,
        ),
        right_arm_config=SOLeaderConfig(
            port="/dev/am_arm_leader_right",
            arm_profile=args.arm_profile,
        ),
        id=args.leader_id,
    )
    leader = BiSOLeader(bi_cfg)
    print(f"Leader type: feetech | arm_profile={args.arm_profile}")
keyboard_config = KeyboardTeleopConfig(id="my_laptop_keyboard")
keyboard = KeyboardTeleop(keyboard_config)
robot = LeKiwiClient(robot_config)

# Connection logic
if not NO_ROBOT:
    robot.connect()
else:
    print("🧪 robot.connect() skipped, only printing actions.")

if not NO_LEADER:
    leader.connect()
else:
    print("🧪 robot.connect() skipped, only printing actions.")

keyboard.connect()



init_rerun(session_name="lekiwi_teleop")

if not robot.is_connected or not leader.is_connected or not keyboard.is_connected:
    print("⚠️ Warning: Some devices are not connected! Still running for debug.")

# Main loop
while True:
    t0 = time.perf_counter()

    # Read gamepad events and inject into keyboard
    if gamepad:
        try:
            event = gamepad.read_one()
            while event:
                if event.type == ecodes.EV_KEY:
                    if event.code == 164 and event.value == 1:
                        gamepad_mode = 1 - gamepad_mode
                    elif event.value == 1:
                        if gamepad_mode == 0:
                            if event.code == 115: keyboard.event_queue.put(('w', True))
                            elif event.code == 114: keyboard.event_queue.put(('s', True))
                            elif event.code == 165: keyboard.event_queue.put(('a', True))
                            elif event.code == 163: keyboard.event_queue.put(('d', True))
                        else:
                            if event.code == 115: keyboard.event_queue.put(('u', True))
                            elif event.code == 114: keyboard.event_queue.put(('j', True))
                            elif event.code == 165: keyboard.event_queue.put(('a', True))
                            elif event.code == 163: keyboard.event_queue.put(('d', True))
                    elif event.value == 0:
                        if event.code == 115:
                            keyboard.event_queue.put(('w', False))
                            keyboard.event_queue.put(('u', False))
                        elif event.code == 114:
                            keyboard.event_queue.put(('s', False))
                            keyboard.event_queue.put(('j', False))
                        elif event.code == 165: keyboard.event_queue.put(('a', False))
                        elif event.code == 163: keyboard.event_queue.put(('d', False))
                event = gamepad.read_one()
        except:
            pass

    observation = robot.get_observation() if not NO_ROBOT else {}
    arm_actions = leader.get_action() if not NO_LEADER else {}
    arm_actions = {f"arm_{k}": v for k, v in arm_actions.items()}
    keyboard_keys = keyboard.get_action()
    base_action = robot._from_keyboard_to_base_action(keyboard_keys)
    lift_action = robot._from_keyboard_to_lift_action(keyboard_keys)

    action = {**arm_actions, **base_action, **lift_action}
    log_rerun_data(observation, action)

    if not NO_ROBOT:
        robot.send_action(action)

    precise_sleep(max(1.0 / FPS - (time.perf_counter() - t0), 0.0))
    loop_dt = time.perf_counter() - t0
    loop_fps = 1.0 / loop_dt if loop_dt > 0 else float("inf")

    if NO_ROBOT:
        print(f"[fps={loop_fps:.1f}] [NO_ROBOT] action → {action}")
    else:
        print(f"[fps={loop_fps:.1f}] Sent action → {action}")
