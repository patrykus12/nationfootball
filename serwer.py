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
  /cron                               budzi serwer i uruchamia cykl harmonogramu w tle

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

from flask import Flask, Response, abort, jsonify, request

import pobieranie_danych as dane

DNI_HISTORII = 14
DNI_NAPRZOD = 14
INTERWAL_HARMONOGRAMU_MIN = int(os.environ.get("NF_INTERWAL_MIN", 10))

app = Flask(__name__)


def _przygotuj_pliki_startowe():
    """Gdy dane trzymamy na osobnym wolumenie - skopiuj tam pliki z repozytorium przy pierwszym starcie."""
    for nazwa in ("zawodnicy.xlsx", "ligi.json", "slownik_lig.json"):
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
        "harmonogram": {"watek_dziala": _watek.is_alive(), "etap": s["etap"], "pid": os.getpid(),
                        "ostatni_blad": s["ostatni_blad"]},
    })


@app.route("/mecze/<data_str>")
def mecze(data_str):
    try:
        data_obj = datetime.strptime(data_str, "%Y%m%d").date()
    except ValueError:
        abort(400, "Format daty to YYYYMMDD, np. 20260925")

    dzisiaj = datetime.now(dane.TZ_PL).date()
    if not (dzisiaj - timedelta(days=DNI_HISTORII) <= data_obj <= dzisiaj + timedelta(days=DNI_NAPRZOD)):
        abort(404, f"Data poza obsługiwanym zakresem ({DNI_HISTORII} dni wstecz / {DNI_NAPRZOD} dni w przód)")

    lista = dane.mecze_dnia_z_cache(data_obj)
    if lista is None: abort(404, "Serwer nie ma jeszcze danych dla tego dnia")
    return odpowiedz_json(lista)


@app.route("/sklad/<int:mecz_id>/<strona>")
def sklad(mecz_id, strona):
    if strona not in ("home", "away"): abort(400, "strona = home albo away")
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


def _uruchom_cykl():
    try:
        for wpis in dane.cykl_harmonogramu(): print(f"[harmonogram] {wpis}", flush=True)
    except Exception as e:
        print(f"[harmonogram] błąd: {e}", flush=True)


@app.route("/cron")
def cron():
    """Wywoływane z zewnątrz co ~10 min (GitHub Actions) - nie pozwala darmowemu hostingowi uśpić
    serwera (uśpienie = utrata cache i przerwa w harmonogramie). Cykl rusza w tle; wywołanie
    jest bezpieczne dowolnie często - API i tak odpytywane jest tylko wtedy, gdy trzeba."""
    threading.Thread(target=_uruchom_cykl, daemon=True).start()
    return jsonify({"status": "ok", "ostatni_cykl": _czas(dane.STATYSTYKI["ostatni_cykl"])})


def watek_harmonogramu():
    _przygotuj_pliki_startowe()
    while True:
        _uruchom_cykl()
        time.sleep(INTERWAL_HARMONOGRAMU_MIN * 60)


# Wszystko, co może dotykać sieci, startuje w wątku - import modułu (start gunicorna) jest natychmiastowy
_watek = threading.Thread(target=watek_harmonogramu, daemon=True)
_watek.start()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, threaded=True)
