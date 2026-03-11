#!/usr/bin/env python3
import pygame
import sys

pygame.init()
pygame.joystick.init()

print(f"找到 {pygame.joystick.get_count()} 个游戏手柄")

if pygame.joystick.get_count() == 0:
    print("未找到手柄，请确保手柄已连接")
    sys.exit(1)

joystick = pygame.joystick.Joystick(0)
joystick.init()

print(f"手柄名称: {joystick.get_name()}")
print(f"按键数: {joystick.get_numbuttons()}")
print(f"摇杆数: {joystick.get_numaxes()}")
print("\n按手柄按键查看输出，按 Ctrl+C 退出\n")

try:
    while True:
        pygame.event.pump()

        for i in range(joystick.get_numbuttons()):
            if joystick.get_button(i):
                print(f"按键 {i} 按下")

        for i in range(joystick.get_numaxes()):
            value = joystick.get_axis(i)
            if abs(value) > 0.1:
                print(f"摇杆轴 {i}: {value:.2f}")

        pygame.time.wait(100)
except KeyboardInterrupt:
    print("\n退出")
