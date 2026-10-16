"""Собирает приложение «Брюс Ли 4.0».

plan.py + exercises.py -> appdata.py -> build-data/data.json
web/app.html + data.json -> app/src/main/assets/index.html (то, что открывает APK)
                         -> build-data/web.html (копия для веб-версии в Claude: без обёртки документа и без локальных шрифтов)

Запуск: python3 tools/build.py
"""
import json, os, re, subprocess, sys

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
tools = os.path.join(root, "tools")
out = os.path.join(root, "build-data")
os.makedirs(out, exist_ok=True)

data_path = os.path.join(out, "data.json")
subprocess.check_call([sys.executable, "-I", os.path.join(tools, "appdata.py"), data_path])
data = open(data_path, encoding="utf-8").read()
plan = json.loads(data)
print("дней в плане:", len(plan["days"]))
data = data.replace("</", "<\\/")

tpl = open(os.path.join(root, "web", "app.html"), encoding="utf-8").read()
assert tpl.count("__PLAN_DATA__") == 1, "в web/app.html должна быть ровно одна метка __PLAN_DATA__"
html = tpl.replace("__PLAN_DATA__", data)
index = os.path.join(root, "app", "src", "main", "assets", "index.html")
open(index, "w", encoding="utf-8").write(html)
print("index.html", len(html.encode("utf-8")), "bytes")

# Веб-версия для Claude
title = "<title>План «Брюс Ли 4.0»</title>"
style = re.search(r"<style>([\s\S]*?)</style>", html).group(1)
style = re.sub(r"@font-face\{[^}]*\}\n?", "", style)
body = re.search(r"<body>\n?([\s\S]*)</body>", html).group(1)
web = title + "\n<style>\n" + style.lstrip("\n") + "</style>\n" + body
open(os.path.join(out, "web.html"), "w", encoding="utf-8").write(web)
print("web.html", len(web.encode("utf-8")), "bytes")
