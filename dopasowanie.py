"""
Wspólna logika "który mecz jest z Polakami" - używana przez aplikację (test_flashscore.py)
i przez serwer (serwer.py, automatyczne odświeżanie meczów Polaków). Bez pandas/Tkinter,
żeby serwer pozostał lekki.
"""
import os
import re
import difflib
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
    'włochy': 'it', 'zjednoczone emiraty arabskie': 'ae', 'polska': 'pl'
}

SLOWA_KLUCZOWE_LIGI_KOBIECE = ("women", "female", "ladies", "kobiet", "femin", "frauen", "wsl")


def normalizuj_tekst(tekst): return unicodedata.normalize('NFKD', str(tekst)).encode('ASCII', 'ignore').decode('utf-8').lower().strip()

def wyczysc_nazwe_klubu(nazwa):
    n = normalizuj_tekst(nazwa)
    for fraza in ["1. fc ", "1.fc ", " fc", " sc", " fk", " afc"]:
        if n.endswith(fraza): n = n[:-len(fraza)].strip()
        elif n.startswith(fraza): n = n[len(fraza):].strip()
    return re.sub(r'\[.*?\]', '', n).strip()

def podobienstwo(a, b): return difflib.SequenceMatcher(None, wyczysc_nazwe_klubu(a), wyczysc_nazwe_klubu(b)).ratio()

def czy_liga_kobieca(nazwa_ligi):
    n = (nazwa_ligi or "").lower()
    return any(slowo in n for slowo in SLOWA_KLUCZOWE_LIGI_KOBIECE)

def czy_to_niechciana_druzyna(nazwa):
    n = nazwa.lower().strip()
    if "(w)" in n or " (w) " in n or n.endswith(" (w)") or n.endswith(" w") or "women" in n or "kobiety" in n: return True
    if "willem ii" in n: return False
    return bool(re.search(r'\b(b|ii|2)\b$', n) or " u2" in n or " u1" in n)

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
            return kod_z_excela == alpha2_z_api or alpha2_z_api in kod_z_excela or kod_z_excela in alpha2_z_api
        return True

    if norm_klub_api in baza_klubow:
        if weryfikuj_kraj(baza_klubow[norm_klub_api]): return norm_klub_api, baza_klubow[norm_klub_api]

    for k_baza, info in baza_klubow.items():
        if len(k_baza) >= 4 and len(norm_klub_api) >= 4 and (k_baza in norm_klub_api or norm_klub_api in k_baza):
            if weryfikuj_kraj(info): return k_baza, info

    best_match, best_ratio = None, 0
    for k_baza, info in baza_klubow.items():
        if not weryfikuj_kraj(info): continue
        r = podobienstwo(k_baza, norm_klub_api)
        if r > best_ratio: best_ratio, best_match = r, (k_baza, info)
    if best_ratio > 0.89: return best_match
    return None, None

def dopasuj_mecz(mecz, polskie_kluby, nasz_slownik_lig, baza_lig):
    """Zwraca słownik z ligą i dopasowanymi klubami, jeśli mecz jest z udziałem Polaków
    (i nie jest odfiltrowany: drużyny rezerw/kobiece, ligi ignorowane), w przeciwnym razie None."""
    gosp, gosc = mecz.get('home', {}).get('name', ''), mecz.get('away', {}).get('name', '')
    if czy_to_niechciana_druzyna(gosp) or czy_to_niechciana_druzyna(gosc): return None

    league_id = str(mecz.get('leagueId', mecz.get('tournament', {}).get('id', '')))
    dane_ze_slownika = nasz_slownik_lig.get(league_id, {})
    prawdziwa_nazwa = dane_ze_slownika.get("nazwa", f"Rozgrywki (ID: {league_id})")
    prawdziwa_flaga = dane_ze_slownika.get("flaga", "")
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

    _, info_gosp = dopasuj_klub_do_bazy(gosp, flaga_ligi, polskie_kluby)
    _, info_gosc = dopasuj_klub_do_bazy(gosc, flaga_ligi, polskie_kluby)
    if not (info_gosp or info_gosc): return None

    return {
        'gosp': gosp, 'gosc': gosc, 'league_id': league_id, 'znana_liga': bool(dane_ze_slownika),
        'nazwa_ligi': nazwa_ligi, 'flaga_ligi': flaga_ligi,
        'nazwa_override': nazwa_override, 'flaga_override': flaga_override,
        'polacy_gosp': info_gosp['gracze'] if info_gosp else [],
        'polacy_gosc': info_gosc['gracze'] if info_gosc else [],
    }

def czas_rozpoczecia_utc(mecz):
    """Godzina rozpoczęcia meczu jako datetime w UTC albo None."""
    try:
        return pytz.utc.localize(datetime.strptime(mecz.get('status', {}).get('utcTime', '')[:19], "%Y-%m-%dT%H:%M:%S"))
    except Exception:
        return None
