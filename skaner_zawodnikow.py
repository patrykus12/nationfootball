import cloudscraper
from bs4 import BeautifulSoup
import pandas as pd
import time
import os
import re

KATALOG = os.path.dirname(os.path.abspath(__file__))

# --- INTELIGENTNY FILTR LIG CENTRALNYCH ---
# Ile poziomów rozgrywkowych od góry liczy się jako "liga centralna" w danym kraju - czyli
# wszystko AŻ DO poziomu, na którym piramida ligowa jeszcze jest jedną, ogólnokrajową ligą.
# Gdy dany poziom rozpada się na równoległe grupy regionalne (np. niemiecka 4. liga to już
# 5 osobnych Regionallig, hiszpańska 3. liga to 2 grupy Primera Federación) - ten i kolejne
# poziomy są już pomijane. Wartości zweryfikowane 2026-09-17 empirycznie na
# transfermarkt.pl/wettbewerbe/national/wettbewerbe/{land_id} (licząc rozgrywki na poziom).
LIMIT_SZCZEBLI_DLA_KRAJU = {
    "Niemcy": 3, "Austria": 2, "Włochy": 2, "Anglia": 5, "Stany Zjednaczone": 2,
    "Islandia": 3, "Norwegia": 2, "Hiszpania": 2, "Holandia": 3, "Czechy": 2,
    "Cypr": 2, "Portugalia": 3, "Słowacja": 2, "Walia": 1, "Szwajcaria": 3,
    "Szkocja": 4, "Francja": 3, "Irlandia": 3, "Belgia": 2, "Turcja": 2,
    "Dania": 4, "Grecja": 2, "Finlandia": 3, "Gibraltar": 1, "Szwecja": 2,
}
# Kraj spoza powyższej listy (rzadki legionista) - bezpieczny, najczęściej spotykany próg.
DOMYSLNY_LIMIT_SZCZEBLA = 2

# Nazwy rozgrywek, które ZAWSZE liczą się jako niecentralne, niezależnie od tego, co wyjdzie
# z parsowania kodu ligi (np. niemiecka "Regionalliga West" ma kod "RLW3" - regex niżej
# wyłapałby z niego cyfrę "3" i błędnie zaliczył ją do 3. poziomu, mimo że to realnie 4. liga)
SLOWA_KLUCZOWE_NIECENTRALNE = [
    "regionalliga", "oberliga", "landesliga", "bezirksliga", "kreisliga", "verbandsliga",
    "reserve", "reserves", "primavera", "youth", "junior",
    "u23", "u21", "u20", "u19", "u18", "u17",
    "women", "frauen", "femenina", "feminine", "kobiet",
]

def pobierz_zawodnikow():
    print("=== URUCHAMIAM SKANER TRANSFERMARKT (W pełni Dynamiczny) ===")
    print("KROK 1: Otwieram listę państw (odrzucam kwoty i liczby)... \n")

    scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True})

    # --- KROK 1: POBRANIE KRAJÓW Z GŁÓWNEJ LISTY ---
    url_kraje = "https://www.transfermarkt.pl/spieler-statistik/legionaere/statistik/stat/land_id/135/plus/0?land=0"

    try:
        res_kraje = scraper.get(url_kraje, timeout=15)
    except Exception as e:
        print(f"[!] Błąd połączenia przy pobieraniu państw: {e}")
        return

    soup_kraje = BeautifulSoup(res_kraje.text, 'html.parser')

    if "Just a moment" in soup_kraje.text or "cloudflare" in soup_kraje.text.lower():
        print("[!] Cloudflare zablokował Krok 1. Użyj Hotspota z telefonu!")
        return

    kraje_docelowe = {}

    # Lista krajów z tabeli na stronie pokazuje tylko czołówkę (np. top 25 wg wartości
    # rynkowej) - kraje z mniejszą liczbą legionistów (np. Węgry) w ogóle się tam nie
    # pojawiają, mimo że gra tam Polak. Prawdziwym, kompletnym źródłem wszystkich krajów
    # jest rozwijana lista filtra <select name="land"> na tej samej stronie - to sam
    # Transfermarkt na bieżąco oblicza, w których krajach ma zarejestrowanego jakiegoś
    # polskiego legionistę, więc ta lista jest zawsze aktualna (sprawdzone: dała identyczny
    # komplet 131 zawodników co ręczne przeszukanie wszystkich ~250 krajów świata).
    select_kraj = soup_kraje.find('select', {'name': 'land'})
    if select_kraj:
        for opt in select_kraj.find_all('option'):
            wartosc = (opt.get('value') or '').strip()
            nazwa = opt.text.strip()
            if wartosc and wartosc != '0' and len(nazwa) > 2 and nazwa.lower() != "polska":
                kraje_docelowe[nazwa] = int(wartosc)

    if not kraje_docelowe:
        print("[!] Nie udało się pobrać państw.")
        return

    print(f"[+] SUKCES! Znaleziono {len(kraje_docelowe)} rzeczywistych państw!")
    print(f"[+] Na liście są m.in.: {', '.join(list(kraje_docelowe.keys())[:5])}...\n")

    # --- KROK 2: SKANOWANIE KRAJÓW ---
    print("KROK 2: Rozpoczynam bezlitosne skanowanie zawodników...")
    
    wszyscy_zawodnicy = {}
    suma_wszystkich = 0

    for kraj_nazwa, kraj_id in kraje_docelowe.items():
        print(f"-> Skanuję: {kraj_nazwa.ljust(15)}", end="", flush=True)
        
        strona = 1
        znaleziono_w_kraju = 0
        blad_blokady = False
        ostatni_pierwszy_zawodnik = ""
        
        while True:
            print(".", end="", flush=True)
            url = f"https://www.transfermarkt.pl/spieler-statistik/legionaere/statistik/stat/land_id/135/land/{kraj_id}?page={strona}"
            
            try:
                res = scraper.get(url, timeout=(5, 15))
            except Exception:
                print(" [BŁĄD POŁĄCZENIA]", end="")
                blad_blokady = True
                break
                
            if res.status_code == 403 or res.status_code == 429:
                print(f" [BLOKADA {res.status_code}]", end="")
                blad_blokady = True
                break
            elif res.status_code != 200:
                break
                
            soup = BeautifulSoup(res.text, 'html.parser')
            
            if "Just a moment" in soup.text or "cloudflare" in soup.text.lower():
                print(" [CAPTCHA]", end="")
                blad_blokady = True
                break
                
            tabela = soup.select_one("table.items tbody")
            if not tabela: break
                
            wiersze = tabela.select("tr.odd, tr.even")
            if not wiersze: break
                
            pierwszy_zawodnik_na_stronie = wiersze[0].text.strip()
            if pierwszy_zawodnik_na_stronie == ostatni_pierwszy_zawodnik:
                break 
            ostatni_pierwszy_zawodnik = pierwszy_zawodnik_na_stronie
                
            dodani_na_stronie = 0
            for wiersz in wiersze:
                try:
                    kolumny = wiersz.find_all("td")
                    if not kolumny: continue
                        
                    # Warunek: gracz musi mieć jakąkolwiek wycenę rynkową na Transfermarkcie
                    # (odrzuca juniorów/rezerwowych bez wyceny, którzy inaczej zaśmiecaliby bazę)
                    wartosc_rynkowa = kolumny[-1].text.strip()
                    if not wartosc_rynkowa or wartosc_rynkowa in ("-", "?", "brak", "N/A"):
                        continue

                    nazwa_link = wiersz.select_one("td.hauptlink a")
                    if not nazwa_link: continue
                    pelne_imie = nazwa_link.text.strip()

                    klub_img = wiersz.select_one("img.tiny_wappen")
                    klub = klub_img.get('title', klub_img.get('alt', '')).strip() if klub_img else ""
                    if not klub or "Bez klubu" in klub: continue

                    poziom_ligi = 1
                    liga_link = wiersz.select_one("a[href*='wettbewerb']")

                    if liga_link:
                        href = liga_link.get('href', '')
                        nazwa_ligi = liga_link.text.strip().lower()

                        if any(slowo in nazwa_ligi for slowo in SLOWA_KLUCZOWE_NIECENTRALNE):
                            poziom_ligi = 99
                        else:
                            match = re.search(r'wettbewerb/[A-Za-z\-]+(\d+)', href)
                            poziom_ligi = int(match.group(1)) if match else 1

                    max_poziom = LIMIT_SZCZEBLI_DLA_KRAJU.get(kraj_nazwa, DOMYSLNY_LIMIT_SZCZEBLA)
                    
                    if poziom_ligi <= max_poziom:
                        wszyscy_zawodnicy[pelne_imie] = f"[{kraj_nazwa}] {klub}"
                        dodani_na_stronie += 1
                        znaleziono_w_kraju += 1
                        suma_wszystkich += 1
                        
                except Exception:
                    pass
            
            if not wiersze or dodani_na_stronie == 0: 
                break
                
            strona += 1
            time.sleep(1)
            
        if blad_blokady:
            print(" (Przerwano ze względu na blokadę)")
        elif znaleziono_w_kraju > 0:
            print(f" znaleziono {znaleziono_w_kraju} prof.")
        else:
            print(" brak (lub sami amatorzy)")

        time.sleep(1.2)

    print("\n--- PODSUMOWANIE ---")
    if wszyscy_zawodnicy:
        dane_excel = []
        for pelne_imie, klub in wszyscy_zawodnicy.items():
            czesci = pelne_imie.split(" ", 1)
            imie = czesci[0]
            nazwisko = czesci[1] if len(czesci) > 1 else ""
            dane_excel.append({"Imię": imie, "Nazwisko": nazwisko, "Klub": klub})
            
        df = pd.DataFrame(dane_excel)
        df = df.sort_values(by=["Nazwisko", "Imię"])
        
        sciezka_excel = os.path.join(KATALOG, "zawodnicy.xlsx")
        
        if os.path.exists(sciezka_excel):
            stary_plik = os.path.join(KATALOG, "zawodnicy_kopia_zapasowa.xlsx")
            try: os.replace(sciezka_excel, stary_plik)
            except: pass
            
        df.to_excel(sciezka_excel, index=False)
        print(f"GOTOWE! Zapisano {suma_wszystkich} perfekcyjnie wyselekcjonowanych graczy do zawodnicy.xlsx!")
    else:
        print("Nie udało się pobrać zawodników.")

if __name__ == "__main__":
    pobierz_zawodnikow()