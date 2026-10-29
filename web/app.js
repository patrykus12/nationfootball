"use strict";
// NationFootball na telefon - wszystko liczy serwer (/api/dzien/YYYYMMDD), strona tylko wyświetla.

const DNI_WSTECZ = 14, DNI_NAPRZOD = 14;
const ODSWIEZANIE_MS = 3 * 60 * 1000;          // dziś/wczoraj: co 3 min, gdy aplikacja jest na ekranie
const DNI_TYG = ["nd", "pn", "wt", "śr", "cz", "pt", "sb"];
const DNI_TYG_PELNE = ["Niedziela", "Poniedziałek", "Wtorek", "Środa", "Czwartek", "Piątek", "Sobota"];
const MIESIACE = ["stycznia", "lutego", "marca", "kwietnia", "maja", "czerwca", "lipca", "sierpnia",
                  "września", "października", "listopada", "grudnia"];

// Śledzone nacje (te same kody co dopasowanie.NACJE na serwerze); formy: 1 / 2-4 / 5+
const NACJE = {
  pl: { nazwa: "Polacy", kraj: "Polska", flaga: "pl", formy: ["Polak", "Polaków", "Polaków"], dopelniacz: "Polaków" },
  tr: { nazwa: "Turcy", kraj: "Turcja", flaga: "tr", formy: ["Turek", "Turków", "Turków"], dopelniacz: "Turków" },
  in: { nazwa: "Hindusi", kraj: "Indie", flaga: "in", formy: ["Hindus", "Hindusów", "Hindusów"], dopelniacz: "Hindusów" },
  cn: { nazwa: "Chińczycy", kraj: "Chiny", flaga: "cn", formy: ["Chińczyk", "Chińczyków", "Chińczyków"], dopelniacz: "Chińczyków" },
  us: { nazwa: "Amerykanie", kraj: "USA", flaga: "us", formy: ["Amerykanin", "Amerykanów", "Amerykanów"], dopelniacz: "Amerykanów" },
  cz: { nazwa: "Czesi", kraj: "Czechy", flaga: "cz", formy: ["Czech", "Czechów", "Czechów"], dopelniacz: "Czechów" },
  id: { nazwa: "Indonezyjczycy", kraj: "Indonezja", flaga: "id", formy: ["Indonezyjczyk", "Indonezyjczyków", "Indonezyjczyków"], dopelniacz: "Indonezyjczyków" },
  pk: { nazwa: "Pakistańczycy", kraj: "Pakistan", flaga: "pk", formy: ["Pakistańczyk", "Pakistańczyków", "Pakistańczyków"], dopelniacz: "Pakistańczyków" },
  ng: { nazwa: "Nigeryjczycy", kraj: "Nigeria", flaga: "ng", formy: ["Nigeryjczyk", "Nigeryjczyków", "Nigeryjczyków"], dopelniacz: "Nigeryjczyków" },
  br: { nazwa: "Brazylijczycy", kraj: "Brazylia", flaga: "br", formy: ["Brazylijczyk", "Brazylijczyków", "Brazylijczyków"], dopelniacz: "Brazylijczyków" },
  bd: { nazwa: "Banglijczycy", kraj: "Bangladesz", flaga: "bd", formy: ["Banglijczyk", "Banglijczyków", "Banglijczyków"], dopelniacz: "Banglijczyków" },
  mx: { nazwa: "Meksykanie", kraj: "Meksyk", flaga: "mx", formy: ["Meksykanin", "Meksykanów", "Meksykanów"], dopelniacz: "Meksykanów" },
  jp: { nazwa: "Japończycy", kraj: "Japonia", flaga: "jp", formy: ["Japończyk", "Japończyków", "Japończyków"], dopelniacz: "Japończyków" },
  ph: { nazwa: "Filipińczycy", kraj: "Filipiny", flaga: "ph", formy: ["Filipińczyk", "Filipińczyków", "Filipińczyków"], dopelniacz: "Filipińczyków" },
  et: { nazwa: "Etiopczycy", kraj: "Etiopia", flaga: "et", formy: ["Etiopczyk", "Etiopczyków", "Etiopczyków"], dopelniacz: "Etiopczyków" },
  cd: { nazwa: "Kongijczycy", kraj: "DR Konga", flaga: "cd", formy: ["Kongijczyk", "Kongijczyków", "Kongijczyków"], dopelniacz: "Kongijczyków" },
  eg: { nazwa: "Egipcjanie", kraj: "Egipt", flaga: "eg", formy: ["Egipcjanin", "Egipcjan", "Egipcjan"], dopelniacz: "Egipcjan" },
  vn: { nazwa: "Wietnamczycy", kraj: "Wietnam", flaga: "vn", formy: ["Wietnamczyk", "Wietnamczyków", "Wietnamczyków"], dopelniacz: "Wietnamczyków" },
  ir: { nazwa: "Irańczycy", kraj: "Iran", flaga: "ir", formy: ["Irańczyk", "Irańczyków", "Irańczyków"], dopelniacz: "Irańczyków" },
  de: { nazwa: "Niemcy", kraj: "Niemcy", flaga: "de", formy: ["Niemiec", "Niemców", "Niemców"], dopelniacz: "Niemców" },
  th: { nazwa: "Tajowie", kraj: "Tajlandia", flaga: "th", formy: ["Taj", "Tajów", "Tajów"], dopelniacz: "Tajów" },
};
const KLUCZ_NACJI = "nf-nacja";

const $ = (id) => document.getElementById(id);
const pamiec = {};          // "nacja:YYYYMMDD" -> odpowiedź serwera
let wybrany = null;          // "YYYYMMDD"
let nacja = null;            // klucz z NACJE
let zapytanie = 0;           // chroni przed nadpisaniem widoku starszą odpowiedzią

// --- DATY (zawsze czas polski, niezależnie od strefy telefonu) ---
function dzisPL() {
  const [r, m, d] = new Intl.DateTimeFormat("en-CA", { timeZone: "Europe/Warsaw", year: "numeric", month: "2-digit", day: "2-digit" })
    .format(new Date()).split("-").map(Number);
  return new Date(Date.UTC(r, m - 1, d));
}
const klucz = (data) => data.toISOString().slice(0, 10).replace(/-/g, "");
const zKlucza = (k) => new Date(Date.UTC(+k.slice(0, 4), +k.slice(4, 6) - 1, +k.slice(6, 8)));
const przesun = (data, dni) => new Date(data.getTime() + dni * 86400000);

function tytulDnia(k) {
  const data = zKlucza(k), roznica = Math.round((data - dzisPL()) / 86400000);
  const opis = `${data.getUTCDate()} ${MIESIACE[data.getUTCMonth()]}`;
  if (roznica === 0) return `Dziś, ${opis}`;
  if (roznica === -1) return `Wczoraj, ${opis}`;
  if (roznica === 1) return `Jutro, ${opis}`;
  return `${DNI_TYG_PELNE[data.getUTCDay()]}, ${opis}`;
}

// --- PASEK DNI ---
function zbudujDni() {
  const dzis = dzisPL(), kDzis = klucz(dzis), nav = $("dni");
  nav.innerHTML = "";
  for (let i = -DNI_WSTECZ; i <= DNI_NAPRZOD; i++) {
    const d = przesun(dzis, i), k = klucz(d);
    const b = document.createElement("button");
    b.className = "dzien" + (k === kDzis ? " dzis" : "") + (k === wybrany ? " wybrany" : "");
    b.dataset.k = k;
    b.innerHTML = `<span class="dt">${k === kDzis ? "dziś" : DNI_TYG[d.getUTCDay()]}</span><span class="dn">${d.getUTCDate()}</span>`;
    b.addEventListener("click", () => wybierzDzien(k));
    nav.appendChild(b);
  }
}

function zaznaczDzien(plynnie) {
  document.querySelectorAll(".dzien").forEach((b) => b.classList.toggle("wybrany", b.dataset.k === wybrany));
  const b = document.querySelector(`.dzien[data-k="${wybrany}"]`);
  if (b) b.scrollIntoView({ inline: "center", block: "nearest", behavior: plynnie ? "smooth" : "auto" });
}

function wybierzDzien(k, plynnie = true) {
  wybrany = k;
  zaznaczDzien(plynnie);
  $("tytul-dnia").textContent = tytulDnia(k);
  const zapamietane = pamiec[`${nacja}:${k}`];
  if (zapamietane) pokaz(zapamietane); else pokazSzkielet();
  pobierz(k);
}

// --- POBIERANIE ---
async function pobierz(k) {
  const nr = ++zapytanie, n = nacja, klucz = `${n}:${k}`;
  $("odswiez").classList.add("kreci");
  try {
    const res = await fetch(`/api/dzien/${k}?nacja=${n}`, { cache: "no-store" });
    if (res.status === 404) {
      if (nr === zapytanie) pokazKomunikat("⏳", "Serwer nie ma jeszcze danych dla tego dnia", "Spróbuj ponownie za kilka minut.");
      return;
    }
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const dane = await res.json();
    dane.offline = res.headers.get("X-Z-Pamieci") === "1";
    pamiec[klucz] = dane;
    if (nr === zapytanie && k === wybrany && n === nacja) pokaz(dane);
  } catch (e) {
    if (nr === zapytanie && !pamiec[klucz]) pokazKomunikat("📡", "Brak połączenia z serwerem", "Sprawdź internet i dotknij przycisku odświeżania.");
  } finally {
    if (nr === zapytanie) $("odswiez").classList.remove("kreci");
  }
}

// --- WIDOK ---
const esc = (t) => String(t ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

const flagaNacji = (n) => `<img class="flaga" src="https://flagcdn.com/w40/${NACJE[n].flaga}.png" alt="">`;

function flagaHTML(kod) {
  kod = (kod || "").toLowerCase();
  if (!kod || ["int", "none", "world", "international"].includes(kod)) return `<span class="flaga-swiat">🌍</span>`;
  return `<img class="flaga" src="https://flagcdn.com/w40/${esc(kod)}.png" alt="" loading="lazy" onerror="this.outerHTML='<span class=&quot;flaga-swiat&quot;>🌍</span>'">`;
}

// Jak w aplikacji na komputer: pierwszy człon nazwy klubu, chyba że jest liczbą albo zbyt krótki (FC, St...)
function skrotKlubu(nazwa) {
  if (!nazwa) return "";
  const pierwszy = nazwa.split(" ")[0], rdzen = pierwszy.replace(/\.+$/, "");
  return (/^\d+$/.test(rdzen) || rdzen.length <= 3) ? nazwa : pierwszy;
}

function klasaOceny(o) { return o >= 7.5 ? "wysoka" : o >= 6.5 ? "srednia" : "niska"; }

function graczHTML(klub, g) {
  let wyczyny = "";
  if (g.gole) wyczyny += g.gole > 1 ? `${g.gole}×⚽` : "⚽";
  if (g.asysty) wyczyny += (wyczyny ? " " : "") + (g.asysty > 1 ? `${g.asysty}×🅰️` : "🅰️");
  const szczegoly = [`<span class="klub">${esc(skrotKlubu(klub))}</span>`];
  if (g.minuty_tekst) szczegoly.push(esc(g.minuty_tekst));
  const ocena = g.ocena != null ? `<span class="ocena ${klasaOceny(g.ocena)}">${Number(g.ocena).toFixed(1)}</span>` : "";
  return `<div class="gracz${g.aktywny === false ? " nie-gral" : ""}">
    <div class="opis"><div class="imie">${esc(g.nazwa)}</div><div class="szczegoly">${szczegoly.join(" · ")}</div></div>
    ${wyczyny ? `<span class="wyczyny">${wyczyny}</span>` : ""}${ocena}</div>`;
}

function kartaHTML(m) {
  let status, klasa = "";
  if (m.odwolany) { status = "odwołany"; klasa = "odwolany"; }
  else if (m.zakonczony) status = "koniec";
  else if (m.rozpoczety) { status = "w trakcie"; klasa = "trwa"; }
  else status = m.godzina;

  const [gg, gs] = (m.wynik || "").split(":").map((x) => x.trim());
  const maWynik = m.zakonczony && gg !== undefined && gs !== undefined && gg !== "";
  const druzyna = (nazwa, gole, rywal, nasza) =>
    `<div class="druzyna${nasza ? " nasza" : ""}"><span class="nazwa">${esc(nazwa)}${nasza ? flagaNacji(nacja) : ""}</span>` +
    `<span class="gole${maWynik && +gole > +rywal ? " wygrana" : ""}">${maWynik ? esc(gole) : ""}</span></div>`;

  const gracze = m.gracze_gosp.map((g) => graczHTML(m.gosp, g)).concat(m.gracze_gosc.map((g) => graczHTML(m.gosc, g)));
  return `<article class="karta">
    <div class="karta-liga">${flagaHTML(m.flaga)}<span class="nazwa">${esc(m.liga)}</span>
      <span class="status ${klasa}">${m.zakonczony || m.rozpoczety ? esc(m.godzina) + " · " : ""}${esc(status)}</span></div>
    <div class="druzyny">${druzyna(m.gosp, gg, gs, m.gracze_gosp.length)}${druzyna(m.gosc, gs, gg, m.gracze_gosc.length)}</div>
    <div class="gracze">${gracze.join("")}</div>
  </article>`;
}

function pokaz(dane) {
  const mecze = dane.mecze || [];
  const gracze = mecze.reduce((s, m) => s + m.gracze_gosp.length + m.gracze_gosc.length, 0), formy = NACJE[nacja].formy;
  const odmiana = (n, a, b, c) => n === 1 ? a : (n % 10 >= 2 && n % 10 <= 4 && (n % 100 < 10 || n % 100 >= 20)) ? b : c;
  const stan = dane.stan_na ? ` · stan z ${dane.stan_na.slice(11)}` : "";
  $("podsumowanie").innerHTML = mecze.length
    ? `${mecze.length} ${odmiana(mecze.length, "mecz", "mecze", "meczów")} · ${gracze} ${odmiana(gracze, ...formy)}${stan}` +
      (dane.offline ? ` <span class="offline">· bez internetu</span>` : "")
    : "";
  $("lista").innerHTML = mecze.length ? mecze.map(kartaHTML).join("")
    : `<div class="komunikat"><div class="duza">🏟️</div><b>Brak meczów ${NACJE[nacja].dopelniacz}</b>Tego dnia żaden z nich nie gra.</div>`;
}

function pokazSzkielet() {
  $("podsumowanie").textContent = "Wczytywanie…";
  $("lista").innerHTML = '<div class="szkielet"></div>'.repeat(4);
}

function pokazKomunikat(ikona, tytul, tekst) {
  $("podsumowanie").textContent = "";
  $("lista").innerHTML = `<div class="komunikat"><div class="duza">${ikona}</div><b>${esc(tytul)}</b>${esc(tekst)}</div>`;
}

// --- GESTY: przesunięcie palcem w bok zmienia dzień ---
(function () {
  let x0 = null, y0 = null;
  const glowna = $("glowna");
  glowna.addEventListener("touchstart", (e) => { x0 = e.touches[0].clientX; y0 = e.touches[0].clientY; }, { passive: true });
  glowna.addEventListener("touchend", (e) => {
    if (x0 === null) return;
    const dx = e.changedTouches[0].clientX - x0, dy = e.changedTouches[0].clientY - y0;
    x0 = null;
    if (Math.abs(dx) < 70 || Math.abs(dx) < Math.abs(dy) * 1.5) return;
    const nowy = przesun(zKlucza(wybrany), dx < 0 ? 1 : -1), dzis = dzisPL();
    if (nowy < przesun(dzis, -DNI_WSTECZ) || nowy > przesun(dzis, DNI_NAPRZOD)) return;
    wybierzDzien(klucz(nowy));
  }, { passive: true });
})();

// --- WYBÓR NACJI: przy pierwszym uruchomieniu, potem przyciskiem z flagą ---
function wczytajNacje() {
  try { const n = localStorage.getItem(KLUCZ_NACJI); return NACJE[n] ? n : null; } catch (e) { return null; }
}

function ustawNacje(n) {
  const zmiana = n !== nacja;
  nacja = n;
  try { localStorage.setItem(KLUCZ_NACJI, n); } catch (e) {}
  const b = $("zmien-nacje");
  b.innerHTML = flagaNacji(n);
  b.setAttribute("aria-label", `Zmień kraj (teraz: ${NACJE[n].kraj})`);
  b.hidden = false;
  zamknijWyborNacji();
  if (zmiana) wybierzDzien(wybrany, false);
}

function otworzWyborNacji() {
  $("nacje").innerHTML = Object.entries(NACJE).map(([k, n]) =>
    `<button class="nacja${k === nacja ? " obecna" : ""}" data-n="${k}">${flagaNacji(k)}` +
    `<span><b>${esc(n.kraj)}</b></span></button>`).join("");
  $("nacje").querySelectorAll(".nacja").forEach((b) => b.addEventListener("click", () => ustawNacje(b.dataset.n)));
  $("zamknij-wybor").hidden = !nacja;     // przy pierwszym uruchomieniu wybór jest obowiązkowy
  $("wybor-nacji").hidden = false;
}

function zamknijWyborNacji() { $("wybor-nacji").hidden = true; }

$("zmien-nacje").addEventListener("click", otworzWyborNacji);
$("zamknij-wybor").addEventListener("click", zamknijWyborNacji);
$("wybor-nacji").addEventListener("click", (e) => { if (e.target === e.currentTarget && nacja) zamknijWyborNacji(); });
document.addEventListener("keydown", (e) => { if (e.key === "Escape" && nacja) zamknijWyborNacji(); });

// --- START ---
$("odswiez").addEventListener("click", () => { if (nacja) pobierz(wybrany); });

function czyAktualnyDzien() {
  const roznica = Math.round((zKlucza(wybrany) - dzisPL()) / 86400000);
  return roznica === 0 || roznica === -1;
}
setInterval(() => { if (nacja && document.visibilityState === "visible" && czyAktualnyDzien()) pobierz(wybrany); }, ODSWIEZANIE_MS);
let ostatniDzien = klucz(dzisPL());
document.addEventListener("visibilitychange", () => {
  if (document.visibilityState !== "visible" || !nacja) return;
  const teraz = klucz(dzisPL());
  if (teraz !== ostatniDzien) {          // aplikacja wisiała w tle przez północ
    ostatniDzien = teraz;
    zbudujDni();
    wybierzDzien(teraz, false);
  } else {
    pobierz(wybrany);
  }
});

// Instalacja na ekranie głównym (Chrome na Androidzie)
let prosbaInstalacji = null;
window.addEventListener("beforeinstallprompt", (e) => { e.preventDefault(); prosbaInstalacji = e; $("instaluj").hidden = false; });
$("instaluj").addEventListener("click", async () => {
  if (!prosbaInstalacji) return;
  prosbaInstalacji.prompt();
  await prosbaInstalacji.userChoice;
  prosbaInstalacji = null;
  $("instaluj").hidden = true;
});
window.addEventListener("appinstalled", () => { $("instaluj").hidden = true; });

// iPhone/iPad: Safari nie ma przycisku instalacji - pokazujemy, jak dodać aplikację do ekranu
// początkowego. Tylko poza zainstalowaną aplikacją; po zamknięciu wraca najwcześniej po 14 dniach.
(function () {
  const ios = /iphone|ipad|ipod/i.test(navigator.userAgent) ||
    (navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1);  // iPadOS udaje Maca
  const zainstalowana = navigator.standalone === true || window.matchMedia("(display-mode: standalone)").matches;
  if (!ios || zainstalowana) return;
  let zamknieto = 0;
  try { zamknieto = +localStorage.getItem("nf-wskazowka-ios") || 0; } catch (e) {}
  if (Date.now() - zamknieto < 14 * 86400000) return;
  $("wskazowka-ios").hidden = false;
  document.body.classList.add("z-wskazowka");
  $("zamknij-wskazowke").addEventListener("click", () => {
    $("wskazowka-ios").hidden = true;
    document.body.classList.remove("z-wskazowka");
    try { localStorage.setItem("nf-wskazowka-ios", String(Date.now())); } catch (e) {}
  });
})();

if ("serviceWorker" in navigator) navigator.serviceWorker.register("sw.js").catch(() => {});

wybrany = ostatniDzien;
zbudujDni();
zaznaczDzien(false);
$("tytul-dnia").textContent = tytulDnia(wybrany);
const zapisana = wczytajNacje();
if (zapisana) ustawNacje(zapisana); else { pokazSzkielet(); otworzWyborNacji(); }
