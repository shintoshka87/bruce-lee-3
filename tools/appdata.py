# -*- coding: utf-8 -*-
"""Данные приложения «Брюс Ли 6.1»: гайды Сарычева 100 → 150 → 200 на графике 2/2, две силовые за цикл.

program.txt  — программа гайдов как есть (проценты, повторы, подходы).
exercises.py — справочник упражнений приложения.
Здесь: замены ради позвоночника, сборка недели гайда в две силовые (А и Б), раскладка на цикл 8 дней,
кардио для сердца и протоколы восстановления. Веса не считаются здесь — их считает приложение по максимуму и записям.

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
# цикл 2/2: В1 — силовая А, В2 — кардио, две смены, В3 — силовая Б, В4 — восстановление, две смены.
# Между силовыми всегда три дня, перед каждой парой смен — лёгкий день.
SLOTS = [
    {'kind': 'gym', 'gd': 'a', 'name': 'Выходной 1', 'short': 'В1'},
    {'kind': 'cardio', 'name': 'Выходной 2', 'short': 'В2'},
    {'kind': 'work', 'name': 'Смена 1', 'short': 'См'},
    {'kind': 'work', 'name': 'Смена 2', 'short': 'См'},
    {'kind': 'gym', 'gd': 'b', 'name': 'Выходной 3', 'short': 'В3'},
    {'kind': 'rest', 'name': 'Выходной 4', 'short': 'В4'},
    {'kind': 'work', 'name': 'Смена 1', 'short': 'См'},
    {'kind': 'work', 'name': 'Смена 2', 'short': 'См'},
]
# где стояли дни гайда в версии 6.0 (В1 — День 1, В3 — День 3, В4 — День 2): по этим меткам приложение переносит старые записи
OLD_SLOT = {'d1': 0, 'd3': 4, 'd2': 5}


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
#       own  — % от собственного максимума упражнения; gv — противовес гравитрона; bw — без веса; core — тройка Макгилла; note — текст;
#       sq   — широкий присед (по желанию в профиле): старт 40 кг, +2,5 кг за цикл при запасе 3+, потолок по гайду.
WHY = {
    'squat': 'Штанга на плечах — осевая нагрузка на все отделы с протрузиями. Сплит-присед с гантелями — из твоей программы 5.0: ноги работают так же, '
             'а спина нагружена в разы меньше. Вместо него можно разгибание ног — это разрешает сам гайд. '
             'Широкий присед на скамью можно включить в профиле.',
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
WHY_WIDE = ('Включено в профиле вместо сплит-приседа. Широкая постановка и скамья на высоте колена держат корпус вертикальнее и ограничивают глубину — '
            'рычаг на поясницу короче. Вес: старт 40 кг, +2,5 кг за цикл, если все повторы шли с запасом 3+ и на следующий день спина была в норме; '
            'потолок 60 кг в гайде 150 и 70 кг в гайде 200. Гриф — специальный для приседа или низко на трапециях, не на шее: в шее протрузии. '
            'Что-то отдаёт в ногу или на следующий день боль в спине выше 3 из 10 — сразу обратно на сплит-присед (Профиль → Присед).')
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
REST = {'main': 180, 'test': 240, 'pct': 150, 'dbpct': 120, 'acc': 90, 'own': 120, 'gv': 90, 'bw': 60, 'farewell': 60, 'core': 0, 'note': 0,
        'sq': 150}


def map_item(e):
    key = e['k']
    ex, role, prm = MAP[key]
    it = {'ex': ex, 'role': role, 'src': key}
    for f in ('P', 'W', 'B', 'ss', 'o'):
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
    if e.get('opt'):
        it['opt'] = 1
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
        # вариант из профиля: широкий присед на скамью (потолок веса ставит program() по гайду)
        it['wide'] = {'ex': 'wide_box_squat', 'role': 'sq', 'rest': REST['sq'], 'rir': 3, 'per': '', 'why': WHY_WIDE}
    return it


DELOAD = {
    'd3': [{'k': 'bench', 'P': [[60, 5, 3]], 'n': 'разгрузка'}, {'k': 'db_fly', 'W': [12, 2], 'n': 'легко'},
           {'k': 'lat_raise', 'W': [15, 2], 'n': 'легко'}, {'k': 'core', 'B': [1, 2]}],
    'd2': [{'k': 'lat_pull', 'W': [12, 2], 'n': 'легко'}, {'k': 'cable_row', 'W': [12, 2], 'n': 'легко'},
           {'k': 'leg_curl', 'W': [12, 2], 'n': 'легко'}, {'k': 'hyper', 'B': [12, 2]}, {'k': 'core', 'B': [1, 2]}],
}

# ------------------------------------------------------------------ неделя гайда -> две силовые
# А (В1) = День 1 + тяги из Дня 2.  Б (В3) = День 3 + один жим из Дня 2 (до 4 подходов) + ноги и ягодицы из Дня 2.
# Жим, его вариации, тяги, трицепс и вся работа на бицепс и предплечья сохраняются. Пресс (тройка Макгилла) — дома каждый вечер,
# мостики из Дня 2 — дома в день восстановления. Вторая разводка и махи из Дня 2 не дублируются.
# Руки — в конце, парами с трицепсом или разводкой; если тренировка дольше 105 минут, третий жим из Дня 2 и вторая разводка — «по желанию».
CAT = {}
for _ks, _c in [('bench test bench_speed bench_neg board board15 sling', 'BM'),
                ('cg_bench mg_bench wg_bench incl_bench seated_press standing_press db_bench_pct incl_db_pct db_bench incl_db db_seated dips cg_pushups', 'P2'),
                ('french french_pct tri_push', 'TRI'), ('db_fly incl_db_fly', 'FLY'), ('lat_raise', 'DELT'),
                ('bb_curl rev_curl db_curl hammer wrist_curl bb_curl_empty', 'ARM'),
                ('lat_pull cable_row tbar bb_row db_row cg_pullups wide_pullups neg_pullups farewell', 'PULL'),
                ('squat kb_squat bw_squat box_squat leg_ext leg_curl dl rdl hyper hyper_w', 'LOW'),
                ('core', 'CORE'), ('meditation', 'NOTE')]:
    for _k in _ks.split():
        CAT[_k] = _c
COMPOUND = {'BM', 'P2', 'LOW', 'PULL'}
HOME = {'hyper', 'hyper_w'}
LONG = 105  # минут: дольше — третий жим из Дня 2 и вторая разводка «по желанию»


def _sets(e):
    if 'P' in e:
        return [r for p, r, n in e['P'] for _ in range(n)]
    if 'W' in e:
        return [e['W'][0]] * e['W'][1]
    if 'B' in e:
        return [e['B'][0]] * e['B'][1]
    return []


def _rest(e):
    ex, role, prm = MAP[e['k']]
    return prm.get('rest', REST[role]) / 60


def _exec(e):
    ex, role, prm = MAP[e['k']]
    k = 2 if prm.get('per') else 1
    return [(0.4 if r <= 5 else 0.6 if r <= 10 else 0.8 if r <= 15 else 1.0) * k for r in _sets(e)]


def _single(e):
    c = CAT[e['k']]
    if c == 'CORE':
        return 6.0
    if c == 'NOTE':
        return 5.0
    if e['k'] == 'farewell':
        return 10.0
    return 1.5 + sum(x + _rest(e) for x in _exec(e))


def _pair(u):
    ex = [_exec(e) for e in u]
    n = max(len(x) for x in ex)
    rest = max(_rest(e) for e in u)
    return 2.0 + sum(sum(x[i] for x in ex if i < len(x)) + rest for i in range(n))


def est_minutes(us):
    """Оценка длительности: разминка 8 мин, подводящие к жиму 8 мин, подходы и отдых по таймерам приложения."""
    t = 8.0 + (8.0 if any(CAT[e['k']] == 'BM' for u in us for e in u) else 0.0)
    return t + sum(_single(u[0]) if len(u) == 1 else _pair(u) for u in us)


def _units(lst, src):
    out = []
    for i, e in enumerate(lst):
        e = dict(e, o=[OLD_SLOT[src], i])
        if e.get('ss') and out:
            out[-1].append(e)
        else:
            out.append([e])
    return out


def _cat(u):
    return CAT[u[0]['k']]


def _split(us):
    """День гайда: голова (до последнего базового упражнения), хвост (изоляция и руки), заметки. Пресс уходит домой."""
    last = max([j for j, u in enumerate(us) if _cat(u) in COMPOUND], default=-1)
    keep = lambda part: [u for u in part if _cat(u) not in ('CORE', 'NOTE')]
    return keep(us[:last + 1]), keep(us[last + 1:]), [u for u in us if _cat(u) == 'NOTE']


def _cap(u, n=4):
    e = dict(u[0])
    if 'P' in e:
        P, left = [], n
        for p, r, s in e['P']:
            if left <= 0:
                break
            P.append([p, r, min(s, left)])
            left -= min(s, left)
        e['P'] = P
    for f in ('W', 'B'):
        if f in e:
            e[f] = [e[f][0], min(e[f][1], n)]
    return [e] + u[1:]


LIGHT_LOW = {'leg_ext', 'leg_curl', 'kb_squat', 'box_squat', 'bw_squat', 'rdl'}
PRESS_ACC = {'db_bench', 'incl_db', 'db_seated', 'cg_pushups'}


def _kind(u):
    """Тип одиночного упражнения для суперсетов; None — не ставится в пару (жимы от максимума, тяжёлые ноги, пары гайда)."""
    if len(u) != 1 or u[0].get('opt'):
        return None
    k, c = u[0]['k'], _cat(u)
    if c in ('TRI', 'FLY', 'DELT', 'ARM', 'PULL') and k != 'farewell':
        return c
    if c == 'LOW' and k in LIGHT_LOW:
        return 'LOWL'
    if k in PRESS_ACC:
        return 'PACC'
    return None


# суперсеты: первый — второй (по порядку предпочтения). Руки в паре всегда вторые и только после всех жимов.
PAIR_RULES = [
    ('TRI', ('ARM',)),                       # трицепс + бицепс / предплечья
    ('PULL', ('PACC', 'FLY', 'DELT', 'TRI')),  # тяга + жим гантелей / разводка / махи / трицепс
    ('LOWL', ('DELT', 'FLY', 'TRI')),          # лёгкие ноги + изоляция верха
    ('FLY', ('ARM',)), ('DELT', ('ARM',)), ('LOWL', ('ARM',)),
]


def _presses(u):
    return any(CAT[e['k']] in ('BM', 'P2') for e in u)


def _pair_all(us):
    us = [list(u) for u in us]
    for a_kind, b_kinds in PAIR_RULES:
        j = 0
        while j < len(us):
            u = us[j]
            if _kind(u) == a_kind:
                last_press = max([i for i, v in enumerate(us) if _presses(v)], default=-1)
                partner = None
                for bk in b_kinds:
                    if bk == 'ARM' and j < last_press:
                        continue  # руки не встают перед жимами
                    cands = [v for v in us if v is not u and _kind(v) == bk]
                    if bk == 'ARM':
                        cands = [v for v in cands if us.index(v) > j] or cands
                    if cands:
                        partner = cands[0]
                        break
                if partner:
                    pi = us.index(partner)
                    us[j] = u + [dict(partner[0], ss=1)]
                    us.pop(pi)
                    if pi < j:
                        j -= 1
            j += 1
    return us


def _arms_last(us):
    """Руки — в самом конце, после всех жимов и тяг (кроме пар, которые ставит сам гайд, например жим + обратный хват)."""
    is_arm = lambda u: any(CAT[e['k']] == 'ARM' for e in u) and not any(CAT[e['k']] in ('BM', 'P2') for e in u)
    is_end = lambda u: _cat(u) == 'NOTE' or u[0]['k'] == 'farewell'
    body = [u for u in us if not is_end(u)]
    return [u for u in body if not is_arm(u)] + [u for u in body if is_arm(u)] + [u for u in us if is_end(u)]


def _flat(us):
    return [e for u in us for e in u]


def merge_week(wk, test):
    d = wk['d']
    if test:  # проходка в А, разгрузка в Б
        A = [u for u in _units(d['d1'], 'd1') if _cat(u) != 'CORE']
        B = [u for u in _units(DELOAD['d3'], 'd3') + _units(DELOAD['d2'], 'd2') if _cat(u) != 'CORE' and u[0]['k'] not in HOME]
        return A, B
    h1, t1, n1 = _split(_units(d['d1'], 'd1'))
    h3, t3, n3 = _split(_units(d['d3'], 'd3'))
    u2 = _units(d['d2'], 'd2')
    pulls = [u for u in u2 if _cat(u) == 'PULL' and u[0]['k'] != 'farewell']
    fare = [u for u in u2 if u[0]['k'] == 'farewell']
    press = [_cap(u) for u in u2 if _cat(u) in ('P2', 'BM')][:1]
    low = [u for u in u2 if _cat(u) == 'LOW' and u[0]['k'] not in HOME][:1]
    have, iso2 = {_cat(u) for u in h3 + t3}, []
    for u in u2:
        c = _cat(u)
        if c in ('TRI', 'ARM'):
            iso2.append(u)
        elif c in ('FLY', 'DELT') and c not in have:
            iso2.append(u)
            have.add(c)
    A = [h1 + pulls, t1, fare + n1]
    B = [h3 + press + low, t3 + iso2, n3]
    def tt(parts):
        return est_minutes(_pair_all(_flat_s(parts)))

    movable = [(u, 0) for u in pulls] + [(u, 1) for u in low]  # тяги могут переехать в Б, ноги — в А
    for _ in range(2):  # до двух переездов, если это заметно выравнивает тренировки
        cur = max(tt(A), tt(B))
        best = None
        for u, side in movable:
            src, dst = (A, B) if side == 0 else (B, A)
            if not any(u is x for x in src[0]):
                continue
            s2 = [[x for x in src[0] if x is not u], src[1], src[2]]
            d2_ = [dst[0] + [u], dst[1], dst[2]]
            nA, nB = (s2, d2_) if side == 0 else (d2_, s2)
            m = max(tt(nA), tt(nB))
            if m < cur - 3 and (best is None or m < best[0]):
                best = (m, nA, nB)
        if not best:
            break
        A, B = best[1], best[2]
    out = []
    for head, tail, end in (A, B):
        us = _arms_last(_pair_all(head + tail + end))
        if est_minutes(us) > LONG:  # самый длинный день: третий жим из Дня 2 и вторая разводка — по желанию
            fly_seen = False
            for u in us:
                if len(u) == 1 and any(u[0] is p[0] or u[0] == p[0] for p in press):
                    u[0] = dict(u[0], opt=1)
                elif len(u) == 1 and _cat(u) == 'FLY':
                    if fly_seen:
                        u[0] = dict(u[0], opt=1)
                    fly_seen = True
        out.append(us)
    return out[0], out[1]


def _flat_s(parts):
    return [u for part in parts for u in part]


def program():
    raw = parse_program()
    out = {}
    for gi, g in enumerate(GUIDES):
        weeks = []
        for w, wk in enumerate(raw[g['id']], 1):
            test = w == g['weeks']
            A, B = merge_week(wk, test)
            days = {}
            for dk, us in (('a', A), ('b', B)):
                items = [map_item(e) for e in _flat(us)]
                for it in items:
                    if test and dk == 'b':
                        it['dl'] = 1
                    if 'wide' in it:
                        it['wide']['cap'] = 60 if gi == 1 else 70
                full = int(5 * round(est_minutes(us) / 5))
                core = int(5 * round(est_minutes([u for u in us if not (u[0].get('opt') or MAP[u[0]['k']][2].get('opt'))]) / 5))
                days[dk] = {'items': items, 'deload': test and dk == 'b', 'test': any(it['role'] == 'test' for it in items), 'mins': full}
                if core < full:
                    days[dk]['minsCore'] = core
            weeks.append(days)
        out[g['id']] = weeks
    return out


# ------------------------------------------------------------------ кардио для сердца и протоколы
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
    return {'title': title, 'mins': mins, 'eq': mins, 'kind': 'z2', 'segs': segs,
            'lines': ['Велосипед, эллипс или ходьба в горку (уклон 6–10%, без поручней). Не бег и не гребной тренажёр — они бьют по дискам.',
                      'Пульс {Z2} — зона 2 по твоему пульсу покоя из профиля: дышишь носом и можешь говорить фразами. Пульс уходит выше — сбавь темп, а не терпи.']}


def int_session():
    segs = [seg('Разминка — зона 2', 600, 'warm', 'пульс {Z2}, последние 2 минуты чуть быстрее')]
    for i in range(4):
        segs.append(seg(f'Отрезок {i + 1}/4 — тяжело', 240, 'work', 'к концу 2-й минуты пульс {Z5} — и держишь до конца отрезка'))
        if i < 3:
            segs.append(seg('Отдых — легко крутишь', 180, 'easy', 'пульс {Z1}'))
    segs.append(seg('Заминка', 360, 'easy', 'пульс {Z1}'))
    return {'title': 'Интервалы 4 × 4 мин', 'mins': 40, 'eq': 56, 'kind': 'int', 'segs': segs,
            'lines': ['Норвежский протокол: 4 отрезка по 4 минуты на 85–95% от максимального пульса, между ними 3 минуты легко.',
                      'Велосипед или крутая горка, не бег. Темп ровный: последний отрезок не слабее первого. Пульс догоняет нагрузку за 1–2 минуты — это нормально.',
                      'Плохо спал, ноет спина или нет сил — выбери жёлтый в светофоре: вместо интервалов будут 50 минут зоны 2.',
                      'Боль или давление в груди, необычная одышка, перебои, головокружение — стоп и к врачу.']}


def walk_session(mins, title):
    return {'title': title, 'mins': mins, 'eq': mins, 'kind': 'walk',
            'segs': [seg('Прогулка — быстрый шаг', mins * 60, 'easy', 'пульс {Z1}')],
            'lines': ['На улице, быстрым шагом, руки свободно работают. Пульс {Z1}: дышишь носом, говорить легко.',
                      'Ходьба — лучшая нагрузка для поясницы: диски «питаются» от движения, мышцы спины работают без сжатия.']}


def easy_bike(mins, title, lines, opt=False):
    d = {'title': title, 'mins': mins, 'eq': mins, 'kind': 'z1', 'segs': [seg('Велосипед — легко', mins * 60, 'easy', 'пульс {Z1}')], 'lines': lines}
    if opt:
        d['opt'] = 1
    return d


def cardio_main(gi, w, weeks):
    if w == weeks:
        return z2_session(40), 'Вчера была проходка — сегодня только спокойная зона 2.'
    if gi == 0:
        return z2_session([45, 45, 50, 50, 55, 55, 60, 60][w - 1]), \
            'Гайд 100 — строим аэробную базу: только зона 2, каждые два цикла на 5 минут дольше. Интервалы начнутся в гайде 150.'
    last_int = 10 if gi == 1 else 12
    if w > last_int:
        m = 45 if gi == 1 else (40 if w == 13 else 30)
        return z2_session(m), 'Перед проходкой интервалы убраны — силы идут в жим.'
    return int_session(), 'Раз в цикл — интервалы 4 × 4: они сильнее всего поднимают МПК, а он лучше всего показывает, насколько здорово сердце.'


HEART = [
    '<b>Объём спокойной аэробики</b> — зона 2, прогулка, заминки после зала. Она снижает давление и пульс покоя, тренирует сосуды и обмен веществ, помогает худеть и не мешает восстановлению.',
    '<b>Одна тяжёлая интервальная за цикл</b> — с гайда 150. Норвежские 4 × 4 сильнее всего поднимают МПК (VO2max), а он лучше всего показывает, насколько здорово сердце.',
    '<b>Сколько.</b> Минута интервалов идёт за две минуты спокойной работы. Без крутилки за цикл выходит около 2 часов кардио — 105–115 минут в неделю. С лёгкой крутилкой после первых смен — 135–150 минут в неделю, почти норма ВОЗ: 150 минут умеренной нагрузки в неделю.',
    '<b>Смена кардио не заменяет:</b> 12 часов работы держат пульс высоким без отдыха, а сердце крепнет от тренировки с восстановлением после неё.',
    '<b>Как понять, что работает:</b> за 2–3 месяца пульс покоя по утрам снижается на 3–8 ударов, а тот же темп на велосипеде даётся при меньшем пульсе. Записывай пульс покоя в профиль раз в цикл.',
]
REST_WHY = ('Сегодня без зала: между силовыми три дня, и перед сменами спине нужен свежий день. '
            'Прогулка разгоняет кровь и «кормит» диски, мостик и тройка Макгилла держат ягодицы и корпус в тонусе.')

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


def recovery_steps():
    s = spine_steps()
    return s[:3] + [{'ex': 'bridge', 't': '<b>Ягодичный мост с резинкой над коленями</b> — 2 × 15, наверху пауза 2 с. Стало легко — на одной ноге, 2 × 10 на каждую'}] + s[3:]


READY_GYM = [
    '<b>Пульс покоя</b> (лёжа, сразу после пробуждения): норма — ±5 от обычного; жёлтый — +6–9; красный — +10 и больше или простуда.',
    '<b>Сон:</b> норма — 7 ч и больше; жёлтый — 5,5–7 ч; красный — меньше 5,5 ч.',
    '<b>Боль в пояснице или шее (0–10):</b> норма — 0–2; жёлтый — 3–4 или скованность дольше 30 мин; красный — 5 и выше.',
    '<b>Смена накануне:</b> тяжёлая (переработка, больше 15 тыс. шагов, усталость 8 из 10) — жёлтый.',
    '<b>Первый разминочный подход жима</b> (55–60% на 5) идёт заметно тяжелее обычного — жёлтый.',
    '<b>Решение.</b> Всё в норме — по плану. Жёлтый — в зале веса −10% и без подходов от 90%, в день кардио вместо интервалов — зона 2. '
    'Красный — вместо зала и интервалов восстановление: 30 мин прогулки, тройка Макгилла и растяжка.',
    '<b>Онемение, слабость или боль в ноге или руке — не жёлтый, а стоп</b>: тренировку отменить, план действий — в «Красных флагах» профиля.',
]
FOOD_SHIFT = ('<b>Рабочий день — около 2100 ккал:</b> белок 165 г, жиры 75 г, углеводы ≈ 190 г, клетчатка 30–40 г, вода 2,5–3 л. '
              'Завтрак около 06:00 (35–40 г белка, самый углеводный приём), обед в 11–12 (40 г белка), перекус в 15–16 (25–30 г), '
              'ужин в 19:50–20:20 (40 г белка, мало жира) — не позже чем за 1,5 ч до сна. Кофеин — до 14:00.')
FOOD_GYM = ('<b>День силовой — около 2350 ккал:</b> белок 165 г, жиры 70 г, углеводы ≈ 265 г; 4 приёма по ≈ 40 г белка; основные углеводы — до и после зала. '
            'Это самый сытный день цикла — не урезай его: недобор калорий в день силовой бьёт по восстановлению. '
            'Вода 2,5–3 л и ещё 0,5 л на час тренировки. Креатин моногидрат 3–5 г в день — по желанию. Кофеин — до 14:00.')
FOOD_REST = ('<b>Выходной без зала — около 2200 ккал:</b> белок 165 г, углеводы меньше, чем в день зала. Прогулка и кардио — лучший добор против висцерального жира.')
FOOD_RULE = 'Раз в 2 недели сверяй средний вес: худеешь медленнее 0,3 кг в неделю — минус 150 ккал (углеводы и жиры); быстрее 0,8 кг — плюс 150 ккал.'
SLEEP_SHIFT = 'Сон 22:00 – 05:30: экран убрать за 45 минут, в спальне темно и прохладно. Интенсивной нагрузки вечером нет.'
SLEEP_OFF = 'Сон 7,5–9 часов, подъём в одно время ±1 час. Зал — через 1,5–3 часа после еды; первые 1–2 часа после сна без тяжёлых наклонов: диски ещё «набухшие».'


def gym_title(dk, d):
    if d['test']:
        return 'Проходка: разовый максимум в жиме'
    if d['deload']:
        return 'Разгрузка после проходки'
    exs = {it['ex'] for it in d['items']}
    t = 'Скоростной жим' if 'bench_speed' in exs else 'Жим лёжа'
    parts = []
    if exs & {'split_db', 'leg_ext', 'goblet_box', 'box_squat', 'leg_curl'}:
        parts.append('ноги')
    if exs & {'hipthrust', 'fitball_curl', 'bridge_sl', 'bridge'}:
        parts.append('ягодицы')
    if exs & {'tbar_cs', 'latpd', 'seatrow', 'pullup_cg', 'pullup_wg', 'cs_db_row', 'pullup_neg'}:
        parts.append('спина')
    if not parts:
        return t
    return t + (', ' + ', '.join(parts[:-1]) + ' и ' + parts[-1] if len(parts) > 1 else ' и ' + parts[0])


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

    cool = ref(easy_bike(10, 'После зала: заминка 10 мин', ['Велосипед или ходьба, пульс {Z1}: разгоняет кровь после тяжёлых подходов.']))
    walk = ref(walk_session(50, 'Прогулка 50 минут'))
    spin = ref(easy_bike(20, 'По желанию: лёгкая крутилка 20 мин', [
        'Велотренажёр дома, пульс {Z1} — так легко, что можно говорить без пауз.',
        'Только если есть силы. Устал после смены — пропусти: восстановление важнее.',
        'Закончи не позже чем за 1,5 часа до сна.'], opt=True))
    alt_y = ref(z2_session(50, 'Жёлтый день: зона 2 вместо интервалов'))
    alt_r = ref(walk_session(30, 'Красный день: прогулка 30 минут'))
    for gi, g in enumerate(GUIDES):
        for w in range(1, g['weeks'] + 1):
            c = gstart + w
            main, why = cardio_main(gi, w, g['weeks'])
            for i, sl in enumerate(SLOTS):
                d = {'d': (c - 1) * 8 + i + 1, 'c': c, 'i': i, 'g': gi, 'w': w, 'kind': sl['kind']}
                if sl['kind'] == 'gym':
                    gd = prog[g['id']][w - 1][sl['gd']]
                    d.update(gd=sl['gd'], test=gd['test'], deload=gd['deload'], title=gym_title(sl['gd'], gd), mins=gd['mins'],
                             after=cool, food='gym')
                    if 'minsCore' in gd:
                        d['minsCore'] = gd['minsCore']
                elif sl['kind'] == 'cardio':
                    d.update(title='Сердце: ' + ('интервалы 4 × 4' if main['kind'] == 'int' else 'зона 2'), cardio=ref(main), why=why,
                             red=alt_r, food='rest')
                    if main['kind'] == 'int':
                        d['alt'] = alt_y
                elif sl['kind'] == 'rest':
                    d.update(title='Восстановление: прогулка и спина', cardio=walk, food='rest')
                else:
                    first = i in (2, 6)
                    d.update(title='Смена: восстановление', food='shift', eve=1 if first else 2)
                    if first:
                        d['opt'] = spin
                days.append(d)
        gstart += g['weeks']
    assert len(days) == NCYC * 8
    used = {it['ex'] for g in prog.values() for wk in g for dd in wk.values() for it in dd['items']}
    used |= {it['wide']['ex'] for g in prog.values() for wk in g for dd in wk.values() for it in dd['items'] if 'wide' in it}
    used |= {'curlup', 'splank', 'birddog', 'breath9090', 'hipflex', 'couch', 'lying9090', 'leg_ext', 'bridge'}
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
            'evening': evening_steps(), 'spine': spine_steps(), 'recovery': recovery_steps(), 'mcgill': MCGILL, 'ready': READY_GYM, 'zones': zones,
            'heart': HEART, 'restWhy': REST_WHY, 'layout': 2}


def main(out):
    data = build()
    s = json.dumps(data, ensure_ascii=False, separators=(',', ':'))
    open(out, 'w', encoding='utf-8').write(s)
    n_items = sum(len(dd['items']) for g in data['prog'].values() for wk in g for dd in wk.values())
    print('days', len(data['days']), 'items', n_items, 'ex', len(data['ex']), 'bytes', len(s.encode('utf-8')))


if __name__ == '__main__':
    main(sys.argv[1])
