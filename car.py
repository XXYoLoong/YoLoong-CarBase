#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
car.py — 四轮差速小车控制系统（手柄 + GUI 二合一）
核心功能：
  - 图形化 GUI 控制摇杆，支持鼠标拖拽
  - USB 手柄左摇杆控制底盘，按键切换模式
  - 驱动模式：标准四驱、智能节能（根据方向自动选择轮子）
  - 模块化结构设计，方便扩展、维护与平台适配
"""

import tkinter as tk
import pygame
from gpiozero import DigitalOutputDevice
import math

# ========== 电机驱动模块 ==========
class MotorPair:
    """封装一对电机（正/反），用于控制一轮"""
    def __init__(self, fwd_pin, rev_pin, name=''):
        self.fwd = DigitalOutputDevice(fwd_pin)
        self.rev = DigitalOutputDevice(rev_pin)
        self.name = name

    def stop(self):
        """关闭当前轮"""
        self.fwd.off()
        self.rev.off()

    def set(self, value: float):
        """设定速度值（-1.0~1.0），正转或反转"""
        self.stop()
        if value > 0.1:
            self.fwd.on()
        elif value < -0.1:
            self.rev.on()

# ========== 底盘控制模块 ==========
class Chassis:
    """底盘控制类，管理四轮驱动逻辑与节能模式切换"""
    def __init__(self):
        self.mode_4wd = True  # 默认为标准四驱
        self.motors = {
            'FL': MotorPair(13, 19, 'FL'),
            'FR': MotorPair(6, 5, 'FR'),
            'RL': MotorPair(26, 16, 'RL'),
            'RR': MotorPair(12, 20, 'RR')
        }

    def stop_all(self):
        """停止所有电机"""
        for m in self.motors.values():
            m.stop()

    def drive(self, v_l: float, v_r: float):
        """主驱动入口，根据模式决定具体驱动方式"""
        if self.mode_4wd:
            self._drive_standard(v_l, v_r)
        else:
            self._drive_smart_eco(v_l, v_r)

    def _drive_standard(self, v_l, v_r):
        """标准四轮差速控制（后轮方向需补偿）"""
        self.stop_all()
        self.motors['FL'].set(v_l)
        self.motors['RL'].set(-v_l)
        self.motors['FR'].set(v_r)
        self.motors['RR'].set(-v_r)

    def _drive_smart_eco(self, v_l, v_r):
        """智能节能驱动模式，根据方向动态选择对角轮或侧轮"""
        self.stop_all()
        forward_component = (v_l + v_r) / 2
        turn_component = (v_l - v_r) / 2

        if abs(forward_component) > abs(turn_component):
            if forward_component > 0:
                # 前进：用后轮推
                self.motors['RL'].set(-v_l)
                self.motors['RR'].set(-v_r)
            elif forward_component < 0:
                # 后退：用前轮推
                self.motors['FL'].set(v_l)
                self.motors['FR'].set(v_r)
        else:
            if turn_component > 0:
                # 向右：使用左侧轮
                self.motors['FL'].set(v_l)
                self.motors['RL'].set(-v_l)
            elif turn_component < 0:
                # 向左：使用右侧轮
                self.motors['FR'].set(v_r)
                self.motors['RR'].set(-v_r)

    def set_mode(self, mode):
        """切换驱动模式"""
        self.mode_4wd = mode

# ========== 主程序 GUI + 手柄 ==========
class CarApp:
    def __init__(self):
        # 初始化界面
        self.root = tk.Tk()
        self.root.title("4WD Car Control")

        # 虚拟摇杆区
        self.canvas = tk.Canvas(self.root, width=200, height=200, bg='#eee')
        self.canvas.grid(row=0, column=0, columnspan=2)
        self.pad = self.canvas.create_oval(10, 10, 190, 190, outline='#333')
        self.knob = self.canvas.create_oval(95, 95, 105, 105, fill='#555')
        self.canvas.bind('<Button-1>', self.on_press)
        self.canvas.bind('<B1-Motion>', self.on_drag)

        # 控制状态
        self.throttle = 0.0
        self.turn = 0.0
        self.chassis = Chassis()

        # 控制按钮
        btns = [
            ('A:Forward', lambda: self.quick(1, 0)),
            ('B:Spin',    lambda: self.quick(0, 1)),
            ('X:Stop',    lambda: self.quick(0, 0)),
            ('LB:4WD',    lambda: self.chassis.set_mode(True)),
            ('RB:Eco',    lambda: self.chassis.set_mode(False)),
        ]
        for i, (txt, cmd) in enumerate(btns):
            tk.Button(self.root, text=txt, width=10, command=cmd).grid(row=1+i//2, column=i%2, padx=5, pady=5)

        # 初始化手柄
        pygame.init()
        pygame.joystick.init()
        self.joy = pygame.joystick.Joystick(0) if pygame.joystick.get_count() > 0 else None
        if self.joy:
            self.joy.init()

        self.update()
        self.root.protocol('WM_DELETE_WINDOW', self.on_close)
        self.root.mainloop()

    def quick(self, t, r):
        """快捷设置 throttle/turn"""
        self.throttle = t
        self.turn = r
        self.apply()

    def on_press(self, e):
        self.calc_axes(e.x, e.y)

    def on_drag(self, e):
        self.calc_axes(e.x, e.y)

    def calc_axes(self, x, y):
        """将鼠标坐标转换为摇杆控制值"""
        cx, cy = 100, 100
        dx, dy = x - cx, cy - y
        dist = math.hypot(dx, dy)
        if dist > 80:
            dx *= 80 / dist
            dy *= 80 / dist
        self.turn = dx / 80
        self.throttle = dy / 80
        self.apply()

    def apply(self):
        """根据 throttle/turn 更新图形与驱动信号"""
        x = 100 + self.turn * 80
        y = 100 - self.throttle * 80
        self.canvas.coords(self.knob, x-5, y-5, x+5, y+5)
        v_l = max(-1, min(1, self.throttle + self.turn))
        v_r = max(-1, min(1, self.throttle - self.turn))
        self.chassis.drive(v_l, v_r)

    def update(self):
        """50ms 更新一次手柄输入"""
        if self.joy:
            pygame.event.pump()
            lx = self.joy.get_axis(0)
            ly = -self.joy.get_axis(1)
            self.throttle, self.turn = ly, lx
            if self.joy.get_button(0): self.quick(1, 0)
            if self.joy.get_button(1): self.quick(0, 1)
            if self.joy.get_button(2): self.quick(0, 0)
            if self.joy.get_button(4): self.chassis.set_mode(True)
            if self.joy.get_button(5): self.chassis.set_mode(False)
            self.apply()
        self.root.after(50, self.update)

    def on_close(self):
        """关闭前停止电机和释放资源"""
        self.chassis.stop_all()
        if self.joy: pygame.quit()
        self.root.destroy()

# 主程序入口
if __name__ == '__main__':
    CarApp()
