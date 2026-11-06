// Service worker: aplikacja otwiera się także bez internetu (ostatnio oglądane dni z pamięci).
// Zawsze najpierw sieć - nowa wersja strony i świeże wyniki trafiają do telefonu od razu.
const PAMIEC = "nationfootball-v80";
const POWLOKA = ["./", "index.html", "styl.css", "i18n.js", "app.js", "manifest.webmanifest", "favicon.png", "ikona-192.png"];

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(PAMIEC).then((c) => c.addAll(POWLOKA)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", (e) => {
  e.waitUntil(caches.keys()
    .then((klucze) => Promise.all(klucze.filter((k) => k !== PAMIEC).map((k) => caches.delete(k))))
    .then(() => self.clients.claim()));
});

self.addEventListener("fetch", (e) => {
  const req = e.request;
  if (req.method !== "GET") return;
  const url = new URL(req.url);

  // Flagi lig - niezmienne, najpierw z pamięci
  if (url.hostname === "flagcdn.com") {
    e.respondWith(caches.match(req).then((z) => z || fetch(req).then((res) => {
      const kopia = res.clone();
      caches.open(PAMIEC).then((c) => c.put(req, kopia));
      return res;
    })));
    return;
  }
  if (url.origin !== location.origin || !(url.pathname.startsWith("/app/") || url.pathname.startsWith("/api/"))) return;

  e.respondWith(fetch(req).then((res) => {
    if (res.ok) {
      const kopia = res.clone();
      caches.open(PAMIEC).then((c) => c.put(req, kopia));
    }
    return res;
  // Dni z /api/ różnią się nacją (?nacja=tr) - tam adres musi pasować w całości
  }).catch(() => caches.match(req, { ignoreSearch: !url.pathname.startsWith("/api/") }).then((z) => {
    if (!z) return Response.error();
    if (!url.pathname.startsWith("/api/")) return z;
    // Dane z pamięci - strona pokaże "bez internetu"
    const naglowki = new Headers(z.headers);
    naglowki.set("X-Z-Pamieci", "1");
    return z.blob().then((b) => new Response(b, { status: z.status, headers: naglowki }));
  })));
});

// Ciche powiadomienie o golu/asyście ulubionego zawodnika (bez dźwięku i wibracji)
self.addEventListener("push", (e) => {
  let d = {};
  try { d = e.data ? e.data.json() : {}; } catch (err) { d = { tytul: "NationFootball", tresc: e.data ? e.data.text() : "" }; }
  e.waitUntil(self.registration.showNotification(d.tytul || "NationFootball", {
    body: d.tresc || "", icon: "ikona-192.png", badge: "favicon.png", tag: d.tag, silent: true, renotify: false,
    data: { url: d.url || "/app/" },
  }));
});

self.addEventListener("notificationclick", (e) => {
  e.notification.close();
  const url = new URL((e.notification.data && e.notification.data.url) || "/app/", self.location.origin).href;
  e.waitUntil(self.clients.matchAll({ type: "window", includeUncontrolled: true }).then((okna) => {
    const okno = okna.find((o) => o.url.includes("/app/"));
    if (okno) return okno.navigate(url).then((o) => (o || okno).focus()).catch(() => okno.focus());
    return self.clients.openWindow(url);
  }));
});
