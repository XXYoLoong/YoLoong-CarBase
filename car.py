#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
car.py — 四轮差速小车控制（手柄+GUI二合一）
功能：
- 左摇杆控制底盘前进/转向
- 右摇杆（预留）将来控制二自由度云台
- 按键 A：执行前进（Forward）
- 按键 B：执行原地旋转（Spin）
- 按键 X：停止所有运动（Stop）
- 按键 Y：未设定
- LT：切换四轮驱动模式（4WD）
- RT：切换节能模式（节省电机数量）
"""
import tkinter as tk
import pygame
from gpiozero import DigitalOutputDevice
from threading import Thread
import time

# ——————— BCM 引脚定义 ———————
FL_FWD = DigitalOutputDevice(13)   # 前左轮正转
FL_REV = DigitalOutputDevice(19)   # 前左轮反转
FR_FWD = DigitalOutputDevice(6)    # 前右轮正转
FR_REV = DigitalOutputDevice(5)    # 前右轮反转
RL_FWD = DigitalOutputDevice(26)   # 后左轮正转
RL_REV = DigitalOutputDevice(16)   # 后左轮反转
RR_FWD = DigitalOutputDevice(12)   # 后右轮正转
RR_REV = DigitalOutputDevice(20)   # 后右轮反转
ALL = [FL_FWD, FL_REV, FR_FWD, FR_REV, RL_FWD, RL_REV, RR_FWD, RR_REV]

# 驱动模式标志
mode_4wd = True  # True: 四轮驱动, False: 节能模式

def stop_all():
    """停止所有轮子"""
    for m in ALL:
        m.off()


def drive(v_l, v_r):
    """
    差速驱动：
    v_l, v_r 在 [-1,1]
    >0 正转, <0 反转
    """
    stop_all()
    # 左轮
    if v_l > 0:
        FL_FWD.on(); RL_FWD.on()
    elif v_l < 0:
        FL_REV.on(); RL_REV.on()
    # 右轮
    if v_r > 0:
        FR_FWD.on(); RR_FWD.on()
    elif v_r < 0:
        FR_REV.on(); RR_REV.on()

# ——————— GUI 部分 ———————
class CarGUI(Thread):
    def __init__(self):
        super().__init__(daemon=True)
        self.root = tk.Tk()
        self.root.title("4WD Car Control GUI")
        # 前后推杆（Throttle）
        tk.Label(self.root, text="Throttle").pack()
        self.throttle = tk.DoubleVar()
        tk.Scale(self.root, variable=self.throttle,
                 from_=1.0, to=-1.0, resolution=0.01,
                 orient=tk.VERTICAL, length=200).pack(side=tk.LEFT)
        # 左右转杆（Turn）
        tk.Label(self.root, text="Turn").pack()
        self.turn = tk.DoubleVar()
        tk.Scale(self.root, variable=self.turn,
                 from_=-1.0, to=1.0, resolution=0.01,
                 orient=tk.VERTICAL, length=200).pack(side=tk.LEFT)
        # 驱动模式切换按钮
        self.mode_btn = tk.Button(self.root, text="Mode:4WD", command=self.toggle_mode)
        self.mode_btn.pack(pady=10)
        # 停止按钮
        tk.Button(self.root, text="STOP", command=lambda: self.set(0,0), bg="#ff4444").pack(pady=5)
        self._running = True
        self._update()

    def toggle_mode(self):
        """切换四轮/节能模式"""
        global mode_4wd
        mode_4wd = not mode_4wd
        self.mode_btn.config(text=f"Mode:{'4WD' if mode_4wd else 'ECO'}")

    def set(self, t, r):
        self.throttle.set(t); self.turn.set(r)

    def get(self):
        return self.throttle.get(), self.turn.get()

    def _update(self):
        t, r = self.get()
        # 差速计算
        v_l = max(-1, min(1, t + r))
        v_r = max(-1, min(1, t - r))
        if not mode_4wd:
            # 节能模式：只驱动两个轮 (前左+后右)
            stop_all()
            if v_l !=0:  # 左轮信号
                (FL_FWD if v_l>0 else FL_REV).on()
            if v_r !=0:
                (RR_FWD if v_r>0 else RR_REV).on()
        else:
            drive(v_l, v_r)
        if self._running:
            self.root.after(50, self._update)

    def run(self):
        self.root.protocol("WM_DELETE_WINDOW", self.stop)
        self.root.mainloop()

    def stop(self):
        self._running=False; stop_all(); self.root.destroy()

# ——————— 手柄部分 ———————
class CarJoystick(Thread):
    def __init__(self):
        super().__init__(daemon=True)
        pygame.init(); pygame.joystick.init()
        self.joy = None
        if pygame.joystick.get_count()>0:
            self.joy=pygame.joystick.Joystick(0); self.joy.init()
        self._running=True

    def run(self):
        while self._running:
            pygame.event.pump()
            if self.joy:
                # 左摇杆轴 0/1 控制底盘
                x = self.joy.get_axis(0); y = -self.joy.get_axis(1)
                # 右摇杆轴 3/4 将来云台
                # 按键映射
                if self.joy.get_button(0):  # A
                    drive(1,1)  # 前进
                if self.joy.get_button(1):  # B
                    drive(1,-1) # 原地转
                if self.joy.get_button(2):  # X
                    stop_all()
                # Y 不设
                if self.joy.get_button(6):  # LT
                    global mode_4wd; mode_4wd=True
                if self.joy.get_button(7):  # RT
                    mode_4wd=False
                # 同时响应摇杆
                gui.set(y, x)
            time.sleep(0.05)

    def stop(self):
        self._running=False; stop_all(); pygame.quit()

# ——————— 主程序 ———————
if __name__=='__main__':
    gui = CarGUI(); gui.start()
    joy = CarJoystick(); joy.start()
    gui.join(); joy.stop()