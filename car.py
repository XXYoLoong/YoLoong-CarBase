#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
car.py — 四轮差速小车控制（手柄+GUI二合一）
功能说明：
  - GUI 圆盘摇杆 + 按钮，支持鼠标点击或拖拽操作
  - USB 手柄左摇杆控制底盘行驶，右摇杆预留云台控制
  - 手柄按键：A 全速前进；B 原地旋转；X 停止；Y 保留；LB 切换 4WD；RB 切换 ECO
  - 驱动模式：4WD 全轮驱动；ECO 节能驱动（仅前左+后右）
"""
import tkinter as tk
import pygame
from gpiozero import DigitalOutputDevice
import math

# —————— 硬件引脚定义 ——————
# DigitalOutputDevice 控制对应 GPIO 脚上的高低电平
FL_FWD = DigitalOutputDevice(13)  # 前左轮正向驱动 GPIO13
FL_REV = DigitalOutputDevice(19)  # 前左轮反向驱动 GPIO19
FR_FWD = DigitalOutputDevice(6)   # 前右轮正向驱动 GPIO6
FR_REV = DigitalOutputDevice(5)   # 前右轮反向驱动 GPIO5
RL_FWD = DigitalOutputDevice(26)  # 后左轮正向驱动 GPIO26
RL_REV = DigitalOutputDevice(16)  # 后左轮反向驱动 GPIO16
RR_FWD = DigitalOutputDevice(12)  # 后右轮正向驱动 GPIO12
RR_REV = DigitalOutputDevice(20)  # 后右轮反向驱动 GPIO20
# 所有电机列表，用于统一停止
ALL = [FL_FWD, FL_REV, FR_FWD, FR_REV, RL_FWD, RL_REV, RR_FWD, RR_REV]

# 驱动模式标志，全局变量
mode_4wd = True  # True: 四轮驱动；False: 节能模式

# —————— 停止所有电机函数 ——————
def stop_all():
    """立即关闭所有电机输出"""
    for m in ALL:
        m.off()

    # —————— 方向补偿函数 ——————
def compensate(val, is_rear=False):
    """后轮方向需要反转补偿"""
    return -val if is_rear else val

# —————— 差速驱动函数 ——————
def drive(v_l, v_r):
    """
    v_l, v_r: 左轮、右轮速度 [-1.0,1.0]
    >0 表示前进(正向)，<0 表示后退(反向)
    根据 mode_4wd 全局变量决定驱动模式
    """
    global mode_4wd
    stop_all()  # 先停止所有电机，避免冲突

    def apply(fwd_device, rev_device, val):
        """
        根据 val 值启用正向或反向输出
        fwd_device: DigitalOutputDevice 正向
        rev_device: DigitalOutputDevice 反向
        val: -1.0..1.0，阈值 0.1
        """
        if val > 0.1:
            fwd_device.on()
        elif val < -0.1:
            rev_device.on()
        # |val| <0.1 时不驱动，保持停止

    if mode_4wd:
        # 左侧：前左 & 后左（后轮方向补偿）
        apply(FL_FWD, FL_REV, compensate(v_l, is_rear=False))  # 前左
        apply(RL_FWD, RL_REV, compensate(v_l, is_rear=True))  # 后左

        # 右侧：前右 & 后右（后轮方向补偿）
        apply(FR_FWD, FR_REV, compensate(v_r, is_rear=False))  # 前右
        apply(RR_FWD, RR_REV, compensate(v_r, is_rear=True))  # 后右
    else:
        # 节能模式：仅驱动前左 & 后右（后轮方向补偿）
        apply(FL_FWD, FL_REV, compensate(v_l, is_rear=False))  # 前左
        apply(RR_FWD, RR_REV, compensate(v_r, is_rear=True))  # 后右


# —————— 主应用类，包含 GUI 与手柄交互 ——————
class CarApp:
    def __init__(self):
        # 创建主窗口
        self.root = tk.Tk()
        self.root.title("4WD Car Control")

        # 创建 Canvas 以画出虚拟摇杆圆盘
        self.canvas = tk.Canvas(self.root, width=200, height=200, bg='#eee')
        self.canvas.grid(row=0, column=0, columnspan=2)
        # 圆盘边框: 外圆
        self.pad = self.canvas.create_oval(10, 10, 190, 190, outline='#333')
        # 摇杆节点: 初始在圆心
        self.knob = self.canvas.create_oval(95, 95, 105, 105, fill='#555')
        # 绑定鼠标按下与拖拽事件
        self.canvas.bind('<Button-1>', self.on_press)
        self.canvas.bind('<B1-Motion>', self.on_drag)

        # 初始化摇杆值
        self.throttle = 0.0  # 前后速度
        self.turn = 0.0      # 左右转向

        # 按钮布局：A/B/X/LB/RB
        btn_configs = [
            ('A:Forward', lambda: self.quick(1, 0)),
            ('B:Spin',    lambda: self.quick(0, 1)),
            ('X:Stop',    lambda: self.quick(0, 0)),
            ('LB:4WD',    self.set_4wd),
            ('RB:Eco',    self.set_eco),
        ]
        # 按钮放置网格
        for idx, (text, cmd) in enumerate(btn_configs):
            r = 1 + idx // 2
            c = idx % 2
            tk.Button(self.root, text=text, width=10, command=cmd).grid(row=r, column=c, padx=5, pady=5)

        # 初始化 Pygame 手柄
        pygame.init()
        pygame.joystick.init()
        self.joy = None
        if pygame.joystick.get_count() > 0:
            self.joy = pygame.joystick.Joystick(0)
            self.joy.init()

        # 启动周期更新
        self.update()
        # 关闭窗口时清理
        self.root.protocol('WM_DELETE_WINDOW', self.on_close)
        self.root.mainloop()

    def set_4wd(self):
        """切换到全轮驱动模式"""
        global mode_4wd
        mode_4wd = True

    def set_eco(self):
        """切换到节能驱动模式"""
        global mode_4wd
        mode_4wd = False

    def quick(self, t, r):
        """
        快捷设置摇杆值并驱动：
        t: throttle, r: turn
        """
        self.throttle = t
        self.turn = r
        self.apply()  # 立即生效

    def on_press(self, event):
        """鼠标按下时更新摇杆值"""
        self.calc_axes(event.x, event.y)

    def on_drag(self, event):
        """鼠标拖拽时持续更新摇杆值"""
        self.calc_axes(event.x, event.y)

    def calc_axes(self, x, y):
        """
        将鼠标坐标(x,y)转换为摇杆的 throttle/turn
        圆心(100,100)，半径80
        """
        cx, cy = 100, 100
        dx, dy = x - cx, cy - y  # y 反转: 上为正
        dist = math.hypot(dx, dy)
        # 限制在圆范围内
        if dist > 80:
            dx *= 80 / dist
            dy *= 80 / dist
        # 归一化到 [-1,1]
        self.turn = dx / 80
        self.throttle = dy / 80
        self.apply()

    def apply(self):
        """
        更新摇杆 GUI 位置 & 调用驱动函数
        """
        # 更新 knob 位置
        x = 100 + self.turn * 80
        y = 100 - self.throttle * 80
        self.canvas.coords(self.knob, x-5, y-5, x+5, y+5)
        # 计算左右速度
        v_l = max(-1, min(1, self.throttle + self.turn))
        v_r = max(-1, min(1, self.throttle - self.turn))
        drive(v_l, v_r)

    def update(self):
        """
        定时 (50ms) 读取手柄输入并更新
        """
        if self.joy:
            pygame.event.pump()
            # 读取左摇杆
            lx = self.joy.get_axis(0)  # 左右
            ly = self.joy.get_axis(1)  # 上下
            self.throttle, self.turn = ly, lx
            # 按键 A/B/X
            if self.joy.get_button(0):  # A 键
                self.quick(1, 0)
            if self.joy.get_button(1):  # B 键
                self.quick(0, 1)
            if self.joy.get_button(2):  # X 键
                self.quick(0, 0)
            # 模式切换 LB/RB
            if self.joy.get_button(4):  # LB
                self.set_4wd()
            if self.joy.get_button(5):  # RB
                self.set_eco()
            self.apply()
        # 下次调用
        self.root.after(50, self.update)

    def on_close(self):
        """退出前停止电机并清理手柄"""
        stop_all()
        if self.joy:
            pygame.quit()
        self.root.destroy()

if __name__ == '__main__':
    CarApp()