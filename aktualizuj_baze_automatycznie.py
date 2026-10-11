"""
Cotygodniowa aktualizacja bazy zawodników - uruchamiana automatycznie przez GitHub Actions
(.github/workflows/baza_zawodnikow.yml), ale da się też odpalić ręcznie.

1. Skanuje Transfermarkt (skaner_zawodnikow.py).
2. Sprawdza, czy wynik wygląda sensownie - jeśli skan się wysypał albo zwrócił podejrzanie mało
   zawodników (np. blokada Cloudflare w połowie), PRZYWRACA starą bazę i kończy się błędem
   (GitHub wyśle wtedy maila), żeby aplikacja nigdy nie dostała okrojonej listy.
3. Opcjonalnie (gdy ustawiona zmienna NF_SERWER) pobiera z serwera słownik lig, żeby nazwy lig,
   których serwer nauczył się w ciągu tygodnia, trafiły na stałe do repozytorium.
"""
import json
import os
import shutil
import sys

import requests

from dopasowanie import wczytaj_kluby

KATALOG = os.path.dirname(os.path.abspath(__file__))
EXCEL = os.path.join(KATALOG, "zawodnicy.xlsx")
MIN_UDZIAL_STAREJ_BAZY = 0.6  # nowa baza musi mieć co najmniej 60% zawodników starej


def policz_zawodnikow(plik):
    return sum(len(info["gracze"]) for info in wczytaj_kluby(plik).values())


def aktualizuj_zawodnikow():
    kopia = EXCEL + ".przed_skanem"
    stara_liczba = policz_zawodnikow(EXCEL) if os.path.exists(EXCEL) else 0
    if os.path.exists(EXCEL): shutil.copy2(EXCEL, kopia)

    try:
        import skaner_zawodnikow
        skaner_zawodnikow.pobierz_zawodnikow()
        nowa_liczba = policz_zawodnikow(EXCEL)
    except Exception as e:
        print(f"Skan nie powiódł się: {e}")
        nowa_liczba = 0

    if nowa_liczba == 0 or nowa_liczba < stara_liczba * MIN_UDZIAL_STAREJ_BAZY:
        if os.path.exists(kopia): shutil.move(kopia, EXCEL)
        print(f"ODRZUCONO nową bazę: {nowa_liczba} zawodników (było {stara_liczba}). Zostaje stara baza.")
        return False

    if os.path.exists(kopia): os.remove(kopia)
    print(f"OK: {nowa_liczba} zawodników (było {stara_liczba}).")
    return True


def pobierz_slownik_lig():
    """Dopisuje do repozytorium nazwy lig, których serwer nauczył się od ostatniego razu (nic nie usuwa
    i nie zmienia - po restarcie serwer może jeszcze nie znać części lig)."""
    serwer = os.environ.get("NF_SERWER", "").rstrip("/")
    if not serwer: return
    plik = os.path.join(KATALOG, "slownik_lig.json")
    try:
        res = requests.get(f"{serwer}/slownik-lig", timeout=180)
        res.raise_for_status()
        z_serwera = res.json()
        with open(plik, encoding="utf-8") as f: nasz = json.load(f)
        nowe = {k: v for k, v in z_serwera.items() if k not in nasz and v.get("nazwa")}
        if nowe:
            nasz.update(nowe)
            with open(plik, "w", encoding="utf-8") as f: json.dump(nasz, f, ensure_ascii=False, indent=4)
        print(f"Słownik lig z serwera: +{len(nowe)} lig ({', '.join(v['nazwa'] for v in nowe.values())}).")
    except Exception as e:
        print(f"Nie udało się pobrać słownika lig z serwera (nieistotne): {e}")


if __name__ == "__main__":
    pobierz_slownik_lig()
    if "--tylko-slownik" in sys.argv: sys.exit(0)
    sys.exit(0 if aktualizuj_zawodnikow() else 1)
