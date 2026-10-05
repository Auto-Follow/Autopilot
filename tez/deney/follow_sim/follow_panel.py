#!/usr/bin/env python3
"""Follow Me control panel (Tkinter).

Virtual RC sticks (Mode 2) send MANUAL_CONTROL to PX4 SITL. In Follow Me mode PX4 uses them like a real RC:
  left stick up/down  -> follow height   (throttle)
  right stick up/down -> follow distance (pitch)
  right stick left/right -> follow angle (roll)
The panel also moves the red target, streams FOLLOW_TARGET and draws the slant-distance geometry in Gazebo.
"""
import fcntl
import math
import os
import subprocess
import sys
import time
import tkinter as tk
from tkinter import ttk

from follow_core import (CAMERA_PITCH_DEG, FOLLOW_DEFAULTS, IMAGE_H, IMAGE_W, LINK_RANGE_M, LINK_WARN_M, MODE_FOLLOW,
                         MODE_HOLD, MODE_LAND, MODE_RTL, PX4_TARGET_STALE_S, VISION_DEMO_HEIGHT_M, FollowSim)

STICK_SIZE = 150
KNOB_R = 14
BG = "#1e2227"
FG = "#e6e6e6"
MUTED = "#9aa4ad"
ACCENT = "#ff8c1a"

AUTO_EXIT = os.environ.get("FOLLOW_PANEL_AUTO_EXIT") == "1"
LOCK_FILE = "/tmp/follow_panel.lock"

PATTERN_LABELS = [("dur", "Dur"), ("gidip_gel", "Gidip gel (30 m)"), ("daire", "Daire (R = 15 m)"),
                  ("kare", "Kare (30 m)"), ("klavye", "Klavye (I J K L)"), ("parkur", "Test parkuru (~85 s)")]


class Stick(tk.Canvas):
    """Spring-loaded virtual stick. Values in [-1, 1]; up = +y, right = +x."""

    def __init__(self, master, title, x_label, y_label, on_change):
        super().__init__(master, width=STICK_SIZE, height=STICK_SIZE, bg="#2a2f36", highlightthickness=1,
                         highlightbackground="#3b424b")
        self.on_change = on_change
        c = STICK_SIZE / 2
        self.create_line(c, 8, c, STICK_SIZE - 8, fill="#4a525c")
        self.create_line(8, c, STICK_SIZE - 8, c, fill="#4a525c")
        self.create_oval(8, 8, STICK_SIZE - 8, STICK_SIZE - 8, outline="#4a525c")
        self.create_text(c, 10, text=y_label.split("|")[0], fill=MUTED, font=("DejaVu Sans", 8), anchor="n")
        self.create_text(c, STICK_SIZE - 10, text=y_label.split("|")[1], fill=MUTED, font=("DejaVu Sans", 8),
                         anchor="s")
        self.create_text(10, c - 10, text=x_label.split("|")[0], fill=MUTED, font=("DejaVu Sans", 8), anchor="w")
        self.create_text(STICK_SIZE - 10, c - 10, text=x_label.split("|")[1], fill=MUTED, font=("DejaVu Sans", 8),
                         anchor="e")
        self.knob = self.create_oval(c - KNOB_R, c - KNOB_R, c + KNOB_R, c + KNOB_R, fill=ACCENT, outline="")
        self.title = title
        self.x = self.y = 0.0
        self.mouse_active = False
        self.key_x = self.key_y = 0.0
        self.bind("<B1-Motion>", self._drag)
        self.bind("<Button-1>", self._drag)
        self.bind("<ButtonRelease-1>", self._release)

    def _drag(self, event):
        c, r = STICK_SIZE / 2, STICK_SIZE / 2 - 8
        self.mouse_active = True
        self.set((event.x - c) / r, (c - event.y) / r)

    def _release(self, _event):
        self.mouse_active = False
        self.set(self.key_x, self.key_y)

    def set_keys(self, kx, ky):
        self.key_x, self.key_y = kx, ky
        if not self.mouse_active:
            self.set(kx, ky)

    def set(self, x, y):
        self.x, self.y = max(-1.0, min(1.0, x)), max(-1.0, min(1.0, y))
        c, r = STICK_SIZE / 2, STICK_SIZE / 2 - 8
        px, py = c + self.x * r, c - self.y * r
        self.coords(self.knob, px - KNOB_R, py - KNOB_R, px + KNOB_R, py + KNOB_R)
        self.on_change()


class Panel(tk.Tk):
    def __init__(self, sim):
        super().__init__()
        self.sim = sim
        self.title("Follow Me Kontrol Paneli")
        self.configure(bg=BG)
        self.resizable(False, False)
        self.pressed = set()

        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure(".", background=BG, foreground=FG, font=("DejaVu Sans", 9))
        style.configure("TButton", padding=(8, 4), background="#343b44", foreground=FG)
        style.map("TButton", background=[("active", "#46505b")])
        style.configure("Accent.TButton", background="#b85c00", foreground="white")
        style.map("Accent.TButton", background=[("active", "#d06a00")])
        style.configure("TLabelframe", background=BG, foreground=FG, bordercolor="#3b424b")
        style.configure("TLabelframe.Label", background=BG, foreground=ACCENT, font=("DejaVu Sans", 9, "bold"))
        style.configure("TRadiobutton", background=BG, foreground=FG)
        style.configure("TCheckbutton", background=BG, foreground=FG)
        style.configure("Value.TLabel", font=("DejaVu Sans Mono", 10))

        self._build()
        self.bind_all("<KeyPress>", self._key_down)
        self.bind_all("<KeyRelease>", self._key_up)
        self.protocol("WM_DELETE_WINDOW", self._close)
        self.after(100, self._refresh)

    # ------------------------------------------------------------------ layout
    def _build(self):
        top = ttk.Frame(self, padding=8)
        top.grid(row=0, column=0, columnspan=2, sticky="ew")
        self.status_var = tk.StringVar(value="PX4 bekleniyor…")
        ttk.Label(top, textvariable=self.status_var, font=("DejaVu Sans", 10, "bold")).pack(side="left")

        # Flight buttons
        fb = ttk.LabelFrame(self, text="Uçuş", padding=8)
        fb.grid(row=1, column=0, columnspan=2, sticky="ew", padx=8)
        ttk.Button(fb, text="1) Kalk", command=self.sim.link.takeoff).grid(row=0, column=0, padx=3)
        ttk.Button(fb, text="2) Follow Me", style="Accent.TButton",
                   command=lambda: self.sim.link.set_mode(MODE_FOLLOW)).grid(row=0, column=1, padx=3)
        ttk.Button(fb, text="Bekle", command=lambda: self.sim.link.set_mode(MODE_HOLD)).grid(row=0, column=2, padx=3)
        ttk.Button(fb, text="Eve dön", command=lambda: self.sim.link.set_mode(MODE_RTL)).grid(row=0, column=3, padx=3)
        ttk.Button(fb, text="İn", command=lambda: self.sim.link.set_mode(MODE_LAND)).grid(row=0, column=4, padx=3)
        ttk.Button(fb, text="Varsayılan FLW param.", command=self._defaults).grid(row=0, column=5, padx=3)
        ttk.Button(fb, text="Kamera penceresi", command=self._open_viewer).grid(row=0, column=6, padx=3)

        # Sticks
        sf = ttk.LabelFrame(self, text="Kumanda (Mode 2) — fare ile sürükle veya klavye", padding=8)
        sf.grid(row=2, column=0, sticky="nsew", padx=(8, 4), pady=8)
        self.left = Stick(sf, "Sol", "Yaw ←|→ Yaw", "Yükseklik ↑|Yükseklik ↓", self._sticks_changed)
        self.right = Stick(sf, "Sağ", "Açı ←|→ Açı", "Mesafe +|Mesafe −", self._sticks_changed)
        self.left.grid(row=0, column=0, padx=6)
        self.right.grid(row=0, column=1, padx=6)
        ttk.Label(sf, text="Sol çubuk\nW/S: yükseklik  A/D: yaw", foreground=MUTED, justify="center").grid(
            row=1, column=0, pady=(4, 0))
        ttk.Label(sf, text="Sağ çubuk\n↑/↓: mesafe  ←/→: açı", foreground=MUTED, justify="center").grid(
            row=1, column=1, pady=(4, 0))
        ttk.Label(sf, text="Follow Me'de: gaz = FLW_TGT_HT, pitch = FLW_TGT_DST, roll = FLW_TGT_FA\n"
                           "(moddan çıkınca PX4 bu ayarları sıfırlar)", foreground=MUTED,
                  justify="center").grid(row=2, column=0, columnspan=2, pady=(6, 0))

        # Target controls
        tf = ttk.LabelFrame(self, text="Hedef (kırmızı figür)", padding=8)
        tf.grid(row=2, column=1, sticky="nsew", padx=(4, 8), pady=8)
        self.pattern_var = tk.StringVar(value=self.sim.target.pattern)
        for i, (key, label) in enumerate(PATTERN_LABELS):
            ttk.Radiobutton(tf, text=label, value=key, variable=self.pattern_var,
                            command=lambda: self.sim.target.set_pattern(self.pattern_var.get())).grid(
                row=i, column=0, sticky="w")
        ttk.Label(tf, text="Hız (m/s)").grid(row=len(PATTERN_LABELS), column=0, sticky="w", pady=(6, 0))
        self.speed_var = tk.DoubleVar(value=self.sim.target.speed)
        tk.Scale(tf, from_=0.0, to=5.0, resolution=0.1, orient="horizontal", variable=self.speed_var,
                 command=lambda v: setattr(self.sim.target, "speed", float(v)), bg=BG, fg=FG,
                 highlightthickness=0, troughcolor="#343b44", length=170).grid(
            row=len(PATTERN_LABELS) + 1, column=0, sticky="w")
        self.bcast_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(tf, text="FOLLOW_TARGET yayınla", variable=self.bcast_var,
                        command=lambda: setattr(self.sim, "broadcast_target", self.bcast_var.get())).grid(
            row=len(PATTERN_LABELS) + 2, column=0, sticky="w")
        self.vel_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(tf, text="Hedef hızını gönder\n(kaldır: Vision gibi sadece konum)", variable=self.vel_var,
                        command=self._velocity_toggled).grid(row=len(PATTERN_LABELS) + 3, column=0, sticky="w")
        self.scene_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(tf, text="Sahnede ışın/düzlem çiz", variable=self.scene_var,
                        command=lambda: setattr(self.sim, "show_scene", self.scene_var.get())).grid(
            row=len(PATTERN_LABELS) + 4, column=0, sticky="w")
        self.vision_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(tf, text="Vision modu: FOLLOW_TARGET\nsadece kamera hedefi görünce", variable=self.vision_var,
                        command=self._vision_toggled).grid(row=len(PATTERN_LABELS) + 5, column=0, sticky="w",
                                                           pady=(6, 0))
        ttk.Button(tf, text=f"Takip yüksekliği {VISION_DEMO_HEIGHT_M:g} m (kamera görsün)",
                   command=self._vision_height).grid(row=len(PATTERN_LABELS) + 6, column=0, sticky="w", pady=(4, 0))

        # Geometry readout
        gf = ttk.LabelFrame(self, text="Slant distance geometrisi (canlı)", padding=8)
        gf.grid(row=3, column=0, columnspan=2, sticky="ew", padx=8)
        self.geo_vars = {}
        rows = [("h", "Yükseklik h (kamera → zemin)"), ("theta", "θ (dik ile ışın arası)"),
                ("slant", "Slant distance = h / cos θ"), ("hdist", "Yatay mesafe (nadir → hedef)"),
                ("nadir", "Zemin kesişimi (yükseklik)"), ("hit", "Zemin kesişimi (ışın)"),
                ("pixel", "Görüntü düzlemi (u, v)"), ("gps", "Hedef GPS (FOLLOW_TARGET)"),
                ("gcs", "Yer istasyonu mesafesi (Wi-Fi)"), ("vis", "Hedef görünürlüğü")]
        for i, (key, label) in enumerate(rows):
            ttk.Label(gf, text=label, foreground=MUTED).grid(row=i, column=0, sticky="w", padx=(0, 12))
            var = tk.StringVar(value="—")
            lbl = ttk.Label(gf, textvariable=var, style="Value.TLabel")
            lbl.grid(row=i, column=1, sticky="w")
            self.geo_vars[key] = var
            if key == "gcs":
                self.gcs_label = lbl
            if key == "vis":
                self.vis_label = lbl

        self._build_experiments()

        # Log
        lf = ttk.LabelFrame(self, text="Mesajlar", padding=6)
        lf.grid(row=4, column=0, columnspan=2, sticky="ew", padx=8, pady=8)
        self.log = tk.Text(lf, height=6, width=74, bg="#15181c", fg=FG, relief="flat", font=("DejaVu Sans Mono", 8))
        self.log.pack(fill="both")
        self._log_count = 0

    def _build_experiments(self):
        """Right column: camera tilt, geolocation (target position from the image) and the Wi-Fi model."""
        col = ttk.Frame(self)
        col.grid(row=1, column=2, rowspan=4, sticky="ns", padx=(0, 8), pady=(0, 8))

        gf = ttk.LabelFrame(col, text="Geolocation (kameradan hedef konumu)", padding=8)
        gf.pack(fill="x")
        tilt = (f"Kamera {CAMERA_PITCH_DEG:g}° aşağı eğik" if CAMERA_PITCH_DEG else
                "Kamera düz (eğik: baslat.sh --egim 40)")
        ttk.Label(gf, text=tilt, foreground=MUTED).pack(anchor="w")
        ttk.Label(gf, text="FOLLOW_TARGET konum kaynağı:").pack(anchor="w", pady=(6, 0))
        self.source_var = tk.StringVar(value=self.sim.target_source)
        ttk.Radiobutton(gf, text="Gerçek konum (GPS'li hedef gibi)", value="gercek", variable=self.source_var,
                        command=self._source_changed).pack(anchor="w")
        ttk.Radiobutton(gf, text="Kameradan hesap (Vision: piksel → konum)", value="kamera",
                        variable=self.source_var, command=self._source_changed).pack(anchor="w")
        ttk.Label(gf, text="Kameradan konumla gönderilen hız:").pack(anchor="w", pady=(6, 0))
        self.camvel_var = tk.StringVar(value=self.sim.camera_velocity)
        for key, label in (("yok", "Yok (PX4 konumlardan kestirir)"), ("kalman", "Kalman filtresi (konum + hız)"),
                           ("gercek", "Gerçek hız (üst sınır, karşılaştırma)")):
            ttk.Radiobutton(gf, text=label, value=key, variable=self.camvel_var,
                            command=self._camvel_changed).pack(anchor="w")
        self.band_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(gf, text="Mesafe bandı: hedefi görüntüde tut\n(FLW_TGT_DST uçuşta otomatik)",
                        variable=self.band_var, command=self._band_toggled).pack(anchor="w", pady=(4, 0))
        self.fix_vars = {}
        for key, label in (("fix", "Hesaplanan konum"), ("err", "Hata (gerçeğe göre)"), ("geom", "Bakış açısı / h"),
                           ("kf", "Kalman hızı / bant")):
            row = ttk.Frame(gf)
            row.pack(fill="x", pady=(2, 0))
            ttk.Label(row, text=label, foreground=MUTED, width=20).pack(side="left")
            var = tk.StringVar(value="—")
            ttk.Label(row, textvariable=var, style="Value.TLabel").pack(side="left")
            self.fix_vars[key] = var

        wf = ttk.LabelFrame(col, text="Wi-Fi / gecikme benzetimi", padding=8)
        wf.pack(fill="x", pady=(8, 0))
        ttk.Label(wf, text="FOLLOW_TARGET yolu (Vision işlem gecikmesi\nveya yerde işlem + Wi-Fi):",
                  foreground=MUTED, justify="left").pack(anchor="w")
        self.ft_delay = self._slider(wf, "Gecikme (ms)", 0, 2000, 50, self._ft_changed)
        self.ft_loss = self._slider(wf, "Kayıp (%)", 0, 90, 5, self._ft_changed)
        self.burst_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(wf, text="Kayıplar patlamalı (ort. 2 s'lik kesinti)", variable=self.burst_var,
                        command=self._ft_changed).pack(anchor="w")
        self.ft_stats = tk.StringVar(value="—")
        ttk.Label(wf, textvariable=self.ft_stats, style="Value.TLabel").pack(anchor="w", pady=(2, 6))
        ttk.Label(wf, text="Video yayını (RTP paketleri, QGC + pencere):", foreground=MUTED).pack(anchor="w")
        self.v_delay = self._slider(wf, "Gecikme (ms)", 0, 1000, 25, self._video_changed)
        self.v_loss = self._slider(wf, "Paket kaybı (%)", 0, 20, 0.5, self._video_changed)
        ttk.Button(wf, text="Sıfırla (kusursuz bağlantı)", command=self._wifi_reset).pack(anchor="w", pady=(4, 0))

    def _slider(self, parent, label, lo, hi, res, command):
        row = ttk.Frame(parent)
        row.pack(fill="x")
        ttk.Label(row, text=label, width=15).pack(side="left")
        var = tk.DoubleVar(value=0)
        tk.Scale(row, from_=lo, to=hi, resolution=res, orient="horizontal", variable=var,
                 command=lambda _v: command(), bg=BG, fg=FG, highlightthickness=0, troughcolor="#343b44",
                 length=170).pack(side="left")
        return var

    def _source_changed(self):
        src = self.source_var.get()
        self.sim.target_source = src
        if src == "kamera":
            self.sim.link._log("Konum kaynağı: KAMERA. FOLLOW_TARGET sadece hedef görünürken, pikselden hesaplanan "
                               "konumla gider (hız yok)")
            if not CAMERA_PITCH_DEG:
                self.sim.link._log("Kamera düz: 8 m'de hedef görünmez. Eğik kamera için: baslat.sh --egim 40")
        else:
            self.sim.link._log("Konum kaynağı: gerçek hedef konumu")

    def _ft_changed(self):
        ft = self.sim.ft_link
        ft.delay_s = self.ft_delay.get() / 1000.0
        ft.loss = self.ft_loss.get() / 100.0
        ft.burst = 20.0 if self.burst_var.get() else 1.0  # 20 messages at 10 Hz = 2 s

    def _video_changed(self):
        self.sim.set_video_impairment(self.v_delay.get(), self.v_loss.get() / 100.0)

    def _wifi_reset(self):
        for var in (self.ft_delay, self.ft_loss, self.v_delay, self.v_loss):
            var.set(0)
        self.burst_var.set(False)
        self._ft_changed()
        self._video_changed()
        self.sim.link._log("Wi-Fi benzetimi sıfırlandı")

    def _refresh_experiments(self):
        f = self.sim._fresh_fix(time.monotonic())
        v = self.fix_vars
        if f is None:
            v["fix"].set("— (hedef görünmüyor veya EKF bekleniyor)")
            v["err"].set("—")
            v["geom"].set("—")
        else:
            v["fix"].set(f"{f.lat:.7f}, {f.lon:.7f}")
            v["err"].set(f"{f.error_m:5.2f} m (K {f.error_ne[0]:+.2f}, D {f.error_ne[1]:+.2f})")
            v["geom"].set(f"{f.depression_deg:4.1f}° / {f.height:4.1f} m")
        est = self.sim.kalman.estimate(self.sim._sim_now)
        kf = f"{math.hypot(est[2], est[3]):4.1f} m/s" if est is not None else "—"
        band = f"DST {self.sim.band.dst:4.1f} m" if self.sim.band.enabled else "kapalı"
        v["kf"].set(f"{kf} / {band}")
        ft = self.sim.ft_link
        pct = 100.0 * ft.dropped / ft.submitted if ft.submitted else 0.0
        self.ft_stats.set(f"gönderilen {ft.submitted}, düşen {ft.dropped} (%{pct:.0f})")

    # ------------------------------------------------------------------ input
    KEYMAP = {"w": ("left", 0, 1), "s": ("left", 0, -1), "a": ("left", -1, 0), "d": ("left", 1, 0),
              "Up": ("right", 0, 1), "Down": ("right", 0, -1), "Left": ("right", -1, 0), "Right": ("right", 1, 0)}
    TARGET_KEYS = {"i": "ileri", "k": "geri", "j": "sol", "l": "sag"}

    def _key_down(self, event):
        key = event.keysym if event.keysym in self.KEYMAP else event.keysym.lower()
        self.pressed.add(key)
        self._apply_keys()

    def _key_up(self, event):
        key = event.keysym if event.keysym in self.KEYMAP else event.keysym.lower()
        self.pressed.discard(key)
        self._apply_keys()

    def _apply_keys(self):
        acc = {"left": [0, 0], "right": [0, 0]}
        for key in self.pressed:
            if key in self.KEYMAP:
                stick, dx, dy = self.KEYMAP[key]
                acc[stick][0] += dx
                acc[stick][1] += dy
        self.left.set_keys(*acc["left"])
        self.right.set_keys(*acc["right"])
        self.sim.target.keys = {self.TARGET_KEYS[k] for k in self.pressed if k in self.TARGET_KEYS}

    def _sticks_changed(self):
        s = self.sim.link.sticks
        s["yaw"], s["throttle"] = self.left.x, self.left.y
        s["roll"], s["pitch"] = self.right.x, self.right.y

    def _open_viewer(self):
        """Separate video window (can be moved to a second monitor), fed by video/goruntu_yayini.py on UDP 5601."""
        here = os.path.dirname(os.path.abspath(__file__))
        python = os.path.join(here, ".venv", "bin", "python")
        viewer = os.path.join(here, "video", "video_izleyici.py")
        if not os.path.exists(python):
            self.sim.link._log("Kamera penceresi için follow_sim/.venv (kur.sh) gerekli (OpenCV)")
            return
        subprocess.Popen([python, viewer], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         start_new_session=True)
        self.sim.link._log("Kamera penceresi açılıyor (F: tam ekran, Q: kapat)")

    def _camvel_changed(self):
        mode = self.camvel_var.get()
        self.sim.kalman.reset()
        self.sim.camera_velocity = mode
        self.sim.link._log({"yok": "Kamera konumu hızsız gidiyor (PX4 hızı kestirir)",
                            "kalman": "Kamera konumu Kalman filtresinden: konum + hız",
                            "gercek": "Kamera konumu + GERÇEK hedef hızı (karşılaştırma için üst sınır)"}[mode])

    def _band_toggled(self):
        if self.band_var.get():
            # same bands as deney.py: tilted camera keeps the middle half, a level camera the lower part
            self.sim.band.v_top, self.sim.band.v_bottom = (0.25, 0.75) if CAMERA_PITCH_DEG >= 20 else (0.6, 0.9)
            self.sim.band.start(FOLLOW_DEFAULTS["FLW_TGT_DST"])
            self.sim.link._log(f"Mesafe bandı AÇIK: hedef görüntünün %{self.sim.band.v_top * 100:.0f}–"
                               f"%{self.sim.band.v_bottom * 100:.0f} satırları arasında tutulur")
        else:
            self.sim.band.stop()
            self.sim.link.set_param("FLW_TGT_DST", float(FOLLOW_DEFAULTS["FLW_TGT_DST"]))
            self.sim.link._log("Mesafe bandı kapalı, FLW_TGT_DST varsayılana döndü")

    def _vision_toggled(self):
        on = self.vision_var.get()
        self.sim.vision_mode = on
        if on:
            self.sim.link._log("Vision modu AÇIK: FOLLOW_TARGET sadece hedef kamerada görünürken gönderiliyor")
            if not self.sim.target_seen:
                self.sim.link._log(f"Hedef şu an kamerada yok. 8 m yükseklikte düz kamera hedefi göremez; "
                                   f"'Takip yüksekliği {VISION_DEMO_HEIGHT_M:g} m' düğmesine bas")
        else:
            self.sim.link._log("Vision modu kapalı: hedef konumu her zaman gönderiliyor")

    def _vision_height(self):
        def run():
            self.sim.link.set_param("FLW_TGT_HT", float(VISION_DEMO_HEIGHT_M))
            self.sim.link._log(f"FLW_TGT_HT = {VISION_DEMO_HEIGHT_M:g} m (varsayılana dönmek: 'Varsayılan FLW param.')")
        import threading
        threading.Thread(target=run, daemon=True).start()

    def _velocity_toggled(self):
        on = self.vel_var.get()
        self.sim.send_target_velocity = on
        self.sim.link._log("FOLLOW_TARGET: konum + hız gönderiliyor" if on else
                           "FOLLOW_TARGET: sadece konum (hız = NaN); PX4 hızı konum değişiminden kestiriyor")

    def _defaults(self):
        import threading
        threading.Thread(target=self.sim.link.apply_follow_defaults, daemon=True).start()

    # ------------------------------------------------------------------ refresh
    def _refresh(self):
        st = self.sim.link.state
        if st.connected:
            alt = f"{st.rel_alt:.1f} m" if not math.isnan(st.rel_alt) else "—"
            self.status_var.set(f"● Bağlı   Mod: {st.mode}   {'ARMED' if st.armed else 'disarmed'}   İrtifa: {alt}")
        else:
            self.status_var.set("○ PX4 bekleniyor… (baslat.sh çalışıyor mu?)")

        g = self.sim.geometry
        v = self.geo_vars
        if g is not None:
            v["h"].set(f"{g.height:6.2f} m")
            v["theta"].set(f"{g.theta_deg:6.1f}°")
            v["slant"].set(f"{g.slant:6.2f} m")
            v["hdist"].set(f"{g.horizontal_dist:6.2f} m")
            v["nadir"].set(f"x = {g.nadir.x():7.2f}  y = {g.nadir.y():7.2f}  z = 0")
            v["hit"].set(f"x = {g.ground_hit.x():7.2f}  y = {g.ground_hit.y():7.2f}  z = 0")
            if g.pixel:
                where = "kadrajda" if g.in_frame else "KADRAJ DIŞI"
                v["pixel"].set(f"({g.pixel[0]:6.0f}, {g.pixel[1]:6.0f}) / {IMAGE_W}×{IMAGE_H}  {where}")
            else:
                v["pixel"].set("hedef kameranın arkasında")
        else:
            for var in v.values():
                var.set("— (drone modeli bekleniyor)")
        self._refresh_visibility()
        self._refresh_experiments()
        d = self.sim.gcs_distance
        if d is not None:
            state, color = (("menzil dışı!", "#ff5a5a") if d > LINK_RANGE_M else
                            ("sınıra yakın", "#ffc94d") if d > LINK_WARN_M else ("iyi", "#5ad17a"))
            v["gcs"].set(f"{d:6.1f} m / {LINK_RANGE_M:.0f} m  {state}")
            self.gcs_label.configure(foreground=color)
        if self.sim.target_gps:
            lat, lon, alt = self.sim.target_gps
            v["gps"].set(f"{lat:.7f}, {lon:.7f}  alt {alt:.1f} m")

        # Started by the PX4 hook: close together with PX4 (no heartbeat for a while after being connected).
        if AUTO_EXIT and st.last_heartbeat and time.monotonic() - st.last_heartbeat > 8.0:
            self._close()
            return

        msgs = st.messages
        if len(msgs) != self._log_count or (msgs and self._log_count == 50):
            self.log.delete("1.0", "end")
            self.log.insert("end", "\n".join(f"{t}  {m}" for t, m in msgs[-50:]))
            self.log.see("end")
            self._log_count = len(msgs)
        self.after(100, self._refresh)

    def _refresh_visibility(self):
        sim, now = self.sim, time.monotonic()
        src = f" ({sim.visibility_source})" if sim.visibility_source else ""
        if not (sim.vision_mode or sim.target_source == "kamera"):
            text, color = (f"{'görünüyor' if sim.target_seen else 'görünmüyor'}{src}; Vision modu kapalı, "
                           f"konum her zaman gönderiliyor", MUTED)
        elif sim.target_seen:
            text, color = f"görünüyor{src} → FOLLOW_TARGET gönderiliyor", "#5ad17a"
        elif sim.last_target_sent is None:
            text, color = "hiç görülmedi → PX4'e hedef bilgisi gitmedi, drone bekliyor", "#ff5a5a"
        else:
            lost = now - sim.last_target_sent
            if lost < PX4_TARGET_STALE_S:
                text, color = f"KAYIP {lost:4.1f} s → PX4 son hızla tahmin ediyor (3 s)", "#ffc94d"
            else:
                text, color = f"KAYIP {lost:4.1f} s → PX4 tahmini durdu, drone son noktada bekliyor", "#ff5a5a"
        self.geo_vars["vis"].set(text)
        self.vis_label.configure(foreground=color)

    def _close(self):
        self.sim.stop()
        self.destroy()


def main():
    lock = open(LOCK_FILE, "w")
    try:  # only one panel at a time (PX4 may be restarted while a panel is still open)
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        print("Follow Me paneli zaten açık.")
        return 0
    sim = FollowSim()
    sim.start()
    panel = Panel(sim)
    sim.link._log("Panel hazır. Sıra: 1) Kalk → 2) Follow Me. Varsayılanlar: " +
                  ", ".join(f"{k}={v}" for k, v in FOLLOW_DEFAULTS.items()))
    try:
        panel.mainloop()
    except KeyboardInterrupt:
        sim.stop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
