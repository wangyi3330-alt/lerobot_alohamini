#!/usr/bin/env python3
import evdev

devices = [evdev.InputDevice(path) for path in evdev.list_devices()]

print("MagicSee 设备:")
magicsee_devices = []
for d in devices:
    if "magicsee" in d.name.lower():
        magicsee_devices.append(d)
        print(f"{len(magicsee_devices)-1}: {d.name}")

if not magicsee_devices:
    print("未找到 MagicSee 设备")
    exit(1)

choice = int(input("\n选择设备: "))
gamepad = magicsee_devices[choice]

print(f"\n监听: {gamepad.name}\n")

try:
    for event in gamepad.read_loop():
        print(f"类型:{event.type} 代码:{event.code} 值:{event.value}")
except KeyboardInterrupt:
    print("\n退出")
