#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
car.py — 四轮差速小车控制（手柄+GUI二合一）
功能：
- GUI 圆盘摇杆 + 控制按钮 鼠标点击+拖拽控制
- USB 手柄左摇杆控制底盘，右摇杆预留云台
- 按键 A：全速前进； B：原地旋转； X：停止； Y：未用
- LB (按钮4)：切换四轮驱动模式； RB (按钮5)：切换节能模式
注：前进方向物理映射已修正，前后前轮与后轮一致移动
"""
import tkinter as tk
import pygame
from gpiozero import DigitalOutputDevice
import math

# —————— 硬件引脚定义 ——————
FL_FWD = DigitalOutputDevice(13); FL_REV = DigitalOutputDevice(19)
FR_FWD = DigitalOutputDevice(6);  FR_REV = DigitalOutputDevice(5)
RL_FWD = DigitalOutputDevice(26); RL_REV = DigitalOutputDevice(16)
RR_FWD = DigitalOutputDevice(12); RR_REV = DigitalOutputDevice(20)
ALL = [FL_FWD, FL_REV, FR_FWD, FR_REV, RL_FWD, RL_REV, RR_FWD, RR_REV]

mode_4wd = True  # 驱动模式标志

def stop_all():
    """停止所有电机"""
    for m in ALL: m.off()

# 差速输出，v_l, v_r in [-1,1]
def drive(v_l, v_r):
    stop_all()
    def apply(fwd, rev, val, invert=False):
        # invert 控制正向是否反转（前轮物理映射一致）
        if abs(val) < 0.1: return
        if (val > 0) ^ invert:
            fwd.on()
        else:
            rev.on()
    # 应用差速
    if mode_4wd:
        apply(FL_FWD, FL_REV, v_l)  # 前左
        apply(RL_FWD, RL_REV, v_l)  # 后左
        apply(FR_FWD, FR_REV, v_r)  # 前右
        apply(RR_FWD, RR_REV, v_r)  # 后右
    else:
        # 节能：仅驱动前左+后右
        apply(FL_FWD, FL_REV, v_l)
        apply(RR_FWD, RR_REV, v_r)

class CarApp:
    def __init__(self):
        # GUI 初始化
        self.root = tk.Tk(); self.root.title("4WD Car Control")
        # 圆盘
        self.canvas = tk.Canvas(self.root, width=200, height=200, bg='#eee')
        self.canvas.grid(row=0, column=0, columnspan=2)
        self.pad = self.canvas.create_oval(10,10,190,190,outline='#333')
        self.knob = self.canvas.create_oval(95,95,105,105,fill='#555')
        self.canvas.bind('<Button-1>', self.on_press)
        self.canvas.bind('<B1-Motion>', self.on_drag)
        self.throttle = 0; self.turn = 0
        # 按钮区
        btns = [ ('A:Forward', lambda: self.quick(1,0)),
                 ('B:Spin',    lambda: self.quick(0,1)),
                 ('X:Stop',    lambda: self.quick(0,0)),
                 ('LB:4WD',    self.set_4wd),
                 ('RB:Eco',    self.set_eco) ]
        for i,(txt,cmd) in enumerate(btns):
            tk.Button(self.root, text=txt, width=10, command=cmd).grid(row=1+i, column=i%2)
        # pygame 手柄
        pygame.init(); pygame.joystick.init()
        self.joy = pygame.joystick.Joystick(0) if pygame.joystick.get_count()>0 else None
        if self.joy: self.joy.init()
        # update loop
        self.update()
        self.root.protocol('WM_DELETE_WINDOW', self.on_close)
        self.root.mainloop()

    def set_4wd(self):
        global mode_4wd; mode_4wd = True
    def set_eco(self):
        global mode_4wd; mode_4wd = False
    def quick(self, t, r):
        self.throttle, self.turn = t, r; self.apply()

    def on_press(self, e):
        self.calc_axes(e.x, e.y)
    def on_drag(self, e):
        self.calc_axes(e.x, e.y)

    def calc_axes(self, x, y):
        # 转换 canvas 坐标到 [-1,1]
        cx, cy = 100,100
        dx, dy = x-cx, cy-y
        dist = math.hypot(dx, dy)
        if dist>80: dx,dy = dx*80/dist, dy*80/dist
        self.turn = dx/80; self.throttle = dy/80
        self.apply()

    def apply(self):
        # 更新旋钮
        x = 100 + self.turn*80; y = 100 - self.throttle*80
        self.canvas.coords(self.knob, x-5,y-5,x+5,y+5)
        # 差速驱动
        vl = max(-1,min(1,self.throttle+self.turn))
        vr = max(-1,min(1,self.throttle-self.turn))
        drive(vl, vr)

    def update(self):
        if self.joy:
            pygame.event.pump()
            # 左摇杆控制盘
            ax,ay = self.joy.get_axis(0), -self.joy.get_axis(1)
            self.throttle, self.turn = ay, ax
            # 按键
            if self.joy.get_button(0): self.quick(1,0)
            if self.joy.get_button(1): self.quick(0,1)
            if self.joy.get_button(2): self.quick(0,0)
            if self.joy.get_button(4): self.set_4wd()
            if self.joy.get_button(5): self.set_eco()
            self.apply()
        self.root.after(50, self.update)

    def on_close(self):
        stop_all()
        if self.joy: pygame.quit()
        self.root.destroy()

if __name__=='__main__':
    CarApp()