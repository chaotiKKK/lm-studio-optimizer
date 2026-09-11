"""LM Studio Optimizer - Mobile (Flet).

Gleiche Profile wie die Desktop-App (tasks.json, Single Source of Truth).
Bauen:  flet run .            (Desktop-Vorschau)
        flet build apk        (Android APK, Sideload)
        flet build aab        (Play-Store-Bundle)

Hinweis: psutil/GPUtil gibt es auf Android nicht - Live-Systemwerte werden
dort als "n/a" gezeigt, alle Presets funktionieren trotzdem. HTTP laeuft
ueber urllib (stdlib), damit kein natives Wheel noetig ist.
"""
import json
import os
import urllib.parse
import urllib.request

import flet as ft

try:
    import psutil
    HAS_PSUTIL = True
except Exception:
    HAS_PSUTIL = False

HERE = os.path.dirname(os.path.abspath(__file__))
CTX = [2048, 4096, 8192, 16384, 32768, 65536, 131072]
BATCH = [128, 256, 512, 1024, 2048]


def load_tasks():
    with open(os.path.join(HERE, "tasks.json"), "r", encoding="utf-8") as f:
        return json.load(f)["profiles"]


TASKS = load_tasks()


def eff(cur, alvl, overrides):
    p = TASKS[cur]
    if cur == "audio":
        i = p["levels"][alvl]
        s = dict(i)
        s.update({"batch": 256, "phys_batch": 256, "threads": 8,
                  "max_conc": 2, "unified_kv": True, "ctx_cp": 32,
                  "keep_mem": False, "offload_kv": True, "spec": "OFF",
                  "max_draft": 0, "min_draft": 0, "draft_p": 0.0,
                  "rope_base": 0, "rope_scale": 0, "flash": True,
                  "mmap": False, "k_quant": i["kv"], "v_quant": i["kv"],
                  "kv": i["kv"], "tok": i["speed"], "ram": 2.0,
                  "stab": p["stab"], "model": i["model"],
                  "search": i["search"], "name": "Audio-" + alvl})
        base = {"vram": i["vram"], "ctx": i["ctx"], "layers": i["layers"],
                "kv": i["kv"], "offload_kv": True}
    else:
        s = dict(p)
        base = p
    for k, v in overrides.get(cur if cur != "audio" else "audio:" + alvl,
                              {}).items():
        if k in s:
            s[k] = v
    return s, base


def est_vram(base, s):
    try:
        v = float(base.get("vram", 7.0))
        kv = str(s.get("kv", s.get("k_quant", "Q8_0")))
        per8k = 0.28 if "Q4" in kv else (0.42 if "Q5" in kv else 0.55)
        v += ((int(s["ctx"]) - int(base["ctx"])) / 8192.0) * per8k
        v += (int(s["layers"]) - int(base["layers"])) * 0.06
        if not s.get("offload_kv", True):
            v -= 0.4
        return max(0.5, round(v, 1))
    except Exception:
        return float(base.get("vram", 7.0))


def hf_search(query, limit=8):
    url = ("https://huggingface.co/api/models?search="
           + urllib.parse.quote(query)
           + "&filter=gguf&sort=downloads&direction=-1&limit=%d" % limit)
    with urllib.request.urlopen(url, timeout=10) as r:
        data = json.loads(r.read().decode("utf-8"))
    return [{"id": m.get("modelId", "?"), "dl": m.get("downloads", 0)}
            for m in data]


def preset_json(s):
    return json.dumps(
        {"name": s.get("name", "?"),
         "load_params": {
             "ctx_len": s["ctx"], "n_gpu_layers": s["layers"],
             "flash_attention": bool(s.get("flash", True)),
             "use_mmap": bool(s["mmap"]),
             "eval_batch_size": s["batch"],
             "physical_batch_size": s["phys_batch"],
             "cpu_threads": s["threads"],
             "max_concurrent_predictions": s["max_conc"],
             "unified_kv_cache": bool(s["unified_kv"]),
             "context_checkpoints": s["ctx_cp"],
             "keep_model_in_memory": bool(s["keep_mem"]),
             "offload_kv_cache_to_gpu": bool(s["offload_kv"]),
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
             "top_k": 40, "repeat_penalty": 1.1, "seed": -1}},
        indent=2, ensure_ascii=False)


def main(page: ft.Page):
    page.title = "LM Studio Optimizer"
    page.theme_mode = ft.ThemeMode.DARK
    page.scroll = ft.ScrollMode.AUTO
    cur = {"key": "coding", "alvl": "normal"}
    overrides: dict = {}

    snack = ft.SnackBar(content=ft.Text(""))
    page.overlay.append(snack)

    def note(msg):
        snack.content = ft.Text(msg)
        snack.open = True
        page.update()

    def do_copy(text):
        try:
            page.clipboard.set(text)  # Flet >= 0.80: Clipboard-Service
            note("In Zwischenablage kopiert.")
        except Exception as ex:
            note("Kopieren nicht möglich: %s" % ex)

    # ---------------- Profil-Ansicht ----------------
    profile_col = ft.Column(spacing=8, scroll=ft.ScrollMode.AUTO,
                            expand=True)

    def ctx_options():
        return [ft.dropdown.Option(str(c)) for c in CTX]

    def refresh_profile():
        s, base = eff(cur["key"], cur["alvl"], overrides)
        vram = est_vram(base, s)
        ctrls = []
        if cur["key"] == "audio":
            row = ft.Row(spacing=6)
            for lv in ("min", "normal", "max"):
                def _mk(lv):
                    return ft.ElevatedButton(
                        lv.upper(),
                        bgcolor=TASKS["audio"]["color"]
                        if lv == cur["alvl"] else None,
                        on_click=lambda e, lv=lv: (
                            cur.update(alvl=lv), refresh_all()))
                row.controls.append(_mk(lv))
            ctrls.append(ft.Text("Genauigkeits-Stufe",
                                 weight=ft.FontWeight.BOLD))
            ctrls.append(row)
            ctrls.append(ft.Text(s["model"], size=18,
                                 weight=ft.FontWeight.BOLD))
            ctrls.append(ft.Text(s.get("desc", ""), color=ft.Colors.GREY))

        def dropdown(label, key, options, cur_val, parse=str):
            dd = ft.Dropdown(label=label, value=str(cur_val),
                             options=[ft.dropdown.Option(str(o))
                                      for o in options],
                             on_change=lambda e, k=key, p=parse: (
                                 overrides.setdefault(
                                     cur["key"] if cur["key"] != "audio"
                                     else "audio:" + cur["alvl"], {})
                                 .update({k: p(e.control.value)}),
                                 refresh_all()))
            return dd

        ctrls.append(dropdown("Context Length", "ctx", CTX, s["ctx"], int))
        ctrls.append(dropdown("Evaluation Batch", "batch", BATCH,
                              s["batch"], int))
        ctrls.append(dropdown("KV Quant", "kv",
                              ["Q8_0", "Q4_0", "Q5_K_M", "F16"], s["kv"]))
        ctrls.append(dropdown("Speculative Decoding", "spec",
                              ["OFF", "MTP"], s["spec"]))
        ctrls.append(ft.Text("GPU Offload: %d Layer" % s["layers"]))
        ctrls.append(ft.Text("CPU Threads: %d" % s["threads"]))
        ctrls.append(ft.ProgressBar(value=min(1.0, vram / 8.0)))
        ctrls.append(ft.Text("VRAM ca. %.1f / 8.0 GB" % vram,
                             weight=ft.FontWeight.BOLD))
        ctrls.append(ft.Text("Modell: %s" % s["model"]))
        ctrls.append(ft.Text("Tempo: %s · Stabil: %s"
                             % (s.get("tok", "?"), s.get("stab", "?")),
                             color=ft.Colors.GREY))
        if TASKS[cur["key"]].get("warn"):
            ctrls.append(ft.Text("WARNUNG: "
                                 + TASKS[cur["key"]]["warn"],
                                 color=ft.Colors.RED))
        ctrls.append(ft.Row([
            ft.ElevatedButton("Werte kopieren",
                              on_click=lambda e: do_copy(
                                  "%s\nModell: %s\nctx=%s layers=%s kv=%s "
                                  "batch=%s threads=%s" % (
                                      s.get("name", "?"), s["model"],
                                      s["ctx"], s["layers"], s["kv"],
                                      s["batch"], s["threads"]))),
            ft.ElevatedButton("JSON kopieren",
                              on_click=lambda e: do_copy(preset_json(s))),
        ], spacing=6))
        ctrls.append(ft.TextField(label="LM-Studio-Preset (JSON)",
                                  value=preset_json(s), multiline=True,
                                  min_lines=6, max_lines=12, read_only=True))
        for a in TASKS[cur["key"]].get("alts", []):
            ctrls.append(ft.TextButton(
                "• " + a, on_click=lambda e, a=a: do_copy(a)))
        profile_col.controls = ctrls

    # ---------------- Dashboard ----------------
    dash_col = ft.Column(spacing=4, scroll=ft.ScrollMode.AUTO, expand=True)

    def refresh_dash():
        rows = []
        live = "n/a (mobil)"
        if HAS_PSUTIL:
            try:
                m = psutil.virtual_memory()
                live = ("RAM %.1f/%.1f GB (%.0f%%) · CPU %.0f%%"
                        % ((m.total - m.available) / 1024.0**3,
                           m.total / 1024.0**3, m.percent,
                           psutil.cpu_percent(interval=None)))
            except Exception:
                pass
        keep = dict(cur)
        for k in TASKS.keys():
            if k == "audio":
                for lv in ("min", "normal", "max"):
                    cur["key"], cur["alvl"] = k, lv
                    s, b = eff(k, lv, overrides)
                    rows.append((k, "Audio " + lv.upper(),
                                 est_vram(b, s), s))
            else:
                cur["key"] = k
                s, b = eff(k, cur["alvl"], overrides)
                rows.append((k, TASKS[k]["name"], est_vram(b, s), s))
        cur.update(keep)
        data_rows = []
        for k, label, v, s in rows:
            col = (ft.Colors.RED if v >= 7.9
                   else (ft.Colors.AMBER if v >= 7.4 else ft.Colors.CYAN))
            sym = "✕" if v >= 7.9 else ("!" if v >= 7.4 else "✓")
            data_rows.append(ft.DataRow(cells=[
                ft.DataCell(ft.TextButton(
                    label, on_click=lambda e, k=k: (
                        cur.update(key=k), tabs.__setattr__(
                            "selected_index", 0), refresh_all()))),
                ft.DataCell(ft.Text("%s %.1f" % (sym, v), color=col)),
                ft.DataCell(ft.Text("%dk" % round(s["ctx"] / 1024))),
            ]))
        dash_col.controls = [
            ft.Text("Live: " + live, color=ft.Colors.GREY),
            ft.DataTable(
                columns=[ft.DataColumn(ft.Text("Profil")),
                         ft.DataColumn(ft.Text("VRAM"),
                                       numeric=True),
                         ft.DataColumn(ft.Text("Ctx"), numeric=True)],
                rows=data_rows),
            ft.Text("✓ <7.4 passt · ! 7.4–7.8 eng · ✕ ≥7.9 kritisch",
                    color=ft.Colors.GREY),
        ]

    # ---------------- Suche ----------------
    search_col = ft.Column(spacing=8, scroll=ft.ScrollMode.AUTO, expand=True)
    q_field = ft.TextField(label="Hugging Face Suche", value="",
                           on_submit=lambda e: do_hf())
    res_list = ft.ListView(spacing=4, expand=True)

    def do_hf():
        q = (q_field.value or "").strip()
        if not q:
            s, _ = eff(cur["key"], cur["alvl"], overrides)
            q = s.get("search", "")
            q_field.value = q
        res_list.controls = [ft.Text("Suche läuft …")]
        page.update()
        try:
            hits = hf_search(q)
            if not hits:
                res_list.controls = [ft.Text("Keine Treffer.")]
            else:
                res_list.controls = [
                    ft.TextButton(
                        "%s · %d DL" % (h["id"][:52], h["dl"]),
                        on_click=lambda e, h=h: do_copy(h["id"]))
                    for h in hits]
        except Exception as ex:
            res_list.controls = [ft.Text("Fehler: %s" % ex,
                                         color=ft.Colors.RED)]
        page.update()

    search_col.controls = [
        q_field,
        ft.ElevatedButton("Suchen", on_click=lambda e: do_hf()),
        res_list,
    ]

    # ---------------- Tabs ----------------
    def refresh_all():
        refresh_profile()
        refresh_dash()
        page.update()

    prof_select = ft.Dropdown(
        label="Profil",
        value=cur["key"],
        options=[ft.dropdown.Option(k, TASKS[k]["name"]) for k in TASKS],
        on_change=lambda e: (cur.update(key=e.control.value),
                             refresh_all()))
    tabs = ft.Tabs(
        selected_index=0,
        tabs=[ft.Tab(text="Profil", content=ft.Column(
                 [prof_select, profile_col], spacing=8, expand=True)),
              ft.Tab(text="Dashboard", content=dash_col),
              ft.Tab(text="Suche", content=search_col)],
        expand=True)
    page.add(tabs)
    refresh_all()


if __name__ == "__main__":
    ft.app(target=main)
