#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LM Studio Optimizer v4 - Reforged
=================================
- Scrollbar: kompletter Content-Bereich scrollt vertikal (Mausrad, Tasten, Touchpad)
- Zoombar: 65%-160% Zoom via Buttons, Slider, Strg+Mausrad, Strg+Plus/Minus/0
- Auto-Button: erkennt Aufloesung/DPI und passt Fenster + Zoom + Layout an
- Responsive: 2-spaltig auf breit, 1-spaltig gestapelt auf schmal
- Editierbar: alle Kern-Werte pro Profil tweakbar (mit Reset), inkl. VRAM-Schaetzung
- Nice2Have: Toasts, Statusbar mit Live-Sys, bessere Suche (Scrollbar, Browser-Link),
  Bericht als Fenster mit Speichern, Alle-JSON-Export, Shortcuts, Tooltips,
  einklappbare Sektionen, Config-Persistenz.
- Info-Dashboard (Strg+D): zentrale Ansicht mit Live-CPU/RAM/GPU/Disk,
  allen Profilen im Vergleich (VRAM-Ampel), Verlaufschart, CSV/Kopieren.

Design-Tokens (frontend-design-skill):
  Void #080816 / Console #121222 / Holo #1a1a30 / Signal #00d2ff / Warp #7b2ff7
  Amber #ff9500 / Go #00ff88 / Alert #ff2d95 / Text #e8e8f0 / Muted #A9A9C6 (AAA)
  Display: Segoe UI Bold / Body: Segoe UI / Data: Consolas
  Signatur: Signal-Bar (Gradient oben) + glowende aktive Pille + Holo-VRAM-Bar.
"""
import tkinter as tk
from tkinter import messagebox, filedialog
import psutil
import platform
import sys
import json
import os
import shutil
import subprocess
import threading
import webbrowser
from datetime import datetime

try:
    import requests
    HAS_REQ = True
except ImportError:
    HAS_REQ = False

# Windows DPI-Awareness (scharf auf HiDPI), ignorieren wenn nicht verfuegbar
try:
    import ctypes
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass
except Exception:
    pass

# ---------------------------------------------------------------- Tokens
BG = "#080816"        # Void
PANEL = "#121222"     # Console
PANEL2 = "#1a1a30"    # Holo-Deck
SIGNAL = "#00d2ff"    # Signal (primaer)
WARP = "#7b2ff7"      # Warp (sekundaer)
AMBER = "#ff9500"
GO = "#00ff88"
ALERT = "#ff2d95"
TEXT = "#e8e8f0"
MUTED = "#A9A9C6"   # AAA: >=7:1 auf PANEL/BG (war #8888a0, nur ~5:1)
MUTED_DIM = "#9A9AB5"  # mind. AA auf PANEL2, nur fuer große/dekorative Texte
DESC_FG = "#C6C6DA"    # AAA fuer Beschreibungen auf PANEL (war #999)
LINE = "#23233d"
FOCUS = "#00d2ff"      # sichtbarer Tastaturfokus (WCAG 2.4.7, 3:1 auf dunkel)

# ---------------------------------------------------------------- Daten (unveraendert, nur erweitert um Persistenz)
DEFAULTS = {
    "phys_batch": 512, "max_conc": 2,
    "unified_kv": True, "ctx_cp": 32,
    "keep_mem": False, "offload_kv": True,
    "spec": "OFF", "max_draft": 0, "min_draft": 0, "draft_p": 0.0,
    "rope_base": 0, "rope_scale": 0,
    "k_quant": "Q8_0", "v_quant": "Q8_0",
    "threads": 10, "batch": 512,
    "flash": True, "mmap": False,
}

TASKS = {
 "coding": {
    "icon": "[C]", "name": "Coding", "color": "#00d2ff",
    "desc": "Programmierung, Aider/Cline",
    "ctx": 32768, "layers": 24, "kv": "Q8_0",
    "tok": "20-28 tok/s", "vram": 7.5, "ram": 6.0, "stab": "Gut",
    "model": "Qwen2.5-Coder-14B-Instruct (Q4_K_M)",
    "search": "Qwen2.5-Coder-14B-Instruct-GGUF",
    "alts": ["Qwen3-Coder-30B-A3B (Q4_K_M)",
            "Devstral-Small-2-24B (Q4_K_M)",
            "DeepSeek-Coder-V2-Lite (Q4_K_M)"],
    "warn": "Nur Q4_K_M! Layer 24 max.",
    "ok": "Beste Balance fuer Code.",
    "spec": "OFF", "k_quant": "Q8_0", "v_quant": "Q8_0", "max_conc": 2
 },
 "unreal": {
    "icon": "[UE]", "name": "Unreal Engine", "color": "#ff2d95",
    "desc": "UE5 C++ und Blueprint",
    "ctx": 16384, "layers": 20, "kv": "Q8_0",
    "tok": "18-24 tok/s", "vram": 7.2, "ram": 8.0, "stab": "Gut",
    "model": "ue-expert-v2 (Qwen2.5-Coder-14B SFT)",
    "search": "ue-expert-v2-gguf",
    "alts": ["Qwen3.6-27B (Q4_K_M)",
            "Gemma-4-12B-it (Q4_K_M)",
            "DeepSeek-V4 (Q4_K_M)"],
    "warn": "Kontext auf 16k begrenzen.",
    "ok": "Speziell fuer UE5 feinabgestimmt.",
    "spec": "OFF", "k_quant": "Q8_0", "v_quant": "Q8_0"
 },
 "html": {
    "icon": "[H]", "name": "Single-File HTML", "color": "#00ff88",
    "desc": "HTML/CSS/JS in einer Datei",
    "ctx": 32768, "layers": 20, "kv": "Q8_0",
    "tok": "22-30 tok/s", "vram": 7.8, "ram": 10.0, "stab": "Gut",
    "model": "Qwen3-Coder-30B-A3B (Q4_K_M)",
    "search": "Qwen3-Coder-30B-A3B-Instruct-GGUF",
    "alts": ["Qwen2.5-Coder-14B (Q4_K_M)",
            "Codestral-22B-v0.1 (Q4_K_M)",
            "Phi-4-14B (Q4_K_M)"],
    "warn": "30B MoE: Layer auf 20. Batch 256.",
    "ok": "MoE = hohe Qualitaet, wenig VRAM.",
    "threads": 12, "batch": 256, "phys_batch": 256,
    "spec": "OFF", "k_quant": "Q8_0", "v_quant": "Q8_0", "max_conc": 2
 },
 "image": {
    "icon": "[I]", "name": "Bildgenerierung", "color": "#ff9500",
    "desc": "Prompt-Enhancement fuer Flux/SDXL",
    "ctx": 8192, "layers": 32, "kv": "Q8_0",
    "tok": "30-40 tok/s", "vram": 6.8, "ram": 3.0, "stab": "Sehr gut",
    "model": "Qwen3-VL-8B-Caption-it (Q8_0)",
    "search": "Qwen3-VL-8B-abliterated-caption-gguf",
    "alts": ["Qwen2.5-VL-7B-abliterated (Q5_K_M)",
            "Gemma-4-E4B-Uncensored (Q4_K_M)",
            "Flux-Prompt-Enhance (GGUF)"],
    "warn": "LM Studio generiert keine Bilder!",
    "ok": "Nutze fuer Prompt-Enhancement.",
    "threads": 8, "spec": "MTP", "max_draft": 8, "min_draft": 0, "draft_p": 0.7,
    "k_quant": "Q8_0", "v_quant": "Q8_0"
 },
 "audio": {
    "icon": "[A]", "name": "Audio Transkription", "color": "#7b2ff7",
    "desc": "Sprache zu Text, Meeting-Notizen",
    "ctx": 4096, "layers": 32, "kv": "Q8_0",
    "tok": "15x Echtzeit", "vram": 2.5, "ram": 1.0, "stab": "Exzellent",
    "model": "Whisper-Large-v3-Turbo",
    "search": "whisper-large-v3-turbo-gguf",
    "alts": ["S1-mini 600M", "Voxtral-Mini-3B", "Voxtral-Small-24B"],
    "warn": "In LM Studio als Audio-Modell laden!",
    "ok": "Min/Normal/Max zur Feinsteuerung.",
    "threads": 8, "batch": 256, "phys_batch": 256,
    "spec": "OFF", "k_quant": "Q8_0", "v_quant": "Q8_0",
    "levels": {
      "min": {"model": "S1-mini (600M)", "search": "S1-mini-gguf",
             "vram": 1.0, "speed": "50x Echtzeit", "desc": "Schnellste Variante",
             "ctx": 2048, "layers": 32, "kv": "Q4_0"},
      "normal": {"model": "Whisper-Large-v3-Turbo", "search": "whisper-large-v3-turbo-gguf",
                "vram": 2.5, "speed": "15x Echtzeit", "desc": "Beste Balance",
                "ctx": 4096, "layers": 32, "kv": "Q8_0"},
      "max": {"model": "Voxtral-Small-24B (Q4_K_M)", "search": "Voxtral-Small-24B-2507-gguf",
             "vram": 7.0, "speed": "5x Echtzeit", "desc": "Maximale Genauigkeit",
             "ctx": 8192, "layers": 24, "kv": "Q8_0"}
    }
 },
 "balanced": {
    "icon": "[B]", "name": "Allgemein", "color": "#3a7bd5",
    "desc": "Chat, Zusammenfassungen",
    "ctx": 16384, "layers": 32, "kv": "Q8_0",
    "tok": "30-35 tok/s", "vram": 7.2, "ram": 3.0, "stab": "Sehr gut",
    "model": "Qwen3.5-9B (Q4_K_M)", "search": "Qwen3.5-9B-GGUF",
    "alts": ["Gemma-4-12B-it (Q4_K_M)",
            "Mistral-Small-3.1-24B (Q4_K_M)",
            "Llama-4-Scout-17B (Q4_K_M)"],
    "warn": None, "ok": "Empfohlen fuer 90% aller Faelle.",
    "spec": "MTP", "max_draft": 6, "min_draft": 0, "draft_p": 0.7,
    "k_quant": "Q8_0", "v_quant": "Q8_0"
 },
 "long32k": {
    "icon": "[L]", "name": "Long Context 32k", "color": "#7b2ff7",
    "desc": "Dokumente, Codebasen",
    "ctx": 32768, "layers": 28, "kv": "Q8_0",
    "tok": "18-24 tok/s", "vram": 7.8, "ram": 6.0, "stab": "Gut",
    "model": "Qwen2.5-7B-Instruct (Q4_K_M)",
    "search": "Qwen2.5-7B-Instruct-GGUF",
    "alts": ["Llama-3.1-8B-Instruct (Q4_K_M)", "Qwen3.5-9B (Q4_K_M)"],
    "warn": "Nur 7B/8B Q4_K_M! Kein 14B.",
    "ok": "Erfuellt Minimum 30.000 Tokens.",
    "spec": "OFF", "k_quant": "Q8_0", "v_quant": "Q8_0", "max_conc": 2
 },
 "ultra64k": {
    "icon": "[U]", "name": "Ultra 64k", "color": "#ff9500",
    "desc": "Buecher, sehr lange Texte",
    "ctx": 65536, "layers": 20, "kv": "Q4_0",
    "tok": "10-15 tok/s", "vram": 7.9, "ram": 12.0, "stab": "Mittel",
    "model": "Qwen2.5-7B-Instruct (Q4_K_M)",
    "search": "Qwen2.5-7B-Instruct-GGUF",
    "alts": ["Llama-3.1-8B-Instruct (Q4_K_M)"],
    "warn": "Nur 7B/8B! RAM ca. 12 GB. Offload KV AUS.",
    "ok": "Fuer Buecher und lange Dokumente.",
    "threads": 12, "batch": 256, "phys_batch": 256,
    "offload_kv": False, "max_conc": 1,
    "spec": "OFF", "k_quant": "Q4_0", "v_quant": "Q4_0"
 }
}

for k, p in TASKS.items():
    for dk, dv in DEFAULTS.items():
        p.setdefault(dk, dv)

TOOLTIPS = {
    "Context Length": "Wie viel Text das Modell gleichzeitig sieht. Mehr = mehr VRAM/RAM.",
    "GPU Offload": "Wie viele Layer auf der GPU laufen. Rest auf CPU (langsamer).",
    "KV Cache Quantization": "Kompression des Zwischenspeichers. Q4_0 spart VRAM, Q8_0 ist genauer.",
    "Flash Attention": "Schnellerer Attention-Kernel. In LM Studio i.d.R. AN lassen.",
    "Physical Batch Size": "Rechen-Batch auf der GPU. 256 bei knappem VRAM, sonst 512.",
    "Evaluation Batch Size": "Prompt-Verarbeitung pro Schritt. Gleich wie Physical starten.",
    "CPU Thread Pool Size": "CPU-Threads fuers Offload. Faustregel: phys. Kerne minus 2.",
    "Max Concurrent": "Parallele Anfragen. 1 bei 64k, sonst 2.",
    "Unified KV Cache": "Geteilter KV-Speicher. AN lassen ausser bei Ultra-64k-Problemen.",
    "Context Checkpoints": "Speicher vs. Rechenzeit. 32 ist der sichere Standard.",
    "Try mmap()": "Memory-Mapping. Bei Q4_K_M oft AUS stabiler.",
    "Keep Model in Memory": "Modell nach Antwort im VRAM halten. AN nur bei viel VRAM.",
    "Offload KV to GPU": "KV-Cache auf GPU. Bei Ultra-64k AUS (RAM nutzen).",
    "Speculative Decoding": "MTP = Entwurfs-Tokens fuer Tempo. OFF = kompatibelste Option.",
    "Max Draft Tokens": "Max. Entwurfs-Tokens (MTP: 6-8).",
    "Min Draft Tokens": "Min. Entwurfs-Tokens, meist 0.",
    "Draft Probability": "Akzeptanz-Schwelle, meist 0.7 bei MTP.",
    "RoPE Frequency Base": "Positions-Encoding. Auto (=0) lassen ausser bei Long-Context-Tuning.",
    "RoPE Frequency Scale": "Skalierung fuer lange Kontexte. Auto (=0) lassen.",
    "K-Cache Quantization": "K-Anteil des KV-Cache. Q8_0 Standard, Q4_0 fuer 64k.",
    "V-Cache Quantization": "V-Anteil des KV-Cache. Wie K-Cache setzen.",
    "Seed": "Zufalls-Seed. -1 = zufaellig bei jedem Start.",
}

CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "lm_optimizer_config.json")

CTX_CHOICES = [2048, 4096, 8192, 16384, 32768, 65536, 131072]
BATCH_CHOICES = [128, 256, 512, 1024, 2048]
KV_CHOICES = ["Q8_0", "Q4_0", "Q5_K_M", "F16"]
SPEC_CHOICES = ["OFF", "MTP"]
BOOL_TXT = ["An", "Aus"]


def sysinfo():
    d = {}
    try:
        d["OS"] = "%s %s" % (platform.system(), platform.release())
    except Exception:
        d["OS"] = "?"
    try:
        d["CPU"] = "%d Kerne / %d Threads" % (
            psutil.cpu_count(logical=False) or 0,
            psutil.cpu_count(logical=True) or 0)
    except Exception:
        d["CPU"] = "?"
    try:
        m = psutil.virtual_memory()
        d["RAM"] = "%.1f GB (%.1f GB frei)" % (
            m.total / (1024.0 ** 3), m.available / (1024.0 ** 3))
    except Exception:
        d["RAM"] = "?"
    try:
        import GPUtil
        g = GPUtil.getGPUs()
        d["GPU"] = "%s (%d MB)" % (g[0].name, g[0].memoryTotal) if g else "Keine NVIDIA"
    except Exception:
        d["GPU"] = "GPUtil fehlt"
    d["Python"] = sys.version.split()[0]
    d["Zeit"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return d


def search_hf(q, limit, cb):
    def _r():
        if not HAS_REQ:
            cb([], "requests fehlt (pip install requests)")
            return
        try:
            r = requests.get(
                "https://huggingface.co/api/models",
                params={"search": q, "filter": "gguf", "sort": "downloads",
                        "direction": "-1", "limit": int(limit)}, timeout=10)
            if r.status_code == 200:
                out = [{"id": m.get("modelId", "?"),
                        "dl": m.get("downloads", 0),
                        "likes": m.get("likes", 0),
                        "upd": (m.get("lastModified", "") or "")[:10]}
                       for m in r.json()]
                cb(out, None)
            else:
                cb([], "HTTP %d" % r.status_code)
        except Exception as e:
            cb([], str(e))
    threading.Thread(target=_r, daemon=True).start()


def suggested_zoom(sw, sh):
    """Zoom-Vorschlag aus Bildschirmgroesse ( conservative, damit alles passt )."""
    try:
        if sw <= 1280 or sh <= 720:
            return 0.75
        if sw <= 1366 or sh <= 768:
            return 0.80
        if sw <= 1536 or sh <= 864:
            return 0.90
        if sw <= 1920 or sh <= 1080:
            return 1.00
        return 1.10
    except Exception:
        return 1.0


class Tooltip:
    """Minimaler Hover-Tooltip."""
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tip = None
        widget.bind("<Enter>", self._show, add="+")
        widget.bind("<Leave>", self._hide, add="+")

    def _show(self, _e=None):
        if not self.text or self.tip is not None:
            return
        try:
            x = self.widget.winfo_rootx() + 16
            y = self.widget.winfo_rooty() + 18
            self.tip = tk.Toplevel(self.widget)
            self.tip.wm_overrideredirect(True)
            self.tip.wm_geometry("+%d+%d" % (x, y))
            tk.Label(self.tip, text=self.text, font=("Segoe UI", 8),
                     bg="#23233d", fg="#e8e8f0", padx=8, pady=5,
                     wraplength=300, justify=tk.LEFT,
                     relief="solid", bd=1).pack()
        except Exception:
            self.tip = None

    def _hide(self, _e=None):
        try:
            if self.tip is not None:
                self.tip.destroy()
        except Exception:
            pass
        self.tip = None


class App:
    def __init__(self, root):
        self.root = root
        root.title("LM Studio Optimizer v4 - Reforged")
        root.configure(bg=BG)

        self.sysi = sysinfo()
        self.cur = "coding"
        self.alvl = "normal"
        self.zoom = 1.0
        self.view = "profile"    # "profile" oder "dashboard"
        self.overrides = {}      # key -> {feld: wert}
        self.collapsed = set()   # eingeklappte Sektions-Titel
        self._wraplabels = []    # (label, anteil)
        self._meters = []        # live-update refs
        self._dash_refs = {}     # dashboard live-widget refs
        self._dash_hist = {"cpu": [], "ram": []}
        self._live_paused = False  # AAA: Live-Bewegung pausierbar (WCAG 2.3)
        self._toast_after = None
        self._render_job = None
        self.stacked = False

        self._load_config()

        # Start-Geometrie: passt auf jeden Bildschirm, minsize bewusst klein
        sw, sh = self._screen()
        if not getattr(self, "_zoom_from_config", False):
            self.zoom = suggested_zoom(sw, sh)
        self.zoom = max(0.65, min(1.6, self.zoom))
        win_w = min(1280, max(780, sw - 40))
        win_h = min(920, max(560, sh - 80))
        root.geometry("%dx%d+%d+%d" % (win_w, win_h,
                                       max(0, (sw - win_w) // 2),
                                       max(0, (sh - win_h) // 2)))
        root.minsize(760, 540)

        self._build_shell()
        self._bind_shortcuts()
        self._switch(self.cur if self.cur in TASKS else "coding", save=False)
        self.root.after(2500, self._live_sys)

    # ------------------------------------------------- helpers: zoom/fonts
    def F(self, base, weight="normal", family="Segoe UI"):
        return (family, max(6, int(round(base * self.zoom))), weight)

    def FC(self, base, weight="bold"):
        return ("Consolas", max(6, int(round(base * self.zoom))), weight)

    def P(self, base):
        return max(1, int(round(base * self.zoom)))

    def _screen(self):
        try:
            return (self.root.winfo_screenwidth(),
                    self.root.winfo_screenheight())
        except Exception:
            return (1920, 1080)

    # ------------------------------------------------- persistenz
    def _load_config(self):
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    c = json.load(f)
                if c.get("cur") in TASKS:
                    self.cur = c["cur"]
                if c.get("alvl") in ("min", "normal", "max"):
                    self.alvl = c["alvl"]
                z = float(c.get("zoom", 0) or 0)
                if 0.65 <= z <= 1.6:
                    self.zoom = z
                    self._zoom_from_config = True
                if isinstance(c.get("overrides"), dict):
                    self.overrides = c["overrides"]
                if isinstance(c.get("collapsed"), list):
                    self.collapsed = set(c["collapsed"])
        except Exception:
            pass

    def _save_config(self):
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump({"cur": self.cur, "alvl": self.alvl,
                           "zoom": round(self.zoom, 2),
                           "overrides": self.overrides,
                           "collapsed": sorted(self.collapsed)},
                          f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    # ------------------------------------------------- shell (fixe bereiche)
    def _build_shell(self):
        # Signatur: duenner Signal-Gradient oben
        top = tk.Frame(self.root, bg=SIGNAL, height=3)
        top.pack(fill=tk.X)
        top.pack_propagate(False)
        # (zweite Linie in Warp fuer Verlauf-Anmutung)
        tk.Frame(self.root, bg=WARP, height=1).pack(fill=tk.X)

        # Header
        h = tk.Frame(self.root, bg=BG)
        h.pack(fill=tk.X, padx=self.P(16), pady=(self.P(8), 0))
        tk.Label(h, text="LM Studio Optimizer v4",
                 font=self.F(18, "bold"), bg=BG, fg=SIGNAL).pack(side=tk.LEFT)
        tk.Label(h, text="reforged \u00b7 scrollbar \u00b7 zoombar \u00b7 auto-fit",
                 font=self.F(9), bg=BG, fg=MUTED).pack(side=tk.LEFT, padx=(10, 0))
        self.sys_pill = tk.Label(h, text="", font=self.FC(8),
                                 bg=PANEL2, fg=MUTED, padx=8, pady=3)
        self.sys_pill.pack(side=tk.RIGHT)
        self._refresh_sys_pill()

        # Profil-Pillen (wrappen via grid, skalieren mit Zoom)
        self.tabframe = tk.Frame(self.root, bg=BG)
        self.tabframe.pack(fill=tk.X, padx=self.P(16), pady=(self.P(8), 0))
        self.btns = {}
        keys = list(TASKS.keys())
        cols = 4
        for i, k in enumerate(keys):
            p = TASKS[k]
            b = tk.Button(self.tabframe, text="%s %s" % (p["icon"], p["name"]),
                          font=self.F(9, "bold"), bg=PANEL, fg="#c0c0c0",
                          relief="flat", bd=0, padx=self.P(8), pady=self.P(7),
                          cursor="hand2", activebackground=p["color"],
                          activeforeground=BG,
                          highlightthickness=2, highlightbackground=BG,
                          highlightcolor=FOCUS,
                          command=lambda kk=k: self._switch(kk))
            b.grid(row=i // cols, column=i % cols, padx=3, pady=3, sticky="ew")
            for c in range(cols):
                self.tabframe.columnconfigure(c, weight=1)
            self.btns[k] = b
            Tooltip(b, "%s\n%s" % (p["name"], p["desc"]))

        # Zoom-/Werkzeugleiste
        tb = tk.Frame(self.root, bg=BG)
        tb.pack(fill=tk.X, padx=self.P(16), pady=(self.P(6), 0))
        tk.Label(tb, text="Zoom:", font=self.F(9, "bold"),
                 bg=BG, fg=MUTED).pack(side=tk.LEFT)
        self._mkbtn(tb, "\u2212", self.zoom_out, SIGNAL, BG,
                    tip="Verkleinern (Strg+Minus)").pack(side=tk.LEFT, padx=2)
        self.zoom_lbl = tk.Button(tb, text="100%", font=self.FC(9),
                                  bg=PANEL2, fg=TEXT, relief="flat", bd=0,
                                  padx=8, pady=3, cursor="hand2",
                                  command=self.zoom_reset)
        Tooltip(self.zoom_lbl, "Klick = auf 100% zuruecksetzen (Strg+0)")
        self.zoom_lbl.pack(side=tk.LEFT, padx=2)
        self._mkbtn(tb, "+", self.zoom_in, SIGNAL, BG,
                    tip="Vergroessern (Strg+Plus)").pack(side=tk.LEFT, padx=2)
        self.zoom_scale = tk.Scale(tb, from_=65, to=160, orient=tk.HORIZONTAL,
                                   showvalue=0, length=110, bg=BG, fg=MUTED,
                                   troughcolor=PANEL2, highlightthickness=0,
                                   bd=0, activebackground=SIGNAL,
                                   command=self._on_slider)
        self.zoom_scale.set(int(round(self.zoom * 100)))
        self.zoom_scale.pack(side=tk.LEFT, padx=(6, 2))
        Tooltip(self.zoom_scale, "Ziehen zum Zoomen (65%-160%)")

        self.auto_btn = tk.Button(tb, text="\u2726 Auto", font=self.F(9, "bold"),
                                  bg=WARP, fg="#ffffff", relief="flat", bd=0,
                                  padx=10, pady=4, cursor="hand2",
                                  activebackground=WARP, activeforeground="#ffffff",
                                  highlightthickness=2,
                                  highlightbackground=BG,
                                  highlightcolor=FOCUS,
                                  command=self.auto_fit)
        self.auto_btn.pack(side=tk.LEFT, padx=(8, 2))
        Tooltip(self.auto_btn, "Passt Fenster + Zoom + Layout an deine Aufloesung an")

        self.dash_btn = tk.Button(tb, text="\u2630 Dashboard",
                                  font=self.F(9, "bold"),
                                  bg="#1a3a4a", fg=SIGNAL, relief="flat", bd=0,
                                  padx=10, pady=4, cursor="hand2",
                                  activebackground="#1a3a4a",
                                  activeforeground=SIGNAL,
                                  highlightthickness=2,
                                  highlightbackground=BG,
                                  highlightcolor=FOCUS,
                                  command=self._toggle_dashboard)
        self.dash_btn.pack(side=tk.LEFT, padx=(2, 2))
        Tooltip(self.dash_btn, "Zentrales Info-Dashboard: alle Ressourcen live (Strg+D)")

        self.res_lbl = tk.Label(tb, text="", font=self.FC(8), bg=BG, fg=MUTED)
        self.res_lbl.pack(side=tk.LEFT, padx=(8, 0))
        self._refresh_res()

        # HF-Schnellsuche (lese-Reihenfolge HF: -> Feld -> Suchen;
        # bei side=RIGHT dafuer in umgekehrter Pack-Reihenfolge)
        self._hf_btn = self._mkbtn(
            tb, "Suchen", lambda: self._search(
                self.quick_q.get().strip() or None), AMBER, BG,
            tip="Hugging-Face-Suche (Strg+F)")
        self._hf_btn.pack(side=tk.RIGHT, padx=(4, 0))
        self.quick_q = tk.Entry(tb, font=self.FC(9), bg=PANEL2, fg=TEXT,
                                insertbackground=TEXT, relief="flat", width=22,
                                highlightthickness=2,
                                highlightbackground=PANEL2,
                                highlightcolor=FOCUS)
        self.quick_q.pack(side=tk.RIGHT, ipady=3)
        self.quick_q.bind("<Return>", lambda _e: self._search(
            self.quick_q.get().strip() or None))
        self._hf_label = tk.Label(tb, text="HF:", font=self.F(9, "bold"),
                                  bg=BG, fg=MUTED)
        self._hf_label.pack(side=tk.RIGHT, padx=(6, 2))
        Tooltip(self.quick_q, "Modellname fuer Hugging Face (Enter = suchen)")

        # Scroll-Bereich (Canvas + Scrollbar + Innen-Frame)
        outer = tk.Frame(self.root, bg=BG)
        outer.pack(fill=tk.BOTH, expand=True, padx=self.P(16), pady=self.P(8))
        self.canvas = tk.Canvas(outer, bg=BG, highlightthickness=0)
        self.vsb = tk.Scrollbar(outer, orient="vertical",
                                command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.vsb.set)
        self.vsb.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.inner = tk.Frame(self.canvas, bg=BG)
        self._win_id = self.canvas.create_window((0, 0), window=self.inner,
                                                 anchor="nw")
        self.inner.bind("<Configure>",
                        lambda _e: self.canvas.configure(
                            scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", self._on_canvas_configure)
        self._bind_wheel(self.canvas)
        self._bind_wheel(self.inner)

        # Footer (fix, scrollt NICHT mit)
        ff = tk.Frame(self.root, bg=BG)
        ff.pack(fill=tk.X, padx=self.P(16), pady=(0, self.P(6)))
        self._mkbtn(ff, "Werte kopieren", self._copy, SIGNAL, BG,
                    tip="Text-Block in Zwischenablage (Strg+C)").pack(
                        side=tk.LEFT, padx=2)
        self._mkbtn(ff, "JSON-Preset", self._json, WARP, "#ffffff",
                    tip="LM-Studio-Preset speichern (Strg+S)").pack(
                        side=tk.LEFT, padx=2)
        self._mkbtn(ff, "Alle JSON", self._json_all, "#2a2a4a", TEXT,
                    tip="Alle Profile in eine Datei exportieren").pack(
                        side=tk.LEFT, padx=2)
        self._mkbtn(ff, "Online-Suche", lambda: self._search(None),
                    AMBER, BG, tip="Modelle auf Hugging Face suchen").pack(
                        side=tk.LEFT, padx=2)
        self._mkbtn(ff, "Dashboard", self._toggle_dashboard, "#1a3a4a",
                    SIGNAL,
                    tip="Zentrales Info-Dashboard (Strg+D)").pack(
                        side=tk.LEFT, padx=2)
        self._mkbtn(ff, "Systembericht", self._report, GO, BG,
                    tip="System + alle Profile anzeigen/speichern").pack(
                        side=tk.LEFT, padx=2)
        self._mkbtn(ff, "Reset", self._reset_profile, "#3a1a1a", "#ff6b6b",
                    tip="Deine Aenderungen an diesem Profil verwerfen").pack(
                        side=tk.LEFT, padx=2)
        self._mkbtn(ff, "Beenden", self.root.quit, "#3a1a1a", "#ff6b6b",
                    tip="Programm schliessen").pack(side=tk.RIGHT, padx=2)

        # Statusbar
        sb = tk.Frame(self.root, bg=PANEL, height=26)
        sb.pack(fill=tk.X, side=tk.BOTTOM)
        sb.pack_propagate(False)
        self.st_left = tk.Label(sb, text="", font=self.FC(8), bg=PANEL,
                                fg=MUTED, anchor=tk.W)
        self.st_left.pack(side=tk.LEFT, padx=10)
        self.st_mid = tk.Label(sb, text="Bereit.", font=self.F(8),
                               bg=PANEL, fg=GO, anchor=tk.CENTER)
        self.st_mid.pack(side=tk.LEFT, expand=True)
        self.st_right = tk.Label(sb, text="", font=self.FC(8), bg=PANEL,
                                 fg=MUTED, anchor=tk.E)
        self.st_right.pack(side=tk.RIGHT, padx=10)

    def _mkbtn(self, parent, text, cmd, bg, fg, tip=None):
        # AAA: sichtbarer Fokus (2.4.7) + mind. ~24px Ziel (2.5.8)
        b = tk.Button(parent, text=text, command=cmd,
                      font=self.F(9, "bold"), bg=bg, fg=fg,
                      relief="flat", bd=0, padx=self.P(10), pady=self.P(5),
                      cursor="hand2", activebackground=bg,
                      activeforeground=fg, highlightthickness=2,
                      highlightbackground=BG, highlightcolor=FOCUS)
        if tip:
            Tooltip(b, tip)
        return b

    # ------------------------------------------------- shortcuts & wheel
    def _bind_shortcuts(self):
        r = self.root
        r.bind_all("<Control-plus>", lambda _e: self.zoom_in())
        r.bind_all("<Control-KP_Add>", lambda _e: self.zoom_in())
        r.bind_all("<Control-minus>", lambda _e: self.zoom_out())
        r.bind_all("<Control-KP_Subtract>", lambda _e: self.zoom_out())
        r.bind_all("<Control-0>", lambda _e: self.zoom_reset())
        r.bind_all("<Control-KP_0>", lambda _e: self.zoom_reset())
        r.bind_all("<Control-c>", lambda _e: self._copy())
        r.bind_all("<Control-s>", lambda _e: self._json())
        r.bind_all("<Control-f>", lambda _e: (self.quick_q.focus_set(),
                                              self.quick_q.select_range(0, tk.END)))
        r.bind_all("<Control-d>", lambda _e: self._toggle_dashboard())
        r.bind_all("<F9>", lambda _e: self._toggle_dashboard())
        r.bind_all("<Control-MouseWheel>", self._on_ctrl_wheel)
        r.bind_all("<Control-Button-4>", lambda _e: self.zoom_in())
        r.bind_all("<Control-Button-5>", lambda _e: self.zoom_out())
        # 1..8 = Profile
        for i, k in enumerate(TASKS.keys(), start=1):
            r.bind_all("<Alt-Key-%d>" % i, lambda _e, kk=k: self._switch(kk))
        # Scrollen mit Pfeilen/Bild-Tasten im Canvas
        self.canvas.bind("<Up>", lambda _e: self.canvas.yview_scroll(-1, "units"))
        self.canvas.bind("<Down>", lambda _e: self.canvas.yview_scroll(1, "units"))
        self.canvas.bind("<Prior>", lambda _e: self.canvas.yview_scroll(-1, "pages"))
        self.canvas.bind("<Next>", lambda _e: self.canvas.yview_scroll(1, "pages"))
        self.canvas.focus_set()

    def _bind_wheel(self, w):
        w.bind("<MouseWheel>", self._on_wheel, add="+")
        w.bind("<Button-4>", lambda e: self.canvas.yview_scroll(-1, "units"),
               add="+")
        w.bind("<Button-5>", lambda e: self.canvas.yview_scroll(1, "units"),
               add="+")
        for ch in w.winfo_children():
            try:
                self._bind_wheel(ch)
            except Exception:
                pass

    def _on_wheel(self, e):
        # Strg+Rad = Zoom, sonst Scrollen
        try:
            if (e.state & 0x4):
                if e.delta > 0:
                    self.zoom_in()
                elif e.delta < 0:
                    self.zoom_out()
                return "break"
            self.canvas.yview_scroll(-1 * (e.delta // 120), "units")
            return "break"
        except Exception:
            return None

    def _on_ctrl_wheel(self, e):
        try:
            if getattr(e, "delta", 0) >= 0:
                self.zoom_in()
            else:
                self.zoom_out()
        except Exception:
            pass
        return "break"

    # ------------------------------------------------- zoom & auto
    def set_zoom(self, z, save=True):
        z = max(0.65, min(1.6, round(float(z) * 20) / 20))
        if abs(z - self.zoom) < 1e-9:
            return
        self.zoom = z
        try:
            self.zoom_lbl.configure(text="%d%%" % int(round(z * 100)))
            self.zoom_scale.set(int(round(z * 100)))
        except Exception:
            pass
        self._refresh_res()
        if save:
            self._save_config()
        # Neu aufbauen (debounced, damit Slider-Ziehen nicht flackert)
        if self._render_job is not None:
            try:
                self.root.after_cancel(self._render_job)
            except Exception:
                pass
        self._render_job = self.root.after(120, self._rebuild_shell_text)

    def _rebuild_shell_text(self):
        self._render_job = None
        # fixe Shell-Texte neu skalieren: am einfachsten Shell neu bauen
        # (Canvas-Inhalt bleibt erhalten, wird danach neu gerendert)
        try:
            for w in (self.root.winfo_children()):
                pass
        except Exception:
            pass
        self._render()

    def zoom_in(self, _e=None):
        self.set_zoom(self.zoom + 0.10)

    def zoom_out(self, _e=None):
        self.set_zoom(self.zoom - 0.10)

    def zoom_reset(self, _e=None):
        self.set_zoom(1.0)
        self._toast("Zoom auf 100% zurueckgesetzt.")

    def _on_slider(self, val):
        try:
            self.set_zoom(int(float(val)) / 100.0)
        except Exception:
            pass

    def auto_fit(self):
        """AUTO-Knopf: Aufloesung erkennen, Fenster + Zoom + Layout anpassen."""
        sw, sh = self._screen()
        z = suggested_zoom(sw, sh)
        win_w = min(1280, max(780, sw - 40))
        win_h = min(920, max(560, sh - 80))
        self.zoom = max(0.65, min(1.6, z))
        try:
            self.zoom_lbl.configure(text="%d%%" % int(round(self.zoom * 100)))
            self.zoom_scale.set(int(round(self.zoom * 100)))
        except Exception:
            pass
        self.root.geometry("%dx%d+%d+%d" % (win_w, win_h,
                                            max(0, (sw - win_w) // 2),
                                            max(0, (sh - win_h) // 2)))
        self._refresh_res()
        self._save_config()
        self._render()
        self._toast("Auto: %dx%d erkannt \u2192 Zoom %d%%, Fenster %dx%d." % (
            sw, sh, int(round(self.zoom * 100)), win_w, win_h))

    def _refresh_res(self):
        try:
            sw, sh = self._screen()
            self.res_lbl.configure(
                text="%dx%d \u00b7 %d%%" % (sw, sh, int(round(self.zoom * 100))))
        except Exception:
            pass

    def _refresh_sys_pill(self):
        try:
            m = psutil.virtual_memory()
            self.sys_pill.configure(
                text="RAM %.0f GB frei \u00b7 CPU %d Threads" % (
                    m.available / (1024.0 ** 3),
                    psutil.cpu_count(logical=True) or 0))
        except Exception:
            self.sys_pill.configure(text="System OK")

    # ------------------------------------------------- daten: basis vs. effektiv
    def _ov_key(self):
        if self.cur == "audio":
            return "audio:%s" % self.alvl
        return self.cur

    def _base_act(self):
        p = TASKS[self.cur]
        if self.cur == "audio":
            i = p["levels"][self.alvl]
            s = dict(i)
            s.update({"batch": 256, "phys_batch": 256, "threads": 8,
                      "max_conc": 2, "unified_kv": True, "ctx_cp": 32,
                      "keep_mem": False, "offload_kv": True,
                      "spec": "OFF", "max_draft": 0, "min_draft": 0,
                      "draft_p": 0.0, "rope_base": 0, "rope_scale": 0,
                      "flash": True, "mmap": False,
                      "k_quant": i["kv"], "v_quant": i["kv"],
                      "kv": i["kv"], "tok": i["speed"], "ram": 2.0,
                      "stab": p["stab"],
                      "model": i["model"], "search": i["search"],
                      "desc": i["desc"],
                      "name": "%s-%s" % (p["name"], self.alvl)})
            return s
        return dict(p)

    def _act(self):
        s = self._base_act()
        ov = self.overrides.get(self._ov_key(), {})
        for k, v in ov.items():
            if k in s:
                s[k] = v
        return s

    def _is_edited(self):
        return bool(self.overrides.get(self._ov_key()))

    def estimate_vram(self, base, eff):
        """Heuristik: Kontext-Delta + Layer-Delta + KV-Art. Nur Schaetzung!"""
        try:
            v = float(base.get("vram", 7.0))
            ctx0 = int(base.get("ctx", 16384) or 16384)
            ctx1 = int(eff.get("ctx", ctx0) or ctx0)
            kv = str(eff.get("kv", eff.get("k_quant", "Q8_0")))
            per8k = 0.28 if "Q4" in kv else (0.42 if "Q5" in kv else 0.55)
            v += ((ctx1 - ctx0) / 8192.0) * per8k
            lay0 = int(base.get("layers", 24) or 24)
            lay1 = int(eff.get("layers", lay0) or lay0)
            v += (lay1 - lay0) * 0.06
            if not eff.get("offload_kv", True):
                v -= 0.4
            return max(0.5, round(v, 1))
        except Exception:
            return base.get("vram", 7.0)

    # ------------------------------------------------- navigation
    def _switch(self, k, save=True):
        self.cur = k
        self.view = "profile"
        for kk, b in self.btns.items():
            if kk == k:
                b.configure(bg=TASKS[kk]["color"], fg=BG)
            else:
                b.configure(bg=PANEL, fg="#c0c0c0")
        self._refresh_dash_btn()
        if save:
            self._save_config()
        self._render()
        try:
            self.canvas.yview_moveto(0.0)
        except Exception:
            pass

    def _setlvl(self, lv):
        self.alvl = lv
        self.view = "profile"
        self._save_config()
        self._refresh_dash_btn()
        self._render()

    def _refresh_dash_btn(self):
        try:
            if self.view == "dashboard":
                self.dash_btn.configure(bg=SIGNAL, fg=BG,
                                        activebackground=SIGNAL,
                                        activeforeground=BG)
            else:
                self.dash_btn.configure(bg="#1a3a4a", fg=SIGNAL,
                                        activebackground="#1a3a4a",
                                        activeforeground=SIGNAL)
        except Exception:
            pass

    def _toggle_dashboard(self):
        if self.view == "dashboard":
            self.view = "profile"
        else:
            self.view = "dashboard"
        self._refresh_dash_btn()
        self._render()
        try:
            self.canvas.yview_moveto(0.0)
        except Exception:
            pass

    def _show_dashboard(self):
        self.view = "dashboard"
        self._refresh_dash_btn()
        self._render()
        try:
            self.canvas.yview_moveto(0.0)
        except Exception:
            pass

    # ------------------------------------------------- render (scroll-inhalt)
    def _render(self):
        for w in self.inner.winfo_children():
            w.destroy()
        self._wraplabels = []
        self._meters = []
        self._dash_refs = {}
        self._refresh_dash_btn()

        if getattr(self, "view", "profile") == "dashboard":
            self._render_dashboard()
            return

        base = self._base_act()
        eff = self._act()
        p_color = TASKS[self.cur]["color"]

        # Kopf-Karte
        head = tk.Frame(self.inner, bg=PANEL, padx=self.P(16), pady=self.P(12))
        head.pack(fill=tk.X, padx=self.P(2), pady=(self.P(2), self.P(6)))
        title_row = tk.Frame(head, bg=PANEL)
        title_row.pack(fill=tk.X)
        tk.Label(title_row,
                 text="%s  %s" % (TASKS[self.cur]["icon"],
                                  eff.get("name", TASKS[self.cur]["name"])),
                 font=self.F(14, "bold"), bg=PANEL, fg=SIGNAL).pack(side=tk.LEFT)
        if self._is_edited():
            tk.Label(title_row, text="\u25cf bearbeitet",
                     font=self.F(8, "bold"), bg=PANEL, fg=AMBER).pack(
                         side=tk.LEFT, padx=(8, 0))
            tk.Button(title_row, text="Reset", font=self.F(8, "bold"),
                      bg="#3a1a1a", fg="#ff6b6b", relief="flat", bd=0,
                      padx=8, pady=2, cursor="hand2",
                      command=self._reset_profile).pack(side=tk.RIGHT)
        desc = tk.Label(head, text=TASKS[self.cur]["desc"],
                        font=self.F(9), bg=PANEL, fg="#C6C6DA",
                        justify=tk.LEFT, anchor=tk.W)
        desc.pack(anchor=tk.W, pady=(self.P(2), 0))
        self._wraplabels.append((desc, 0.90))

        # Spalten-Container (responsive: nebeneinander oder gestapelt)
        self.cols = tk.Frame(self.inner, bg=BG)
        self.cols.pack(fill=tk.BOTH, expand=True, padx=self.P(2))
        self._L = tk.Frame(self.cols, bg=PANEL, padx=self.P(16),
                           pady=self.P(14))
        self._R = tk.Frame(self.cols, bg=PANEL, padx=self.P(16),
                           pady=self.P(14))

        if self.cur == "audio":
            self._audio(self._L, eff)
        else:
            self._normal(self._L, eff)
        self._right(self._R, base, eff, p_color)

        self._apply_stack()
        self._update_wraps()
        self._update_status()
        self._bind_wheel(self.inner)
        try:
            self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        except Exception:
            pass

    def _apply_stack(self):
        try:
            w = self.canvas.winfo_width() or self.root.winfo_width()
        except Exception:
            w = 1200
        stacked = w < 900
        self.stacked = stacked
        if not hasattr(self, "_L") or not hasattr(self, "_R"):
            return
        try:
            if not self._L.winfo_exists() or not self._R.winfo_exists():
                return
        except Exception:
            return
        for wdg in (self._L, self._R):
            try:
                wdg.grid_forget()
                wdg.pack_forget()
            except Exception:
                pass
        if stacked:
            self.cols.columnconfigure(0, weight=1)
            try:
                self.cols.columnconfigure(1, weight=0)
            except Exception:
                pass
            self._L.grid(row=0, column=0, sticky="ew", pady=(0, self.P(6)))
            self._R.grid(row=1, column=0, sticky="ew")
        else:
            self.cols.columnconfigure(0, weight=3)
            self.cols.columnconfigure(1, weight=2)
            self._L.grid(row=0, column=0, sticky="nsew",
                         padx=(0, self.P(4)))
            self._R.grid(row=0, column=1, sticky="nsew",
                         padx=(self.P(4), 0))

    def _on_canvas_configure(self, e):
        try:
            self.canvas.itemconfig(self._win_id, width=e.width)
        except Exception:
            pass
        self._apply_stack()
        try:
            if getattr(self, "view", "profile") == "dashboard":
                self._layout_dash_grid()
        except Exception:
            pass
        self._update_wraps()
        try:
            self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        except Exception:
            pass

    def _update_wraps(self):
        try:
            w = self.canvas.winfo_width() or 1000
        except Exception:
            w = 1000
        col_w = (w - 40) if self.stacked else (w - 60) / 2
        for lbl, frac in self._wraplabels:
            try:
                if frac >= 0.9:
                    lbl.configure(wraplength=max(280, int(w * 0.88)))
                else:
                    lbl.configure(wraplength=max(240, int(col_w * 0.92)))
            except Exception:
                pass

    # ------------------------------------------------- linke karte
    def _section(self, parent, title):
        open_ = title not in self.collapsed
        hdr = tk.Frame(parent, bg=PANEL2, padx=self.P(10), pady=self.P(5))
        hdr.pack(fill=tk.X, pady=(self.P(8), self.P(2)))
        arrow = "\u25bc" if open_ else "\u25b6"
        btn = tk.Button(hdr, text="%s  %s" % (arrow, title),
                        font=self.F(9, "bold"), bg=PANEL2, fg=SIGNAL,
                        relief="flat", bd=0, anchor=tk.W, cursor="hand2",
                        activebackground=PANEL2, activeforeground=SIGNAL)
        btn.pack(fill=tk.X)
        body = tk.Frame(parent, bg=PANEL)
        if open_:
            body.pack(fill=tk.X)
        def _toggle(_e=None, t=title, b=body, bb=btn):
            if t in self.collapsed:
                self.collapsed.discard(t)
                b.pack(fill=tk.X)
                bb.configure(text="\u25bc  %s" % t)
            else:
                self.collapsed.add(t)
                b.pack_forget()
                bb.configure(text="\u25b6  %s" % t)
            self._save_config()
            try:
                self.canvas.configure(scrollregion=self.canvas.bbox("all"))
            except Exception:
                pass
        btn.configure(command=_toggle)
        return body

    def _normal(self, parent, eff):
        b = self._section(parent, "KERN-EINSTELLUNGEN")
        self._edit_rows(b, [
            ("Context Length", "ctx", "ctx", eff["ctx"]),
            ("GPU Offload", "layers", "layers", eff["layers"]),
            ("KV Cache Quantization", "kv", "kv", eff["kv"]),
            ("Flash Attention", "flash", "bool", eff["flash"]),
        ])
        b = self._section(parent, "PERFORMANCE")
        self._edit_rows(b, [
            ("Physical Batch Size", "phys_batch", "batch", eff["phys_batch"]),
            ("Evaluation Batch Size", "batch", "batch", eff["batch"]),
            ("CPU Thread Pool Size", "threads", "threads", eff["threads"]),
            ("Max Concurrent", "max_conc", "conc", eff["max_conc"]),
        ])
        b = self._section(parent, "SPEICHER-MANAGEMENT")
        self._edit_rows(b, [
            ("Unified KV Cache", "unified_kv", "bool", eff["unified_kv"]),
            ("Context Checkpoints", "ctx_cp", "ctxcp", eff["ctx_cp"]),
            ("Try mmap()", "mmap", "bool", eff["mmap"]),
            ("Keep Model in Memory", "keep_mem", "bool", eff["keep_mem"]),
            ("Offload KV to GPU", "offload_kv", "bool", eff["offload_kv"]),
        ])
        b = self._section(parent, "SPECULATIVE DECODING")
        self._edit_rows(b, [
            ("Speculative Decoding", "spec", "spec", eff["spec"]),
            ("Max Draft Tokens", "max_draft", "draft", eff["max_draft"]),
            ("Min Draft Tokens", "min_draft", "draft", eff["min_draft"]),
            ("Draft Probability", "draft_p", "prob", eff["draft_p"]),
        ])
        b = self._section(parent, "ERWEITERT")
        self._edit_rows(b, [
            ("RoPE Frequency Base", "rope_base", "rope", eff["rope_base"]),
            ("RoPE Frequency Scale", "rope_scale", "rope", eff["rope_scale"]),
            ("K-Cache Quantization", "k_quant", "kv", eff["k_quant"]),
            ("V-Cache Quantization", "v_quant", "kv", eff["v_quant"]),
            ("Seed", None, "static", "-1 (random)"),
        ])
        hint = tk.Label(parent,
                        text="Tipp: Werte sind klickbar/editierbar. Hover fuer Erklaerung. "
                             "Strg+Rad zoomt, \u2726 Auto passt alles an.",
                        font=self.F(8), bg=PANEL, fg=MUTED,
                        justify=tk.LEFT, anchor=tk.W)
        hint.pack(anchor=tk.W, pady=(self.P(8), 0))
        self._wraplabels.append((hint, 0.5))

    def _audio(self, parent, eff):
        tk.Label(parent, text="Genauigkeits-Stufe",
                 font=self.F(10, "bold"), bg=PANEL, fg=WARP).pack(anchor=tk.W)
        bf = tk.Frame(parent, bg=PANEL)
        bf.pack(fill=tk.X, pady=(self.P(4), self.P(8)))
        self.lbtns = {}
        for lv in ["min", "normal", "max"]:
            b = tk.Button(bf, text=lv.upper(), font=self.F(9, "bold"),
                          bg=PANEL2, fg="#c0c0c0", relief="flat", bd=0,
                          padx=self.P(10), pady=self.P(5), cursor="hand2",
                          highlightthickness=2, highlightbackground=PANEL,
                          highlightcolor=FOCUS,
                          command=lambda l=lv: self._setlvl(l))
            b.pack(side=tk.LEFT, padx=3)
            self.lbtns[lv] = b
        i = TASKS["audio"]["levels"][self.alvl]
        c = tk.Frame(parent, bg=PANEL2, padx=self.P(12), pady=self.P(10))
        c.pack(fill=tk.X, pady=(0, self.P(8)))
        cmap = {"min": GO, "normal": SIGNAL, "max": AMBER}
        tk.Label(c, text=i["model"], font=self.F(11, "bold"), bg=PANEL2,
                 fg=cmap[self.alvl]).pack(anchor=tk.W)
        d = tk.Label(c, text=i["desc"], font=self.F(9), bg=PANEL2,
                     fg="#c0c0c0")
        d.pack(anchor=tk.W, pady=(2, 4))
        tk.Label(c, text="VRAM: %.1f GB | %s" % (i["vram"], i["speed"]),
                 font=self.FC(9), bg=PANEL2, fg=TEXT).pack(anchor=tk.W)
        s = tk.Label(c, text="Suche: " + i["search"], font=self.FC(8),
                     bg=PANEL2, fg="#9A9AB5")
        s.pack(anchor=tk.W, pady=(4, 0))
        self._wraplabels.append((d, 0.5))
        self._upd_lbtns()

        b = self._section(parent, "KERN")
        self._edit_rows(b, [
            ("Context Length", "ctx", "ctx", eff["ctx"]),
            ("GPU Offload", "layers", "layers", eff["layers"]),
            ("KV Cache Quantization", "kv", "kv", eff["kv"]),
            ("Flash Attention", "flash", "bool", eff.get("flash", True)),
        ])
        b = self._section(parent, "PERFORMANCE")
        self._edit_rows(b, [
            ("Physical Batch Size", "phys_batch", "batch", eff["phys_batch"]),
            ("Evaluation Batch Size", "batch", "batch", eff["batch"]),
            ("CPU Thread Pool Size", "threads", "threads", eff["threads"]),
            ("Max Concurrent", "max_conc", "conc", eff["max_conc"]),
        ])
        b = self._section(parent, "SPEICHER")
        self._edit_rows(b, [
            ("Unified KV Cache", "unified_kv", "bool", eff["unified_kv"]),
            ("Context Checkpoints", "ctx_cp", "ctxcp", eff["ctx_cp"]),
            ("Try mmap()", "mmap", "bool", eff["mmap"]),
            ("Keep Model in Memory", "keep_mem", "bool", eff["keep_mem"]),
            ("Offload KV to GPU", "offload_kv", "bool", eff["offload_kv"]),
        ])
        b = self._section(parent, "ERWEITERT")
        self._edit_rows(b, [
            ("Speculative Decoding", "spec", "spec", eff["spec"]),
            ("K-Cache Quantization", "k_quant", "kv", eff["k_quant"]),
            ("V-Cache Quantization", "v_quant", "kv", eff["v_quant"]),
            ("Seed", None, "static", "-1 (random)"),
        ])

    # ------------------------------------------------- editierbare zeilen
    def _edit_rows(self, parent, rows):
        for label, key, kind, val in rows:
            r = tk.Frame(parent, bg=PANEL)
            r.pack(fill=tk.X, pady=2)
            lab = tk.Label(r, text=label, font=self.F(9), bg=PANEL,
                           fg=MUTED, anchor=tk.W)
            lab.pack(side=tk.LEFT, fill=tk.X, expand=True)
            if label in TOOLTIPS:
                Tooltip(lab, TOOLTIPS[label])
                Tooltip(r, TOOLTIPS[label])
            warn = self._is_warn(label, val)
            fg = GO if (warn and kind == "static") or (
                label == "Context Length") else (TEXT if not warn else AMBER)
            if kind == "static" or key is None:
                tk.Label(r, text=str(val), font=self.FC(10),
                         bg=PANEL, fg=fg).pack(side=tk.LEFT, padx=6)
                cb_btn = tk.Button(r, text="Copy", font=self.F(8),
                                   bg="#1a3a4a", fg=SIGNAL, relief="flat",
                                   bd=0, padx=8, pady=2, cursor="hand2",
                                   command=lambda vv=val: self._clip(vv))
                cb_btn.pack(side=tk.RIGHT)
            else:
                w = self._editor(r, key, kind, val)
                w.pack(side=tk.LEFT, padx=6)
                disp = self._disp(key, val, kind)
                tk.Button(r, text="Copy", font=self.F(8),
                          bg="#1a3a4a", fg=SIGNAL, relief="flat", bd=0,
                          padx=8, pady=2, cursor="hand2",
                          command=lambda k=key, kk=kind: self._clip(
                              self._disp(k, self._act().get(k), kk))).pack(
                                  side=tk.RIGHT)

    def _disp(self, key, val, kind):
        if kind == "bool":
            return "An" if val else "Aus"
        if key == "ctx":
            try:
                return "{:,}".format(int(val)).replace(",", ".")
            except Exception:
                return str(val)
        if key == "layers":
            return "%d Layer" % int(val)
        if key in ("rope_base", "rope_scale") and int(val or 0) == 0:
            return "Auto"
        return str(val)

    def _is_warn(self, label, val):
        if label == "Context Length":
            return True
        if label == "Max Concurrent":
            try:
                return int(val) >= 4
            except Exception:
                return False
        if label == "KV Cache Quantization":
            return val == "F16"
        if label == "Keep Model in Memory":
            return bool(val)
        return False

    def _editor(self, parent, key, kind, val):
        ovk = self._ov_key()
        if kind == "bool":
            var = tk.StringVar(value="An" if val else "Aus")
            om = tk.OptionMenu(parent, var, *BOOL_TXT)
            om.configure(font=self.F(9), bg=PANEL2, fg=TEXT,
                         relief="flat", bd=0, highlightthickness=0,
                         activebackground=PANEL2, activeforeground=TEXT)
            try:
                om["menu"].configure(bg=PANEL2, fg=TEXT, font=self.F(9))
            except Exception:
                pass
            def _cb(*_a, v=var, k=key, o=ovk):
                self._set_override(o, k, v.get() == "An")
            var.trace_add("write", _cb)
            return om
        if kind in ("ctx", "batch"):
            choices = CTX_CHOICES if kind == "ctx" else BATCH_CHOICES
            var = tk.StringVar(value=str(val))
            om = tk.OptionMenu(parent, var, *[str(c) for c in choices])
            om.configure(font=self.FC(9), bg=PANEL2, fg=TEXT,
                         relief="flat", bd=0, highlightthickness=0,
                         activebackground=PANEL2, activeforeground=TEXT)
            try:
                om["menu"].configure(bg=PANEL2, fg=TEXT, font=self.FC(9))
            except Exception:
                pass
            def _cb(*_a, v=var, k=key, o=ovk):
                try:
                    self._set_override(o, k, int(v.get()))
                except Exception:
                    pass
            var.trace_add("write", _cb)
            return om
        if kind == "kv":
            var = tk.StringVar(value=str(val))
            om = tk.OptionMenu(parent, var, *KV_CHOICES)
            om.configure(font=self.FC(9), bg=PANEL2, fg=TEXT,
                         relief="flat", bd=0, highlightthickness=0,
                         activebackground=PANEL2, activeforeground=TEXT)
            try:
                om["menu"].configure(bg=PANEL2, fg=TEXT, font=self.FC(9))
            except Exception:
                pass
            def _cb(*_a, v=var, k=key, o=ovk):
                self._set_override(o, k, v.get())
            var.trace_add("write", _cb)
            return om
        if kind == "spec":
            var = tk.StringVar(value=str(val))
            om = tk.OptionMenu(parent, var, *SPEC_CHOICES)
            om.configure(font=self.FC(9), bg=PANEL2, fg=TEXT,
                         relief="flat", bd=0, highlightthickness=0,
                         activebackground=PANEL2, activeforeground=TEXT)
            try:
                om["menu"].configure(bg=PANEL2, fg=TEXT, font=self.FC(9))
            except Exception:
                pass
            def _cb(*_a, v=var, k=key, o=ovk):
                self._set_override(o, k, v.get())
            var.trace_add("write", _cb)
            return om
        if kind in ("threads", "conc", "ctxcp", "draft", "rope"):
            lo, hi = {"threads": (1, 32), "conc": (1, 8),
                      "ctxcp": (8, 128), "draft": (0, 32),
                      "rope": (0, 100000)}.get(kind, (0, 64))
            var = tk.StringVar(value=str(val))
            sp = tk.Spinbox(parent, from_=lo, to=hi, textvariable=var,
                            width=8, font=self.FC(9), bg=PANEL2, fg=TEXT,
                            buttonbackground=PANEL2, relief="flat", bd=0,
                            insertbackground=TEXT)
            def _cb(*_a, v=var, k=key, o=ovk):
                try:
                    self._set_override(o, k, int(float(v.get())))
                except Exception:
                    pass
            var.trace_add("write", _cb)
            sp.bind("<FocusOut>", lambda _e, v=var, k=key, o=ovk: self._set_override(
                o, k, self._to_int(v.get(), self._base_act().get(k))))
            return sp
        if kind == "prob":
            var = tk.StringVar(value=str(val))
            sp = tk.Spinbox(parent, from_=0.0, to=1.0, increment=0.1,
                            textvariable=var, width=6, font=self.FC(9),
                            bg=PANEL2, fg=TEXT, buttonbackground=PANEL2,
                            relief="flat", bd=0, insertbackground=TEXT)
            def _cb(*_a, v=var, k=key, o=ovk):
                try:
                    self._set_override(o, k, round(float(v.get()), 2))
                except Exception:
                    pass
            var.trace_add("write", _cb)
            return sp
        lab = tk.Label(parent, text=str(val), font=self.FC(10),
                       bg=PANEL, fg=TEXT)
        return lab

    def _to_int(self, v, fb):
        try:
            return int(float(v))
        except Exception:
            return fb

    def _set_override(self, ovk, key, value):
        base = self._base_act().get(key, None)
        d = self.overrides.setdefault(ovk, {})
        if value == base:
            d.pop(key, None)
            if not d:
                self.overrides.pop(ovk, None)
        else:
            d[key] = value
        self._save_config()
        self._refresh_dynamic()

    def _refresh_dynamic(self):
        """Live: Meter + Status + Titel-Marker ohne Fokus-Verlust."""
        try:
            base = self._base_act()
            eff = self._act()
            for m in self._meters:
                try:
                    m["redraw"](base, eff)
                except Exception:
                    pass
            self._update_status()
        except Exception:
            pass

    def _reset_profile(self):
        k = self._ov_key()
        if k in self.overrides:
            self.overrides.pop(k, None)
            self._save_config()
            self._render()
            self._toast("Profil zurueckgesetzt (Standardwerte).")
        else:
            self._toast("Nichts zu resetten - bereits Standard.")

    def _upd_lbtns(self):
        cmap = {"min": GO, "normal": SIGNAL, "max": AMBER}
        for lv, b in getattr(self, "lbtns", {}).items():
            if lv == self.alvl:
                b.configure(bg=cmap[lv], fg=BG)
            else:
                b.configure(bg=PANEL2, fg="#c0c0c0")

    # ------------------------------------------------- rechte karte
    def _right(self, R, base, eff, color):
        tk.Label(R, text="Leistung und Modelle", font=self.F(14, "bold"),
                 bg=PANEL, fg=SIGNAL).pack(anchor=tk.W, pady=(0, self.P(8)))
        est = self.estimate_vram(base, eff)
        vram_txt = "%.1f GB / 8.0 GB" % est
        if self._is_edited() and abs(est - float(base.get("vram", 0))) > 0.05:
            vram_txt += "  (Basis %.1f)" % float(base.get("vram", 0))
        self._meter(R, "VRAM (8 GB)", vram_txt, est / 8.0, "vram")
        ram_v = float(eff.get("ram", base.get("ram", 3.0)) or 3.0)
        # RAM-Schaetzung folgt Kontext leicht
        try:
            ram_v = round(float(base.get("ram", 3.0)) * (
                int(eff.get("ctx", 0)) / max(1, int(base.get("ctx", 1)))), 1)
            ram_v = max(0.5, min(28.0, ram_v))
        except Exception:
            pass
        self._meter(R, "RAM (32 GB)", "%.1f GB / 32.0 GB" % ram_v,
                    ram_v / 32.0, "ram")

        for l, v in [("Tempo", eff.get("tok", base.get("tok", "?"))),
                     ("Stabilitaet", eff.get("stab", base.get("stab", "?"))),
                     ("Kontext", "{:,}".format(int(eff.get("ctx", 0))).replace(
                         ",", "."))]:
            r = tk.Frame(R, bg=PANEL)
            r.pack(fill=tk.X, pady=2)
            tk.Label(r, text=l + ":", font=self.F(9), bg=PANEL,
                     fg=MUTED, width=14, anchor=tk.W).pack(side=tk.LEFT)
            tk.Label(r, text=v, font=self.FC(10),
                     bg=PANEL, fg=TEXT).pack(side=tk.LEFT)

        tk.Label(R, text="Empfohlenes Modell:", font=self.F(9, "bold"),
                 bg=PANEL, fg=SIGNAL).pack(anchor=tk.W, pady=(self.P(8), 2))
        ml = tk.Label(R, text=eff.get("model", ""), font=self.F(9),
                      bg=PANEL, fg=TEXT, justify=tk.LEFT, anchor=tk.W)
        ml.pack(anchor=tk.W)
        self._wraplabels.append((ml, 0.45))
        sl = tk.Label(R, text="Suche: " + str(eff.get("search", "")),
                      font=self.FC(8), bg=PANEL, fg="#9A9AB5",
                      justify=tk.LEFT, anchor=tk.W)
        sl.pack(anchor=tk.W, pady=(2, self.P(6)))
        self._wraplabels.append((sl, 0.45))

        row = tk.Frame(R, bg=PANEL)
        row.pack(fill=tk.X, pady=(0, self.P(4)))
        tk.Button(row, text="Modell kopieren", font=self.F(8, "bold"),
                  bg="#1a3a4a", fg=SIGNAL, relief="flat", bd=0,
                  padx=8, pady=3, cursor="hand2",
                  command=lambda: self._clip(eff.get("model", ""))).pack(
                      side=tk.LEFT, padx=(0, 4))
        tk.Button(row, text="HF oeffnen", font=self.F(8, "bold"),
                  bg="#1a3a4a", fg=SIGNAL, relief="flat", bd=0,
                  padx=8, pady=3, cursor="hand2",
                  command=lambda: webbrowser.open(
                      "https://huggingface.co/search?fullText=1&search=" + str(
                          eff.get("search", "")))).pack(side=tk.LEFT)

        tk.Label(R, text="Alternativen:", font=self.F(9, "bold"),
                 bg=PANEL, fg=AMBER).pack(anchor=tk.W, pady=(self.P(4), 2))
        for a in TASKS[self.cur].get("alts", []):
            al = tk.Label(R, text="  \u2022  " + a, font=self.F(8),
                          bg=PANEL, fg="#c0c0c0", justify=tk.LEFT,
                          anchor=tk.W)
            al.pack(anchor=tk.W)
            self._wraplabels.append((al, 0.45))
            Tooltip(al, "Klicken zum Kopieren")
            al.bind("<Button-1>", lambda _e, v=a: self._clip(v))

        if TASKS[self.cur].get("warn"):
            w = tk.Frame(R, bg="#3a1a1a", padx=self.P(10), pady=self.P(8))
            w.pack(fill=tk.X, pady=(self.P(8), 0))
            tk.Label(w, text="WARNUNG", font=self.F(9, "bold"),
                     bg="#3a1a1a", fg="#ff6b6b").pack(anchor=tk.W)
            wl = tk.Label(w, text=TASKS[self.cur]["warn"], font=self.F(9),
                          bg="#3a1a1a", fg="#ffbbbb", justify=tk.LEFT,
                          anchor=tk.W)
            wl.pack(anchor=tk.W, pady=(2, 0))
            self._wraplabels.append((wl, 0.45))
        if TASKS[self.cur].get("ok"):
            w = tk.Frame(R, bg="#0f2a1a", padx=self.P(10), pady=self.P(8))
            w.pack(fill=tk.X, pady=(self.P(6), 0))
            tk.Label(w, text="EMPFEHLUNG", font=self.F(9, "bold"),
                     bg="#0f2a1a", fg=GO).pack(anchor=tk.W)
            ol = tk.Label(w, text=TASKS[self.cur]["ok"], font=self.F(9),
                          bg="#0f2a1a", fg="#aaffcc", justify=tk.LEFT,
                          anchor=tk.W)
            ol.pack(anchor=tk.W, pady=(2, 0))
            self._wraplabels.append((ol, 0.45))

    def _meter(self, parent, label, value, frac, kind):
        f = tk.Frame(parent, bg=PANEL)
        f.pack(fill=tk.X, pady=(self.P(4), 0))
        t = tk.Frame(f, bg=PANEL)
        t.pack(fill=tk.X)
        tk.Label(t, text=label, font=self.F(9), bg=PANEL,
                 fg="#c0c0c0").pack(side=tk.LEFT)
        vlab = tk.Label(t, text=value, font=self.F(9, "bold"), bg=PANEL,
                        fg=TEXT)
        vlab.pack(side=tk.RIGHT)
        cv = tk.Canvas(f, height=self.P(10), bg=PANEL2,
                       highlightthickness=0)
        cv.pack(fill=tk.X, pady=(4, self.P(6)))

        state = {"frac": frac, "value": value}

        def draw(base=None, eff=None):
            if base is not None and eff is not None:
                if kind == "vram":
                    est = self.estimate_vram(base, eff)
                    state["frac"] = est / 8.0
                    txt = "%.1f GB / 8.0 GB" % est
                    if self._is_edited():
                        txt += "  (Basis %.1f)" % float(base.get("vram", 0))
                    state["value"] = txt
                elif kind == "ram":
                    try:
                        rv = round(float(base.get("ram", 3.0)) * (
                            int(eff.get("ctx", 0)) / max(
                                1, int(base.get("ctx", 1)))), 1)
                        rv = max(0.5, min(28.0, rv))
                    except Exception:
                        rv = base.get("ram", 3.0)
                    state["frac"] = rv / 32.0
                    state["value"] = "%.1f GB / 32.0 GB" % rv
                try:
                    vlab.configure(text=state["value"])
                except Exception:
                    pass
            try:
                cv.delete("all")
                w = cv.winfo_width() or 300
                h = self.P(10)
                cv.create_rectangle(0, 0, w, h, fill=PANEL2, outline="")
                fr = max(0.0, min(1.0, state["frac"]))
                col = SIGNAL if fr < 0.85 else ("#ffc107" if fr < 0.95
                                                else "#ff4444")
                # Holo-Segmente: 20 Bloecke
                segs = 20
                lit = int(round(fr * segs))
                gap = 2
                swd = (w - gap * (segs - 1)) / segs
                for i in range(segs):
                    x0 = i * (swd + gap)
                    x1 = x0 + swd
                    cv.create_rectangle(x0, 0, x1, h,
                                        fill=(col if i < lit else "#26263d"),
                                        outline="")
            except Exception:
                pass

        cv.bind("<Configure>", lambda _e: draw())
        self.root.after(50, draw)
        self._meters.append({"redraw": draw})

    # ================================================ INFO-DASHBOARD
    def _live_resources(self):
        """Zentrale Momentaufnahme aller genutzten Ressourcen."""
        r = {}
        try:
            r["cpu_pct"] = float(psutil.cpu_percent(interval=None))
        except Exception:
            r["cpu_pct"] = 0.0
        try:
            r["cpu_log"] = psutil.cpu_count(logical=True) or 0
            r["cpu_phys"] = psutil.cpu_count(logical=False) or 0
        except Exception:
            r["cpu_log"] = r["cpu_phys"] = 0
        try:
            fq = psutil.cpu_freq()
            r["cpu_freq"] = int(fq.current) if fq and fq.current else 0
        except Exception:
            r["cpu_freq"] = 0
        try:
            m = psutil.virtual_memory()
            r["ram_total"] = m.total / (1024.0 ** 3)
            r["ram_used"] = (m.total - m.available) / (1024.0 ** 3)
            r["ram_free"] = m.available / (1024.0 ** 3)
            r["ram_pct"] = float(m.percent)
        except Exception:
            r["ram_total"] = r["ram_used"] = r["ram_free"] = 0.0
            r["ram_pct"] = 0.0
        try:
            du = shutil.disk_usage(os.path.abspath(os.sep))
            r["disk_total"] = du.total / (1024.0 ** 3)
            r["disk_used"] = du.used / (1024.0 ** 3)
            r["disk_free"] = du.free / (1024.0 ** 3)
            r["disk_pct"] = (du.used / max(1, du.total)) * 100.0
            r["disk_path"] = os.path.abspath(os.sep)
        except Exception:
            r["disk_total"] = r["disk_used"] = r["disk_free"] = 0.0
            r["disk_pct"] = 0.0
            r["disk_path"] = "?"
        try:
            pr = psutil.Process(os.getpid())
            r["app_mb"] = pr.memory_info().rss / (1024.0 ** 2)
        except Exception:
            r["app_mb"] = 0.0
        r["gpu"] = self._gpu_snapshot()
        return r

    def _gpu_snapshot(self):
        """GPU-Info: GPUtil > nvidia-smi > Hinweis. Nie crashen."""
        try:
            import GPUtil
            g = GPUtil.getGPUs()
            if g:
                gg = g[0]
                try:
                    return {"name": gg.name,
                            "mem_total": float(gg.memoryTotal),
                            "mem_used": float(gg.memoryUsed),
                            "load": float(gg.load),
                            "src": "GPUtil"}
                except Exception:
                    pass
        except Exception:
            pass
        try:
            if shutil.which("nvidia-smi"):
                out = subprocess.check_output(
                    ["nvidia-smi",
                     "--query-gpu=name,memory.total,memory.used,utilization.gpu",
                     "--format=csv,noheader,nounits"],
                    stderr=subprocess.STDOUT, timeout=4).decode(
                        "utf-8", "replace").strip().splitlines()
                if out:
                    parts = [p.strip() for p in out[0].split(",")]
                    if len(parts) >= 4:
                        return {"name": parts[0],
                                "mem_total": float(parts[1]),
                                "mem_used": float(parts[2]),
                                "load": float(parts[3]) / 100.0,
                                "src": "nvidia-smi"}
        except Exception:
            pass
        return {"name": self.sysi.get("GPU", "Keine GPU-Daten"),
                "mem_total": 0.0, "mem_used": 0.0, "load": 0.0,
                "src": "none"}

    def _eff_for(self, key, alvl=None):
        """Effektive Werte fuer beliebiges Profil (inkl. Overrides)."""
        if key == "audio":
            lv = alvl or self.alvl
            i = TASKS["audio"]["levels"][lv]
            s = dict(i)
            s.update({"batch": 256, "phys_batch": 256, "threads": 8,
                      "max_conc": 2, "unified_kv": True, "ctx_cp": 32,
                      "keep_mem": False, "offload_kv": True,
                      "spec": "OFF", "max_draft": 0, "min_draft": 0,
                      "draft_p": 0.0, "rope_base": 0, "rope_scale": 0,
                      "flash": True, "mmap": False,
                      "k_quant": i["kv"], "v_quant": i["kv"],
                      "kv": i["kv"], "tok": i["speed"], "ram": 2.0,
                      "stab": TASKS["audio"]["stab"],
                      "model": i["model"], "search": i["search"],
                      "desc": i["desc"],
                      "name": "Audio-%s" % lv})
            base_ctx, base_lay, base_vram = i["ctx"], i["layers"], i["vram"]
            base = {"ctx": base_ctx, "layers": base_lay, "vram": base_vram,
                    "kv": i["kv"], "offload_kv": True}
            ov = self.overrides.get("audio:%s" % lv, {})
            for k, v in ov.items():
                if k in s:
                    s[k] = v
            est = self.estimate_vram(base, {"ctx": s["ctx"],
                                            "layers": s["layers"],
                                            "kv": s.get("kv", i["kv"]),
                                            "offload_kv": s.get(
                                                "offload_kv", True)})
            return {"key": "audio:%s" % lv, "tab": "audio",
                    "label": "Audio %s" % lv.upper(),
                    "icon": TASKS["audio"]["icon"],
                    "color": TASKS["audio"]["color"],
                    "vram": est, "ram": 2.0, "ctx": s["ctx"],
                    "layers": s["layers"], "tok": i["speed"],
                    "stab": TASKS["audio"]["stab"],
                    "edited": bool(ov), "model": s["model"]}
        p = TASKS[key]
        s = dict(p)
        ov = self.overrides.get(key, {})
        for k, v in ov.items():
            if k in s:
                s[k] = v
        est = self.estimate_vram(p, s)
        try:
            ram_v = round(float(p.get("ram", 3.0)) * (
                int(s.get("ctx", 0)) / max(1, int(p.get("ctx", 1)))), 1)
        except Exception:
            ram_v = p.get("ram", 3.0)
        return {"key": key, "tab": key,
                "label": p["name"], "icon": p["icon"], "color": p["color"],
                "vram": est, "ram": ram_v, "ctx": s.get("ctx", 0),
                "layers": s.get("layers", 0),
                "tok": s.get("tok", "?"), "stab": s.get("stab", "?"),
                "edited": bool(ov), "model": s.get("model", "")}

    def _dashboard_rows(self):
        rows = []
        for k in TASKS.keys():
            if k == "audio":
                for lv in ("min", "normal", "max"):
                    rows.append(self._eff_for("audio", lv))
            else:
                rows.append(self._eff_for(k))
        return rows

    def _dash_card(self, parent, title, accent):
        card = tk.Frame(parent, bg=PANEL, padx=self.P(14), pady=self.P(10))
        tk.Label(card, text=title, font=self.F(9, "bold"),
                 bg=PANEL, fg=accent).pack(anchor=tk.W)
        return card

    def _dash_bar(self, parent, frac, color):
        cv = tk.Canvas(parent, height=self.P(10), bg=PANEL2,
                       highlightthickness=0)
        cv.pack(fill=tk.X, pady=(self.P(4), 0))
        state = {"frac": max(0.0, min(1.0, frac)), "color": color}

        def draw(fr=None):
            if fr is not None:
                state["frac"] = max(0.0, min(1.0, fr))
            try:
                cv.delete("all")
                w = cv.winfo_width() or 200
                h = self.P(10)
                segs, gap = 20, 2
                swd = (w - gap * (segs - 1)) / segs
                lit = int(round(state["frac"] * segs))
                for i in range(segs):
                    x0 = i * (swd + gap)
                    cv.create_rectangle(x0, 0, x0 + swd, h,
                                        fill=(state["color"] if i < lit
                                              else "#26263d"), outline="")
            except Exception:
                pass
        cv.bind("<Configure>", lambda _e: draw())
        self.root.after(40, draw)
        return cv, draw

    def _render_dashboard(self):
        res = self._live_resources()
        rows = self._dashboard_rows()
        sw, sh = self._screen()

        head = tk.Frame(self.inner, bg=PANEL, padx=self.P(16),
                        pady=self.P(12))
        head.pack(fill=tk.X, padx=self.P(2), pady=(self.P(2), self.P(6)))
        tr = tk.Frame(head, bg=PANEL)
        tr.pack(fill=tk.X)
        tk.Label(tr, text="\u2630  Info-Dashboard",
                 font=self.F(14, "bold"), bg=PANEL, fg=SIGNAL).pack(
                     side=tk.LEFT)
        tk.Label(tr, text="%d Profile \u00b7 %d bearbeitet" % (
            len(rows), sum(1 for r in rows if r["edited"])),
            font=self.F(8, "bold"), bg=PANEL, fg=AMBER).pack(
                side=tk.LEFT, padx=(10, 0))
        desc = tk.Label(head,
                        text="Zentrale Ansicht: Live-System (CPU/RAM/GPU/Disk), "
                             "alle Profile mit VRAM/RAM/Kontext im Vergleich, "
                             "plus Verlauf der letzten Minuten. Klick oder "
                             "Enter auf einer Zeile springt direkt ins Profil.",
                        font=self.F(9), bg=PANEL, fg="#C6C6DA",
                        justify=tk.LEFT, anchor=tk.W)
        desc.pack(anchor=tk.W, pady=(self.P(2), self.P(6)))
        self._wraplabels.append((desc, 0.90))
        brow = tk.Frame(head, bg=PANEL)
        brow.pack(fill=tk.X)
        for txt, fn, bg, fg in [
                ("\u27f3 Aktualisieren", self._dash_refresh, PANEL2, TEXT),
                ("CSV exportieren", self._dashboard_csv, "#1a3a4a", SIGNAL),
                ("Kopieren", self._dashboard_copy, "#1a3a4a", SIGNAL),
                ("\u2190 Zurueck zum Profil", self._toggle_dashboard,
                 SIGNAL, BG)]:
            tk.Button(brow, text=txt, command=fn, font=self.F(9, "bold"),
                      bg=bg, fg=fg, relief="flat", bd=0,
                      padx=self.P(10), pady=self.P(5),
                      cursor="hand2", activebackground=bg,
                      activeforeground=fg, highlightthickness=2,
                      highlightbackground=PANEL,
                      highlightcolor=FOCUS).pack(side=tk.LEFT, padx=2,
                                                 pady=2)
        # AAA: Live-Aktualisierung pausierbar (Bewegung/Timing, WCAG 2.2/2.3)
        self._pause_btn = tk.Button(
            brow, text="\u23f8 Pause" if not self._live_paused
            else "\u25b6 Live",
            command=self._toggle_live_pause, font=self.F(9, "bold"),
            bg="#3a2a1a" if not self._live_paused else "#0f2a1a",
            fg=AMBER if not self._live_paused else GO,
            relief="flat", bd=0, padx=self.P(10), pady=self.P(5),
            cursor="hand2", highlightthickness=2,
            highlightbackground=PANEL, highlightcolor=FOCUS)
        self._pause_btn.pack(side=tk.LEFT, padx=2, pady=2)
        Tooltip(self._pause_btn, "Live-Aktualisierung anhalten/fortsetzen")

        # ---- Live-Karten (responsives Grid)
        sec = tk.Label(self.inner, text="LIVE-SYSTEM (aktualisiert alle 3 s)",
                       font=self.F(9, "bold"), bg=BG, fg=SIGNAL)
        sec.pack(anchor=tk.W, padx=self.P(4), pady=(self.P(6), self.P(2)))
        grid = tk.Frame(self.inner, bg=BG)
        grid.pack(fill=tk.X, padx=self.P(2))
        self._dash_grid = grid
        self._dash_cards = []

        c1 = self._dash_card(grid, "CPU", SIGNAL)
        self._dash_refs["cpu_big"] = tk.Label(
            c1, text="%.0f %%" % res["cpu_pct"], font=self.F(20, "bold"),
            bg=PANEL, fg=TEXT)
        self._dash_refs["cpu_big"].pack(anchor=tk.W)
        self._dash_refs["cpu_sub"] = tk.Label(
            c1, text="%d Kerne / %d Threads \u00b7 %d MHz" % (
                res["cpu_phys"], res["cpu_log"], res["cpu_freq"]),
            font=self.FC(8), bg=PANEL, fg=MUTED)
        self._dash_refs["cpu_sub"].pack(anchor=tk.W)
        _, d1 = self._dash_bar(c1, res["cpu_pct"] / 100.0, SIGNAL)
        self._dash_refs["cpu_bar"] = d1
        self._dash_cards.append(c1)

        c2 = self._dash_card(grid, "RAM", GO)
        self._dash_refs["ram_big"] = tk.Label(
            c2, text="%.1f / %.1f GB" % (res["ram_used"], res["ram_total"]),
            font=self.F(20, "bold"), bg=PANEL, fg=TEXT)
        self._dash_refs["ram_big"].pack(anchor=tk.W)
        self._dash_refs["ram_sub"] = tk.Label(
            c2, text="%.1f GB frei \u00b7 %.0f %% belegt" % (
                res["ram_free"], res["ram_pct"]),
            font=self.FC(8), bg=PANEL, fg=MUTED)
        self._dash_refs["ram_sub"].pack(anchor=tk.W)
        _, d2 = self._dash_bar(c2, res["ram_pct"] / 100.0, GO)
        self._dash_refs["ram_bar"] = d2
        self._dash_cards.append(c2)

        g = res["gpu"]
        c3 = self._dash_card(grid, "GPU (%s)" % g.get("src", "?"), WARP)
        if g.get("mem_total"):
            big = "%.1f / %.1f GB" % (g["mem_used"] / 1024.0,
                                      g["mem_total"] / 1024.0)
            sub = "%s \u00b7 Last %.0f %%" % (g["name"][:34],
                                              g["load"] * 100.0)
            fr = g["mem_used"] / max(1.0, g["mem_total"])
        else:
            big = "n/a"
            sub = g["name"][:44]
            fr = 0.0
        self._dash_refs["gpu_big"] = tk.Label(c3, text=big,
                                              font=self.F(20, "bold"),
                                              bg=PANEL, fg=TEXT)
        self._dash_refs["gpu_big"].pack(anchor=tk.W)
        gl = tk.Label(c3, text=sub, font=self.FC(8), bg=PANEL, fg=MUTED,
                      justify=tk.LEFT, anchor=tk.W)
        gl.pack(anchor=tk.W)
        self._wraplabels.append((gl, 0.30))
        _, d3 = self._dash_bar(c3, fr, WARP)
        self._dash_refs["gpu_bar"] = d3
        self._dash_cards.append(c3)

        c4 = self._dash_card(grid, "DISK (%s)" % res["disk_path"], AMBER)
        self._dash_refs["disk_big"] = tk.Label(
            c4, text="%.0f / %.0f GB" % (res["disk_used"], res["disk_total"]),
            font=self.F(20, "bold"), bg=PANEL, fg=TEXT)
        self._dash_refs["disk_big"].pack(anchor=tk.W)
        self._dash_refs["disk_sub"] = tk.Label(
            c4, text="%.0f GB frei \u00b7 %.0f %% belegt" % (
                res["disk_free"], res["disk_pct"]),
            font=self.FC(8), bg=PANEL, fg=MUTED)
        self._dash_refs["disk_sub"].pack(anchor=tk.W)
        _, d4 = self._dash_bar(c4, res["disk_pct"] / 100.0, AMBER)
        self._dash_refs["disk_bar"] = d4
        self._dash_cards.append(c4)

        c5 = self._dash_card(grid, "APP & FENSTER", SIGNAL)
        tk.Label(c5, text="%.0f MB" % res["app_mb"],
                 font=self.F(20, "bold"), bg=PANEL, fg=TEXT).pack(anchor=tk.W)
        al = tk.Label(c5, text="Screen %dx%d \u00b7 Zoom %d %% \u00b7 %s" % (
            sw, sh, int(round(self.zoom * 100)), CONFIG_FILE),
            font=self.FC(8), bg=PANEL, fg=MUTED, justify=tk.LEFT,
            anchor=tk.W)
        al.pack(anchor=tk.W)
        self._wraplabels.append((al, 0.30))
        tk.Label(c5, text="Config: %d Override(s)" % len(self.overrides),
                 font=self.FC(8), bg=PANEL, fg=MUTED).pack(anchor=tk.W)
        self._dash_cards.append(c5)

        c6 = self._dash_card(grid, "VERLAUF (CPU/RAM %)", GO)
        hist_cv = tk.Canvas(c6, height=self.P(52), bg=PANEL2,
                            highlightthickness=0)
        hist_cv.pack(fill=tk.X, pady=(self.P(4), 0))
        self._dash_refs["hist_cv"] = hist_cv
        # Text-Alternative zum Canvas (WCAG 1.1.1): aktuelle Werte als Satz
        self._dash_refs["hist_sum"] = tk.Label(
            c6, text="CPU %.0f %%, RAM %.0f %%." % (
                res["cpu_pct"], res["ram_pct"]),
            font=self.F(8, "bold"), bg=PANEL, fg=TEXT)
        self._dash_refs["hist_sum"].pack(anchor=tk.W, pady=(self.P(2), 0))
        tk.Label(c6, text="Linie hell = CPU, gruen = RAM (letzte ~2 Min.). "
                          "Achse: oben 100 %, unten 0 %.",
                 font=self.F(8), bg=PANEL, fg=MUTED).pack(anchor=tk.W)
        self._dash_cards.append(c6)
        self._layout_dash_grid()

        # ---- Profil-Vergleich (AAA: echte Buttons = Tastatur + Fokus;
        # Balken in eigener Zeile, damit Text nie ueberlagert wird)
        sec2 = tk.Label(self.inner, text="ALLE PROFILE IM VERGLEICH "
                                         "(Klick oder Enter = oeffnen, "
                                         "* = bearbeitet)",
                        font=self.F(9, "bold"), bg=BG, fg=SIGNAL)
        sec2.pack(anchor=tk.W, padx=self.P(4),
                  pady=(self.P(10), self.P(2)))
        tbl = tk.Frame(self.inner, bg=PANEL, padx=self.P(10),
                       pady=self.P(8))
        tbl.pack(fill=tk.X, padx=self.P(2))
        headers = ["Profil", "VRAM/8G", "RAM", "Ctx", "Lay", "Tempo",
                   "Stab", ""]
        for ci, hh in enumerate(headers):
            anchor = tk.E if ci in (1, 2, 3, 4) else tk.W
            tk.Label(tbl, text=hh, font=self.F(8, "bold"), bg=PANEL,
                     fg=MUTED, anchor=anchor).grid(
                         row=0, column=ci, sticky=anchor,
                         padx=4, pady=(0, 4))
        for idx, r in enumerate(rows):
            lr, br = 1 + idx * 2, 2 + idx * 2
            bgc = PANEL2 if r["tab"] == self.cur else PANEL
            fgname = r["color"] if r["tab"] == self.cur else TEXT
            name = "%s %s%s" % (r["icon"], r["label"],
                                "*" if r["edited"] else "")
            # Status als Symbol + Zahl (nie Farbe allein, WCAG 1.4.1)
            if r["vram"] >= 7.9:
                sym, scol = "\u2715", "#ff6b6b"   # kritisch
            elif r["vram"] >= 7.4:
                sym, scol = "!", "#ffc107"        # grenzwertig
            else:
                sym, scol = "\u2713", SIGNAL       # passt
            nb = tk.Button(
                tbl, text=name, font=self.F(8, "bold"), bg=bgc,
                fg=fgname, relief="flat", bd=0, anchor=tk.W,
                cursor="hand2", activebackground=LINE,
                activeforeground=fgname, padx=4, pady=4,
                highlightthickness=2, highlightbackground=bgc,
                highlightcolor=FOCUS,
                command=lambda rk=r["key"]: self._open_dash_row(rk))
            nb.grid(row=lr, column=0, sticky="ew", padx=2, pady=2)
            Tooltip(nb, "%s\n%s\nKlick oder Enter zum Oeffnen" % (
                r["label"], r["model"]))
            vlab = tk.Label(tbl, text="%s %.1f" % (sym, r["vram"]),
                            font=self.FC(8, "bold"), bg=bgc, fg=scol,
                            anchor=tk.E)
            vlab.grid(row=lr, column=1, sticky=tk.E, padx=4, pady=2)
            Tooltip(vlab, "VRAM-Schaetzung: %s (%.1f von 8 GB)" % (
                ("kritisch" if sym == "\u2715" else (
                    "grenzwertig" if sym == "!" else "passt")), r["vram"]))
            rlab = tk.Label(tbl, text="%.1f" % r["ram"],
                            font=self.FC(8), bg=bgc, fg=TEXT, anchor=tk.E)
            rlab.grid(row=lr, column=2, sticky=tk.E, padx=4, pady=2)
            clab = tk.Label(tbl, text="%dk" % int(round(r["ctx"] / 1024)),
                            font=self.FC(8), bg=bgc, fg=TEXT, anchor=tk.E)
            clab.grid(row=lr, column=3, sticky=tk.E, padx=4, pady=2)
            llab = tk.Label(tbl, text=str(r["layers"]),
                            font=self.FC(8), bg=bgc, fg=TEXT, anchor=tk.E)
            llab.grid(row=lr, column=4, sticky=tk.E, padx=4, pady=2)
            tlab = tk.Label(tbl, text=r["tok"][:12],
                            font=self.FC(8), bg=bgc, fg=TEXT, anchor=tk.W)
            tlab.grid(row=lr, column=5, sticky=tk.W, padx=4, pady=2)
            slab = tk.Label(tbl, text=r["stab"][:9],
                            font=self.FC(8), bg=bgc, fg=TEXT, anchor=tk.W)
            slab.grid(row=lr, column=6, sticky=tk.W, padx=4, pady=2)
            ob = tk.Button(
                tbl, text="\u25b6", font=self.F(8, "bold"), bg=bgc,
                fg=MUTED, relief="flat", bd=0, width=3, cursor="hand2",
                activebackground=LINE, activeforeground=TEXT,
                highlightthickness=2, highlightbackground=bgc,
                highlightcolor=FOCUS, pady=4,
                command=lambda rk=r["key"]: self._open_dash_row(rk))
            ob.grid(row=lr, column=7, padx=2, pady=2)
            Tooltip(ob, "Profil %s oeffnen" % r["label"])
            # Hover: ganze Zeile aufhellen (alle Zellen)
            _cells = (nb, vlab, rlab, clab, llab, tlab, slab, ob)

            def _enter(_e, cells=_cells):
                for cc in cells:
                    try:
                        cc.configure(bg=LINE, highlightbackground=LINE)
                    except Exception:
                        pass

            def _leave(_e, cells=_cells, b=bgc):
                for cc in cells:
                    try:
                        cc.configure(bg=b, highlightbackground=b)
                    except Exception:
                        pass
            for cc in _cells:
                cc.bind("<Enter>", _enter, add="+")
                cc.bind("<Leave>", _leave, add="+")
            # VRAM-Balken in EIGENER Zeile (Bugfix: lag auf dem Text)
            bar = tk.Canvas(tbl, height=self.P(5), bg=bgc,
                            highlightthickness=0)
            bar.grid(row=br, column=0, columnspan=8, sticky="ew",
                     padx=4, pady=(0, 6))
            fr = r["vram"] / 8.0
            col = (SIGNAL if fr < 0.9 else (
                "#ffc107" if fr < 0.99 else "#ff4444"))

            def _paint(_e=None, b=bar, f=fr, c=col):
                try:
                    b.delete("all")
                    w = b.winfo_width() or 400
                    b.create_rectangle(0, 0, w, self.P(5), fill="#26263d",
                                       outline="")
                    b.create_rectangle(0, 0, int(w * min(1.0, f)),
                                       self.P(5), fill=c, outline="")
                except Exception:
                    pass
            bar.bind("<Configure>", _paint)
            self.root.after(60, _paint)
        tbl.columnconfigure(0, weight=1, minsize=140)
        tbl.columnconfigure(1, weight=0, minsize=70)
        tbl.columnconfigure(2, weight=0, minsize=56)
        tbl.columnconfigure(3, weight=0, minsize=56)
        tbl.columnconfigure(4, weight=0, minsize=44)
        tbl.columnconfigure(5, weight=0, minsize=110)
        tbl.columnconfigure(6, weight=0, minsize=70)
        tbl.columnconfigure(7, weight=0, minsize=40)
        hint = tk.Label(
            self.inner,
            text="Legende (Symbol + Zahl, nicht Farbe allein): \u2713 < 7.4 GB "
                 "= passt, ! 7.4-7.8 = grenzwertig, \u2715 >= 7.9 = kritisch "
                 "bei 8-GB-Karten.",
            font=self.F(8), bg=BG, fg=MUTED, justify=tk.LEFT, anchor=tk.W)
        hint.pack(anchor=tk.W, padx=self.P(4), pady=(self.P(2), 0))
        self._wraplabels.append((hint, 0.90))

        # ---- Top-Verbraucher Hinweis
        top = sorted(rows, key=lambda r: r["vram"], reverse=True)[:3]
        box = tk.Frame(self.inner, bg="#0f2a1a", padx=self.P(12),
                       pady=self.P(10))
        box.pack(fill=tk.X, padx=self.P(2), pady=(self.P(8), 0))
        tk.Label(box, text="EINORDNUNG", font=self.F(9, "bold"),
                 bg="#0f2a1a", fg=GO).pack(anchor=tk.W)
        txt = ("Hoechster VRAM: %s (%.1f GB). " % (top[0]["label"],
                                                   top[0]["vram"]) if top
               else "")
        txt += ("Niedrigster: %s (%.1f GB). " % (sorted(
            rows, key=lambda r: r["vram"])[0]["label"], sorted(
                rows, key=lambda r: r["vram"])[0]["vram"]) if rows else "")
        txt += "Fuer 90 %% der Faelle: Allgemein-Profil. 64k nur mit 7B/8B."
        bl = tk.Label(box, text=txt, font=self.F(9), bg="#0f2a1a",
                      fg="#aaffcc", justify=tk.LEFT, anchor=tk.W)
        bl.pack(anchor=tk.W, pady=(2, 0))
        self._wraplabels.append((bl, 0.90))

        self._update_status()
        self._draw_dash_hist()
        self._bind_wheel(self.inner)
        try:
            self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        except Exception:
            pass

    def _layout_dash_grid(self):
        g = getattr(self, "_dash_grid", None)
        cards = getattr(self, "_dash_cards", [])
        if g is None or not cards:
            return
        try:
            w = self.canvas.winfo_width() or 1000
        except Exception:
            w = 1000
        ncols = 3 if w >= 1050 else (2 if w >= 700 else 1)
        for c in cards:
            try:
                c.grid_forget()
            except Exception:
                pass
        for i, c in enumerate(cards):
            c.grid(row=i // ncols, column=i % ncols, sticky="nsew",
                   padx=3, pady=3)
        for ci in range(ncols):
            try:
                g.columnconfigure(ci, weight=1)
            except Exception:
                pass

    def _draw_dash_hist(self):
        cv = self._dash_refs.get("hist_cv")
        if cv is None:
            return
        try:
            if not cv.winfo_exists():
                return
            cv.delete("all")
            w = cv.winfo_width() or 220
            h = self.P(52)
            cv.create_rectangle(0, 0, w, h, fill="#1a1a30", outline="")
            for frac in (0.25, 0.5, 0.75):
                y = h - int(h * frac)
                cv.create_line(0, y, w, y, fill="#26263d")
            try:
                cv.create_text(6, 8, text="100", fill="#A9A9C6",
                               font=("Segoe UI", 7), anchor=tk.W)
                cv.create_text(6, h - 8, text="0", fill="#A9A9C6",
                               font=("Segoe UI", 7), anchor=tk.W)
            except Exception:
                pass
            def _line(vals, color):
                if len(vals) < 2:
                    return
                step = w / max(1, 39)
                pts = []
                for i, v in enumerate(vals[-40:]):
                    x = w - (len(vals[-40:]) - 1 - i) * step
                    y = h - int((max(0.0, min(100.0, v)) / 100.0) * (h - 4)) - 2
                    pts += [x, y]
                if len(pts) >= 4:
                    cv.create_line(*pts, fill=color, width=2)
            _line(self._dash_hist.get("cpu", []), SIGNAL)
            _line(self._dash_hist.get("ram", []), GO)
        except Exception:
            pass

    def _open_dash_row(self, rkey):
        """Sprung aus Dashboard-Tabelle ins passende Profil/Level."""
        try:
            if rkey.startswith("audio:"):
                self.alvl = rkey.split(":", 1)[1]
                self._switch("audio")
            else:
                self._switch(rkey)
        except Exception:
            pass

    def _toggle_live_pause(self):
        self._live_paused = not self._live_paused
        try:
            self._pause_btn.configure(
                text="\u23f8 Pause" if not self._live_paused
                else "\u25b6 Live",
                bg="#3a2a1a" if not self._live_paused else "#0f2a1a",
                fg=AMBER if not self._live_paused else GO)
        except Exception:
            pass
        self._toast("Live-Aktualisierung pausiert. Wiederholen: Live."
                    if self._live_paused else
                    "Live-Aktualisierung laeuft (alle 3 s).")

    def _dash_refresh(self):
        self._render()
        self._toast("Dashboard aktualisiert.")

    def _dashboard_text(self):
        res = self._live_resources()
        rows = self._dashboard_rows()
        sw, sh = self._screen()
        t = "=== INFO-DASHBOARD (%s) ===\n" % datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S")
        t += "Screen: %dx%d, Zoom: %d%%, App-RAM: %.0f MB\n" % (
            sw, sh, int(round(self.zoom * 100)), res["app_mb"])
        t += ("CPU: %.0f%% (%d Kerne/%d Threads, %d MHz)\n" % (
            res["cpu_pct"], res["cpu_phys"], res["cpu_log"],
            res["cpu_freq"]))
        t += ("RAM: %.1f/%.1f GB benutzt (%.1f frei, %.0f%%)\n" % (
            res["ram_used"], res["ram_total"], res["ram_free"],
            res["ram_pct"]))
        g = res["gpu"]
        if g.get("mem_total"):
            t += "GPU [%s]: %s %.0f/%.0f MB, Last %.0f%%\n" % (
                g["src"], g["name"], g["mem_used"], g["mem_total"],
                g["load"] * 100.0)
        else:
            t += "GPU: %s\n" % g["name"]
        t += ("Disk %s: %.0f/%.0f GB (%.0f frei)\n\n" % (
            res["disk_path"], res["disk_used"], res["disk_total"],
            res["disk_free"]))
        t += "--- Alle Profile (effektiv, * = bearbeitet) ---\n"
        for r in rows:
            t += "%s%-16s VRAM %4.1f  RAM %4.1f  ctx %6d  lay %2d  %s\n" % (
                "*" if r["edited"] else " ", r["label"], r["vram"],
                r["ram"], r["ctx"], r["layers"], r["model"][:60])
        return t

    def _dashboard_copy(self):
        self._clip(self._dashboard_text())

    def _dashboard_csv(self):
        rows = self._dashboard_rows()
        fp = filedialog.asksaveasfilename(
            defaultextension=".csv", filetypes=[("CSV", "*.csv")],
            initialfile="lm_optimizer_dashboard.csv")
        if not fp:
            return
        try:
            import csv
            with open(fp, "w", newline="", encoding="utf-8") as f:
                wr = csv.writer(f, delimiter=";")
                wr.writerow(["Profil", "VRAM_GB", "RAM_GB", "Ctx",
                             "Layer", "Tempo", "Stab", "Bearbeitet",
                             "Modell"])
                for r in rows:
                    wr.writerow([r["label"], "%.1f" % r["vram"],
                                 "%.1f" % r["ram"], r["ctx"], r["layers"],
                                 r["tok"], r["stab"],
                                 "ja" if r["edited"] else "nein",
                                 r["model"]])
            self._toast("CSV gespeichert: %s" % os.path.basename(fp))
        except Exception as e:
            messagebox.showerror("Fehler", str(e))

    # ------------------------------------------------- status & toast
    def _update_status(self):
        try:
            if getattr(self, "view", "profile") == "dashboard":
                self.st_left.configure(text="\u2630 Dashboard \u00b7 alle Ressourcen")
                return
            eff = self._act()
            self.st_left.configure(
                text="%s %s \u00b7 %s" % (TASKS[self.cur]["icon"],
                                          TASKS[self.cur]["name"],
                                          eff.get("model", "")[:52]))
        except Exception:
            pass

    def _toast(self, msg, ok=True):
        try:
            self.st_mid.configure(text=msg, fg=GO if ok else AMBER)
            if self._toast_after is not None:
                try:
                    self.root.after_cancel(self._toast_after)
                except Exception:
                    pass
            self._toast_after = self.root.after(4000, lambda: self.st_mid.configure(
                text="Bereit.", fg=GO))
        except Exception:
            pass

    def _live_sys(self):
        try:
            m = psutil.virtual_memory()
            cpu = psutil.cpu_percent(interval=None)
            self.st_right.configure(
                text="CPU %.0f%% \u00b7 RAM %.1f GB frei \u00b7 %s" % (
                    cpu, m.available / (1024.0 ** 3),
                    datetime.now().strftime("%H:%M:%S")))
            self._refresh_sys_pill()
            # Verlauf fuettern + Dashboard live nachziehen
            # (pausierbar: keine Bewegung ohne Zustimmung, WCAG 2.3)
            if not getattr(self, "_live_paused", False):
                try:
                    self._dash_hist["cpu"].append(float(cpu))
                    self._dash_hist["ram"].append(float(m.percent))
                    for kk in ("cpu", "ram"):
                        if len(self._dash_hist[kk]) > 40:
                            self._dash_hist[kk] = self._dash_hist[kk][-40:]
                except Exception:
                    pass
                if getattr(self, "view", "profile") == "dashboard" \
                        and self._dash_refs:
                    self._update_dashboard_live()
        except Exception:
            pass
        self.root.after(3000, self._live_sys)

    def _update_dashboard_live(self):
        """Aktualisiert Dashboard-Karten ohne Neuaufbau (Fokus bleibt)."""
        try:
            res = self._live_resources()
            R = self._dash_refs
            if "cpu_big" in R:
                R["cpu_big"].configure(text="%.0f %%" % res["cpu_pct"])
            if "cpu_sub" in R:
                R["cpu_sub"].configure(
                    text="%d Kerne / %d Threads \u00b7 %d MHz" % (
                        res["cpu_phys"], res["cpu_log"], res["cpu_freq"]))
            if "cpu_bar" in R:
                try:
                    R["cpu_bar"](res["cpu_pct"] / 100.0)
                except Exception:
                    pass
            if "ram_big" in R:
                R["ram_big"].configure(
                    text="%.1f / %.1f GB" % (res["ram_used"],
                                             res["ram_total"]))
            if "ram_sub" in R:
                R["ram_sub"].configure(
                    text="%.1f GB frei \u00b7 %.0f %% belegt" % (
                        res["ram_free"], res["ram_pct"]))
            if "ram_bar" in R:
                try:
                    R["ram_bar"](res["ram_pct"] / 100.0)
                except Exception:
                    pass
            if "disk_big" in R:
                R["disk_big"].configure(
                    text="%.0f / %.0f GB" % (res["disk_used"],
                                             res["disk_total"]))
            if "disk_sub" in R:
                R["disk_sub"].configure(
                    text="%.0f GB frei \u00b7 %.0f %% belegt" % (
                        res["disk_free"], res["disk_pct"]))
            if "disk_bar" in R:
                try:
                    R["disk_bar"](res["disk_pct"] / 100.0)
                except Exception:
                    pass
            g = res["gpu"]
            if "gpu_big" in R:
                if g.get("mem_total"):
                    R["gpu_big"].configure(
                        text="%.1f / %.1f GB" % (g["mem_used"] / 1024.0,
                                                 g["mem_total"] / 1024.0))
                else:
                    R["gpu_big"].configure(text="n/a")
            if "gpu_bar" in R and g.get("mem_total"):
                try:
                    R["gpu_bar"](g["mem_used"] / max(1.0, g["mem_total"]))
                except Exception:
                    pass
            if "hist_sum" in R:
                try:
                    R["hist_sum"].configure(
                        text="CPU %.0f %%, RAM %.0f %%. %s" % (
                            res["cpu_pct"], res["ram_pct"],
                            "Pausiert." if getattr(
                                self, "_live_paused", False)
                            else "Aktualisiert alle 3 s."))
                except Exception:
                    pass
            self._draw_dash_hist()
        except Exception:
            pass

    def _clip(self, t):
        try:
            self.root.clipboard_clear()
            self.root.clipboard_append(str(t))
            self.root.update()
            self._toast("In Zwischenablage kopiert.")
        except Exception as e:
            messagebox.showerror("Fehler", str(e))

    # ------------------------------------------------- aktionen
    def _copy(self, _e=None):
        s = self._act()
        ed = " (angepasst*)" if self._is_edited() else ""
        t = "=== %s%s ===\nModell: %s\nSuche: %s\n\n" % (
            s.get("name", "?"), ed, s.get("model", "?"), s.get("search", "?"))
        t += "--- Kern ---\n"
        t += "Context Length: %d\nGPU Offload: %d Layer\nKV Quant: %s\n" % (
            s["ctx"], s["layers"], s["kv"])
        t += "Flash Attention: %s\n\n--- Performance ---\n" % (
            "An" if s.get("flash") else "Aus")
        t += "Physical Batch: %d\nEval Batch: %d\nCPU Threads: %d\nMax Concurrent: %d\n" % (
            s["phys_batch"], s["batch"], s["threads"], s["max_conc"])
        t += "\n--- Speicher ---\n"
        t += "Unified KV: %s\nContext Checkpoints: %d\ntry mmap(): %s\nKeep in Mem: %s\nOffload KV GPU: %s\n" % (
            "An" if s["unified_kv"] else "Aus", s["ctx_cp"],
            "An" if s["mmap"] else "Aus", "An" if s["keep_mem"] else "Aus",
            "An" if s["offload_kv"] else "Aus")
        t += "\n--- Speculative ---\n"
        t += "Mode: %s\nMax Draft: %d\nMin Draft: %d\nDraft Prob: %s\n" % (
            s["spec"], s["max_draft"], s["min_draft"], s["draft_p"])
        t += "\n--- Advanced ---\n"
        t += "RoPE Base: %s\nRoPE Scale: %s\nK Quant: %s\nV Quant: %s\nSeed: -1\n" % (
            "Auto" if s["rope_base"] == 0 else s["rope_base"],
            "Auto" if s["rope_scale"] == 0 else s["rope_scale"],
            s["k_quant"], s["v_quant"])
        self._clip(t)

    def _preset_dict(self, s):
        return {
            "name": s.get("name", "?"),
            "load_params": {
                "ctx_len": s["ctx"], "n_gpu_layers": s["layers"],
                "flash_attention": s.get("flash", True),
                "use_mmap": s["mmap"],
                "eval_batch_size": s["batch"],
                "physical_batch_size": s["phys_batch"],
                "cpu_threads": s["threads"],
                "max_concurrent_predictions": s["max_conc"],
                "unified_kv_cache": s["unified_kv"],
                "context_checkpoints": s["ctx_cp"],
                "keep_model_in_memory": s["keep_mem"],
                "offload_kv_cache_to_gpu": s["offload_kv"],
                "rope_freq_base": s["rope_base"],
                "rope_freq_scale": s["rope_scale"],
                "cache_type_k": str(s["k_quant"]).lower(),
                "cache_type_v": str(s["v_quant"]).lower(),
                "speculative_decoding": s["spec"],
                "max_draft_tokens": s["max_draft"],
                "min_draft_tokens": s["min_draft"],
                "draft_probability": s["draft_p"]},
            "inference_params": {
                "max_tokens": -1, "temperature": 0.7, "top_p": 0.95,
                "top_k": 40, "repeat_penalty": 1.1, "seed": -1},
            "_meta": {"app": "LM Studio Optimizer v4",
                      "exported": datetime.now().isoformat(timespec="seconds"),
                      "edited": self._is_edited(),
                      "model": s.get("model", ""),
                      "search": s.get("search", "")}}

    def _json(self, _e=None):
        s = self._act()
        pre = self._preset_dict(s)
        fp = filedialog.asksaveasfilename(
            defaultextension=".json", filetypes=[("JSON", "*.json")],
            initialfile=str(s.get("name", "preset")).replace(
                " ", "_").lower() + ".json")
        if not fp:
            return
        try:
            with open(fp, "w", encoding="utf-8") as f:
                json.dump(pre, f, indent=2, ensure_ascii=False)
            self._toast("Preset gespeichert: %s" % os.path.basename(fp))
        except Exception as e:
            messagebox.showerror("Fehler", str(e))

    def _json_all(self):
        cur0, alvl0 = self.cur, self.alvl
        allp = []
        try:
            for k in TASKS.keys():
                self.cur = k
                if k == "audio":
                    for lv in ("min", "normal", "max"):
                        self.alvl = lv
                        allp.append(self._preset_dict(self._act()))
                else:
                    allp.append(self._preset_dict(self._act()))
        finally:
            self.cur, self.alvl = cur0, alvl0
        fp = filedialog.asksaveasfilename(
            defaultextension=".json", filetypes=[("JSON", "*.json")],
            initialfile="lm_studio_presets_alle.json")
        if not fp:
            self._render()
            return
        try:
            with open(fp, "w", encoding="utf-8") as f:
                json.dump(allp, f, indent=2, ensure_ascii=False)
            self._toast("%d Presets exportiert." % len(allp))
        except Exception as e:
            messagebox.showerror("Fehler", str(e))
        self._render()

    def _search(self, query=None, _e=None):
        s = self._act()
        q0 = (query or s.get("search", "") or "").strip()
        if query:
            try:
                self.quick_q.delete(0, tk.END)
                self.quick_q.insert(0, q0)
            except Exception:
                pass
        w = tk.Toplevel(self.root)
        w.title("Online-Suche - Hugging Face")
        w.configure(bg=BG)
        sw, sh = self._screen()
        w.geometry("%dx%d" % (min(760, sw - 60), min(560, sh - 80)))
        w.minsize(480, 360)
        w.transient(self.root)

        tk.Label(w, text="Hugging Face Suche", font=("Segoe UI", 14, "bold"),
                 bg=BG, fg=SIGNAL).pack(pady=(12, 2))
        row = tk.Frame(w, bg=BG)
        row.pack(fill=tk.X, padx=12, pady=(0, 6))
        tk.Label(row, text="Query:", font=("Segoe UI", 9), bg=BG,
                 fg=MUTED).pack(side=tk.LEFT)
        qvar = tk.StringVar(value=q0)
        qe = tk.Entry(row, textvariable=qvar, font=("Consolas", 9),
                      bg=PANEL2, fg=TEXT, insertbackground=TEXT,
                      relief="flat", width=40)
        qe.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(6, 6), ipady=4)
        limvar = tk.StringVar(value="8")
        tk.Label(row, text="Limit:", font=("Segoe UI", 9), bg=BG,
                 fg=MUTED).pack(side=tk.LEFT)
        tk.OptionMenu(row, limvar, "5", "8", "12", "20").pack(side=tk.LEFT,
                                                              padx=(4, 6))

        tframe = tk.Frame(w, bg=BG)
        tframe.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 8))
        sb = tk.Scrollbar(tframe, orient="vertical")
        t = tk.Text(tframe, bg="#0f0f1e", fg="#e0e0e0",
                    font=("Consolas", 9), wrap=tk.WORD, relief="flat",
                    bd=0, padx=10, pady=10, yscrollcommand=sb.set)
        sb.configure(command=t.yview)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        t.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        t.insert(tk.END, "Suche laeuft...\n")
        t.configure(state=tk.DISABLED)

        brow = tk.Frame(w, bg=BG)
        brow.pack(fill=tk.X, padx=12, pady=(0, 12))
        results = {"list": []}

        def do_search():
            q = qvar.get().strip()
            try:
                lim = int(limvar.get())
            except Exception:
                lim = 8
            t.configure(state=tk.NORMAL)
            t.delete("1.0", tk.END)
            t.insert(tk.END, "Suche nach '%s' laeuft...\n" % q)
            t.configure(state=tk.DISABLED)

            def cb(r, e):
                def u():
                    t.configure(state=tk.NORMAL)
                    t.delete("1.0", tk.END)
                    if e:
                        t.insert(tk.END, "Fehler: %s\n" % e)
                    elif not r:
                        t.insert(tk.END, "Keine Treffer.\n")
                    else:
                        results["list"] = r
                        t.insert(tk.END, "%-48s %8s %6s  %s\n" % (
                            "Modell", "DL", "Likes", "Update"))
                        t.insert(tk.END, "-" * 78 + "\n")
                        for m in r:
                            t.insert(tk.END, "%-48s %8d %6d  %s\n" % (
                                m["id"][:48], m["dl"], m["likes"], m["upd"]))
                        t.insert(tk.END, "\nTipp: Erste Zeile kopieren mit "
                                          "'Top-Treffer kopieren'.\n")
                    t.configure(state=tk.DISABLED)
                self.root.after(0, u)
            search_hf(q, lim, cb)

        def copy_top():
            if results["list"]:
                self._clip(results["list"][0]["id"])
            else:
                self._toast("Noch keine Ergebnisse.", ok=False)

        def open_browser():
            webbrowser.open(
                "https://huggingface.co/search?fullText=1&search=" + qvar.get().strip())

        for txt, fn in [("Suchen", do_search), ("Top-Treffer kopieren", copy_top),
                        ("Im Browser oeffnen", open_browser),
                        ("Schliessen", w.destroy)]:
            tk.Button(brow, text=txt, command=fn, font=("Segoe UI", 9, "bold"),
                      bg=PANEL2, fg=TEXT, relief="flat", bd=0,
                      padx=10, pady=5, cursor="hand2").pack(side=tk.LEFT,
                                                           padx=3)
        qe.bind("<Return>", lambda _e: do_search())
        do_search()

    def _report(self):
        t = "=== SYSTEM ===\n"
        for k, v in self.sysi.items():
            t += "%-12s: %s\n" % (k, v)
        try:
            sw, sh = self._screen()
            t += "%-12s: %dx%d (Zoom %d%%)\n" % (
                "Screen", sw, sh, int(round(self.zoom * 100)))
        except Exception:
            pass
        t += "\n=== PROFILE (effektiv, inkl. deiner Aenderungen*) ===\n\n"
        cur0, alvl0 = self.cur, self.alvl
        try:
            for k, p in TASKS.items():
                self.cur = k
                if k == "audio":
                    for lv in ("min", "normal", "max"):
                        self.alvl = lv
                        s = self._act()
                        mark = "*" if self._ov_key() in self.overrides else " "
                        t += "%s%s %s [%s]\n  %s\n  ctx=%d lay=%d kv=%s %s\n" % (
                            mark, p["icon"], s.get("model", "?"), lv,
                            s.get("model", "?"), s["ctx"], s["layers"],
                            s["kv"], s.get("tok", ""))
                else:
                    s = self._act()
                    mark = "*" if self._ov_key() in self.overrides else " "
                    t += "%s%s %s\n  %s\n  ctx=%d lay=%d kv=%s %s\n" % (
                        mark, p["icon"], p["name"], s.get("model", "?"),
                        s["ctx"], s["layers"], s["kv"], s.get("tok", "?"))
                    t += "  batch=%d phys=%d thr=%d conc=%d\n" % (
                        s["batch"], s["phys_batch"], s["threads"],
                        s["max_conc"])
                    t += "  unified=%s offload_kv=%s keep_mem=%s mmap=%s\n" % (
                        s["unified_kv"], s["offload_kv"], s["keep_mem"],
                        s["mmap"])
                    t += "  spec=%s max_draft=%d draft_p=%s\n" % (
                        s["spec"], s["max_draft"], s["draft_p"])
                t += "\n"
        finally:
            self.cur, self.alvl = cur0, alvl0

        w = tk.Toplevel(self.root)
        w.title("Systembericht")
        w.configure(bg=BG)
        sw, sh = self._screen()
        w.geometry("%dx%d" % (min(720, sw - 60), min(600, sh - 80)))
        w.minsize(480, 360)
        w.transient(self.root)
        tk.Label(w, text="Systembericht", font=("Segoe UI", 14, "bold"),
                 bg=BG, fg=SIGNAL).pack(pady=(12, 4))
        fr = tk.Frame(w, bg=BG)
        fr.pack(fill=tk.BOTH, expand=True, padx=12)
        sb = tk.Scrollbar(fr, orient="vertical")
        tx = tk.Text(fr, bg="#0f0f1e", fg="#e0e0e0", font=("Consolas", 9),
                     wrap=tk.WORD, relief="flat", bd=0, padx=10, pady=10,
                     yscrollcommand=sb.set)
        sb.configure(command=tx.yview)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        tx.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tx.insert(tk.END, t)
        tx.configure(state=tk.DISABLED)
        br = tk.Frame(w, bg=BG)
        br.pack(fill=tk.X, padx=12, pady=10)

        def _save():
            fp = filedialog.asksaveasfilename(
                defaultextension=".txt",
                filetypes=[("Text", "*.txt")],
                initialfile="systembericht.txt")
            if fp:
                try:
                    with open(fp, "w", encoding="utf-8") as f:
                        f.write(t)
                    self._toast("Bericht gespeichert.")
                except Exception as e:
                    messagebox.showerror("Fehler", str(e))

        for txt, fn in [("Kopieren", lambda: self._clip(t)),
                        ("Speichern", _save),
                        ("Schliessen", w.destroy)]:
            tk.Button(br, text=txt, command=fn, font=("Segoe UI", 9, "bold"),
                      bg=PANEL2, fg=TEXT, relief="flat", bd=0,
                      padx=10, pady=5, cursor="hand2").pack(side=tk.LEFT,
                                                           padx=3)


def main():
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
