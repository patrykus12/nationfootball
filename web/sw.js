// Service worker: aplikacja otwiera się także bez internetu (ostatnio oglądane dni z pamięci).
// Zawsze najpierw sieć - nowa wersja strony i świeże wyniki trafiają do telefonu od razu.
const PAMIEC = "nationfootball-v17";
const POWLOKA = ["./", "index.html", "styl.css", "app.js", "manifest.webmanifest", "favicon.png", "ikona-192.png"];

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
