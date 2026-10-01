"""
Warstwa danych SERWERA (serwer.py) - jedyne miejsce, które rozmawia z RapidAPI.

Zasada: zapytania użytkowników NIGDY nie wywołują API. Adresy dla aplikacji czytają tylko
gotowe dane z dysku serwera (funkcje *_z_cache). API odpytuje wyłącznie harmonogram
(cykl_harmonogramu, uruchamiany co kilka minut), i to w wymaganym minimum:
  - terminarz dnia (lista meczów): każdy dzień z okna -15..+15 dni raz; dziś i dni przyszłe
    ponownie raz na dobę (zmiany godzin), dni przeszłe już nigdy,
  - mecz z Polakiem: ~2,5 h po rozpoczęciu (gdy już się skończył) jeden raz świeży wynik
    i składy drużyn z Polakami - potem dane są ostateczne i nie są już pobierane,
  - nazwa ligi: raz, tylko dla nieznanej ligi meczu z Polakiem.
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

OKNO_DNI = 15                                                     # zakres terminarza: dziś -/+ tyle dni
ODSWIEZANIE_TERMINARZA_H = 24                                     # dziś/przyszłe dni: raz na dobę
OPOZNIENIE_MIN = int(os.environ.get("NF_OPOZNIENIE_MIN", 150))    # pobierz mecz Polaka 2,5 h po rozpoczęciu
OKNO_MIN = int(os.environ.get("NF_OKNO_MIN", 360))                # mecz wciąż "trwa" - czekaj max do 6 h
PONOW_TRWAJACY_MIN = 20                                           # co ile sprawdzać mecz, który się przedłuża
LIMIT_SKLADOW_NA_CYKL = 40                                        # uzupełnianie zaległości po restarcie - porcjami
DNI_PRZECHOWYWANIA_SKLADOW = 17

# Baza zawodników / ligi.json są w repozytorium GitHub - serwer sam je stamtąd dociąga, więc
# cotygodniowa aktualizacja bazy nie wymaga restartu serwera (a restart = utrata cache na
# darmowym Renderze). Na Renderze włączone domyślnie, lokalnie wyłączone (nie nadpisuje plików).
REPO_RAW = os.environ.get("NF_REPO_RAW", "https://raw.githubusercontent.com/patrykus12/nationfootball/main"
                          if os.environ.get("RENDER") else "").rstrip("/")
SYNC_REPO_H = 6

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

_blokada_slownika = threading.Lock()
_blokada_harmonogramu = threading.Lock()

# Licznik zapytań do API od startu serwera (podgląd na stronie głównej serwera)
STATYSTYKI = {"start": time.time(), "zapytania_api": 0, "pozostalo_w_limicie": None,
              "ostatni_cykl": None, "ostatnia_synchronizacja_repo": None,
              "etap": "oczekiwanie", "ostatni_blad": None}


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
    """JEDYNE miejsce wywołujące RapidAPI. Używane tylko przez harmonogram."""
    STATYSTYKI["zapytania_api"] += 1
    res = requests.get(
        f"https://{API_HOST}/{endpoint}",
        headers={"x-rapidapi-key": API_KEY, "x-rapidapi-host": API_HOST},
        params=params, timeout=timeout,
    )
    pozostalo = res.headers.get("x-ratelimit-requests-remaining")
    if pozostalo is not None: STATYSTYKI["pozostalo_w_limicie"] = int(pozostalo)
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


def _pobierz_lige_z_api(league_id, mecz_id):
    """Nazwa/flaga nieznanej ligi ze szczegółów meczu - zapamiętywana na stałe w słowniku."""
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


# --- TERMINARZE (listy meczów dnia) ---
def _plik_dnia(data_api):
    return os.path.join(KATALOG_SUROWYCH, f"{data_api.strftime('%Y%m%d')}.json")


def surowe_z_cache(data_api):
    return wczytaj_json(_plik_dnia(data_api))


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


def _pobierz_dzien_z_api(data_api):
    """Terminarz jednego dnia API (1 zapytanie). Zwraca listę meczów albo None przy błędzie."""
    klucz = data_api.strftime("%Y%m%d")
    if time.time() - _nieudane_dni.get(klucz, 0) < 30 * 60: return None
    try:
        mecze, ligi = [], {}
        _skanuj_odpowiedz(_api_get("football-get-matches-by-date", {"date": klucz}), mecze, ligi)
    except Exception as e:
        print(f"[api] blad pobierania dnia {klucz}: {e}")
        mecze = []
    if not mecze:
        _nieudane_dni[klucz] = time.time()
        return None
    dopisz_do_slownika(ligi)
    zapisz_json_atomowo(_plik_dnia(data_api), {"pobrano": time.time(), "mecze": mecze})
    return mecze


def mecze_dnia_z_cache(data_pl):
    """Mecze potencjalnie z danego dnia w polskim czasie (API liczy daty w innej strefie, więc
    sklejamy dzień poprzedni, bieżący i następny; aplikacja sama odfiltrowuje godziny).
    Zwraca None, jeśli serwer nie ma jeszcze żadnych danych dla tego dnia."""
    wszystkie, cokolwiek = [], False
    for offset in (-1, 0, 1):
        cache = surowe_z_cache(data_pl + timedelta(days=offset))
        if cache:
            cokolwiek = True
            wszystkie += cache["mecze"]
    if not cokolwiek: return None
    return list({m.get("id"): m for m in wszystkie if "id" in m}.values())


# --- SKŁADY ---
def _plik_skladu(mecz_id, strona):
    return os.path.join(KATALOG_SKLADOW, f"{mecz_id}_{strona}.json")


def sklad_z_cache(mecz_id, strona):
    cache = wczytaj_json(_plik_skladu(mecz_id, strona))
    return cache["sklad"] if cache else None


def sklad_ostateczny(mecz_id, strona):
    cache = wczytaj_json(_plik_skladu(mecz_id, strona))
    return bool(cache and cache["zakonczony"])


def _pobierz_sklad_z_api(mecz_id, strona):
    """Ostateczny skład jednej drużyny po meczu (1 zapytanie). Zapisywany na stałe - także pusty,
    gdy API go nie ma (np. mecz odwołany), żeby nie ponawiać w nieskończoność."""
    endpoint = "football-get-hometeam-lineup" if strona == "home" else "football-get-awayteam-lineup"
    try:
        sklad = _api_get(endpoint, {"eventid": mecz_id}, timeout=15).get("response", {}).get("lineup")
    except Exception as e:
        print(f"[api] blad pobierania skladu {mecz_id}/{strona}: {e}")
        return False
    zapisz_json_atomowo(_plik_skladu(mecz_id, strona), {"pobrano": time.time(), "zakonczony": True, "sklad": sklad})
    return True


# --- SYNCHRONIZACJA BAZ Z REPOZYTORIUM ---
def synchronizuj_z_repo():
    """Dociąga z GitHuba zawodnicy.xlsx i ligi.json (podmienia, jeśli się zmieniły) oraz dopisuje
    do słownika ligi z repozytorium, których serwer nie zna. Zwraca listę zmienionych plików."""
    if not REPO_RAW: return []
    from dopasowanie import wczytaj_kluby
    zmienione = []
    try:
        res = requests.get(f"{REPO_RAW}/zawodnicy.xlsx", timeout=30)
        if res.status_code == 200 and res.content:
            obecny = open(EXCEL_PLIK, "rb").read() if os.path.exists(EXCEL_PLIK) else b""
            if res.content != obecny:
                tymczasowy = EXCEL_PLIK + ".nowy.xlsx"
                with open(tymczasowy, "wb") as f: f.write(res.content)
                if wczytaj_kluby(tymczasowy):
                    os.replace(tymczasowy, EXCEL_PLIK)
                    zmienione.append("zawodnicy.xlsx")
                else:
                    os.remove(tymczasowy)

        res = requests.get(f"{REPO_RAW}/ligi.json", timeout=30)
        if res.status_code == 200 and isinstance(res.json(), dict):
            obecny = open(LIGI_PLIK, "rb").read() if os.path.exists(LIGI_PLIK) else b""
            if res.content != obecny:
                with open(LIGI_PLIK + ".tmp", "wb") as f: f.write(res.content)
                os.replace(LIGI_PLIK + ".tmp", LIGI_PLIK)
                zmienione.append("ligi.json")

        res = requests.get(f"{REPO_RAW}/slownik_lig.json", timeout=30)
        if res.status_code == 200 and isinstance(res.json(), dict):
            znane = wczytaj_nasz_slownik()
            nowe = {k: v for k, v in res.json().items() if k not in znane}
            if nowe:
                dopisz_do_slownika(nowe)
                zmienione.append(f"slownik_lig.json (+{len(nowe)})")
    except Exception as e:
        print(f"[repo] blad synchronizacji: {e}")
    STATYSTYKI["ostatnia_synchronizacja_repo"] = time.time()
    if zmienione: _gotowe_mecze.clear()  # nowa baza zawodników -> przejrzyj mecze od nowa
    return zmienione


# --- HARMONOGRAM ---
_gotowe_mecze = set()      # id meczów już załatwionych (bez Polaków albo z ostatecznymi składami)
_cache_dopasowan = {}      # (mecz_id, czy_liga_znana, wersja_bazy) -> wynik dopasuj_mecz


def _odswiez_terminarze(raport):
    dzis = datetime.now(TZ_PL).date()
    for offset in range(-OKNO_DNI - 1, OKNO_DNI + 2):
        data_api = dzis + timedelta(days=offset)
        cache = surowe_z_cache(data_api)
        if cache is None:
            powod = "brak"
        elif data_api >= dzis and time.time() - cache["pobrano"] > ODSWIEZANIE_TERMINARZA_H * 3600:
            powod = "aktualizacja"
        else:
            continue
        if _pobierz_dzien_z_api(data_api) is not None:
            raport.append(f"terminarz {data_api} ({powod})")


def _odswiez_mecze_polakow(raport):
    from dopasowanie import wczytaj_kluby, dopasuj_mecz, czas_rozpoczecia_utc
    kluby = wczytaj_kluby(EXCEL_PLIK)
    if not kluby: return
    wersja_bazy = os.path.getmtime(EXCEL_PLIK)
    slownik, ligi = wczytaj_nasz_slownik(), wczytaj_json(LIGI_PLIK, {}) or {}
    teraz = time.time()
    dzis = datetime.now(TZ_PL).date()
    pobrane_sklady = 0

    def dopasuj(mecz):
        klucz = (mecz.get('id'), str(mecz.get('leagueId', '')) in slownik, wersja_bazy)
        if klucz not in _cache_dopasowan:
            _cache_dopasowan[klucz] = dopasuj_mecz(mecz, kluby, slownik, ligi)
        return _cache_dopasowan[klucz]

    for offset in range(-OKNO_DNI - 1, 2):
        data_api = dzis + timedelta(days=offset)
        cache = surowe_z_cache(data_api)
        if not cache: continue

        do_zrobienia = []  # (mecz_id, dopasowanie, strony, wiek_min)
        for mecz in cache["mecze"]:
            mecz_id = mecz.get('id')
            if mecz_id in _gotowe_mecze: continue
            start = czas_rozpoczecia_utc(mecz)
            if start is None: continue
            wiek_min = (teraz - start.timestamp()) / 60
            if wiek_min < OPOZNIENIE_MIN: continue

            dop = dopasuj(mecz)
            if dop and not dop['znana_liga'] and dop['league_id'].isdigit():
                # Bez nazwy ligi nie wiemy, czy to np. liga kobieca (odfiltrowywana) - ustal ją przed składami
                info = _pobierz_lige_z_api(dop['league_id'], mecz_id)
                if info:
                    slownik[dop['league_id']] = info
                    dop = dopasuj(mecz)
            if not dop:
                _gotowe_mecze.add(mecz_id)
                continue
            strony = [s for s, polacy in (("home", dop['polacy_gosp']), ("away", dop['polacy_gosc'])) if polacy]
            if all(sklad_ostateczny(mecz_id, s) for s in strony):
                _gotowe_mecze.add(mecz_id)
                continue
            do_zrobienia.append((mecz_id, dop, strony, wiek_min))
        if not do_zrobienia: continue

        # Wynik i status "zakończony" muszą pochodzić z terminarza pobranego już PO meczu.
        # Mecz, który się przedłuża, sprawdzamy ponownie co PONOW_TRWAJACY_MIN minut.
        prog = max(teraz - (w - OPOZNIENIE_MIN) * 60 for *_, w in do_zrobienia)
        aktualne = {m.get('id'): m for m in cache["mecze"]}
        przestarzaly = cache["pobrano"] < prog
        trwa = any(not aktualne.get(i, {}).get('status', {}).get('finished') and w <= OKNO_MIN for i, _, _, w in do_zrobienia)
        if przestarzaly or (trwa and teraz - cache["pobrano"] > PONOW_TRWAJACY_MIN * 60):
            swieze = _pobierz_dzien_z_api(data_api)
            if swieze is not None: aktualne = {m.get('id'): m for m in swieze}

        for mecz_id, dop, strony, wiek_min in do_zrobienia:
            zakonczony = bool(aktualne.get(mecz_id, {}).get('status', {}).get('finished'))
            if not zakonczony and wiek_min <= OKNO_MIN:
                continue  # jeszcze trwa - spróbujemy w kolejnym cyklu
            if pobrane_sklady >= LIMIT_SKLADOW_NA_CYKL:
                raport.append("(limit składów na cykl - reszta w następnym)")
                return
            for strona in strony:
                if not sklad_ostateczny(mecz_id, strona) and _pobierz_sklad_z_api(mecz_id, strona):
                    pobrane_sklady += 1
            raport.append(f"{dop['gosp']} - {dop['gosc']}: {'wynik + składy' if zakonczony else 'składy (brak statusu zakończenia po 6 h)'}")


def _wyczysc_stary_cache():
    dzis = datetime.now(TZ_PL).date()
    granica_dnia = (dzis - timedelta(days=OKNO_DNI + 2)).strftime("%Y%m%d")
    for nazwa in os.listdir(KATALOG_SUROWYCH):
        if nazwa.endswith(".json") and nazwa[:8] < granica_dnia:
            try: os.remove(os.path.join(KATALOG_SUROWYCH, nazwa))
            except Exception: pass
    granica = time.time() - DNI_PRZECHOWYWANIA_SKLADOW * 86400
    for nazwa in os.listdir(KATALOG_SKLADOW):
        sciezka = os.path.join(KATALOG_SKLADOW, nazwa)
        try:
            if os.path.getmtime(sciezka) < granica: os.remove(sciezka)
        except Exception: pass
    if len(_cache_dopasowan) > 100000: _cache_dopasowan.clear()
    if len(_gotowe_mecze) > 100000: _gotowe_mecze.clear()


def cykl_harmonogramu():
    """Jeden przebieg harmonogramu. Zwraca listę opisów tego, co pobrano z API."""
    if not _blokada_harmonogramu.acquire(blocking=False):
        return ["(cykl już trwa)"]
    try:
        raport = []
        ostatnia = STATYSTYKI["ostatnia_synchronizacja_repo"]
        if REPO_RAW and (ostatnia is None or time.time() - ostatnia > SYNC_REPO_H * 3600):
            STATYSTYKI["etap"] = "synchronizacja z repozytorium"
            for plik in synchronizuj_z_repo(): raport.append(f"z repozytorium: {plik}")
        STATYSTYKI["etap"] = "terminarze"
        _odswiez_terminarze(raport)
        STATYSTYKI["etap"] = "mecze Polaków"
        _odswiez_mecze_polakow(raport)
        _wyczysc_stary_cache()
        STATYSTYKI["ostatni_cykl"] = time.time()
        return raport
    except Exception:
        import traceback
        STATYSTYKI["ostatni_blad"] = traceback.format_exc()[-1500:]
        raise
    finally:
        STATYSTYKI["etap"] = "oczekiwanie"
        _blokada_harmonogramu.release()
