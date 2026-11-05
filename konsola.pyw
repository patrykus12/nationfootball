"""
Konsola administratora NationFootball - ręczna aktualizacja baz zawodników z Transfermarktu.

Transfermarkt blokuje serwery GitHuba, więc skan musi iść z domowego internetu. Tu klikasz:
  1. "Skanuj" - wybrane / nieaktualne / wszystkie nacje (kilka naraz, każda w osobnym procesie,
     każda sprawdzana osobno - nieudany skan zostawia starą bazę),
  2. "Wyślij na GitHub" - commit + push zmienionych baz,
  3. serwer od razu pobiera nowe bazy (/cron?repo=1) - widać w nich transfery w aplikacji.

Uruchamianie: dwuklik na "Konsola NationFootball.bat" (albo: pyw konsola.pyw).
"""
import json
import os
import queue
import re
import subprocess
import sys
import threading
import time
import tkinter as tk
from datetime import datetime
from tkinter import messagebox, ttk

import openpyxl
import requests

from dopasowanie import NACJE

KATALOG = os.path.dirname(os.path.abspath(__file__))
SERWER = os.environ.get("NF_SERWER", "https://nationfootball.onrender.com").rstrip("/")
PLIK_SKANOW = os.path.join(KATALOG, "ostatnie_skany.json")   # lokalnie (w .gitignore)
NIEAKTUALNA_PO_DNIACH = 6
PRZERWA_MIEDZY_NACJAMI_S = 5   # łagodnie dla Transfermarktu (zbyt częste wizyty = weryfikacja "czy jesteś człowiekiem")
BEZ_OKNA = 0x08000000 if os.name == "nt" else 0   # CREATE_NO_WINDOW - procesy skanu bez czarnych okienek

KOLORY = {"tlo": "#0b1622", "karta": "#132235", "ramka": "#22364d", "tekst": "#ecf0f1", "wyciszony": "#7f95ab",
          "zloto": "#f1c40f", "zielony": "#2ecc71", "czerwony": "#e74c3c", "zolty": "#f39c12"}


def wczytaj_skany():
    try:
        with open(PLIK_SKANOW, encoding="utf-8") as f: return json.load(f)
    except Exception:
        return {}


def zapisz_skany(skany):
    with open(PLIK_SKANOW + ".tmp", "w", encoding="utf-8") as f: json.dump(skany, f, ensure_ascii=False, indent=1)
    os.replace(PLIK_SKANOW + ".tmp", PLIK_SKANOW)


def policz_zawodnikow(plik):
    sciezka = os.path.join(KATALOG, plik)
    if not os.path.exists(sciezka): return 0
    try:
        wb = openpyxl.load_workbook(sciezka, read_only=True)
        try: return max(0, (wb.active.max_row or 1) - 1)
        finally: wb.close()
    except Exception:
        return 0


def git(*argumenty):
    w = subprocess.run(["git", *argumenty], cwd=KATALOG, capture_output=True, text=True, encoding="utf-8",
                       errors="replace", creationflags=BEZ_OKNA)
    return w.returncode, (w.stdout + w.stderr).strip()


def _wiersze_xlsx(zrodlo):
    wb = openpyxl.load_workbook(zrodlo, read_only=True)
    try: return sorted(tuple("" if v is None else str(v) for v in w) for w in wb.active.iter_rows(values_only=True))
    finally: wb.close()


def zmienione_bazy():
    """Bazy realnie zmienione względem repozytorium. Skaner zapisuje plik zawsze (z nową datą w środku xlsx),
    więc plik z identyczną listą zawodników wraca do wersji z repozytorium - nie wysyłamy pustych zmian."""
    import io
    _, wynik = git("status", "--porcelain", "--", "zawodnicy*.xlsx", "slownik_lig.json")
    pliki = [l[3:].strip().strip('"') for l in wynik.splitlines() if l.strip() and "kopia_zapasowa" not in l]
    zmienione = []
    for plik in pliki:
        if plik.endswith(".xlsx") and os.path.exists(os.path.join(KATALOG, plik)):
            w = subprocess.run(["git", "show", f"HEAD:{plik}"], cwd=KATALOG, capture_output=True, creationflags=BEZ_OKNA)
            try:
                if w.returncode == 0 and _wiersze_xlsx(io.BytesIO(w.stdout)) == _wiersze_xlsx(os.path.join(KATALOG, plik)):
                    git("checkout", "--", plik)
                    continue
            except Exception:
                pass
        zmienione.append(plik)
    return zmienione


class Konsola:
    def __init__(self, okno):
        self.okno = okno
        self.skany = wczytaj_skany()
        self.czasy_git = {}
        self.kolejka_zdarzen = queue.Queue()
        self.procesy = {}
        self.stop = threading.Event()
        self.trwa = False
        okno.title("NationFootball - konsola")
        okno.geometry("1020x720")
        okno.minsize(860, 560)
        okno.configure(bg=KOLORY["tlo"])
        self._styl()
        self._uklad()
        self.wypelnij_tabele()
        threading.Thread(target=self._policz_wszystkich, daemon=True).start()
        threading.Thread(target=self._status_serwera, daemon=True).start()
        self.okno.after(200, self._obsluz_zdarzenia)
        okno.protocol("WM_DELETE_WINDOW", self.zamknij)

    # ------------------------------------------------------------------ wygląd
    def _styl(self):
        s = ttk.Style()
        s.theme_use("clam")
        k = KOLORY
        s.configure(".", background=k["tlo"], foreground=k["tekst"], fieldbackground=k["karta"], font=("Segoe UI", 10))
        s.configure("Treeview", background=k["karta"], foreground=k["tekst"], fieldbackground=k["karta"], rowheight=24,
                    bordercolor=k["ramka"])
        s.configure("Treeview.Heading", background=k["ramka"], foreground=k["tekst"], font=("Segoe UI", 9, "bold"))
        s.map("Treeview", background=[("selected", "#2b4a6b")])
        s.configure("TButton", background=k["karta"], foreground=k["tekst"], bordercolor=k["ramka"], padding=(12, 7))
        s.map("TButton", background=[("active", k["ramka"]), ("disabled", k["tlo"])], foreground=[("disabled", k["wyciszony"])])
        s.configure("Glowny.TButton", background=k["zloto"], foreground="#0d1b2a", font=("Segoe UI", 10, "bold"))
        s.map("Glowny.TButton", background=[("active", "#ffd83d"), ("disabled", k["ramka"])])
        s.configure("Horizontal.TProgressbar", background=k["zloto"], troughcolor=k["karta"], bordercolor=k["ramka"])
        s.configure("TLabel", background=k["tlo"], foreground=k["tekst"])
        s.configure("Wyciszony.TLabel", foreground=k["wyciszony"])
        s.configure("Tytul.TLabel", font=("Segoe UI", 15, "bold"), foreground=k["zloto"])
        s.configure("TCheckbutton", background=k["tlo"], foreground=k["tekst"])
        s.configure("TSpinbox", arrowsize=12)

    def _uklad(self):
        gora = ttk.Frame(self.okno, padding=(14, 12, 14, 4))
        gora.pack(fill="x")
        ttk.Label(gora, text="NATION FOOTBALL · konsola", style="Tytul.TLabel").pack(side="left")
        self.status_serwera = ttk.Label(gora, text="serwer: sprawdzam…", style="Wyciszony.TLabel")
        self.status_serwera.pack(side="right")

        przyciski = ttk.Frame(self.okno, padding=(14, 6))
        przyciski.pack(fill="x")
        self.b_nieaktualne = ttk.Button(przyciski, text=f"▶ Skanuj nieaktualne (> {NIEAKTUALNA_PO_DNIACH} dni)",
                                        style="Glowny.TButton", command=lambda: self.start("nieaktualne"))
        self.b_nieaktualne.pack(side="left")
        self.b_zaznaczone = ttk.Button(przyciski, text="Skanuj zaznaczone", command=lambda: self.start("zaznaczone"))
        self.b_zaznaczone.pack(side="left", padx=6)
        self.b_wszystkie = ttk.Button(przyciski, text="Skanuj wszystkie", command=lambda: self.start("wszystkie"))
        self.b_wszystkie.pack(side="left")
        self.b_stop = ttk.Button(przyciski, text="■ Zatrzymaj", command=self.zatrzymaj, state="disabled")
        self.b_stop.pack(side="left", padx=6)
        ttk.Label(przyciski, text="naraz:").pack(side="left", padx=(12, 4))
        self.watki = tk.IntVar(value=1)
        ttk.Spinbox(przyciski, from_=1, to=2, width=3, textvariable=self.watki, state="readonly").pack(side="left")
        self.b_wyslij = ttk.Button(przyciski, text="⬆ Wyślij na GitHub", style="Glowny.TButton", command=self.wyslij)
        self.b_wyslij.pack(side="right")

        postep = ttk.Frame(self.okno, padding=(14, 2, 14, 6))
        postep.pack(fill="x")
        self.pasek = ttk.Progressbar(postep, mode="determinate")
        self.pasek.pack(fill="x")
        self.opis_postepu = ttk.Label(postep, text="Zaznacz nacje (Ctrl/Shift) albo użyj „Skanuj nieaktualne” - przerwany skan wznowisz tym samym przyciskiem.",
                                      style="Wyciszony.TLabel")
        self.opis_postepu.pack(anchor="w", pady=(4, 0))

        srodek = ttk.PanedWindow(self.okno, orient="horizontal")
        srodek.pack(fill="both", expand=True, padx=14, pady=(0, 12))
        ramka_tab = ttk.Frame(srodek)
        kolumny = ("kod", "kraj", "zawodnikow", "skan", "wynik")
        self.tabela = ttk.Treeview(ramka_tab, columns=kolumny, show="headings", selectmode="extended")
        for kol, tytul, szer, anchor in (("kod", "Kod", 50, "w"), ("kraj", "Kraj", 190, "w"), ("zawodnikow", "Zaw.", 60, "e"),
                                         ("skan", "Ostatni skan", 120, "w"), ("wynik", "Wynik", 230, "w")):
            self.tabela.heading(kol, text=tytul, command=lambda k=kol: self.sortuj(k))
            self.tabela.column(kol, width=szer, anchor=anchor, stretch=kol in ("kraj", "wynik"))
        for tag, kolor in (("ok", KOLORY["zielony"]), ("blad", KOLORY["czerwony"]), ("trwa", KOLORY["zloto"]),
                           ("stara", KOLORY["zolty"]), ("czeka", KOLORY["wyciszony"])):
            self.tabela.tag_configure(tag, foreground=kolor)
        pas = ttk.Scrollbar(ramka_tab, orient="vertical", command=self.tabela.yview)
        self.tabela.configure(yscrollcommand=pas.set)
        self.tabela.pack(side="left", fill="both", expand=True)
        pas.pack(side="right", fill="y")
        srodek.add(ramka_tab, weight=3)

        ramka_log = ttk.Frame(srodek)
        naglowek_logu = ttk.Frame(ramka_log)
        naglowek_logu.pack(fill="x")
        ttk.Label(naglowek_logu, text="Dziennik", style="Wyciszony.TLabel").pack(side="left")
        self.pelny_log = tk.BooleanVar(value=False)
        ttk.Checkbutton(naglowek_logu, text="szczegóły skanu", variable=self.pelny_log).pack(side="right")
        self.log = tk.Text(ramka_log, bg=KOLORY["karta"], fg=KOLORY["tekst"], insertbackground=KOLORY["tekst"],
                           font=("Consolas", 9), wrap="word", relief="flat", borderwidth=0, padx=8, pady=6)
        for tag, kolor in (("ok", KOLORY["zielony"]), ("blad", KOLORY["czerwony"]), ("info", KOLORY["zloto"]),
                           ("wyc", KOLORY["wyciszony"])):
            self.log.tag_configure(tag, foreground=kolor)
        self.log.pack(fill="both", expand=True, pady=(4, 0))
        srodek.add(ramka_log, weight=2)

    # ------------------------------------------------------------------ tabela
    def czas_skanu(self, kod):
        """Ostatni udany skan z konsoli, a gdy go nie było - ostatnia zmiana bazy w repozytorium."""
        info = self.skany.get(kod, {})
        return info.get("czas") or self.czasy_git.get(NACJE[kod]["plik"])

    def _wiersz(self, kod):
        info = self.skany.get(kod, {})
        skan = self.czas_skanu(kod)
        opis = (datetime.fromtimestamp(skan).strftime("%d.%m %H:%M") + ("" if info.get("czas") else " (repo)")) if skan else "nigdy"
        wynik = info.get("wynik", "")
        tag = "ok" if wynik.startswith("OK") else "blad" if wynik and not wynik.startswith("OK") else ""
        if not skan or time.time() - skan > NIEAKTUALNA_PO_DNIACH * 86400: tag = tag or "stara"
        return (kod, NACJE[kod]["nazwa"], info.get("zawodnikow", ""), opis, wynik), tag

    def wypelnij_tabele(self):
        self.tabela.delete(*self.tabela.get_children())
        for kod in NACJE:
            wartosci, tag = self._wiersz(kod)
            self.tabela.insert("", "end", iid=kod, values=wartosci, tags=(tag,) if tag else ())

    def odswiez_wiersz(self, kod, wynik_tymczasowy=None, tag=None):
        wartosci, t = self._wiersz(kod)
        if wynik_tymczasowy is not None: wartosci = wartosci[:4] + (wynik_tymczasowy,)
        self.tabela.item(kod, values=wartosci, tags=((tag or t),) if (tag or t) else ())

    def sortuj(self, kolumna):
        wiersze = [(self.tabela.set(k, kolumna), k) for k in self.tabela.get_children("")]
        liczbowa = kolumna == "zawodnikow"
        wiersze.sort(key=lambda w: (int(w[0]) if str(w[0]).isdigit() else -1) if liczbowa else str(w[0]).lower(),
                     reverse=liczbowa)
        for i, (_, k) in enumerate(wiersze): self.tabela.move(k, "", i)

    def _policz_wszystkich(self):
        # Data ostatniej zmiany każdej bazy w repozytorium - jednym wywołaniem gita
        _, wynik = git("log", "--format=@%ct", "--name-only", "--", "zawodnicy*.xlsx")
        czas = None
        for linia in wynik.splitlines():
            if linia.startswith("@"): czas = int(linia[1:])
            elif linia.strip() and czas and linia.strip() not in self.czasy_git: self.czasy_git[linia.strip()] = czas
        for kod in NACJE:
            n = policz_zawodnikow(NACJE[kod]["plik"])
            self.skany.setdefault(kod, {})["zawodnikow"] = n
            self.kolejka_zdarzen.put(("wiersz", kod))

    def _status_serwera(self):
        try:
            d = requests.get(f"{SERWER}/", timeout=60).json()
            z = d.get("zuzycie_api") or {}
            tekst = (f"serwer: OK · API ~{z.get('szacunek_na_30_dni', '?')}/mies. · "
                     f"zostało w limicie {d.get('pozostalo_w_limicie_api', '?')} · cykl {str(d.get('ostatni_cykl_harmonogramu') or '-')[11:]}")
        except Exception as e:
            tekst = f"serwer: brak odpowiedzi ({type(e).__name__})"
        self.kolejka_zdarzen.put(("serwer", tekst))

    # ------------------------------------------------------------------ dziennik
    def pisz(self, tekst, tag=None):
        self.log.insert("end", tekst + "\n", (tag,) if tag else ())
        if int(self.log.index("end-1c").split(".")[0]) > 4000: self.log.delete("1.0", "1000.0")
        self.log.see("end")

    def _obsluz_zdarzenia(self):
        try:
            while True:
                zd = self.kolejka_zdarzen.get_nowait()
                rodzaj = zd[0]
                if rodzaj == "log": self.pisz(zd[1], zd[2] if len(zd) > 2 else None)
                elif rodzaj == "wiersz": self.odswiez_wiersz(zd[1])
                elif rodzaj == "trwa": self.odswiez_wiersz(zd[1], "skanuję…", "trwa")
                elif rodzaj == "postep":
                    zrobione, razem, start = zd[1], zd[2], zd[3]
                    self.pasek.configure(maximum=max(razem, 1), value=zrobione)
                    eta = ""
                    if zrobione:
                        zostalo = (time.time() - start) / zrobione * (razem - zrobione)
                        eta = f" · zostało ok. {int(zostalo // 3600)} h {int(zostalo % 3600 // 60)} min" if zostalo >= 3600 \
                            else f" · zostało ok. {int(zostalo // 60) + 1} min"
                    self.opis_postepu.configure(text=f"Zeskanowano {zrobione} z {razem}{eta if zrobione < razem else ''}")
                elif rodzaj == "koniec": self._koniec(*zd[1:])
                elif rodzaj == "serwer": self.status_serwera.configure(text=zd[1])
                elif rodzaj == "wyslano": self._po_wyslaniu(*zd[1:])
        except queue.Empty:
            pass
        self.okno.after(200, self._obsluz_zdarzenia)

    # ------------------------------------------------------------------ skanowanie
    def _przyciski(self, skan_trwa):
        stan = "disabled" if skan_trwa else "normal"
        for b in (self.b_nieaktualne, self.b_zaznaczone, self.b_wszystkie, self.b_wyslij): b.configure(state=stan)
        self.b_stop.configure(state="normal" if skan_trwa else "disabled")

    def start(self, tryb):
        if self.trwa: return
        if tryb == "zaznaczone":
            kody = [k for k in self.tabela.selection()]
            if not kody:
                messagebox.showinfo("NationFootball", "Zaznacz w tabeli nacje do skanowania (Ctrl/Shift + klik).")
                return
        elif tryb == "wszystkie":
            kody = list(NACJE)
            if not messagebox.askyesno("NationFootball", f"Skanować wszystkie {len(kody)} nacje? To potrwa kilka godzin "
                                                          "(przerwany skan dokończysz przyciskiem „Skanuj nieaktualne”)."):
                return
        else:
            granica = time.time() - NIEAKTUALNA_PO_DNIACH * 86400
            kody = [k for k in NACJE if (self.czas_skanu(k) or 0) < granica
                    or (self.skany.get(k, {}).get("wynik") and not self.skany[k]["wynik"].startswith("OK"))]
            if not kody:
                messagebox.showinfo("NationFootball", "Wszystkie nacje są aktualne.")
                return
        # Najpierw duże bazy - im dłużej trwają, tym lepiej, żeby szły równolegle z małymi
        kody.sort(key=lambda k: -int(self.skany.get(k, {}).get("zawodnikow") or 0))
        self.trwa = True
        self.stop.clear()
        self._przyciski(True)
        for k in kody: self.odswiez_wiersz(k, "w kolejce", "czeka")
        self.pisz(f"=== {datetime.now():%d.%m %H:%M} skan {len(kody)} nacji, {self.watki.get()} naraz ===", "info")
        threading.Thread(target=self._skanuj, args=(kody, self.watki.get()), daemon=True).start()

    def _skanuj(self, kody, ile_naraz):
        kolejka = queue.Queue()
        for k in kody: kolejka.put(k)
        start, zrobione, wyniki = time.time(), [0], {"ok": 0, "blad": 0}
        blokada = threading.Lock()
        self.kolejka_zdarzen.put(("postep", 0, len(kody), start))

        def pracownik():
            while not self.stop.is_set():
                try: kod = kolejka.get_nowait()
                except queue.Empty: return
                self.kolejka_zdarzen.put(("trwa", kod))
                ok, opis = self._skanuj_nacje(kod)
                with blokada:
                    zrobione[0] += 1
                    wyniki["ok" if ok else "blad"] += 1
                    self.skany.setdefault(kod, {}).update(wynik=opis, **({"czas": time.time()} if ok else {}))
                    self.skany[kod]["zawodnikow"] = policz_zawodnikow(NACJE[kod]["plik"])
                    zapisz_skany(self.skany)
                self.kolejka_zdarzen.put(("wiersz", kod))
                self.kolejka_zdarzen.put(("postep", zrobione[0], len(kody), start))
                if opis.startswith("WERYFIKACJA"):
                    # Dalsze próby tylko przedłużyłyby blokadę - stop całego skanu
                    self.stop.set()
                    self.kolejka_zdarzen.put(("log", "Transfermarkt poprosił o weryfikację „czy jesteś człowiekiem” - skan przerwany. "
                                                     "Odczekaj kilka godzin i kliknij „Skanuj nieaktualne” (dokończy resztę).", "blad"))
                    return
                self.stop.wait(PRZERWA_MIEDZY_NACJAMI_S)

        watki = [threading.Thread(target=pracownik, daemon=True) for _ in range(max(1, min(2, ile_naraz)))]
        for w in watki: w.start()
        for w in watki: w.join()
        self.kolejka_zdarzen.put(("koniec", wyniki, time.time() - start, self.stop.is_set()))

    def _skanuj_nacje(self, kod):
        """Jedna nacja w osobnym procesie (aktualizuj_baze_automatycznie --nacja) - zwraca (ok, opis)."""
        env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUNBUFFERED="1")
        try:
            p = subprocess.Popen([sys.executable.replace("pythonw", "python"), "aktualizuj_baze_automatycznie.py", "--nacja", kod],
                                 cwd=KATALOG, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                                 encoding="utf-8", errors="replace", env=env, creationflags=BEZ_OKNA)
        except Exception as e:
            return False, f"BŁĄD uruchomienia: {e}"
        self.procesy[kod] = p
        podsumowanie, cloudflare, weryfikacja = [], False, False
        for linia in p.stdout:
            linia = linia.rstrip()
            if not linia: continue
            if "WERYFIKACJA" in linia: weryfikacja = True
            if "Cloudflare" in linia or "Nie udało się pobrać państw" in linia: cloudflare = True
            if linia.startswith(f"[{kod}]"):
                podsumowanie.append(linia)
                self.kolejka_zdarzen.put(("log", linia, "ok" if " OK " in linia else "blad"))
            elif self.pelny_log.get():
                self.kolejka_zdarzen.put(("log", f"  {kod}: {linia}", "wyc"))
        p.wait()
        self.procesy.pop(kod, None)
        if self.stop.is_set() and p.returncode != 0: return False, "przerwano"
        if p.returncode == 0:
            m = re.search(r"OK \S+: (\d+) zawodników \(było (\d+)\)", podsumowanie[0] if podsumowanie else "")
            return True, f"OK {m.group(1)} (było {m.group(2)})" if m else "OK"
        if weryfikacja: return False, "WERYFIKACJA Transfermarktu - odczekaj kilka godzin"
        if cloudflare: return False, "BŁĄD: Transfermarkt nie odpowiedział / blokada"
        odrzucone = next((l for l in podsumowanie if "ODRZUCONO" in l), None)
        if odrzucone:
            m = re.search(r": (\d+) zawodników \(było (\d+)\)", odrzucone)
            return False, f"ODRZUCONO {m.group(1)} (było {m.group(2)}) - zostaje stara" if m else "ODRZUCONO - zostaje stara"
        return False, "BŁĄD (szczegóły w dzienniku)"

    def zatrzymaj(self):
        if not self.trwa: return
        self.stop.set()
        self.pisz("Zatrzymuję - przerwane nacje zostają ze starą bazą…", "info")
        for p in list(self.procesy.values()):
            try: p.terminate()
            except Exception: pass

    def _koniec(self, wyniki, czas, przerwano):
        self.trwa = False
        self._przyciski(False)
        min_ = int(czas // 60)
        self.pisz(f"=== {'PRZERWANO' if przerwano else 'KONIEC'}: {wyniki['ok']} OK, {wyniki['blad']} z błędem · {min_} min ===", "info")
        zmiany = zmienione_bazy()
        if zmiany:
            self.pisz(f"Zmienione bazy: {len(zmiany)} - kliknij „Wyślij na GitHub”.", "info")
        elif not przerwano:
            self.pisz("Bazy bez zmian - nie ma czego wysyłać.", "wyc")
        # *.przed_skanem po przerwanym procesie - przywróć starą bazę
        from dopasowanie import ma_szeroka_baze, plik_szerokiej_bazy
        for kod in NACJE:
            for plik in [NACJE[kod]["plik"]] + ([plik_szerokiej_bazy(kod)] if ma_szeroka_baze(kod) else []):
                sciezka = os.path.join(KATALOG, plik)
                if os.path.exists(sciezka + ".przed_skanem"):
                    os.replace(sciezka + ".przed_skanem", sciezka)
                    self.pisz(f"[{kod}] przywrócono starą bazę {plik} (skan przerwany w trakcie)", "wyc")

    # ------------------------------------------------------------------ wysyłanie
    def wyslij(self):
        zmiany = zmienione_bazy()
        if not zmiany:
            messagebox.showinfo("NationFootball", "Brak zmienionych baz do wysłania.")
            return
        if not messagebox.askyesno("NationFootball", f"Wysłać {len(zmiany)} zmienionych plików na GitHub?\n\n"
                                                      + "\n".join(zmiany[:15]) + ("\n…" if len(zmiany) > 15 else "")):
            return
        self._przyciski(True)
        self.b_stop.configure(state="disabled")
        self.pisz(f"Wysyłam {len(zmiany)} plików…", "info")
        threading.Thread(target=self._wyslij, args=(zmiany,), daemon=True).start()

    def _wyslij(self, zmiany):
        kroki = []
        kod, out = git("add", "--", *zmiany)
        kroki.append(("add", kod, out))
        nacje = sorted({re.sub(r"^zawodnicy_?|(_wszyscy)?\.xlsx$", "", z) or "pl" for z in zmiany if z.endswith(".xlsx")})
        tresc = (f"Baza zawodnikow (konsola): {len(nacje)} nacji - {', '.join(nacje[:40])}{' ...' if len(nacje) > 40 else ''}"
                 " [skip render]")
        if kod == 0:
            kod, out = git("commit", "-m", tresc)
            kroki.append(("commit", kod, out))
        if kod == 0:
            kod, out = git("pull", "--rebase", "--autostash", "origin", "main")
            kroki.append(("pull", kod, out))
        if kod == 0:
            kod, out = git("push", "origin", "main")
            kroki.append(("push", kod, out))
        serwer = None
        if kod == 0:
            try:
                serwer = requests.get(f"{SERWER}/cron", params={"repo": "1"}, timeout=90).status_code
            except Exception as e:
                serwer = type(e).__name__
        self.kolejka_zdarzen.put(("wyslano", kroki, kod == 0, serwer))

    def _po_wyslaniu(self, kroki, ok, serwer):
        for nazwa, kod, out in kroki:
            self.pisz(f"git {nazwa}: {'ok' if kod == 0 else 'BŁĄD'}", "ok" if kod == 0 else "blad")
            if kod != 0 and out: self.pisz(out[-1500:], "wyc")
        if ok:
            self.pisz(f"Wysłano. Serwer pobiera nowe bazy ({serwer}) - transfery pojawią się w aplikacji po jego cyklu.", "ok")
        self._przyciski(False)
        threading.Thread(target=self._status_serwera, daemon=True).start()

    def zamknij(self):
        if self.trwa and not messagebox.askyesno("NationFootball", "Skan trwa. Przerwać i zamknąć?"): return
        self.zatrzymaj()
        self.okno.destroy()


if __name__ == "__main__":
    okno = tk.Tk()
    Konsola(okno)
    okno.mainloop()
