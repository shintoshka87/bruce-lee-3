# -*- coding: utf-8 -*-
"""plan.json -> print.html (часть 2 PDF: план по дням)"""
import json, sys, os, html
here = sys.argv[1]
D = json.load(open(os.path.join(here, "plan.json"), encoding="utf-8"))
EX, DAYS, WEEKS, PH = D["ex"], D["days"], D["weeks"], D["phases"]
PCOL = ["#5F7180", "#1D7560", "#A23E27", "#9A6A0B", "#3A49A3"]
DLCOL = "#7E8781"
e = html.escape

RITUAL = [
    "<b>Растяжка сгибателей бедра на колене — 30–45 с на сторону.</b> Встань на одно колено (под него полотенце), передняя стопа на полу, оба колена под 90°, корпус вертикально. Подкрути таз (копчик вниз, лобок к пупку), сожми ягодицу ноги на полу и подайся вперёд всего на 3–5 см. Тянет спереди бедра и в паху, а не в пояснице. Наклон таза растяжка не меняет — она ради комфорта после смены.",
    "<b>Подъёмы на носки на одной ноге — 1 × 12–20 на каждую ногу.</b> Вверх 1 с, вниз 3 с, пауза внизу; 1–2 повтора в запасе. 20 повторов без боли — допуск к прыжкам на носках.",
    "<b>Дед баг — 6 на сторону, медленно.</b> 3 с на опускание руки и противоположной ноги; поясница не отрывается от пола.",
]
WARMUP = [
    "<b>Кардио 5 мин</b> на вертикальном велотренажёре или эллипсе, пульс 100–120.",
    "<b>Мобильность 3 мин:</b> «величайшая растяжка» 3 на сторону (выпад, локоть к полу, рука вверх с поворотом груди); 90/90 для бёдер 5 на сторону (сидя, переводи колени из стороны в сторону); «открытая книга» 5 на сторону (лёжа на боку, разворачивай руку и грудь к полу за спиной).",
    "<b>Активация 2 мин:</b> тяга каната к лицу лёгким весом × 15, гоблет-присед с лёгкой гантелью и паузой × 6, отжимания × 5.",
    "<b>Скакалка</b> — только если указана в дне (с 5-го цикла). С 9-го цикла в разминке A после скакалки — прыжки на носках микродозами, если ахилл готов.",
    "<b>Подводящие к первому силовому:</b> гриф × 8 → 50% × 5 → 70% × 3 → 85% × 1–2.",
]
COOLDOWN = [
    "<b>3–4 мин лёгкого велотренажёра</b> — пульс ниже 110.",
    "<b>Сгибатели бедра — 60 с на сторону:</b> колено на полу у скамьи, голень вверх по скамье, таз подкручен, ягодица сжата.",
    "<b>Грудные на стойке — 45 с на сторону</b> (предплечье на стойке, корпус медленно разворачивается от руки). <b>Широчайшие — 45 с</b> (держись за стойку, таз назад).",
    "<b>Задняя поверхность бедра — 45 с на сторону:</b> пятка на скамье, наклон от таза с ровной спиной.",
    "<b>Поза ребёнка — 1 мин</b> с длинным выдохом в спину и бока.",
]
HOME = [
    "<b>Только велотренажёр</b> — время указано в дне. Во вводных и разгрузочных циклах легко (пульс 105–125), в волнах — зона 2 (118–135; во вторую смену нижняя часть, 118–128). Устал после смены — 20 мин совсем легко или прогулка.",
    "<b>По желанию, 5 мин:</b> растяжка сгибателей бедра 45 с на сторону, поза ребёнка 1 мин.",
]
SHIFT_C = "Эспандер в перерывах: 3–5 подходов на руку. Каждые 60–90 мин — 2–3 мин движения. Вода около 2 л, креатин 3–5 г."
SHIFT_R = "Эспандер — 3 подхода на руку, легче, чем вчера. Движение каждые 60–90 мин. Вода около 2 л, креатин 3–5 г."
WHERE = {"C": "Смена 1", "R": "Смена 2", "A": "Выходной 1", "B": "Выходной 2"}


def ol(lst):
    return "<ol>" + "".join("<li>%s</li>" % x for x in lst) + "</ol>"


def cond_html(cd):
    return ('<div class="cond"><div class="ch"><b>%s</b><span>≈ %d мин</span></div><ul>%s</ul></div>'
            % (e(cd["title"]), cd["mins"], "".join("<li>%s</li>" % e(l) for l in cd["lines"])))


def ex_table(items):
    rows = []
    for i in items:
        if "cond" in i:
            rows.append('<tr class="condrow"><td colspan="6">%s</td></tr>' % cond_html(i["cond"]))
            continue
        x = EX[i["ex"]]
        pair = i["lab"][-1] in "ab"
        sub = []
        if i.get("note"): sub.append(e(i["note"]))
        sub.append("<i>Если занято:</i> " + e(x["alt"]))
        rows.append(
            '<tr class="%s"><td class="lab">%s</td><td><b>%s</b><div class="sub">%s</div></td><td class="mono">%s</td><td>%s</td><td>%s</td><td class="rec"></td></tr>'
            % ("pair" if pair else "", e(i["lab"]), e(x["name"]), "<br>".join(sub), e(i["sets"]), e(i["load"]), e(i["rest"])))
    return ('<table class="ex"><thead><tr><th>№</th><th>Упражнение</th><th>Подходы</th><th>Нагрузка</th><th>Отдых</th><th>Запись</th></tr></thead><tbody>%s</tbody></table>'
            % "".join(rows))


def day_html(d):
    col = DLCOL if d["dl"] else PCOL[d["p"]]
    chips = ['<span class="chip" style="background:%s">%s</span>' % (PCOL[d["p"]], PH[d["p"]])]
    if d["dl"]: chips.append('<span class="chip ghost">Разгрузка</span>')
    if d["test"]: chips.append('<span class="chip ghost">Тесты</span>')
    if d["diet"]: chips.append('<span class="chip ghost">Перерыв в диете</span>')
    title = d["title"].split("·", 1)[1].strip()
    title = title[0].upper() + title[1:]
    out = ['<section class="day" style="--pc:%s">' % col,
           '<div class="dh"><span class="dn">День %d</span><span class="dm">неделя %d · цикл %d · %s</span>%s<span class="chk">☐ сделано</span></div>'
           % (d["d"], d["w"], d["c"], WHERE[d["k"]], "".join(chips)),
           '<h3>%s</h3><p class="goal">%s <span class="time">Время: %s.</span></p>' % (e(title), e(d["goal"]), e(d["time"]))]
    out.append('<p class="line"><b>Утро:</b> короткий ритуал, 5 мин (стр. «Стандартные блоки»).</p>')
    if d["k"] == "C":
        out.append('<p class="line"><b>На смене:</b> %s</p>' % SHIFT_C)
        out.append('<p class="line"><b>После смены — только велотренажёр.</b> Ничего силового: вся силовая работа в зале. Первые 3 мин — разминка.</p>')
        out.append(ex_table(d["items"]))
        out.append('<p class="line small"><b>Нет сил или спал меньше 6 ч:</b> 20 мин совсем легко; совсем плохо — прогулка 30 мин или отдых.</p>')
    elif d["k"] == "R":
        out.append('<p class="line"><b>На смене:</b> %s</p>' % SHIFT_R)
        bike = ("зона 2 на велотренажёре <b>%d мин</b> (пульс 118–128, ровно)" if d.get("rk") == "z2" else "лёгкий велотренажёр <b>%d мин</b> (пульс 105–125)") % (d.get("easy") or 25)
        out.append('<p class="line"><b>После смены — только</b> %s. По желанию 5 мин растяжки. Никаких интервалов: завтра тренировка A. Устал — 20 мин совсем легко или прогулка.</p>' % bike)
        out.append('<p class="line small"><b>Сон:</b> перед тренировкой A — 7+ ч, экран убрать за 45 мин.</p>')
    else:
        wu = "Разминка 12 мин (стр. «Стандартные блоки»)" + ((". " + e(d["rope"])) if d.get("rope") else "") + "."
        out.append('<p class="line"><b>%s</b></p>' % wu)
        out.append(ex_table(d["items"]))
        if d.get("cond"):
            if d["k"] == "A" and not d["test"]:
                out.append('<p class="line"><b>Аэробный финиш</b> — сразу после силовой, перед растяжками.</p>')
            out.append(cond_html(d["cond"]))
        out.append('<p class="line small"><b>Заминка 8 мин.</b> ' + ("" if d["test"] else "<b>Тяжёлый день:</b> разминка, первые два основных упражнения и 10 мин зоны 2. ") +
                   "<b>Еда:</b> за 2–3 ч до зала обычный приём пищи, после — 40 г белка и рис, картофель или фрукты." +
                   (" Перерыв в диете: около 2700 ккал." if d["diet"] else "") + "</p>")
    if d["k"] in "CR" and d["diet"]:
        out.append('<p class="line small"><b>Перерыв в диете (дни 77–88):</b> около 2700 ккал за счёт углеводов.</p>')
    out.append('<div class="notes">Сон ___ ч · пульс покоя ___ · самочувствие ___/10 · заметки:</div>')
    out.append("</section>")
    return "\n".join(out)


def week_html(w):
    ds = [d for d in DAYS if d["w"] == w["w"]]
    cyc = w["cycles"]
    ct = "циклы %d–%d" % (cyc[0], cyc[-1]) if len(cyc) > 1 else "цикл %d" % cyc[0]
    head = ('<header class="wk" id="w%d" style="--pc:%s"><div class="wkn">Неделя %d</div><div class="wkm">%s · %s · дни %d–%d</div><p>%s</p></header>'
            % (w["w"], PCOL[w["p"]], w["w"], PH[w["p"]], ct, ds[0]["d"], ds[-1]["d"], e(w["note"])))
    return '<div class="week">' + head + "".join(day_html(d) for d in ds) + "</div>"


USED = {i["ex"] for d in DAYS for i in d.get("items", []) if "ex" in i}


def ref_html():
    order = ["Ноги", "Задняя цепь", "Грудь", "Спина", "Плечи", "Руки", "Кор", "Хват и кор", "Икры и ахилл", "Таз", "Мощность", "Давление", "Дома: резина"]
    out = ['<div class="week ref"><header class="wk" style="--pc:#16201B"><div class="wkn">Техника упражнений</div><p>Все упражнения программы: как делать, частая ошибка и чем заменить, если снаряд занят.</p></header>']
    for g in order:
        ks = [k for k in EX if EX[k]["group"] == g and (k in USED or k == "pogo")]
        if not ks: continue
        out.append("<h4>%s</h4>" % g)
        for k in ks:
            x = EX[k]
            out.append('<div class="refex"><b>%s</b><p>%s</p><p><i>Ошибка:</i> %s</p><p><i>Если занято:</i> %s</p></div>' % (e(x["name"]), e(x["how"]), e(x["err"]), e(x["alt"])))
    out.append("</div>")
    return "".join(out)


def intro_html():
    rpe = [[1, 89, 92, 96], [2, 86, 89, 92], [3, 84, 86, 89], [4, 81, 84, 86], [5, 79, 81, 84], [6, 76, 79, 81], [8, 72, 74, 76]]
    t = "".join("<tr><td>%d</td><td>%d%%</td><td>%d%%</td><td>%d%%</td></tr>" % tuple(r) for r in rpe)
    return """
<div class="week intro">
<header class="wk" style="--pc:#16201B"><div class="wkn">Часть 2. План по дням</div><p>140 дней = 35 циклов по 4 дня. День 1 — твоя первая смена после выходных. Цикл: смена 1 (сессия C дома после работы) → смена 2 (восстановление дома) → выходной 1 (тренировка A) → выходной 2 (тренировка B).</p></header>
<h4>Как читать день</h4>
<ul>
<li><b>Пары 4a / 4b</b> — суперсет: подход 4a, сразу подход 4b, отдых, снова 4a. Пара всегда «одна станция + упражнение рядом без станции», чтобы не держать два снаряда в людном зале.</li>
<li><b>Если занято</b> — замена указана под каждым упражнением. Ждать дольше 3 минут не нужно.</li>
<li><b>Запись</b> — пустая колонка для веса × повторов и запаса. Оценка максимума = вес ÷ процент из таблицы ниже.</li>
<li><b>Пропустил день</b> — не делай две тренировки подряд, просто сдвинь план. Выпал один выходной — делай ту тренировку, которая была давно.</li>
<li>Интерактивная версия с датами и дневником: claude.ai/artifact/NSYizs6ECC8Bthdd68hoKX</li>
</ul>
<div class="two">
<div><h4>Запас повторов</h4><p class="small">Сколько ещё повторов ты сделал бы чисто. Смотри на скорость последних повторов:</p><ul class="small">
<li><b>4+</b> — все повторы одинаково быстрые; для рабочего подхода легко.</li>
<li><b>3</b> — последний повтор чуть медленнее первого.</li>
<li><b>2</b> — последние 1–2 повтора заметно медленнее, техника та же. Главная цель.</li>
<li><b>1</b> — последний повтор «ползёт», ещё один — точно последний.</li>
<li><b>0</b> — повтор встал или техника поплыла. Так не делаем.</li></ul>
<p class="small">Проверка себя: первые 2 недели в последнем подходе на тренажёре продолжи после нужных повторов, пока скорость держится, и посчитай лишние.</p>
<h4>Запас и %% от максимума</h4>
<table class="rpe"><thead><tr><th>Повторы</th><th>запас 3</th><th>запас 2</th><th>запас 1</th></tr></thead><tbody>%s</tbody></table></div>
<div><h4>Саморегуляция</h4><ul class="small">
<li><b>Светофор каждое утро:</b> сон меньше 6 ч · пульс покоя на 7+ выше обычного · тяжёлые ноги или настроение ниже 5/10. Ни одного — по плану; один — интервалы заменить зоной 2, в силовой минус подход; два-три — прогулка 30 мин и растяжка.</li>
<li>Боль в суставе больше 3 из 10 или нарастает — бери замену.</li>
<li>Две плохие тренировки подряд — внеплановый разгрузочный цикл.</li>
<li>Давление перед тренировкой выше 160/100 — только зона 2 и визит к врачу.</li></ul></div>
</div>
<h4 id="std">Стандартные блоки</h4>
<div class="two">
<div><b>Короткий ритуал — каждое утро, 5 мин</b>%s</div>
<div><b>Разминка перед A и B — 12 мин, без исключений</b>%s<p class="small">Ли повредил крестцовый нерв, сделав «доброе утро» с весом своего тела без разминки.</p></div>
</div>
<div class="two">
<div><b>Заминка — 8 мин</b>%s</div>
<div><b>Дома после смен — только велотренажёр</b>%s</div>
</div>
<h4>День 0 — до старта</h4>
<ul class="small">
<li><b>Врач:</b> ЭКГ (лучше с нагрузкой), давление, липидограмма, глюкоза или HbA1c, АЛТ/АСТ, ТТГ, ферритин, витамин D.</li>
<li><b>Купить:</b> бинты и перчатки 14–16 oz, кистевой эспандер, пульсометр, кухонные весы, креатин.</li>
<li><b>Замеры:</b> вес ____ кг · талия ____ см · пульс покоя ____ · давление ______ · фото спереди, сбоку, сзади.</li>
<li><b>Тесты:</b> подтягивания ____ · отжимания ____ · велоспринт 8 с ____ Вт · вело 12 мин ____ (уровень ___, пульс через 1 мин ___) · боковая планка ____ / ____ с · тест Томаса ______ · жим лёжа (известный максимум) ____ кг.</li>
</ul>
</div>""" % (t, ol(RITUAL), ol(WARMUP), ol(COOLDOWN), ol(HOME))


CSS = """
@page { size: A4; margin: 13mm 12mm 14mm 12mm; }
* { box-sizing: border-box; }
body { font-family: "Inter", "DejaVu Sans", sans-serif; font-size: 9pt; line-height: 1.38; color: #16201B; margin: 0; }
h3 { font-size: 11.5pt; margin: 3px 0 2px; }
h4 { font-size: 10.5pt; margin: 12px 0 4px; }
p { margin: 2px 0; }
ul, ol { margin: 3px 0; padding-left: 16px; }
li { margin: 1px 0; }
.small { font-size: 8.3pt; }
.week { break-before: page; }
.wk { border-left: 5px solid var(--pc); padding: 2px 0 4px 10px; margin-bottom: 8px; }
.wkn { font-family: "Inter Display", "Inter", sans-serif; font-weight: 800; font-size: 19pt; line-height: 1.1; }
.wkm { color: #56635C; font-weight: 600; margin: 2px 0; }
.wk p { max-width: 165mm; }
.day { border-top: 2.5px solid var(--pc); padding-top: 5px; margin: 10px 0 6px; }
.dh { display: flex; flex-wrap: wrap; align-items: baseline; gap: 4px 8px; break-after: avoid; }
.dn { font-family: "Inter Display", "Inter", sans-serif; font-weight: 800; font-size: 14pt; }
.dm { color: #56635C; }
.chk { margin-left: auto; color: #56635C; }
.chip { font-size: 7.5pt; font-weight: 700; color: #fff; border-radius: 9px; padding: 0 7px; }
.chip.ghost { color: #16201B; border: 1px solid #9AA39E; background: none; }
.goal { color: #2D3A33; }
.time { color: #56635C; }
.line { margin: 3px 0; }
table.ex { width: 100%; border-collapse: collapse; margin: 4px 0; font-size: 8.4pt; }
table.ex th { text-align: left; font-weight: 600; color: #56635C; border-bottom: 1px solid #9AA39E; padding: 2px 4px; }
table.ex td { border-bottom: 1px solid #D3D9D1; padding: 3px 4px; vertical-align: top; }
table.ex tr { break-inside: avoid; }
table.ex td.lab { font-weight: 700; color: var(--pc); width: 18px; }
table.ex tr.pair td.lab { border-left: 2px solid var(--pc); }
table.ex td.mono { white-space: nowrap; font-weight: 700; }
table.ex td.rec { width: 24mm; border-left: 1px dashed #C9CFC7; }
table.ex col { }
.sub { font-size: 7.6pt; color: #4A564F; margin-top: 1px; }
.cond { border: 1px solid var(--pc); border-radius: 5px; padding: 4px 8px; margin: 5px 0; break-inside: avoid; }
.cond .ch { display: flex; justify-content: space-between; }
.cond .ch span { color: #56635C; }
.cond ul { font-size: 8.2pt; }
tr.condrow td { border-bottom: none; padding: 0; }
.notes { color: #7E8781; font-size: 8pt; border-bottom: 1px dotted #9AA39E; padding-bottom: 10px; margin-top: 4px; }
.two { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; margin: 6px 0; }
table.rpe { border-collapse: collapse; font-size: 8.5pt; }
table.rpe td, table.rpe th { border-bottom: 1px solid #D3D9D1; padding: 2px 8px; text-align: right; }
table.rpe td:first-child, table.rpe th:first-child { text-align: left; }
.refex { break-inside: avoid; margin: 5px 0 7px; }
.refex p { font-size: 8.5pt; }
.ref h4 { border-bottom: 1px solid #D3D9D1; padding-bottom: 2px; }
"""

body = intro_html() + "".join(week_html(w) for w in WEEKS) + ref_html()
doc = '<!doctype html><html lang="ru"><head><meta charset="utf-8"><style>%s</style></head><body>%s</body></html>' % (CSS, body)
open(os.path.join(here, "print.html"), "w", encoding="utf-8").write(doc)
print("ok", len(doc))
