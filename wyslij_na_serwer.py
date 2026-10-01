"""
Narzędzie administratora: aktualizuje bazę zawodników (Transfermarkt) i/lub wysyła
zawodnicy.xlsx oraz ligi.json na serwer NationFootball, skąd pobiorą je wszyscy użytkownicy.

    python wyslij_na_serwer.py            -> zeskanuj Transfermarkt, potem wyślij oba pliki
    python wyslij_na_serwer.py --bez-skanu  -> tylko wyślij obecne pliki

Wymaga zmiennych środowiskowych (albo pliku admin_serwer.txt: 1. linia adres, 2. linia token):
    NF_SERWER       np. https://nationfootball.onrender.com
    NF_ADMIN_TOKEN  ten sam token co ustawiony na serwerze
"""
import os
import sys
import requests

KATALOG = os.path.dirname(os.path.abspath(__file__))


def konfiguracja():
    serwer, token = os.environ.get("NF_SERWER", ""), os.environ.get("NF_ADMIN_TOKEN", "")
    plik = os.path.join(KATALOG, "admin_serwer.txt")
    if (not serwer or not token) and os.path.exists(plik):
        with open(plik, "r", encoding="utf-8") as f:
            linie = [l.strip() for l in f if l.strip()]
        serwer, token = serwer or linie[0], token or linie[1]
    if not serwer or not token:
        sys.exit("Brak NF_SERWER / NF_ADMIN_TOKEN (albo pliku admin_serwer.txt).")
    return serwer.rstrip("/"), token


def main():
    serwer, token = konfiguracja()
    if "--bez-skanu" not in sys.argv:
        import skaner_zawodnikow
        skaner_zawodnikow.pobierz_zawodnikow()

    for nazwa, plik in (("zawodnicy", "zawodnicy.xlsx"), ("ligi", "ligi.json")):
        with open(os.path.join(KATALOG, plik), "rb") as f: tresc = f.read()
        res = requests.post(f"{serwer}/admin/{nazwa}", data=tresc,
                            headers={"X-Admin-Token": token}, timeout=120)
        print(f"{plik}: {res.status_code} {res.text.strip()}")


if __name__ == "__main__":
    main()
