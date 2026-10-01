import sys
import os
import traceback

# --- KATALOGI ---
# W spakowanym .exe (PyInstaller --onefile) kod rozpakowuje się do tymczasowego folderu _MEI...,
# więc dane użytkownika trzymamy w %LOCALAPPDATA%\NationFootball, a obrazki (tło, ikona) bierzemy z paczki.
if getattr(sys, "frozen", False):
    KATALOG_ZASOBOW = sys._MEIPASS
    KATALOG_PROJEKTU = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "NationFootball")
else:
    KATALOG_ZASOBOW = KATALOG_PROJEKTU = os.path.dirname(os.path.abspath(__file__))
os.makedirs(KATALOG_PROJEKTU, exist_ok=True)

# --- CZARNA SKRZYNKA ---
def crash_logger(exc_type, exc_value, exc_tb):
    log_path = os.path.join(KATALOG_PROJEKTU, "CRASH_LOG.txt")
    with open(log_path, "w", encoding="utf-8") as f:
        f.write("KRYTYCZNY BLAD APLIKACJI:\n")
        traceback.print_exception(exc_type, exc_value, exc_tb, file=f)
    sys.exit(1)

sys.excepthook = crash_logger

import json
import re
import requests
import time
from datetime import datetime, timedelta
import pytz
import tkinter as tk
from tkinter import messagebox
import tkinter.font as tkFont
from PIL import Image, ImageTk, ImageDraw

from dopasowanie import normalizuj_tekst, podobienstwo, wczytaj_kluby, dopasuj_mecz, czas_rozpoczecia_utc

# --- KONFIGURACJA ---
# Aplikacja nie łączy się z RapidAPI - wszystkie dane bierze z serwera NationFootball (serwer.py).
# Adres można nadpisać zmienną środowiskową NF_SERWER (np. http://127.0.0.1:5000 do testów z lokalnym serwer.py).
SERWER_URL = os.environ.get("NF_SERWER", "https://nationfootball.onrender.com").rstrip("/")
# Darmowe hostingi usypiają serwer po bezczynności - pierwsze zapytanie może czekać ~minutę
TIMEOUT_SERWERA = 90

EXCEL_PLIK = os.path.join(KATALOG_PROJEKTU, "zawodnicy.xlsx")
LIGI_PLIK = os.path.join(KATALOG_PROJEKTU, "ligi.json")
SLOWNIK_PLIK = os.path.join(KATALOG_PROJEKTU, "slownik_lig.json")
CACHE_DIR = os.path.join(KATALOG_PROJEKTU, "cache_sklady")
CACHE_FLAGI_DIR = os.path.join(KATALOG_PROJEKTU, "cache_flagi")
OBRAZ_TLO = os.path.join(KATALOG_ZASOBOW, "tlo.png")
IKONA = os.path.join(KATALOG_ZASOBOW, "ball.ico")

os.makedirs(CACHE_DIR, exist_ok=True)
os.makedirs(CACHE_FLAGI_DIR, exist_ok=True)

# FLAGI EMOTIKONY (Uwaga: w pliku archiwum.txt będą kolorowe, w GUI Windowsa wyświetlą się jako literki m.in. DE, NO)
FLAGI_EMOJI = {
    "gb-eng": "🏴󠁧󠁢󠁥󠁮󠁧󠁿", "es": "🇪🇸", "it": "🇮🇹", "de": "🇩🇪", "fr": "🇫🇷", "pl": "🇵🇱", 
    "nl": "🇳🇱", "pt": "🇵🇹", "gb-sct": "🏴󠁧󠁢󠁳󠁣󠁴󠁿", "gb-wls": "🏴󠁧󠁢󠁷󠁬󠁳󠁿", "us": "🇺🇸", 
    "jp": "🇯🇵", "kr": "🇰🇷", "cy": "🇨🇾", "au": "🇦🇺", "at": "🇦🇹", "az": "🇦🇿", 
    "be": "🇧🇪", "cz": "🇨🇿", "dk": "🇩🇰", "fi": "🇫🇮", "gi": "🇬🇮", "gr": "🇬🇷", 
    "id": "🇮🇩", "ie": "🇮🇪", "is": "🇮🇸", "ca": "🇨🇦", "lt": "🇱🇹", "md": "🇲🇩", 
    "no": "🇳🇴", "ro": "🇷🇴", "ch": "🇨🇭", "se": "🇸🇪", "sk": "🇸🇰", "tr": "🇹🇷", 
    "ua": "🇺🇦", "fo": "🇫🇴", "hu": "🇭🇺", "ae": "🇦🇪", "sa": "🇸🇦", "qa": "🇶🇦", 
    "hr": "🇭🇷", "rs": "🇷🇸", "en": "🏴󠁧󠁢󠁥󠁮󠁧󠁿", "gb": "🇬🇧", "uy": "🇺🇾",
    "eu": "🇪🇺", "un": "🌍", "il": "🇮🇱", "bg": "🇧🇬", "ee": "🇪🇪", "lv": "🇱🇻", 
    "kz": "🇰🇿", "uz": "🇺🇿", "in": "🇮🇳", "mt": "🇲🇹", "gb-nir": "🇬🇧", "si": "🇸🇮", "ba": "🇧🇦",
    "ec": "🇪🇨", "cn": "🇨🇳", "br": "🇧🇷", "int": "🌍"
}


# Kody, dla których serwis z flagami (flagcdn.com) nie ma osobnego pliku - mapujemy na najbliższy odpowiednik
ALIAS_KOD_OBRAZKA_FLAGI = {"int": "un", "none": "un", "": "un"}

def pobierz_plik_flagi(kod):
    """Zwraca ścieżkę do lokalnego PNG z flagą (zawsze 24x18), pobierając i cache'ując go przy pierwszym użyciu."""
    kod = (kod or "").lower().strip()
    kod = ALIAS_KOD_OBRAZKA_FLAGI.get(kod, kod)
    if not kod: return None

    sciezka = os.path.join(CACHE_FLAGI_DIR, f"{kod}.png")
    if os.path.exists(sciezka):
        # Zabezpieczenie przed starym, osieroconym cache w innym rozmiarze (np. 16x12) - dociągnij od nowa
        try:
            with Image.open(sciezka) as im:
                if im.size == (24, 18): return sciezka
        except Exception:
            pass

    try:
        res = requests.get(f"https://flagcdn.com/24x18/{kod}.png", timeout=6)
        if res.status_code == 200 and res.content:
            with open(sciezka, "wb") as f: f.write(res.content)
            return sciezka
    except Exception:
        pass
    return sciezka if os.path.exists(sciezka) else None

# --- KOMUNIKACJA Z SERWEREM ---
class BladSerwera(Exception): pass

def zapytaj_serwer(sciezka, params=None, timeout=TIMEOUT_SERWERA):
    """GET do serwera NationFootball. Zwraca obiekt requests.Response (200) albo None (404).
    Rzuca BladSerwera, gdy serwer jest nieosiągalny lub zwraca inny błąd."""
    try:
        res = requests.get(f"{SERWER_URL}{sciezka}", params=params, timeout=timeout)
    except requests.RequestException as e:
        raise BladSerwera(f"Brak połączenia z serwerem danych ({SERWER_URL}).\n{e}")
    if res.status_code == 404: return None
    if res.status_code != 200: raise BladSerwera(f"Serwer danych zwrócił błąd {res.status_code}.")
    return res

def zapisz_atomowo(sciezka, tresc_bajty):
    tymczasowy = sciezka + ".tmp"
    with open(tymczasowy, "wb") as f: f.write(tresc_bajty)
    # Windows potrafi chwilowo blokować plik (antywirus, inny proces czytający) - ponów kilka razy
    for proba in range(5):
        try:
            os.replace(tymczasowy, sciezka)
            return
        except PermissionError:
            if proba == 4: raise
            time.sleep(0.3)

def synchronizuj_bazy_z_serwera():
    """Pobiera z serwera bazę zawodników, słownik lig i ligi.json. Zwraca liczbę zaktualizowanych plików."""
    ile = 0
    for sciezka, plik in (("/zawodnicy", EXCEL_PLIK), ("/slownik-lig", SLOWNIK_PLIK), ("/ligi", LIGI_PLIK)):
        res = zapytaj_serwer(sciezka)
        if res is not None and res.content:
            zapisz_atomowo(plik, res.content)
            ile += 1
    return ile

# --- BAZA LOKALNA (kopie plików z serwera) ---
def _wczytaj_json(sciezka):
    if os.path.exists(sciezka):
        try:
            with open(sciezka, 'r', encoding='utf-8') as f: return json.load(f)
        except Exception: pass
    return {}

def wczytaj_ligi(): return _wczytaj_json(LIGI_PLIK)

def wczytaj_nasz_slownik(): return _wczytaj_json(SLOWNIK_PLIK)

def zapisz_nasz_slownik(slownik):
    with open(SLOWNIK_PLIK, 'w', encoding='utf-8') as f:
        json.dump(slownik, f, indent=4, ensure_ascii=False)

DNI_HISTORII_MECZY = 14  # ile dni wstecz trzymamy pliki mecze_YYYYMMDD.json
DNI_NAPRZOD_LIMIT = 14   # ile dni do przodu wolno przeglądać w GUI

def wyczysc_stare_pliki_meczy():
    """Usuwa pliki mecze_YYYYMMDD.json i archiwum_YYYY-MM-DD.txt starsze niż
    DNI_HISTORII_MECZY dni wstecz od dziś, a następnie czyści osierocone wpisy
    w cache_sklady (dotyczące meczów, których plik mecze_*.json już nie istnieje)."""
    dzis = datetime.now(pytz.timezone('Europe/Warsaw')).date()
    wzorzec_mecze = re.compile(r'^mecze_(\d{8})\.json$')
    wzorzec_archiwum = re.compile(r'^archiwum_(\d{4}-\d{2}-\d{2})\.txt$')
    zachowane_id = set()

    for nazwa in os.listdir(KATALOG_PROJEKTU):
        m = wzorzec_mecze.match(nazwa)
        if m:
            try:
                data_pliku = datetime.strptime(m.group(1), "%Y%m%d").date()
            except ValueError:
                continue
            sciezka = os.path.join(KATALOG_PROJEKTU, nazwa)
            if (dzis - data_pliku).days > DNI_HISTORII_MECZY:
                try: os.remove(sciezka)
                except Exception: pass
            else:
                try:
                    with open(sciezka, "r", encoding="utf-8") as f:
                        zachowane_id.update(str(mecz.get('id')) for mecz in json.load(f) if mecz.get('id') is not None)
                except Exception: pass
            continue

        m = wzorzec_archiwum.match(nazwa)
        if m:
            try:
                data_pliku = datetime.strptime(m.group(1), "%Y-%m-%d").date()
            except ValueError:
                continue
            if (dzis - data_pliku).days > DNI_HISTORII_MECZY:
                try: os.remove(os.path.join(KATALOG_PROJEKTU, nazwa))
                except Exception: pass

    if os.path.isdir(CACHE_DIR):
        for nazwa in os.listdir(CACHE_DIR):
            if nazwa.endswith(".json") and nazwa[:-5] not in zachowane_id:
                try: os.remove(os.path.join(CACHE_DIR, nazwa))
                except Exception: pass

# --- FUNKCJE LOGIKI BIZNESOWEJ ---
# (dopasowywanie klubów/meczów do bazy Polaków jest w dopasowanie.py - wspólne z serwerem)

def pobierz_lige_z_serwera(league_id, mecz_id):
    """Douczanie brakującej ligi (serwer sam sprawdza szczegóły meczu w API i zapamiętuje wynik dla wszystkich)."""
    try:
        res = zapytaj_serwer(f"/liga/{league_id}", params={"mecz": mecz_id}, timeout=20)
        return res.json() if res is not None else None
    except Exception:
        return None

def pobierz_sklad_z_serwera(mecz_id, czy_zakonczony, uzyj_serwera=False, fetch_home=True, fetch_away=True):
    plik_cache = os.path.join(CACHE_DIR, f"{mecz_id}.json")
    if os.path.exists(plik_cache):
        with open(plik_cache, "r", encoding="utf-8") as f: return json.load(f)
    if not uzyj_serwera: return []

    sklady, kompletne = [], True
    for strona, potrzebna in (("home", fetch_home), ("away", fetch_away)):
        if not potrzebna: continue
        try:
            res = zapytaj_serwer(f"/sklad/{mecz_id}/{strona}", params={"zakonczony": int(bool(czy_zakonczony))}, timeout=30)
            sklad = res.json().get("sklad") if res is not None else None
        except Exception:
            sklad = None
        if sklad: sklady.append(sklad)
        else: kompletne = False

    # Lokalnie zapamiętujemy na stałe tylko składy z zakończonych meczów - w trakcie meczu
    # statystyki jeszcze się zmieniają (serwer i tak trzyma swój cache odświeżany co kilkanaście minut)
    if sklady and kompletne and czy_zakonczony:
        with open(plik_cache, "w", encoding="utf-8") as f: json.dump(sklady, f)
    return sklady

def wyodrebnij_wystepy_polakow(sklady_api, lista_polakow, oczekiwano_danych=False):
    """Jak przeanalizuj_wystepy_polakow, ale zwraca dane w formie ustrukturyzowanej
    (do tabeli w GUI), zamiast gotowego tekstu (który dalej powstaje z tych danych
    dla pliku archiwum.txt - patrz _tekst_wystepu)."""
    if not sklady_api:
        if oczekiwano_danych:
            return [{'nazwa': p, 'gole': 0, 'asysty': 0, 'minuty_tekst': 'brak danych', 'ocena': None, 'aktywny': False} for p in lista_polakow]
        return [{'nazwa': p, 'gole': 0, 'asysty': 0, 'minuty_tekst': '', 'ocena': None, 'aktywny': None} for p in lista_polakow]

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
                        minuty_tekst = f"do {sub_out}'" if sub_out else "90'"
                        aktywny = True
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

def _tekst_wystepu(d):
    """Zamienia jeden wpis z wyodrebnij_wystepy_polakow na tekst w formacie archiwum.txt."""
    if d['aktywny'] is None: return d['nazwa']
    tekst = d['nazwa']
    if d['gole'] > 0: tekst += f" {d['gole']}x⚽" if d['gole'] > 1 else " ⚽"
    if d['asysty'] > 0: tekst += f" {d['asysty']}x🅰️" if d['asysty'] > 1 else " 🅰️"
    if d['minuty_tekst']: tekst += f" ({d['minuty_tekst']})"
    if d['ocena'] is not None: tekst += f" [ocena: {d['ocena']}]"
    return tekst

def przeanalizuj_wystepy_polakow(sklady_api, lista_polakow, oczekiwano_danych=False):
    dane = wyodrebnij_wystepy_polakow(sklady_api, lista_polakow, oczekiwano_danych)
    return ", ".join(_tekst_wystepu(d) for d in dane)

def przetworz_dane(data_obliczeniowa, wymus_aktualizacje=False):
    if wymus_aktualizacje:
        synchronizuj_bazy_z_serwera()
    polskie_kluby = wczytaj_kluby(EXCEL_PLIK)
    if not polskie_kluby: return ["Brak bazy zawodników.", "Kliknij '1. Pobierz Mecze', aby pobrać dane z serwera."], False
    
    baza_lig = wczytaj_ligi()
    nasz_slownik_lig = wczytaj_nasz_slownik() 
    zapisano_nowy_slownik = False
    
    tz_pl = pytz.timezone('Europe/Warsaw')
    now_utc = datetime.now(pytz.utc)
    
    data_str_pl = data_obliczeniowa.strftime("%Y-%m-%d")
    api_date_str = data_obliczeniowa.strftime("%Y%m%d")
    plik_meczy = os.path.join(KATALOG_PROJEKTU, f"mecze_{api_date_str}.json")
    
    potrzeba_aktualizacji = not os.path.exists(plik_meczy)
    wszystkie_mecze = []

    if wymus_aktualizacje:
        # Serwer sam decyduje, czy ma świeże dane w cache, czy musi dopytać API
        res = zapytaj_serwer(f"/mecze/{api_date_str}")
        if res is not None and res.content:
            zapisz_atomowo(plik_meczy, res.content)
            potrzeba_aktualizacji = True

    if os.path.exists(plik_meczy):
        with open(plik_meczy, "r", encoding="utf-8") as f: wszystkie_mecze = json.load(f)

    wyniki_gui = []
    
    for mecz in wszystkie_mecze:
        dopasowany = dopasuj_mecz(mecz, polskie_kluby, nasz_slownik_lig, baza_lig)
        if not dopasowany: continue
        gosp, gosc = dopasowany['gosp'], dopasowany['gosc']
        league_id = dopasowany['league_id']
        nazwa_ligi, flaga_ligi = dopasowany['nazwa_ligi'], dopasowany['flaga_ligi']
        polacy_gosp, polacy_gosc = dopasowany['polacy_gosp'], dopasowany['polacy_gosc']

        # Jeżeli mimo skanera i bazy lig wciąż nie znamy nazwy tej ligi - doczytaj ją 1:1 ze szczegółów meczu
        if not dopasowany['znana_liga'] and wymus_aktualizacje and league_id.isdigit():
            info_z_serwera = pobierz_lige_z_serwera(league_id, mecz.get('id'))
            if info_z_serwera and info_z_serwera.get("nazwa"):
                nasz_slownik_lig[league_id] = info_z_serwera
                zapisano_nowy_slownik = True
                if not dopasowany['nazwa_override']: nazwa_ligi = info_z_serwera["nazwa"]
                if not dopasowany['flaga_override']: flaga_ligi = info_z_serwera.get("flaga") or "int"

        dt_utc = czas_rozpoczecia_utc(mecz)
        if dt_utc is None: continue
        dt_pl = dt_utc.astimezone(tz_pl)
        if dt_pl.strftime("%Y-%m-%d") != data_str_pl: continue

        czy_zakonczony = mecz.get('status', {}).get('finished', False)
        minely_2h = (now_utc - dt_utc) > timedelta(hours=2)
        oczekiwano_danych = czy_zakonczony or minely_2h

        sklady = pobierz_sklad_z_serwera(mecz.get('id'), czy_zakonczony, uzyj_serwera=wymus_aktualizacje, fetch_home=bool(polacy_gosp), fetch_away=bool(polacy_gosc)) if oczekiwano_danych else []

        gracze_gosp = wyodrebnij_wystepy_polakow(sklady, polacy_gosp, oczekiwano_danych) if polacy_gosp else []
        gracze_gosc = wyodrebnij_wystepy_polakow(sklady, polacy_gosc, oczekiwano_danych) if polacy_gosc else []
        txt_p_gosp = ", ".join(_tekst_wystepu(d) for d in gracze_gosp)
        txt_p_gosc = ", ".join(_tekst_wystepu(d) for d in gracze_gosc)

        # POBRANIE EMOTIKONY FLAGI (Która w Windowsie zmieni się w kod regionalny)
        flaga_emoji = FLAGI_EMOJI.get(flaga_ligi.lower(), "")
        if not flaga_emoji and (flaga_ligi.lower() in ["europe", "world", "international", "int"]):
            flaga_emoji = FLAGI_EMOJI.get("eu") if "europ" in flaga_ligi.lower() else FLAGI_EMOJI.get("int")
            
        flaga_str = f"{flaga_emoji} " if flaga_emoji else ""
        
        wynik_str = mecz.get('status', {}).get('scoreStr', "").replace(" - ", ":") if czy_zakonczony else "vs"
        gosp_txt = f"{gosp} [{txt_p_gosp}]" if polacy_gosp else gosp
        gosc_txt = f"{gosc} [{txt_p_gosc}]" if polacy_gosc else gosc

        tresc_meczu = f"{nazwa_ligi} | {gosp_txt} {wynik_str} {gosc_txt}"
        # Do pliku archiwum.txt - z emotikoną (tam kolorowe flagi wyświetlają się poprawnie)
        tekst_archiwum = f"[{dt_pl.strftime('%H:%M')}] {flaga_str}{tresc_meczu}"
        # Do GUI - bez emotikony, flagę dorysujemy jako obrazek (patrz: get_flaga_photo)
        tekst_gui = f"[{dt_pl.strftime('%H:%M')}] {tresc_meczu}"
        wyniki_gui.append({
            'czas_obj': dt_pl, 'txt': tekst_gui, 'txt_archiwum': tekst_archiwum, 'flaga_kod': flaga_ligi.lower(),
            'godzina': dt_pl.strftime("%H:%M"), 'liga': nazwa_ligi, 'gospodarz': gosp, 'gosc': gosc,
            'wynik': wynik_str, 'zakonczony': czy_zakonczony,
            'gracze_gosp': gracze_gosp, 'gracze_gosc': gracze_gosc,
        })

    # Zapisywanie zaktualizowanego Skanerem Słownika
    if zapisano_nowy_slownik:
        zapisz_nasz_slownik(nasz_slownik_lig)

    wyniki_gui.sort(key=lambda x: x['czas_obj'])
    
    lista_txt = [w['txt_archiwum'] for w in wyniki_gui] if wyniki_gui else [f"Brak meczów Polaków z dnia {data_str_pl}."]
    with open(os.path.join(KATALOG_PROJEKTU, f"archiwum_{data_str_pl}.txt"), "w", encoding="utf-8") as f:
        f.write(f"NATION FOOTBALL - MECZE Z DNIA: {data_str_pl}\n" + "="*45 + "\n\n")
        f.write("\n\n".join(lista_txt))
        
    return wyniki_gui if wyniki_gui else None, potrzeba_aktualizacji

# --- INTERFEJS GRAFICZNY CM STYLE ---
class AplikacjaFootball:
    def __init__(self, root):
        self.root = root
        self.root.title("NationFootball")
        self.root.geometry("1150x750")
        
        if os.path.exists(IKONA):
            try: self.root.iconbitmap(IKONA)
            except: pass
        
        self.main_container = tk.Frame(root)
        self.main_container.pack(fill=tk.BOTH, expand=True)
        
        self.canvas = tk.Canvas(self.main_container, highlightthickness=0, bg="#0d1b2a")
        self.scrollbar = tk.Scrollbar(self.main_container, orient=tk.VERTICAL, command=self.canvas.yview)
        self.canvas.config(yscrollcommand=self.scrollbar.set)
        
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.canvas.bind_all("<MouseWheel>", self.on_mousewheel) 
        
        self.bg_image_raw = Image.open(OBRAZ_TLO) if os.path.exists(OBRAZ_TLO) else None
        self.current_date = datetime.now(pytz.timezone('Europe/Warsaw')).date()
        self.ostatnie_wyniki = []
        self.pokazuj_wyniki = False
        self.flag_photo_cache = {}
        self.badge_font = tkFont.Font(family="Segoe UI", size=8)

        # --- TABELA WYNIKÓW (zawartość odtwarzana przy każdym odświeżeniu) ---
        self.tabela_frame = tk.Frame(self.canvas, bg="#142436", highlightbackground="#2c3e50", highlightthickness=1)

        wyczysc_stare_pliki_meczy()

        self.canvas.bind("<Configure>", self.odswiez_widok)
        self.zmien_dzien()

    def on_mousewheel(self, event): self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")

    def get_flaga_photo(self, kod):
        """Zwraca ImageTk.PhotoImage z flagą danego kodu (pobierając/cache'ując w razie potrzeby), albo None."""
        kod_norm = (kod or "").lower().strip()
        if kod_norm in self.flag_photo_cache: return self.flag_photo_cache[kod_norm]

        photo = None
        sciezka = pobierz_plik_flagi(kod_norm)
        if sciezka:
            try: photo = ImageTk.PhotoImage(Image.open(sciezka).convert("RGBA"))
            except Exception: photo = None

        self.flag_photo_cache[kod_norm] = photo
        return photo

    def format_date(self):
        dzisiaj = datetime.now(pytz.timezone('Europe/Warsaw')).date()
        if self.current_date == dzisiaj: return f"DZISIAJ ({self.current_date.strftime('%d.%m.%Y')})"
        elif self.current_date == dzisiaj - timedelta(days=1): return f"WCZORAJ ({self.current_date.strftime('%d.%m.%Y')})"
        elif self.current_date == dzisiaj + timedelta(days=1): return f"JUTRO ({self.current_date.strftime('%d.%m.%Y')})"
        return self.current_date.strftime("%d.%m.%Y")
        
    def dzien_tyl(self):
        self.current_date -= timedelta(days=1)
        self.zmien_dzien()
        
    def dzien_przod(self):
        dzisiaj = datetime.now(pytz.timezone('Europe/Warsaw')).date()
        if self.current_date >= dzisiaj + timedelta(days=DNI_NAPRZOD_LIMIT):
            messagebox.showinfo("Limit", f"Mecze można sprawdzać maksymalnie {DNI_NAPRZOD_LIMIT} dni do przodu.")
            return
        self.current_date += timedelta(days=1)
        self.zmien_dzien()
        
    def zmien_dzien(self):
        dane_gui, _ = przetworz_dane(self.current_date, wymus_aktualizacje=False)
        if dane_gui is None: self.ostatnie_wyniki = ["Brak lokalnej bazy danych dla tego dnia.", "Kliknij '1. Pobierz Mecze', aby pobrać dane z serwera."]
        else: self.ostatnie_wyniki = dane_gui
        self.pokazuj_wyniki = True
        self.canvas.yview_moveto(0)
        self.odswiez_widok()

    def kliknij_pobierz_slownik(self):
        self.canvas.itemconfig("btn_dict_text", text="Łączenie z serwerem...")
        self.root.update()
        try:
            ile = synchronizuj_bazy_z_serwera()
            messagebox.showinfo("Gotowe", f"Pobrano z serwera aktualne bazy ({ile} pliki): zawodnicy, słownik lig, ustawienia lig.")
            self.zmien_dzien()
        except BladSerwera as e:
            messagebox.showerror("Błąd", f"Nie udało się pobrać baz z serwera.\n{e}")
        self.canvas.itemconfig("btn_dict_text", text="2. Odśwież Bazy")

    def kliknij_generuj(self):
        self.canvas.itemconfig("btn_text", text="Łączenie z serwerem...")
        self.root.update()
        try:
            dane_gui, _ = przetworz_dane(self.current_date, wymus_aktualizacje=True)
            self.ostatnie_wyniki = dane_gui if dane_gui else [f"Brak meczów Polaków z dnia {self.current_date.strftime('%d.%m.%Y')}."]
            self.pokazuj_wyniki = True
            self.canvas.yview_moveto(0)
            self.odswiez_widok()
        except BladSerwera as e: messagebox.showerror("Serwer niedostępny", str(e))
        except Exception as e: messagebox.showerror("Błąd", str(e))
        self.canvas.itemconfig("btn_text", text="1. Pobierz Mecze")

    def _skrot_klubu(self, nazwa):
        if not nazwa: return ""
        pierwszy_czlon = nazwa.split(" ")[0]
        rdzen = pierwszy_czlon.rstrip(".")
        # Pierwszy człon jest liczbą (np. "1.") albo zbyt krótki/ogólnikowy (FC, St, RW...) -
        # w takich przypadkach pokaż pełną nazwę klubu, żeby było wiadomo o jaki klub chodzi.
        if rdzen.isdigit() or len(rdzen) <= 3:
            return nazwa
        return pierwszy_czlon

    def _kolor_oceny(self, ocena):
        if ocena is None: return "#7f95ab"
        if ocena >= 7.5: return "#2ecc71"
        if ocena >= 6.5: return "#f1c40f"
        return "#e74c3c"

    def _skonfiguruj_kolumny(self, ramka):
        ramka.grid_columnconfigure(0, minsize=64)
        ramka.grid_columnconfigure(1, minsize=190)
        ramka.grid_columnconfigure(2, minsize=280)
        ramka.grid_columnconfigure(3, minsize=90)
        ramka.grid_columnconfigure(4, weight=1, minsize=200)

    def _szacuj_szerokosc_plakietki(self, klub, gracz):
        tekst = f"{klub} {gracz['nazwa']}"
        if gracz['gole'] == 1: tekst += " ⚽"
        elif gracz['gole'] > 1: tekst += f" {gracz['gole']}x⚽"
        if gracz['asysty'] == 1: tekst += " 🅰️"
        elif gracz['asysty'] > 1: tekst += f" {gracz['asysty']}x🅰️"
        if gracz['minuty_tekst']: tekst += f" {gracz['minuty_tekst']}"
        if gracz['ocena'] is not None: tekst += f" {gracz['ocena']:.1f}"
        return self.badge_font.measure(tekst) + 36

    def _zbuduj_plakietke(self, rodzic, klub, gracz):
        ramka = tk.Frame(rodzic, bg="#24344a", highlightbackground="#3a5068", highlightthickness=1)
        tk.Label(ramka, text=klub, bg="#24344a", fg="#f1c40f", font=("Segoe UI", 8, "bold")).pack(side=tk.LEFT, padx=(6, 3), pady=3)

        aktywny = gracz['aktywny']
        kolor_imienia = "#9aa8b8" if aktywny is False else "#f4f6f7"
        styl_imienia = ("Segoe UI", 8, "italic") if aktywny is False else ("Segoe UI", 8, "bold")
        tk.Label(ramka, text=gracz['nazwa'], bg="#24344a", fg=kolor_imienia, font=styl_imienia).pack(side=tk.LEFT, pady=3)

        ikony = ""
        if gracz['gole'] == 1: ikony += "⚽"
        elif gracz['gole'] > 1: ikony += f"{gracz['gole']}x⚽"
        if gracz['asysty']:
            if ikony: ikony += " "
            ikony += "🅰️" if gracz['asysty'] == 1 else f"{gracz['asysty']}x🅰️"
        if ikony:
            tk.Label(ramka, text=ikony, bg="#24344a", fg="#f4f6f7", font=("Segoe UI Emoji", 8)).pack(side=tk.LEFT, padx=3, pady=3)

        if gracz['minuty_tekst']:
            tk.Label(ramka, text=gracz['minuty_tekst'], bg="#24344a", fg="#8a9db3", font=("Segoe UI", 7)).pack(side=tk.LEFT, padx=3, pady=3)

        if gracz['ocena'] is not None:
            tk.Label(ramka, text=f"{gracz['ocena']:.1f}", bg="#24344a", fg=self._kolor_oceny(gracz['ocena']),
                     font=("Segoe UI", 8, "bold")).pack(side=tk.LEFT, padx=(3, 6), pady=3)
        else:
            tk.Frame(ramka, bg="#24344a", width=6).pack(side=tk.LEFT)

        return ramka

    def _zbuduj_komorke_graczy(self, rodzic, klub_gosp, gracze_gosp, klub_gosc, gracze_gosc, szerokosc_docelowa, bg):
        kontener = tk.Frame(rodzic, bg=bg)
        wszyscy = [(klub_gosp, g) for g in gracze_gosp] + [(klub_gosc, g) for g in gracze_gosc]

        if not wszyscy:
            tk.Label(kontener, text="—", bg=bg, fg="#5d7086", font=("Segoe UI", 9)).pack(anchor="w")
            return kontener

        linia = tk.Frame(kontener, bg=bg)
        linia.pack(anchor="w", fill=tk.X)
        szerokosc_biezaca = 0

        for klub, gracz in wszyscy:
            szerokosc = self._szacuj_szerokosc_plakietki(klub, gracz)
            if szerokosc_biezaca > 0 and szerokosc_biezaca + szerokosc > szerokosc_docelowa:
                linia = tk.Frame(kontener, bg=bg)
                linia.pack(anchor="w", fill=tk.X, pady=(4, 0))
                szerokosc_biezaca = 0
            plakietka = self._zbuduj_plakietke(linia, klub, gracz)
            plakietka.pack(side=tk.LEFT, padx=(0, 6))
            szerokosc_biezaca += szerokosc + 6

        return kontener

    def _wypelnij_tabele(self):
        for dziecko in self.tabela_frame.winfo_children():
            dziecko.destroy()

        if not self.pokazuj_wyniki:
            return

        if self.ostatnie_wyniki and isinstance(self.ostatnie_wyniki[0], str):
            for komunikat in self.ostatnie_wyniki:
                tk.Label(self.tabela_frame, text=komunikat, bg="#142436", fg="#e74c3c", font=("Segoe UI", 11, "bold"),
                         wraplength=max(self._szer_tabeli - 20, 200), pady=16).pack(fill=tk.X)
            return

        naglowek = tk.Frame(self.tabela_frame, bg="#1b263b")
        naglowek.pack(fill=tk.X)
        self._skonfiguruj_kolumny(naglowek)
        for i, (tekst, wyr) in enumerate([("GODZ.", "w"), ("LIGA", "w"), ("MECZ", "w"), ("WYNIK", "center"), ("POLSCY PIŁKARZE", "w")]):
            tk.Label(naglowek, text=tekst, bg="#1b263b", fg="#f1c40f", font=("Segoe UI", 8, "bold")
                     ).grid(row=0, column=i, sticky=("n" if wyr == "center" else "nw"), padx=10, pady=8)

        for m in self.ostatnie_wyniki:
            bg = "#142436"
            wiersz = tk.Frame(self.tabela_frame, bg=bg)
            wiersz.pack(fill=tk.X)
            self._skonfiguruj_kolumny(wiersz)

            tk.Label(wiersz, text=m['godzina'], bg=bg, fg="#ecf0f1", font=("Segoe UI", 9, "bold")
                     ).grid(row=0, column=0, sticky="nw", padx=10, pady=8)

            komorka_liga = tk.Frame(wiersz, bg=bg)
            komorka_liga.grid(row=0, column=1, sticky="new", padx=10, pady=8)
            flaga_photo = self.get_flaga_photo(m.get('flaga_kod'))
            if flaga_photo:
                tk.Label(komorka_liga, image=flaga_photo, bg=bg).pack(side=tk.LEFT, padx=(0, 6))
            tk.Label(komorka_liga, text=m['liga'], bg=bg, fg="#bcccdc", font=("Segoe UI", 9),
                     wraplength=170, justify=tk.LEFT, anchor="w").pack(side=tk.LEFT, fill=tk.X)

            tk.Label(wiersz, text=f"{m['gospodarz']} – {m['gosc']}", bg=bg, fg="#ecf0f1", font=("Segoe UI", 9),
                     wraplength=280, justify=tk.LEFT, anchor="w").grid(row=0, column=2, sticky="nw", padx=10, pady=8)

            komorka_wynik = tk.Frame(wiersz, bg=bg)
            komorka_wynik.grid(row=0, column=3, sticky="new", padx=10, pady=8)
            chip_bg = "#0d1b2a" if m['zakonczony'] else "#1b263b"
            chip_fg = "#f1c40f" if m['zakonczony'] else "#7f95ab"
            tk.Label(komorka_wynik, text=m['wynik'], bg=chip_bg, fg=chip_fg, font=("Segoe UI", 10, "bold"),
                     padx=10, pady=2).pack()

            komorka_graczy = self._zbuduj_komorke_graczy(
                wiersz, self._skrot_klubu(m['gospodarz']), m['gracze_gosp'],
                self._skrot_klubu(m['gosc']), m['gracze_gosc'], self._szer_graczy, bg
            )
            komorka_graczy.grid(row=0, column=4, sticky="new", padx=10, pady=8)

            tk.Frame(self.tabela_frame, bg="#1e2f45", height=1).pack(fill=tk.X)

    def odswiez_widok(self, event=None):
        w = self.canvas.winfo_width()
        h = max(self.canvas.winfo_height(), 600)
        if w < 10 or h < 10: return

        self._szer_tabeli = max(w - 40, 400)
        self._szer_graczy = max(self._szer_tabeli - (64 + 190 + 280 + 90) - 60, 220)
        self._ostatnie_w = w

        y_tabeli = 195
        self._wypelnij_tabele()
        self.tabela_frame.update_idletasks()
        self._y_tabeli = y_tabeli
        wysokosc_tabeli = self.tabela_frame.winfo_reqheight() if self.pokazuj_wyniki else 0

        total_height = max(h, y_tabeli + wysokosc_tabeli + 40)
        self._ostatnie_h = total_height
        self.canvas.config(scrollregion=(0, 0, w, total_height))

        full_img = Image.new("RGBA", (w, total_height), (15, 23, 42, 255))
        if self.bg_image_raw:
            bg_ratio = self.bg_image_raw.width / self.bg_image_raw.height
            new_w = int(total_height * bg_ratio)
            if new_w >= w:
                resized_bg = self.bg_image_raw.resize((new_w, total_height), Image.Resampling.LANCZOS)
                left = (new_w - w) // 2
                resized_bg = resized_bg.crop((left, 0, left + w, total_height))
            else:
                new_h = int(w / bg_ratio)
                if new_h >= total_height:
                    resized_bg = self.bg_image_raw.resize((w, new_h), Image.Resampling.LANCZOS)
                    resized_bg = resized_bg.crop((0, 0, w, total_height))
                else:
                    new_w2 = int(total_height * bg_ratio)
                    resized_bg = self.bg_image_raw.resize((new_w2, total_height), Image.Resampling.LANCZOS)
                    left = (new_w2 - w) // 2
                    resized_bg = resized_bg.crop((left, 0, left + w, total_height))
            full_img.paste(resized_bg, (0, 0))
            
        if self.pokazuj_wyniki:
            overlay = Image.new("RGBA", (w, total_height), (0, 0, 0, 0))
            draw = ImageDraw.Draw(overlay)
            draw.rectangle([20, 170, w-20, y_tabeli + wysokosc_tabeli + 20], fill=(15, 23, 42, 210), outline=(241, 196, 15, 220), width=2)
            full_img.paste(overlay, (0, 0), overlay)
            
        self.bg_image_tk = ImageTk.PhotoImage(full_img)
        self.canvas.delete("all")
        self.canvas.create_image(0, 0, image=self.bg_image_tk, anchor=tk.NW)

        self.canvas.create_rectangle(w//2 - 270, 20, w//2 + 270, 100, fill="#1b263b", outline="#34495e", width=3)
        self.canvas.create_text(w//2, 45, text="NATION FOOTBALL", font=("Arial", 16, "bold"), fill="#f1c40f")
        self.canvas.create_text(w//2, 75, text=self.format_date(), font=("Arial", 12, "bold"), fill="#ecf0f1")
        
        btn_y = 75
        dzisiaj = datetime.now(pytz.timezone('Europe/Warsaw')).date()
        czy_limit_dalej = self.current_date >= dzisiaj + timedelta(days=DNI_NAPRZOD_LIMIT)

        self.canvas.create_rectangle(w//2 - 240, btn_y - 12, w//2 - 200, btn_y + 12, fill="#34495e", outline="#2c3e50")
        self.canvas.create_text(w//2 - 220, btn_y, text="◄", font=("Arial", 12, "bold"), fill="white", tags="btn_prev")

        self.canvas.create_rectangle(w//2 + 200, btn_y - 12, w//2 + 240, btn_y + 12, fill=("#4a4a4a" if czy_limit_dalej else "#34495e"), outline="#2c3e50")
        self.canvas.create_text(w//2 + 220, btn_y, text="►", font=("Arial", 12, "bold"), fill=("#8a8a8a" if czy_limit_dalej else "white"), tags="btn_next")

        self.canvas.create_rectangle(w//2 - 270, 115, w//2 - 5, 145, fill="#c0392b", outline="#e74c3c", tags="btn_gen_bg")
        self.canvas.create_text(w//2 - 137, 130, text="1. Pobierz Mecze", font=("Arial", 9, "bold"), fill="white", tags="btn_text")

        self.canvas.create_rectangle(w//2 + 5, 115, w//2 + 270, 145, fill="#2980b9", outline="#3498db", tags="btn_dict_bg")
        self.canvas.create_text(w//2 + 137, 130, text="2. Odśwież Bazy", font=("Arial", 9, "bold"), fill="white", tags="btn_dict_text")

        self.canvas.tag_bind("btn_prev", "<Button-1>", lambda e: self.dzien_tyl())
        self.canvas.tag_bind("btn_next", "<Button-1>", lambda e: self.dzien_przod())
        self.canvas.tag_bind("btn_gen_bg", "<Button-1>", lambda e: self.kliknij_generuj())
        self.canvas.tag_bind("btn_text", "<Button-1>", lambda e: self.kliknij_generuj())

        self.canvas.tag_bind("btn_dict_bg", "<Button-1>", lambda e: self.kliknij_pobierz_slownik())
        self.canvas.tag_bind("btn_dict_text", "<Button-1>", lambda e: self.kliknij_pobierz_slownik())

        if self.pokazuj_wyniki:
            self.canvas.create_window(w // 2, y_tabeli, window=self.tabela_frame, anchor="n", width=self._szer_tabeli)

if __name__ == "__main__":
    root = tk.Tk()
    app = AplikacjaFootball(root)
    root.mainloop()