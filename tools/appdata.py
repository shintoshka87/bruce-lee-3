# -*- coding: utf-8 -*-
"""Данные приложения «Брюс Ли 4.0»: 180 дней программы из plan.py и справочник упражнений из exercises.py."""
import importlib.util, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))


def _load(name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(HERE, name + '.py'))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


P = _load('plan')
X = _load('exercises')
EX = X.EX


# ------------------------------------------------------------------ помощники
def seg(l, s, k='work', t=None):
    d = {'l': l, 's': int(round(s)), 'k': k}
    if t:
        d['t'] = t
    return d


def cond(title, segs, lines=None, kind=None):
    c = {'title': title, 'mins': max(1, int(round(sum(x['s'] for x in segs) / 60))), 'lines': lines or [], 'segs': segs}
    if kind:
        c['kind'] = kind
    return {'cond': c}


def hdr(t):
    return {'hdr': t}


def kgs(s):
    return [float(x.replace(',', '.')) for x in re.findall(r'(\d+(?:,\d+)?) кг', s)]


def pg(s):
    m = re.search(r'\(с\. ([^)]+)\)', s)
    return 'с. ' + m.group(1) if m else None


def rest_of(s, default):
    m = re.search(r'отдых (\d+(?:,\d+)?)(?:–(\d+))? (мин|с)', s)
    if not m:
        return default, ''
    a = float(m.group(1).replace(',', '.'))
    b = float(m.group(2)) if m.group(2) else None
    v = (a + b) / 2 if b else a
    return int(round(v * 60 if m.group(3) == 'мин' else v)), m.group(0)[6:]


def clean_how(s):
    s = re.sub(r'(^|;\s*)отдых [^;]+', r'\1', s)
    s = re.sub(r'^≈?\s*\d+(?:,\d+)? кг(?: каждой рукой)?;?\s*', '', s)
    s = re.sub(r'^(\d+(?:,\d+)?) кг и (\d+(?:,\d+)?) кг;?\s*', '', s)
    s = re.sub(r';\s*;', ';', s).strip('; ').strip()
    s = re.sub(r'^≈ (\d+)(?=$|;)', lambda m: P.ud(int(m.group(1))), s)
    return s[:1].upper() + s[1:] if s else ''


def fmt_kg(x):
    return ('%g' % x).replace('.', ',')


def rows(n, lo, hi=None, rpe=None, pw=None, pct=None, lbl=None, kind='work', off=None, reps=None, rr=None):
    out = []
    for i in range(n):
        r = {'kind': kind}
        if lo is not None:
            r['lo'] = lo
            r['hi'] = hi if hi is not None else lo
        if rpe:
            r['rpe'] = rpe
        if pw is not None:
            r['pw'] = pw
        if pct is not None:
            r['pct'] = pct
        if off is not None:
            r['off'] = off
        if reps:
            r['n'] = reps
            r['rr'] = rr or 5
        if lbl is not None:
            r['lbl'] = lbl[i] if isinstance(lbl, list) else lbl
        out.append(r)
    return out


def item(ex, sets, rws, load='', rest=0, rest_txt='', note='', wt=None, unit='reps', per='', main=False, lr=False, page=None, **kw):
    assert ex in EX, ex
    m = re.match(r'^(\d+) × \(максимум − (\d+)\)$', sets)
    if m:  # «2 × (максимум − 3)» не помещается в шапку карточки — «2 подхода», а «максимум минус 3» — в строке веса
        n = int(m.group(1))
        sets = f'{n} ' + ('подход' if n == 1 else 'подхода' if n < 5 else 'подходов')
        load = load or f'В каждом подходе — максимум минус {m.group(2)}'
    sp = {'wt': wt or EX[ex]['wt'], 'unit': unit, 'rows': rws, 'rest': rest}
    if per:
        sp['per'] = per
    if main:
        sp['main'] = True
    if lr:
        sp['lr'] = True
    sp.update(kw)
    it = {'ex': ex, 'sets': sets, 'load': load, 'rest': rest_txt or (fmt_rest(rest) if rest else ''), 'note': note, 'spec': sp}
    if page:
        it['pg'] = page
    return it


def fmt_rest(s):
    if s >= 60 and s % 60 == 0:
        return f'{s // 60} мин'
    if s > 60 and s % 30 == 0:
        return ('%g' % (s / 60)).replace('.', ',') + ' мин'
    return f'{s} с'


PER = {'каждой ногой каждым': 'каждой ногой, каждым ударом', 'на сторону': 'на сторону', 'каждой рукой': 'каждой рукой',
       'каждого': 'каждого удара', 'каждой': 'каждой комбинации', 'на ногу': 'на ногу', 'каждой ногой': 'каждой ногой',
       'каждым': 'каждым ударом', 'двоек': 'двоек', 'каждой связки каждой ногой': 'каждой связкой, каждой ногой',
       'каждой связки на каждую сторону': 'каждой связкой на каждую сторону', 'по 10 каждым': 'по 10 каждым ударом'}


def parse_nr(a):
    """'3 × 8 каждой ногой каждым' → (3, 8, per)."""
    m = re.match(r'^(\d+) × (\d+)(?:,)?(?: (.*))?$', a)
    if not m:
        raise ValueError(a)
    per = (m.group(3) or '').strip()
    return int(m.group(1)), int(m.group(2)), PER.get(per, per)


def rpe_for(Pp, main, deload):
    if deload:
        return 6
    if Pp == 1:
        return 7
    return 8 if main else 7


# ------------------------------------------------------------------ растяжка, таймеры
def stretch_segs(positions, H):
    segs = []
    for i, (name, sides) in enumerate(positions):
        if sides == 2:
            segs += [seg(name + ' — левая', H, 'work'), seg('Смена стороны', 5, 'rest'), seg(name + ' — правая', H, 'work')]
        else:
            segs.append(seg(name, H if sides == 1 else sides, 'work'))
        if i < len(positions) - 1:
            segs.append(seg('Переход', 8, 'rest'))
    return segs


D3_STRETCH = [('Нога на опоре вперёд', 2), ('Нога на опоре в сторону', 2), ('Растяжение паха сидя', 1), ('Растяжение в выпаде', 2)]
D4_STRETCH = [('Подколенные сухожилия — наклон к прямым ногам', 1), ('Растяжение бедра — пятка к ягодице', 2), ('Растяжение в выпаде', 2),
              ('Растяжение лодыжек у стены', 2), ('Боковое растяжение', 2), ('Расслабление плеч', 20)]
D1_STRETCH = [('Растяжение бедра стоя — колено к груди', 2), ('Растяжение бедра — пятка к ягодице', 2), ('Растяжение в выпаде', 2),
              ('Растяжение лодыжек у стены', 2), ('Боковое растяжение', 2)]


def stretch_cond(title, positions, H, how):
    return cond(title, stretch_segs(positions, H), [how], kind='stretch')


def round_segs(n, mins, rest, label, kind='work', tips=None):
    segs = []
    for j in range(n):
        lbl = label if n == 1 else (tips[j] if tips else f'{label} — раунд {j + 1} из {n}')
        segs.append(seg(lbl, mins * 60, kind))
        if j < n - 1 and rest:
            segs.append(seg('Отдых', rest, 'rest'))
    return segs


# ------------------------------------------------------------------ рабочие дни
def morning_steps():
    return [
        {'t': '<b>Потянись всем телом</b> — 5 раз: 3 с тянешься, 2 с отдых.'},
        {'t': '<b>Прогни спину</b> — 5 раз, мягко.'},
        {'t': '<b>Напряги ноги</b> — 12 раз и <b>пресс</b> — 10 раз: 3 с напряжение, 2 с отдых.'},
        {'t': '<b>Сядь и коснись пальцев ног</b> — 5 раз, мягко: утром диски чувствительны к сгибанию.'},
        {'t': '<b>Подними согнутые ноги</b> — 5 раз.'},
    ]


SHIFT_TIPS = ['Лестница вместо лифта, пешком при любой возможности.',
              'Стой на одной ноге, когда обуваешься или ждёшь.',
              'Стакан воды каждый час, кофеин — только до 12:00.',
              'Совет Ли о бдительности (с. 208): представь, что противник атакует тебя сидящего или стоящего, и придумай самую простую контратаку.']


def cardio_block(Pp, mp):
    mins, txt = P.cardio(Pp, mp)
    if Pp == 1:
        segs = [seg('Зона 2: ходьба в горку или велотренажёр', mins * 60, 'work', 'пульс 108–126, говоришь полными фразами')]
    elif Pp == 2:
        warm, n, walk, jog = [(5, 5, 4, 1), (2, 6, 3, 2), (0, 7, 2, 3)][mp - 1]
        segs = [seg('Ходьба — разогрев', warm * 60, 'easy')] if warm else []
        for i in range(n):
            segs += [seg(f'Ходьба {i + 1}/{n}', walk * 60, 'easy', 'пульс 108–126'), seg(f'Трусца {i + 1}/{n}', jog * 60, 'work', 'разговорный темп')]
    else:
        jog = mins - 5
        segs = [seg('Ходьба — разогрев', 300, 'easy'), seg('Трусца без остановок', jog * 60, 'work', 'Зона 2, пульс 108–126')]
    return mins, txt, segs


def proto_c(c, Pp, mp):
    mins, txt, segs = cardio_block(Pp, mp)
    H = P.hold(Pp, mp)
    test = c in P.TEST
    if test:
        mins = 30
        card = {'t': '<b>Калибровка Зоны 2 — 30 мин</b> вместо обычного кардио: быстрая ходьба или велотренажёр в темпе «говорю полными фразами, дышу носом». Запиши средний пульс с 10-й по 30-ю минуту и насколько он вырос к концу — это твоя Зона 2 на ' + ('следующий этап.' if c == 45 else 'следующую фазу.'),
                'segs': [seg('Разогрев до разговорного темпа', 600, 'easy'), seg('Держи темп — запоминай пульс', 1200, 'work', 'средний пульс 10–30 мин')]}
    else:
        card = {'t': f'<b>Кардио в Зоне 2 — {mins} мин:</b> {txt}. Пульс 108–126.', 'segs': segs}
    shadow = {'t': '<b>Бой с тенью — 2 × 3 мин</b> в среднем темпе, отдых 1 мин (с. 129–130): двигайся без остановок, руки всё время у головы — плечи и руки работают на выносливость; пульс — до начала Зоны 3.',
              'segs': [seg('Бой с тенью — раунд 1 из 2', 180, 'work', 'средний темп, без остановок'), seg('Отдых', 60, 'rest'), seg('Бой с тенью — раунд 2 из 2', 180, 'work', 'руки у головы, не стой на месте')]}
    gym = {'t': '<b>Суставная гимнастика Ли — 5 мин:</b> голова — медленно, полукругом (с. 112; назад не запрокидываем); вращение плечами вперёд и назад по 10 (с. 47); «расслабление плеч» 5 раз (с. 111–112); вращения запястьями (с. 111); вращение в талии с палкой, стоя прямо, — 20 раз (с. 45); таз, колени, стопы — по 5–8 кругов.',
           'segs': [seg('Голова — полукруги', 40, 'work'), seg('Вращение плечами', 40, 'work'), seg('Расслабление плеч × 5', 30, 'work'),
                    seg('Вращения запястьями', 30, 'work'), seg('Вращение в талии × 20', 50, 'work'), seg('Таз, колени, стопы', 90, 'work')]}
    st = {'t': f'<b>Растяжка Ли — 8 мин,</b> по {H} с на сторону, без пружинения: «растяжение бедра стоя» — колено к груди (с. 108); «растяжение бедра» — пятка к ягодице (с. 109); «растяжение в выпаде» (с. 109); «растяжение лодыжек» у стены (с. 109–110); «боковое растяжение» (с. 110).',
          'segs': stretch_segs(D1_STRETCH, H)}
    br = {'t': '<b>Перед сном — дыхание животом, 3 мин.</b> Ли: «следует учиться постоянно дышать животом» (с. 118). Вдох носом 4 с, выдох 6 с. Потом в постели — практика «после смены».',
          'segs': [seg('Дыхание животом', 180, 'easy', 'вдох 4 с, выдох 6 с')]}
    secs = [
        {'t': 'steps', 'title': 'Перед сменой — «утренний комплекс» Ли, 3 мин', 'id': 'pre', 'steps': morning_steps(), 'foot': 'Прямо в постели, до подъёма (с. 214).'},
        {'t': 'list', 'title': 'В течение смены — «ежедневные возможности» Ли', 'lines': SHIFT_TIPS},
        {'t': 'steps', 'title': f'После смены — ≈ {mins + 23} мин', 'id': 'aft', 'main': True, 'steps': [card, shadow, gym, st, br],
         'foot': 'Начни в течение часа после смены, закончи за 60–90 мин до сна.'},
    ]
    if test:
        secs.append({'t': 'tests', 'title': 'Запиши результат калибровки', 'tests': [
            {'id': 'z2', 'name': 'Зона 2: средний пульс с 10-й по 30-ю минуту'}, {'id': 'z2drift', 'name': 'На сколько вырос пульс к концу, уд/мин'}]})
    secs.append({'t': 'list', 'title': 'Жёлтый или красный день', 'lines': ['<b>Жёлтый:</b> 15 мин спокойной ходьбы и дыхание перед сном.', '<b>Красный:</b> только дыхание и сон.']})
    return secs, mins + 23


def flex_segs(prog, H, Pp):
    rep2 = (Pp == 2)
    S = []

    def hold(name, sides=1, twice=False):
        for k in range(2 if twice else 1):
            nm = name + (' — ещё раз' if k else '')
            if sides == 2:
                S.append([seg(nm + ' — левая', H), seg('Смена стороны', 5, 'rest'), seg(nm + ' — правая', H)])
            else:
                S.append([seg(nm, H)])

    def swings(name):
        S.append([seg(name + ' — левая, 8 раз', 25), seg('Смена', 5, 'rest'), seg(name + ' — правая, 8 раз', 25)])
    if prog == 'А':
        hold('Наклон вперёд стоя, ноги вместе', twice=rep2)
        hold('Выпад вперёд — «растяжение при широком шаге»', 2)
        swings('Выброс ноги вверх')
        swings('Выброс ноги в сторону')
        hold('Растяжение паха сидя, стопы вместе', twice=rep2)
        S.append([seg('Вращение в талии × 20', 40)])
        hold('Попеременный шпагат на стуле', 2)
        hold('Наклоны сидя — ноги вместе')
        hold('Наклоны сидя — ноги врозь')
        hold('Нога на опоре прямо', 2)
        hold('Нога на опоре в сторону', 2)
        S.append([seg('Заднее растяжение — 5 мягких прогибов', 30)])
    else:
        swings('Мах вперёд и нога назад на опору')
        swings('Выброс ноги в сторону')
        hold('Наклон вперёд стоя', twice=rep2)
        hold('Паховое растяжение сидя', twice=rep2)
        S.append([seg('Вращение в талии × 20', 40)])
        hold('Попеременный шпагат на стуле', 2)
        hold('Нога на опоре вперёд', 2)
        hold('Нога на опоре в сторону', 2)
        hold('Наклоны сидя')
        hold('Выпад вперёд', 2)
        hold('Выпад в сторону', 2)
        hold('Растяжение барьериста — стопа у бедра', 2)
    out = []
    for i, grp in enumerate(S):
        out += grp
        if i < len(S) - 1:
            out.append(seg('Переход', 8, 'rest'))
    return out


def proto_r(c, Pp, mp):
    H = P.hold(Pp, mp)
    prog = 'А' if c % 2 == 1 else 'Б'
    abs_ = {1: ['2 × 10', '2 × 12', '2 × 15'][mp - 1], 2: '2 × 15', 3: '2 × 15'}[Pp]
    flut = {1: [20, 25, 30][mp - 1], 2: 30, 3: 30}[Pp]
    rock = {1: ['2 × 6', '2 × 8', '2 × 10'][mp - 1], 2: '2 × 10', 3: '2 × 10'}[Pp]
    reps = '1 раз' if Pp != 2 else '1 раз; задняя поверхность бедра и пах — 2 раза'
    progtxt = {'А': 'наклон вперёд стоя; выпад вперёд; махи вперёд и в сторону по 8; «растяжение паха» сидя; «вращение в талии» 20 раз; «попеременный шпагат на стуле»; «наклоны сидя» вместе и врозь; нога на опоре прямо и в сторону; «заднее растяжение» — 5 мягких прогибов вместо мостика.',
               'Б': 'мах вперёд и нога назад на опору; махи в сторону по 8; наклон вперёд стоя; «паховое растяжение сидя»; «вращение в талии»; «попеременный шпагат на стуле»; нога на опоре вперёд и в сторону; «наклоны сидя»; выпад вперёд и в сторону; «растяжение барьериста» в варианте Ли — стопа у внутренней стороны бедра (с. 107).'}[prog]
    steps = [
        {'t': '<b>Велотренажёр — 20 мин,</b> лёгкая езда: пульс 100–120 (Зоны 1–2), каденс 80–90 (с. 99). Добавляет к неделе ≈ 35 мин аэробной базы и разогревает мышцы перед растяжкой. Только в «зелёный» день; в жёлтый — 3 мин спокойной езды.',
         'segs': [seg('Велотренажёр, лёгко', 1200, 'easy', 'пульс 100–120, каденс 80–90')]},
        {'t': '<b>Разогрев суставов — 2 мин:</b> вращение плечами 10 + 10 (с. 47); «высокий удар ногой» — мах вперёд и мах в сторону, по 8 каждой ногой, высота растёт с каждым махом (с. 45, 186).',
         'segs': [seg('Вращение плечами', 30, 'work'), seg('Махи вперёд и в сторону', 90, 'work')]},
        {'t': '<b>Бой с тенью — 2 × 3 мин</b> в лёгком темпе, отдых 1 мин (с. 129–130): разогрев плеч, корпуса и ног перед растяжкой.',
         'segs': [seg('Бой с тенью — раунд 1 из 2', 180, 'work', 'лёгкий темп'), seg('Отдых', 60, 'rest'), seg('Бой с тенью — раунд 2 из 2', 180, 'work', 'лёгкий темп, дыхание ровное')]},
        {'t': f'<b>Гибкость Ли — программа {prog}</b> (с. 211–212), удержание {H} с, {reps}: {progtxt} Правила Ли (с. 105): не до боли, не пружинить, дышать ровно.',
         'segs': flex_segs(prog, H, Pp)},
        {'t': f'<b>Пресс Ли:</b> «подтягивание колен» лёжа (с. 46) — {abs_}. Поясницу не скручиваем.'},
        {'t': f'<b>«Попеременное поднимание ног» — ножницы</b> (с. 48, 62) — 2 × {flut} с.',
         'segs': [seg('Ножницы', flut), seg('Отдых', 30, 'rest'), seg('Ножницы', flut)]},
        {'t': f'<b>«Качание спинных мышц лёжа»</b> — противоположные рука и нога (с. 186) — {rock} на сторону.'},
        {'t': '<b>Наклоны в стороны без веса</b> (с. 46) — 2 × 15 на сторону.'},
        {'t': '<b>«Статическое сокращение» пресса</b> (с. 64) — 5 × 5 с.', 'segs': [x for i in range(5) for x in ([seg(f'Напряги пресс {i + 1}/5', 5)] + ([seg('Отпусти', 5, 'rest')] if i < 4 else []))]},
        {'t': '<b>Шея — 2 мин:</b> изометрия рукой — лоб, затылок, левый и правый висок, по 2 × 10 с на 30–50% усилия. Замена «борцовскому мостику» Ли (с. 75).',
         'segs': [x for r in range(2) for i, nm in enumerate(['Лоб', 'Затылок', 'Левый висок', 'Правый висок'])
                  for x in ([seg(f'{nm} — давит в ладонь', 10)] + ([seg('Пауза', 5, 'rest')] if not (r == 1 and i == 3) else []))]},
        {'t': '<b>Финал — 3 мин:</b> дыхание животом. В постели — практика «после смены».', 'segs': [seg('Дыхание животом', 180, 'easy', 'вдох 4 с, выдох 6 с')]},
    ]
    secs = [
        {'t': 'steps', 'title': 'Перед сменой — «утренний комплекс» Ли, 3 мин', 'id': 'pre', 'steps': morning_steps(), 'foot': 'Прямо в постели, до подъёма (с. 214).'},
        {'t': 'list', 'title': 'В течение смены', 'lines': ['Как в первый рабочий день: лестницы, пешком, стойка на одной ноге, вода, кофеин до 12:00.']},
        {'t': 'steps', 'title': 'После смены — ≈ 65 мин', 'id': 'aft', 'main': True, 'steps': steps},
        {'t': 'list', 'title': 'Жёлтый или красный день', 'lines': ['<b>Жёлтый:</b> 3 мин спокойной езды, разогрев суставов, половина программы гибкости, дыхание.', '<b>Красный:</b> только дыхание и сон.']},
    ]
    return secs, prog


# ------------------------------------------------------------------ разминки
def warm_steps(kind, Pp):
    txt = P.proto_warmA(Pp) if kind == 'A' else P.proto_warmB()
    lines = [re.sub(r'^\d+\.\s*', '', l) for l in txt.split('\n') if re.match(r'^\d+\. ', l)]
    out = []
    for i, l in enumerate(lines):
        st = {'t': l}
        if i == 0:
            st['segs'] = [seg('Бег на месте или велотренажёр, Зона 1–2', 180, 'warm')] if kind == 'A' else [seg('Скакалка легко или велотренажёр', 180, 'warm')]
        if kind == 'A' and i == len(lines) - 1:
            st['segs'] = [seg('Бой с тенью в лёгком темпе', 60, 'easy')]
        if kind == 'B' and i == len(lines) - 1:
            st['ramp'] = True
        out.append(st)
    return out


def warm_sec(kind, Pp, note=None, title=None, noramp=False):
    title = title or ('Разминка А — 12 мин' if kind == 'A' else 'Разминка Б — 12 мин')
    if noramp:
        st = warm_steps(kind, Pp)[:-1]
        return {'t': 'steps', 'title': title, 'id': 'warm', 'warm': True, 'steps': st, 'foot': note or ''}
    foot = ('По мотивам разминки Ли для его школы в Китайском квартале (с. 186). Ли приступал к боевой тренировке только после тщательной разминки (с. 100).'
            if kind == 'A' else 'Ли повредил крестцовый нерв, сделав «доброе утро» без разминки (с. 40). Разминка — половина защиты от травм.')
    return {'t': 'steps', 'title': title, 'id': 'warm', 'warm': True, 'steps': warm_steps(kind, Pp), 'foot': note or foot}


# ------------------------------------------------------------------ День 3
FIGHTER = ['Трусца', 'Рывок', 'Спиной вперёд', 'Скрестный шаг', 'Поворот вокруг себя']


def run_series_cond(n, fast_lbl, fast_tip, title, how):
    segs = []
    for i in range(n):
        segs += [seg(f'Трусца {i + 1}/{n}', 60, 'easy'), seg(f'{fast_lbl} {i + 1}/{n}', 30, 'work', fast_tip), seg(f'Ходьба {i + 1}/{n}', 60, 'rest')]
    return cond(title, segs, [how], kind='run')


def bag_segs(n, mins, label, finish=0, tip=None):
    """Раунды на груше по времени; finish — последние секунды раунда на максимум."""
    segs = []
    for j in range(n):
        lbl = f'{label} — раунд {j + 1} из {n}'
        if finish:
            segs += [seg(lbl, mins * 60 - finish, 'work', tip), seg(f'{label} — на максимум!', finish, 'work', 'последние секунды раунда — на пределе')]
        else:
            segs.append(seg(lbl, mins * 60, 'work', tip))
        if j < n - 1:
            segs.append(seg('Отдых', 60, 'rest'))
    return segs


def speed_segs(n, fast, slow, label, mins=2):
    """Скоростные раунды: внутри раунда fast с на максимальной скорости, slow с легко."""
    segs = []
    for j in range(n):
        for i in range(mins * 60 // (fast + slow)):
            segs += [seg(f'{label} {j + 1}/{n} — быстро', fast, 'work', 'максимальная скорость'), seg(f'{label} {j + 1}/{n} — легко', slow, 'easy', 'лёгкие удары, дыши')]
        if j < n - 1:
            segs.append(seg('Отдых', 60, 'rest'))
    return segs


def rounds_from(title, rws, lines_extra=None):
    segs, lines = [], []
    for i, r in enumerate(rws):
        name, amt, how = r[1], r[2], r[3]
        m = re.match(r'(\d+) × (\d+) мин', amt)
        n, mins = (int(m.group(1)), int(m.group(2))) if m else (1, int(re.match(r'(\d+) мин', amt).group(1)))
        easy = ('разминк' in name or 'в темпе разминки' in name)
        tip = re.sub(r';?\s*отдых [^;]+', '', how).strip('; ') or None
        for j in range(n):
            lbl = name if n == 1 else f'{name} — раунд {j + 1} из {n}'
            segs.append(seg(lbl, mins * 60, 'easy' if easy else 'work', tip))
            last = (i == len(rws) - 1 and j == n - 1)
            if not last:
                segs.append(seg('Отдых', 90 if 'отдых 1,5 мин' in how else 60, 'rest'))
        lines.append(name + ' — ' + amt + (f' ({tip})' if tip else ''))
    return cond(title, segs, lines + (lines_extra or []), kind='rounds')


def conv_d3_row(r, c, Pp, deload):
    """Строка «Упражнение — Сколько — Как» → записи приложения (кроме раундов и бега)."""
    name, amt, how = r[1], r[2], r[3]
    page = pg(name)
    rs, rest_txt = rest_of(how, 0)
    note = clean_how(how)

    t = name
    if t.startswith('«Отжимания» — широкое'):
        m = re.match(r'^(\d+) × \(максимум − (\d+)\)$', amt)
        return [item('pushup_wide', amt, rows(int(m.group(1)), None, kind='amrap', off=int(m.group(2))), load=f'В каждом подходе — максимум минус {m.group(2)}', rest=60, note=note, page=page)]
    if t.startswith('Отжимания с хлопком'):
        n, k, per = parse_nr(amt)
        return [item('clap_pushup', amt, rows(n, k), rest=60, note=note, page=page)]
    if t.startswith('«1/2 приседа»'):
        n, k, per = parse_nr(amt)
        return [item('half_squat', amt, rows(n, k), rest=45, note=note, page=page)]
    if t.startswith('Приседания «на четыре счёта'):
        n, k, per = parse_nr(amt)
        jump = 'и прыжок' in t
        return [item('squat4', amt, rows(n, k), load=('С прыжком вверх' if jump else 'Без прыжка'), rest=60, note=note, page=page)]
    if t.startswith('Медленный подъём ноги'):
        n, k, per = parse_nr(amt)
        return [item('slow_leg', amt, rows(n, k), rest=30, note=note, per=per, page=page)]
    if t.startswith('«Прыжки в стороны»') or t.startswith('«Прыжки вверх»'):
        n, k, per = parse_nr(amt)
        return [item('jumps', amt, rows(n, k), load=('Вверх с места' if 'вверх' in t else 'В стороны, низко'), rest=45 if 'в стороны' in t else 60, note=note, page=page)]
    if t.startswith('Функциональная изометрия Ли (с. 215): упор кулаком'):
        return [item('iso_fist', amt, rows(3, 6, lbl=['Нижний уровень', 'Верхний уровень', 'Средний уровень']), unit='sec', rest=45, note=note, page=page)]
    if t.startswith('Функциональная изометрия Ли (с. 215): упор стопой'):
        return [item('iso_foot', amt, rows(4, 6, lbl=['Прямой — нижний', 'Прямой — средний', 'Боковой — нижний', 'Боковой — средний']), unit='sec', lr=True, rest=45, note=note, page=page)]
    # пресс
    if t.startswith('«Лягушка»'):
        m = re.match(r'^(\d+) × \(максимум − (\d+)\)$', amt)
        if m:
            return [item('frog', amt, rows(int(m.group(1)), None, kind='amrap', off=int(m.group(2))), rest=60, note=note, page=page)]
        n, k, per = parse_nr(amt)
        return [item('frog', amt, rows(n, k), rest=60, note=note, page=page)]
    if t.startswith('«Поднимание ног»'):
        n, k, per = parse_nr(amt)
        return [item('leg_raise', amt, rows(n, k), rest=45, note=note, page=page)]
    if t.startswith('«Наклоны в стороны»'):
        n, k, per = parse_nr(amt)
        w = kgs(how)
        return [item('side_bend', amt, rows(n, k, pw=w[0] if w else None), load=(f'План: {fmt_kg(w[0])} кг' if w else ''), rest=45, note=note, per='на сторону', page=page)]
    if t.startswith('«Вращение в талии», «поднимание ног», «лягушка»'):
        return [item('waist_twist', '1 × 30', rows(1, 30), rest=30), item('leg_raise', '1 × 10', rows(1, 10), rest=30), item('frog', '1 × 8', rows(1, 8), rest=30)]
    if t.startswith('«Вращение в талии»'):
        n, k, per = parse_nr(amt)
        return [item('waist_twist', amt, rows(n, k), rest=30, note=note, page=page)]
    if t.startswith('«Вращения сидя»') or t.startswith('«Из положения лёжа в положение сидя'):
        n, k, per = parse_nr(amt)
        return [item('situp_twist', amt, rows(n, k), rest=45, note=note, page=page)]
    if t.startswith('«Статическое сокращение»'):
        return [item('static_abs', '5 × 5 с', rows(1, 5, reps=5, rr=5, lbl='5 × 5 с'), unit='sec', rest=0, note=('Напряги пресс, как перед пропущенным ударом, на 5 с и отпусти; дыхание не задерживай. ' + note).strip(), page=page)]
    raise ValueError('D3 row not mapped: ' + t)


def d3_entries(c):
    Pp, m, mp, w = P.info(c)
    deload = (w == 5)
    fn = P.d3_phase1 if Pp == 1 else P.d3_phase2 if Pp == 2 else P.d3_phase3
    R, meta = fn(c)
    R = P.reletter(R)
    # группируем по блокам
    blocks = []
    for r in R:
        if r[0]:
            blocks.append([r[0], [r]])
        else:
            blocks[-1][1].append(r)
    out, tests = [], []
    for bname, rws in blocks:
        bn = re.sub(r'^[А-ЯЁ]\. ', '', bname)
        if bn.startswith('Разминка'):
            continue
        out.append(hdr(bname))
        first = rws[0]
        if bn.startswith('Скакалка'):
            n, mins = re.match(r'(\d+) × (\d+) мин', first[2]).groups()
            rest, _ = rest_of(first[3], 60)
            out.append(cond(f'Скакалка — {first[2]}', round_segs(int(n), int(mins), rest, 'Скакалка'), [first[3]], kind='rope'))
        elif bn.startswith('Бой с тенью'):
            n, mins = re.match(r'(\d+) × (\d+) мин', first[2]).groups()
            n = int(n)
            tips = None
            if 'в сдержанном темпе' in first[1]:
                tips = ['Раунд 1 — в сдержанном темпе', 'Раунд 2 — на 50%, быстрее, но экономичнее']
            elif 'разминка — быстро — спокойно' in first[1]:
                tips = ['Раунд 1 — разминка', 'Раунд 2 — быстро', 'Раунд 3 — спокойно']
            out.append(cond('Бой с тенью — ' + first[2], round_segs(n, int(mins), 60, 'Бой с тенью', tips=tips[:n] if tips else None), [first[1] + '.']))
        elif bn.startswith('Тяжёлая груша'):
            n, mins = map(int, re.match(r'(\d+) × (\d+) мин', first[2]).groups())
            part = re.match(r'Тяжёлая груша — ([^,]+)', bn).group(1)
            fm = re.search(r'последние (\d+) с раунда', first[3])
            tip = re.sub(r'^отдых [^;]+;\s*', '', first[3])
            tip = re.sub(r';\s*последние \d+ с раунда — на максимум', '', tip).split(';')[0].strip()
            lines = [first[1] + '.', first[3][:1].upper() + first[3][1:] + '.']
            out.append(cond(f'Груша, {part} — {first[2]}', bag_segs(n, mins, f'Груша, {part}', int(fm.group(1)) if fm else 0, tip or None), lines, kind='rounds'))
            for r in rws[1:]:
                out += conv_d3_row(r, c, Pp, deload)
        elif bn.startswith('Скоростные раунды'):
            n, mins = map(int, re.match(r'(\d+) × (\d+) мин', first[2]).groups())
            fast = int(re.search(r': (\d+) с — ', first[1]).group(1))
            part = 'руки' if '— руки' in bn else 'ноги'
            lines = [first[1] + '.', first[3][:1].upper() + first[3][1:] + '.']
            out.append(cond(f'Скоростные раунды, {part} — {first[2]}', speed_segs(n, fast, 30 - fast, 'Раунд', mins), lines, kind='rounds'))
            for r in rws[1:]:
                out += conv_d3_row(r, c, Pp, deload)
        elif bn.startswith('Лёгкая груша'):
            n, mins = re.match(r'(\d+) × (\d+) мин', first[2]).groups()
            out.append(cond('Лёгкая груша — ' + first[2], round_segs(int(n), int(mins), 60, 'Лёгкая груша'), [first[1] + '.']))
        elif bn.startswith('Заминка'):
            out.append(cond('Бой с тенью «в темпе разминки» — 2 мин', [seg('Бой с тенью в темпе разминки', 120, 'easy')], ['Как заканчивал Ли (с. 129).']))
        elif bn.startswith('Растяжка Ли'):
            H = int(re.search(r'(\d+)', first[2]).group(1))
            mins = re.search(r'(\d+) мин', bn).group(1)
            out.append(stretch_cond(f'Растяжка Ли — по {H} с на позицию', D3_STRETCH, H, first[1] + '. Без пружинения.'))
        elif bn.startswith('Беговые упражнения Ли') and Pp == 2:
            n = int(re.match(r'(\d+)', first[2]).group(1))
            pct = re.search(r'на (\d+)%', first[3]).group(1)
            out.append(run_series_cond(n, f'Быстрый бег на {pct}%', '+4–5 км/ч к трусце', f'Беговые серии Ли — {first[2]}', first[3]))
        elif bn == 'Бег':
            if Pp == 2:  # разгрузка
                segs = [x for i in range(2) for x in (seg(f'Трусца {i + 1}/2', 120, 'easy'), seg(f'Ходьба {i + 1}/2', 60, 'rest'))]
                out.append(cond('Бег — 2 серии без ускорений', segs, [first[1] + '.', 'Зона 2.'], kind='run'))
            elif deload:
                segs = [seg(x, 30, 'easy') for x in ['Трусца', 'Спиной вперёд', 'Скрестный шаг', 'Поворот вокруг себя']]
                segs += [x for i in range(2) for x in (seg(f'Трусца {i + 1}/2', 120, 'easy'), seg(f'Ходьба {i + 1}/2', 60, 'rest'))]
                out.append(cond('Бег Ли «с переменами» без рывков + трусца', segs, [first[1] + '.', 'Без спринтов и рывков.'], kind='run'))
            else:
                segs = [seg(FIGHTER[i % 5], 30, 'work' if FIGHTER[i % 5] == 'Рывок' else 'easy') for i in range(8)]
                out.append(cond('Бег Ли «с переменами» — 4 мин', segs, ['Как бегал Ли по воспоминаниям Бустильо (с. 120): трусца, рывок, спиной вперёд, скрестный шаг, поворот вокруг себя — по 30 с, «для тренировки ног и координации».', 'Зона 2–3.'], kind='run'))
                sr = rws[1]
                n = int(re.match(r'(\d+)', sr[2]).group(1))
                pct = re.search(r'на (\d+)%', sr[3]).group(1)
                out.append(run_series_cond(n, f'Спринт на {pct}%', '+6–7 км/ч к трусце или в горку', f'Беговые серии Ли — {sr[2]}', sr[3]))
        elif bn.startswith('Программа Ли для Хартселла') or bn.startswith('Личная программа Ли') or bn.startswith('Контрольная тренировка') or bn.startswith('Проверка ворот'):
            title = {True: bn}[True]
            title = re.sub(r'(?: — раунды)?, отдых 1 мин$', '', title)
            out.append(rounds_from(title, rws, ['Отдых между раундами 1 мин, после скакалки 1,5 мин.']))
            if bn.startswith('Проверка ворот'):
                tests = [{'id': 'hr5', 'name': 'Пульс в конце 5-го раунда на груше'}, {'id': 'hr5r', 'name': 'Пульс через 1 мин отдыха'},
                         {'id': 'gate115', 'name': 'Падение на 20 ударов и больше?', 'yn': True}]
            if bn.startswith('Контрольная тренировка'):
                tests = [{'id': 'avgbag', 'name': 'Средний пульс раундов на груше'}, {'id': 'hr44', 'name': 'Пульс в конце последнего раунда на груше'},
                         {'id': 'hr44r', 'name': 'Пульс через 1 мин отдыха'}]
        else:
            for r in rws:
                out += conv_d3_row(r, c, Pp, deload)
    return out, meta, tests


# ------------------------------------------------------------------ День 4
def conv_d4(c):
    Pp, m, mp, w = P.info(c)
    deload = (w == 5)
    R, meta = P.d4_rows(c)
    R = P.reletter(R)
    out = []
    i = 0
    cur_block = None
    while i < len(R):
        r = R[i]
        name, amt, how = r[1], r[2], r[3]
        if r[0]:
            cur_block = r[0]
            bn = re.sub(r'^[А-ЯЁ]\. ', '', cur_block)
            if bn.startswith('Разминка'):
                i += 1
                continue
            out.append(hdr(cur_block))
        page = pg(name)
        rest, rest_txt = rest_of(how, 0)
        note = clean_how(how)
        W = kgs(how)
        t = name
        main = False
        if 'лёгкие подходы' in t:
            n, k, _ = parse_nr(amt)
            ex = 'squat' if t.startswith('«Приседания»') else 'deadlift'
            pct = '65' if ex == 'squat' else '60'
            out.append(item(ex, amt, rows(n, k, pw=W[0]), load=f'Лёгкие подходы: {fmt_kg(W[0])} кг ≈ {pct}% рабочего веса', rest=rest or 90, rest_txt=rest_txt,
                            note='Второе главное движение дня — для частоты и техники: быстро и чисто, ни одного трудного повтора. Вес не повышаем.', light=True, page=page))
        elif t.startswith('Броски медбола'):
            a, b = amt.split(' + ')
            n1, k1, per1 = parse_nr(a)
            n2, k2, _ = parse_nr(b)
            out.append(item('mb_rot', a, rows(n1, k1), wt='none', load='Мяч 4–6 кг', rest=45, per=per1, page='не из книги',
                            note='Взрывно: разворот начинается с задней ноги и таза, как в боковом ударе. 5 бросков на одну сторону, затем на другую — один подход.'))
            out.append(item('mb_chest', b, rows(n2, k2), wt='none', load='Мяч 4–6 кг', rest=45, page='не из книги',
                            note='Толчок с шагом вперёд — сила идёт от ног.'))
        elif t.startswith('«Приседания»'):
            n, k, _ = parse_nr(amt)
            pair = i + 1 < len(R) and R[i + 1][1].startswith('«Занос за голову»')
            it = item('squat', amt, rows(n, k, rpe=rpe_for(Pp, True, deload), pw=W[0]), load=f'План: {fmt_kg(W[0])} кг', rest=rest or 150, rest_txt=rest_txt, note=note, main=True, page=page)
            if pair:
                pn, pk, _ = parse_nr(R[i + 1][2])
                it['spec']['pairNext'] = True
                it['spec']['pairFrom'] = max(0, n - pn)
                it['lab_pair'] = True
            out.append(it)
        elif t.startswith('«Занос за голову»'):
            n, k, _ = parse_nr(amt)
            sq = [x for x in out if x.get('ex') == 'squat'][-1]
            wt = 'db'
            out.append(item('pullover', amt, rows(n, k, rpe=rpe_for(Pp, False, deload), pw=W[0]), load=f'План: {fmt_kg(W[0])} кг', rest=sq['spec']['rest'], rest_txt=sq['rest'], note=note, wt=wt, page=page, pairPrev=True))
        elif t.startswith('«Жим штанги стоя»'):
            n, k, _ = parse_nr(amt)
            out.append(item('milpress', amt, rows(n, k, rpe=rpe_for(Pp, False, deload), pw=W[0]), load=f'План: {fmt_kg(W[0])} кг', rest=rest or 90, rest_txt=rest_txt, note=note, page=page))
        elif t.startswith('«Переднее подтягивание»'):
            m1 = re.match(r'^(\d+) подход', amt)
            m2 = re.match(r'^(\d+) × \(максимум − (\d+)\)$', amt)
            m3 = re.match(r'^(\d+) × (\d+) с весом$', amt)
            if m1:
                off = 3 if 'минус 3' in how else 2
                out.append(item('pullup', amt, rows(int(m1.group(1)), None, kind='amrap', off=off), load=f'В каждом подходе — максимум минус {off}', rest=120, note=note, page=page))
            elif m2:
                out.append(item('pullup', amt, rows(int(m2.group(1)), None, kind='amrap', off=int(m2.group(2))), load='Без веса', rest=120, note='', page=page))
            else:
                out.append(item('pullup', '3 × 5 с весом', rows(int(m3.group(1)), int(m3.group(2)), rpe=rpe_for(Pp, False, deload), pw=5), wt='belt', load='План: +5–10 кг на поясе', rest=120,
                                note='Без пояса — 3 × (максимум − 1).', page=page))
        elif t.startswith('«Гиперрастяжение»'):
            n, k, _ = parse_nr(amt)
            if not W:
                out.append(item('hyper', amt, rows(n, k), wt='bw', load='Без веса', rest=60, note=re.sub(r'^Без веса;\s*', '', note).capitalize(), page=page))
            else:
                out.append(item('hyper', amt, rows(n, k, rpe=rpe_for(Pp, False, deload), pw=W[0]), wt='plate', load=f'План: блин {fmt_kg(W[0])} кг у груди', rest=60, note=note, page=page))
        elif t.startswith('«Жим для бицепсов» + «французский жим»'):
            n = int(amt.split(' × ')[0])
            k1 = 8
            out.append(item('curl', f'{n} × {k1}', rows(n, k1, rpe=rpe_for(Pp, False, deload), pw=W[0]), load=f'План: {fmt_kg(W[0])} кг', rest=60, page='с. 41'))
            out.append(item('french', f'{n} × {k1}', rows(n, k1, rpe=rpe_for(Pp, False, deload), pw=W[1]), load=f'План: {fmt_kg(W[1])} кг', rest=60, page='с. 31, 92'))
        elif t.startswith('«Жим для бицепсов»'):
            n, k, _ = parse_nr(amt)
            out.append(item('curl', amt, rows(n, k, rpe=rpe_for(Pp, False, deload), pw=W[0]), load=f'План: {fmt_kg(W[0])} кг', rest=60, note=note, page=page))
        elif t.startswith('«Поднимание пяток сидя»'):
            n, k, _ = parse_nr(amt)
            out.append(item('calf_seat', amt, rows(n, k, rpe=rpe_for(Pp, False, deload), pw=W[0]), load=f'План: {fmt_kg(W[0])} кг', rest=60, note=note, page=page))
        elif t.startswith('«Поднимание пяток»'):
            n, k, _ = parse_nr(amt)
            pw = W[0] if W else 0
            if pw:
                out.append(item('calf', amt, rows(n, k, rpe=rpe_for(Pp, False, deload), pw=pw), load=f'План: {fmt_kg(pw)} кг', rest=60, note=note, page=page))
            else:
                out.append(item('calf', amt, rows(n, k), wt='bw', load='Без веса', rest=60, note=note.replace('Без веса — в', 'В'), page=page))
        elif t.startswith('«Запястный вращатель»'):
            n = int(re.match(r'(\d+)', amt).group(1))
            out.append(item('wrist_roller', amt, rows(n, None, kind='round', lbl='Намотка', pw=W[0]), unit='rounds', load=f'План: груз {fmt_kg(W[0])} кг', rest=45, note=note, page=page))
        elif t.startswith('«Тяжёлая штанга»'):
            n, k, _ = parse_nr(amt)
            out.append(item('deadlift', amt, rows(n, k, rpe=rpe_for(Pp, True, deload), pw=W[0]), load=f'План: {fmt_kg(W[0])} кг', rest=rest or 150, rest_txt=rest_txt, note=note, main=True, page=page))
        elif t.startswith('«Байтак»'):
            n, k, _ = parse_nr(amt)
            out.append(item('baithak', amt, rows(n, k), rest=60, note=note, page=page))
        elif t.startswith('«Гребля гантелью одной рукой»'):
            n, k, _ = parse_nr(amt)
            out.append(item('db_row', amt, rows(n, k, rpe=rpe_for(Pp, False, deload), pw=W[0]), load=f'План: {fmt_kg(W[0])} кг', rest=60, note=note, per='каждой рукой', page=page))
        elif t.startswith('«Данд»'):
            n, k, _ = parse_nr(amt)
            out.append(item('dand', amt, rows(n, k), rest=60, note=note, page=page))
        elif t.startswith('«Боковое поднятие гантелей стоя»'):
            n, k, _ = parse_nr(amt)
            out.append(item('lat_raise', amt, rows(n, k, rpe=rpe_for(Pp, False, deload), pw=W[0]), load=f'План: {fmt_kg(W[0])} кг', rest=60, note=note, page=page))
        elif t.startswith('«Французский жим»'):
            n, k, _ = parse_nr(amt)
            out.append(item('french', amt, rows(n, k, rpe=rpe_for(Pp, False, deload), pw=W[0]), load=f'План: {fmt_kg(W[0])} кг', rest=60, note=note, page=page))
        elif t.startswith('«Обратный жим»'):
            a, b = amt.split(' + ')
            n1, k1, _ = parse_nr(a)
            n2, k2, _ = parse_nr(b)
            nt = 'Ли: «используйте только тот вес, с которым можете работать без излишнего напряжения» (с. 65).'
            out.append(item('rev_curl', a, rows(n1, k1, rpe=rpe_for(Pp, False, deload), pw=W[0]), load=f'План: {fmt_kg(W[0])} кг', rest=45, note=nt, page='с. 33, 48'))
            out.append(item('wrist_curl', b, rows(n2, k2, rpe=rpe_for(Pp, False, deload), pw=W[1]), load=f'План: {fmt_kg(W[1])} кг', rest=45, page='с. 33, 45'))
        elif t.startswith('«Прыжок из приседа»'):
            n, k, _ = parse_nr(amt)
            out.append(item('jump_squat', amt, rows(n, k), rest=60, note=note, page=page))
        elif t.startswith('«Выжимание штанги»'):
            n, k, _ = parse_nr(amt)
            out.append(item('clean_press', amt, rows(n, k, rpe=rpe_for(Pp, True, deload), pw=W[0]), load=f'План: {fmt_kg(W[0])} кг' + (' · с виса' if 'с виса' in t else ''), rest=rest or 150, rest_txt=rest_txt, note=note, main=True, page=page))
        elif t.startswith('Изометрия Ли'):
            lbl = ['Давление вперёд — перекладина на уровне подбородка', 'Тяга снизу — на 15–18 см ниже пояса', 'Параллельное приседание — перекладина на плечах']
            if '8–10' in amt:
                rw = rows(3, 8, 10, lbl=lbl)
            else:
                rw = rows(3, 6, lbl=lbl)
            out.append(item('iso_rack', amt, rw, unit='sec', rest=60, note=note, page=page))
        elif t.startswith('«Жим с концентрацией»'):
            n, k, _ = parse_nr(amt)
            out.append(item('conc_curl', amt, rows(n, k, rpe=rpe_for(Pp, False, deload), pw=W[0]), load=f'План: {fmt_kg(W[0])} кг', rest=60, per='каждой рукой', page=page))
        elif t.startswith('Предплечья — программа Ли «А»') or t.startswith('Предплечья — программа Ли «В»'):
            ex = 'forearm_a' if '«А»' in t else 'forearm_b'
            n = 1 if 'по 1' in amt else 2
            detail = t.split(': ', 1)[1]
            out.append(item(ex, amt, rows(n, None, kind='round', lbl='Круг'), unit='rounds', wt='none', load='', rest=60,
                            note=detail[:1].upper() + detail[1:] + '. ' + (clean_how(how) or ''), page=page))
        elif t.startswith('«Попеременный шпагат» в прыжке'):
            n, k, _ = parse_nr(amt)
            out.append(item('split_jump', amt, rows(n, k), rest=60, note=note, per='на ногу', page=page))
        elif t.startswith('«Жим на скамье»'):
            n, k, _ = parse_nr(amt)
            pct = float(re.search(r'≈ (\d+(?:,\d+)?)%', how).group(1).replace(',', '.'))
            out.append(item('bench', amt, rows(n, k, rpe=rpe_for(Pp, True, deload), pct=pct), load=f'≈ {fmt_kg(pct)}% твоего лучшего жима', rest=150,
                            note=re.sub(r'^≈ [\d,]+% (твоего )?лучшего жима( \(при 100 кг — [\d,]+ кг\))?;?\s*', '', how).strip('; ').capitalize(), main=True, page=page))
        elif t.startswith('«Гребля» согнувшись'):
            n, k, _ = parse_nr(amt)
            out.append(item('bb_row', amt, rows(n, k, rpe=rpe_for(Pp, False, deload), pw=W[0]), load=f'План: {fmt_kg(W[0])} кг', rest=rest or 90, rest_txt=rest_txt, note=note, page=page))
        elif t.startswith('«Растяжение трицепсов»'):
            n, k, _ = parse_nr(amt)
            out.append(item('tri_ext', amt, rows(n, k, rpe=rpe_for(Pp, False, deload), pw=W[0]), load=f'План: {fmt_kg(W[0])} кг', rest=45, per='каждой рукой', page=page))
        elif t.startswith('Хват'):
            a, b = amt.split(' + ')
            n1, k1, _ = parse_nr(a)
            nr = int(re.match(r'(\d+)', b).group(1))
            out.append(item('gripper', a, rows(n1, k1), wt='none', rest=30, note='«Ежедневно при каждой возможности» (с. 72).', page='с. 68, 72'))
            out.append(item('wrist_roller', b, rows(nr, None, kind='round', lbl='Намотка', pw=W[0]), unit='rounds', load=f'План: груз {fmt_kg(W[0])} кг', rest=45, page='с. 48, 72–73'))
        elif t.startswith('«Жим Зоттмана»'):
            n, k, _ = parse_nr(amt)
            out.append(item('zottman', amt, rows(n, k, rpe=rpe_for(Pp, False, deload), pw=W[0]), load=f'План: {fmt_kg(W[0])} кг в каждой руке', rest=60, page=page))
        elif t.startswith('Ровная езда'):
            mins = int(re.match(r'(\d+)', amt).group(1))
            out.append(cond(f'Велотренажёр — {mins} мин, Зона 2', [seg('Велотренажёр, Зона 2', mins * 60, 'work', 'пульс 108–126, каденс 80–90')],
                            ['Ровная езда в Зоне 2: пульс 108–126, каденс 80–90. Ли «обычно пользовался велотренажёром» (с. 99).'], kind='bike'))
        elif t.startswith('«Растяжение подколенных сухожилий»'):
            H = int(re.search(r'(\d+)', amt).group(1))
            out.append(stretch_cond(f'Растяжка Ли — по {H} с на позицию', D4_STRETCH, H, 'Растяжка после силовой быстро возвращает работоспособность (с. 103). Без пружинения.'))
        else:
            raise ValueError('D4 row not mapped: ' + t)
        i += 1
    return out, meta


# ------------------------------------------------------------------ тесты
TESTS = [
    ('weight', 'Вес, кг', 'Среднее 7 утренних взвешиваний натощак после туалета'),
    ('waist', 'Талия, см', 'На уровне пупка и в самой узкой точке, утром, на спокойном выдохе'),
    ('rhr', 'Пульс покоя', 'Утром лёжа, 60 с, до телефона и кофе; среднее за 7 дней'),
    ('bp', 'Давление дома', 'Утром и вечером по 2 замера, 3 дня подряд; ниже 135/85 — норма'),
    ('step', 'Степ-тест, пульс за 1 мин', 'Ступенька 30 см, 24 шага в минуту, 3 мин; сразу сесть и считать пульс 1 мин — чем ниже, тем лучше'),
    ('z2', 'Зона 2: средний пульс', '30 мин быстрой ходьбы или велотренажёра в темпе «говорю полными фразами»; средний пульс с 10-й по 30-ю минуту'),
    ('speed', 'Тест скорости рук, ударов за 10 с', 'Максимум точных прямых передней и задней по груше за 10 с, в бинтах и перчатках; лучшая из 2, отдых 2 мин'),
    ('ljump', 'Прыжок в длину с места, см', 'Только если нет боли в коленях и ахилле; лучшая из 3'),
    ('vjump', 'Прыжок вверх с места, см', 'Метка мелом на стене: стоя тянешься вверх, в прыжке касаешься как можно выше; разница, лучшая из 3'),
    ('pushups', 'Отжимания', 'До потери техники, корпус прямой'),
    ('pullups', 'Подтягивания', 'Строгие, из виса на прямых руках, через 3 мин после отжиманий'),
    ('split', 'Сплит-присед без веса', 'На каждую ногу до потери техники, без завала колена внутрь, максимум 30'),
    ('calf1', 'Подъём на носок на одной ноге', 'Полная амплитуда, максимум 30, на каждую ногу'),
    ('plank', 'Планка, с', 'До потери прямой линии, максимум 120 с'),
    ('splank', 'Боковая планка, с', 'На каждую сторону, максимум 120 с'),
    ('hang', 'Вис на перекладине, с', 'Активный вис, 1 попытка'),
    ('balance', 'Стойка на одной ноге, с', 'Глаза закрыты, руки на поясе, до 30 с; лучшая из 2 на каждую ногу'),
    ('reach', 'Наклон стоя, см до пола', 'Сколько сантиметров от пальцев до пола; достал — 0'),
    ('knee', 'Колено к стене, см', 'От большого пальца до стены, когда колено касается стены, а пятка на полу'),
    ('arms', 'Руки вверх у стены', 'Спина и таз у стены, прямые руки до касания стены: есть ли прогиб в пояснице'),
    ('thomas', 'Тест Томаса', 'Лёжа на краю стола, одно колено к груди: доходит ли второе бедро до горизонтали'),
]
TMAP = {t[0]: t for t in TESTS}
C0_EXTRA = [('frog', '«Лягушка» в висе', 'Колени к груди без раскачки, до потери техники'),
            ('rope', 'Скакалка до первого сбоя', 'Лёгкий темп, максимум 5 мин'),
            ('mile2', '«Две мили Ли» — 3,2 км', 'Быстрой ходьбой (можно с трусцой) в Зоне 2: время и средний пульс с 10-й минуты')]


def t_(i, extra=None):
    t = TMAP[i]
    d = {'id': i, 'name': t[1], 'how': t[2]}
    if extra:
        d.update(extra)
    return d


def test_day3(c):
    secs = [
        {'t': 'tests', 'title': 'Утренние замеры', 'tests': [t_('weight'), t_('waist'), t_('rhr'), t_('bp')],
         'foot': 'Давление — 3-й день замеров. Тесты — после обычного сна; результаты сравниваются с Циклом 0 во вкладке «Прогресс».'},
        warm_sec('A', P.info(c)[0]),
        {'t': 'tests', 'title': 'Тесты, часть 1', 'id': 'sec-ex', 'tests': [t_('speed'), t_('ljump'), t_('vjump'), t_('pushups'), t_('pullups')]},
        {'t': 'ex', 'title': 'После тестов', 'items': [
            cond('Бой с тенью на 50% — 3 × 2 мин', round_segs(3, 2, 60, 'Бой с тенью на 50%'), ['Отдых 1 мин.']),
            stretch_cond(f'Растяжка Ли — по {P.hold(P.info(c)[0], P.info(c)[2])} с', D4_STRETCH, P.hold(P.info(c)[0], P.info(c)[2]), 'Без пружинения.')]},
    ]
    return secs


def test_day4(c):
    tests2 = [t_('split'), t_('calf1'), t_('plank'), t_('splank'), t_('hang'), t_('balance'), t_('reach'), t_('knee'), t_('arms', {'yn': True}), t_('thomas', {'yn': True})]
    if c == 15:
        tests2.append({'id': 'gate_rope', 'name': 'Проверка ворот: скакалка 2 × 3 мин и 10 прыжков из приседа', 'how': 'Есть ли боль в ахилле и коленях', 'yn': True, 'ynLabels': ['Без боли', 'Есть боль']})
    if c == 30:
        tests2.append({'id': 'gate_hops', 'name': 'Проверка ворот: прыжки на одной ноге на месте, 3 × 10 на каждую', 'how': 'Отдых 1 мин; есть ли боль', 'yn': True, 'ynLabels': ['Без боли', 'Есть боль']})
        tests2.append({'id': 'dl125', 'name': 'Становая тяга: 5 повторов с весом 1,25 × масса тела', 'how': 'Разминка 50% × 5, 70% × 3, 85% × 1; до RPE 8. Запиши вес и прошёл ли'})
    if c == 45:
        tests2.append({'id': 'rec5', 'name': '«Рекорды на 5»: приседания и становая', 'how': 'Вес, с которым 5 повторов идут на RPE 8, без максимумов; после разминочных подходов'})
    secs = [
        {'t': 'tests', 'title': 'Степ-тест — первым, до разминки', 'tests': [t_('step')], 'foot': 'Утром — фото спереди, сбоку и сзади.'},
        warm_sec('B', 3, 'Без разминочных подходов со штангой: становая в тестах идёт со своими подводящими.' if c == 30 else 'Без разминочных подходов со штангой.', title='Разминка Б — 10 мин', noramp=True),
        {'t': 'tests', 'title': 'Тесты, часть 2', 'id': 'sec-ex', 'tests': tests2},
        {'t': 'ex', 'title': 'Заминка', 'items': [
            cond('Велотренажёр в Зоне 1 — 10 мин', [seg('Велотренажёр, Зона 1', 600, 'easy')], ['Спокойно, пульс до 108.'], kind='bike'),
            stretch_cond(f'Растяжка Ли — по {P.hold(P.info(c)[0], P.info(c)[2])} с', D4_STRETCH, P.hold(P.info(c)[0], P.info(c)[2]), 'Без пружинения.')]},
    ]
    if c in (15, 30):
        gate = P.GATE1 if c == 15 else P.GATE2
        nxt = {15: ('Фаза 2', 61, '41–60', 'циклы 11–15'), 30: ('Фаза 3', 121, '101–120', 'циклы 26–30')}[c]
        secs.append({'t': 'gate', 'title': 'Решение о переходе — отметь выполненное', 'items': list(gate),
                     'foot': f'Всё отмечено — с Дня {nxt[1]} начинается {nxt[0]}. Хотя бы один пункт не выполнен — повтори дни {nxt[2]} ({nxt[3]}) и проверь снова; нумерация дальше сдвигается на 20 дней. Лучше задержаться на 20 дней, чем потерять 3 месяца на травме.'})
    else:
        secs.append({'t': 'list', 'title': 'Итоги и что дальше', 'lines': [
            'Сравни каждую цифру со стартом из Цикла 0 и с тестами Дней 60 и 120 — таблица во вкладке «Прогресс»; положи рядом фото Цикла 0 и Дня 180.',
            'Тренировки продолжаются в режиме Фазы 3: разгрузка каждый 5-й цикл, тесты раз в 3 мезоцикла. Питание первые 2 цикла — на поддержании.',
            'Талия меньше 87 см и до формы уровня Брюса Ли (10–12% жира) осталось меньше 3 кг — так и оставайся на поддержании. Больше — после этих 2 циклов начни второй круг сушки на 2–4 месяца по правилам раздела 4 плана.']})
    return secs


# ------------------------------------------------------------------ сборка дней
MORNING_CHECK = 'Пульс покоя лёжа 60 с, сон, индекс готовности (сон, усталость, стресс, мышцы — каждое от 1 до 5), вес натощак. Цвет дня: зелёный — по плану; жёлтый — минус треть подходов, без ускорений, прыжков и изометрии; красный — прогулка 20–30 мин и растяжка или отдых.'


def strip_md(s):
    return re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', s)


def cycle_intro(c):
    Pp, m, mp, w = P.info(c)
    intro = [P.WAVE[w]]
    if w == 4 and c not in (29, 44):
        intro.append(P.STEP[Pp])
    if c in (15, 30):
        intro.append(f'Конец фазы: тесты в Дни {P.dn(c, 3)}–{P.dn(c, 4)} и решение о переходе.')
    if c == 45:
        intro.append(f'Последний цикл программы: итоговые тесты в Дни {P.dn(c, 3)}–{P.dn(c, 4)}.')
    if c in P.DIET:
        intro.append('Диет-брейк: все 4 дня — питание на поддержании, около +500 ккал за счёт углеводов. Вес может подняться на 0,5–1 кг за счёт воды — это запланировано.')
    if c == 32:
        intro.append('С Фазы 3 питание — на поддержании: тяжёлые веса, спринты и раунды требуют восстановления. До цели по талии (меньше 87 см) больше 2–3 см — мягкий дефицит; цифры — в разделе «Питание и сон».')
    if c == 29:
        intro.append('Шаг вперёд — проверка ворот в День 115: 5 раундов по 3 мин на груше.')
    if c == 44:
        intro.append('Шаг вперёд — контрольная тренировка по личной программе Ли в День 175.')
    return ' '.join(intro)


def morning_sec(c, k, extra=None):
    t = P.morning_tasks(c, k)
    lines = [MORNING_CHECK]
    if t:
        lines.append('<b>Сегодня ещё:</b> ' + '; '.join(t) + '.')
    if extra:
        lines += extra
    return {'t': 'list', 'title': 'Утро — 2 минуты', 'lines': lines, 'collapse': not t}


def build_day(c, k):
    Pp, m, mp, w = P.info(c)
    D = P.dn(c, k)
    deload = (w == 5)
    test = (c in P.TEST and k in (3, 4))
    day = {'d': D, 'c': c, 'm': m, 'P': Pp, 'w': w, 'dl': deload, 'test': c in P.TEST and k in (3, 4), 'diet': c in P.DIET, 'goal': cycle_intro(c)}
    food = strip_md(P.food('shift' if k <= 2 else 'train', c))
    if k == 1:
        secs, mins = proto_c(c, Pp, mp)
        day.update(k='C', title=('Кардио = калибровка Зоны 2' if c in P.TEST else 'Кардио Ли + бой с тенью'), time=f'≈ {mins} мин после смены')
        day['secs'] = [morning_sec(c, k)] + secs
    elif k == 2:
        secs, prog = proto_r(c, Pp, mp)
        day.update(k='R', title='Велотренажёр + бой с тенью + гибкость Ли', time='≈ 65 мин после смены', flex=prog)
        day['secs'] = [morning_sec(c, k)] + secs
    elif test and k == 3:
        day.update(k='T', title='Контрольные тесты, часть 1', time='≈ 70 мин')
        day['secs'] = test_day3(c)
    elif test and k == 4:
        title = {15: 'Контрольные тесты, часть 2 и решение о Фазе 2', 30: 'Контрольные тесты, часть 2 и решение о Фазе 3', 45: 'Итоговые тесты'}[c]
        day.update(k='T', title=title, time='≈ 60 мин')
        day['secs'] = test_day4(c)
    elif k == 3:
        entries, meta, tests = d3_entries(c)
        mm = int(5 * round(meta['minutes'] / 5))
        if c == 44:
            title = 'Контрольная тренировка Ли'
        elif c == 29:
            title = 'Раунды Ли + проверка ворот'
        elif deload:
            title = 'Раунды Ли, разгрузка'
        else:
            focus = ''
            if Pp >= 2:
                focus = ' (руки)' if c % 2 == 1 else ' (ноги)'
                if Pp == 2 and mp == 3 and c % 2 == 0:
                    focus = ' (руки + ноги)'
            title = 'Раунды Ли' + focus
        day.update(k='F', title=title, time=f'≈ {mm} мин')
        pre = 'Лучше в первой половине дня. За 5 мин до старта — квадратное дыхание 3 мин и визуализация 2 мин.'
        if Pp >= 2:
            pre += ' Бег можно сделать утром отдельно: Ли бегал рано утром, а раунды делал ближе к полудню (с. 130).'
        day['pre'] = pre
        notes = [strip_md(P.BAG_NOTE)]
        if c == 44:
            notes.append('<b>Сравни с Днём 115:</b> насколько упал пульс за минуту отдыха после последнего раунда на груше. Сегодня работа тяжелее (RPE 8–9 против 7) — если падение такое же или больше, выносливость выросла.')
        secs = [morning_sec(c, k), warm_sec('A', Pp), {'t': 'ex', 'title': 'Тренировка', 'id': 'sec-ex', 'items': entries}]
        if tests:
            secs.append({'t': 'tests', 'title': 'Запиши пульс', 'tests': tests})
        secs.append({'t': 'list', 'title': 'Груша и заметки', 'lines': notes})
        secs.append({'t': 'list', 'title': 'Вечером', 'lines': ['Прогулка 20–30 мин — «ежедневные возможности» Ли (с. 208).', 'Приготовь 4 контейнера еды на две смены.']})
        day['secs'] = secs
    else:
        entries, meta = conv_d4(c)
        mm = int(5 * round(meta['minutes'] / 5))
        A = (c % 2 == 1)
        kind = ('силовая Ли «А»' if A else 'силовая Ли «Б»') + (', разгрузка' if deload else '') + ' + велотренажёр + растяжка'
        if c == 44:
            kind += ' (после контрольной — без рекордов)'
        day.update(k='A' if A else 'B', title=kind[:1].upper() + kind[1:], time=f'≈ {mm} мин')
        day['pre'] = 'За 5 мин до старта — квадратное дыхание 3 мин и визуализация 2 мин.'
        day['secs'] = [morning_sec(c, k), warm_sec('B', Pp), {'t': 'ex', 'title': 'Тренировка', 'id': 'sec-ex', 'items': entries}]
    day['food'] = food
    # нумерация упражнений; пара «присед + занос за голову» — один номер, a и b
    n = 0
    for s in day['secs']:
        if s['t'] != 'ex':
            continue
        its = s['items']
        skip = set()
        for j, it in enumerate(its):
            if 'ex' not in it or j in skip:
                continue
            n += 1
            if it.get('lab_pair'):
                k = next(q for q in range(j + 1, len(its)) if 'ex' in its[q])
                it['lab'], its[k]['lab'] = f'{n}a', f'{n}b'
                skip.add(k)
                del it['lab_pair']
            else:
                it['lab'] = str(n)
    return day


def blocks():
    out = []
    for m in range(1, 10):
        Pp = (m - 1) // 3 + 1
        cyc = list(range(5 * (m - 1) + 1, 5 * m + 1))
        out.append({'m': m, 'P': Pp, 'cycles': cyc, 'days': [P.dn(cyc[0], 1), P.dn(cyc[-1], 4)], 'note': ' '.join(P.LEADS[m]), 'test': m in (3, 6, 9)})
    return out


def main(out):
    days = [build_day(c, k) for c in range(1, 46) for k in range(1, 5)]
    secs, index = [], {}
    for d in days:
        ids = []
        for sct in d['secs']:
            key = json.dumps(sct, ensure_ascii=False, sort_keys=True)
            if key not in index:
                index[key] = len(secs)
                secs.append(sct)
            ids.append(index[key])
        d['secs'] = ids
    data = {'ex': EX, 'groups': X.GROUPS, 'blocks': blocks(), 'days': days, 'secs': secs, 'tests': [{'id': t[0], 'name': t[1], 'how': t[2]} for t in TESTS],
            'c0extra': [{'id': t[0], 'name': t[1], 'how': t[2]} for t in C0_EXTRA], 'phases': ['Цикл 0', 'Фаза 1', 'Фаза 2', 'Фаза 3']}
    s = json.dumps(data, ensure_ascii=False, separators=(',', ':'))
    open(out, 'w', encoding='utf-8').write(s)
    print('days', len(days), 'bytes', len(s.encode('utf-8')))


if __name__ == '__main__':
    main(sys.argv[1])
