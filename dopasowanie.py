"""
Wspólna logika "który mecz jest z Polakami" - używana przez aplikację (test_flashscore.py)
i przez serwer (serwer.py, automatyczne odświeżanie meczów Polaków). Bez pandas/Tkinter,
żeby serwer pozostał lekki.
"""
import os
import re
import difflib
import functools
import unicodedata
from datetime import datetime

import openpyxl
import pytz

KODY_KRAJOW_RECZNE = {
    'anglia': 'gb-eng', 'australia': 'au', 'austria': 'at', 'azerbejdżan': 'az',
    'belgia': 'be', 'cypr': 'cy', 'czechy': 'cz', 'dania': 'dk',
    'finlandia': 'fi', 'francja': 'fr', 'gibraltar': 'gi', 'grecja': 'gr',
    'hiszpania': 'es', 'holandia': 'nl', 'indonezja': 'id', 'irlandia': 'ie',
    'islandia': 'is', 'japonia': 'jp', 'kanada': 'ca', 'korea południowa': 'kr',
    'litwa': 'lt', 'mołdawia': 'md', 'niemcy': 'de', 'norwegia': 'no',
    'portugalia': 'pt', 'rumunia': 'ro', 'szkocja': 'gb-sct', 'szwajcaria': 'ch',
    'szwecja': 'se', 'słowacja': 'sk', 'turcja': 'tr', 'usa': 'us', 'stany zjednoczone': 'us',
    'stany zjednaczone': 'us',
    'ukraina': 'ua', 'walia': 'gb-wls', 'wyspy owcze': 'fo', 'węgry': 'hu',
    'włochy': 'it', 'zjednoczone emiraty arabskie': 'ae', 'polska': 'pl',
    'nowa zelandia': 'nz', 'filipiny': 'ph', 'hong kong': 'hk', 'chiny': 'cn', 'tajlandia': 'th',
    'słowenia': 'si', 'uganda': 'ug', 'arabia saudyjska': 'sa', 'kirgistan': 'kg',
    'zjednaczone emiraty arabskie': 'ae', 'argentyna': 'ar', 'brazylia': 'br', 'ekwador': 'ec',
    'kolumbia': 'co', 'urugwaj': 'uy', 'meksyk': 'mx', 'republika południowej afryki': 'za',
    'maroko': 'ma', 'egipt': 'eg', 'algieria': 'dz', 'tanzania': 'tz', 'iran': 'ir', 'kuwejt': 'kw'
}

# Śledzone nacje: kod -> kraj na Transfermarkcie (land_id, nazwa na liście krajów) i plik bazy
# zawodników. Polska zostaje w zawodnicy.xlsx - z tego pliku korzysta też aplikacja na komputer.
# pomin_kraje - kraje, w których gra się w tych samych rozgrywkach co u siebie (to nie "za granicą").
# od - kiedy nację dodano: jej zawodnicy nie liczą się w meczach sprzed tej chwili (bez dociągania
# składów wstecz), nawet gdy serwer straci zapis dat dopisania zawodników.
# ligi - nacja z mnóstwem legionistów: do bazy (czyli do pobierania składów) tylko kraje z tej listy,
# do podanego poziomu rozgrywkowego. Bez "ligi" - wszystkie ligi centralne (skaner_zawodnikow.py).
# kraje_bez_lig - kraje, których lig Transfermarkt nie ma (zawodnik bez linku do ligi); tam brak linku
# to najwyższa liga, a nie amatorska.

# Kraj (nazwa jak na Transfermarkcie) -> najniższy uwzględniany poziom rozgrywkowy
LIGI_CZOLOWE = {
    # Europa - top 10 lig, w pierwszej piątce także 2. poziom
    "Anglia": 2, "Hiszpania": 2, "Niemcy": 2, "Włochy": 2, "Francja": 2,
    "Portugalia": 1, "Belgia": 1, "Holandia": 1, "Turcja": 1, "Polska": 1,
    # Ameryka Południowa i Północna
    "Argentyna": 1, "Brazylia": 1, "Ekwador": 1, "Kolumbia": 1, "Urugwaj": 1,
    "Stany Zjednaczone": 1, "Meksyk": 1,
    # Afryka
    "Republika Południowej Afryki": 1, "Maroko": 1, "Egipt": 1, "Algieria": 1, "Tanzania": 1,
    # Azja i Oceania
    "Arabia Saudyjska": 1, "Japonia": 1, "Korea Południowa": 1, "Zjednaczone Emiraty Arabskie": 1,
    "Iran": 1, "Australia": 1, "Nowa Zelandia": 1,
}

NACJE = {
    "pl": {"nazwa": "Polska", "land_id": 135, "plik": "zawodnicy.xlsx"},
    "tr": {"nazwa": "Turcja", "land_id": 174, "plik": "zawodnicy_tr.xlsx"},
    "in": {"nazwa": "Indie", "land_id": 67, "plik": "zawodnicy_in.xlsx"},
    "cn": {"nazwa": "Chiny", "land_id": 34, "plik": "zawodnicy_cn.xlsx"},
    "us": {"nazwa": "Stany Zjednaczone", "land_id": 184, "plik": "zawodnicy_us.xlsx",
           "pomin_kraje": ["Kanada"]},  # kanadyjskie kluby grają w MLS
    "cz": {"nazwa": "Czechy", "land_id": 172, "plik": "zawodnicy_cz.xlsx"},
    "id": {"nazwa": "Indonezja", "land_id": 68, "plik": "zawodnicy_id.xlsx"},
    "pk": {"nazwa": "Pakistan", "land_id": 128, "plik": "zawodnicy_pk.xlsx", "od": "2026-10-22 16:30"},
    "ng": {"nazwa": "Nigeria", "land_id": 124, "plik": "zawodnicy_ng.xlsx", "od": "2026-10-22 16:45"},
    "br": {"nazwa": "Brazylia", "land_id": 26, "plik": "zawodnicy_br.xlsx", "od": "2026-10-29 11:45",
           "ligi": LIGI_CZOLOWE},
    "bd": {"nazwa": "Bangladesz", "land_id": 16, "plik": "zawodnicy_bd.xlsx", "od": "2026-10-29 11:50"},
    "mx": {"nazwa": "Meksyk", "land_id": 110, "plik": "zawodnicy_mx.xlsx", "od": "2026-10-29 11:55"},
    "jp": {"nazwa": "Japonia", "land_id": 77, "plik": "zawodnicy_jp.xlsx", "od": "2026-10-29 12:15"},
    "ph": {"nazwa": "Filipiny", "land_id": 134, "plik": "zawodnicy_ph.xlsx", "od": "2026-10-29 12:20"},
    "et": {"nazwa": "Etiopia", "land_id": 11, "plik": "zawodnicy_et.xlsx", "od": "2026-10-29 12:25",
           "kraje_bez_lig": ["Kuwejt"]},  # Al-Arabi, Al-Fahaheel
    "cd": {"nazwa": "Demokratyczna Republika Kongo", "land_id": 193, "plik": "zawodnicy_cd.xlsx", "od": "2026-10-29 12:40"},
    "eg": {"nazwa": "Egipt", "land_id": 2, "plik": "zawodnicy_eg.xlsx", "od": "2026-10-29 12:45"},
    "vn": {"nazwa": "Wietnam", "land_id": 185, "plik": "zawodnicy_vn.xlsx", "od": "2026-10-29 13:00"},
    "ir": {"nazwa": "Iran", "land_id": 71, "plik": "zawodnicy_ir.xlsx", "od": "2026-10-29 13:05"},
}


def ma_szeroka_baze(nacja):
    """Nacja z zawężonymi ligami ("ligi") ma też szeroką bazę - pozostałe działają jak dotąd."""
    return "ligi" in NACJE[nacja]

def plik_szerokiej_bazy(nacja):
    """Wszyscy zawodnicy nacji z zawężonymi ligami, bez limitu lig (zawodnicy_XX_wszyscy.xlsx). Ta baza
    nigdy nie powoduje zapytań do API - liczy się tylko w meczach, których składy serwer i tak ma
    (pobrane dla innych nacji, np. Brazylijczyk w szkockim klubie Polaka)."""
    return NACJE[nacja]["plik"].replace(".xlsx", "_wszyscy.xlsx")

# Kody krajów z API, których nie ma w CCODE_DO_ALPHA2 serwera (słownik lig ma je zapisane np. jako "ksa") -
# bez zamiany liga nie ma flagi, a sprawdzanie kraju klubu przepuszcza np. katarskie Al-Ahli jako saudyjskie
FLAGI_TRZYLITEROWE = {
    "qat": "qa", "ksa": "sa", "ind": "in", "uae": "ae", "can": "ca", "blr": "by", "chn": "cn",
    "alb": "al", "crc": "cr", "est": "ee", "arm": "am", "aze": "az", "bol": "bo", "geo": "ge",
    "alg": "dz", "ban": "bd", "bih": "ba",
}

# Kluby, które grają w lidze innego kraju: kanadyjskie (Toronto FC, CF Montréal...) w MLS (USA)
LIGI_ZA_GRANICA = {"ca": {"us"}}

# Ligi kobiece - także te, w których drużyny nazywają się jak męskie (szkocka SWPL: "Aberdeen", "Celtic")
SLOWA_KLUCZOWE_LIGI_KOBIECE = ("women", "female", "ladies", "kobiet", "femin", "frauen", "wsl", "swpl",
                               "kvinner", "vrouwen", "damallsvenskan", "toppserien", "kvindeliga",
                               "nwsl", "arkema", "iberdrola", "(w)")


def normalizuj_tekst(tekst): return unicodedata.normalize('NFKD', str(tekst)).encode('ASCII', 'ignore').decode('utf-8').lower().strip()

@functools.lru_cache(maxsize=200000)  # te same nazwy czyszczone tysiące razy przy dopasowaniu
def wyczysc_nazwe_klubu(nazwa):
    n = normalizuj_tekst(nazwa)
    for fraza in ["1. fc ", "1.fc ", " fc", " sc", " fk", " afc"]:
        if n.endswith(fraza): n = n[:-len(fraza)].strip()
        elif n.startswith(fraza): n = n[len(fraza):].strip()
    return re.sub(r'\[.*?\]', '', n).strip()

def podobienstwo(a, b): return difflib.SequenceMatcher(None, wyczysc_nazwe_klubu(a), wyczysc_nazwe_klubu(b)).ratio()

def czy_liga_kobieca(nazwa_ligi):
    n = (nazwa_ligi or "").lower()
    return any(slowo in n for slowo in SLOWA_KLUCZOWE_LIGI_KOBIECE) or bool(re.search(r"\bliga f\b", n))

def czy_to_niechciana_druzyna(nazwa):
    n = nazwa.lower().strip()
    if "(w)" in n or " (w) " in n or n.endswith(" (w)") or n.endswith(" w") or "women" in n or "kobiety" in n: return True
    if "willem ii" in n: return False
    if n.endswith((" akatemia", " reserves")) or n.startswith("jong "): return True  # rezerwy: "KuPS Akatemia", "Jong Sparta Rotterdam"
    return bool(re.search(r'\b(b|c|ii|2)\b$', n) or " u2" in n or " u1" in n)

def wczytaj_kluby(excel_plik):
    """{oczyszczona_nazwa_klubu: {'gracze': [...], 'kraj': '...'}} z zawodnicy.xlsx (kolumny Imię, Nazwisko, Klub)."""
    if not os.path.exists(excel_plik): return {}
    wb = openpyxl.load_workbook(excel_plik, read_only=True)
    try:
        wiersze = list(wb.active.iter_rows(values_only=True))
    finally:
        wb.close()
    if not wiersze: return {}
    kolumny = [str(c).strip().lower() if c is not None else "" for c in wiersze[0]]
    baza = {}

    for wartosci in wiersze[1:]:
        wiersz = {k: ("" if v is None else str(v).strip()) for k, v in zip(kolumny, wartosci)}
        i, n, k_raw = wiersz.get('imię', ''), wiersz.get('nazwisko', ''), wiersz.get('klub', '')
        if i.lower() == "nan": i = ""
        if n.lower() == "nan": n = ""
        pelne_imie = f"{i} {n}".strip()

        if k_raw and k_raw.lower() != "nan":
            kraj = ""
            match = re.search(r'\[(.*?)\]', k_raw)
            if match:
                kraj = match.group(1).strip()
                k_raw = k_raw.replace(f"[{match.group(1)}]", "").strip()

            # Zawodnik rezerw (np. "Ajax Amsterdam U21", "VfB Stuttgart II") - mecze rezerw są
            # odfiltrowywane, a wpis łapałby przez dopasowanie nazw mecze pierwszej drużyny
            if czy_to_niechciana_druzyna(k_raw): continue
            k_czysty = wyczysc_nazwe_klubu(k_raw)
            if k_czysty not in baza: baza[k_czysty] = {'gracze': [], 'kraj': kraj}
            if pelne_imie not in baza[k_czysty]['gracze']:
                baza[k_czysty]['gracze'].append(pelne_imie)
    return baza

def dopasuj_klub_do_bazy(nazwa_klubu_z_api, alpha2_z_api, baza_klubow):
    norm_klub_api = wyczysc_nazwe_klubu(nazwa_klubu_z_api)
    if norm_klub_api in ["fire", "chicago"]: norm_klub_api = "chicago fire"

    def weryfikuj_kraj(info_klubu):
        kraj_z_excela = info_klubu.get('kraj', '').lower()
        if not kraj_z_excela: return True
        kod_z_excela = KODY_KRAJOW_RECZNE.get(kraj_z_excela, "")
        if not kod_z_excela: return True
        if alpha2_z_api and alpha2_z_api != "int":
            return (kod_z_excela == alpha2_z_api or alpha2_z_api in kod_z_excela or kod_z_excela in alpha2_z_api
                    or alpha2_z_api in LIGI_ZA_GRANICA.get(kod_z_excela, ()))
        return True

    if norm_klub_api in baza_klubow:
        if weryfikuj_kraj(baza_klubow[norm_klub_api]): return norm_klub_api, baza_klubow[norm_klub_api]

    # Nazwa z API zawarta w dłuższej nazwie z bazy ("Juventus" -> "Juventus Turyn"), ale tylko jako
    # całe słowa ("Russia" to nie "Borussia ...") i bez obcinania "1. FC" ("1. FC Köln" to nie
    # "SC Fortuna Köln"). W drugą stronę nie: "Clube Futebol Benfica" to nie "Benfica".
    norm_do_zawierania = norm_klub_api
    if re.match(r'1\. ?fc ', normalizuj_tekst(nazwa_klubu_z_api)): norm_do_zawierania = normalizuj_tekst(nazwa_klubu_z_api)
    wzorzec = re.compile(rf'(?<![\w.]){re.escape(norm_do_zawierania)}(?!\w)')
    for k_baza, info in baza_klubow.items():
        if norm_klub_api == normalizuj_tekst(info.get('kraj', '')): continue  # reprezentacja "Gibraltar" to nie "Lions Gibraltar"
        if len(norm_klub_api) >= 4 and wzorzec.search(k_baza):
            if weryfikuj_kraj(info): return k_baza, info

    # To samo co podobienstwo(k_baza, norm_klub_api) dla każdego klubu, ale szybciej: tanie górne
    # oszacowania (real_quick_ratio, quick_ratio >= ratio) odsiewają kluby, które i tak nie przebiją
    # najlepszego wyniku ani progu 0.89 - wynik identyczny
    porownanie = difflib.SequenceMatcher(None)
    porownanie.set_seq2(wyczysc_nazwe_klubu(norm_klub_api))
    best_match, best_ratio = None, 0
    for k_baza, info in baza_klubow.items():
        if not weryfikuj_kraj(info): continue
        porownanie.set_seq1(wyczysc_nazwe_klubu(k_baza))
        prog = max(best_ratio, 0.89)
        if porownanie.real_quick_ratio() <= prog or porownanie.quick_ratio() <= prog: continue
        r = porownanie.ratio()
        if r > best_ratio: best_ratio, best_match = r, (k_baza, info)
    if best_ratio > 0.89: return best_match
    return None, None

def dopasuj_mecz(mecz, polskie_kluby, nasz_slownik_lig, baza_lig, pamiec_druzyn=None):
    """Zwraca słownik z ligą i dopasowanymi klubami, jeśli mecz jest z udziałem Polaków
    (i nie jest odfiltrowany: drużyny rezerw/kobiece, ligi ignorowane), w przeciwnym razie None.
    pamiec_druzyn - słownik na wyniki dopasowania drużyn (ta sama drużyna gra w wielu meczach,
    a porównywanie nazwy z każdym klubem bazy jest kosztowne); czyścić po zmianie bazy."""
    gosp, gosc = mecz.get('home', {}).get('name', ''), mecz.get('away', {}).get('name', '')
    if czy_to_niechciana_druzyna(gosp) or czy_to_niechciana_druzyna(gosc): return None

    league_id = str(mecz.get('leagueId', mecz.get('tournament', {}).get('id', '')))
    dane_ze_slownika = nasz_slownik_lig.get(league_id, {})
    prawdziwa_nazwa = dane_ze_slownika.get("nazwa", f"Rozgrywki (ID: {league_id})")
    prawdziwa_flaga = dane_ze_slownika.get("flaga", "")
    prawdziwa_flaga = FLAGI_TRZYLITEROWE.get(prawdziwa_flaga, prawdziwa_flaga)
    # Ochrona przed brakiem kraju z API (np. Puchary Afryki)
    if not prawdziwa_flaga or prawdziwa_flaga == "none": prawdziwa_flaga = "int"

    info_uzytkownika = baza_lig.get(league_id, {})
    if info_uzytkownika.get('ignoruj', False): return None

    # Override z ligi.json liczy się tylko jeśli jest realną wartością, a nie starym
    # zaśmieconym placeholderem "Rozgrywki (ID: ...)" / pustym stringiem zapisanym kiedyś przez pomyłkę
    nazwa_override = info_uzytkownika.get('nazwa', '')
    if not nazwa_override or nazwa_override.startswith("Rozgrywki (ID:"): nazwa_override = ""
    flaga_override = info_uzytkownika.get('flaga', '')

    flaga_ligi = flaga_override or prawdziwa_flaga
    nazwa_ligi = nazwa_override or prawdziwa_nazwa
    if czy_liga_kobieca(nazwa_ligi): return None

    def klub(nazwa):
        if pamiec_druzyn is None: return dopasuj_klub_do_bazy(nazwa, flaga_ligi, polskie_kluby)
        klucz = (nazwa, flaga_ligi)
        if klucz not in pamiec_druzyn: pamiec_druzyn[klucz] = dopasuj_klub_do_bazy(nazwa, flaga_ligi, polskie_kluby)
        return pamiec_druzyn[klucz]

    klub_gosp, info_gosp = klub(gosp)
    klub_gosc, info_gosc = klub(gosc)
    if not (info_gosp or info_gosc): return None

    return {
        'gosp': gosp, 'gosc': gosc, 'league_id': league_id, 'znana_liga': bool(dane_ze_slownika),
        'nazwa_ligi': nazwa_ligi, 'flaga_ligi': flaga_ligi,
        'nazwa_override': nazwa_override, 'flaga_override': flaga_override,
        'polacy_gosp': info_gosp['gracze'] if info_gosp else [],
        'polacy_gosc': info_gosc['gracze'] if info_gosc else [],
        'klub_gosp': klub_gosp if info_gosp else None, 'klub_gosc': klub_gosc if info_gosc else None,
    }

def czas_rozpoczecia_utc(mecz):
    """Godzina rozpoczęcia meczu jako datetime w UTC albo None."""
    try:
        return pytz.utc.localize(datetime.strptime(mecz.get('status', {}).get('utcTime', '')[:19], "%Y-%m-%dT%H:%M:%S"))
    except Exception:
        return None

def _zawodnicy_skladu(sklady_api):
    for zespol in sklady_api:
        for z in zespol.get('starters', []) + zespol.get('subs', []) + zespol.get('unavailable', []):
            yield normalizuj_tekst(f"{z.get('firstName', '')} {z.get('lastName', '')}")

def jest_w_skladzie(sklady_api, gracz):
    """Czy gracz jest w składzie z API (także wśród rezerwowych / niedostępnych) - to samo porównanie
    nazwisk co w wyodrebnij_wystepy_polakow."""
    g = normalizuj_tekst(gracz)
    return any(z == g or podobienstwo(z, g) > 0.8 for z in _zawodnicy_skladu(sklady_api or []))

def wyodrebnij_wystepy_polakow(sklady_api, lista_polakow, oczekiwano_danych=False):
    """Występy Polaków w meczu na podstawie składów z API: dla każdego gracza słownik z kluczami
    nazwa, gole, asysty, minuty_tekst, ocena, aktywny (True grał / False nie grał / None nie wiadomo)."""
    if not sklady_api:
        if oczekiwano_danych:
            return [{'nazwa': p, 'gole': 0, 'asysty': 0, 'minuty_tekst': 'brak danych', 'ocena': None, 'aktywny': False} for p in lista_polakow]
        return [{'nazwa': p, 'gole': 0, 'asysty': 0, 'minuty_tekst': '', 'ocena': None, 'aktywny': None} for p in lista_polakow]

    # Dla części lig (np. K-League) API podaje gole/asysty, ale żadnych zmian ani ocen -
    # wtedy rezerwowy bez zdarzenia "subIn" mógł wejść na boisko, więc nie piszemy "nie grał"
    api_podaje_zmiany = any(
        z.get('performance', {}).get('substitutionEvents')
        for zespol in sklady_api for z in zespol.get('starters', []) + zespol.get('subs', []))

    wyniki = []
    for p_org in lista_polakow:
        p_norm = normalizuj_tekst(p_org)
        znaleziono = False
        for zespol in sklady_api:
            for z in zespol.get('starters', []) + zespol.get('subs', []) + zespol.get('unavailable', []):
                if normalizuj_tekst(f"{z.get('firstName', '')} {z.get('lastName', '')}") == p_norm or podobienstwo(normalizuj_tekst(f"{z.get('firstName', '')} {z.get('lastName', '')}"), p_norm) > 0.8:
                    znaleziono = True
                    perf = z.get('performance', {})
                    events = perf.get('events', [])
                    g, a = sum(1 for e in events if e.get('type') == 'goal'), sum(1 for e in events if e.get('type') == 'assist')

                    sub_in = next((e.get('time') for e in perf.get('substitutionEvents', []) if e.get('type') == 'subIn'), None)
                    sub_out = next((e.get('time') for e in perf.get('substitutionEvents', []) if e.get('type') == 'subOut'), None)

                    if z in zespol.get('starters', []):
                        minuty_tekst = f"do {sub_out}'" if sub_out else ("90'" if api_podaje_zmiany else "w podstawie")
                        aktywny = True
                    elif z in zespol.get('subs', []) and not api_podaje_zmiany:
                        minuty_tekst = "rezerwowy, brak danych o zmianach"
                        aktywny = None
                    elif z in zespol.get('subs', []):
                        if sub_in:
                            minuty_tekst = f"od {sub_in}' do {sub_out}'" if sub_out else f"od {sub_in}'"
                            aktywny = True
                        else:
                            minuty_tekst = "nie grał"
                            aktywny = False
                    else:
                        minuty_tekst = "nie grał"
                        aktywny = False

                    wyniki.append({
                        'nazwa': p_org, 'gole': g, 'asysty': a, 'minuty_tekst': minuty_tekst,
                        'ocena': perf.get('rating'), 'aktywny': aktywny
                    })
                    break
            if znaleziono: break

        if not znaleziono:
            wyniki.append({'nazwa': p_org, 'gole': 0, 'asysty': 0, 'minuty_tekst': 'nie grał', 'ocena': None, 'aktywny': False})

    return wyniki
