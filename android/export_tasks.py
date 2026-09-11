#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Exportiert TASKS + DEFAULTS aus lm_studio_optimizer_v3.py nach tasks.json.

Single Source of Truth fuer PWA und Flet-App. Liest per AST (kein Import,
kein tkinter/psutil noetig) und wendet DEFAULTS wie die Desktop-App an.

Aufruf:  python android/export_tasks.py
Schreibt: android/tasks.json, android/pwa/tasks.json und
          android/flet/tasks.json (jeweils Kopien derselben Quelle)
"""
import ast
import json
import os
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(os.path.dirname(HERE), "lm_studio_optimizer_v3.py")


def main():
    with open(SRC, "r", encoding="utf-8") as f:
        tree = ast.parse(f.read())
    mod = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 \
                and isinstance(node.targets[0], ast.Name) \
                and node.targets[0].id in ("TASKS", "DEFAULTS"):
            mod[node.targets[0].id] = ast.literal_eval(node.value)
    tasks, defaults = mod["TASKS"], mod["DEFAULTS"]
    for p in tasks.values():
        for dk, dv in defaults.items():
            p.setdefault(dk, dv)
    out = {"app": "LM Studio Optimizer",
           "exported": datetime.now(timezone.utc).isoformat(timespec="seconds"),
           "defaults": defaults,
           "profiles": tasks}
    targets = [os.path.join(HERE, "tasks.json"),
               os.path.join(HERE, "pwa", "tasks.json"),
               os.path.join(HERE, "flet", "tasks.json")]
    for t in targets:
        with open(t, "w", encoding="utf-8") as f:
            json.dump(out, f, indent=2, ensure_ascii=False)
        print("wrote %s (%d profiles)" % (t, len(tasks)))


if __name__ == "__main__":
    main()
