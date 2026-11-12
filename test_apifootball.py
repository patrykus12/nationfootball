"""Test pokrycia API-Football (api-sports.io) względem obecnego API.

Dla wczoraj/dziś/jutro: bierze mecze z udziałem zawodników naszych nacji wyliczone z obecnego API
i sprawdza, ile z nich jest też w API-Football (ta sama godzina +/- 20 min i podobne nazwy drużyn).
Zużycie: 1 zapytanie /status + 3 zapytania /fixtures (API-Football) i do 3 zapytań do obecnego API.
Klucz API-Football: plik apifootball_klucz.txt (poza repozytorium) albo zmienna APIFOOTBALL_KEY.
"""
import difflib
import json
import os
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime, timedelta

import requests

KATALOG = os.path.dirname(os.path.abspath(__file__))
WYNIKI = os.path.join(KATALOG, "serwer_cache", "test_apifootball")
os.makedirs(WYNIKI, exist_ok=True)


def klucz():
    k = os.environ.get("APIFOOTBALL_KEY", "").strip()
    plik = os.path.join(KATALOG, "apifootball_klucz.txt")
    if not k and os.path.exists(plik):
        with open(plik, encoding="utf-8") as f: k = f.read().strip()
    if not k: sys.exit("Brak klucza: wklej go do apifootball_klucz.txt")
    return k


KLUCZ = klucz()


def af_get(endpoint, params=None):
    r = requests.get(f"https://v3.football.api-sports.io/{endpoint}", params=params or {},
                     headers={"x-apisports-key": KLUCZ}, timeout=30)
    r.raise_for_status()
    dane = r.json()
    if dane.get("errors"): print(f"  [API-Football] {endpoint} {params}: błąd {dane['errors']}")
    return dane


SMIECI = {"fc", "cf", "sc", "ac", "fk", "sk", "club", "cd", "ud", "sv", "afc", "ca", "cs", "if", "bk",
          "the", "de", "kv", "nk", "hnk", "gnk", "ks", "mks", "fsv", "vfb", "vfl", "tsv", "us", "ss", "as",
          "rc", "rcd", "sd", "real", "athletic", "atletico", "sporting", "deportivo", "u21", "u23", "ii", "b"}


def norm(nazwa):
    n = unicodedata.normalize("NFKD", str(nazwa or "")).encode("ascii", "ignore").decode().lower()
    slowa = [s for s in re.split(r"[^a-z0-9]+", n) if s and s not in SMIECI and not s.isdigit()]
    return " ".join(slowa) or n


def podobne(a, b):
    a, b = norm(a), norm(b)
    if not a or not b: return 0.0
    if a in b or b in a: return 0.95
    return difflib.SequenceMatcher(None, a, b).ratio()


def main():
    status = af_get("status")
    print("=== Konto API-Football ===")
    print(json.dumps(status.get("response"), indent=1, ensure_ascii=False))

    import pobieranie_danych as pd
    from dopasowanie import NACJE

    dzis = datetime.now(pd.TZ_PL).date()
    dni = [dzis + timedelta(days=o) for o in (-1, 0, 1)]

    # --- API-Football: terminarze dni ---
    af_mecze = []
    for d in dni:
        plik = os.path.join(WYNIKI, f"af_{d:%Y%m%d}.json")
        if os.path.exists(plik):
            with open(plik, encoding="utf-8") as f: odp = json.load(f)
        else:
            odp = af_get("fixtures", {"date": f"{d:%Y-%m-%d}", "timezone": "UTC"})
            if odp.get("response"):
                with open(plik, "w", encoding="utf-8") as f: json.dump(odp, f, ensure_ascii=False)
        print(f"API-Football {d}: {len(odp.get('response') or [])} meczów")
        af_mecze += odp.get("response") or []
    if not af_mecze: sys.exit("API-Football nie zwróciło meczów (pewnie ograniczenie darmowego planu - patrz błąd wyżej).")
    af_ligi = {(m["league"]["country"], m["league"]["name"]) for m in af_mecze}

    # --- obecne API: terminarze tych samych dni (z cache albo 1 zapytanie na dzień) ---
    nasze = []
    for d in dni:
        cache = pd.surowe_z_cache(d)
        mecze = cache["mecze"] if cache else pd._pobierz_dzien_z_api(d)
        print(f"Obecne API     {d}: {len(mecze or [])} meczów")
        nasze += mecze or []
    nasze = list({m["id"]: m for m in nasze if "id" in m}.values())

    # --- mecze naszych nacji (dopasowanie jak na serwerze) ---
    istotne = {}  # id -> mecz z listą nacji
    wspolny = None
    for nacja in NACJE:
        kontekst = pd.kontekst_dopasowania(nacja, wspolny)
        if not kontekst: continue
        wspolny = wspolny or kontekst
        for mecz in nasze:
            m = pd.mecz_nacji(mecz, nacja, kontekst)
            if m:
                istotne.setdefault(m["id"], dict(m, nacje=[]))["nacje"].append(nacja)
    print(f"\nMecze z zawodnikami naszych nacji (obecne API, 3 dni): {len(istotne)}")

    # --- szukamy każdego w API-Football ---
    po_czasie = defaultdict(list)
    for m in af_mecze:
        po_czasie[m["fixture"]["timestamp"] // 60].append(m)

    def znajdz(m):
        """Najpierw ta sama godzina (+/- 20 min); potem do 6 h różnicy, ale tylko przy obu podobnych nazwach."""
        start = int(datetime.fromisoformat(m["start"]).timestamp()) // 60
        najlepszy, wynik = None, 0
        for minuta in range(start - 360, start + 361):
            blisko = abs(minuta - start) <= 20
            for k in po_czasie.get(minuta, []):
                g = podobne(m["gosp"], k["teams"]["home"]["name"])
                a = podobne(m["gosc"], k["teams"]["away"]["name"])
                if blisko:
                    w = (g + a) / 2 if min(g, a) >= 0.5 else (max(g, a) if max(g, a) >= 0.85 else 0)
                else:
                    w = (g + a) / 2 - 0.1 if min(g, a) >= 0.7 else 0
                if w > wynik: najlepszy, wynik = k, w
        return najlepszy

    # tylko mecze z okna, które pobraliśmy z API-Football (pliki dni obecnego API zawierają też sąsiednie dni)
    od = min(m["fixture"]["timestamp"] for m in af_mecze)
    do = max(m["fixture"]["timestamp"] for m in af_mecze)
    istotne = {i: m for i, m in istotne.items() if od <= datetime.fromisoformat(m["start"]).timestamp() <= do}
    print(f"W tym w oknie pobranym z API-Football: {len(istotne)}")

    brak_lig, brak_nacji, jest_nacji = Counter(), Counter(), Counter()
    przyklady = defaultdict(list)
    znalezione = 0
    for m in istotne.values():
        k = znajdz(m)
        for n in m["nacje"]: (jest_nacji if k else brak_nacji)[n] += 1
        if k:
            znalezione += 1
        else:
            brak_lig[m["liga"]] += 1
            if len(przyklady[m["liga"]]) < 2: przyklady[m["liga"]].append(f"{m['gosp']} - {m['gosc']} ({m['godzina']})")

    proc = 100 * znalezione / max(1, len(istotne))
    raport = [f"POKRYCIE: {znalezione}/{len(istotne)} meczów naszych nacji jest w API-Football ({proc:.1f}%)",
              f"Wszystkie mecze 3 dni: obecne API {len(nasze)}, API-Football {len(af_mecze)} ({len(af_ligi)} rozgrywek)",
              "", "Ligi z meczami, których nie znaleziono (liczba meczów):"]
    for liga, ile in brak_lig.most_common():
        raport.append(f"  {ile:3}  {liga}   np. {'; '.join(przyklady[liga])}")
    raport += ["", "Nacje z brakami (brak / wszystkie):"]
    for n, ile in sorted(brak_nacji.items(), key=lambda x: -x[1] / (x[1] + jest_nacji[x[0]])):
        raport.append(f"  {n:4} {ile}/{ile + jest_nacji[n]}")
    tekst = "\n".join(raport)
    print("\n" + tekst)
    with open(os.path.join(WYNIKI, "raport.txt"), "w", encoding="utf-8") as f: f.write(tekst)


if __name__ == "__main__":
    main()
