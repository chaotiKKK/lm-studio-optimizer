@echo off
chcp 65001 >nul
title LM Studio Optimizer v3 - Build
color 0B
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"

set "LOGFILE=%~dp0build-log.txt"
> "%LOGFILE%" echo Build gestartet: %DATE% %TIME%

echo.
echo ==========================================================
echo   LM STUDIO OPTIMIZER v3 - BUILD
echo ==========================================================
echo.

echo [1/6] Pruefe Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo   FEHLER: Python fehlt.
    pause
    exit /b 1
)
for /f "tokens=2" %%v in ('python --version 2^>^&1') do set PYVER=%%v
echo       Python %PYVER%
echo.

echo [2/6] Pruefe Batch-Groesse...
for %%A in ("%~f0") do set BATSIZE=%%~zA
if %BATSIZE% LSS 25000 (
    echo   FEHLER: Batch zu klein (%BATSIZE% Bytes^).
    echo   Bitte mit Notepad++ / VS Code speichern.
    pause
    exit /b 1
)
echo       %BATSIZE% Bytes - OK.
echo.

echo [3/6] Extrahiere Python-Code...
if exist "extract.ps1" del /Q "extract.ps1" >nul 2>&1

> "extract.ps1" echo $ErrorActionPreference='Stop';
>>"extract.ps1" echo $p='%~f0';
>>"extract.ps1" echo $c=[System.IO.File]::ReadAllText($p);
>>"extract.ps1" echo $m1='QQQ_PY'+'_BEGIN';
>>"extract.ps1" echo $m2='QQQ_PY'+'_END';
>>"extract.ps1" echo $s=$c.IndexOf($m1);
>>"extract.ps1" echo $e=$c.IndexOf($m2);
>>"extract.ps1" echo if($s -lt 0 -or $e -lt 0 -or $e -le $s){Write-Host 'FEHLER: Marker';exit 1};
>>"extract.ps1" echo $start=$s+$m1.Length;
>>"extract.ps1" echo $len=$e-$start;
>>"extract.ps1" echo $code=$c.Substring($start,$len).Trim();
>>"extract.ps1" echo $enc=New-Object System.Text.UTF8Encoding($false);
>>"extract.ps1" echo [System.IO.File]::WriteAllText('lm_studio_optimizer_v3.py',$code,$enc);
>>"extract.ps1" echo Write-Host ('      '+$code.Length+' Zeichen.');

powershell -NoProfile -ExecutionPolicy Bypass -File "extract.ps1"
if errorlevel 1 ( echo   FEHLER: Extraktion. & del /Q "extract.ps1" & pause & exit /b 1 )
del /Q "extract.ps1" >nul 2>&1
for %%A in (lm_studio_optimizer_v3.py) do set SIZE=%%~zA
echo       %SIZE% Bytes
if %SIZE% LSS 8000 ( echo   FEHLER: zu klein. & pause & exit /b 1 )
echo.

echo [4/6] Installiere Abhaengigkeiten...
python -m pip install --quiet --upgrade pip >> "%LOGFILE%" 2>&1
python -m pip install --quiet psutil GPUtil py-cpuinfo pyinstaller requests >> "%LOGFILE%" 2>&1
echo       OK.
echo.

echo [5/6] Syntax-Check...
python -m py_compile lm_studio_optimizer_v3.py
if errorlevel 1 ( echo   FEHLER: Syntax. & pause & exit /b 1 )
echo       OK.
if exist build rmdir /S /Q build >nul 2>&1
if exist dist rmdir /S /Q dist >nul 2>&1
if exist "__pycache__" rmdir /S /Q "__pycache__" >nul 2>&1
echo.

echo [6/6] Baue EXE (1-3 Min)...
python -m PyInstaller --onefile --windowed --clean --noconfirm ^
  --name "LM-Studio-Optimizer-v3" ^
  --hidden-import=tkinter --hidden-import=tkinter.ttk ^
  --hidden-import=tkinter.scrolledtext ^
  --hidden-import=tkinter.filedialog --hidden-import=tkinter.messagebox ^
  --hidden-import=psutil --hidden-import=GPUtil ^
  --hidden-import=cpuinfo --hidden-import=requests ^
  lm_studio_optimizer_v3.py

echo.
if exist "dist\LM-Studio-Optimizer-v3.exe" (
    for %%A in ("dist\LM-Studio-Optimizer-v3.exe") do set EXESIZE=%%~zA
    echo ==========================================================
    echo   FERTIG! %EXESIZE% Bytes
    echo   %cd%\dist\LM-Studio-Optimizer-v3.exe
    echo ==========================================================
    start "" explorer "%cd%\dist"
) else ( echo   FEHLER: EXE fehlt. )
echo.
pause
exit /b 0

QQQ_PY_BEGIN
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import tkinter as tk
from tkinter import messagebox, filedialog
import psutil, platform, sys, json, threading
from datetime import datetime
try:
    import requests
    HAS_REQ = True
except ImportError:
    HAS_REQ = False

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
    "icon":"[C]","name":"Coding","color":"#00d2ff",
    "desc":"Programmierung, Aider/Cline",
    "ctx":32768,"layers":24,"kv":"Q8_0",
    "tok":"20-28 tok/s","vram":7.5,"ram":6.0,"stab":"Gut",
    "model":"Qwen2.5-Coder-14B-Instruct (Q4_K_M)",
    "search":"Qwen2.5-Coder-14B-Instruct-GGUF",
    "alts":["Qwen3-Coder-30B-A3B (Q4_K_M)",
            "Devstral-Small-2-24B (Q4_K_M)",
            "DeepSeek-Coder-V2-Lite (Q4_K_M)"],
    "warn":"Nur Q4_K_M! Layer 24 max.",
    "ok":"Beste Balance fuer Code.",
    "spec":"OFF","k_quant":"Q8_0","v_quant":"Q8_0","max_conc":2
 },
 "unreal": {
    "icon":"[UE]","name":"Unreal Engine","color":"#ff2d95",
    "desc":"UE5 C++ und Blueprint",
    "ctx":16384,"layers":20,"kv":"Q8_0",
    "tok":"18-24 tok/s","vram":7.2,"ram":8.0,"stab":"Gut",
    "model":"ue-expert-v2 (Qwen2.5-Coder-14B SFT)",
    "search":"ue-expert-v2-gguf",
    "alts":["Qwen3.6-27B (Q4_K_M)",
            "Gemma-4-12B-it (Q4_K_M)",
            "DeepSeek-V4 (Q4_K_M)"],
    "warn":"Kontext auf 16k begrenzen.",
    "ok":"Speziell fuer UE5 feinabgestimmt.",
    "spec":"OFF","k_quant":"Q8_0","v_quant":"Q8_0"
 },
 "html": {
    "icon":"[H]","name":"Single-File HTML","color":"#00ff88",
    "desc":"HTML/CSS/JS in einer Datei",
    "ctx":32768,"layers":20,"kv":"Q8_0",
    "tok":"22-30 tok/s","vram":7.8,"ram":10.0,"stab":"Gut",
    "model":"Qwen3-Coder-30B-A3B (Q4_K_M)",
    "search":"Qwen3-Coder-30B-A3B-Instruct-GGUF",
    "alts":["Qwen2.5-Coder-14B (Q4_K_M)",
            "Codestral-22B-v0.1 (Q4_K_M)",
            "Phi-4-14B (Q4_K_M)"],
    "warn":"30B MoE: Layer auf 20. Batch 256.",
    "ok":"MoE = hohe Qualitaet, wenig VRAM.",
    "threads":12,"batch":256,"phys_batch":256,
    "spec":"OFF","k_quant":"Q8_0","v_quant":"Q8_0","max_conc":2
 },
 "image": {
    "icon":"[I]","name":"Bildgenerierung","color":"#ff9500",
    "desc":"Prompt-Enhancement fuer Flux/SDXL",
    "ctx":8192,"layers":32,"kv":"Q8_0",
    "tok":"30-40 tok/s","vram":6.8,"ram":3.0,"stab":"Sehr gut",
    "model":"Qwen3-VL-8B-Caption-it (Q8_0)",
    "search":"Qwen3-VL-8B-abliterated-caption-gguf",
    "alts":["Qwen2.5-VL-7B-abliterated (Q5_K_M)",
            "Gemma-4-E4B-Uncensored (Q4_K_M)",
            "Flux-Prompt-Enhance (GGUF)"],
    "warn":"LM Studio generiert keine Bilder!",
    "ok":"Nutze fuer Prompt-Enhancement.",
    "threads":8,"spec":"MTP","max_draft":8,"min_draft":0,"draft_p":0.7,
    "k_quant":"Q8_0","v_quant":"Q8_0"
 },
 "audio": {
    "icon":"[A]","name":"Audio Transkription","color":"#7b2ff7",
    "desc":"Sprache zu Text, Meeting-Notizen",
    "ctx":4096,"layers":32,"kv":"Q8_0",
    "tok":"15x Echtzeit","vram":2.5,"ram":1.0,"stab":"Exzellent",
    "model":"Whisper-Large-v3-Turbo",
    "search":"whisper-large-v3-turbo-gguf",
    "alts":["S1-mini 600M","Voxtral-Mini-3B","Voxtral-Small-24B"],
    "warn":"In LM Studio als Audio-Modell laden!",
    "ok":"Min/Normal/Max zur Feinsteuerung.",
    "threads":8,"batch":256,"phys_batch":256,
    "spec":"OFF","k_quant":"Q8_0","v_quant":"Q8_0",
    "levels":{
      "min":{"model":"S1-mini (600M)","search":"S1-mini-gguf",
             "vram":1.0,"speed":"50x Echtzeit","desc":"Schnellste Variante",
             "ctx":2048,"layers":32,"kv":"Q4_0"},
      "normal":{"model":"Whisper-Large-v3-Turbo","search":"whisper-large-v3-turbo-gguf",
                "vram":2.5,"speed":"15x Echtzeit","desc":"Beste Balance",
                "ctx":4096,"layers":32,"kv":"Q8_0"},
      "max":{"model":"Voxtral-Small-24B (Q4_K_M)","search":"Voxtral-Small-24B-2507-gguf",
             "vram":7.0,"speed":"5x Echtzeit","desc":"Maximale Genauigkeit",
             "ctx":8192,"layers":24,"kv":"Q8_0"}
    }
 },
 "balanced": {
    "icon":"[B]","name":"Allgemein","color":"#3a7bd5",
    "desc":"Chat, Zusammenfassungen",
    "ctx":16384,"layers":32,"kv":"Q8_0",
    "tok":"30-35 tok/s","vram":7.2,"ram":3.0,"stab":"Sehr gut",
    "model":"Qwen3.5-9B (Q4_K_M)","search":"Qwen3.5-9B-GGUF",
    "alts":["Gemma-4-12B-it (Q4_K_M)",
            "Mistral-Small-3.1-24B (Q4_K_M)",
            "Llama-4-Scout-17B (Q4_K_M)"],
    "warn":None,"ok":"Empfohlen fuer 90% aller Faelle.",
    "spec":"MTP","max_draft":6,"min_draft":0,"draft_p":0.7,
    "k_quant":"Q8_0","v_quant":"Q8_0"
 },
 "long32k": {
    "icon":"[L]","name":"Long Context 32k","color":"#7b2ff7",
    "desc":"Dokumente, Codebasen",
    "ctx":32768,"layers":28,"kv":"Q8_0",
    "tok":"18-24 tok/s","vram":7.8,"ram":6.0,"stab":"Gut",
    "model":"Qwen2.5-7B-Instruct (Q4_K_M)",
    "search":"Qwen2.5-7B-Instruct-GGUF",
    "alts":["Llama-3.1-8B-Instruct (Q4_K_M)","Qwen3.5-9B (Q4_K_M)"],
    "warn":"Nur 7B/8B Q4_K_M! Kein 14B.",
    "ok":"Erfuellt Minimum 30.000 Tokens.",
    "spec":"OFF","k_quant":"Q8_0","v_quant":"Q8_0","max_conc":2
 },
 "ultra64k": {
    "icon":"[U]","name":"Ultra 64k","color":"#ff9500",
    "desc":"Buecher, sehr lange Texte",
    "ctx":65536,"layers":20,"kv":"Q4_0",
    "tok":"10-15 tok/s","vram":7.9,"ram":12.0,"stab":"Mittel",
    "model":"Qwen2.5-7B-Instruct (Q4_K_M)",
    "search":"Qwen2.5-7B-Instruct-GGUF",
    "alts":["Llama-3.1-8B-Instruct (Q4_K_M)"],
    "warn":"Nur 7B/8B! RAM ca. 12 GB. Offload KV AUS.",
    "ok":"Fuer Buecher und lange Dokumente.",
    "threads":12,"batch":256,"phys_batch":256,
    "offload_kv":False,"max_conc":1,
    "spec":"OFF","k_quant":"Q4_0","v_quant":"Q4_0"
 }
}

for k,p in TASKS.items():
    for dk,dv in DEFAULTS.items():
        p.setdefault(dk,dv)

def sysinfo():
    d = {}
    try: d["OS"] = "%s %s" % (platform.system(), platform.release())
    except: d["OS"] = "?"
    try:
        d["CPU"] = "%d Kerne / %d Threads" % (
            psutil.cpu_count(logical=False) or 0,
            psutil.cpu_count(logical=True) or 0)
    except: d["CPU"] = "?"
    try:
        m = psutil.virtual_memory()
        d["RAM"] = "%.1f GB (%.1f GB frei)" % (
            m.total/(1024.0**3), m.available/(1024.0**3))
    except: d["RAM"] = "?"
    try:
        import GPUtil
        g = GPUtil.getGPUs()
        d["GPU"] = "%s (%d MB)" % (g[0].name, g[0].memoryTotal) if g else "Keine NVIDIA"
    except: d["GPU"] = "GPUtil fehlt"
    d["Python"] = sys.version.split()[0]
    d["Zeit"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return d

def search_hf(q, cb):
    def _r():
        if not HAS_REQ:
            cb([], "requests fehlt"); return
        try:
            r = requests.get("https://huggingface.co/api/models",
                params={"search":q,"filter":"gguf","sort":"downloads",
                        "direction":"-1","limit":8}, timeout=8)
            if r.status_code == 200:
                out = [{"id":m.get("modelId","?"),
                        "dl":m.get("downloads",0),
                        "likes":m.get("likes",0),
                        "upd":m.get("lastModified","")[:10]}
                       for m in r.json()]
                cb(out, None)
            else:
                cb([], "HTTP %d" % r.status_code)
        except Exception as e:
            cb([], str(e))
    threading.Thread(target=_r, daemon=True).start()

class App:
    def __init__(self, root):
        self.root = root
        root.title("LM Studio Optimizer v3 - Extended")
        root.geometry("1250x850")
        root.minsize(1100, 750)
        root.configure(bg="#0a0a1a")
        self.sysi = sysinfo()
        self.cur = "coding"
        self.alvl = "normal"
        self._ui()
        self._switch("coding")

    def _ui(self):
        h = tk.Frame(self.root, bg="#0a0a1a"); h.pack(fill=tk.X, pady=(10,4))
        tk.Label(h, text="LM Studio Optimizer v3", font=("Segoe UI",20,"bold"),
                 bg="#0a0a1a", fg="#00d2ff").pack()
        tk.Label(h, text="Aufgaben-Profile - Erweiterte Einstellungen - Online-Suche",
                 font=("Segoe UI",10), bg="#0a0a1a", fg="#888").pack()

        tf = tk.Frame(self.root, bg="#0a0a1a"); tf.pack(pady=10)
        self.btns = {}
        for i,k in enumerate(TASKS.keys()):
            p = TASKS[k]
            b = tk.Button(tf, text="%s %s"%(p["icon"],p["name"]),
                          font=("Segoe UI",9,"bold"), bg="#141428", fg="#c0c0c0",
                          relief="flat", bd=0, padx=10, pady=8, cursor="hand2",
                          activebackground=p["color"], activeforeground="#0a0a1a",
                          command=lambda kk=k: self._switch(kk))
            b.grid(row=i//4, column=i%4, padx=3, pady=3)
            self.btns[k] = b

        self.cnt = tk.Frame(self.root, bg="#0a0a1a")
        self.cnt.pack(fill=tk.BOTH, expand=True, padx=20, pady=6)

        ff = tk.Frame(self.root, bg="#0a0a1a")
        ff.pack(fill=tk.X, padx=20, pady=(0,12))
        for t,c,bg,fg in [("Werte kopieren",self._copy,"#00d2ff","#0a0a1a"),
                          ("JSON-Preset",self._json,"#7b2ff7","#ffffff"),
                          ("Online-Suche",self._search,"#ff9500","#0a0a1a"),
                          ("Systembericht",self._report,"#00ff88","#0a0a1a")]:
            tk.Button(ff,text=t,command=c,font=("Segoe UI",10,"bold"),
                      bg=bg,fg=fg,relief="flat",padx=12,pady=7,
                      cursor="hand2").pack(side=tk.LEFT,padx=3)
        tk.Button(ff,text="Beenden",command=self.root.quit,
                  font=("Segoe UI",10,"bold"),bg="#3a1a1a",fg="#ff6b6b",
                  relief="flat",padx=12,pady=7,cursor="hand2").pack(side=tk.RIGHT,padx=3)

    def _switch(self, k):
        self.cur = k
        for kk,b in self.btns.items():
            if kk==k: b.configure(bg=TASKS[kk]["color"], fg="#0a0a1a")
            else: b.configure(bg="#141428", fg="#c0c0c0")
        self._render()

    def _render(self):
        for w in self.cnt.winfo_children(): w.destroy()
        p = TASKS[self.cur]

        # Scrollbarer Bereich fuer linke Spalte
        L = tk.Frame(self.cnt, bg="#141428", padx=20, pady=20)
        L.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0,8))
        tk.Label(L, text="%s  %s"%(p["icon"],p["name"]),
                 font=("Segoe UI",14,"bold"), bg="#141428",
                 fg="#00d2ff").pack(anchor=tk.W)
        tk.Label(L, text=p["desc"], font=("Segoe UI",9), bg="#141428",
                 fg="#999", wraplength=520, justify=tk.LEFT).pack(anchor=tk.W, pady=(4,14))

        if self.cur=="audio":
            self._audio(L,p)
        else:
            self._normal(L,p)

        # Rechte Spalte
        R = tk.Frame(self.cnt, bg="#141428", padx=20, pady=20)
        R.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(8,0))
        tk.Label(R, text="Leistung und Modelle", font=("Segoe UI",14,"bold"),
                 bg="#141428", fg="#00d2ff").pack(anchor=tk.W, pady=(0,12))
        self._meter(R,"VRAM (8 GB)","%.1f GB / 8.0 GB"%p["vram"],p["vram"]/8.0)
        self._meter(R,"RAM (32 GB)","%.1f GB / 32.0 GB"%p["ram"],p["ram"]/32.0)
        for l,v in [("Tempo",p["tok"]),("Stabilitaet",p["stab"]),
                    ("Kontext","{:,} Tokens".format(p["ctx"]))]:
            r = tk.Frame(R, bg="#141428"); r.pack(fill=tk.X, pady=3)
            tk.Label(r,text=l+":",font=("Segoe UI",9),bg="#141428",
                     fg="#888",width=15,anchor=tk.W).pack(side=tk.LEFT)
            tk.Label(r,text=v,font=("Consolas",10,"bold"),bg="#141428",
                     fg="#ffffff").pack(side=tk.LEFT)
        tk.Label(R,text="Empfohlenes Modell:",font=("Segoe UI",9,"bold"),
                 bg="#141428",fg="#00d2ff").pack(anchor=tk.W,pady=(12,2))
        tk.Label(R,text=p["model"],font=("Segoe UI",9),bg="#141428",
                 fg="#ffffff",wraplength=380,justify=tk.LEFT).pack(anchor=tk.W)
        tk.Label(R,text="Suche: "+p["search"],font=("Consolas",8),
                 bg="#141428",fg="#666",wraplength=380,
                 justify=tk.LEFT).pack(anchor=tk.W,pady=(2,8))
        tk.Label(R,text="Alternativen:",font=("Segoe UI",9,"bold"),
                 bg="#141428",fg="#ff9500").pack(anchor=tk.W,pady=(8,2))
        for a in p["alts"]:
            tk.Label(R,text="  - "+a,font=("Segoe UI",8),bg="#141428",
                     fg="#c0c0c0",wraplength=380,
                     justify=tk.LEFT).pack(anchor=tk.W)
        if p.get("warn"):
            w = tk.Frame(R,bg="#3a1a1a",padx=12,pady=10); w.pack(fill=tk.X,pady=(12,0))
            tk.Label(w,text="WARNUNG",font=("Segoe UI",9,"bold"),
                     bg="#3a1a1a",fg="#ff6b6b").pack(anchor=tk.W)
            tk.Label(w,text=p["warn"],font=("Segoe UI",9),bg="#3a1a1a",
                     fg="#ffbbbb",wraplength=380,justify=tk.LEFT).pack(anchor=tk.W,pady=(2,0))
        if p.get("ok"):
            w = tk.Frame(R,bg="#0f2a1a",padx=12,pady=10); w.pack(fill=tk.X,pady=(8,0))
            tk.Label(w,text="EMPFEHLUNG",font=("Segoe UI",9,"bold"),
                     bg="#0f2a1a",fg="#00ff88").pack(anchor=tk.W)
            tk.Label(w,text=p["ok"],font=("Segoe UI",9),bg="#0f2a1a",
                     fg="#aaffcc",wraplength=380,justify=tk.LEFT).pack(anchor=tk.W,pady=(2,0))

    def _section(self, parent, title):
        f = tk.Frame(parent, bg="#1a1a2e", padx=10, pady=6)
        f.pack(fill=tk.X, pady=(10,4))
        tk.Label(f, text=title, font=("Segoe UI",9,"bold"),
                 bg="#1a1a2e", fg="#00d2ff").pack(anchor=tk.W)

    def _normal(self, parent, p):
        self._section(parent, "KERN-EINSTELLUNGEN")
        self._rows(parent, [
            ("Context Length","{:,}".format(p["ctx"]),True),
            ("GPU Offload","%d Layer"%p["layers"],False),
            ("KV Cache Quantization",p["kv"],p["kv"]=="F16"),
            ("Flash Attention","An" if p["flash"] else "Aus",False),
        ])
        self._section(parent, "PERFORMANCE")
        self._rows(parent, [
            ("Physical Batch Size",str(p["phys_batch"]),False),
            ("Evaluation Batch Size",str(p["batch"]),False),
            ("CPU Thread Pool Size",str(p["threads"]),False),
            ("Max Concurrent",str(p["max_conc"]),p["max_conc"]>=4),
        ])
        self._section(parent, "SPEICHER-MANAGEMENT")
        self._rows(parent, [
            ("Unified KV Cache","An" if p["unified_kv"] else "Aus",False),
            ("Context Checkpoints",str(p["ctx_cp"]),False),
            ("Try mmap()","An" if p["mmap"] else "Aus",False),
            ("Keep Model in Memory","An" if p["keep_mem"] else "Aus",p["keep_mem"]),
            ("Offload KV to GPU","An" if p["offload_kv"] else "Aus",False),
        ])
        self._section(parent, "SPECULATIVE DECODING")
        self._rows(parent, [
            ("Speculative Decoding",p["spec"],False),
            ("Max Draft Tokens",str(p["max_draft"]),False),
            ("Min Draft Tokens",str(p["min_draft"]),False),
            ("Draft Probability",str(p["draft_p"]),False),
        ])
        self._section(parent, "ERWEITERT")
        self._rows(parent, [
            ("RoPE Frequency Base","Auto" if p["rope_base"]==0 else str(p["rope_base"]),False),
            ("RoPE Frequency Scale","Auto" if p["rope_scale"]==0 else str(p["rope_scale"]),False),
            ("K-Cache Quantization",p["k_quant"],False),
            ("V-Cache Quantization",p["v_quant"],False),
            ("Seed","-1 (random)",False),
        ])

    def _audio(self, parent, p):
        tk.Label(parent,text="Genauigkeits-Stufe",font=("Segoe UI",10,"bold"),
                 bg="#141428",fg="#7b2ff7").pack(anchor=tk.W,pady=(0,6))
        bf = tk.Frame(parent, bg="#141428"); bf.pack(fill=tk.X, pady=(0,12))
        self.lbtns = {}
        for lv in ["min","normal","max"]:
            b = tk.Button(bf,text=lv.upper(),font=("Segoe UI",9,"bold"),
                          bg="#1a1a2e",fg="#c0c0c0",relief="flat",bd=0,
                          padx=10,pady=6,cursor="hand2",
                          command=lambda l=lv: self._setlvl(l))
            b.pack(side=tk.LEFT,padx=3); self.lbtns[lv]=b
        i = p["levels"][self.alvl]
        c = tk.Frame(parent,bg="#1a1a2e",padx=14,pady=12); c.pack(fill=tk.X,pady=(0,12))
        cmap = {"min":"#00ff88","normal":"#00d2ff","max":"#ff9500"}
        tk.Label(c,text=i["model"],font=("Segoe UI",11,"bold"),bg="#1a1a2e",
                 fg=cmap[self.alvl]).pack(anchor=tk.W)
        tk.Label(c,text=i["desc"],font=("Segoe UI",9),bg="#1a1a2e",
                 fg="#c0c0c0").pack(anchor=tk.W,pady=(2,6))
        tk.Label(c,text="VRAM: %.1f GB | %s"%(i["vram"],i["speed"]),
                 font=("Consolas",9),bg="#1a1a2e",fg="#ffffff").pack(anchor=tk.W)
        tk.Label(c,text="Suche: "+i["search"],font=("Consolas",8),
                 bg="#1a1a2e",fg="#666").pack(anchor=tk.W,pady=(4,0))

        self._section(parent, "KERN")
        self._rows(parent, [
            ("Context Length","{:,}".format(i["ctx"]),True),
            ("GPU Offload","%d Layer"%i["layers"],False),
            ("KV Cache Quantization",i["kv"],False),
            ("Flash Attention","An",False),
        ])
        self._section(parent, "PERFORMANCE")
        self._rows(parent, [
            ("Physical Batch Size","256",False),
            ("Evaluation Batch Size","256",False),
            ("CPU Thread Pool Size","8",False),
            ("Max Concurrent","2",False),
        ])
        self._section(parent, "SPEICHER")
        self._rows(parent, [
            ("Unified KV Cache","An",False),
            ("Context Checkpoints","32",False),
            ("Try mmap()","Aus",False),
            ("Keep Model in Memory","Aus",False),
            ("Offload KV to GPU","An",False),
        ])
        self._section(parent, "ERWEITERT")
        self._rows(parent, [
            ("Speculative Decoding","OFF",False),
            ("K-Cache Quantization",i["kv"],False),
            ("V-Cache Quantization",i["kv"],False),
            ("Seed","-1 (random)",False),
        ])
        self._upd_lbtns()

    def _rows(self, parent, rows):
        for l,v,h in rows:
            r = tk.Frame(parent, bg="#141428"); r.pack(fill=tk.X, pady=2)
            tk.Label(r,text=l,font=("Segoe UI",9),bg="#141428",
                     fg="#888",width=24,anchor=tk.W).pack(side=tk.LEFT)
            tk.Label(r,text=v,font=("Consolas",11,"bold"),bg="#141428",
                     fg="#00ff88" if h else "#ffffff").pack(side=tk.LEFT,padx=8)
            tk.Button(r,text="Copy",font=("Segoe UI",8),bg="#1a3a4a",
                      fg="#00d2ff",relief="flat",bd=0,padx=8,pady=2,
                      cursor="hand2",
                      command=lambda vv=v: self._clip(vv)).pack(side=tk.RIGHT)

    def _setlvl(self, lv): self.alvl = lv; self._render()

    def _upd_lbtns(self):
        cmap = {"min":"#00ff88","normal":"#00d2ff","max":"#ff9500"}
        for lv,b in self.lbtns.items():
            if lv==self.alvl: b.configure(bg=cmap[lv],fg="#0a0a1a")
            else: b.configure(bg="#1a1a2e",fg="#c0c0c0")

    def _meter(self, parent, label, value, frac):
        f = tk.Frame(parent, bg="#141428"); f.pack(fill=tk.X,pady=(6,0))
        t = tk.Frame(f, bg="#141428"); t.pack(fill=tk.X)
        tk.Label(t,text=label,font=("Segoe UI",9),bg="#141428",
                 fg="#c0c0c0").pack(side=tk.LEFT)
        tk.Label(t,text=value,font=("Segoe UI",9,"bold"),bg="#141428",
                 fg="#ffffff").pack(side=tk.RIGHT)
        cv = tk.Canvas(f,height=10,bg="#1a1a2e",highlightthickness=0)
        cv.pack(fill=tk.X,pady=(4,8))
        def dr(e=None):
            cv.delete("all"); w=cv.winfo_width()
            cv.create_rectangle(0,0,w,10,fill="#1a1a2e",outline="")
            col = "#00d2ff" if frac<0.85 else "#ffc107" if frac<0.95 else "#ff4444"
            cv.create_rectangle(0,0,int(w*min(frac,1.0)),10,fill=col,outline="")
        cv.bind("<Configure>",dr); self.root.after(50,dr)

    def _clip(self,t):
        self.root.clipboard_clear(); self.root.clipboard_append(str(t)); self.root.update()

    def _act(self):
        p = TASKS[self.cur]
        if self.cur=="audio":
            i = p["levels"][self.alvl]
            return dict(i, batch=256, phys_batch=256, threads=8,
                        max_conc=2, unified_kv=True, ctx_cp=32,
                        keep_mem=False, offload_kv=True,
                        spec="OFF", max_draft=0, min_draft=0, draft_p=0.0,
                        rope_base=0, rope_scale=0,
                        k_quant=i["kv"], v_quant=i["kv"],
                        name="%s-%s"%(p["name"],self.alvl))
        return p

    def _copy(self):
        s = self._act()
        t = "=== %s ===\nModell: %s\nSuche: %s\n\n"%(s["name"],s["model"],s["search"])
        t += "--- Kern ---\n"
        t += "Context Length: %d\nGPU Offload: %d Layer\nKV Quant: %s\n"%(s["ctx"],s["layers"],s["kv"])
        t += "Flash Attention: An\n\n--- Performance ---\n"
        t += "Physical Batch: %d\nEval Batch: %d\nCPU Threads: %d\nMax Concurrent: %d\n"%(
            s["phys_batch"],s["batch"],s["threads"],s["max_conc"])
        t += "\n--- Speicher ---\n"
        t += "Unified KV: %s\nContext Checkpoints: %d\ntry mmap(): %s\nKeep in Mem: %s\nOffload KV GPU: %s\n"%(
            "An" if s["unified_kv"] else "Aus", s["ctx_cp"],
            "An" if s["mmap"] else "Aus", "An" if s["keep_mem"] else "Aus",
            "An" if s["offload_kv"] else "Aus")
        t += "\n--- Speculative ---\n"
        t += "Mode: %s\nMax Draft: %d\nMin Draft: %d\nDraft Prob: %s\n"%(
            s["spec"],s["max_draft"],s["min_draft"],s["draft_p"])
        t += "\n--- Advanced ---\n"
        t += "RoPE Base: %s\nRoPE Scale: %s\nK Quant: %s\nV Quant: %s\nSeed: -1\n"%(
            "Auto" if s["rope_base"]==0 else s["rope_base"],
            "Auto" if s["rope_scale"]==0 else s["rope_scale"],
            s["k_quant"],s["v_quant"])
        self._clip(t); messagebox.showinfo("Kopiert", "Werte kopiert!")

    def _json(self):
        s = self._act()
        pre = {"name":s["name"],
               "load_params":{
                 "ctx_len":s["ctx"],"n_gpu_layers":s["layers"],
                 "flash_attention":s["flash"],"use_mmap":s["mmap"],
                 "eval_batch_size":s["batch"],"physical_batch_size":s["phys_batch"],
                 "cpu_threads":s["threads"],
                 "max_concurrent_predictions":s["max_conc"],
                 "unified_kv_cache":s["unified_kv"],
                 "context_checkpoints":s["ctx_cp"],
                 "keep_model_in_memory":s["keep_mem"],
                 "offload_kv_cache_to_gpu":s["offload_kv"],
                 "rope_freq_base":s["rope_base"],
                 "rope_freq_scale":s["rope_scale"],
                 "cache_type_k":s["k_quant"].lower(),
                 "cache_type_v":s["v_quant"].lower(),
                 "speculative_decoding":s["spec"],
                 "max_draft_tokens":s["max_draft"],
                 "min_draft_tokens":s["min_draft"],
                 "draft_probability":s["draft_p"]},
               "inference_params":{
                 "max_tokens":-1,"temperature":0.7,"top_p":0.95,
                 "top_k":40,"repeat_penalty":1.1,"seed":-1}}
        fp = filedialog.asksaveasfilename(defaultextension=".json",
            filetypes=[("JSON","*.json")],
            initialfile=s["name"].replace(" ","_").lower()+".json")
        if not fp: return
        try:
            with open(fp,"w",encoding="utf-8") as f:
                json.dump(pre,f,indent=2,ensure_ascii=False)
            messagebox.showinfo("OK","Preset: "+fp)
        except Exception as e: messagebox.showerror("Fehler",str(e))

    def _search(self):
        s = self._act()
        w = tk.Toplevel(self.root); w.title("Online-Suche")
        w.geometry("720x520"); w.configure(bg="#0a0a1a")
        tk.Label(w,text="Hugging Face Suche",font=("Segoe UI",14,"bold"),
                 bg="#0a0a1a",fg="#00d2ff").pack(pady=(12,4))
        tk.Label(w,text="Query: "+s["search"],font=("Consolas",9),
                 bg="#0a0a1a",fg="#888").pack(pady=(0,8))
        t = tk.Text(w,bg="#0f0f1e",fg="#e0e0e0",font=("Consolas",9),
                    wrap=tk.WORD,relief="flat",bd=0,padx=10,pady=10)
        t.pack(fill=tk.BOTH,expand=True,padx=12,pady=(0,12))
        t.insert(tk.END,"Suche laeuft...\n"); t.configure(state=tk.DISABLED)
        def cb(r,e):
            def u():
                t.configure(state=tk.NORMAL); t.delete("1.0",tk.END)
                if e: t.insert(tk.END,"Fehler: %s\n"%e)
                elif not r: t.insert(tk.END,"Keine Treffer.\n")
                else:
                    t.insert(tk.END,"%-48s %8s %6s  %s\n"%("Modell","DL","Likes","Update"))
                    t.insert(tk.END,"-"*78+"\n")
                    for m in r:
                        t.insert(tk.END,"%-48s %8d %6d  %s\n"%(
                            m["id"][:48],m["dl"],m["likes"],m["upd"]))
                t.configure(state=tk.DISABLED)
            self.root.after(0,u)
        search_hf(s["search"],cb)

    def _report(self):
        t = "=== SYSTEM ===\n"
        for k,v in self.sysi.items(): t += "%-12s: %s\n"%(k,v)
        t += "\n=== PROFILE ===\n\n"
        for k,p in TASKS.items():
            t += "%s %s\n  %s\n  ctx=%d lay=%d kv=%s %s\n"%(
                p["icon"],p["name"],p["model"],p["ctx"],p["layers"],p["kv"],p["tok"])
            t += "  batch=%d phys=%d thr=%d conc=%d\n"%(
                p["batch"],p["phys_batch"],p["threads"],p["max_conc"])
            t += "  unified=%s offload_kv=%s keep_mem=%s mmap=%s\n"%(
                p["unified_kv"],p["offload_kv"],p["keep_mem"],p["mmap"])
            t += "  spec=%s max_draft=%d draft_p=%s\n"%(
                p["spec"],p["max_draft"],p["draft_p"])
            if k=="audio":
                for lv,i in p["levels"].items():
                    t += "  [%s] %s - %s\n"%(lv,i["model"],i["speed"])
            t += "\n"
        messagebox.showinfo("Systembericht",t)

def main():
    root = tk.Tk(); App(root); root.mainloop()

if __name__ == "__main__":
    main()
QQQ_PY_END