"""
Serwer danych dla NationFootball - pośrednik między RapidAPI a aplikacjami użytkowników.

    RapidAPI  --(tylko harmonogram serwera)-->  serwer.py  --(HTTP)-->  aplikacje

Zapytania aplikacji NIGDY nie wywołują API - dostają wyłącznie dane, które serwer już ma.
API odpytuje tylko harmonogram (pobieranie_danych.cykl_harmonogramu, co NF_INTERWAL_MIN minut),
w wymaganym minimum - szczegóły w pobieranie_danych.py.

Endpointy (wszystkie GET, JSON skompresowany gzipem jeśli klient to obsługuje):
  /                                   status + licznik zapytań do API od startu
  /mecze/<YYYYMMDD>                   mecze z danego dnia (czas polski), 404 = serwer jeszcze nie ma danych
  /sklad/<mecz_id>/<home|away>        skład jednej drużyny ({"sklad": null}, jeśli jeszcze nie ma)
  /slownik-lig                        slownik_lig.json
  /ligi                               ligi.json (ręczne nadpisania / ignorowane ligi)
  /zawodnicy                          zawodnicy.xlsx
  /api/dzien/<YYYYMMDD>[?nacja=tr]    gotowe mecze Polaków (albo innej nacji) z występami (aplikacja na telefon)
  /api/zawodnik?nacja=&nazwa=         profil zawodnika: historia meczów, forma, statystyki, najbliższy mecz
  /api/zawodnik/najblizszy?nacja=&nazwa=  najbliższy mecz (gdy profil podał najblizszy_liczony)
  /api/rankingi?nacja=&dni=7|30|0     legion (najlepsza jedenastka), strzelcy, asystenci, minuty, oceny, nacje
  /api/transfery?nacja=               zmiany klubów i nowi zawodnicy w bazie
  /api/kadra?nacja=                   wszyscy zawodnicy nacji (wyszukiwarka)
  /api/ulubieni?z=nacja|nazwa&z=...   skrócone profile ulubionych
  /api/push/klucz, POST /api/push/subskrypcja, POST /api/push/usun   ciche powiadomienia o golach/asystach
  /app/                               aplikacja na telefon (PWA, pliki z katalogu web/)
  /cron                               budzi serwer i uruchamia cykl harmonogramu w tle
                                      (?repo=1 - od razu pobierz bazy z repozytorium, np. po aktualizacji)
  /eksport                            kopia cache (tar.gz) - zapisywana co godzinę w repozytorium

Lokalnie:     python serwer.py
Na hostingu:  gunicorn -w 1 --threads 8 -b 0.0.0.0:$PORT serwer:app
              (JEDEN worker - harmonogram działa w obrębie procesu)
Zmienne:      RAPIDAPI_KEY (wymagana), NF_KATALOG_DANYCH, NF_INTERWAL_MIN, NF_REPO_RAW (opcjonalnie)
"""
import gzip
import json
import os
import shutil
import threading
import time
from datetime import datetime, timedelta

from flask import Flask, Response, abort, jsonify, redirect, request, send_from_directory

import historia
import kadry_api
import pobieranie_danych as dane

KATALOG_WEB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web")
DNI_HISTORII = 14
DNI_NAPRZOD = 14
INTERWAL_HARMONOGRAMU_MIN = int(os.environ.get("NF_INTERWAL_MIN", 10))
# Darmowy Render usypia serwer po 15 min bez zapytań z zewnątrz (a uśpienie kasuje dysk). Zaplanowane
# workflowy GitHuba odpalają się w praktyce co kilka godzin, więc serwer sam odpytuje swój publiczny
# adres (zapytanie przechodzi przez Render jak każde inne). Render ustawia RENDER_EXTERNAL_URL.
ADRES_PUBLICZNY = os.environ.get("RENDER_EXTERNAL_URL", "").rstrip("/")
PODTRZYMANIE_MIN = 5

app = Flask(__name__)

# Błędy 500 z zapytań aplikacji - ślad trafia do logu i na stronę statusu ("/"), bo logów Rendera nie widać od ręki
_bledy_zapytan = []


@app.errorhandler(Exception)
def _blad_zapytania(e):
    from werkzeug.exceptions import HTTPException
    if isinstance(e, HTTPException): return e
    import traceback
    slad = traceback.format_exc()
    print(f"[blad zapytania] {request.path}\n{slad}", flush=True)
    _bledy_zapytan.append({"czas": datetime.now(dane.TZ_PL).strftime("%Y-%m-%d %H:%M:%S"), "adres": request.full_path[:200],
                           "blad": slad[-1200:]})
    del _bledy_zapytan[:-20]
    return jsonify({"blad": "Błąd serwera - spróbuj ponownie za chwilę"}), 500


def _przygotuj_pliki_startowe():
    """Gdy dane trzymamy na osobnym wolumenie - skopiuj tam pliki z repozytorium przy pierwszym starcie."""
    bazy = [os.path.basename(dane.plik_bazy_tm(n, s)) for n, s in dane.pliki_baz()]
    for nazwa in bazy + ["ligi.json", "slownik_lig.json"]:
        cel = os.path.join(dane.KATALOG_DANYCH, nazwa)
        zrodlo = os.path.join(dane.KATALOG_PROJEKTU, nazwa)
        if not os.path.exists(cel) and os.path.exists(zrodlo) and cel != zrodlo:
            shutil.copy2(zrodlo, cel)
    if len(dane.wczytaj_nasz_slownik()) < 100:
        try:
            print(f"[start] pobrano {dane.pobierz_wszystkie_ligi_z_api()} lig do słownika")
        except Exception as e:
            print(f"[start] nie udało się pobrać listy lig: {e}")


def odpowiedz_json(obiekt=None, tresc=None):
    if tresc is None:
        tresc = json.dumps(obiekt, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    if "gzip" in request.headers.get("Accept-Encoding", ""):
        resp = Response(gzip.compress(tresc, compresslevel=6), mimetype="application/json")
        resp.headers["Content-Encoding"] = "gzip"
        resp.headers["Vary"] = "Accept-Encoding"
        return resp
    return Response(tresc, mimetype="application/json")


def plik_json(sciezka, komunikat_404):
    """Plik wysyłany 1:1 (z zachowanym formatowaniem), tylko skompresowany."""
    if not os.path.exists(sciezka): abort(404, komunikat_404)
    with open(sciezka, "rb") as f: return odpowiedz_json(tresc=f.read())


def _czas(ts):
    return datetime.fromtimestamp(ts, dane.TZ_PL).strftime("%Y-%m-%d %H:%M") if ts else None


@app.route("/")
def status():
    s = dane.STATYSTYKI
    return jsonify({
        "status": "ok", "serwis": "NationFootball - serwer danych",
        "dziala_od": _czas(s["start"]), "zapytania_api_od_startu": s["zapytania_api"],
        "pozostalo_w_limicie_api": s["pozostalo_w_limicie"],
        "ostatni_cykl_harmonogramu": _czas(s["ostatni_cykl"]),
        "ostatnia_synchronizacja_z_repo": _czas(s["ostatnia_synchronizacja_repo"]),
        "harmonogram": {"watek_dziala": bool(_watek and _watek.is_alive()), "etap": s["etap"], "pid": os.getpid(),
                        "ostatni_blad": s["ostatni_blad"]},
        "kopia_zapasowa": s["kopia"],
        "awaria_api": f"tak - kolejna próba po {_czas(s['awaria_api_do'])[11:]}" if dane.awaria_api() else "nie",
        "ostatni_blad_api": s["ostatni_blad_api"],
        "zuzycie_api": dane.podsumowanie_licznika(),
        "kadry_z_api": kadry_api.status(),
        "ostatnie_bledy_zapytan": _bledy_zapytan[-5:],
    })


def _dzien_z_adresu(data_str):
    try:
        data_obj = datetime.strptime(data_str, "%Y%m%d").date()
    except ValueError:
        abort(400, "Format daty to YYYYMMDD, np. 20260925")

    dzisiaj = datetime.now(dane.TZ_PL).date()
    if not (dzisiaj - timedelta(days=DNI_HISTORII) <= data_obj <= dzisiaj + timedelta(days=DNI_NAPRZOD)):
        abort(404, f"Data poza obsługiwanym zakresem ({DNI_HISTORII} dni wstecz / {DNI_NAPRZOD} dni w przód)")
    dane.kopia_gotowa.wait(timeout=60)  # tuż po starcie serwer odtwarza dane z kopii (kilka sekund)
    return data_obj


@app.route("/mecze/<data_str>")
def mecze(data_str):
    lista = dane.mecze_dnia_z_cache(_dzien_z_adresu(data_str))
    if lista is None: abort(404, "Serwer nie ma jeszcze danych dla tego dnia")
    return odpowiedz_json(lista)


@app.route("/api/dzien/<data_str>")
def dzien_polakow(data_str):
    nacja = request.args.get("nacja", "pl")
    if nacja not in dane.NACJE: abort(400, f"Nieznana nacja - dostępne: {', '.join(dane.NACJE)}")
    lista = dane.mecze_polakow_dnia(_dzien_z_adresu(data_str), nacja)
    if lista is None: abort(404, "Serwer nie ma jeszcze danych dla tego dnia")
    historia.rozgrzej_najblizsze(nacja)   # profile zawodników tej nacji otworzą się od razu
    return odpowiedz_json({"dzien": data_str, "stan_na": _czas(time.time()), "mecze": lista})


def _nacja_z_adresu():
    nacja = request.args.get("nacja", "pl")
    if nacja not in dane.NACJE: abort(400, "Nieznana nacja")
    dane.kopia_gotowa.wait(timeout=60)
    return nacja


@app.route("/api/zawodnik")
def zawodnik():
    nacja, nazwa = _nacja_z_adresu(), request.args.get("nazwa", "").strip()[:100]
    if not nazwa: abort(400, "Brak nazwy zawodnika")
    return odpowiedz_json(historia.profil(nacja, nazwa))


@app.route("/api/zawodnik/najblizszy")
def zawodnik_najblizszy():
    nacja, nazwa = _nacja_z_adresu(), request.args.get("nazwa", "").strip()[:100]
    if not nazwa: abort(400, "Brak nazwy zawodnika")
    return odpowiedz_json(historia.najblizszy(nacja, nazwa))


@app.route("/api/rankingi")
def rankingi():
    nacja = _nacja_z_adresu()
    try: dni = int(request.args.get("dni", 7))
    except ValueError: abort(400, "dni = 7, 30 albo 0 (cały sezon)")
    if dni not in (0, 7, 30): abort(400, "dni = 7, 30 albo 0 (cały sezon)")
    return odpowiedz_json(historia.rankingi(nacja, dni or None))


@app.route("/api/transfery")
def transfery():
    return odpowiedz_json({"zdarzenia": historia.transfery(_nacja_z_adresu())})


@app.route("/api/kadra")
def kadra():
    return odpowiedz_json({"zawodnicy": historia.kadra(_nacja_z_adresu())})


@app.route("/api/ulubieni")
def ulubieni():
    dane.kopia_gotowa.wait(timeout=60)
    lista, doliczanie = historia.ulubieni(request.args.getlist("z")[:historia.MAX_ULUBIONYCH])
    return odpowiedz_json({"zawodnicy": lista, "doliczanie": doliczanie})


@app.route("/api/push/klucz")
def push_klucz():
    return jsonify({"wlaczone": historia.push_wlaczony(), "klucz": historia.VAPID_PUBLICZNY if historia.push_wlaczony() else None})


@app.route("/api/push/subskrypcja", methods=["POST"])
def push_subskrypcja():
    if not historia.push_wlaczony(): abort(503, "Powiadomienia wyłączone na serwerze")
    dane_zad = request.get_json(silent=True) or {}
    try:
        historia.zapisz_subskrypcje(dane_zad.get("sub"), dane_zad.get("ulubieni") or [], str(dane_zad.get("jezyk") or "pl")[:5])
    except ValueError as e:
        abort(400, str(e))
    return jsonify({"ok": True})


@app.route("/api/push/usun", methods=["POST"])
def push_usun():
    historia.usun_subskrypcje((request.get_json(silent=True) or {}).get("endpoint", ""))
    return jsonify({"ok": True})


@app.route("/app")
def aplikacja_bez_ukosnika():
    return redirect("/app/")


@app.route("/app/")
@app.route("/app/<path:plik>")
def aplikacja(plik="index.html"):
    # max_age=0 - telefony zawsze sprawdzają, czy jest nowa wersja (offline działa service worker)
    odp = send_from_directory(KATALOG_WEB, plik, max_age=0)
    if plik == "sw.js": odp.headers["Service-Worker-Allowed"] = "/app/"
    return odp


@app.route("/sklad/<int:mecz_id>/<strona>")
def sklad(mecz_id, strona):
    if strona not in ("home", "away"): abort(400, "strona = home albo away")
    dane.kopia_gotowa.wait(timeout=60)
    return odpowiedz_json({"sklad": dane.sklad_z_cache(mecz_id, strona)})


@app.route("/slownik-lig")
def slownik_lig():
    return plik_json(dane.SLOWNIK_PLIK, "Słownik lig jeszcze nie istnieje")


@app.route("/ligi")
def ligi():
    return plik_json(dane.LIGI_PLIK, "Plik ligi.json jeszcze nie istnieje")


@app.route("/zawodnicy")
def zawodnicy():
    if not os.path.exists(dane.EXCEL_PLIK): abort(404, "Brak pliku zawodnicy.xlsx na serwerze")
    # Wczytujemy do pamięci zamiast send_file, żeby nie trzymać otwartego pliku w trakcie
    # wysyłania (na Windowsie blokowałoby to jego podmianę przy synchronizacji)
    with open(dane.EXCEL_PLIK, "rb") as f: tresc = f.read()
    return Response(tresc, mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


@app.route("/eksport")
def eksport():
    # Dopiero po pełnym cyklu - kopia z serwera tuż po starcie (np. gdy odtworzenie się nie udało)
    # nadpisałaby w repozytorium dobrą kopię prawie pustą
    # Po udanym odtworzeniu kopii dane są pełne już przed pierwszym cyklem (który po restarcie trwa długo) -
    # wcześniej workflow kopii dostawał 503 i kopia potrafiła nie odświeżać się przez pół dnia
    odtworzono = str(dane.STATYSTYKI["kopia"] or "").startswith("odtworzono")
    if dane.STATYSTYKI["ostatni_cykl"] is None and not odtworzono:
        abort(503, "Serwer dopiero startuje - kopia po pierwszym cyklu")
    return Response(dane.eksportuj_kopie(), mimetype="application/gzip")


def _uruchom_cykl(wymus_repo=False):
    try:
        raport = dane.cykl_harmonogramu(wymus_repo)
        for wpis in raport: print(f"[harmonogram] {wpis}", flush=True)
    except Exception as e:
        print(f"[harmonogram] błąd: {e}", flush=True)
        return
    # Historia występów / transfery / powiadomienia - tylko z danych serwera, bez zapytań do API
    if dane.STATYSTYKI["ostatni_cykl"] and raport not in (["(cykl już trwa)"], ["(trwa odtwarzanie kopii)"]):
        for wpis in historia.po_cyklu(): print(f"[historia] {wpis}", flush=True)
        # Bazy zawodników z API (kadry klubów + transfery) - z bezpiecznikiem limitu, po meczach
        if not dane.awaria_api():
            for wpis in kadry_api.po_cyklu(): print(f"[kadry] {wpis}", flush=True)


@app.route("/cron")
def cron():
    """Wywoływane z zewnątrz co ~10 min (GitHub Actions) - nie pozwala darmowemu hostingowi uśpić
    serwera (uśpienie = utrata cache i przerwa w harmonogramie). Cykl rusza w tle; wywołanie
    jest bezpieczne dowolnie często - API i tak odpytywane jest tylko wtedy, gdy trzeba."""
    threading.Thread(target=_uruchom_cykl, args=(request.args.get("repo") == "1",), daemon=True).start()
    return jsonify({"status": "ok", "ostatni_cykl": _czas(dane.STATYSTYKI["ostatni_cykl"])})


def watek_harmonogramu():
    try: _przygotuj_pliki_startowe()
    except Exception as e: print(f"[start] {e}", flush=True)
    dane.przywroc_kopie()
    # Historia/rankingi z danych odtworzonych z kopii - od razu, bez czekania na pierwszy (długi) cykl z API
    threading.Thread(target=lambda: [print(f"[historia] {w}", flush=True) for w in historia.po_cyklu()], daemon=True).start()
    while True:
        _uruchom_cykl()
        time.sleep(INTERWAL_HARMONOGRAMU_MIN * 60)


def watek_podtrzymania():
    import requests
    while True:
        time.sleep(PODTRZYMANIE_MIN * 60)
        try: requests.get(f"{ADRES_PUBLICZNY}/", timeout=60)
        except Exception as e: print(f"[podtrzymanie] {e}", flush=True)


# Harmonogram startuje dopiero w procesie, który faktycznie obsługuje zapytania (przy pierwszym
# zapytaniu). Gdyby startował przy imporcie, gunicorn z --preload uruchomiłby go w procesie
# głównym, a proces obsługujący zapytania dostałby tylko martwą kopię (patrz po_starcie_procesu).
_watek = None
_watek_pid = None
_blokada_startu = threading.Lock()


def _upewnij_sie_ze_harmonogram_dziala():
    global _watek, _watek_pid
    if _watek is not None and _watek_pid == os.getpid() and _watek.is_alive(): return
    with _blokada_startu:
        if _watek is not None and _watek_pid == os.getpid() and _watek.is_alive(): return
        if _watek_pid != os.getpid(): dane.po_starcie_procesu()
        _watek_pid = os.getpid()
        _watek = threading.Thread(target=watek_harmonogramu, daemon=True)
        _watek.start()
        if ADRES_PUBLICZNY: threading.Thread(target=watek_podtrzymania, daemon=True).start()


@app.before_request
def _start_harmonogramu():
    _upewnij_sie_ze_harmonogram_dziala()


if __name__ == "__main__":
    _upewnij_sie_ze_harmonogram_dziala()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, threaded=True)
