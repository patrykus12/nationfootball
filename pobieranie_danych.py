"""
Warstwa danych SERWERA (serwer.py) - jedyne miejsce, które rozmawia z RapidAPI.

Zasada: zapytania użytkowników NIGDY nie wywołują API. Adresy dla aplikacji czytają tylko
gotowe dane z dysku serwera (funkcje *_z_cache). API odpytuje wyłącznie harmonogram
(cykl_harmonogramu, uruchamiany co kilka minut), i to w wymaganym minimum:
  - terminarz dnia (lista meczów): każdy dzień z okna -15..+15 dni raz; dziś i dni przyszłe
    ponownie raz na dobę, zaraz po północy czasu polskiego (zmiany godzin), dni przeszłe już nigdy,
  - mecz z Polakiem (albo zawodnikiem innej nacji z dopasowanie.NACJE): ~2,5 h po rozpoczęciu (gdy już się skończył) jeden raz świeży wynik
    i składy drużyn z Polakami - potem dane są ostateczne i nie są już pobierane,
  - nazwa ligi: raz, tylko dla nieznanej ligi meczu z Polakiem.
"""
import io
import os
import json
import re
import tarfile
import time
import threading
import requests
from datetime import datetime, timedelta

import pytz

from dopasowanie import FLAGI_TRZYLITEROWE, NACJE

KATALOG_PROJEKTU = os.path.dirname(os.path.abspath(__file__))
# Na hostingu z trwałym dyskiem ustaw NF_KATALOG_DANYCH na zamontowany wolumen.
KATALOG_DANYCH = os.environ.get("NF_KATALOG_DANYCH", KATALOG_PROJEKTU)
KATALOG_SUROWYCH = os.path.join(KATALOG_DANYCH, "serwer_cache", "surowe")
KATALOG_SKLADOW = os.path.join(KATALOG_DANYCH, "serwer_cache", "sklady")
os.makedirs(KATALOG_SUROWYCH, exist_ok=True)
os.makedirs(KATALOG_SKLADOW, exist_ok=True)

EXCEL_PLIK = os.path.join(KATALOG_DANYCH, NACJE["pl"]["plik"])  # Polacy - także dla aplikacji na komputer
LIGI_PLIK = os.path.join(KATALOG_DANYCH, "ligi.json")
SLOWNIK_PLIK = os.path.join(KATALOG_DANYCH, "slownik_lig.json")
ZNANI_PLIK = os.path.join(KATALOG_DANYCH, "serwer_cache", "znani_zawodnicy.json")

TZ_PL = pytz.timezone("Europe/Warsaw")


def plik_bazy(nacja):
    return os.path.join(KATALOG_DANYCH, NACJE[nacja]["plik"])


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
OPOZNIENIE_MIN = int(os.environ.get("NF_OPOZNIENIE_MIN", 150))    # pobierz mecz Polaka 2,5 h po rozpoczęciu
OKNO_MIN = int(os.environ.get("NF_OKNO_MIN", 360))                # mecz wciąż "trwa" - czekaj max do 6 h
PONOW_TRWAJACY_MIN = 20                                           # co ile sprawdzać mecz, który się przedłuża
LIMIT_SKLADOW_NA_CYKL = 40                                        # uzupełnianie zaległości po restarcie - porcjami
BLEDY_DO_AWARII = 3                                               # tyle nieudanych zapytań z rzędu = awaria API
PRZERWA_PO_AWARII_MIN = 60                                        # wtedy przez tyle minut nie pytamy API wcale
DNI_PRZECHOWYWANIA_SKLADOW = 17

# Baza zawodników / ligi.json są w repozytorium GitHub - serwer sam je stamtąd dociąga, więc
# cotygodniowa aktualizacja bazy nie wymaga restartu serwera (a restart = utrata cache na
# darmowym Renderze). Na Renderze włączone domyślnie, lokalnie wyłączone (nie nadpisuje plików).
REPO_RAW = os.environ.get("NF_REPO_RAW", "https://raw.githubusercontent.com/patrykus12/nationfootball/main"
                          if os.environ.get("RENDER") else "").rstrip("/")
# raw.githubusercontent.com bywa do ~5 min za repozytorium (CDN) - tuż po wdrożeniu serwer nadpisałby
# nowe pliki starymi i trzymał je do następnej synchronizacji. API GitHuba zwraca aktualną wersję.
REPO_API = os.environ.get("NF_REPO_API", "https://api.github.com/repos/patrykus12/nationfootball/contents"
                          if REPO_RAW else "").rstrip("/")
SYNC_REPO_H = 6

# Kopia zapasowa cache (terminarze, składy, słownik lig) na osobnej gałęzi repozytorium. Darmowy
# Render kasuje dysk przy każdym restarcie/uśpieniu - po starcie serwer odtwarza dane z kopii
# zamiast pobierać wszystko od nowa z API. Kopię co godzinę zapisuje workflow kopia_danych.yml.
GALAZ_KOPII = "kopia-danych"
PLIK_KOPII = "kopia.tar.gz"

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
CCODE_DO_ALPHA2.update(FLAGI_TRZYLITEROWE)

_blokada_slownika = threading.Lock()
_blokada_harmonogramu = threading.Lock()

# Licznik zapytań do API od startu serwera (podgląd na stronie głównej serwera)
STATYSTYKI = {"start": time.time(), "zapytania_api": 0, "pozostalo_w_limicie": None,
              "ostatni_cykl": None, "ostatnia_synchronizacja_repo": None,
              "etap": "oczekiwanie", "ostatni_blad": None, "kopia": None,
              "bledy_api_z_rzedu": 0, "awaria_api_do": None, "ostatni_blad_api": None}

# Ustawiane po próbie odtworzenia kopii - do tego czasu /mecze czeka (zamiast oddać "brak danych")
kopia_gotowa = threading.Event()


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


class AwariaAPI(Exception):
    """API nie odpowiada - zapytanie nie zostało nawet wysłane."""


def awaria_api():
    """True, gdy po serii błędów czekamy z kolejną próbą (patrz _api_get)."""
    return bool(STATYSTYKI["awaria_api_do"] and time.time() < STATYSTYKI["awaria_api_do"])


def _api_get(endpoint, params, timeout=20):
    """JEDYNE miejsce wywołujące RapidAPI. Używane tylko przez harmonogram.
    Po BLEDY_DO_AWARII nieudanych zapytaniach z rzędu (np. awaria dostawcy API) przez
    PRZERWA_PO_AWARII_MIN minut nie wysyła niczego - ponawianie w kółko zjadałoby limit."""
    if awaria_api():
        raise AwariaAPI(f"awaria API - kolejna próba po {datetime.fromtimestamp(STATYSTYKI['awaria_api_do'], TZ_PL):%H:%M}")
    STATYSTYKI["zapytania_api"] += 1
    try:
        res = requests.get(
            f"https://{API_HOST}/{endpoint}",
            headers={"x-rapidapi-key": API_KEY, "x-rapidapi-host": API_HOST},
            params=params, timeout=timeout,
        )
        pozostalo = res.headers.get("x-ratelimit-requests-remaining")
        if pozostalo is not None: STATYSTYKI["pozostalo_w_limicie"] = int(pozostalo)
        res.raise_for_status()
        wynik = res.json()
    except Exception as e:
        STATYSTYKI["bledy_api_z_rzedu"] += 1
        STATYSTYKI["ostatni_blad_api"] = f"{datetime.now(TZ_PL):%Y-%m-%d %H:%M} {endpoint}: {e}"[:300]
        if STATYSTYKI["bledy_api_z_rzedu"] >= BLEDY_DO_AWARII:
            STATYSTYKI["awaria_api_do"] = time.time() + PRZERWA_PO_AWARII_MIN * 60
            STATYSTYKI["bledy_api_z_rzedu"] = 0
            print(f"[api] {BLEDY_DO_AWARII} błędy z rzędu - przerwa {PRZERWA_PO_AWARII_MIN} min", flush=True)
        raise
    STATYSTYKI["bledy_api_z_rzedu"] = 0
    STATYSTYKI["awaria_api_do"] = None
    return wynik


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
    except AwariaAPI:
        return None  # to nie wina ligi - nie blokujemy jej na 6 h
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
def _pobierz_z_repo(nazwa):
    if REPO_API:
        try:
            res = requests.get(f"{REPO_API}/{nazwa}", headers={"Accept": "application/vnd.github.raw"}, timeout=30)
            if res.status_code == 200: return res
        except requests.RequestException:
            pass  # np. limit 60 zapytań/h na IP - wtedy kopia z raw.githubusercontent.com
    return requests.get(f"{REPO_RAW}/{nazwa}", timeout=30)


def synchronizuj_z_repo():
    """Dociąga z GitHuba bazy zawodników wszystkich nacji i ligi.json (podmienia, jeśli się zmieniły) oraz dopisuje
    do słownika ligi z repozytorium, których serwer nie zna. Zwraca listę zmienionych plików."""
    if not REPO_RAW: return []
    from dopasowanie import wczytaj_kluby
    zmienione = []
    try:
        for nacja, info in NACJE.items():
            res = _pobierz_z_repo(info["plik"])
            if res.status_code == 200 and res.content:
                sciezka = plik_bazy(nacja)
                obecny = open(sciezka, "rb").read() if os.path.exists(sciezka) else b""
                if res.content != obecny:
                    tymczasowy = sciezka + ".nowy.xlsx"
                    with open(tymczasowy, "wb") as f: f.write(res.content)
                    if wczytaj_kluby(tymczasowy):
                        os.replace(tymczasowy, sciezka)
                        zmienione.append(info["plik"])
                    else:
                        os.remove(tymczasowy)

        res = _pobierz_z_repo("ligi.json")
        if res.status_code == 200 and isinstance(res.json(), dict):
            obecny = open(LIGI_PLIK, "rb").read() if os.path.exists(LIGI_PLIK) else b""
            if res.content != obecny:
                with open(LIGI_PLIK + ".tmp", "wb") as f: f.write(res.content)
                os.replace(LIGI_PLIK + ".tmp", LIGI_PLIK)
                zmienione.append("ligi.json")

        res = _pobierz_z_repo("slownik_lig.json")
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


# --- KOPIA ZAPASOWA CACHE ---
_WZORZEC_KOPII = re.compile(r"^(surowe/\d{8}\.json|sklady/\d+_(home|away)\.json|slownik_lig\.json|znani_zawodnicy\.json)$")


def eksportuj_kopie():
    """Cały cache serwera jako tar.gz (bajty)."""
    bufor = io.BytesIO()
    with tarfile.open(fileobj=bufor, mode="w:gz") as tar:
        for podkatalog, katalog in (("surowe", KATALOG_SUROWYCH), ("sklady", KATALOG_SKLADOW)):
            for nazwa in sorted(os.listdir(katalog)):
                if _WZORZEC_KOPII.match(f"{podkatalog}/{nazwa}"):
                    tar.add(os.path.join(katalog, nazwa), arcname=f"{podkatalog}/{nazwa}")
        if os.path.exists(SLOWNIK_PLIK): tar.add(SLOWNIK_PLIK, arcname="slownik_lig.json")
        if os.path.exists(ZNANI_PLIK): tar.add(ZNANI_PLIK, arcname="znani_zawodnicy.json")
    return bufor.getvalue()


def _pobierz_kopie_z_repo():
    if REPO_API:
        try:
            res = requests.get(f"{REPO_API}/{PLIK_KOPII}", params={"ref": GALAZ_KOPII},
                               headers={"Accept": "application/vnd.github.raw"}, timeout=60)
            if res.status_code == 200: return res.content
        except requests.RequestException:
            pass
    baza_raw = REPO_RAW.rsplit("/", 1)[0]  # .../nationfootball/main -> .../nationfootball
    res = requests.get(f"{baza_raw}/{GALAZ_KOPII}/{PLIK_KOPII}", timeout=60)
    return res.content if res.status_code == 200 else None


def przywroc_kopie():
    """Po starcie: odtwarza z kopii pliki cache, których serwer nie ma (nic nie nadpisuje)."""
    try:
        if not REPO_RAW: return
        tresc = _pobierz_kopie_z_repo()
        if not tresc:
            STATYSTYKI["kopia"] = "brak kopii w repozytorium"
            return
        odtworzone = 0
        granica_dnia = (datetime.now(TZ_PL).date() - timedelta(days=OKNO_DNI + 2)).strftime("%Y%m%d")
        with tarfile.open(fileobj=io.BytesIO(tresc), mode="r:gz") as tar:
            for czlon in tar.getmembers():
                # Tylko znane nazwy plików, zapisywane przez nas - żadnych ścieżek z archiwum
                if not czlon.isfile() or not _WZORZEC_KOPII.match(czlon.name): continue
                dane_pliku = tar.extractfile(czlon).read()
                if czlon.name == "znani_zawodnicy.json":
                    if not os.path.exists(ZNANI_PLIK):
                        with open(ZNANI_PLIK, "wb") as f: f.write(dane_pliku)
                    continue
                if czlon.name == "slownik_lig.json":
                    znane = wczytaj_nasz_slownik()
                    dopisz_do_slownika({k: v for k, v in json.loads(dane_pliku).items() if k not in znane})
                    continue
                podkatalog, nazwa = czlon.name.split("/")
                if podkatalog == "surowe" and nazwa[:8] < granica_dnia: continue
                cel = os.path.join(KATALOG_SUROWYCH if podkatalog == "surowe" else KATALOG_SKLADOW, nazwa)
                if os.path.exists(cel): continue
                with open(cel + ".tmp", "wb") as f: f.write(dane_pliku)
                os.replace(cel + ".tmp", cel)
                os.utime(cel, (czlon.mtime, czlon.mtime))  # sprzątanie starych składów liczy wiek pliku
                odtworzone += 1
        STATYSTYKI["kopia"] = f"odtworzono {odtworzone} plików"
        print(f"[kopia] odtworzono {odtworzone} plików", flush=True)
    except Exception as e:
        STATYSTYKI["kopia"] = f"błąd odtwarzania: {e}"
        print(f"[kopia] blad odtwarzania: {e}", flush=True)
    finally:
        kopia_gotowa.set()


# --- GOTOWE MECZE POLAKÓW (aplikacja na telefon) ---
def mecze_polakow_dnia(data_pl, nacja="pl"):
    """Mecze z udziałem zawodników danej nacji (domyślnie Polaków) z danego dnia (czas polski) z ich
    występami - to samo, co liczy aplikacja na komputer, ale po stronie serwera. None, gdy serwer
    nie ma jeszcze tego dnia."""
    from dopasowanie import czas_rozpoczecia_utc, wyodrebnij_wystepy_polakow
    wszystkie = mecze_dnia_z_cache(data_pl)
    if wszystkie is None: return None
    kluby = _kluby_z_bazy(nacja)
    if not kluby: return None
    wersja_baz = _wersja_baz()
    slownik, ligi = wczytaj_nasz_slownik(), wczytaj_json(LIGI_PLIK, {}) or {}
    teraz = datetime.now(pytz.utc)

    wyniki = []
    for mecz in wszystkie:
        dop = _dopasuj(mecz, nacja, kluby, slownik, ligi, wersja_baz)
        if dop: dop = _bez_dopisanych_pozniej(dop, nacja, mecz)
        if not dop: continue
        start = czas_rozpoczecia_utc(mecz)
        if start is None: continue
        start_pl = start.astimezone(TZ_PL)
        if start_pl.date() != data_pl: continue

        status = mecz.get('status', {})
        zakonczony = bool(status.get('finished'))
        oczekiwano_danych = zakonczony or (teraz - start) > timedelta(hours=2)
        sklady = []
        if oczekiwano_danych:
            for strona, polacy in (("home", dop['polacy_gosp']), ("away", dop['polacy_gosc'])):
                sklad = sklad_z_cache(mecz.get('id'), strona) if polacy else None
                if sklad: sklady.append(sklad)

        wyniki.append({
            'id': mecz.get('id'), 'godzina': start_pl.strftime("%H:%M"), 'start': start.isoformat(),
            'liga': dop['nazwa_ligi'], 'flaga': dop['flaga_ligi'].lower(),
            'gosp': dop['gosp'], 'gosc': dop['gosc'],
            'wynik': status.get('scoreStr', "").replace(" - ", ":") if zakonczony else None,
            'zakonczony': zakonczony, 'rozpoczety': teraz >= start, 'odwolany': bool(status.get('cancelled')),
            'gracze_gosp': wyodrebnij_wystepy_polakow(sklady, dop['polacy_gosp'], oczekiwano_danych) if dop['polacy_gosp'] else [],
            'gracze_gosc': wyodrebnij_wystepy_polakow(sklady, dop['polacy_gosc'], oczekiwano_danych) if dop['polacy_gosc'] else [],
        })
    wyniki.sort(key=lambda m: m['start'])
    return wyniki


# --- HARMONOGRAM ---
_gotowe_mecze = set()      # id meczów już załatwionych (bez naszych zawodników albo z ostatecznymi składami)
_cache_dopasowan = {}      # (mecz_id, nacja, czy_liga_znana, wersja_baz) -> wynik dopasuj_mecz
_cache_klubow = {}         # nacja -> {"wersja": ..., "kluby": {...}}


def _wersja_baz():
    """Zmienia się, gdy podmieniono którąś bazę zawodników albo ligi.json - wtedy dopasowania liczymy od nowa."""
    pliki = [plik_bazy(n) for n in NACJE] + [LIGI_PLIK]
    return tuple(os.path.getmtime(p) if os.path.exists(p) else 0 for p in pliki)


def _kluby_z_bazy(nacja):
    from dopasowanie import wczytaj_kluby
    wersja = _wersja_baz()
    cache = _cache_klubow.get(nacja)
    if not cache or cache["wersja"] != wersja:
        cache = _cache_klubow[nacja] = {"wersja": wersja, "kluby": wczytaj_kluby(plik_bazy(nacja))}
    return cache["kluby"]


_znani = {"wersja": None, "od": {}}


def _znani_od():
    """{"nacja|klub|zawodnik": od kiedy jest w bazie}. Zawodnik dopisany później (cotygodniowa
    aktualizacja, transfer, nowa nacja) nie "gra" w meczach sprzed dopisania - serwer nie dociąga
    dla nich składów wstecz (oszczędność limitu API), a widok nie pokazuje go w meczach nowego
    klubu sprzed transferu. Pierwszy raz (brak pliku) - wszyscy obecni są w bazie od zawsze."""
    wersja = _wersja_baz()
    if _znani["wersja"] == wersja: return _znani["od"]
    zapisane = wczytaj_json(ZNANI_PLIK)
    od_teraz = time.time() if zapisane is not None else 0
    zapisane = zapisane or {}
    od = {}
    for nacja in NACJE:
        for klub, info in _kluby_z_bazy(nacja).items():
            for gracz in info['gracze']:
                klucz = f"{nacja}|{klub}|{gracz}"
                od[klucz] = zapisane.get(klucz, od_teraz)
    if od != zapisane or not os.path.exists(ZNANI_PLIK): zapisz_json_atomowo(ZNANI_PLIK, od)
    _znani.update(wersja=wersja, od=od)
    return od


def _bez_dopisanych_pozniej(dop, nacja, mecz):
    """Dopasowanie bez zawodników dopisanych do bazy po rozpoczęciu meczu (None, gdy nikt nie zostaje)."""
    from dopasowanie import czas_rozpoczecia_utc
    start = czas_rozpoczecia_utc(mecz)
    if start is None: return dop
    znani, ts = _znani_od(), start.timestamp()
    gosp = [g for g in dop['polacy_gosp'] if znani.get(f"{nacja}|{dop['klub_gosp']}|{g}", 0) <= ts]
    gosc = [g for g in dop['polacy_gosc'] if znani.get(f"{nacja}|{dop['klub_gosc']}|{g}", 0) <= ts]
    if not (gosp or gosc): return None
    if gosp == dop['polacy_gosp'] and gosc == dop['polacy_gosc']: return dop
    return dict(dop, polacy_gosp=gosp, polacy_gosc=gosc)


def _dopasuj(mecz, nacja, kluby, slownik, ligi, wersja):
    from dopasowanie import dopasuj_mecz
    klucz = (mecz.get('id'), nacja, str(mecz.get('leagueId', '')) in slownik, wersja)
    if klucz not in _cache_dopasowan:
        _cache_dopasowan[klucz] = dopasuj_mecz(mecz, kluby, slownik, ligi)
    return _cache_dopasowan[klucz]


def _odswiez_terminarze(raport):
    dzis = datetime.now(TZ_PL).date()
    polnoc = TZ_PL.localize(datetime.combine(dzis, datetime.min.time())).timestamp()
    for offset in range(-OKNO_DNI - 1, OKNO_DNI + 2):
        data_api = dzis + timedelta(days=offset)
        cache = surowe_z_cache(data_api)
        if cache is None:
            powod = "brak"
        elif data_api >= dzis and cache["pobrano"] < polnoc:
            powod = "aktualizacja po północy"
        else:
            continue
        if _pobierz_dzien_z_api(data_api) is not None:
            raport.append(f"terminarz {data_api} ({powod})")


def _odswiez_mecze_polakow(raport):
    from dopasowanie import czas_rozpoczecia_utc
    kluby = {nacja: _kluby_z_bazy(nacja) for nacja in NACJE}
    kluby = {nacja: k for nacja, k in kluby.items() if k}
    if not kluby: return
    wersja_baz = _wersja_baz()
    slownik, ligi = wczytaj_nasz_slownik(), wczytaj_json(LIGI_PLIK, {}) or {}
    teraz = time.time()
    dzis = datetime.now(TZ_PL).date()
    pobrane_sklady = 0

    def dopasuj(mecz):
        """{nacja: dopasowanie} - tylko nacje, których zawodnicy grają w tym meczu."""
        dopasowania = {nacja: _dopasuj(mecz, nacja, k, slownik, ligi, wersja_baz) for nacja, k in kluby.items()}
        dopasowania = {nacja: _bez_dopisanych_pozniej(dop, nacja, mecz) for nacja, dop in dopasowania.items() if dop}
        return {nacja: dop for nacja, dop in dopasowania.items() if dop}

    # Najpierw nazwy nieznanych lig meczów z Polakami w całym oknie (także przyszłe dni), zanim
    # limit składów na cykl przerwie pętlę niżej - 1 zapytanie na ligę, potem na stałe w słowniku.
    # Bez nazwy aplikacja pokazuje "Rozgrywki (ID: ...)" i nie wiemy, czy to np. liga kobieca.
    for offset in range(OKNO_DNI + 1, -OKNO_DNI - 2, -1):
        cache = surowe_z_cache(dzis + timedelta(days=offset))
        for mecz in (cache or {}).get("mecze", []):
            dop = next(iter(dopasuj(mecz).values()), None)  # liga ta sama dla każdej nacji
            if dop and not dop['znana_liga'] and dop['league_id'].isdigit() and dop['league_id'] not in slownik:
                info = _pobierz_lige_z_api(dop['league_id'], mecz.get('id'))
                if info:
                    slownik[dop['league_id']] = info
                    raport.append(f"nazwa ligi {dop['league_id']}: {info['nazwa']}")

    # Od najnowszych dni: po restarcie (utrata cache) zaległe składy idą porcjami po
    # LIMIT_SKLADOW_NA_CYKL - dzisiejsze mecze nie mogą czekać, aż serwer nadrobi stare dni
    for offset in range(1, -OKNO_DNI - 2, -1):
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

            dopasowania = dopasuj(mecz)
            if wiek_min < OPOZNIENIE_MIN: continue
            if not dopasowania:
                _gotowe_mecze.add(mecz_id)
                continue
            # Składy drużyn, w których gra ktokolwiek z naszych - z dowolnej nacji
            strony = [s for s, klucz in (("home", 'polacy_gosp'), ("away", 'polacy_gosc'))
                      if any(d[klucz] for d in dopasowania.values())]
            dop = next(iter(dopasowania.values()))
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
            if awaria_api(): return
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


def po_starcie_procesu():
    """Świeże blokady w nowym procesie. Gunicorn potrafi wczytać kod w procesie głównym i dopiero
    potem go sklonować - klon dostaje kopię pamięci (np. blokadę zajętą przez wątek, który w klonie
    nie istnieje), a wątki nie przechodzą do klonu."""
    global _blokada_harmonogramu, _blokada_slownika, kopia_gotowa
    _blokada_harmonogramu = threading.Lock()
    _blokada_slownika = threading.Lock()
    kopia_gotowa = threading.Event()
    STATYSTYKI.update({"start": time.time(), "zapytania_api": 0, "etap": "oczekiwanie", "ostatni_blad": None,
                       "ostatni_cykl": None, "ostatnia_synchronizacja_repo": None, "kopia": None,
                       "bledy_api_z_rzedu": 0, "awaria_api_do": None, "ostatni_blad_api": None})


def cykl_harmonogramu(wymus_repo=False):
    """Jeden przebieg harmonogramu. Zwraca listę opisów tego, co pobrano z API.
    wymus_repo - pobierz bazy z repozytorium od razu (po ręcznej aktualizacji przez administratora)."""
    if not kopia_gotowa.is_set():
        return ["(trwa odtwarzanie kopii)"]
    if not _blokada_harmonogramu.acquire(blocking=False):
        return ["(cykl już trwa)"]
    try:
        raport = []
        ostatnia = STATYSTYKI["ostatnia_synchronizacja_repo"]
        if REPO_RAW and (wymus_repo or ostatnia is None or time.time() - ostatnia > SYNC_REPO_H * 3600):
            STATYSTYKI["etap"] = "synchronizacja z repozytorium"
            for plik in synchronizuj_z_repo(): raport.append(f"z repozytorium: {plik}")
        if awaria_api():
            raport.append(f"(awaria API - kolejna próba po {datetime.fromtimestamp(STATYSTYKI['awaria_api_do'], TZ_PL):%H:%M})")
        else:
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
