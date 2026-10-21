# -*- coding: utf-8 -*-
"""Данные приложения «Брюс Ли 5.0»: 140 дней программы «Позвоночник прежде всего» из plan.py
и справочник упражнений из exercises.py. Запуск: python3 tools/appdata.py out.json"""
import importlib.util, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))


def _load(name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(HERE, name + '.py'))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


P = _load('plan')
X = _load('exercises')
EX = X.EX
P.EXWT.update({k: v['wt'] for k, v in EX.items()})


def fmt_rest(s):
    if s >= 60 and s % 60 == 0:
        return f'{s // 60} мин'
    if s > 60 and s % 30 == 0:
        return ('%g' % (s / 60)).replace('.', ',') + ' мин'
    return f'{s} с'


def rpe_of(rir):
    if not rir:
        return None
    return round(10 - (rir[0] + rir[1]) / 2, 1)


def conv_ex(it):
    e = EX[it['id']]
    wt = e['wt']
    rpe = rpe_of(it.get('rir'))
    rows = []
    unit = it['unit']
    if it.get('cluster'):
        for i in range(it['n']):
            r = {'kind': 'work', 'lo': it['lo'], 'hi': it['hi'], 'cl': it['cluster'], 'lbl': f'Кл. {i + 1}/{it["n"]}'}
            if rpe:
                r['rpe'] = rpe
            rows.append(r)
    elif unit == 'sec':
        if it.get('rows'):
            for k, rr in it['rows']:
                rows.append({'kind': 'work', 'lo': it['hi'], 'hi': it['hi'], 'n': k, 'rr': rr, 'lbl': f'{k} × {it["hi"]} с'})
        elif it.get('hold'):
            k, rr = it['hold']
            for i in range(it['n']):
                rows.append({'kind': 'work', 'lo': it['hi'], 'hi': it['hi'], 'n': k, 'rr': rr})
        else:
            for i in range(it['n']):
                rows.append({'kind': 'work', 'lo': it['hi'], 'hi': it['hi']})
    elif it.get('rows'):
        for x in it['rows']:
            r = {'kind': 'work', 'lo': it['lo'], 'hi': it['hi']}
            if x == 'half':
                r.update(lbl='½ ампл.', half=True, rpe=9)
            elif rpe:
                r['rpe'] = rpe
            rows.append(r)
    else:
        for i in range(it['n']):
            r = {'kind': 'work', 'lo': it['lo'], 'hi': it['hi']}
            if rpe:
                r['rpe'] = rpe
            rows.append(r)
    sp = {'wt': wt, 'unit': unit, 'rows': rows, 'rest': it['rest']}
    if it.get('per'):
        sp['per'] = it['per']
    if it.get('lr'):
        sp['lr'] = True
    if it.get('slow'):
        sp['slow'] = True
    if it.get('grp') and it['lab'].endswith('a'):
        sp['alt'] = True
    if it['id'] in ('suitcase', 'bottoms_up'):
        pg = 'ходьба'
    elif unit == 'sec':
        pg = f'удержания по {it["hi"]} с' if (it.get('hold') or it.get('rows')) else f'{it["hi"]} с'
    else:
        pg = ('темп ' + it['tempo']) if it.get('tempo') else ''
    rest_txt = fmt_rest(it['rest']) if it['rest'] else ''
    if it.get('grp') and it['rest']:
        rest_txt += ' — и сразу второе упражнение пары'
    out = {'ex': it['id'], 'sets': P.sets_text(it), 'load': it.get('load') or '', 'rest': rest_txt, 'note': it.get('note') or '', 'spec': sp, 'lab': it['lab']}
    if pg:
        out['pg'] = pg
    return out


def conv_items(items):
    P.label_items(items)
    out = []
    for it in items:
        if it['t'] == 'hdr':
            out.append({'hdr': it['text']})
        elif it['t'] == 'cond':
            c = {'title': it['title'], 'mins': max(1, int(round(sum(x['s'] for x in it['segs']) / 60))), 'lines': it['lines'], 'segs': it['segs']}
            if it.get('kind'):
                c['kind'] = it['kind']
            out.append({'cond': c})
        else:
            out.append(conv_ex(it))
    return out


def mins_txt(sec, gym):
    m = sec / 60
    return f'≈ {int(5 * round(m / 5))} мин' if gym else f'≈ {int(round(m))} мин'


SLEEP_SHIFT = ('Сон 22:00 – 05:45: экран убрать за 45 минут, в спальне темно и прохладно. Интенсивной нагрузки после 19:30 нет — '
               'домашние протоколы закончи к 20:15–20:45.')
SLEEP_GYM = 'Сон до 10 часов, подъём в одно время ±1 час. Зал — в первой половине дня, через 1,5–3 часа после еды.'
EVENING_WALK = 'Вечером — по желанию прогулка 30–40 мин в зоне 1–2: лучший добор против висцерального жира.'


def ready_sec(mode):
    if mode == 'home':
        return {'t': 'ready', 'mode': 'home', 'title': 'Вечер после смены — 30 секунд', 'lines': P.READY_HOME,
                'y': 'Жёлтый вечер: только дыхание 90/90, curl-up, боковая планка, bird dog и «лёжа 90/90» (≈ 12 мин); во второй рабочий день — 10–12 мин зоны 1 и разгрузка спины.',
                'r': 'Красный вечер: только дыхание 90/90 и «лёжа 90/90», 10 минут. Онемение, слабость или боль в ноге или руке — к врачу.'}
    return {'t': 'ready', 'mode': 'gym', 'title': 'Утро — светофор, 3 минуты', 'lines': P.READY_GYM,
            'y': 'Жёлтый день: приложение снизило рабочие веса на 15%. Интервалы замени 20 минутами зоны 2; в волне Т — запас на 1 больше и минус 1 подход.',
            'r': 'Красный день: вместо зала — восстановление: 30 мин зоны 1–2 (прогулка или велотренажёр), протокол домашнего Дня 1 и растяжка. Онемение, слабость или боль в ноге — тренировку отменить и к врачу.'}


def warm_sec(steps, title):
    return {'t': 'steps', 'title': title, 'id': 'warm', 'warm': True, 'steps': steps, 'foot': 'Разминка — половина защиты спины: пресс и ягодицы включаются до первого тяжёлого подхода.'}


def test_day(c):
    t = P.info(c)
    TM = {x[0]: x for x in P.TESTS}

    def tt(i):
        x = TM[i]
        d = {'id': x[0], 'name': x[1], 'how': x[2]}
        if len(x) > 3 and x[3] == 'yn':
            d['yn'] = True
        return d
    light = P.b3_items(t['cx'], t['L'], 'Р', c) + P.c3_items(t['cx'], t['L'], 'Р')
    items = [{'t': 'hdr', 'text': 'Лёгкая работа после тестов — разгрузка'}] + light + [{'t': 'hdr', 'text': 'Заминка'}, P.cool3()]
    secs = [
        {'t': 'tests', 'title': 'Утренние замеры', 'tests': [tt('weight'), tt('waist'), tt('rhr'), tt('bp')],
         'foot': 'Вес и пульс — средние за 7 утр; давление — 3-й день замеров. Результаты сравниваются с Циклом 0 во вкладке «Прогресс».'},
        warm_sec(P.warm3('Р')[:3], 'Разминка — 6 мин'),
        {'t': 'tests', 'title': 'Тесты в зале — по порядку', 'id': 'sec-ex',
         'tests': [tt('z2w'), tt('rowt'), tt('presst'), tt('splank'), tt('thomas'), tt('arms'), tt('pain'), tt('leg')],
         'foot': 'Зона 2 — первым тестом, она же разминка. Контрольные подходы — с весом из Цикла 0, до запаса 2, а не до отказа. Любая боль — тест прекращаем.'},
        {'t': 'ex', 'title': 'После тестов', 'items': conv_items(items)},
    ]
    if c == 35:
        secs.append({'t': 'list', 'title': 'Итоги 20 недель и что дальше', 'lines': [
            'Сравни каждую цифру с Циклом 0 и циклом 18 — таблица во вкладке «Прогресс»; сделай фото сбоку в той же позе, что в Цикле 0.',
            'Дальше — повтори блоки 5–6 с новыми рабочими весами или сделай 2 цикла на поддержании калорий и начни новый круг с уровня 2.',
            'Покажи результаты врачу или физиотерапевту: если симптомов не было, обсудите, что из жёлтого списка можно постепенно вернуть.']})
    else:
        secs.append({'t': 'list', 'title': 'Что дальше', 'lines': [
            'Сравни результаты с Циклом 0 во вкладке «Прогресс».',
            'Талия уменьшилась меньше чем на 2 см за 10 недель — проверь средний вес: возможно, пора снизить калории на 150 ккал.',
            'Со следующего цикла — Комплекс №2, уровень 2.']})
    return secs


def build_day(c, k):
    t = P.info(c)
    D = P.dn(c, k)
    cx, L, w, b = t['cx'], t['L'], t['w'], t['b']
    day = {'d': D, 'c': c, 'm': b, 'P': L, 'w': w, 'cx': cx, 'dl': w == 'Р', 'test': t['test'] and k == 3, 'goal': P.cycle_goal(c)}
    if k == 1:
        items = P.home1(cx, L)
        day.update(k='H1', title='Дом: таз, кор и сон', time=mins_txt(P.est_seconds(items), False) + ' после смены')
        day['secs'] = [ready_sec('home'), {'t': 'ex', 'title': 'После смены — протокол', 'id': 'sec-main', 'items': conv_items(items)}]
        day['food'] = [P.FOOD_SHIFT, P.FOOD_RULE, SLEEP_SHIFT]
    elif k == 2:
        items = P.home2(cx, L, c)
        day.update(k='H2', title='Дом: зона 2 и разгрузка спины', time=mins_txt(P.est_seconds(items), False) + ' после смены')
        day['secs'] = [ready_sec('home'), {'t': 'ex', 'title': 'После смены — протокол', 'id': 'sec-main', 'items': conv_items(items)}]
        day['food'] = [P.FOOD_SHIFT, P.FOOD_RULE, SLEEP_SHIFT]
    elif k == 3 and t['test']:
        day.update(k='T', title='Контрольные тесты + лёгкая работа', time='≈ 60 мин')
        day['secs'] = [ready_sec('gym')] + test_day(c)
        day['food'] = [P.FOOD_GYM, P.FOOD_RULE, SLEEP_GYM]
    elif k == 3:
        items = P.day3(c)
        warm = P.warm3(w)
        sec = P.est_seconds(items) + P.warm_seconds(warm)
        title = 'Зал А: жимы, тяги, ягодицы и зона 2' if w != 'Р' else 'Зал А — разгрузка'
        day.update(k='A', title=title, time=mins_txt(sec, True))
        day['pre'] = 'Лучше в первой половине дня. ' + EVENING_WALK
        day['secs'] = [ready_sec('gym'), warm_sec(warm, 'Разминка — 8 мин'), {'t': 'ex', 'title': 'Тренировка', 'id': 'sec-ex', 'items': conv_items(items)}]
        day['food'] = [P.FOOD_GYM, P.FOOD_RULE, SLEEP_GYM]
    else:
        items = P.day4(c)
        warm = P.warm4(cx)
        sec = P.est_seconds(items) + P.warm_seconds(warm)
        title = 'Зал Б: всё тело, интервалы' + (', мешок' if P.bag(b, w, c) else '') if w != 'Р' else 'Зал Б — разгрузка и зона 2'
        day.update(k='B', title=title, time=mins_txt(sec, True))
        day['pre'] = 'Лучше в первой половине дня. ' + EVENING_WALK
        day['secs'] = [ready_sec('gym'), warm_sec(warm, 'Разминка — 7 мин'), {'t': 'ex', 'title': 'Тренировка', 'id': 'sec-ex', 'items': conv_items(items)}]
        day['food'] = [P.FOOD_GYM, P.FOOD_RULE, SLEEP_GYM]
    return day


def blocks():
    out = []
    for b, a, z in P.BLOCKS:
        cyc = list(range(a, z + 1))
        out.append({'m': b, 'P': (b + 1) // 2, 'cx': 1 if b % 2 else 2, 'cycles': cyc, 'days': [P.dn(a, 1), P.dn(z, 4)],
                    'note': P.BLOCK_NOTES[b], 'test': any(c in P.TEST_CYCLES for c in cyc)})
    return out


def main(out):
    days = [build_day(c, k) for c in range(1, P.NC + 1) for k in range(1, 5)]
    used = set()
    secs, index = [], {}
    for d in days:
        ids = []
        for sct in d['secs']:
            if sct['t'] == 'ex':
                for it in sct['items']:
                    if 'ex' in it:
                        used.add(it['ex'])
            key = json.dumps(sct, ensure_ascii=False, sort_keys=True)
            if key not in index:
                index[key] = len(secs)
                secs.append(sct)
            ids.append(index[key])
        d['secs'] = ids
    used |= {'breath9090', 'hipflex', 'couch', 'lying9090', 'croc', 'hip9090', 'latstretch', 'pecstretch', 'hamstring_band', 'pigeon_bench'}
    ex = {k: v for k, v in EX.items() if k in used}
    tests = []
    for x in P.TESTS:
        d = {'id': x[0], 'name': x[1], 'how': x[2]}
        if len(x) > 3 and x[3] == 'yn':
            d['yn'] = True
        tests.append(d)
    zones = [{'id': z[0], 'name': z[1], 'lo': z[2], 'hi': z[3]} for z in P.ZONES]
    data = {'ex': ex, 'groups': X.GROUPS, 'blocks': blocks(), 'days': days, 'secs': secs, 'tests': tests,
            'c0extra': [{'id': t[0], 'name': t[1], 'how': t[2]} for t in P.C0_EXTRA], 'phases': ['Цикл 0', 'Уровень 1', 'Уровень 2', 'Уровень 3'],
            'zones': zones, 'waves': P.WFULL, 'testCycles': list(P.TEST_CYCLES)}
    s = json.dumps(data, ensure_ascii=False, separators=(',', ':'))
    open(out, 'w', encoding='utf-8').write(s)
    print('days', len(days), 'secs', len(secs), 'ex', len(ex), 'bytes', len(s.encode('utf-8')))


if __name__ == '__main__':
    main(sys.argv[1])
