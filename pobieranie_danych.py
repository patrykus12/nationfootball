"""
Warstwa danych SERWERA (serwer.py) - jedyne miejsce, które rozmawia z RapidAPI.
Aplikacja desktopowa (test_flashscore.py) nie importuje tego pliku i nie zna
klucza API - pobiera wszystko z serwera.

Każde zapytanie do RapidAPI jest cache'owane na dysku z czasem ważności
(TTL), dzięki czemu niezależnie od liczby użytkowników to samo zapytanie
idzie do API najwyżej raz na kilkanaście minut.
"""
import os
import json
import time
import threading
import requests
from datetime import datetime, timedelta

import pytz

KATALOG_PROJEKTU = os.path.dirname(os.path.abspath(__file__))
# Na hostingu z trwałym dyskiem ustaw NF_KATALOG_DANYCH na zamontowany wolumen.
KATALOG_DANYCH = os.environ.get("NF_KATALOG_DANYCH", KATALOG_PROJEKTU)
KATALOG_SUROWYCH = os.path.join(KATALOG_DANYCH, "serwer_cache", "surowe")
KATALOG_SKLADOW = os.path.join(KATALOG_DANYCH, "serwer_cache", "sklady")
os.makedirs(KATALOG_SUROWYCH, exist_ok=True)
os.makedirs(KATALOG_SKLADOW, exist_ok=True)

EXCEL_PLIK = os.path.join(KATALOG_DANYCH, "zawodnicy.xlsx")
LIGI_PLIK = os.path.join(KATALOG_DANYCH, "ligi.json")
SLOWNIK_PLIK = os.path.join(KATALOG_DANYCH, "slownik_lig.json")

TZ_PL = pytz.timezone("Europe/Warsaw")


def _wczytaj_klucz_api():
    klucz = os.environ.get("RAPIDAPI_KEY", "").strip()
    if klucz: return klucz
    plik = os.path.join(KATALOG_PROJEKTU, "rapidapi_klucz.txt")  # lokalnie, poza repozytorium (.gitignore)
    if os.path.exists(plik):
        with open(plik, "r", encoding="utf-8") as f: return f.read().strip()
    raise RuntimeError("Brak klucza RapidAPI: ustaw zmienną RAPIDAPI_KEY albo utwórz plik rapidapi_klucz.txt")


API_KEY = _wczytaj_klucz_api()
API_HOST = "free-api-live-football-data.p.rapidapi.com"

# Czasy ważności cache (w minutach), do nadpisania zmiennymi środowiskowymi
TTL_AKTYWNE_DNI_MIN = int(os.environ.get("NF_TTL_AKTYWNE_MIN", 20))   # wczoraj/dziś/jutro
TTL_PRZYSZLE_DNI_MIN = int(os.environ.get("NF_TTL_PRZYSZLE_MIN", 360))
TTL_SKLADU_MIN = int(os.environ.get("NF_TTL_SKLADU_MIN", 15))         # mecz jeszcze trwa
DNI_PRZECHOWYWANIA = 16

CCODE_DO_ALPHA2 = {
    "eng": "gb-eng", "esp": "es", "ita": "it", "ger": "de", "fra": "fr", "pol": "pl",
    "ned": "nl", "por": "pt", "sco": "gb-sct", "wal": "gb-wls", "usa": "us", "jpn": "jp",
    "kor": "kr", "aus": "au", "aut": "at", "bel": "be", "cze": "cz", "den": "dk",
    "gre": "gr", "mex": "mx", "rou": "ro", "rus": "ru", "swe": "se", "sui": "ch",
    "tur": "tr", "ukr": "ua", "arg": "ar", "bra": "br", "chi": "cl", "col": "co",
    "uru": "uy", "cro": "hr", "srb": "rs", "svn": "si", "svk": "sk", "fin": "fi",
    "nor": "no", "irl": "ie", "nir": "gb-nir", "isl": "is", "isr": "il", "bul": "bg",
    "cyp": "cy", "ecu": "ec", "egy": "eg", "slv": "sv", "fro": "fo", "gha": "gh",
    "gua": "gt", "hon": "hn", "hun": "hu", "idn": "id", "irn": "ir", "irq": "iq",
    "kaz": "kz", "kuw": "kw", "lva": "lv", "ltu": "lt", "lux": "lu", "mkd": "mk",
    "mas": "my", "mda": "md", "mne": "me", "mar": "ma", "nzl": "nz", "nga": "ng",
    "pan": "pa", "par": "py", "per": "pe", "sin": "sg", "rsa": "za", "tan": "tz",
    "tha": "th", "tun": "tn", "uzb": "uz", "ven": "ve", "vie": "vn", "int": "int"
}

_blokady = {}
_blokada_slownika = threading.Lock()
_blokada_blokad = threading.Lock()


def blokada(klucz):
    """Osobna blokada na każdy zasób, żeby równoległe zapytania o to samo nie dublowały wywołań API."""
    with _blokada_blokad:
        return _blokady.setdefault(klucz, threading.Lock())


def zapisz_json_atomowo(sciezka, dane, wciecia=None):
    tymczasowy = sciezka + ".tmp"
    with open(tymczasowy, "w", encoding="utf-8") as f: json.dump(dane, f, ensure_ascii=False, indent=wciecia)
    os.replace(tymczasowy, sciezka)


def wczytaj_json(sciezka, domyslne=None):
    if os.path.exists(sciezka):
        try:
            with open(sciezka, "r", encoding="utf-8") as f: return json.load(f)
        except Exception: pass
    return domyslne


def _api_get(endpoint, params, timeout=20):
    res = requests.get(
        f"https://{API_HOST}/{endpoint}",
        headers={"x-rapidapi-key": API_KEY, "x-rapidapi-host": API_HOST},
        params=params, timeout=timeout,
    )
    res.raise_for_status()
    return res.json()


# --- SŁOWNIK LIG ---
def wczytaj_nasz_slownik():
    return wczytaj_json(SLOWNIK_PLIK, {}) or {}


def dopisz_do_slownika(nowe_ligi, nadpisz=False):
    if not nowe_ligi: return
    with _blokada_slownika:
        slownik = wczytaj_nasz_slownik()
        zmieniono = False
        for l_id, info in nowe_ligi.items():
            if nadpisz or l_id not in slownik:
                slownik[l_id] = info
                zmieniono = True
        if zmieniono: zapisz_json_atomowo(SLOWNIK_PLIK, slownik, wciecia=4)


def pobierz_wszystkie_ligi_z_api():
    """Pełna lista lig z API (jednorazowo, gdy słownik jest pusty)."""
    dane_json = _api_get("football-get-all-leagues-with-countries", {}, timeout=30)
    mapa_lig = {}
    for element in dane_json.get("response", {}).get("leagues", []):
        if "id" in element and "name" in element:
            kod = str(element.get("ccode", "int")).lower()
            mapa_lig[str(element["id"])] = {"nazwa": str(element["name"]), "flaga": CCODE_DO_ALPHA2.get(kod, kod)}
        kod = str(element.get("ccode", "")).lower()
        for liga in element.get("leagues", []):
            if "id" in liga and "name" in liga:
                mapa_lig[str(liga["id"])] = {"nazwa": str(liga["name"]), "flaga": CCODE_DO_ALPHA2.get(kod, kod)}
    dopisz_do_slownika(mapa_lig, nadpisz=True)
    return len(mapa_lig)


_nieudane_ligi = {}  # league_id -> czas ostatniej nieudanej próby


def liga_dla_meczu(league_id, mecz_id):
    """Nazwa/flaga ligi; jeśli nie ma jej w słowniku, doczytuje ze szczegółów meczu i zapamiętuje na stałe."""
    info = wczytaj_nasz_slownik().get(league_id)
    if info: return info
    if not mecz_id: return None
    with blokada(f"liga:{league_id}"):
        info = wczytaj_nasz_slownik().get(league_id)
        if info: return info
        if time.time() - _nieudane_ligi.get(league_id, 0) < 6 * 3600: return None
        try:
            detal = _api_get("football-get-match-detail", {"eventid": mecz_id}, timeout=10).get("response", {}).get("detail", {})
            nazwa = detal.get("leagueName", "")
            kod_kraju = str(detal.get("countryCode", "")).split("-")[0].lower()
        except Exception:
            nazwa = ""
        if not nazwa:
            _nieudane_ligi[league_id] = time.time()
            return None
        flaga = CCODE_DO_ALPHA2.get(kod_kraju, kod_kraju) if kod_kraju else "int"
        if not flaga or flaga == "none": flaga = "int"
        info = {"nazwa": nazwa, "flaga": flaga}
        dopisz_do_slownika({league_id: info})
        return info


# --- MECZE ---
def _ttl_dnia_api(data_api, pobrano_ts):
    """Czy surowe dane dla dnia API (date) wymagają ponownego pobrania."""
    dzis = datetime.now(TZ_PL).date()
    wiek_min = (time.time() - pobrano_ts) / 60
    if data_api > dzis + timedelta(days=1):
        return wiek_min > TTL_PRZYSZLE_DNI_MIN
    if data_api >= dzis - timedelta(days=1):
        return wiek_min > TTL_AKTYWNE_DNI_MIN
    # Dzień zamknięty: wystarczy, że raz pobraliśmy go po jego zakończeniu (+zapas na mecze po północy)
    granica = TZ_PL.localize(datetime.combine(data_api + timedelta(days=2), datetime.min.time())).timestamp()
    return pobrano_ts < granica


def _skanuj_odpowiedz(obj, mecze, ligi):
    if isinstance(obj, dict):
        l_id, l_name, l_ccode = None, "", ""
        if "league" in obj and isinstance(obj["league"], dict):
            l_id, l_name, l_ccode = str(obj["league"].get("id", "")), obj["league"].get("name", ""), obj["league"].get("ccode", "")
        elif "tournament" in obj and isinstance(obj["tournament"], dict):
            l_id, l_name = str(obj["tournament"].get("id", "")), obj["tournament"].get("name", "")
            l_ccode = obj["tournament"].get("category", {}).get("ccode", "")
        elif "id" in obj and "name" in obj and ("matches" in obj or "events" in obj):
            l_id, l_name = str(obj.get("id", "")), obj.get("name", "")
            l_ccode = obj.get("ccode", obj.get("category", {}).get("ccode", ""))
        if l_id and l_name and str(l_name).lower() not in ["matches", "events", "all"]:
            ligi[l_id] = {"nazwa": l_name, "flaga": str(l_ccode).lower()}
        if "home" in obj and "away" in obj and "status" in obj:
            mecze.append(obj)
        for v in obj.values(): _skanuj_odpowiedz(v, mecze, ligi)
    elif isinstance(obj, list):
        for e in obj: _skanuj_odpowiedz(e, mecze, ligi)


_nieudane_dni = {}  # "YYYYMMDD" -> czas ostatniej nieudanej próby


def surowe_mecze_dnia_api(data_api, pobrano_po=0):
    """Mecze z jednego dnia API (football-get-matches-by-date), z cache i TTL.
    pobrano_po (timestamp): wymuś ponowne pobranie, jeśli cache jest starszy niż ta chwila."""
    klucz = data_api.strftime("%Y%m%d")
    plik = os.path.join(KATALOG_SUROWYCH, f"{klucz}.json")
    with blokada(f"dzien:{klucz}"):
        cache = wczytaj_json(plik)
        if cache and cache["pobrano"] >= pobrano_po and not _ttl_dnia_api(data_api, cache["pobrano"]):
            return cache["mecze"]
        if time.time() - _nieudane_dni.get(klucz, 0) < TTL_AKTYWNE_DNI_MIN * 60:
            return cache["mecze"] if cache else []
        try:
            mecze, ligi = [], {}
            _skanuj_odpowiedz(_api_get("football-get-matches-by-date", {"date": klucz}), mecze, ligi)
        except Exception as e:
            print(f"[api] blad pobierania dnia {klucz}: {e}")
            mecze = []
        if not mecze:
            _nieudane_dni[klucz] = time.time()
            return cache["mecze"] if cache else []
        dopisz_do_slownika(ligi)
        zapisz_json_atomowo(plik, {"pobrano": time.time(), "mecze": mecze})
        return mecze


def mecze_dnia(data_pl):
    """Wszystkie mecze potencjalnie z danego dnia w polskim czasie (API liczy daty w innej strefie,
    więc sklejamy dzień poprzedni, bieżący i następny; aplikacja sama odfiltrowuje godziny)."""
    wszystkie = []
    for offset in (-1, 0, 1):
        wszystkie += surowe_mecze_dnia_api(data_pl + timedelta(days=offset))
    return list({m.get("id"): m for m in wszystkie if "id" in m}.values())


# --- SKŁADY ---
def sklad_druzyny(mecz_id, strona, zakonczony):
    """Skład jednej drużyny (strona = 'home' / 'away'). Po zakończeniu meczu cache jest ostateczny,
    w trakcie meczu odświeżany co TTL_SKLADU_MIN minut."""
    plik = os.path.join(KATALOG_SKLADOW, f"{mecz_id}_{strona}.json")
    with blokada(f"sklad:{mecz_id}:{strona}"):
        cache = wczytaj_json(plik)
        if cache and (cache["zakonczony"] or (not zakonczony and time.time() - cache["pobrano"] < TTL_SKLADU_MIN * 60)):
            return cache["sklad"]
        endpoint = "football-get-hometeam-lineup" if strona == "home" else "football-get-awayteam-lineup"
        try:
            sklad = _api_get(endpoint, {"eventid": mecz_id}, timeout=15).get("response", {}).get("lineup")
        except Exception as e:
            print(f"[api] blad pobierania skladu {mecz_id}/{strona}: {e}")
            return cache["sklad"] if cache else None
        if sklad is None and cache:
            return cache["sklad"]
        zapisz_json_atomowo(plik, {"pobrano": time.time(), "zakonczony": bool(zakonczony and sklad), "sklad": sklad})
        return sklad


def sklad_ostateczny(mecz_id, strona):
    cache = wczytaj_json(os.path.join(KATALOG_SKLADOW, f"{mecz_id}_{strona}.json"))
    return bool(cache and cache["zakonczony"])


# --- AUTOMATYCZNE ODŚWIEŻANIE MECZÓW POLAKÓW ---
# Po OPOZNIENIE_MIN minutach od rozpoczęcia meczu z Polakiem serwer sam pobiera wynik i składy,
# żeby były gotowe, zanim ktokolwiek kliknie "Pobierz Mecze". Jeśli mecz jeszcze trwa (dogrywka,
# opóźnienie), próbuje przy kolejnych uruchomieniach aż do OKNO_MIN minut od rozpoczęcia.
OPOZNIENIE_MIN = int(os.environ.get("NF_OPOZNIENIE_MIN", 150))
OKNO_MIN = int(os.environ.get("NF_OKNO_MIN", 360))
_blokada_odswiezania = threading.Lock()


def odswiez_mecze_polakow():
    """Zwraca listę opisów odświeżonych meczów (pustą, gdy nic nie było do zrobienia)."""
    if not _blokada_odswiezania.acquire(blocking=False):
        return ["(odświeżanie już trwa)"]
    try:
        from dopasowanie import wczytaj_kluby, dopasuj_mecz, czas_rozpoczecia_utc
        kluby = wczytaj_kluby(EXCEL_PLIK)
        if not kluby: return []
        slownik, ligi = wczytaj_nasz_slownik(), wczytaj_json(LIGI_PLIK, {}) or {}
        teraz = time.time()
        dzis = datetime.now(TZ_PL).date()
        raport = []

        for offset in (-1, 0, 1):
            data_api = dzis + timedelta(days=offset)
            cache = wczytaj_json(os.path.join(KATALOG_SUROWYCH, f"{data_api.strftime('%Y%m%d')}.json"))
            if cache: mecze = cache["mecze"]
            elif offset <= 0: mecze = surowe_mecze_dnia_api(data_api)
            else: continue

            do_odswiezenia = []  # (mecz_id, dopasowanie, chwila "rozpoczęcie + OPOZNIENIE")
            for mecz in mecze:
                start = czas_rozpoczecia_utc(mecz)
                if start is None or not (OPOZNIENIE_MIN <= (teraz - start.timestamp()) / 60 <= OKNO_MIN): continue
                dop = dopasuj_mecz(mecz, kluby, slownik, ligi)
                if not dop: continue
                if not dop['znana_liga'] and dop['league_id'].isdigit():
                    # Bez nazwy ligi nie wiemy, czy to np. liga kobieca (odfiltrowywana) - ustal ją
                    # PRZED pobieraniem składów i dopasuj mecz jeszcze raz
                    info = liga_dla_meczu(dop['league_id'], mecz.get('id'))
                    if info:
                        slownik[dop['league_id']] = info
                        dop = dopasuj_mecz(mecz, kluby, slownik, ligi)
                        if not dop: continue
                strony = [s for s, polacy in (("home", dop['polacy_gosp']), ("away", dop['polacy_gosc'])) if polacy]
                if all(sklad_ostateczny(mecz.get('id'), s) for s in strony): continue
                do_odswiezenia.append((mecz.get('id'), dop, strony, start.timestamp() + OPOZNIENIE_MIN * 60))
            if not do_odswiezenia: continue

            # Świeży wynik/status "zakończony" - dzień API pobrany po progu 2,5 h najpóźniejszego z tych meczów
            aktualne = {m.get('id'): m for m in surowe_mecze_dnia_api(data_api, pobrano_po=max(p for *_, p in do_odswiezenia))}
            for mecz_id, dop, strony, _ in do_odswiezenia:
                mecz = aktualne.get(mecz_id, {})
                zakonczony = bool(mecz.get('status', {}).get('finished', False))
                for strona in strony: sklad_druzyny(mecz_id, strona, zakonczony)
                raport.append(f"{dop['gosp']} - {dop['gosc']}: {'zakończony' if zakonczony else 'jeszcze trwa'}")
        return raport
    finally:
        _blokada_odswiezania.release()


def wyczysc_stary_cache():
    granica = time.time() - DNI_PRZECHOWYWANIA * 86400
    for katalog in (KATALOG_SUROWYCH, KATALOG_SKLADOW):
        for nazwa in os.listdir(katalog):
            sciezka = os.path.join(katalog, nazwa)
            try:
                if os.path.getmtime(sciezka) < granica: os.remove(sciezka)
            except Exception: pass
