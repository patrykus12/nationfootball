"""
Bazy zawodników aktualizowane z API (kadry klubów + kanał transferów) - bez Transfermarktu, który blokuje serwery.

Źródła:
  * baza z Transfermarktu (repozytorium, konsola.pyw) - punkt wyjścia; zostaje dla klubów, których kadr API nie ma
    (część niższych lig zwraca pustą kadrę) i dla zawodników z podwójnym obywatelstwem,
  * kadry klubów z API (football-get-list-player): narodowość, wartość rynkowa - pobierane rotacyjnie: raz na
    ~30 dni, w oknach transferowych (styczeń, lipiec, sierpień) co ~7 dni; drużyny = wszystkie z lig, w których
    grają nasi zawodnicy (z terminarzy - bez osobnych zapytań),
  * kanał transferów (football-get-all-transfers) co kilka godzin: zawodnik z naszych kadr przenosi się od razu,
    a nowy zawodnik w klubie z naszych lig -> kadra tego klubu idzie na początek kolejki.

Wynik: scalone bazy w serwer_cache/kadry/<plik nacji>.xlsx (ten sam format co z Transfermarktu), które serwer
używa zamiast baz z repozytorium (pobieranie_danych.plik_bazy). Zawodnik, który został w tym samym klubie, zachowuje
wiersz z Transfermarktu bez zmian - daty dopisania (znani_zawodnicy) i dopasowania nie drgną.

Bezpiecznik limitu: gdy prognoza zużycia API na 30 dni przekracza PROG_OSTRZEZENIA, kadry odświeżają się 2x rzadziej,
powyżej PROG_STOP - wcale (mecze i składy mają zawsze pierwszeństwo).
"""
import json
import math
import os
import threading
import time
from datetime import datetime, timedelta

import openpyxl

import pobieranie_danych as dane
from dopasowanie import KODY_KRAJOW_RECZNE, NACJE, dopasuj_klub_do_bazy, wyczysc_nazwe_klubu

STAN_PLIK = os.path.join(dane.KATALOG_DANYCH, "serwer_cache", "kadry_api.json")
KATALOG_KADR = dane.KATALOG_KADR

DNI_ODSWIEZANIA = 30
DNI_ODSWIEZANIA_OKNO = 7
MIESIACE_OKIEN = (1, 7, 8)
MAX_KADR_NA_CYKL = 12               # cykl co ~10 min -> do ~1700/dobę, w praktyce limit dzienny niżej
MAX_KADR_PIERWSZE_DNI = 150         # pierwsze pobranie wszystkich drużyn - szybciej niż 1/30 dziennie
TRANSFERY_CO_H = 6
MAX_STRON_TRANSFEROW = 6
PROG_OSTRZEZENIA = 17000            # prognoza zużycia API / 30 dni (limit 20 000)
PROG_STOP = 18500
PRZEBUDOWA_CO_H = 12

# Kody krajów w API (FIFA, z kilkoma wyjątkami - zebrane ze składów meczowych) -> nasze nacje
KODY_API = {
    "POL": "pl", "TUR": "tr", "IND": "in", "CHN": "cn", "USA": "us", "CZE": "cz", "IDN": "id", "PAK": "pk", "NGA": "ng",
    "BRA": "br", "BAN": "bd", "MEX": "mx", "JPN": "jp", "PHI": "ph", "ETH": "et", "COD": "cd", "EGY": "eg", "VIE": "vn",
    "IRN": "ir", "GER": "de", "THA": "th", "FRA": "fr", "ENG": "en", "SCO": "sc", "WAL": "wl", "NIR": "ni", "TAN": "tz",
    "ITA": "it", "MYA": "mm", "RSA": "za", "KEN": "ke", "KOR": "kr", "COL": "co", "SUD": "sd", "ESP": "es", "ARG": "ar",
    "UGA": "ug", "ALG": "dz", "UKR": "ua", "IRQ": "iq", "AFG": "af", "CAN": "ca", "MAR": "ma", "KSA": "sa", "ANG": "ao",
    "MAS": "my", "GHA": "gh", "PER": "pe", "MOZ": "mz", "UZB": "uz", "YEM": "ye", "NEP": "np", "VEN": "ve", "CMR": "cm",
    "CIV": "ci", "MAD": "mg", "AUS": "au", "PRK": "kp", "NIG": "ne", "TPE": "tw", "SRI": "lk", "BFA": "bf", "SYR": "sy",
    "MWI": "mw", "MLI": "ml", "ZAM": "zm", "KAZ": "kz", "ROU": "ro", "CHI": "cl", "CHA": "td", "SEN": "sn", "NED": "nl",
    "GUA": "gt", "ECU": "ec", "CAM": "kh", "ZIM": "zw", "BEN": "bj", "GUI": "gn", "RWA": "rw", "BDI": "bi", "SOM": "so",
    "BOL": "bo", "TUN": "tn", "BEL": "be", "SSD": "ss", "HAI": "ht", "CUB": "cu", "JOR": "jo", "DOM": "do", "GRE": "gr",
    "SWE": "se", "AZE": "az", "POR": "pt", "UAE": "ae", "ISR": "il", "HUN": "hu", "PNG": "pg", "HON": "hn", "TJK": "tj",
    "AUT": "at", "SLE": "sl", "SUI": "ch", "TOG": "tg", "LAO": "la", "PAR": "py", "HKG": "hk", "LBY": "ly", "BUL": "bg",
    "SRB": "rs", "SLV": "sv", "NCA": "nic", "KGZ": "kg", "ERI": "er", "SIN": "sg", "DEN": "dk", "TKM": "tm", "FIN": "fi",
    "NOR": "no", "CGO": "cg", "CTA": "cf", "SVK": "sk", "LBR": "lr", "LIB": "lb", "LBN": "lb", "IRL": "ie", "CRC": "cr",
    "NZL": "nz", "GEO": "ge", "PAN": "pa", "CRO": "hr", "MTN": "mr", "BIH": "ba", "OMA": "om", "URU": "uy", "MDA": "md",
    "MGL": "mn", "MNG": "mn", "PUR": "pr", "ALB": "al", "ARM": "am", "JAM": "jm", "NAM": "na", "LTU": "lt", "QAT": "qa",
    "GAM": "gm", "BOT": "bw", "GAB": "ga", "LES": "ls", "MKD": "mk", "SVN": "si", "GNB": "gw", "PLE": "ps", "KVX": "xk",
    "KOS": "xk", "LVA": "lv", "EQG": "gq", "BHR": "bh", "MRI": "mu", "EAT": "tl", "TLS": "tl", "TRI": "tt", "CYP": "cy",
    "EST": "ee", "SWZ": "sz", "DJI": "dj", "FIJ": "fj", "COM": "km", "GUY": "gy", "SOL": "sb", "LUX": "lu", "MAC": "mo",
    "SUR": "sr", "MNE": "me", "CPV": "cv", "MLT": "mt", "VAN": "vu", "ISL": "is", "AND": "ad", "ATG": "ag", "ARU": "aw",
    "BRB": "bb", "BER": "bm", "CUW": "cw", "GIB": "gi", "GRN": "gd", "GRL": "gl", "FGU": "gf", "GUF": "gf", "GLP": "gp",
    "CAY": "ky", "LIE": "li", "MTQ": "mq", "MSR": "ms", "NIU": "nu", "NMI": "mp", "NCL": "nc", "SAM": "ws", "ASA": "as",
    "SMR": "sm", "SEY": "syc", "SKN": "kn", "LCA": "lc", "STL": "lc", "VIN": "vc", "TGA": "to", "TCA": "tc", "TUV": "tv",
    "COK": "ck", "FRO": "fo", "STP": "st",
}
# Flaga kraju nacji (jak flagi lig w API) - do sprawdzenia, czy zawodnik gra za granicą
FLAGA_NACJI = {"en": "gb-eng", "sc": "gb-sct", "wl": "gb-wls", "ni": "gb-nir", "nic": "ni", "syc": "sc"}
# Nazwy krajów jak w bazach z Transfermarktu (kolumna Klub: "[Kraj] Klub") - odwrotność KODY_KRAJOW_RECZNE
KRAJ_Z_FLAGI = {}
for _nazwa, _kod in KODY_KRAJOW_RECZNE.items():
    KRAJ_Z_FLAGI.setdefault(_kod, _nazwa[:1].upper() + _nazwa[1:])

_blokada = threading.Lock()
_stan = {"dane": None}


def flaga_nacji(n): return FLAGA_NACJI.get(n, n)


def _wczytaj():
    if _stan["dane"] is None:
        s = dane.wczytaj_json(STAN_PLIK) or {}
        for k, v in (("druzyny", {}), ("ligi", {}), ("przeniesienia", {}), ("transfery_do", ""), ("transfery_t", 0),
                     ("zbudowano", 0), ("wersja_tm", None), ("zmiany", 0)):
            s.setdefault(k, v)
        _stan["dane"] = s
    return _stan["dane"]


def _zapisz():
    s = _wczytaj()
    with open(STAN_PLIK + ".tmp", "w", encoding="utf-8") as f: json.dump(s, f, ensure_ascii=False, separators=(",", ":"))
    os.replace(STAN_PLIK + ".tmp", STAN_PLIK)


# ---------------------------------------------------------------- DRUŻYNY Z NASZYCH LIG
def _odswiez_druzyny():
    """Ligi krajowe, w których grają nasi zawodnicy (mecze z historii), i ich drużyny - z terminarzy, 0 zapytań.
    Raz dopisana liga/drużyna zostaje (poza sezonem nie ma meczów, a transfery są)."""
    import historia
    s = _wczytaj()
    h = historia._historia()
    slownik = dane.wczytaj_nasz_slownik()
    dzis = datetime.now(dane.TZ_PL).date()
    nowe = 0
    mecze = [m for o in range(-dane.OKNO_DNI - 1, dane.OKNO_DNI + 2)
             for m in (dane.surowe_z_cache(dzis + timedelta(days=o)) or {}).get("mecze", [])]
    from dopasowanie import flaga_ligi_meczu
    ligi_json = dane.wczytaj_json(dane.LIGI_PLIK, {}) or {}
    for m in mecze:
        lid = str(m.get("leagueId", ""))
        nasz = str(m.get("id")) in h["mecze"]
        if not lid or not (nasz or lid in s["ligi"]): continue
        # Ta sama flaga co przy dopasowaniu meczów (kody 3-literowe, ręczne nadpisania z ligi.json)
        flaga = flaga_ligi_meczu(m, slownik, ligi_json).lower()
        if flaga in ("int", "", "none"): continue
        s["ligi"][lid] = {"nazwa": (slownik.get(lid) or {}).get("nazwa", lid), "flaga": flaga}
    for m in mecze:
        lid = str(m.get("leagueId", ""))
        if lid not in s["ligi"]: continue
        for strona in ("home", "away"):
            d = m.get(strona) or {}
            tid = str(d.get("id", ""))
            if not tid or not d.get("name"): continue
            if tid not in s["druzyny"]:
                s["druzyny"][tid] = {"n": d["name"], "l": lid, "f": s["ligi"][lid]["flaga"], "t": 0, "z": None}
                nowe += 1
            else:
                s["druzyny"][tid].update(n=d["name"], l=lid, f=s["ligi"][lid]["flaga"])
    return nowe


# ---------------------------------------------------------------- POBIERANIE KADR (rotacyjnie, z bezpiecznikiem)
def _w_oknie_transferowym(): return datetime.now(dane.TZ_PL).month in MIESIACE_OKIEN


def _pobrane_dzis(rodzaj):
    return (dane._licznik_dni().get(datetime.now(dane.TZ_PL).strftime("%Y-%m-%d")) or {}).get(rodzaj, 0)


def plan_kadr():
    """Ile kadr wolno dziś pobrać (i dlaczego) - także do strony statusu."""
    s = _wczytaj()
    n = len(s["druzyny"])
    dni = DNI_ODSWIEZANIA_OKNO if _w_oknie_transferowym() else DNI_ODSWIEZANIA
    prognoza = dane.podsumowanie_licznika().get("szacunek_na_30_dni") or 0
    if prognoza >= PROG_STOP:
        return {"dziennie": 0, "dni": dni, "powod": f"stop - prognoza {prognoza}/mies.", "prognoza": prognoza}
    powod = "okno transferowe" if dni == DNI_ODSWIEZANIA_OKNO else "zwykły miesiąc"
    if prognoza >= PROG_OSTRZEZENIA:
        dni *= 2
        powod += f", zwolnione (prognoza {prognoza}/mies.)"
    dziennie = math.ceil(n / dni) if n else 0
    nigdy = sum(1 for d in s["druzyny"].values() if not d["t"])
    if nigdy and prognoza < PROG_OSTRZEZENIA: dziennie = max(dziennie, min(MAX_KADR_PIERWSZE_DNI, nigdy))
    return {"dziennie": dziennie, "dni": dni, "powod": powod, "prognoza": prognoza, "druzyn": n, "nigdy_pobrane": nigdy}


def _sklad_z_odpowiedzi(odp):
    """[[id, nazwa, kod kraju, wartość, pozycja]] - bez trenerów. None, gdy API nie ma kadry."""
    grupy = (((odp or {}).get("response") or {}).get("list") or {}).get("squad") or []
    zawodnicy = []
    for g in grupy:
        if g.get("title") == "coach": continue
        for z in g.get("members") or []:
            if z.get("id") and z.get("name"):
                zawodnicy.append([z["id"], z["name"], z.get("ccode") or "", z.get("transferValue") or 0, z.get("positionId")])
    return zawodnicy or None


def _pobierz_kadry(raport):
    s = _wczytaj()
    plan = plan_kadr()
    wolno = plan["dziennie"] - _pobrane_dzis("kadry")
    if wolno <= 0: return 0
    teraz = time.time()
    wiek_max = plan["dni"] * 86400
    kolejka = sorted((d["t"], tid) for tid, d in s["druzyny"].items() if teraz - d["t"] >= wiek_max or d.get("pilne"))
    kolejka.sort(key=lambda x: (not s["druzyny"][x[1]].get("pilne"), x[0]))
    pobrane = 0
    for _, tid in kolejka[:min(wolno, MAX_KADR_NA_CYKL)]:
        if dane.awaria_api(): break
        try:
            odp = dane._api_get("football-get-list-player", {"teamid": tid}, timeout=20)
        except Exception as e:
            print(f"[kadry] {tid}: {e}", flush=True)
            continue
        d = s["druzyny"][tid]
        nowy = _sklad_z_odpowiedzi(odp)
        if nowy is not None or d["z"] is None: d["z"] = nowy      # pusta odpowiedź nie kasuje starej kadry
        d["t"] = time.time()
        d.pop("pilne", None)
        pobrane += 1
    if pobrane:
        s["zmiany"] += pobrane
        raport.append(f"kadry z API: {pobrane} ({plan['powod']})")
    return pobrane


# ---------------------------------------------------------------- KANAŁ TRANSFERÓW
def _pobierz_transfery(raport):
    s = _wczytaj()
    if time.time() - s["transfery_t"] < TRANSFERY_CO_H * 3600 or dane.awaria_api(): return 0
    ostatni = s["transfery_do"]
    nowe, najnowszy = [], ostatni
    for strona in range(1, MAX_STRON_TRANSFEROW + 1):
        try:
            lista = (dane._api_get("football-get-all-transfers", {"page": strona}, timeout=20).get("response") or {}).get("transfers") or []
        except Exception as e:
            print(f"[transfery] {e}", flush=True)
            return 0
        doszlismy = False
        for t in lista:
            data = t.get("transferDate") or ""
            if ostatni and data <= ostatni:
                doszlismy = True
                break
            nowe.append(t)
            najnowszy = max(najnowszy, data)
        # Pierwsze uruchomienie: wystarczy pierwsza strona (znacznik, od kiedy czytać)
        if doszlismy or not lista or not ostatni: break
    s["transfery_t"] = time.time()
    if not ostatni:      # pierwsze uruchomienie - tylko zapamiętujemy, gdzie jesteśmy (stare przeniesienia są już w kadrach)
        s["transfery_do"] = najnowszy
        return 1      # stan do zapisania
    s["transfery_do"] = najnowszy
    druzyny = s["druzyny"]
    znani = {z[0] for d in druzyny.values() for z in (d["z"] or [])}
    pilne = 0
    for t in nowe:
        pid, do = t.get("playerId"), str(t.get("toClubId") or "")
        if not pid: continue
        s["przeniesienia"][str(pid)] = {"do": do, "nazwa_do": t.get("toClub"), "data": (t.get("transferDate") or "")[:10],
                                         "zawodnik": t.get("name"), "wypozyczenie": bool(t.get("onLoan"))}
        # Nieznany zawodnik w klubie z naszych lig - pobierz kadrę tego klubu, żeby poznać jego narodowość
        if pid not in znani and do in druzyny and not druzyny[do].get("pilne"):
            druzyny[do]["pilne"] = True
            pilne += 1
    granica = (datetime.now(dane.TZ_PL).date() - timedelta(days=120)).isoformat()
    s["przeniesienia"] = {k: v for k, v in s["przeniesienia"].items() if v["data"] >= granica}
    if nowe:
        s["zmiany"] += len(nowe)
        raport.append(f"transfery z API: {len(nowe)} nowych, {pilne} klubów do sprawdzenia")
    return len(nowe)


# ---------------------------------------------------------------- SCALANIE Z BAZAMI Z TRANSFERMARKTU
def _wiersze_tm(nacja):
    """[(imię, nazwisko, klub_raw)] z bazy z Transfermarktu."""
    sciezka = dane.plik_bazy_tm(nacja)
    if not os.path.exists(sciezka): return []
    wb = openpyxl.load_workbook(sciezka, read_only=True)
    try:
        wiersze = list(wb.active.iter_rows(values_only=True))
    finally:
        wb.close()
    if not wiersze: return []
    kol = [str(c).strip().lower() if c is not None else "" for c in wiersze[0]]
    wynik = []
    for w in wiersze[1:]:
        r = {k: ("" if v is None or str(v).lower() == "nan" else str(v).strip()) for k, v in zip(kol, w)}
        if r.get("klub"): wynik.append((r.get("imię", ""), r.get("nazwisko", ""), r["klub"]))
    return wynik


def _rozbij_klub(klub_raw):
    import historia
    return historia._rozbij_klub(klub_raw)


def _flaga_kraju_tm(kraj): return KODY_KRAJOW_RECZNE.get((kraj or "").strip().lower(), "")


def _mapa_klubow(druzyny, wiersze_tm):
    """Kluby z baz Transfermarktu -> drużyny z API, tym samym dopasowaniem co mecze (nazwa + kraj).
    Zwraca ({(flaga kraju TM, klucz klubu): tid}, {tid: kraj klubu wg Transfermarktu}). Kraj klubu bywa inny niż
    kraj ligi (CF Montréal w MLS) - wtedy liczy się kraj klubu, jak w Transfermarkcie."""
    from dopasowanie import LIGI_ZA_GRANICA
    kluby_kraju = {}
    for wiersze in wiersze_tm.values():
        for _, _, klub_raw in wiersze:
            klub, kraj = _rozbij_klub(klub_raw)
            f = _flaga_kraju_tm(kraj)
            if f: kluby_kraju.setdefault(f, {})[wyczysc_nazwe_klubu(klub)] = {"gracze": [], "kraj": kraj}
    gosci = {}   # flaga ligi -> kraje klubów, które w niej grają (np. us -> ca)
    for kraj_klubu, ligi in LIGI_ZA_GRANICA.items():
        for f in ligi: gosci.setdefault(f, set()).add(kraj_klubu)
    klub_do_tid, kraj_tid = {}, {}
    for tid, d in druzyny.items():
        baza = {}
        for f in {d["f"]} | gosci.get(d["f"], set()):
            baza.update({(f, k): v for k, v in kluby_kraju.get(f, {}).items()})
        if not baza: continue
        po_kluczu = {k: v for (_, k), v in baza.items()}
        trafienie, info = dopasuj_klub_do_bazy(d["n"], d["f"], po_kluczu)
        if trafienie:
            f_klubu = _flaga_kraju_tm(info["kraj"])
            klub_do_tid.setdefault((f_klubu, trafienie), tid)
            kraj_tid[tid] = info["kraj"]
    return klub_do_tid, kraj_tid


def _rozdziel_nazwe(nazwa):
    czesci = nazwa.split(" ", 1)
    return (czesci[0], czesci[1]) if len(czesci) == 2 else ("", nazwa)


def _zawodnicy_api():
    """{klucz nazwy: [(pid, nazwa, kod, wartość, tid, czas kadry, potwierdzony_transfer)]} ze wszystkich kadr
    + przeniesienia z kanału transferów (tid "@Klub" - klub spoza naszych lig, None - bez klubu)."""
    s = _wczytaj()
    gdzie = {}
    for tid, d in s["druzyny"].items():
        for pid, nazwa, kod, wartosc, _ in d["z"] or []:
            stary = gdzie.get(pid)
            if stary is None or d["t"] > stary[5]: gdzie[pid] = (pid, nazwa, kod, wartosc, tid, d["t"], False)
    for pid_s, p in s["przeniesienia"].items():
        pid = int(pid_s)
        if pid not in gdzie: continue
        z = gdzie[pid]
        data_kadry = datetime.fromtimestamp(z[5], dane.TZ_PL).date().isoformat() if z[5] else ""
        if p["data"] < data_kadry: continue     # kadra jest nowsza niż transfer - już go uwzględnia
        if p["do"] in s["druzyny"]:
            cel = p["do"]
        elif p["do"] != z[4]:
            bez_klubu = not p["do"] or (p.get("nazwa_do") or "").lower() in ("free agent", "retired", "")
            cel = None if bez_klubu else "@" + p["nazwa_do"]
        else:
            continue
        gdzie[pid] = z[:4] + (cel, z[5], True)
    wynik = {}
    for z in gdzie.values():
        wynik.setdefault(dane._klucz_znanego(z[1]), []).append(z)
    return wynik


def zbuduj_bazy(raport, wymus=False):
    """Scalone bazy wszystkich nacji -> serwer_cache/kadry/. Pisze tylko pliki, które się zmieniły.

    Zawodnik z Transfermarktu zmienia klub TYLKO gdy: w kadrach API jest dokładnie jeden zawodnik tej narodowości
    o tym nazwisku ORAZ (kanał transferów potwierdził transfer po jego ID albo kadra jego dotychczasowego klubu jest
    pobrana i go w niej nie ma). Inaczej wiersz zostaje bez zmian - np. klub z pustą kadrą w API albo imiennik."""
    s = _wczytaj()
    wersja_tm = [os.path.getmtime(dane.plik_bazy_tm(n)) if os.path.exists(dane.plik_bazy_tm(n)) else 0 for n in NACJE]
    pora = time.time() - s["zbudowano"] >= PRZEBUDOWA_CO_H * 3600 and s["zmiany"]
    brak_plikow = not os.path.isdir(KATALOG_KADR) or not os.listdir(KATALOG_KADR)
    if not any(d["z"] for d in s["druzyny"].values()): return 0   # dopóki API nic nie dało - bazy z Transfermarktu
    if not (wymus or pora or s["wersja_tm"] != wersja_tm or brak_plikow):
        return 0
    os.makedirs(KATALOG_KADR, exist_ok=True)
    druzyny = s["druzyny"]
    wiersze_tm = {n: _wiersze_tm(n) for n in NACJE}
    klub_do_tid, kraj_tid = _mapa_klubow(druzyny, wiersze_tm)
    # Ładne nazwy krajów jak w bazach (np. "Stany Zjednaczone"), gdy kraj klubu znamy tylko z flagi ligi
    nazwy_krajow = {}
    for wiersze in wiersze_tm.values():
        for _, _, klub_raw in wiersze:
            kraj = _rozbij_klub(klub_raw)[1]
            if kraj: nazwy_krajow.setdefault(_flaga_kraju_tm(kraj), kraj)
    flaga_druzyny = lambda tid: _flaga_kraju_tm(kraj_tid[tid]) if tid in kraj_tid else druzyny[tid]["f"]

    def klub_api(tid):
        kraj = kraj_tid.get(tid) or nazwy_krajow.get(druzyny[tid]["f"]) or KRAJ_Z_FLAGI.get(druzyny[tid]["f"], "")
        return f"[{kraj}] {druzyny[tid]['n']}" if kraj else druzyny[tid]["n"]

    api = _zawodnicy_api()
    sklady = {tid: {z[0] for z in d["z"]} for tid, d in druzyny.items() if d["z"]}
    zmienione, staty = 0, {"przeniesieni": 0, "nowi": 0, "odeszli": 0}
    for nacja, info in NACJE.items():
        flaga_n = flaga_nacji(nacja)
        tylko_aktualizuj = bool(info.get("ligi"))   # zasady brazylijskie: z API tylko zmiany klubów, bez dopisywania
        # Te same wyjątki co w skanerze Transfermarktu (np. Amerykanie w kanadyjskich klubach MLS to nie legioniści)
        pomin_flagi = {_flaga_kraju_tm(k) for k in info.get("pomin_kraje", [])}
        pomin_kluby = {wyczysc_nazwe_klubu(k) for k in info.get("pomin_kluby", [])}
        def u_siebie(tid):
            return flaga_druzyny(tid) == flaga_n or flaga_druzyny(tid) in pomin_flagi                 or wyczysc_nazwe_klubu(druzyny[tid]["n"]) in pomin_kluby
        wiersze, uzyci = [], set()
        for imie, nazwisko, klub_raw in wiersze_tm[nacja]:
            nazwa = f"{imie} {nazwisko}".strip()
            klub, kraj = _rozbij_klub(klub_raw)
            tm_tid = klub_do_tid.get((_flaga_kraju_tm(kraj), wyczysc_nazwe_klubu(klub)))
            wszyscy = api.get(dane._klucz_znanego(nazwa), [])
            for z in wszyscy:                   # ten sam człowiek w tym klubie (np. inna narodowość w API) - nie dublujemy
                if tm_tid and z[0] in sklady.get(tm_tid, ()): uzyci.add(z[0])
            kandydaci = [z for z in wszyscy if KODY_API.get(z[2]) == nacja]
            if len(kandydaci) != 1:
                wiersze.append((imie, nazwisko, klub_raw)); continue
            pid, _, _, _, tid, _, potwierdzony = kandydaci[0]
            uzyci.add(pid)
            if tid == tm_tid:
                wiersze.append((imie, nazwisko, klub_raw)); continue
            odszedl = potwierdzony or (tm_tid in sklady and pid not in sklady[tm_tid])
            if not odszedl:
                wiersze.append((imie, nazwisko, klub_raw)); continue
            if tid is None:
                staty["odeszli"] += 1; continue
            if tid.startswith("@"):
                wiersze.append((imie, nazwisko, tid[1:])); staty["przeniesieni"] += 1; continue
            if u_siebie(tid):                   # wrócił do ligi swojego kraju (albo klub z wyjątków nacji)
                staty["odeszli"] += 1; continue
            wiersze.append((imie, nazwisko, klub_api(tid)))
            staty["przeniesieni"] += 1
        if not tylko_aktualizuj:
            for lista in api.values():
                for pid, nazwa, kod, wartosc, tid, _, _ in lista:
                    if pid in uzyci or not tid or tid.startswith("@") or KODY_API.get(kod) != nacja or not wartosc: continue
                    if u_siebie(tid): continue
                    imie, nazwisko = _rozdziel_nazwe(nazwa)
                    wiersze.append((imie, nazwisko, klub_api(tid)))
                    uzyci.add(pid)
                    staty["nowi"] += 1
        wiersze.sort(key=lambda w: (w[1].lower(), w[0].lower()))
        if _zapisz_baze(nacja, wiersze): zmienione += 1
    s.update(zbudowano=time.time(), wersja_tm=wersja_tm, zmiany=0)
    _zapisz()
    if zmienione:
        dane._wersja["wartosc"] = None
        raport.append(f"bazy z API: {zmienione} nacji zmienionych (przeniesieni {staty['przeniesieni']}, "
                      f"nowi {staty['nowi']}, odeszli {staty['odeszli']})")
    return zmienione


def _zapisz_baze(nacja, wiersze):
    sciezka = os.path.join(KATALOG_KADR, NACJE[nacja]["plik"])
    if os.path.exists(sciezka):
        wb = openpyxl.load_workbook(sciezka, read_only=True)
        try: obecne = [tuple("" if v is None else str(v) for v in w) for w in list(wb.active.iter_rows(values_only=True))[1:]]
        finally: wb.close()
        if obecne == [tuple(w) for w in wiersze]: return False
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["Imię", "Nazwisko", "Klub"])
    for w in wiersze: ws.append(list(w))
    wb.save(sciezka + ".tmp.xlsx")
    os.replace(sciezka + ".tmp.xlsx", sciezka)
    return True


# ---------------------------------------------------------------- WEJŚCIE Z HARMONOGRAMU / STATUS
def po_cyklu():
    if not _blokada.acquire(blocking=False): return []
    raport = []
    try:
        zmiany = _odswiez_druzyny()
        zmiany += _pobierz_transfery(raport)
        zmiany += _pobierz_kadry(raport)
        zbuduj_bazy(raport)              # zapisuje stan sam, gdy coś zbudował
        if zmiany: _zapisz()
    except Exception:
        import traceback
        print(traceback.format_exc()[-1500:], flush=True)
        raport.append("kadry: błąd (szczegóły w logu)")
    finally:
        _blokada.release()
    return raport


def status():
    s = _wczytaj()
    plan = plan_kadr()
    pobrane = [d for d in s["druzyny"].values() if d["t"]]
    return {"ligi": len(s["ligi"]), "druzyny": len(s["druzyny"]), "druzyny_z_kadra": sum(1 for d in pobrane if d["z"]),
            "druzyny_pobrane": len(pobrane), "pobrane_dzis": _pobrane_dzis("kadry"), "plan": plan,
            "transfery_do": s["transfery_do"], "przeniesien": len(s["przeniesienia"]),
            "zbudowano": datetime.fromtimestamp(s["zbudowano"], dane.TZ_PL).strftime("%Y-%m-%d %H:%M") if s["zbudowano"] else None}
