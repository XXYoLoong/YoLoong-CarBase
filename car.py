#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import tkinter as tk
import pygame
from gpiozero import DigitalOutputDevice

# —————— 硬件引脚定义 ——————
FL_FWD = DigitalOutputDevice(13); FL_REV = DigitalOutputDevice(19)
FR_FWD = DigitalOutputDevice(6);  FR_REV = DigitalOutputDevice(5)
RL_FWD = DigitalOutputDevice(26); RL_REV = DigitalOutputDevice(16)
RR_FWD = DigitalOutputDevice(12); RR_REV = DigitalOutputDevice(20)
ALL = [FL_FWD, FL_REV, FR_FWD, FR_REV, RL_FWD, RL_REV, RR_FWD, RR_REV]

def stop_all():
    """停止所有通道"""
    for m in ALL: m.off()

def drive(v_l, v_r, mode_four=True):
    """
    v_l, v_r in [-1,1];
    mode_four=True 四轮模式；False 节能模式（仅 FL & RR）
    """
    stop_all()
    def apply(side, v):
        if v>0:
            side[0].on()
        elif v<0:
            side[1].on()
    if mode_four:
        apply((FL_FWD, FL_REV), v_l); apply((RL_FWD, RL_REV), v_l)
        apply((FR_FWD, FR_REV), v_r); apply((RR_FWD, RR_REV), v_r)
    else:
        # 节能：仅前左 + 后右
        apply((FL_FWD, FL_REV), v_l)
        apply((RR_FWD, RR_REV), v_r)

# —————— 主程序 ——————
class CarApp:
    def __init__(self):
        # GUI
        self.root = tk.Tk(); self.root.title("4WD 控制 (Hand+GUI)")
        # 滑块: Throttle & Turn
        tk.Label(self.root, text="Throttle").grid(row=0, column=0)
        self.throttle = tk.DoubleVar(); tk.Scale(self.root, variable=self.throttle,
            from_=1.0, to=-1.0, resolution=0.01, orient=tk.VERTICAL, length=150
        ).grid(row=1, column=0)
        tk.Label(self.root, text="Turn").grid(row=0, column=1)
        self.turn = tk.DoubleVar(); tk.Scale(self.root, variable=self.turn,
            from_=-1.0, to=1.0, resolution=0.01, orient=tk.VERTICAL, length=150
        ).grid(row=1, column=1)
        # 模式按钮
        self.mode_four = True
        self.btn_mode = tk.Button(self.root, text="Mode:4WD", command=self.toggle_mode)
        self.btn_mode.grid(row=2, column=0, columnspan=2, pady=5)
        # STOP 按钮
        tk.Button(self.root, text="STOP", bg="#f44", fg="white",
                  command=lambda: self.set_axes(0,0), width=10).grid(row=3, column=0, columnspan=2)

        # 初始化 pygame 手柄
        pygame.init(); pygame.joystick.init()
        self.joy = pygame.joystick.Joystick(0) if pygame.joystick.get_count()>0 else None
        if self.joy:
            self.joy.init()
        # 按键映射
        self.BTN_A, self.BTN_B, self.BTN_X = 0,1,2
        self.BTN_LT, self.BTN_RT = 4,5

        # 周期调用
        self.update()

        # 关闭时
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def toggle_mode(self):
        """切换四轮/节能"""
        self.mode_four = not self.mode_four
        self.btn_mode.config(text="Mode:4WD" if self.mode_four else "Mode:Eco")

    def set_axes(self, t, r):
        """外部快捷设定"""
        self.throttle.set(t); self.turn.set(r)

    def update(self):
        """定时读 GUI + 手柄，共同驱动"""
        # 1. GUI 滑块优先
        t = self.throttle.get(); r = self.turn.get()

        # 2. 手柄输入覆盖
        if self.joy:
            pygame.event.pump()
            x = self.joy.get_axis(0)      # 左摇杆左右
            y = -self.joy.get_axis(1)     # 左摇杆上下 (反转)
            t, r = y, x
            # 按键快捷
            if self.joy.get_button(self.BTN_A):
                t, r = 1, 0
            if self.joy.get_button(self.BTN_B):
                t, r = 0, 1
            if self.joy.get_button(self.BTN_X):
                t, r = 0, 0
            # 模式切换
            if self.joy.get_button(self.BTN_LT):
                self.mode_four = True; self.btn_mode.config(text="Mode:4WD")
            if self.joy.get_button(self.BTN_RT):
                self.mode_four = False; self.btn_mode.config(text="Mode:Eco")

        # 差速计算并驱动
        v_l = max(-1, min(1, t + r)); v_r = max(-1, min(1, t - r))
        drive(v_l, v_r, self.mode_four)

        # 20ms 后再调用
        self.root.after(20, self.update)

    def on_close(self):
        stop_all()
        if self.joy: pygame.quit()
        self.root.destroy()

if __name__=="__main__":
    CarApp().root.mainloop()
