#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
car.py ? ???????????+GUI????
???
- GUI ???????? + ????
- USB ?????????????????
- ?? A?????? B?????? X???? Y???
- LT/RT ??????/????
"""
import tkinter as tk
import pygame
from gpiozero import DigitalOutputDevice
import time

# ?????? ?????? ??????
FL_FWD = DigitalOutputDevice(13); FL_REV = DigitalOutputDevice(19)
FR_FWD = DigitalOutputDevice(6);  FR_REV = DigitalOutputDevice(5)
RL_FWD = DigitalOutputDevice(26); RL_REV = DigitalOutputDevice(16)
RR_FWD = DigitalOutputDevice(12); RR_REV = DigitalOutputDevice(20)
ALL = [FL_FWD, FL_REV, FR_FWD, FR_REV, RL_FWD, RL_REV, RR_FWD, RR_REV]

# ????
mode_4wd = True  # True: ?????False: ????

def stop_all():
    """??????"""
    for m in ALL:
        m.off()

# ???????v_l, v_r ?[-1,1]
def drive(v_l, v_r):
    stop_all()
    def apply(fwd, rev, val):
        if val > 0.1:
            fwd.on()
        elif val < -0.1:
            rev.on()
    if mode_4wd:
        apply(FL_FWD, FL_REV, v_l); apply(RL_FWD, RL_REV, v_l)
        apply(FR_FWD, FR_REV, v_r); apply(RR_FWD, RR_REV, v_r)
    else:
        apply(FL_FWD, FL_REV, v_l)
        apply(RR_FWD, RR_REV, v_r)

# ?????? ?? ??????
class CarApp:
    def __init__(self):
        # Tkinter GUI ??
        self.root = tk.Tk(); self.root.title("4WD Car Control")
        # ?? Canvas
        self.canvas = tk.Canvas(self.root, width=200, height=200, bg='#eee')
        self.canvas.grid(row=0, column=0, columnspan=2)
        # ??????
        self.pad = self.canvas.create_oval(10,10,190,190,outline='#333')
        self.knob = self.canvas.create_oval(90,90,110,110,fill='#555')
        # ??
        self.btn_A = tk.Button(self.root, text='A:Forward', command=lambda: self.quick(1,0))
        self.btn_B = tk.Button(self.root, text='B:Spin',    command=lambda: self.quick(0,1))
        self.btn_X = tk.Button(self.root, text='X:Stop',    command=lambda: self.quick(0,0))
        self.btn_LT= tk.Button(self.root, text='LT:4WD',    command=self.set_4wd)
        self.btn_RT= tk.Button(self.root, text='RT:Eco',    command=self.set_eco)
        for i,btn in enumerate([self.btn_A,self.btn_B,self.btn_X,self.btn_LT,self.btn_RT]):
            btn.grid(row=1+i//2, column=i%2, padx=5, pady=5)
        # ????
        self.throttle=0; self.turn=0
        # ??? Pygame ??
        pygame.init(); pygame.joystick.init()
        self.joy = pygame.joystick.Joystick(0) if pygame.joystick.get_count()>0 else None
        if self.joy: self.joy.init()
        # ????
        self.update()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.root.mainloop()

    def set_4wd(self):
        global mode_4wd; mode_4wd=True

    def set_eco(self):
        global mode_4wd; mode_4wd=False

    def quick(self, t, r):
        """????/??/??"""
        self.throttle, self.turn = t, r
        self.apply()

    def apply(self):
        v_l = max(-1, min(1, self.throttle + self.turn))
        v_r = max(-1, min(1, self.throttle - self.turn))
        drive(v_l, v_r)
        # GUI ??????
        x = 100 + self.turn * 80; y = 100 - self.throttle * 80
        self.canvas.coords(self.knob, x-10, y-10, x+10, y+10)

    def update(self):
        # ??????
        if self.joy:
            pygame.event.pump()
            self.turn = self.joy.get_axis(0)  # ??? X
            self.throttle = -self.joy.get_axis(1)  # ??? Y
            # ????
            if self.joy.get_button(0): self.quick(1,0)
            elif self.joy.get_button(1): self.quick(0,1)
            elif self.joy.get_button(2): self.quick(0,0)
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