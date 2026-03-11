#!/usr/bin/env python3
import evdev
import sys
from evdev import UInput, ecodes

# 查找 MagicSee R1
devices = [evdev.InputDevice(path) for path in evdev.list_devices()]
gamepad = None

for d in devices:
    if "magicsee r1" in d.name.lower() and "consumer control" in d.name.lower():
        gamepad = d
        break

if not gamepad:
    print("未找到 MagicSee R1 Consumer Control")
    sys.exit(1)

print(f"找到: {gamepad.name}")

# 按键映射
key_map = {
    115: ecodes.KEY_W,
    114: ecodes.KEY_S,
    165: ecodes.KEY_A,
    163: ecodes.KEY_D,
    164: ecodes.KEY_U,
}

# 创建虚拟键盘
ui = UInput()

print("按键映射已启动\n")

try:
    for event in gamepad.read_loop():
        if event.type == ecodes.EV_KEY and event.code in key_map:
            ui.write(ecodes.EV_KEY, key_map[event.code], event.value)
            ui.syn()
            print(f"{event.code} -> {chr(key_map[event.code] - ecodes.KEY_A + ord('a')).upper()}")
except KeyboardInterrupt:
    print("\n退出")
finally:
    ui.close()
