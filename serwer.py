"""
Serwer danych dla NationFootball - pośrednik między RapidAPI a aplikacjami użytkowników.

    RapidAPI  --(tylko serwer, z cache)-->  serwer.py  --(HTTP)-->  aplikacje

Endpointy (wszystkie GET, JSON skompresowany gzipem jeśli klient to obsługuje):
  /                                   status
  /mecze/<YYYYMMDD>                   wszystkie mecze z danego dnia (czas polski)
  /sklad/<mecz_id>/<home|away>?zakonczony=0|1   skład jednej drużyny
  /liga/<league_id>?mecz=<mecz_id>    nazwa+flaga ligi (doczytywana z API, jeśli nieznana)
  /slownik-lig                        slownik_lig.json
  /ligi                               ligi.json (ręczne nadpisania / ignorowane ligi)
  /zawodnicy                          zawodnicy.xlsx
  /cron                               odśwież teraz mecze Polaków (patrz niżej)

Automatyczne odświeżanie: ~2,5 h po rozpoczęciu każdego meczu z Polakiem serwer sam pobiera
wynik i składy (wątek co NF_INTERWAL_MIN minut + /cron wywoływany z GitHub Actions, który
budzi serwer na darmowym hostingu usypiającym po bezczynności).

Aktualizacja bazy zawodników / ligi.json bez redeployu:
  POST /admin/<zawodnicy|ligi>  z nagłówkiem X-Admin-Token (zmienna NF_ADMIN_TOKEN) - patrz wyslij_na_serwer.py

Lokalnie:     python serwer.py
Na hostingu:  gunicorn -w 1 --threads 8 -b 0.0.0.0:$PORT serwer:app
              (JEDEN worker - blokady przed dublowaniem zapytań do API działają w obrębie procesu)
Zmienne:      RAPIDAPI_KEY (wymagana), NF_ADMIN_TOKEN, NF_KATALOG_DANYCH (opcjonalnie)
"""
import gzip
import hmac
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
ADMIN_TOKEN = os.environ.get("NF_ADMIN_TOKEN", "")
INTERWAL_ODSWIEZANIA_MIN = int(os.environ.get("NF_INTERWAL_MIN", 10))

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


_ostatnie_sprzatanie = [0.0]


@app.before_request
def sprzatanie_cache():
    if time.time() - _ostatnie_sprzatanie[0] > 3600:
        _ostatnie_sprzatanie[0] = time.time()
        threading.Thread(target=dane.wyczysc_stary_cache, daemon=True).start()


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


@app.route("/")
def status():
    return jsonify({"status": "ok", "serwis": "NationFootball - serwer danych"})


@app.route("/mecze/<data_str>")
def mecze(data_str):
    try:
        data_obj = datetime.strptime(data_str, "%Y%m%d").date()
    except ValueError:
        abort(400, "Format daty to YYYYMMDD, np. 20260925")

    dzisiaj = datetime.now(dane.TZ_PL).date()
    if not (dzisiaj - timedelta(days=DNI_HISTORII) <= data_obj <= dzisiaj + timedelta(days=DNI_NAPRZOD)):
        abort(404, f"Data poza obsługiwanym zakresem ({DNI_HISTORII} dni wstecz / {DNI_NAPRZOD} dni w przód)")

    return odpowiedz_json(dane.mecze_dnia(data_obj))


@app.route("/sklad/<int:mecz_id>/<strona>")
def sklad(mecz_id, strona):
    if strona not in ("home", "away"): abort(400, "strona = home albo away")
    zakonczony = request.args.get("zakonczony") == "1"
    return odpowiedz_json({"sklad": dane.sklad_druzyny(mecz_id, strona, zakonczony)})


@app.route("/liga/<int:league_id>")
def liga(league_id):
    mecz_id = request.args.get("mecz", type=int)
    info = dane.liga_dla_meczu(str(league_id), mecz_id)
    if not info: abort(404, "Nieznana liga")
    return odpowiedz_json(info)


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
    # wysyłania (na Windowsie blokowałoby to jego podmianę przez /admin/zawodnicy)
    with open(dane.EXCEL_PLIK, "rb") as f: tresc = f.read()
    return Response(tresc, mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


@app.route("/cron")
def cron():
    """Wywoływane z zewnątrz co ~30 min (GitHub Actions) - budzi uśpiony serwer i od razu
    odświeża mecze Polaków. Bezpieczne do wywoływania dowolnie często: API odpytywane jest
    tylko dla meczów, których dane faktycznie trzeba dociągnąć."""
    return jsonify({"odswiezone": dane.odswiez_mecze_polakow()})


def watek_odswiezania():
    while True:
        try:
            for wpis in dane.odswiez_mecze_polakow(): print(f"[auto] {wpis}")
        except Exception as e:
            print(f"[auto] błąd odświeżania: {e}")
        time.sleep(INTERWAL_ODSWIEZANIA_MIN * 60)


@app.route("/admin/<nazwa>", methods=["POST"])
def admin_wyslij(nazwa):
    if not ADMIN_TOKEN or not hmac.compare_digest(request.headers.get("X-Admin-Token", ""), ADMIN_TOKEN):
        abort(403)
    cele = {"zawodnicy": dane.EXCEL_PLIK, "ligi": dane.LIGI_PLIK}
    if nazwa not in cele: abort(404)
    tresc = request.get_data()
    if not tresc: abort(400, "Pusty plik")
    if nazwa == "ligi":
        try: json.loads(tresc)
        except ValueError: abort(400, "ligi.json nie jest poprawnym JSON-em")
    tymczasowy = cele[nazwa] + ".tmp"
    with open(tymczasowy, "wb") as f: f.write(tresc)
    os.replace(tymczasowy, cele[nazwa])
    return jsonify({"status": "ok", "plik": os.path.basename(cele[nazwa]), "bajty": len(tresc)})


_przygotuj_pliki_startowe()
threading.Thread(target=watek_odswiezania, daemon=True).start()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, threaded=True)
