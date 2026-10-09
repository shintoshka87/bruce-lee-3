"""Собирает приложение: план -> app.json -> app/src/main/assets/index.html (+ копия для веб-версии)."""
import os, subprocess, sys, json
root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
tools = os.path.join(root, "tools")
out = os.path.join(root, "build-data")
os.makedirs(out, exist_ok=True)
subprocess.check_call([sys.executable, "-I", os.path.join(tools, "gen.py"), tools, os.path.join(out, "plan.json")])
subprocess.check_call([sys.executable, "-I", os.path.join(tools, "spec.py"), out])
data = open(os.path.join(out, "app.json"), encoding="utf-8").read().replace("</", "<\\/")
tpl = open(os.path.join(root, "web", "app.html"), encoding="utf-8").read()
html = tpl.replace("/*DATA*/", data)
open(os.path.join(root, "app", "src", "main", "assets", "index.html"), "w", encoding="utf-8").write(html)
print("index.html", len(html.encode("utf-8")), "bytes")

# Веб-версия для Claude: без обёртки документа и без локальных шрифтов
import re
title = "<title>План «Брюс Ли 3.0»</title>"
style = re.search(r"<style>([\s\S]*?)</style>", html).group(1)
style = re.sub(r"@font-face\{[^}]*\}\n?", "", style)
body = re.search(r"<body>([\s\S]*)</body>", html).group(1)
web = title + "\n<style>" + style + "</style>\n" + body
open(os.path.join(out, "web.html"), "w", encoding="utf-8").write(web)
print("web.html", len(web.encode("utf-8")), "bytes")
