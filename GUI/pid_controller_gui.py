"""
Ball & Plate PID Controller GUI
Requires: pip install customtkinter pyserial
Run:      python3.13 pid_controller_gui.py
"""

import customtkinter as ctk
import tkinter as tk
import serial
import serial.tools.list_ports
import threading
from datetime import datetime

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

ACCENT = "#5b9bd5"
ORANGE = "#d4813a"
GREEN  = "#6abf69"
DANGER = "#c0392b"
PURPLE = "#9b7fd4"
BG     = "#1e1e1e"
PANEL  = "#252525"
BORDER = "#3a3a3a"
TEXT   = "#cccccc"
MUTED  = "#777777"

# ── Physical table ADC ranges ─────────────────────────────────────────────────
X_LEFT,   X_RIGHT  = 440, 40
Y_BOTTOM, Y_TOP    = 190, 830
X_MID = 240
Y_MID = 510
X_MIN, X_MAX = min(X_LEFT, X_RIGHT), max(X_LEFT, X_RIGHT)
Y_MIN, Y_MAX = min(Y_BOTTOM, Y_TOP), max(Y_BOTTOM, Y_TOP)
X_SPAN = abs(X_LEFT - X_RIGHT)   # 400
Y_SPAN = abs(Y_TOP  - Y_BOTTOM)  # 640

DEFAULTS = {
    "kpx": 0.045,  "kix": 0.01, "kdx": 0.03,
    "kpy": 0.045,  "kiy": 0.01, "kdy": 0.03,
    "set_x": X_MID, "set_y": Y_MID,
    "x_center": 84, "x_min": 74, "x_max": 94,
    "y_center": 83, "y_min": 73, "y_max": 93,
}

PID_LIMITS = {
    "kp": (0.0, 0.2,  0.001),
    "ki": (0.0, 0.02, 0.0001),
    "kd": (0.0, 0.1,  0.001),
}

# Mode constants — match Arduino enum values
MODES = [
    ("SET POINT", "SET_POINT", 0, ACCENT),
    ("SQUARE",    "SQUARE",    1, ORANGE),
    ("CIRCLE",    "CIRCLE",    2, PURPLE),
]


def clamp_x(v):
    try:    v = float(v)
    except: return DEFAULTS["set_x"]
    return int(max(X_MIN, min(X_MAX, v)))


def clamp_y(v):
    try:    v = float(v)
    except: return DEFAULTS["set_y"]
    return int(max(Y_MIN, min(Y_MAX, v)))


# ══════════════════════════════════════════════════════════════════════════════
class TiltTableCanvas(tk.Canvas):
    PAD_L = 40
    PAD_R = 14
    PAD_T = 14
    PAD_B = 32

    def __init__(self, master, set_x_var, set_y_var, on_change_cb, **kwargs):
        super().__init__(master, bg="#1a1a1a", highlightthickness=0, **kwargs)
        self.set_x_var    = set_x_var
        self.set_y_var    = set_y_var
        self.on_change_cb = on_change_cb
        self.bind("<Configure>", lambda e: self._redraw())
        self.bind("<Button-1>",  self._on_click)
        self.bind("<B1-Motion>", self._on_click)

    def _rect(self):
        w, h = self.winfo_width(), self.winfo_height()
        return self.PAD_L, self.PAD_T, w - self.PAD_R, h - self.PAD_B

    def _adc_to_px(self, adc_x, adc_y):
        x0, y0, x1, y1 = self._rect()
        tw, th = x1 - x0, y1 - y0
        if tw <= 0 or th <= 0: return x0, y0
        px = x0 + (X_LEFT - adc_x)  / (X_LEFT  - X_RIGHT)  * tw
        py = y0 + (Y_TOP  - adc_y)  / (Y_TOP   - Y_BOTTOM) * th
        return px, py

    def _px_to_adc(self, px, py):
        x0, y0, x1, y1 = self._rect()
        tw, th = x1 - x0, y1 - y0
        if tw <= 0 or th <= 0: return DEFAULTS["set_x"], DEFAULTS["set_y"]
        adc_x = X_LEFT  - (px - x0) / tw * (X_LEFT  - X_RIGHT)
        adc_y = Y_TOP   - (py - y0) / th * (Y_TOP   - Y_BOTTOM)
        return clamp_x(adc_x), clamp_y(adc_y)

    def _on_click(self, event):
        x0, y0, x1, y1 = self._rect()
        px = max(x0, min(x1, event.x))
        py = max(y0, min(y1, event.y))
        ax, ay = self._px_to_adc(px, py)
        self.set_x_var.set(ax)
        self.set_y_var.set(ay)
        self._redraw()
        if self.on_change_cb:
            self.on_change_cb()

    def refresh(self): self._redraw()

    def _redraw(self):
        self.delete("all")
        w, h = self.winfo_width(), self.winfo_height()
        if w < 30 or h < 30: return
        x0, y0, x1, y1 = self._rect()
        tw, th = x1 - x0, y1 - y0

        # Table background & border
        self.create_rectangle(x0, y0, x1, y1,
                               outline=BORDER, fill="#222222", width=1)
        self.create_rectangle(x0, y0, x1, y1,
                               outline=ACCENT, fill="", width=1)

        # Grid lines
        for i in range(1, 4):
            self.create_line(x0 + i*tw/4, y0, x0 + i*tw/4, y1,
                              fill="#2a2a2a", width=1, dash=(2, 4))
        for i in range(1, 4):
            self.create_line(x0, y0 + i*th/4, x1, y0 + i*th/4,
                              fill="#2a2a2a", width=1, dash=(2, 4))

        font_ax = ("Courier", 8)

        # Y axis labels & ticks on left
        for adc_y, label in [(Y_TOP, str(Y_TOP)), (Y_MID, str(Y_MID)), (Y_BOTTOM, str(Y_BOTTOM))]:
            _, py = self._adc_to_px(X_MID, adc_y)
            self.create_line(x0-5, py, x0, py, fill=MUTED, width=1)
            self.create_text(x0-7, py, text=label, fill=MUTED, font=font_ax, anchor="e")
        self.create_text(8, (y0+y1)/2, text="Y", fill=MUTED,
                          font=("Courier", 9, "bold"), anchor="center")

        # X axis labels & ticks on bottom
        for adc_x, label in [(X_LEFT, str(X_LEFT)), (X_MID, str(X_MID)), (X_RIGHT, str(X_RIGHT))]:
            px, _ = self._adc_to_px(adc_x, Y_MID)
            self.create_line(px, y1, px, y1+5, fill=MUTED, width=1)
            self.create_text(px, y1+8, text=label, fill=MUTED, font=font_ax, anchor="n")
        self.create_text((x0+x1)/2, y1+22, text="X",
                          fill=MUTED, font=("Courier", 9, "bold"), anchor="center")

        # Direction hints
        self.create_text(x0+2,  y0-8, text="<- LEFT",  fill=MUTED, font=("Courier", 7), anchor="w")
        self.create_text(x1-2,  y0-8, text="RIGHT ->", fill=MUTED, font=("Courier", 7), anchor="e")

        # Midpoint dot
        mx, my = self._adc_to_px(X_MID, Y_MID)
        self.create_line(mx-8, my, mx+8, my, fill=BORDER, width=1)
        self.create_line(mx, my-8, mx, my+8, fill=BORDER, width=1)
        self.create_oval(mx-4, my-4, mx+4, my+4, fill="#333333", outline=MUTED, width=1)
        self.create_text(mx+8, my-8, text="MID", fill=MUTED, font=("Courier", 7), anchor="sw")

        # Setpoint crosshair
        try:    sx, sy = self.set_x_var.get(), self.set_y_var.get()
        except: sx, sy = DEFAULTS["set_x"], DEFAULTS["set_y"]

        bx, by = self._adc_to_px(sx, sy)
        arm = 14
        self.create_oval(bx-6,  by-6,  bx+6,  by+6,  outline=ACCENT, fill="#1a2a3a", width=2)
        self.create_line(bx-arm, by,   bx-8,   by,    fill=ACCENT, width=1)
        self.create_line(bx+8,   by,   bx+arm, by,    fill=ACCENT, width=1)
        self.create_line(bx, by-arm,   bx,     by-8,  fill=ACCENT, width=1)
        self.create_line(bx, by+8,     bx,     by+arm,fill=ACCENT, width=1)
        self.create_oval(bx-2, by-2, bx+2, by+2, fill=ACCENT, outline="")

        label = f"({sx}, {sy})"
        lx  = bx+14 if bx < (x0+x1)/2 else bx-14
        ly  = by-14 if by > y0+20      else by+14
        anc = "w"   if bx < (x0+x1)/2 else "e"
        self.create_text(lx, ly, text=label, fill=ACCENT,
                          font=("Courier", 9, "bold"), anchor=anc)


# ══════════════════════════════════════════════════════════════════════════════
class App(ctk.CTk):
    MONITOR_MIN_H = 34
    MONITOR_DEF_H = 220

    def __init__(self):
        super().__init__()
        self.title("Ball & Plate — PID Controller")
        self.geometry("1300x900")
        self.minsize(1000, 680)
        self.configure(fg_color=BG)

        self.serial_port   = None
        self.read_thread   = None
        self._running      = False
        self._drag_start_y = 0
        self._drag_start_h = 0
        self._monitor_h    = self.MONITOR_DEF_H

        self._build_ui()
        self._refresh_ports()

    # ── top-level layout ──────────────────────────────────────────────────────
    def _build_ui(self):
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=0)
        self.grid_columnconfigure(0, weight=1)

        top = ctk.CTkFrame(self, fg_color=BG, corner_radius=0)
        top.grid(row=0, column=0, sticky="nsew")
        top.grid_columnconfigure(0, weight=1)
        top.grid_columnconfigure(1, weight=1)
        top.grid_rowconfigure(0, weight=1)

        left_scroll = ctk.CTkScrollableFrame(top, fg_color=PANEL, corner_radius=0,
                                              scrollbar_button_color=BORDER,
                                              scrollbar_button_hover_color=MUTED)
        left_scroll.grid(row=0, column=0, sticky="nsew")
        left_scroll.grid_columnconfigure(0, weight=1)
        self._build_left(left_scroll)

        right_scroll = ctk.CTkScrollableFrame(top, fg_color=BG, corner_radius=0,
                                               scrollbar_button_color=BORDER,
                                               scrollbar_button_hover_color=MUTED)
        right_scroll.grid(row=0, column=1, sticky="nsew", padx=(1, 0))
        right_scroll.grid_columnconfigure(0, weight=1)
        self._build_right(right_scroll)

        self._build_monitor()

    def _section(self, parent, title, row):
        ctk.CTkLabel(parent, text=title,
                      font=ctk.CTkFont(size=12, weight="bold"),
                      text_color=TEXT, anchor="w"
                      ).grid(row=row, column=0, sticky="ew", padx=16, pady=(14, 4))
        return row + 1

    # ══════════════════════════════════════════════════════════════════════════
    # LEFT PANEL
    # ══════════════════════════════════════════════════════════════════════════
    def _build_left(self, p):
        row = 0

        # ── Connection ────────────────────────────────────────────────────────
        row = self._section(p, "Serial Connection", row)

        pf = ctk.CTkFrame(p, fg_color="transparent")
        pf.grid(row=row, column=0, sticky="ew", padx=16)
        pf.grid_columnconfigure(0, weight=1)
        row += 1

        self.port_var = ctk.StringVar()
        self.port_menu = ctk.CTkOptionMenu(pf, variable=self.port_var,
                                            fg_color=BORDER, button_color=BORDER,
                                            button_hover_color=MUTED,
                                            font=ctk.CTkFont("Courier", 12),
                                            text_color=TEXT, width=200)
        self.port_menu.grid(row=0, column=0, sticky="ew", padx=(0, 6))

        self.baud_var = ctk.StringVar(value="115200")
        ctk.CTkOptionMenu(pf, variable=self.baud_var,
                           values=["9600","19200","38400","57600","115200"],
                           fg_color=BORDER, button_color=BORDER,
                           button_hover_color=MUTED,
                           font=ctk.CTkFont("Courier", 12),
                           text_color=TEXT, width=90
                           ).grid(row=0, column=1)

        bf = ctk.CTkFrame(p, fg_color="transparent")
        bf.grid(row=row, column=0, sticky="ew", padx=16, pady=(6, 0))
        bf.grid_columnconfigure((0, 1), weight=1)
        row += 1

        self.connect_btn = ctk.CTkButton(bf, text="CONNECT",
                                          font=ctk.CTkFont("Courier", 12, "bold"),
                                          fg_color="transparent", border_color=ACCENT,
                                          border_width=1, text_color=ACCENT,
                                          hover_color=ACCENT, command=self._toggle_connect)
        self.connect_btn.grid(row=0, column=0, sticky="ew", padx=(0, 4))
        ctk.CTkButton(bf, text="Refresh",
                       font=ctk.CTkFont("Courier", 11),
                       fg_color="transparent", border_color=BORDER,
                       border_width=1, text_color=MUTED, hover_color=BORDER,
                       command=self._refresh_ports
                       ).grid(row=0, column=1, sticky="ew")

        self.status_lbl = ctk.CTkLabel(p, text="● DISCONNECTED",
                                        font=ctk.CTkFont("Courier", 11),
                                        text_color=MUTED)
        self.status_lbl.grid(row=row, column=0, sticky="w", padx=16, pady=(4, 0))
        row += 1

        # ── PID Gains ─────────────────────────────────────────────────────────
        row = self._section(p, "PID Gains", row)
        self.pid_vars = {}

        for axis_lbl, axis_id, color in [("X Axis", "x", ACCENT), ("Y Axis", "y", ORANGE)]:
            ctk.CTkLabel(p, text=axis_lbl,
                          font=ctk.CTkFont(size=11, weight="bold"), text_color=color
                          ).grid(row=row, column=0, sticky="w", padx=16, pady=(8, 2))
            row += 1

            for g_lbl, g_id in [("Kp","kp"), ("Ki","ki"), ("Kd","kd")]:
                g_min, g_max, g_step = PID_LIMITS[g_id]
                key = f"{g_id}{axis_id}"
                var = ctk.DoubleVar(value=DEFAULTS[key])
                self.pid_vars[key] = var

                f = ctk.CTkFrame(p, fg_color="transparent")
                f.grid(row=row, column=0, sticky="ew", padx=16, pady=1)
                f.grid_columnconfigure(1, weight=1)
                row += 1

                ctk.CTkLabel(f, text=g_lbl, width=28,
                              font=ctk.CTkFont("Courier", 12), text_color=MUTED
                              ).grid(row=0, column=0, padx=(0, 6))
                ctk.CTkSlider(f, from_=g_min, to=g_max, variable=var,
                               number_of_steps=int((g_max-g_min)/g_step),
                               button_color=ACCENT, button_hover_color=ACCENT,
                               progress_color=color,
                               command=lambda v, k=key: self._on_slider(k, v)
                               ).grid(row=0, column=1, sticky="ew", padx=(0, 6))
                e = ctk.CTkEntry(f, textvariable=var, width=72,
                                  font=ctk.CTkFont("Courier", 12),
                                  fg_color="#2a2a2a", border_color=BORDER,
                                  text_color=ACCENT, justify="right")
                e.grid(row=0, column=2)
                e.bind("<Return>",   lambda ev, k=key: self._on_entry(k))
                e.bind("<FocusOut>", lambda ev, k=key: self._on_entry(k))

        self.pid_send_btn = ctk.CTkButton(p, text="Send PID Gains",
                                           font=ctk.CTkFont(size=12, weight="bold"),
                                           fg_color=BORDER, text_color=TEXT,
                                           hover_color="#4a4a4a", state="disabled",
                                           command=self._send_pid)
        self.pid_send_btn.grid(row=row, column=0, sticky="ew", padx=16, pady=(10, 0))
        row += 1

        # ── Servo Limits ──────────────────────────────────────────────────────
        row = self._section(p, "Servo Limits", row)
        self.servo_vars = {}
        svf = ctk.CTkFrame(p, fg_color="transparent")
        svf.grid(row=row, column=0, sticky="ew", padx=16)
        for col in range(3): svf.grid_columnconfigure(col, weight=1)
        row += 1

        for idx, (lbl_txt, key) in enumerate([
            ("X CENTER","x_center"),("X MIN","x_min"),("X MAX","x_max"),
            ("Y CENTER","y_center"),("Y MIN","y_min"),("Y MAX","y_max"),
        ]):
            c, r2 = idx % 3, idx // 3
            var = ctk.IntVar(value=DEFAULTS[key])
            self.servo_vars[key] = var
            ctk.CTkLabel(svf, text=lbl_txt, font=ctk.CTkFont("Courier", 9),
                          text_color=MUTED
                          ).grid(row=r2*2, column=c, sticky="w", padx=4, pady=(6, 0))
            ctk.CTkEntry(svf, textvariable=var, width=70,
                          font=ctk.CTkFont("Courier", 12),
                          fg_color="#2a2a2a", border_color=BORDER, text_color=ACCENT
                          ).grid(row=r2*2+1, column=c, sticky="ew", padx=4)

        self.sv_send_btn = ctk.CTkButton(p, text="Send Servo Limits",
                                          font=ctk.CTkFont(size=12, weight="bold"),
                                          fg_color=BORDER, text_color=TEXT,
                                          hover_color="#4a4a4a", state="disabled",
                                          command=self._send_servo_limits)
        self.sv_send_btn.grid(row=row, column=0, sticky="ew", padx=16, pady=(8, 0))
        row += 1

        # ── Quick Commands ────────────────────────────────────────────────────
        row = self._section(p, "Quick Commands", row)
        self.quick_btns = []

        self.reset_btn = ctk.CTkButton(p, text="Reset to Defaults & Send",
                                        font=ctk.CTkFont(size=12),
                                        fg_color=BORDER, text_color=TEXT,
                                        hover_color="#4a4a4a", state="disabled",
                                        command=self._reset_defaults)
        self.reset_btn.grid(row=row, column=0, sticky="ew", padx=16, pady=(0, 16))
        self.quick_btns.append(self.reset_btn)
        row += 1

    # ══════════════════════════════════════════════════════════════════════════
    # RIGHT PANEL
    # ══════════════════════════════════════════════════════════════════════════
    def _build_right(self, p):
        row = 0

        # ── Operating Mode ────────────────────────────────────────────────────
        row = self._section(p, "Operating Mode", row)

        self.mode_var = ctk.StringVar(value="SET_POINT")
        self._mode_btns = {}

        mode_frame = ctk.CTkFrame(p, fg_color="transparent")
        mode_frame.grid(row=row, column=0, sticky="ew", padx=16)
        mode_frame.grid_columnconfigure((0, 1, 2), weight=1)
        row += 1

        for col, (label, key, val, color) in enumerate(MODES):
            btn = ctk.CTkButton(
                mode_frame, text=label,
                font=ctk.CTkFont(size=12, weight="bold"),
                fg_color=color if key == "SET_POINT" else BORDER,
                text_color=BG  if key == "SET_POINT" else MUTED,
                hover_color=color,
                command=lambda k=key, v=val, c=color: self._set_mode(k, v, c))
            btn.grid(row=0, column=col, sticky="ew",
                     padx=(0 if col==0 else 3, 3 if col < 2 else 0), pady=4)
            self._mode_btns[key] = (btn, color)

        self.mode_status_lbl = ctk.CTkLabel(p, text="Current mode: SET POINT",
                                             font=ctk.CTkFont("Courier", 10),
                                             text_color=MUTED)
        self.mode_status_lbl.grid(row=row, column=0, sticky="w", padx=16, pady=(0, 4))
        row += 1

        # ── Setpoint ──────────────────────────────────────────────────────────
        row = self._section(p, "Setpoint", row)

        self.set_x = ctk.IntVar(value=DEFAULTS["set_x"])
        self.set_y = ctk.IntVar(value=DEFAULTS["set_y"])

        spf = ctk.CTkFrame(p, fg_color="transparent")
        spf.grid(row=row, column=0, sticky="ew", padx=16)
        spf.grid_columnconfigure((0, 1), weight=1)
        row += 1

        for i, (lbl, var, cfn) in enumerate([
            (f"Set X  [{X_MIN}-{X_MAX}]", self.set_x, clamp_x),
            (f"Set Y  [{Y_MIN}-{Y_MAX}]", self.set_y, clamp_y),
        ]):
            ctk.CTkLabel(spf, text=lbl, font=ctk.CTkFont("Courier", 10),
                          text_color=MUTED
                          ).grid(row=0, column=i, sticky="w",
                                 padx=(0 if i==0 else 8, 0))
            e = ctk.CTkEntry(spf, textvariable=var, width=110,
                              font=ctk.CTkFont("Courier", 14),
                              fg_color="#2a2a2a", border_color=BORDER, text_color=ACCENT)
            e.grid(row=1, column=i, sticky="ew",
                   padx=(0 if i==0 else 8, 8 if i==0 else 0))
            e.bind("<Return>",   lambda ev, v=var, c=cfn: self._clamp_sp(v, c))
            e.bind("<FocusOut>", lambda ev, v=var, c=cfn: self._clamp_sp(v, c))

        self.sp_send_btn = ctk.CTkButton(p, text="Send Setpoint",
                                          font=ctk.CTkFont(size=12, weight="bold"),
                                          fg_color=BORDER, text_color=TEXT,
                                          hover_color="#4a4a4a", state="disabled",
                                          command=self._send_setpoint)
        self.sp_send_btn.grid(row=row, column=0, sticky="ew", padx=16, pady=(8, 0))
        row += 1

        # Table canvas
        ctk.CTkLabel(p, text="Click table to set position",
                      font=ctk.CTkFont(size=11), text_color=MUTED
                      ).grid(row=row, column=0, sticky="w", padx=16, pady=(14, 4))
        row += 1

        TABLE_PX_W = 380
        TABLE_PX_H = int(TABLE_PX_W * Y_SPAN / X_SPAN)
        CANVAS_H   = TABLE_PX_H + TiltTableCanvas.PAD_T + TiltTableCanvas.PAD_B

        wrap = ctk.CTkFrame(p, fg_color="transparent",
                             height=CANVAS_H,
                             width=TABLE_PX_W + TiltTableCanvas.PAD_L + TiltTableCanvas.PAD_R)
        wrap.grid(row=row, column=0, sticky="ew", padx=16, pady=(0, 16))
        wrap.grid_propagate(False)
        wrap.grid_columnconfigure(0, weight=1)
        wrap.grid_rowconfigure(0, weight=1)
        row += 1

        self.table_canvas = TiltTableCanvas(wrap, self.set_x, self.set_y,
                                             self._on_canvas_click)
        self.table_canvas.grid(row=0, column=0, sticky="nsew")

    # ══════════════════════════════════════════════════════════════════════════
    # SERIAL MONITOR
    # ══════════════════════════════════════════════════════════════════════════
    def _build_monitor(self):
        self.monitor_frame = ctk.CTkFrame(self, fg_color=PANEL, corner_radius=0,
                                           height=self._monitor_h)
        self.monitor_frame.grid(row=1, column=0, sticky="ew")
        self.monitor_frame.grid_propagate(False)
        self.monitor_frame.grid_columnconfigure(0, weight=1)
        self.monitor_frame.grid_rowconfigure(1, weight=1)

        # Drag handle / header bar
        hdr = ctk.CTkFrame(self.monitor_frame, fg_color="#1a1a1a",
                            corner_radius=0, height=36)
        hdr.grid(row=0, column=0, sticky="ew")
        hdr.grid_columnconfigure(0, weight=1)
        hdr.grid_propagate(False)
        hdr.bind("<ButtonPress-1>", self._drag_start)
        hdr.bind("<B1-Motion>",     self._drag_motion)

        title_lbl = ctk.CTkLabel(hdr, text="Serial Monitor",
                                  font=ctk.CTkFont("Courier", 10, "bold"),
                                  text_color=ACCENT)
        title_lbl.grid(row=0, column=0, sticky="w", padx=14)
        title_lbl.bind("<ButtonPress-1>", self._drag_start)
        title_lbl.bind("<B1-Motion>",     self._drag_motion)

        ctrl = ctk.CTkFrame(hdr, fg_color="transparent")
        ctrl.grid(row=0, column=1, padx=10)
        self.autoscroll = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(ctrl, text="Auto-scroll", variable=self.autoscroll,
                         font=ctk.CTkFont("Courier", 10),
                         text_color=MUTED, fg_color=ACCENT, hover_color=ACCENT
                         ).grid(row=0, column=0, padx=8)
        ctk.CTkButton(ctrl, text="Clear", width=56,
                       font=ctk.CTkFont("Courier", 10),
                       fg_color="transparent", border_color=BORDER,
                       border_width=1, text_color=MUTED, hover_color=BORDER,
                       command=self._clear_log).grid(row=0, column=1)

        # Textbox
        self.terminal = ctk.CTkTextbox(self.monitor_frame,
                                        font=ctk.CTkFont("Courier", 12),
                                        fg_color="#1a1a1a", text_color=TEXT,
                                        corner_radius=0, wrap="word", border_width=0)
        self.terminal.grid(row=1, column=0, sticky="nsew")
        self.terminal.configure(state="disabled")
        tb = self.terminal._textbox
        tb.tag_config("rx",  foreground="#8ab8d0")
        tb.tag_config("tx",  foreground=ORANGE)
        tb.tag_config("sys", foreground=GREEN)
        tb.tag_config("err", foreground=DANGER)
        tb.tag_config("ts",  foreground=MUTED)

        # Command input row
        cmd_frame = ctk.CTkFrame(self.monitor_frame, fg_color="#1a1a1a",
                                  corner_radius=0, height=40)
        cmd_frame.grid(row=2, column=0, sticky="ew")
        cmd_frame.grid_columnconfigure(1, weight=1)
        cmd_frame.grid_propagate(False)
        ctk.CTkLabel(cmd_frame, text=">",
                      font=ctk.CTkFont("Courier", 13, "bold"),
                      text_color=ACCENT).grid(row=0, column=0, padx=12)
        self.cmd_entry = ctk.CTkEntry(cmd_frame,
                                       placeholder_text="type a raw command...",
                                       font=ctk.CTkFont("Courier", 12),
                                       fg_color="transparent", border_width=0,
                                       text_color=TEXT)
        self.cmd_entry.grid(row=0, column=1, sticky="ew")
        self.cmd_entry.bind("<Return>", self._send_raw)
        ctk.CTkButton(cmd_frame, text="Send", width=66,
                       font=ctk.CTkFont("Courier", 10, "bold"),
                       fg_color="transparent", border_color=ACCENT,
                       border_width=1, text_color=ACCENT, hover_color=ACCENT,
                       command=self._send_raw).grid(row=0, column=2, padx=8)

        self.monitor_frame.grid_rowconfigure(2, weight=0)

        self._log("Ball & Plate PID Controller", "sys")
        self._log("Select a port and click CONNECT to begin.", "sys")
        self._log(f"X: {X_LEFT}(left) -> {X_RIGHT}(right)   Y: {Y_BOTTOM}(bottom) -> {Y_TOP}(top)   Mid: ({X_MID},{Y_MID})", "sys")

    # ── drag to resize ────────────────────────────────────────────────────────
    def _drag_start(self, event):
        self._drag_start_y = event.y_root
        self._drag_start_h = self.monitor_frame.winfo_height()

    def _drag_motion(self, event):
        delta = self._drag_start_y - event.y_root
        new_h = max(self.MONITOR_MIN_H,
                    min(self.winfo_height() - 200,
                        self._drag_start_h + delta))
        self.monitor_frame.configure(height=int(new_h))

    # ── logging ───────────────────────────────────────────────────────────────
    def _log(self, msg: str, tag: str = "sys"):
        ts = datetime.now().strftime("%H:%M:%S")
        self.terminal.configure(state="normal")
        tb = self.terminal._textbox
        tb.insert("end", f"{ts}  ", "ts")
        tb.insert("end", f"[{tag.upper():3s}]  ", tag)
        tb.insert("end", msg + "\n", tag)
        self.terminal.configure(state="disabled")
        if self.autoscroll.get():
            tb.see("end")
        lc = int(tb.index("end-1c").split(".")[0])
        if lc > 800:
            self.terminal.configure(state="normal")
            tb.delete("1.0", f"{lc-800}.0")
            self.terminal.configure(state="disabled")

    def _clear_log(self):
        self.terminal.configure(state="normal")
        self.terminal._textbox.delete("1.0", "end")
        self.terminal.configure(state="disabled")
        self._log("Log cleared", "sys")

    # ── serial ────────────────────────────────────────────────────────────────
    def _refresh_ports(self):
        ports = [p.device for p in serial.tools.list_ports.comports()]
        if not ports: ports = ["(no ports found)"]
        self.port_menu.configure(values=ports)
        self.port_var.set(ports[0])

    def _toggle_connect(self):
        if self.serial_port and self.serial_port.is_open:
            self._disconnect()
        else:
            self._connect()

    def _connect(self):
        port = self.port_var.get()
        baud = int(self.baud_var.get())
        try:
            self.serial_port = serial.Serial(port, baud, timeout=1)
            self._running = True
            self.read_thread = threading.Thread(target=self._read_loop, daemon=True)
            self.read_thread.start()
            self._set_connected(True)
            self._log(f"Connected to {port} @ {baud} baud", "sys")
        except Exception as e:
            self._log(f"Connection failed: {e}", "err")
            self.serial_port = None

    def _disconnect(self):
        self._running = False
        try:
            if self.serial_port: self.serial_port.close()
        except Exception: pass
        self.serial_port = None
        self._set_connected(False)
        self._log("Disconnected", "sys")

    def _read_loop(self):
        buf = ""
        while self._running and self.serial_port and self.serial_port.is_open:
            try:
                data = self.serial_port.read(256).decode("utf-8", errors="replace")
                if data:
                    buf += data
                    lines = buf.split("\n")
                    buf = lines.pop()
                    for line in lines:
                        line = line.strip()
                        if line: self.after(0, self._log, line, "rx")
            except serial.SerialException as e:
                self.after(0, self._log, f"Serial error: {e}", "err")
                break
            except Exception: break
        self.after(0, self._set_connected, False)

    def _write(self, cmd: str):
        if not self.serial_port or not self.serial_port.is_open:
            self._log("Not connected", "err"); return
        try:
            self.serial_port.write((cmd.strip() + "\n").encode())
            self._log(cmd.strip(), "tx")
        except Exception as e:
            self._log(f"Send error: {e}", "err")

    def _set_connected(self, val: bool):
        self.status_lbl.configure(
            text="● CONNECTED" if val else "● DISCONNECTED",
            text_color=GREEN if val else MUTED)
        self.connect_btn.configure(
            text="DISCONNECT" if val else "CONNECT",
            border_color=DANGER if val else ACCENT,
            text_color=DANGER if val else ACCENT)
        state = "normal" if val else "disabled"
        for btn in [self.pid_send_btn, self.sp_send_btn,
                    self.sv_send_btn] + self.quick_btns:
            btn.configure(state=state)
        for key, (btn, _) in self._mode_btns.items():
            btn.configure(state=state)

    # ── operating mode ────────────────────────────────────────────────────────
    def _set_mode(self, mode_key: str, mode_val: int, color: str):
        self.mode_var.set(mode_key)
        # Update all button appearances
        for key, (btn, btn_color) in self._mode_btns.items():
            if key == mode_key:
                btn.configure(fg_color=btn_color, text_color=BG)
            else:
                btn.configure(fg_color=BORDER, text_color=MUTED)
        label = next(lbl for lbl, k, v, c in MODES if k == mode_key)
        self.mode_status_lbl.configure(text=f"Current mode: {label}")
        self._write(f"MODE:{mode_val}")

    # ── reset to defaults & send all ─────────────────────────────────────────
    def _reset_defaults(self):
        for key, val in [("kpx",0.04),("kix",0.002),("kdx",0.03),
                          ("kpy",0.04),("kiy",0.002),("kdy",0.03)]:
            self.pid_vars[key].set(val)
        self.set_x.set(DEFAULTS["set_x"])
        self.set_y.set(DEFAULTS["set_y"])
        self.table_canvas.refresh()
        for key, val in DEFAULTS.items():
            if key in self.servo_vars:
                self.servo_vars[key].set(val)
        self._send_pid()
        self.after(400, self._send_setpoint)
        self.after(800, self._send_servo_limits)
        self._log("Reset all values to defaults and sent", "sys")

    # ── send helpers ──────────────────────────────────────────────────────────
    def _send_pid(self):
        cmds = [f"KPX:{self.pid_vars['kpx'].get():.4f}",
                f"KIX:{self.pid_vars['kix'].get():.4f}",
                f"KDX:{self.pid_vars['kdx'].get():.4f}",
                f"KPY:{self.pid_vars['kpy'].get():.4f}",
                f"KIY:{self.pid_vars['kiy'].get():.4f}",
                f"KDY:{self.pid_vars['kdy'].get():.4f}"]
        for i, cmd in enumerate(cmds):
            self.after(i*60, self._write, cmd)

    def _send_setpoint(self):
        self._write(f"SETX:{self.set_x.get()}")
        self.after(60, self._write, f"SETY:{self.set_y.get()}")

    def _send_servo_limits(self):
        pairs = list(zip(["x_center","x_min","x_max","y_center","y_min","y_max"],
                         ["XCENTER","XMIN","XMAX","YCENTER","YMIN","YMAX"]))
        for i, (fk, cmd) in enumerate(pairs):
            self.after(i*60, self._write, f"{cmd}:{self.servo_vars[fk].get()}")

    def _send_raw(self, event=None):
        val = self.cmd_entry.get().strip()
        if val:
            self._write(val)
            self.cmd_entry.delete(0, "end")

    # ── setpoint helpers ──────────────────────────────────────────────────────
    def _clamp_sp(self, var, clamp_fn):
        try:    var.set(clamp_fn(var.get()))
        except: pass
        self.table_canvas.refresh()

    def _on_canvas_click(self): self.table_canvas.refresh()

    # ── PID sync ──────────────────────────────────────────────────────────────
    def _on_slider(self, key, value):
        self.pid_vars[key].set(round(value, 4))

    def _on_entry(self, key):
        try:    self.pid_vars[key].set(round(float(self.pid_vars[key].get()), 4))
        except: pass

    # ── cleanup ───────────────────────────────────────────────────────────────
    def on_close(self):
        self._running = False
        if self.serial_port:
            try: self.serial_port.close()
            except Exception: pass
        self.destroy()


if __name__ == "__main__":
    app = App()
    app.protocol("WM_DELETE_WINDOW", app.on_close)
    app.mainloop()
