"""
Historia występów, profile zawodników, rankingi, transfery i powiadomienia push.

Wszystko powstaje z danych, które serwer i tak ma (terminarze, składy, bazy zawodników) - ZERO
dodatkowych zapytań do API. Pliki cache serwera z meczami żyją tylko ~2 tygodnie, więc występy
zapisujemy na bieżąco w osobnej, zwartej historii (historia.json), która trafia do godzinnej kopii
zapasowej razem z resztą cache.

  po_cyklu()          - wołane po każdym cyklu harmonogramu: dopisuje do historii zakończone mecze,
                        wykrywa transfery (zmiany klubów w bazach) i wysyła powiadomienia o golach/asystach
  profil(), rankingi(), transfery(), kadra(), ulubieni()  - dane dla aplikacji (serwer.py)
"""
import base64
import hashlib
import json
import os
import re
import threading
import time
from collections import Counter
from datetime import datetime, timedelta

import openpyxl

import pobieranie_danych as dane
from dopasowanie import KODY_KRAJOW_RECZNE, NACJE, wyczysc_nazwe_klubu

KATALOG = os.path.join(dane.KATALOG_DANYCH, "serwer_cache")
HISTORIA_PLIK = os.path.join(KATALOG, "historia.json")
TRANSFERY_PLIK = os.path.join(KATALOG, "transfery.json")
PUSH_PLIK = os.path.join(KATALOG, "push.json")

DNI_HISTORII = 400            # tyle dni wstecz trzymamy występy (sezon + zapas)
DNI_TRANSFEROW = 120
CZEKAJ_NA_SKLADY_H = 36       # mecz bez kompletu składów zapisujemy najpóźniej po tylu godzinach
POWIADAMIAJ_DO_H = 12         # o golu/asyście powiadamiamy tylko świeżo (nie przy odtwarzaniu zaległości)
MAX_ULUBIONYCH = 300
MAX_SUBSKRYPCJI = 20000

_blokada = threading.Lock()
_blokada_push = threading.Lock()

# Występ w historii (lista, żeby plik był mały):
#  [mecz_id, strona 0=gosp/1=gość, minuty, gole, asysty, ocena, pozycja, status, wyjsciowy, kartki]
#  status: 1 grał, 0 nie grał, None nie wiadomo; kartki: "y" żółta, "r" czerwona (np. "yr")
W_MECZ, W_STRONA, W_MIN, W_GOLE, W_ASYSTY, W_OCENA, W_POZ, W_STATUS, W_WYJSC, W_KARTKI = range(10)


def _teraz_pl(): return datetime.now(dane.TZ_PL)


def klucz_gracza(nacja, nazwa):
    """Ten sam zawodnik mimo różnej pisowni znaków (Transfermarkt raz pisze "Michał", raz "Michal")."""
    return f"{nacja}|{dane._klucz_znanego(nazwa)}"


# ---------------------------------------------------------------- HISTORIA WYSTĘPÓW
_hist = {"dane": None}
_bez_naszych = {"wersja": None, "id": set()}   # mecze bez żadnego naszego zawodnika (w pamięci)


def _historia():
    if _hist["dane"] is None:
        h = dane.wczytaj_json(HISTORIA_PLIK) or {}
        h.setdefault("mecze", {}); h.setdefault("wystepy", {}); h.setdefault("nazwy", {})
        _hist["dane"] = h
    return _hist["dane"]


def _zapisz_historie():
    sciezka, h = HISTORIA_PLIK, _historia()
    with open(sciezka + ".tmp", "w", encoding="utf-8") as f: json.dump(h, f, ensure_ascii=False, separators=(",", ":"))
    os.replace(sciezka + ".tmp", sciezka)


def _status(g):
    if g.get('minuty_tekst') == 'brak danych': return None   # API nie dało składu
    return {True: 1, False: 0}.get(g.get('aktywny'))


def _kartki(g):
    return "".join("r" if k in ("redCard", "secondYellow") else "y" for k in g.get('kartki') or [])


def _aktualizuj_historie(raport):
    """Dopisuje zakończone mecze z ostatnich dni okna. Zwraca świeże gole/asysty do powiadomień."""
    from dopasowanie import czas_rozpoczecia_utc
    h = _historia()
    wersja = dane._wersja_baz()
    if _bez_naszych["wersja"] != wersja: _bez_naszych.update(wersja=wersja, id=set())
    pomin = _bez_naszych["id"]
    wspolny = dane.kontekst_dopasowania("pl")
    if not wspolny: return []
    konteksty = {n: dane.kontekst_dopasowania(n, wspolny) for n in NACJE}
    konteksty = {n: k for n, k in konteksty.items() if k}
    teraz = time.time()
    dzis = _teraz_pl().date()
    nowe_mecze, wyczyny = 0, []
    # Harmonogram pobiera po meczu skład każdej drużyny, w której gra ktoś z naszych - więc mecz bez
    # żadnego pobranego składu nie ma (jeszcze) czego zapisać. To odsiewa ~90% meczów bez dopasowywania.
    ze_skladem = {nazwa.split("_", 1)[0] for nazwa in os.listdir(dane.KATALOG_SKLADOW) if nazwa.endswith(".json")}

    for offset in range(-dane.OKNO_DNI - 1, 1):
        for mecz in (dane.surowe_z_cache(dzis + timedelta(days=offset)) or {}).get("mecze", []):
            mid = str(mecz.get("id"))
            if mid in h["mecze"] or mid in pomin or mid not in ze_skladem: continue
            status = mecz.get("status", {})
            if status.get("cancelled"):
                pomin.add(mid); continue
            start = czas_rozpoczecia_utc(mecz)
            if start is None:
                pomin.add(mid); continue
            # Bez statusu "zakończony" (API czasem go nie daje) zapisujemy dopiero po czasie
            if not status.get("finished") and (teraz - start.timestamp()) / 3600 < CZEKAJ_NA_SKLADY_H: continue

            # Najpierw szybkie dopasowanie (pamiętane dla drużyn) - pełne występy tylko dla trafień
            nacje_meczu = {}
            for n, k in konteksty.items():
                m = dane.mecz_nacji(mecz, n, k)
                if m: nacje_meczu[n] = m
            if not nacje_meczu:
                pomin.add(mid); continue

            # Czekamy na ostateczne składy drużyn z naszymi zawodnikami (harmonogram pobiera je po meczu)
            strony = {s for m in nacje_meczu.values() for s, kl in (("home", 'gracze_gosp'), ("away", 'gracze_gosc')) if m[kl]}
            wiek_h = (teraz - start.timestamp()) / 3600
            if not all(dane.sklad_ostateczny(mecz.get("id"), s) for s in strony) and wiek_h < CZEKAJ_NA_SKLADY_H:
                continue

            pierwszy = next(iter(nacje_meczu.values()))
            h["mecze"][mid] = {"d": pierwszy['data'], "g": pierwszy['gosp'], "a": pierwszy['gosc'],
                               "w": pierwszy['wynik'], "l": pierwszy['liga'], "f": pierwszy['flaga']}
            nowe_mecze += 1
            for n, m in nacje_meczu.items():
                for strona, kl in ((0, 'gracze_gosp'), (1, 'gracze_gosc')):
                    for g in m[kl]:
                        kg = klucz_gracza(n, g['nazwa'])
                        h["nazwy"][kg] = g['nazwa']
                        wpis = [mid, strona, g.get('minuty'), g.get('gole', 0), g.get('asysty', 0), g.get('ocena'),
                                g.get('pozycja'), _status(g), 1 if g.get('wyjsciowy') else 0, _kartki(g)]
                        h["wystepy"].setdefault(kg, []).append(wpis)
                        if (g.get('gole') or g.get('asysty')) and wiek_h <= POWIADAMIAJ_DO_H:
                            wyczyny.append({"klucz": kg, "nazwa": g['nazwa'], "nacja": n, "mecz": h["mecze"][mid],
                                            "gole": g.get('gole', 0), "asysty": g.get('asysty', 0), "ocena": g.get('ocena'),
                                            "id": mid})

    usuniete = _przytnij_historie()
    if nowe_mecze or usuniete:
        _zapisz_historie()
        _rankingi_cache.clear()
    if nowe_mecze: raport.append(f"historia: +{nowe_mecze} meczów")
    return wyczyny


def _przytnij_historie():
    h = _historia()
    granica = (_teraz_pl().date() - timedelta(days=DNI_HISTORII)).strftime("%Y%m%d")
    stare = {mid for mid, m in h["mecze"].items() if m["d"] < granica}
    if not stare: return 0
    for mid in stare: del h["mecze"][mid]
    for kg in list(h["wystepy"]):
        h["wystepy"][kg] = [w for w in h["wystepy"][kg] if w[W_MECZ] not in stare]
        if not h["wystepy"][kg]:
            del h["wystepy"][kg]
            h["nazwy"].pop(kg, None)
    return len(stare)


# ---------------------------------------------------------------- KADRY (bazy zawodników)
_kadry = {}   # nacja -> (wersja baz, {klucz_gracza: (nazwa, klub, kraj)})


def _rozbij_klub(klub_raw):
    """"[Anglia] Arsenal FC" -> ("Arsenal FC", "Anglia")."""
    m = re.match(r"^\[([^\]]+)\]\s*(.*)$", klub_raw or "")
    return (m.group(2).strip(), m.group(1).strip()) if m else ((klub_raw or "").strip(), "")


def flaga_kraju(kraj):
    return KODY_KRAJOW_RECZNE.get((kraj or "").strip().lower(), "")


def _kadra(nacja):
    """{klucz_gracza: (nazwa, klub, kraj)} z bazy nacji (główny plik)."""
    wersja = dane._wersja_baz()
    if nacja in _kadry and _kadry[nacja][0] == wersja: return _kadry[nacja][1]
    wynik = {}
    sciezka = dane.plik_bazy(nacja)
    if os.path.exists(sciezka):
        wb = openpyxl.load_workbook(sciezka, read_only=True)
        try:
            wiersze = list(wb.active.iter_rows(values_only=True))
        finally:
            wb.close()
        if wiersze:
            kol = [str(c).strip().lower() if c is not None else "" for c in wiersze[0]]
            for wartosci in wiersze[1:]:
                w = {k: ("" if v is None or str(v).lower() == "nan" else str(v).strip()) for k, v in zip(kol, wartosci)}
                nazwa = f"{w.get('imię', '')} {w.get('nazwisko', '')}".strip()
                if not nazwa or not w.get('klub'): continue
                klub, kraj = _rozbij_klub(w['klub'])
                wynik[klucz_gracza(nacja, nazwa)] = (nazwa, klub, kraj)
    _kadry[nacja] = (wersja, wynik)
    return wynik


def kadra(nacja):
    """Lista zawodników nacji do wyszukiwarki."""
    return sorted(({"nazwa": n, "klub": k, "kraj": kr, "flaga_kraju": flaga_kraju(kr)} for n, k, kr in _kadra(nacja).values()),
                  key=lambda g: dane._klucz_znanego(g["nazwa"]))


# ---------------------------------------------------------------- PROFIL ZAWODNIKA
def _mecz_wystepu(w, h):
    m = h["mecze"].get(w[W_MECZ])
    if not m: return None
    return {"id": w[W_MECZ], "data": m["d"], "gosp": m["g"], "gosc": m["a"], "wynik": m["w"], "liga": m["l"],
            "flaga": m["f"], "strona": "gosp" if w[W_STRONA] == 0 else "gosc", "minuty": w[W_MIN], "gole": w[W_GOLE],
            "asysty": w[W_ASYSTY], "ocena": w[W_OCENA], "status": w[W_STATUS], "wyjsciowy": bool(w[W_WYJSC]),
            "kartki": w[W_KARTKI] or ""}


def _sumy(mecze):
    zagrane = [m for m in mecze if m["status"] == 1]
    oceny = [m["ocena"] for m in zagrane if m["ocena"] is not None]
    return {"mecze": len(zagrane), "minuty": sum(m["minuty"] or 0 for m in zagrane),
            "gole": sum(m["gole"] for m in zagrane), "asysty": sum(m["asysty"] for m in zagrane),
            "w_podstawie": sum(1 for m in zagrane if m["wyjsciowy"]),
            "srednia_ocena": round(sum(oceny) / len(oceny), 2) if oceny else None,
            "zolte": sum(m["kartki"].count("y") for m in zagrane), "czerwone": sum(m["kartki"].count("r") for m in zagrane)}


def _od_dnia(dni):
    return (_teraz_pl().date() - timedelta(days=dni - 1)).strftime("%Y%m%d") if dni else "00000000"


_przyszle = {}   # (nacja, dzień) -> (czas, lista meczów) - najbliższe mecze, pamiętane 10 min


def _najblizsze_mecze(nacja, dni=10):
    """Mecze nacji od dziś na kilka dni do przodu (te, które się jeszcze nie zaczęły)."""
    wynik = []
    dzis = _teraz_pl().date()
    for o in range(dni):
        d = dzis + timedelta(days=o)
        klucz = (nacja, d)
        if klucz not in _przyszle or time.time() - _przyszle[klucz][0] > 600:
            _przyszle[klucz] = (time.time(), dane.mecze_polakow_dnia(d, nacja) or [])
        wynik += [m for m in _przyszle[klucz][1] if not m['rozpoczety'] and not m['odwolany']]
    if len(_przyszle) > 5000: _przyszle.clear()
    return wynik


def _najblizszy_mecz(nacja, kg, przyszle):
    for m in przyszle:
        for strona, kl in (("gosp", 'gracze_gosp'), ("gosc", 'gracze_gosc')):
            if any(klucz_gracza(nacja, g['nazwa']) == kg for g in m[kl]):
                return {"data": m['data'], "godzina": m['godzina'], "gosp": m['gosp'], "gosc": m['gosc'],
                        "liga": m['liga'], "flaga": m['flaga'], "strona": strona}
    return None


def profil(nacja, nazwa, ile_meczow=40):
    h = _historia()
    kg = klucz_gracza(nacja, nazwa)
    mecze = [m for m in (_mecz_wystepu(w, h) for w in h["wystepy"].get(kg, [])) if m]
    mecze.sort(key=lambda m: (m["data"], m["id"]), reverse=True)
    w_kadrze = _kadra(nacja).get(kg)
    klub, kraj = (w_kadrze[1], w_kadrze[2]) if w_kadrze else (None, None)
    pozycje = Counter(w[W_POZ] for w in h["wystepy"].get(kg, []) if w[W_POZ] is not None)
    return {
        "nazwa": h["nazwy"].get(kg) or (w_kadrze[0] if w_kadrze else nazwa), "nacja": nacja,
        "klub": klub, "kraj_klubu": kraj, "flaga_kraju": flaga_kraju(kraj), "w_bazie": bool(w_kadrze),
        "pozycja": pozycje.most_common(1)[0][0] if pozycje else None,
        "forma": [m["ocena"] for m in mecze if m["status"] == 1][:5],
        "sumy": {"7": _sumy([m for m in mecze if m["data"] >= _od_dnia(7)]),
                 "30": _sumy([m for m in mecze if m["data"] >= _od_dnia(30)]),
                 "wszystko": _sumy(mecze)},
        "od": mecze[-1]["data"] if mecze else None,
        "najblizszy": _najblizszy_mecz(nacja, kg, _najblizsze_mecze(nacja)),
        "mecze": mecze[:ile_meczow],
    }


def ulubieni(lista):
    """Skrócone profile ulubionych (lista "nacja|nazwa") - ostatni i najbliższy mecz, forma, 30 dni."""
    h = _historia()
    wynik, przyszle = [], {}
    for wpis in lista[:MAX_ULUBIONYCH]:
        nacja, _, nazwa = wpis.partition("|")
        if nacja not in NACJE or not nazwa: continue
        kg = klucz_gracza(nacja, nazwa)
        mecze = sorted((m for m in (_mecz_wystepu(w, h) for w in h["wystepy"].get(kg, [])) if m),
                       key=lambda m: (m["data"], m["id"]), reverse=True)
        if nacja not in przyszle: przyszle[nacja] = _najblizsze_mecze(nacja, 8)
        w_kadrze = _kadra(nacja).get(kg)
        wynik.append({"nazwa": h["nazwy"].get(kg) or (w_kadrze[0] if w_kadrze else nazwa), "nacja": nacja,
                      "klub": w_kadrze[1] if w_kadrze else None, "ostatni": mecze[0] if mecze else None,
                      "najblizszy": _najblizszy_mecz(nacja, kg, przyszle[nacja]),
                      "forma": [m["ocena"] for m in mecze if m["status"] == 1][:5],
                      "sumy30": _sumy([m for m in mecze if m["data"] >= _od_dnia(30)])})
    return wynik


# ---------------------------------------------------------------- RANKINGI I LEGION TYGODNIA
_rankingi_cache = {}
FORMACJA = {0: 1, 1: 4, 2: 3, 3: 3}   # 4-3-3


def _zbior(nacja, dni):
    """{klucz_gracza: [mecze z okresu]} dla nacji."""
    h, od = _historia(), _od_dnia(dni)
    wynik = {}
    prefiks = f"{nacja}|"
    for kg, wystepy in h["wystepy"].items():
        if not kg.startswith(prefiks): continue
        mecze = [m for m in (_mecz_wystepu(w, h) for w in wystepy) if m and m["data"] >= od]
        if mecze: wynik[kg] = mecze
    return wynik


def _legion(nacja, zbior):
    """Najlepsza jedenastka okresu (4-3-3) wg najlepszej oceny zawodnika w jednym meczu."""
    h = _historia()
    kandydaci = []
    for kg, mecze in zbior.items():
        oceniane = [m for m in mecze if m["status"] == 1 and m["ocena"] is not None]
        if not oceniane: continue
        najlepszy = max(oceniane, key=lambda m: (m["ocena"], m["gole"] + m["asysty"]))
        poz = Counter(w[W_POZ] for w in h["wystepy"][kg] if w[W_POZ] is not None).most_common(1)
        kandydaci.append({"nazwa": h["nazwy"].get(kg, kg), "pozycja": poz[0][0] if poz else None, "mecz": najlepszy})
    kandydaci.sort(key=lambda k: -k["mecz"]["ocena"])
    linie, wybrani = {p: [] for p in FORMACJA}, set()
    for k in kandydaci:
        if k["pozycja"] in FORMACJA and len(linie[k["pozycja"]]) < FORMACJA[k["pozycja"]]:
            linie[k["pozycja"]].append(k); wybrani.add(k["nazwa"])
    # Za mało np. bramkarzy - wolne miejsca dostają najlepsi pozostali (na swoich pozycjach)
    wolne = sum(FORMACJA.values()) - len(wybrani)
    for k in kandydaci:
        if wolne <= 0: break
        if k["nazwa"] in wybrani: continue
        p = k["pozycja"] if k["pozycja"] in FORMACJA else 2
        if p == 0 and linie[0]: p = 1   # drugi bramkarz nie stanie w bramce
        linie[p].append(k); wybrani.add(k["nazwa"]); wolne -= 1
    return [{"pozycja": p, "gracze": linie[p]} for p in (3, 2, 1, 0) if linie[p]]


def _top(zbior, h, klucz, ile=10, filtr=None):
    wiersze = []
    for kg, mecze in zbior.items():
        s = _sumy(mecze)
        if filtr and not filtr(s): continue
        wiersze.append(dict(s, nazwa=h["nazwy"].get(kg, kg)))
    return sorted(wiersze, key=klucz)[:ile]


def rankingi(nacja, dni):
    klucz = (nacja, dni, len(_historia()["mecze"]), _teraz_pl().date())
    if klucz in _rankingi_cache: return _rankingi_cache[klucz]
    h, zbior = _historia(), _zbior(nacja, dni)
    min_meczow = 1 if dni and dni <= 7 else 3 if dni and dni <= 31 else 5
    wynik = {
        "dni": dni,
        "legion": _legion(nacja, zbior),
        "strzelcy": _top(zbior, h, lambda s: (-s["gole"], -s["asysty"], s["minuty"]), filtr=lambda s: s["gole"] > 0),
        "asystenci": _top(zbior, h, lambda s: (-s["asysty"], -s["gole"], s["minuty"]), filtr=lambda s: s["asysty"] > 0),
        "kanadyjska": _top(zbior, h, lambda s: (-(s["gole"] + s["asysty"]), -s["gole"], s["minuty"]),
                           filtr=lambda s: s["gole"] + s["asysty"] > 0),
        "minuty": _top(zbior, h, lambda s: (-s["minuty"], -s["mecze"]), filtr=lambda s: s["minuty"] > 0),
        "oceny": _top(zbior, h, lambda s: -s["srednia_ocena"],
                      filtr=lambda s: s["srednia_ocena"] is not None and s["mecze"] >= min_meczow),
        "min_meczow_oceny": min_meczow,
        "nacje": _ranking_nacji(dni, nacja),
        "podsumowanie": _sumy([m for mecze in zbior.values() for m in mecze]) | {"zawodnikow": sum(1 for mecze in zbior.values() if any(m["status"] == 1 for m in mecze))},
    }
    if len(_rankingi_cache) > 2000: _rankingi_cache.clear()
    _rankingi_cache[klucz] = wynik
    return wynik


def _ranking_nacji(dni, nacja):
    """Ile zawodników każdej nacji zagrało w okresie i ile strzelili - top 10 + miejsce wybranej nacji."""
    h, od = _historia(), _od_dnia(dni)
    grali, gole = Counter(), Counter()
    for kg, wystepy in h["wystepy"].items():
        n = kg.split("|", 1)[0]
        zagrane = [w for w in wystepy if w[W_STATUS] == 1 and h["mecze"].get(w[W_MECZ], {}).get("d", "") >= od]
        if zagrane:
            grali[n] += 1
            gole[n] += sum(w[W_GOLE] for w in zagrane)
    lista = [{"nacja": n, "grali": c, "gole": gole[n]} for n, c in grali.most_common()]
    for i, w in enumerate(lista, 1): w["miejsce"] = i
    top = lista[:10]
    moja = next((w for w in lista if w["nacja"] == nacja), None)
    return {"top": top, "wybrana": moja if moja and moja not in top else None, "nacji": len(lista)}


# ---------------------------------------------------------------- TRANSFERY (zmiany klubów w bazach)
_transfery = {"dane": None, "wersja": None}


def _dane_transferow():
    if _transfery["dane"] is None:
        t = dane.wczytaj_json(TRANSFERY_PLIK) or {}
        t.setdefault("widziani", {}); t.setdefault("zdarzenia", [])
        _transfery["dane"] = t
    return _transfery["dane"]


def _ten_sam_klub(a, b):
    from pobieranie_danych import DAWNE_NAZWY_KLUBOW
    ka, kb = wyczysc_nazwe_klubu(a), wyczysc_nazwe_klubu(b)
    if ka == kb or ka.replace("-", " ") == kb.replace("-", " "): return True
    return ka in DAWNE_NAZWY_KLUBOW.get(kb, []) or kb in DAWNE_NAZWY_KLUBOW.get(ka, [])


def _aktualizuj_transfery(raport):
    """Porównuje bazy zawodników z tym, co serwer widział wcześniej. Zawodnik, który zniknął (np. Transfermarkt
    nie pokazał kraju przy skanie), zostaje zapamiętany - gdy wróci w tym samym klubie, to nie transfer."""
    wersja = dane._wersja_baz()
    if _transfery["wersja"] == wersja: return
    t = _dane_transferow()
    teraz = time.time()
    nowe = []
    for nacja in NACJE:
        kadra_n = _kadra(nacja)
        widziani = t["widziani"].get(nacja)
        if widziani is None:   # pierwszy raz (albo nowa nacja) - tylko zapamiętujemy, bez zdarzeń
            t["widziani"][nacja] = {kg: [n, k, kr, teraz] for kg, (n, k, kr) in kadra_n.items()}
            continue
        zdarzenia = []
        for kg, (n, klub, kraj) in kadra_n.items():
            stary = widziani.get(kg)
            if stary is None:
                zdarzenia.append({"typ": "nowy", "nazwa": n, "do": klub, "kraj_do": kraj})
            elif not _ten_sam_klub(stary[1], klub):
                zdarzenia.append({"typ": "transfer", "nazwa": n, "z": stary[1], "kraj_z": stary[2], "do": klub, "kraj_do": kraj})
            widziani[kg] = [n, klub, kraj, teraz]
        # Masowa "zmiana" (np. inne nazewnictwo klubów w nowym skanie) to nie transfery
        if len(zdarzenia) > max(15, len(kadra_n) * 0.4):
            raport.append(f"transfery {nacja}: pominięto {len(zdarzenia)} zmian (podejrzanie dużo)")
            continue
        for z in zdarzenia:
            z.update(nacja=nacja, t=teraz, flaga_z=flaga_kraju(z.get("kraj_z")), flaga_do=flaga_kraju(z.get("kraj_do")))
        nowe += zdarzenia
    granica = teraz - DNI_TRANSFEROW * 86400
    t["zdarzenia"] = [z for z in t["zdarzenia"] if z["t"] >= granica] + nowe
    dane.zapisz_json_atomowo(TRANSFERY_PLIK, t)
    _transfery["wersja"] = wersja
    if nowe: raport.append(f"transfery: {len(nowe)} nowych zdarzeń")


def transfery(nacja):
    zd = [z for z in _dane_transferow()["zdarzenia"] if z["nacja"] == nacja]
    zd.sort(key=lambda z: -z["t"])
    return [dict(z, data=datetime.fromtimestamp(z["t"], dane.TZ_PL).strftime("%Y%m%d")) for z in zd[:300]]


# ---------------------------------------------------------------- POWIADOMIENIA PUSH (ciche)
VAPID_PRYWATNY = os.environ.get("NF_VAPID_PRIVATE", "").strip()
VAPID_PUBLICZNY = os.environ.get("NF_VAPID_PUBLIC", "").strip()
# "sub" w tokenie VAPID - kontakt do nadawcy dla usług push (Google/Apple/Mozilla): adres serwisu
VAPID_KONTAKT = os.environ.get("NF_VAPID_KONTAKT", "") or os.environ.get("RENDER_EXTERNAL_URL", "") or "https://nationfootball.onrender.com"
_push = {"dane": None}


def push_wlaczony():
    if not (VAPID_PRYWATNY and VAPID_PUBLICZNY): return False
    try:
        import pywebpush  # noqa: F401
        return True
    except ImportError:
        return False


def _subskrypcje():
    if _push["dane"] is None: _push["dane"] = dane.wczytaj_json(PUSH_PLIK) or {}
    return _push["dane"]


def _zapisz_subskrypcje():
    dane.zapisz_json_atomowo(PUSH_PLIK, _subskrypcje())


def zapisz_subskrypcje(sub, lista_ulubionych, jezyk="pl"):
    if not isinstance(sub, dict): raise ValueError("brak subskrypcji")
    endpoint = str(sub.get("endpoint", ""))
    klucze = sub.get("keys") or {}
    if not endpoint.startswith("https://") or len(endpoint) > 1000 or not klucze.get("p256dh") or not klucze.get("auth"):
        raise ValueError("niepoprawna subskrypcja")
    ulub = []
    for w in (lista_ulubionych or [])[:MAX_ULUBIONYCH]:
        nacja, _, nazwa = str(w).partition("|")
        if nacja in NACJE and nazwa: ulub.append(klucz_gracza(nacja, nazwa[:100]))
    with _blokada_push:
        subs = _subskrypcje()
        if endpoint not in subs and len(subs) >= MAX_SUBSKRYPCJI: raise ValueError("za dużo subskrypcji")
        subs[endpoint] = {"sub": {"endpoint": endpoint, "keys": {"p256dh": str(klucze["p256dh"])[:200], "auth": str(klucze["auth"])[:100]}},
                          "ulubieni": sorted(set(ulub)), "t": time.time(),
                          "jezyk": jezyk if jezyk in TEKSTY_PUSH else "en"}
        _zapisz_subskrypcje()


def usun_subskrypcje(endpoint):
    with _blokada_push:
        if _subskrypcje().pop(str(endpoint), None) is not None: _zapisz_subskrypcje()


# Treść powiadomienia w języku telefonu: (gol 1, gole 2-4, gole 5+), (asysta ...), "i", "ocena"
TEKSTY_PUSH = {
    "pl": (("gol", "{n} gole", "{n} goli"), ("asysta", "{n} asysty", "{n} asyst"), "i", "ocena"),
    "en": (("a goal", "{n} goals", "{n} goals"), ("an assist", "{n} assists", "{n} assists"), "and", "rating"),
    "de": (("ein Tor", "{n} Tore", "{n} Tore"), ("eine Vorlage", "{n} Vorlagen", "{n} Vorlagen"), "und", "Note"),
    "es": (("un gol", "{n} goles", "{n} goles"), ("una asistencia", "{n} asistencias", "{n} asistencias"), "y", "nota"),
    "fr": (("un but", "{n} buts", "{n} buts"), ("une passe décisive", "{n} passes décisives", "{n} passes décisives"), "et", "note"),
    "pt": (("um golo", "{n} golos", "{n} golos"), ("uma assistência", "{n} assistências", "{n} assistências"), "e", "nota"),
    "it": (("un gol", "{n} gol", "{n} gol"), ("un assist", "{n} assist", "{n} assist"), "e", "voto"),
    "tr": (("gol", "{n} gol", "{n} gol"), ("asist", "{n} asist", "{n} asist"), "ve", "puan"),
}


def _tresc_powiadomienia(w, jezyk="pl"):
    gole_f, asysty_f, i_, ocena_s = TEKSTY_PUSH.get(jezyk, TEKSTY_PUSH["en"])
    forma = lambda n, f: f[0] if n == 1 else (f[1] if n < 5 else f[2]).format(n=n)
    g, a = w["gole"], w["asysty"]
    czesci = []
    if g: czesci.append(forma(g, gole_f))
    if a: czesci.append(forma(a, asysty_f))
    m = w["mecz"]
    wynik = f" {m['w']} " if m.get("w") else " - "
    ocena = f" · {ocena_s} {w['ocena']:.1f}" if isinstance(w.get("ocena"), (int, float)) else ""
    ikona = "⚽" if g else "🅰️"
    return {"tytul": f"{ikona} {w['nazwa']}: {f' {i_} '.join(czesci)}",
            "tresc": f"{m['g']}{wynik}{m['a']}{ocena}",
            "tag": f"nf-{w['id']}-{w['klucz']}",
            "url": f"/app/#zawodnik={w['nacja']}|{w['nazwa']}"}


def _wyslij_powiadomienia(wyczyny):
    if not wyczyny or not push_wlaczony(): return
    from pywebpush import WebPushException, webpush
    with _blokada_push:
        subs = dict(_subskrypcje())
    wyslane, do_usuniecia = 0, []
    for endpoint, s in subs.items():
        ulub = set(s.get("ulubieni", []))
        for w in wyczyny:
            if w["klucz"] not in ulub: continue
            try:
                webpush(subscription_info=s["sub"], data=json.dumps(_tresc_powiadomienia(w, s.get("jezyk", "pl")), ensure_ascii=False),
                        vapid_private_key=VAPID_PRYWATNY, vapid_claims={"sub": VAPID_KONTAKT}, ttl=6 * 3600, timeout=15)
                wyslane += 1
            except WebPushException as e:
                kod = getattr(getattr(e, "response", None), "status_code", None)
                if kod in (404, 410): do_usuniecia.append(endpoint); break   # telefon wypisał się z powiadomień
                print(f"[push] {kod}: {str(e)[:200]}", flush=True)
            except Exception as e:
                print(f"[push] {str(e)[:200]}", flush=True)
    if do_usuniecia:
        with _blokada_push:
            for e in do_usuniecia: _subskrypcje().pop(e, None)
            _zapisz_subskrypcje()
    if wyslane: print(f"[push] wysłano {wyslane} powiadomień", flush=True)


# Subskrypcje trafiają do kopii zapasowej (repozytorium jest publiczne) zaszyfrowane kluczem
# wyprowadzonym z prywatnego klucza VAPID - bez niego kopia jest bezużyteczna.
def _szyfr():
    if not VAPID_PRYWATNY: return None
    try:
        from cryptography.fernet import Fernet
    except ImportError:
        return None
    return Fernet(base64.urlsafe_b64encode(hashlib.sha256(b"nf-kopia|" + VAPID_PRYWATNY.encode()).digest()))


def eksport_subskrypcji():
    f = _szyfr()
    if not f: return None
    with _blokada_push:
        return f.encrypt(json.dumps(_subskrypcje(), ensure_ascii=False).encode("utf-8"))


def odtworz_subskrypcje(tresc):
    f = _szyfr()
    if not f or os.path.exists(PUSH_PLIK): return
    try:
        odtworzone = json.loads(f.decrypt(tresc).decode("utf-8"))
    except Exception as e:
        print(f"[push] nie udało się odczytać kopii subskrypcji: {e}", flush=True)
        return
    with _blokada_push:
        _push["dane"] = odtworzone
        _zapisz_subskrypcje()


dane.DODATKOWE_PLIKI_KOPII["push.enc"] = (eksport_subskrypcji, odtworz_subskrypcje)


# ---------------------------------------------------------------- WEJŚCIE Z HARMONOGRAMU
def po_cyklu():
    """Po cyklu harmonogramu (w jego wątku). Nigdy nie przerywa serwera - błędy tylko loguje."""
    if not _blokada.acquire(blocking=False): return []
    raport = []
    try:
        try: _aktualizuj_transfery(raport)
        except Exception as e: raport.append(f"transfery: błąd {e}")
        wyczyny = _aktualizuj_historie(raport)
        if wyczyny:
            threading.Thread(target=_wyslij_powiadomienia, args=(wyczyny,), daemon=True).start()
            raport.append(f"powiadomienia: {len(wyczyny)} goli/asyst")
    except Exception as e:
        import traceback
        print(traceback.format_exc()[-1500:], flush=True)
        raport.append(f"historia: błąd {e}")
    finally:
        _blokada.release()
    return raport
