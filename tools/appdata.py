# -*- coding: utf-8 -*-
"""Данные приложения «Брюс Ли 6.0»: гайды Сарычева 100 → 150 → 200 на графике 2/2.

program.txt  — программа гайдов как есть (проценты, повторы, подходы).
exercises.py — справочник упражнений приложения.
Здесь: замены ради позвоночника, раскладка на график 2/2 (цикл 8 дней), кардио и вечерние протоколы.
Веса не считаются здесь — их считает приложение по максимуму и записям (адаптивно).

Запуск: python3 tools/appdata.py out.json
"""
import importlib.util, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))


def _load(name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(HERE, name + '.py'))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


X = _load('exercises')
EX = X.EX

# ------------------------------------------------------------------ гайды
GUIDES = [
    {'id': '100', 'name': 'Гайд 100', 'weeks': 9},
    {'id': '150', 'name': 'Гайд 150', 'weeks': 13},
    {'id': '200', 'name': 'Гайд 200', 'weeks': 15},
]
NCYC = sum(g['weeks'] for g in GUIDES)  # 37 циклов по 8 дней
# слоты цикла 2/2: В1 — День 1 гайда, В2 — кардио, смены, В3 — День 3, В4 — День 2, смены
SLOTS = [
    {'kind': 'gym', 'gd': 'd1', 'name': 'Выходной 1', 'short': 'В1'},
    {'kind': 'cardio', 'name': 'Выходной 2', 'short': 'В2'},
    {'kind': 'work', 'name': 'Смена 1', 'short': 'См'},
    {'kind': 'work', 'name': 'Смена 2', 'short': 'См'},
    {'kind': 'gym', 'gd': 'd3', 'name': 'Выходной 3', 'short': 'В3'},
    {'kind': 'gym', 'gd': 'd2', 'name': 'Выходной 4', 'short': 'В4'},
    {'kind': 'work', 'name': 'Смена 1', 'short': 'См'},
    {'kind': 'work', 'name': 'Смена 2', 'short': 'См'},
]


def parse_program():
    src = open(os.path.join(HERE, 'program.txt'), encoding='utf-8').read()
    guides, cur = {}, None
    for line in src.splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        m = re.match(r'== G(\d+) W(\d+)', line)
        if m:
            cur = {'w': int(m.group(2)), 'd': {}}
            guides.setdefault(m.group(1), []).append(cur)
            continue
        m = re.match(r'(d[123]):\s*(.*)', line)
        exs = []
        for part in m.group(2).split(';;'):
            part = part.strip()
            note = None
            if '|' in part:
                part, note = [x.strip() for x in part.split('|', 1)]
            ss = part.startswith('+ss ')
            if ss:
                part = part[4:].strip()
            key, spec = part.split(' ', 1)
            spec = spec.strip()
            e = {'k': key}
            if ss:
                e['ss'] = 1
            if note:
                e['n'] = note
            if spec.startswith('W'):
                r, s = spec[2:].split('x')
                e['W'] = [int(r), int(s)]
            elif ',' in spec or spec.count('x') == 2:
                e['P'] = []
                for ch in spec.split(','):
                    p, r, s = ch.strip().split('x')
                    e['P'].append([float(p), int(r), int(s)])
            elif spec.count('x') == 1:
                r, s = spec.split('x')
                e['B'] = [int(r), int(s)]
            else:
                e['B'] = [int(spec), 1]
            exs.append(e)
        cur['d'][m.group(1)] = exs
    for g in GUIDES:
        assert len(guides[g['id']]) == g['weeks'], g
    return guides


# ------------------------------------------------------------------ замены и роли
# role: main — % от максимума жима (рабочий максимум гайда, адаптивный);
#       pct  — % от максимума жима, но не тяжелее «запаса 2» по своей оценке (cap — доля от максимума жима по умолчанию);
#       dbpct — % от максимума жима на пару гантелей; acc — вес по прошлым записям (стартовая оценка e — 1ПМ при жиме 105);
#       own  — % от собственного максимума упражнения; gv — противовес гравитрона; bw — без веса; core — тройка Макгилла; note — текст.
WHY = {
    'squat': 'Штанга на плечах — осевая нагрузка на все отделы с протрузиями. Сплит-присед с гантелями — из твоей программы 5.0: ноги работают так же, '
             'а спина нагружена в разы меньше. Вместо него можно разгибание ног — это разрешает сам гайд.',
    'dl': 'Становая при грыже и 12 часах наклонов на смене — главный риск всей программы. Ягодичный мост нагружает ту же заднюю цепь без сжатия дисков '
          'и учит подкручивать таз — то, чего не хватает при гиперлордозе.',
    'rdl': 'Румынская тяга — наклон под весом. Сгибание ног на фитболе в мосте нагружает заднюю поверхность бедра и ягодицы, не сгибая поясницу.',
    'hyper': 'В версии 5.0 гиперэкстензия была убрана как нагрузка на поясницу. Ягодичный мост делает ту же работу для ягодиц, '
             'а «птица-собака» в тройке Макгилла — для разгибателей спины.',
    'standing_press': 'Стоя поясница уходит в прогиб под весом — при гиперлордозе и грыже это лишнее. Сидя со спинкой 75–80° плечи работают так же.',
    'seated_press': 'Спинка 75–80°, а не вертикальная: так поясница меньше прогибается.',
    'tbar': 'Т-гриф с упором грудью: та же тяга, но поясница не держит вес.',
    'bb_row': 'Тяга штанги в наклоне держит поясницу под весом весь подход. С упором грудью спина работает так же.',
    'db_row': 'С упором грудью тяга не нагружает поясницу.',
    'dips': 'По правилам версии 5.0 брусья — только в гравитроне и неглубоко: так меньше риск для плеч.',
    'kb_squat': 'Касание скамьи ограничивает глубину и не даёт округлить поясницу.',
    'bb_curl': 'Сарычев разрешает скамью Скотта: с опорой корпус не раскачивается и поясница не прогибается.',
    'core': 'Скручивания с весом многократно сгибают позвоночник под нагрузкой — при грыже это плохая сделка. Тройка Макгилла держит корпус жёстким, не сгибая его.',
}
ORIG = {
    'squat': 'Приседания со штангой', 'dl': 'Становая тяга', 'rdl': 'Мёртвая (румынская) тяга', 'hyper': 'Гиперэкстензия',
    'hyper_w': 'Гиперэкстензия с весом', 'standing_press': 'Жим штанги стоя', 'tbar': 'Тяга Т-грифа', 'bb_row': 'Тяга штанги в наклоне',
    'db_row': 'Тяга гантели в наклоне', 'dips': 'Отжимания на брусьях', 'kb_squat': 'Приседания с гирей', 'bb_curl': 'Сгибание штанги на бицепс стоя',
    'core': 'Пресс',
}
# ключ гайда -> (упражнение приложения, роль, параметры)
MAP = {
    'bench': ('bench', 'main', {}), 'test': ('bench', 'test', {}), 'bench_speed': ('bench_speed', 'main', {'rest': 60}),
    'bench_neg': ('bench_neg', 'main', {}), 'board': ('board', 'main', {}), 'board15': ('board15', 'main', {}),
    'sling': ('sling', 'main', {'opt': 1}),
    'cg_bench': ('cg_bench', 'pct', {'cap': 0.90}), 'mg_bench': ('mg_bench', 'pct', {'cap': 0.95}), 'wg_bench': ('wg_bench', 'pct', {'cap': 0.95}),
    'incl_bench': ('incl_bench', 'pct', {'cap': 0.80}), 'seated_press': ('ohp_seat', 'pct', {'cap': 0.60}),
    'standing_press': ('ohp_seat', 'pct', {'cap': 0.60}),
    'db_bench_pct': ('db_bench', 'dbpct', {}), 'incl_db_pct': ('incl_db', 'dbpct', {}), 'french_pct': ('french', 'pct', {'cap': 0.40}),
    'db_fly': ('db_fly', 'acc', {}), 'incl_db_fly': ('incl_db_fly', 'acc', {}), 'db_bench': ('db_bench', 'acc', {}),
    'incl_db': ('incl_db', 'acc', {}), 'db_seated': ('db_seated', 'acc', {}), 'bb_curl': ('ez_scott', 'acc', {}),
    'rev_curl': ('rev_curl', 'acc', {}), 'db_curl': ('db_curl', 'acc', {}), 'hammer': ('hammer', 'acc', {}),
    'wrist_curl': ('wrist_curl', 'acc', {}), 'tri_push': ('tri_rope', 'acc', {}), 'french': ('french', 'acc', {}),
    'lat_raise': ('lat_raise', 'acc', {}), 'lat_pull': ('latpd', 'acc', {}), 'cable_row': ('seatrow', 'acc', {}),
    'tbar': ('tbar_cs', 'acc', {}), 'bb_row': ('tbar_cs', 'acc', {}), 'db_row': ('cs_db_row', 'acc', {}),
    'leg_ext': ('leg_ext', 'acc', {}), 'leg_curl': ('leg_curl', 'acc', {}), 'kb_squat': ('goblet_box', 'acc', {'rir': 3}),
    'squat': ('split_db', 'acc', {'rir': 3, 'per': 'на каждую ногу'}), 'dl': ('hipthrust', 'own', {}),
    'rdl': ('fitball_curl', 'bw', {}),
    'dips': ('dips_grav', 'gv', {}), 'cg_pullups': ('pullup_cg', 'gv', {}), 'wide_pullups': ('pullup_wg', 'gv', {}),
    'neg_pullups': ('pullup_neg', 'bw', {}), 'farewell': ('pullup_wg', 'farewell', {}),
    'cg_pushups': ('cg_pushups', 'bw', {}), 'bw_squat': ('box_squat', 'bw', {}), 'box_squat': ('box_squat', 'bw', {}),
    'hyper': ('bridge', 'bw', {}), 'hyper_w': ('bridge_sl', 'bw', {'per': 'на каждую ногу'}), 'bb_curl_empty': ('ez_empty', 'bw', {}),
    'core': ('core', 'core', {}), 'meditation': ('meditation', 'note', {}),
}
# стартовые оценки разового максимума при жиме 105 кг (кг; у гантелей — одна гантель), тип веса, запас по умолчанию
ENG = {
    'db_fly': 22, 'incl_db_fly': 20, 'db_bench': 40, 'incl_db': 36, 'db_seated': 28, 'ez_scott': 40, 'rev_curl': 32, 'db_curl': 18,
    'hammer': 20, 'wrist_curl': 50, 'tri_rope': 50, 'french': 40, 'lat_raise': 13, 'latpd': 80, 'seatrow': 85, 'tbar_cs': 80,
    'cs_db_row': 34, 'leg_ext': 75, 'leg_curl': 60, 'goblet_box': 36, 'split_db': 20, 'hipthrust': 120,
    'cg_bench': 0.90 * 105, 'mg_bench': 0.95 * 105, 'wg_bench': 0.95 * 105, 'incl_bench': 0.80 * 105, 'ohp_seat': 0.60 * 105,
}
REST = {'main': 180, 'test': 240, 'pct': 150, 'dbpct': 120, 'acc': 90, 'own': 120, 'gv': 90, 'bw': 60, 'farewell': 60, 'core': 0, 'note': 0}


def map_item(e):
    key = e['k']
    ex, role, prm = MAP[key]
    it = {'ex': ex, 'role': role, 'src': key}
    for f in ('P', 'W', 'B', 'ss'):
        if f in e:
            it[f] = e[f]
    note = e.get('n')
    if note and note.startswith('alt:'):
        it['alt'] = ('Или разгибание ног в тренажёре — так разрешает сам гайд' if key == 'squat'
                     else 'Гайд разрешает здесь гиперэкстензию с весом — у тебя её заменяет ягодичный мост')
        note = None
    if note:
        it['n'] = note
    if key in ORIG and not (key == 'core'):
        it['orig'] = ORIG[key]
    if key == 'core':
        it['orig'] = 'Пресс'
    for k in (key, 'hyper' if key == 'hyper_w' else None):
        if k and k in WHY:
            it['why'] = WHY[k]
            break
    it.update({k: v for k, v in prm.items() if k != 'rest'})
    it['rest'] = prm.get('rest', REST[role])
    if role == 'farewell':
        it['name'] = '«Прощание с залом»: 50 подтягиваний'
    if key == 'hyper_w' and 'P' in it:  # «20x10x3» в гайде — это 20 кг × 10 × 3
        kg, r, s = it.pop('P')[0]
        it['B'] = [r, s]
        it['orig'] = f'Гиперэкстензия с весом {int(kg)} кг'
    if key == 'hyper_w' and 'W' in it:
        it['B'] = it.pop('W')
    if key == 'hyper' and 'W' in it:
        it['B'] = it.pop('W')
    if key == 'dips' and 'B' in it:
        it['W'] = it.pop('B')
    if key in ('cg_pullups', 'wide_pullups') and 'B' in it:
        it['W'] = it.pop('B')
    if key == 'rdl':  # % мёртвой тяги -> повторы на фитболе
        it['B'] = [it['P'][0][1], it['P'][0][2]]
        it.pop('P')
    if key == 'squat':  # % приседа -> повторы сплит-приседа, вес по записям
        p, r, s = it.pop('P')[0]
        it['W'] = [r, s]
        it['gp'] = p
    return it


DELOAD = {
    'd3': [{'k': 'bench', 'P': [[60, 5, 3]], 'n': 'разгрузка'}, {'k': 'db_fly', 'W': [12, 2], 'n': 'легко'},
           {'k': 'lat_raise', 'W': [15, 2], 'n': 'легко'}, {'k': 'core', 'B': [1, 2]}],
    'd2': [{'k': 'lat_pull', 'W': [12, 2], 'n': 'легко'}, {'k': 'cable_row', 'W': [12, 2], 'n': 'легко'},
           {'k': 'leg_curl', 'W': [12, 2], 'n': 'легко'}, {'k': 'hyper', 'B': [12, 2]}, {'k': 'core', 'B': [1, 2]}],
}


def program():
    raw = parse_program()
    out = {}
    for g in GUIDES:
        weeks = []
        for wk in raw[g['id']]:
            days = {}
            for dk in ('d1', 'd2', 'd3'):
                src = wk['d'].get(dk)
                dl = False
                if src is None:
                    src, dl = DELOAD[dk], True
                items = [map_item(e) for e in src]
                for it in items:
                    if dl:
                        it['dl'] = 1
                days[dk] = {'items': items, 'deload': dl, 'test': any(it['role'] == 'test' for it in items)}
            weeks.append(days)
        out[g['id']] = weeks
    return out


# ------------------------------------------------------------------ кардио и протоколы
def seg(l, s, k='work', t=None):
    d = {'l': l, 's': int(s), 'k': k}
    if t:
        d['t'] = t
    return d


def z2_session(mins, title='Кардио: зона 2'):
    w = 5 if mins >= 30 else 0
    segs = ([seg('Разминка — зона 1', w * 60, 'warm', 'пульс {Z1}')] if w else []) + \
           [seg('Зона 2', (mins - 2 * w) * 60, 'work', 'пульс {Z2}, дышишь носом, говоришь фразами')] + \
           ([seg('Заминка — зона 1', w * 60, 'easy', 'пульс {Z1}')] if w else [])
    return {'title': title, 'mins': mins, 'kind': 'z2', 'segs': segs,
            'lines': ['Велосипед или ходьба в горку (уклон 6–10%, без поручней). Не бег и не гребной тренажёр — они бьют по дискам.',
                      'Пульс {Z2} — это зона 2 по твоему пульсу покоя из профиля.']}


def int_session():
    segs = [seg('Разминка — зона 2', 600, 'warm', 'пульс {Z2}')]
    for i in range(4):
        segs.append(seg(f'Отрезок {i + 1}/4 — тяжело', 240, 'work', 'пульс {Z5}, темп держишь до конца'))
        if i < 3:
            segs.append(seg('Отдых — легко крутишь', 180, 'easy', 'пульс {Z1}'))
    segs.append(seg('Заминка', 360, 'easy', 'пульс {Z1}'))
    return {'title': 'Интервалы 4 × 4 мин', 'mins': 40, 'kind': 'int', 'segs': segs,
            'lines': ['Велосипед или крутая горка, не бег.', 'Плохо спал, ноет спина или жёлтый день — вместо интервалов 50 минут зоны 2.',
                      'Боль или давление в груди, необычная одышка, головокружение — стоп и к врачу.']}


def short_session(mins, z, title):
    t = 'пульс {Z1}' if z == 1 else 'пульс {Z2}'
    return {'title': title, 'mins': mins, 'kind': 'z' + str(z), 'segs': [seg('Зона ' + str(z), mins * 60, 'work' if z == 2 else 'easy', t)], 'lines': []}


def cardio_main(gi, w, weeks):
    test = w == weeks
    if test:
        return z2_session(40), 'После проходки — только лёгкая аэробика.'
    if gi == 0:
        return z2_session([40, 45, 45, 50, 50, 55, 55, 60][w - 1]), 'Гайд 100 — строим базу: только зона 2.'
    if w >= 11:
        m = 45 if not (gi == 2 and w >= 13) else (30 if w == 14 else 40)
        return z2_session(m), 'Перед проходкой интервалы убраны — силы идут в жим.'
    if w % 2 == 0:
        return int_session(), 'Интервалы раз в два цикла — для выносливости сердца.'
    return z2_session(60), ''


MCGILL = [
    {'ex': 'curlup', 't': '<b>Скручивание по Макгиллу</b> — 6 удержаний по 10 с', 'segs': [seg('Скручивание — удержание', 10, 'work') if i % 2 == 0 else seg('Отпусти', 5, 'easy') for i in range(11)]},
    {'ex': 'splank', 't': '<b>Боковая планка</b> — 20–30 с на каждую сторону', 'segs': [seg('Боковая планка — левая', 25, 'work'), seg('Смена стороны', 5, 'easy'), seg('Боковая планка — правая', 25, 'work')]},
    {'ex': 'birddog', 't': '<b>«Птица-собака»</b> — 6 раз на сторону, удержание 8 с', 'segs': [seg('Птица-собака — ' + ('левая рука' if i % 2 == 0 else 'правая рука'), 8, 'work') for i in range(12)]},
]


def evening_steps():
    return [
        {'ex': 'breath9090', 't': '<b>Дыхание 90/90 у стены</b> — 6 медленных вдохов', 'segs': [seg('Дыхание 90/90', 90, 'easy')]},
    ] + MCGILL + [
        {'ex': 'hipflex', 't': '<b>Растяжка сгибателя бедра в полувыпаде</b> — по 40 с на сторону, таз подкручен', 'segs': [seg('Левая нога сзади', 40, 'work'), seg('Смена', 5, 'easy'), seg('Правая нога сзади', 40, 'work')]},
        {'ex': 'lying9090', 't': '<b>Лёжа 90/90</b> — 2 минуты медленного дыхания перед сном', 'segs': [seg('Лёжа 90/90, вдох 4 с — выдох 6 с', 120, 'easy')]},
    ]


def spine_steps():
    return MCGILL + [
        {'ex': 'couch', 't': '<b>Растяжка у дивана</b> — по 40 с на сторону', 'segs': [seg('Левая нога у дивана', 40, 'work'), seg('Смена', 5, 'easy'), seg('Правая нога у дивана', 40, 'work')]},
        {'ex': 'hipflex', 't': '<b>Сгибатель бедра в полувыпаде</b> — по 40 с на сторону', 'segs': [seg('Левая нога сзади', 40, 'work'), seg('Смена', 5, 'easy'), seg('Правая нога сзади', 40, 'work')]},
    ]


READY_GYM = [
    '<b>Пульс покоя</b> (лёжа, сразу после пробуждения): норма — ±5 от обычного; жёлтый — +6–9; красный — +10 и больше или простуда.',
    '<b>Сон:</b> норма — 7 ч и больше; жёлтый — 5,5–7 ч; красный — меньше 5,5 ч.',
    '<b>Боль в пояснице или шее (0–10):</b> норма — 0–2; жёлтый — 3–4 или скованность дольше 30 мин; красный — 5 и выше.',
    '<b>Смена накануне:</b> тяжёлая (переработка, больше 15 тыс. шагов, усталость 8 из 10) — жёлтый.',
    '<b>Первый разминочный подход жима</b> (55–60% на 5) идёт заметно тяжелее обычного — жёлтый.',
    '<b>Решение.</b> Всё в норме — по плану. Жёлтый — приложение снизит веса на 10% и уберёт подходы от 90%, интервалы — на зону 2. '
    'Красный — вместо зала восстановление: 30 мин зоны 1–2, тройка Макгилла и растяжка.',
    '<b>Онемение, слабость или боль в ноге или руке — не жёлтый, а стоп</b>: тренировку отменить, план действий — в «Красных флагах» профиля.',
]
FOOD_SHIFT = ('<b>Рабочий день — около 2100 ккал:</b> белок 165 г, жиры 75 г, углеводы ≈ 190 г, клетчатка 30–40 г, вода 2,5–3 л. '
              'Завтрак около 06:00 (35–40 г белка, самый углеводный приём), обед в 11–12 (40 г белка), перекус в 15–16 (25–30 г), '
              'ужин в 19:50–20:20 (40 г белка, мало жира) — не позже чем за 1,5 ч до сна. Кофеин — до 14:00.')
FOOD_GYM = ('<b>День зала — около 2350 ккал:</b> белок 165 г, жиры 70 г, углеводы ≈ 265 г; 4 приёма по ≈ 40 г белка; основные углеводы — до и после зала. '
            'Вода 2,5–3 л и ещё 0,5 л на час тренировки. Креатин моногидрат 3–5 г в день — по желанию. Кофеин — до 14:00.')
FOOD_REST = ('<b>Выходной без зала — около 2200 ккал:</b> белок 165 г, углеводы меньше, чем в день зала. Прогулка 30–40 мин — лучший добор против висцерального жира.')
FOOD_RULE = 'Раз в 2 недели сверяй средний вес: худеешь медленнее 0,3 кг в неделю — минус 150 ккал (углеводы и жиры); быстрее 0,8 кг — плюс 150 ккал.'
SLEEP_SHIFT = 'Сон 22:00 – 05:30: экран убрать за 45 минут, в спальне темно и прохладно. Интенсивной нагрузки вечером нет.'
SLEEP_OFF = 'Сон 7,5–9 часов, подъём в одно время ±1 час. Зал — через 1,5–3 часа после еды; первые 1–2 часа после сна без тяжёлых наклонов: диски ещё «набухшие».'


def gym_title(dk, d):
    if d['test']:
        return 'Проходка: разовый максимум в жиме'
    if d['deload']:
        return 'Разгрузка после проходки'
    exs = [it['ex'] for it in d['items']]
    legs = any(x in exs for x in ('split_db', 'leg_ext', 'goblet_box', 'box_squat'))
    back = any(x in exs for x in ('hipthrust', 'tbar_cs', 'latpd', 'seatrow', 'pullup_cg', 'pullup_wg', 'cs_db_row'))
    if dk == 'd2':
        parts = ['спина']
        if any(x in exs for x in ('hipthrust', 'leg_curl', 'fitball_curl', 'split_db', 'leg_ext', 'goblet_box')):
            parts.append('ноги')
        if any(it['role'] in ('pct', 'main') or it['ex'] in ('incl_db', 'db_seated', 'lat_raise') for it in d['items']):
            parts.append('плечи и жимы')
        return 'Спина' + (', ' + ', '.join(parts[1:]) if len(parts) > 1 else '')
    t = 'Жим лёжа'
    if any(it['ex'] == 'bench_speed' for it in d['items']):
        t = 'Скоростной жим'
    if legs:
        t += ' и ноги'
    elif back:
        t += ' и спина'
    return t


def build():
    prog = program()
    days, gstart = [], 0
    pool, pidx = [], {}

    def ref(obj):  # одинаковые кардио-блоки хранятся один раз
        k = json.dumps(obj, ensure_ascii=False, sort_keys=True)
        if k not in pidx:
            pidx[k] = len(pool)
            pool.append(obj)
        return pidx[k]

    for gi, g in enumerate(GUIDES):
        for w in range(1, g['weeks'] + 1):
            c = gstart + w
            main, why = cardio_main(gi, w, g['weeks'])
            for i, sl in enumerate(SLOTS):
                d = {'d': (c - 1) * 8 + i + 1, 'c': c, 'i': i, 'g': gi, 'w': w, 'kind': sl['kind']}
                if sl['kind'] == 'gym':
                    gd = prog[g['id']][w - 1][sl['gd']]
                    d['gd'] = sl['gd']
                    d['test'] = gd['test']
                    d['deload'] = gd['deload']
                    d['title'] = gym_title(sl['gd'], gd)
                    if i == 0:
                        d['after'] = ref(short_session(10, 1, 'После зала: заминка 10 мин'))
                    elif i == 4:
                        d['after'] = ref(short_session(15 if gi == 0 else 20, 2, 'После зала: зона 2'))
                    else:
                        d['after'] = ref(short_session(15, 2, 'После зала: зона 2 — ходьба в горку или велосипед'))
                    d['food'] = 'gym'
                elif sl['kind'] == 'cardio':
                    d['title'] = 'Кардио и спина' if main['kind'] == 'z2' else 'Интервалы и спина'
                    d['cardio'] = ref(main)
                    d['why'] = why
                    d['food'] = 'rest'
                else:
                    d['title'] = 'Смена: восстановление'
                    d['food'] = 'shift'
                days.append(d)
        gstart += g['weeks']
    assert len(days) == NCYC * 8
    used = {it['ex'] for g in prog.values() for wk in g for dd in wk.values() for it in dd['items']}
    used |= {'curlup', 'splank', 'birddog', 'breath9090', 'hipflex', 'couch', 'lying9090', 'leg_ext'}
    used.discard('core')
    ex = {k: v for k, v in EX.items() if k in used}
    missing = used - set(EX)
    assert not missing, missing
    zones = [{'id': 'Z1', 'name': 'Зона 1 — восстановление', 'lo': 0.40, 'hi': 0.50},
             {'id': 'Z2', 'name': 'Зона 2 — аэробная база', 'lo': 0.50, 'hi': 0.60},
             {'id': 'Z3', 'name': 'Зона 3 — «серая зона»', 'lo': 0.60, 'hi': 0.70},
             {'id': 'Z4', 'name': 'Зона 4 — порог', 'lo': 0.70, 'hi': 0.80},
             {'id': 'Z5', 'name': 'Зона 5 — интервалы', 'lo': 0.80, 'hi': 0.90}]
    food = {'gym': [FOOD_GYM, FOOD_RULE, SLEEP_OFF], 'rest': [FOOD_REST, FOOD_RULE, SLEEP_OFF], 'shift': [FOOD_SHIFT, FOOD_RULE, SLEEP_SHIFT]}
    return {'guides': GUIDES, 'slots': SLOTS, 'prog': prog, 'days': days, 'ex': ex, 'groups': X.GROUPS, 'eng': ENG, 'cardios': pool, 'food': food,
            'evening': evening_steps(), 'spine': spine_steps(), 'mcgill': MCGILL, 'ready': READY_GYM, 'zones': zones}


def main(out):
    data = build()
    s = json.dumps(data, ensure_ascii=False, separators=(',', ':'))
    open(out, 'w', encoding='utf-8').write(s)
    n_items = sum(len(dd['items']) for g in data['prog'].values() for wk in g for dd in wk.values())
    print('days', len(data['days']), 'items', n_items, 'ex', len(data['ex']), 'bytes', len(s.encode('utf-8')))


if __name__ == '__main__':
    main(sys.argv[1])
