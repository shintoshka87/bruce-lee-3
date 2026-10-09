# -*- coding: utf-8 -*-
"""plan.json -> app.json: к каждому упражнению добавляет машинную спецификацию подходов,
к кондиции — последовательность отрезков таймера. Текст плана не меняется."""
import json, re, sys, os

here = sys.argv[1]
D = json.load(open(os.path.join(here, "plan.json"), encoding="utf-8"))

WT = {}
for k in "squat bench rdl deadlift".split(): WT[k] = "bar"
for k in "goblet bss revlunge row_chest row_one incline_db hk_press db_press_stand push_press_db zottman farmer suitcase db_swing".split(): WT[k] = "db"
for k in "leg_curl hip_thrust calf adductor tbar_cs cable_row face_pull rear_fly ext_rot preacher pushdown pallof chop".split(): WT[k] = "mach"
WT["pullup"] = "assist"
for k in "plyo_push pushup_pause dead_bug side_plank knee_raise ab_wheel hyperext wall_sit jump".split(): WT[k] = "bw"
WT["bike_sprint"] = "watt"
for k in "band_face_pull band_pull_apart band_curl band_hammer band_ohe band_pallof band_ext_rot band_adduct".split(): WT[k] = "band"
WT["calf_step"] = "bw"
for k in D["ex"]:
    assert k in WT, k
    D["ex"][k]["wt"] = WT[k]
MAIN = {"squat", "bench", "rdl", "deadlift"}


def num(s):
    return float(s.replace(",", "."))


def rest_sec(r):
    if not r: return 0
    if r.startswith("без отдыха"): return 0
    m = re.match(r"(\d+(?:,\d+)?)(?:–(\d+(?:,\d+)?))? (мин|с)", r)
    if not m: raise ValueError(r)
    a = num(m.group(1)); b = num(m.group(2)) if m.group(2) else a
    v = (a + b) / 2
    return int(round(v * (60 if m.group(3) == "мин" else 1)))


def rpe_of(load):
    m = re.search(r"RPE (\d+(?:,\d+)?)(?:–(\d+(?:,\d+)?))?", load)
    if not m: return None
    a = num(m.group(1)); b = num(m.group(2)) if m.group(2) else a
    return (a + b) / 2


def spec_for(day, it):
    ex, sets, load = it["ex"], it["sets"], it["load"]
    s = dict(wt=WT[ex], unit="reps", side=None, rows=[], rest=rest_sec(it["rest"]),
             pairNext=it["rest"].startswith("без отдыха"), main=ex in MAIN, deload=bool(day["dl"]), test=False)
    rpe = rpe_of(load)
    m = re.search(r" на (ногу|руку|сторону)$", sets)
    if m: s["side"] = m.group(1); sets = sets[:m.start()]
    # тесты
    if sets.startswith("тест"):
        s["test"] = True
        if sets in ("тест 5ПМ", "тест 3ПМ", "тест 6ПМ"):
            r = int(re.search(r"(\d)ПМ", sets).group(1))
            s["rows"].append(dict(kind="test", lo=r, hi=r, rpe=rpe))
            back = {"squat": (2, 5, 10), "bench": (2, 5, 15)}.get(ex)
            if back:
                for _ in range(back[0]): s["rows"].append(dict(kind="back", lo=back[1], hi=back[1], rpe=None, drop=back[2]))
        elif sets == "тест на максимум":
            s["rows"].append(dict(kind="amrap", lo=None, hi=None, off=0, rpe=None))
        elif sets == "тест на время":
            s["unit"] = "sec"; s["side"] = "сторону"; s["open"] = True
            s["rows"].append(dict(kind="work", lo=None, hi=None, rpe=None))
        elif sets == "тест 3 × 8 с":
            s["unit"] = "sec"
            for _ in range(3): s["rows"].append(dict(kind="work", lo=8, hi=8, rpe=None))
        else:
            raise ValueError(sets)
        return s
    # топ-сет + добивка
    m = re.match(r"^1 × (\d+) \+ (\d+) × (\d+)$", sets)
    if m:
        top_r, bn, br = int(m.group(1)), int(m.group(2)), int(m.group(3))
        md = re.search(r"−(\d+)% от топа", load)
        s["rows"].append(dict(kind="top", lo=top_r, hi=top_r, rpe=rpe))
        for _ in range(bn): s["rows"].append(dict(kind="back", lo=br, hi=br, rpe=None, drop=int(md.group(1))))
        return s
    # макс − k
    m = re.match(r"^(\d+) × \(макс − (\d+)\)$", sets)
    if m:
        for _ in range(int(m.group(1))): s["rows"].append(dict(kind="amrap", lo=None, hi=None, off=int(m.group(2)), rpe=rpe))
        return s
    m = re.match(r"^(\d+) × (\d+(?:,\d+)?)(?:–(\d+))?(?: (с|м|мин))?$", sets)
    if not m: raise ValueError((ex, sets))
    n = int(m.group(1)); lo = num(m.group(2)); hi = num(m.group(3)) if m.group(3) else lo
    unit = m.group(4)
    if unit == "мин": s["unit"] = "sec"; lo *= 60; hi *= 60
    elif unit == "с": s["unit"] = "sec"
    elif unit == "м": s["unit"] = "m"
    pct = None
    mp = re.match(r"≈(\d+)% от 1ПМ · RPE 6", load)
    if mp: pct = int(mp.group(1))
    for _ in range(n):
        row = dict(kind="work", lo=int(lo), hi=int(hi), rpe=rpe)
        if pct: row["pct"] = pct
        s["rows"].append(row)
    return s


# ---------- отрезки таймера для кондиции ----------
def segs_for(cd):
    k, n = cd.get("kind"), cd.get("n")
    S = []
    def add(label, sec, kind, tip=""): S.append(dict(l=label, s=sec, k=kind, t=tip))
    if k in ("z2", "z2home"):
        add("Зона 2", n * 60, "work", "пульс 118–135, можешь говорить фразами")
    elif k == "series":
        hard = "RPE 8 — сильно, но не на пределе" if cd.get("inten") == "8" else "максимум"
        add("Разминка, легко", 180, "warm")
        for i in range(1, n + 1):
            add("Серия %d из %d — легко" % (i, n), 60, "easy")
            add("Серия %d из %d — СИЛЬНО" % (i, n), 30, "work", hard)
            add("Очень легко", 60, "rest")
    elif k == "4x4":
        add("Разминка, легко", 300, "warm")
        for i in range(1, n + 1):
            add("Отрезок %d из %d" % (i, n), 240, "work", "к концу отрезка пульс 160–172")
            if i < n: add("Легко", 180, "rest", "пульс ниже 120")
    elif k == "circ1":
        for i in range(1, n + 1):
            add("Круг %d из %d" % (i, n), 0, "open", "гоблет-присед 12 → отжимания 10 → тяга гантели 10/рука → обратные выпады 8/нога → махи 12 → дед баг 8/сторона → скакалка 40 с")
            if i < n: add("Отдых шагом", 120, "rest")
    elif k == "circ2":
        st = ["Махи гантелью", "Отжимания", "Тяга гантели с упором в скамью (по 20 с на руку)", "Гоблет-присед", "Обратные выпады",
              "Ролик с колен", "Скакалка", "Бой с тенью — максимальный темп"]
        for i in range(1, n + 1):
            for j, name in enumerate(st):
                add(name, 40, "work", "круг %d из %d" % (i, n))
                if j < len(st) - 1: add("Переход → " + st[j + 1], 20, "rest")
            if i < n: add("Отдых между кругами", 120, "rest")
    elif k == "rounds":
        base = {5: [("Бой с тенью — разминка", 180), ("Скакалка", 120), ("Мешок — одиночные удары", 180), ("Мешок — комбинации", 180), ("Бой с тенью — заминка", 120)],
                6: [("Бой с тенью — разминка", 180), ("Бой с тенью — на скорость", 120), ("Скакалка", 180), ("Мешок — одиночные удары", 180), ("Мешок — комбинации", 180), ("Бой с тенью — заминка", 180)],
                7: [("Бой с тенью — разминка", 180), ("Бой с тенью — на скорость", 120), ("Скакалка", 180), ("Мешок — одиночные удары", 180), ("Мешок — комбинации", 180), ("Мешок — на пределе", 120), ("Бой с тенью — заминка", 180)]}[n]
        for j, (name, sec) in enumerate(base):
            add(name, sec, "work", "раунд %d из %d" % (j + 1, n))
            if j < len(base) - 1: add("Отдых", 60, "rest")
    elif k == "bag3":
        for i in range(1, 4):
            add("Мешок на скорость, раунд %d из 3" % i, 120, "work")
            if i < 3: add("Отдых", 60, "rest")
    elif k == "bike12":
        add("Разминка", 180, "warm")
        add("Тест: максимум дистанции", 720, "work", "один уровень сопротивления, ровный темп")
        add("Стоп. Пульс через 1 мин", 60, "rest", "запиши дистанцию и пульс")
    else:
        raise ValueError(k)
    return S


def rope_segs(rope):
    if not rope: return []
    m = re.search(r"(\d+) × (\d+) с", rope)
    if m:
        n, sec = int(m.group(1)), int(m.group(2)); out = []
        for i in range(n):
            out.append(dict(l="Скакалка %d из %d" % (i + 1, n), s=sec, k="work", t=""))
            if i < n - 1: out.append(dict(l="Пауза", s=30, k="rest", t=""))
        return out
    m = re.search(r"(\d+) мин", rope)
    return [dict(l="Скакалка", s=int(m.group(1)) * 60, k="work", t="")]


cnt = 0
for day in D["days"]:
    for it in day.get("items", []):
        if "cond" in it:
            it["cond"]["segs"] = segs_for(it["cond"]); continue
        it["spec"] = spec_for(day, it); cnt += 1
    if day.get("cond"):
        day["cond"]["segs"] = segs_for(day["cond"])
    if day.get("rope"):
        day["ropeSegs"] = rope_segs(day["rope"])
json.dump(D, open(os.path.join(here, "app.json"), "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
print("items", cnt, "bytes", os.path.getsize(os.path.join(here, "app.json")))
