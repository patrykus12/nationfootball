"use strict";
// Języki aplikacji. Nazwy krajów, dni i miesięcy podaje przeglądarka (Intl) - tu tylko teksty interfejsu.
// Liczba mnoga: klucze one/few/many/other jak w Intl.PluralRules.

const JEZYKI = {
  pl: "Polski", en: "English", de: "Deutsch", es: "Español", fr: "Français", pt: "Português", it: "Italiano", tr: "Türkçe",
};

const TEKSTY = {
  pl: {
    zainstaluj: "Zainstaluj", odswiez: "Odśwież", wybor_dnia: "Wybór dnia", zmien_kraj: "Zmień kraj", zmien_kraj_teraz: "Zmień kraj (teraz: {kraj})",
    tylko_ulubieni: "★ Tylko ulubieni", kraj_ligi: "Kraj ligi", wszystkie_ligi: "Wszystkie ligi", puchary: "Puchary / międzynarodowe",
    zak_mecze: "Mecze", zak_rankingi: "Rankingi", zak_transfery: "Transfery", zak_ulubieni: "Ulubieni",
    rankingi: "Rankingi", transfery: "Transfery", transfery_opis: "Zmiany klubów i nowi zawodnicy w bazie.",
    ulubieni: "Ulubieni", ulubieni_opis: "Dotknij zawodnika w meczu albo znajdź go niżej i dodaj gwiazdką.",
    szukaj_zawodnika: "Szukaj zawodnika", nazwisko: "Nazwisko…", dni7: "7 dni", dni30: "30 dni", sezon: "Sezon",
    wybor_tytul: "Piłkarzy z jakiego kraju śledzisz?", wybor_opis: "Pokażemy mecze i występy zawodników z wybranego kraju grających za granicą. Zmienisz to w każdej chwili w ustawieniach.",
    szukaj_kraju: "Szukaj kraju…", zamknij: "Zamknij",
    ios_tytul: "Zainstaluj NationFootball", ios_dotknij: "Dotknij", ios_udostepnij: "Udostępnij", ios_potem: ", a potem", ios_ekran: "Do ekranu początkowego", ios_drobne: "Nie widzisz przycisku? Dotknij ⋯ na dole Safari.",
    dzis: "Dziś", wczoraj: "Wczoraj", jutro: "Jutro", dzis_krotko: "dziś",
    brak_dnia: "Serwer nie ma jeszcze danych dla tego dnia", sprobuj: "Spróbuj ponownie za kilka minut.",
    brak_polaczenia: "Brak połączenia z serwerem", sprawdz_internet: "Sprawdź internet i dotknij przycisku odświeżania.",
    st_odwolany: "odwołany", st_koniec: "koniec", st_trwa: "w trakcie", stan_z: "stan z {g}", bez_internetu: "bez internetu",
    nic_nie_pasuje: "Nic nie pasuje do filtrów", zmien_filtr: "Zmień albo wyłącz filtr u góry.",
    brak_meczow: "Brak meczów {kto}", nikt_nie_gra: "Tego dnia żaden z nich nie gra.", wczytywanie: "Wczytywanie…",
    mecze_l: { one: "mecz", few: "mecze", many: "meczów", other: "meczu" },
    zawodnicy_l: { one: "zawodnik", few: "zawodników", many: "zawodników", other: "zawodnika" },
    poz: ["BR", "OBR", "POM", "NAP"], poz_pelne: ["Bramkarz", "Obrońca", "Pomocnik", "Napastnik"],
    gral: "grał", z_lawki: " z ławki", nie_gral: "nie grał", brak_danych: "brak danych",
    do_min: "do {m}'", od_min: "od {m}'", od_do: "od {a}' do {b}'", w_podstawie: "w podstawie", rezerwowy_bez: "rezerwowy, brak danych o zmianach",
    brak_ocen: "brak ocen", najblizszy: "Najbliższy mecz:", st_mecze: "Mecze", st_minuty: "Minuty", st_gole: "Gole", st_asysty: "Asysty",
    st_ocena: "Śr. ocena", st_podstawa: "W podstawie", poza_baza: "poza bazą (np. powrót do kraju)", forma: "Forma", kartki: "Kartki",
    ostatnie_mecze: "Ostatnie mecze", historia_pusta: "Historia meczów pojawi się po pierwszym zakończonym meczu.", dane_od: "Dane od {d}",
    rank_opis: "{z} zagrało · {g} goli · {a} asyst", rank_brak: "Jeszcze brak danych", rank_brak_opis: "Rankingi liczą się z zakończonych meczów - pojawią się po najbliższej kolejce.",
    legion7: "Legion tygodnia", legion30: "Legion miesiąca", legion0: "Legion sezonu", legion_opis: "Najlepszy mecz każdego zawodnika wg oceny, ustawienie 4-3-3.",
    strzelcy: "Strzelcy", asystenci: "Asystenci", kanadyjska: "Klasyfikacja kanadyjska", najw_minut: "Najwięcej minut", srednia: "Średnia ocen (min. {n} m.)",
    nacje_ilu: "Nacje: ilu zawodników zagrało", m_skrot: "m.", w_podst: "w podst.", goli_n: "{n} goli",
    brak_zmian: "Brak zmian", transfery_pojawia: "Transfery pojawią się po najbliższej aktualizacji bazy zawodników.", nowy_w_bazie: "nowy w bazie",
    brak_ulub: "Nie masz jeszcze ulubionych", brak_ulub_opis: "Dotknij zawodnika w meczu i gwiazdkę w jego profilu albo wyszukaj go poniżej.",
    brak_zapisanych: "Brak zapisanych meczów.", nastepny: "Następny:", dni30_krotko: "30 dni:", sr: "śr.", brak_nazwiska: "Brak zawodników o takim nazwisku.",
    push_wl_btn: "🔕 Ciche powiadomienia o golach i asystach: <b>włączone</b>", push_wlacz_btn: "🔔 Włącz ciche powiadomienia o golach i asystach ulubionych",
    push_zablok: "Powiadomienia są zablokowane w ustawieniach telefonu.", push_blad: "Nie udało się włączyć powiadomień. Na iPhonie działają tylko w aplikacji dodanej do ekranu początkowego.",
    rozgrywki: "Rozgrywki (ID: {id})",
    ustawienia: "Ustawienia", jezyk: "Język", kraj_zaw: "Kraj zawodników", zmien: "Zmień", powiadomienia: "Powiadomienia",
    push_opis: "Ciche powiadomienie (bez dźwięku i wibracji), gdy ulubiony zawodnik strzeli gola albo zaliczy asystę. Przychodzi po meczu.",
    push_brak_serwer: "Powiadomienia są chwilowo niedostępne.", push_brak_przegl: "Ta przeglądarka nie obsługuje powiadomień.",
    push_ios: "Na iPhonie powiadomienia działają po dodaniu aplikacji do ekranu początkowego.", push_ulubionych: "Ulubionych zawodników: {n}",
    push_bez_ulub: "Dodaj ulubionych zawodników (gwiazdka w profilu), żeby dostawać powiadomienia.",
    o_aplikacji: "Mecze i występy piłkarzy grających za granicą.",
  },
  en: {
    zainstaluj: "Install", odswiez: "Refresh", wybor_dnia: "Choose day", zmien_kraj: "Change country", zmien_kraj_teraz: "Change country (now: {kraj})",
    tylko_ulubieni: "★ Favourites only", kraj_ligi: "League country", wszystkie_ligi: "All leagues", puchary: "Cups / international",
    zak_mecze: "Matches", zak_rankingi: "Rankings", zak_transfery: "Transfers", zak_ulubieni: "Favourites",
    rankingi: "Rankings", transfery: "Transfers", transfery_opis: "Club changes and new players in the database.",
    ulubieni: "Favourites", ulubieni_opis: "Tap a player in a match or find them below and add a star.",
    szukaj_zawodnika: "Find a player", nazwisko: "Surname…", dni7: "7 days", dni30: "30 days", sezon: "Season",
    wybor_tytul: "Which country's players do you follow?", wybor_opis: "We'll show matches and performances of players from the chosen country playing abroad. You can change it any time in settings.",
    szukaj_kraju: "Search country…", zamknij: "Close",
    ios_tytul: "Install NationFootball", ios_dotknij: "Tap", ios_udostepnij: "Share", ios_potem: ", then", ios_ekran: "Add to Home Screen", ios_drobne: "Can't see the button? Tap ⋯ at the bottom of Safari.",
    dzis: "Today", wczoraj: "Yesterday", jutro: "Tomorrow", dzis_krotko: "today",
    brak_dnia: "The server has no data for this day yet", sprobuj: "Try again in a few minutes.",
    brak_polaczenia: "No connection to the server", sprawdz_internet: "Check your internet and tap refresh.",
    st_odwolany: "cancelled", st_koniec: "FT", st_trwa: "live", stan_z: "as of {g}", bez_internetu: "offline",
    nic_nie_pasuje: "Nothing matches the filters", zmien_filtr: "Change or turn off the filter above.",
    brak_meczow: "No matches for players from {kraj}", nikt_nie_gra: "None of them play on this day.", wczytywanie: "Loading…",
    mecze_l: { one: "match", other: "matches" }, zawodnicy_l: { one: "player", other: "players" },
    poz: ["GK", "DF", "MF", "FW"], poz_pelne: ["Goalkeeper", "Defender", "Midfielder", "Forward"],
    gral: "played", z_lawki: " off the bench", nie_gral: "didn't play", brak_danych: "no data",
    do_min: "until {m}'", od_min: "from {m}'", od_do: "{a}'–{b}'", w_podstawie: "started", rezerwowy_bez: "substitute, no data on changes",
    brak_ocen: "no ratings", najblizszy: "Next match:", st_mecze: "Matches", st_minuty: "Minutes", st_gole: "Goals", st_asysty: "Assists",
    st_ocena: "Avg. rating", st_podstawa: "Starts", poza_baza: "not in the database (e.g. returned home)", forma: "Form", kartki: "Cards",
    ostatnie_mecze: "Recent matches", historia_pusta: "Match history will appear after the first finished match.", dane_od: "Data since {d}",
    rank_opis: "{z} played · {g} goals · {a} assists", rank_brak: "No data yet", rank_brak_opis: "Rankings are built from finished matches - they'll appear after the next round.",
    legion7: "Team of the week", legion30: "Team of the month", legion0: "Team of the season", legion_opis: "Each player's best-rated match, 4-3-3 formation.",
    strzelcy: "Top scorers", asystenci: "Top assists", kanadyjska: "Goals + assists", najw_minut: "Most minutes", srednia: "Average rating (min. {n} m.)",
    nacje_ilu: "Nations: how many players played", m_skrot: "m.", w_podst: "starts", goli_n: "{n} goals",
    brak_zmian: "No changes", transfery_pojawia: "Transfers will appear after the next player database update.", nowy_w_bazie: "new in database",
    brak_ulub: "No favourites yet", brak_ulub_opis: "Tap a player in a match and the star in their profile, or search below.",
    brak_zapisanych: "No saved matches.", nastepny: "Next:", dni30_krotko: "30 days:", sr: "avg.", brak_nazwiska: "No players with that name.",
    push_wl_btn: "🔕 Silent goal & assist notifications: <b>on</b>", push_wlacz_btn: "🔔 Turn on silent notifications for your favourites' goals and assists",
    push_zablok: "Notifications are blocked in your phone settings.", push_blad: "Couldn't turn on notifications. On iPhone they only work in the app added to the Home Screen.",
    rozgrywki: "Competition (ID: {id})",
    ustawienia: "Settings", jezyk: "Language", kraj_zaw: "Players' country", zmien: "Change", powiadomienia: "Notifications",
    push_opis: "A silent notification (no sound or vibration) when a favourite player scores or assists. Sent after the match.",
    push_brak_serwer: "Notifications are temporarily unavailable.", push_brak_przegl: "This browser doesn't support notifications.",
    push_ios: "On iPhone, notifications work after adding the app to the Home Screen.", push_ulubionych: "Favourite players: {n}",
    push_bez_ulub: "Add favourite players (star in their profile) to get notifications.",
    o_aplikacji: "Matches and performances of footballers playing abroad.",
  },
  de: {
    zainstaluj: "Installieren", odswiez: "Aktualisieren", wybor_dnia: "Tag wählen", zmien_kraj: "Land ändern", zmien_kraj_teraz: "Land ändern (jetzt: {kraj})",
    tylko_ulubieni: "★ Nur Favoriten", kraj_ligi: "Land der Liga", wszystkie_ligi: "Alle Ligen", puchary: "Pokale / international",
    zak_mecze: "Spiele", zak_rankingi: "Ranglisten", zak_transfery: "Transfers", zak_ulubieni: "Favoriten",
    rankingi: "Ranglisten", transfery: "Transfers", transfery_opis: "Vereinswechsel und neue Spieler in der Datenbank.",
    ulubieni: "Favoriten", ulubieni_opis: "Tippe auf einen Spieler im Spiel oder suche ihn unten und markiere ihn mit einem Stern.",
    szukaj_zawodnika: "Spieler suchen", nazwisko: "Nachname…", dni7: "7 Tage", dni30: "30 Tage", sezon: "Saison",
    wybor_tytul: "Spieler welches Landes verfolgst du?", wybor_opis: "Wir zeigen Spiele und Einsätze von Spielern des gewählten Landes, die im Ausland spielen. Jederzeit in den Einstellungen änderbar.",
    szukaj_kraju: "Land suchen…", zamknij: "Schließen",
    ios_tytul: "NationFootball installieren", ios_dotknij: "Tippe auf", ios_udostepnij: "Teilen", ios_potem: ", dann", ios_ekran: "Zum Home-Bildschirm", ios_drobne: "Kein Knopf zu sehen? Tippe unten in Safari auf ⋯.",
    dzis: "Heute", wczoraj: "Gestern", jutro: "Morgen", dzis_krotko: "heute",
    brak_dnia: "Der Server hat noch keine Daten für diesen Tag", sprobuj: "Versuche es in ein paar Minuten erneut.",
    brak_polaczenia: "Keine Verbindung zum Server", sprawdz_internet: "Prüfe die Internetverbindung und tippe auf Aktualisieren.",
    st_odwolany: "abgesagt", st_koniec: "Ende", st_trwa: "läuft", stan_z: "Stand {g}", bez_internetu: "offline",
    nic_nie_pasuje: "Nichts passt zu den Filtern", zmien_filtr: "Ändere oder deaktiviere den Filter oben.",
    brak_meczow: "Keine Spiele von Spielern aus {kraj}", nikt_nie_gra: "An diesem Tag spielt keiner von ihnen.", wczytywanie: "Wird geladen…",
    mecze_l: { one: "Spiel", other: "Spiele" }, zawodnicy_l: { one: "Spieler", other: "Spieler" },
    poz: ["TW", "AB", "MF", "ST"], poz_pelne: ["Torwart", "Abwehr", "Mittelfeld", "Sturm"],
    gral: "gespielt", z_lawki: " eingewechselt", nie_gral: "nicht gespielt", brak_danych: "keine Daten",
    do_min: "bis {m}'", od_min: "ab {m}'", od_do: "{a}'–{b}'", w_podstawie: "Startelf", rezerwowy_bez: "Ersatz, keine Wechseldaten",
    brak_ocen: "keine Noten", najblizszy: "Nächstes Spiel:", st_mecze: "Spiele", st_minuty: "Minuten", st_gole: "Tore", st_asysty: "Vorlagen",
    st_ocena: "Ø Note", st_podstawa: "Startelf", poza_baza: "nicht in der Datenbank (z. B. Rückkehr ins Heimatland)", forma: "Form", kartki: "Karten",
    ostatnie_mecze: "Letzte Spiele", historia_pusta: "Die Spielhistorie erscheint nach dem ersten beendeten Spiel.", dane_od: "Daten seit {d}",
    rank_opis: "{z} gespielt · {g} Tore · {a} Vorlagen", rank_brak: "Noch keine Daten", rank_brak_opis: "Ranglisten entstehen aus beendeten Spielen - sie erscheinen nach dem nächsten Spieltag.",
    legion7: "Elf der Woche", legion30: "Elf des Monats", legion0: "Elf der Saison", legion_opis: "Bestbewertetes Spiel jedes Spielers, Formation 4-3-3.",
    strzelcy: "Torschützen", asystenci: "Vorlagengeber", kanadyjska: "Scorerpunkte", najw_minut: "Meiste Minuten", srednia: "Durchschnittsnote (min. {n} Sp.)",
    nacje_ilu: "Nationen: wie viele Spieler gespielt haben", m_skrot: "Sp.", w_podst: "Startelf", goli_n: "{n} Tore",
    brak_zmian: "Keine Änderungen", transfery_pojawia: "Transfers erscheinen nach der nächsten Aktualisierung der Spielerdatenbank.", nowy_w_bazie: "neu in der Datenbank",
    brak_ulub: "Noch keine Favoriten", brak_ulub_opis: "Tippe auf einen Spieler und auf den Stern im Profil oder suche unten.",
    brak_zapisanych: "Keine gespeicherten Spiele.", nastepny: "Nächstes:", dni30_krotko: "30 Tage:", sr: "Ø", brak_nazwiska: "Keine Spieler mit diesem Namen.",
    push_wl_btn: "🔕 Stille Benachrichtigungen bei Toren und Vorlagen: <b>an</b>", push_wlacz_btn: "🔔 Stille Benachrichtigungen bei Toren und Vorlagen der Favoriten einschalten",
    push_zablok: "Benachrichtigungen sind in den Telefoneinstellungen blockiert.", push_blad: "Benachrichtigungen konnten nicht eingeschaltet werden. Auf dem iPhone funktionieren sie nur in der zum Home-Bildschirm hinzugefügten App.",
    rozgrywki: "Wettbewerb (ID: {id})",
    ustawienia: "Einstellungen", jezyk: "Sprache", kraj_zaw: "Land der Spieler", zmien: "Ändern", powiadomienia: "Benachrichtigungen",
    push_opis: "Stille Benachrichtigung (ohne Ton und Vibration), wenn ein Favorit trifft oder vorlegt. Kommt nach dem Spiel.",
    push_brak_serwer: "Benachrichtigungen sind vorübergehend nicht verfügbar.", push_brak_przegl: "Dieser Browser unterstützt keine Benachrichtigungen.",
    push_ios: "Auf dem iPhone funktionieren Benachrichtigungen, nachdem die App zum Home-Bildschirm hinzugefügt wurde.", push_ulubionych: "Favoriten: {n}",
    push_bez_ulub: "Füge Favoriten hinzu (Stern im Profil), um Benachrichtigungen zu erhalten.",
    o_aplikacji: "Spiele und Einsätze von Fußballern, die im Ausland spielen.",
  },
  es: {
    zainstaluj: "Instalar", odswiez: "Actualizar", wybor_dnia: "Elegir día", zmien_kraj: "Cambiar país", zmien_kraj_teraz: "Cambiar país (ahora: {kraj})",
    tylko_ulubieni: "★ Solo favoritos", kraj_ligi: "País de la liga", wszystkie_ligi: "Todas las ligas", puchary: "Copas / internacional",
    zak_mecze: "Partidos", zak_rankingi: "Rankings", zak_transfery: "Fichajes", zak_ulubieni: "Favoritos",
    rankingi: "Rankings", transfery: "Fichajes", transfery_opis: "Cambios de club y nuevos jugadores en la base de datos.",
    ulubieni: "Favoritos", ulubieni_opis: "Toca a un jugador en un partido o búscalo abajo y márcalo con una estrella.",
    szukaj_zawodnika: "Buscar jugador", nazwisko: "Apellido…", dni7: "7 días", dni30: "30 días", sezon: "Temporada",
    wybor_tytul: "¿De qué país sigues a los jugadores?", wybor_opis: "Mostraremos partidos y actuaciones de jugadores del país elegido que juegan en el extranjero. Puedes cambiarlo en ajustes.",
    szukaj_kraju: "Buscar país…", zamknij: "Cerrar",
    ios_tytul: "Instala NationFootball", ios_dotknij: "Toca", ios_udostepnij: "Compartir", ios_potem: " y luego", ios_ekran: "Añadir a pantalla de inicio", ios_drobne: "¿No ves el botón? Toca ⋯ abajo en Safari.",
    dzis: "Hoy", wczoraj: "Ayer", jutro: "Mañana", dzis_krotko: "hoy",
    brak_dnia: "El servidor aún no tiene datos de este día", sprobuj: "Inténtalo de nuevo en unos minutos.",
    brak_polaczenia: "Sin conexión con el servidor", sprawdz_internet: "Comprueba internet y toca actualizar.",
    st_odwolany: "cancelado", st_koniec: "final", st_trwa: "en juego", stan_z: "a las {g}", bez_internetu: "sin conexión",
    nic_nie_pasuje: "Nada coincide con los filtros", zmien_filtr: "Cambia o quita el filtro de arriba.",
    brak_meczow: "No hay partidos de jugadores de {kraj}", nikt_nie_gra: "Ese día no juega ninguno.", wczytywanie: "Cargando…",
    mecze_l: { one: "partido", other: "partidos" }, zawodnicy_l: { one: "jugador", other: "jugadores" },
    poz: ["POR", "DEF", "MED", "DEL"], poz_pelne: ["Portero", "Defensa", "Centrocampista", "Delantero"],
    gral: "jugó", z_lawki: " desde el banquillo", nie_gral: "no jugó", brak_danych: "sin datos",
    do_min: "hasta el {m}'", od_min: "desde el {m}'", od_do: "{a}'–{b}'", w_podstawie: "titular", rezerwowy_bez: "suplente, sin datos de cambios",
    brak_ocen: "sin notas", najblizszy: "Próximo partido:", st_mecze: "Partidos", st_minuty: "Minutos", st_gole: "Goles", st_asysty: "Asistencias",
    st_ocena: "Nota media", st_podstawa: "Titular", poza_baza: "fuera de la base (p. ej. volvió a su país)", forma: "Forma", kartki: "Tarjetas",
    ostatnie_mecze: "Últimos partidos", historia_pusta: "El historial aparecerá tras el primer partido terminado.", dane_od: "Datos desde {d}",
    rank_opis: "{z} jugaron · {g} goles · {a} asistencias", rank_brak: "Aún no hay datos", rank_brak_opis: "Los rankings se calculan con partidos terminados; aparecerán tras la próxima jornada.",
    legion7: "Once de la semana", legion30: "Once del mes", legion0: "Once de la temporada", legion_opis: "Mejor partido de cada jugador según su nota, 4-3-3.",
    strzelcy: "Goleadores", asystenci: "Asistentes", kanadyjska: "Goles + asistencias", najw_minut: "Más minutos", srednia: "Nota media (mín. {n} p.)",
    nacje_ilu: "Países: cuántos jugadores jugaron", m_skrot: "p.", w_podst: "titular", goli_n: "{n} goles",
    brak_zmian: "Sin cambios", transfery_pojawia: "Los fichajes aparecerán tras la próxima actualización de la base de jugadores.", nowy_w_bazie: "nuevo en la base",
    brak_ulub: "Aún no tienes favoritos", brak_ulub_opis: "Toca a un jugador y la estrella de su perfil, o búscalo abajo.",
    brak_zapisanych: "No hay partidos guardados.", nastepny: "Próximo:", dni30_krotko: "30 días:", sr: "media", brak_nazwiska: "No hay jugadores con ese apellido.",
    push_wl_btn: "🔕 Avisos silenciosos de goles y asistencias: <b>activados</b>", push_wlacz_btn: "🔔 Activar avisos silenciosos de goles y asistencias de tus favoritos",
    push_zablok: "Las notificaciones están bloqueadas en los ajustes del teléfono.", push_blad: "No se pudieron activar las notificaciones. En iPhone solo funcionan en la app añadida a la pantalla de inicio.",
    rozgrywki: "Competición (ID: {id})",
    ustawienia: "Ajustes", jezyk: "Idioma", kraj_zaw: "País de los jugadores", zmien: "Cambiar", powiadomienia: "Notificaciones",
    push_opis: "Aviso silencioso (sin sonido ni vibración) cuando un favorito marca o da una asistencia. Llega después del partido.",
    push_brak_serwer: "Las notificaciones no están disponibles por ahora.", push_brak_przegl: "Este navegador no admite notificaciones.",
    push_ios: "En iPhone las notificaciones funcionan tras añadir la app a la pantalla de inicio.", push_ulubionych: "Jugadores favoritos: {n}",
    push_bez_ulub: "Añade jugadores favoritos (estrella en su perfil) para recibir avisos.",
    o_aplikacji: "Partidos y actuaciones de futbolistas que juegan en el extranjero.",
  },
  fr: {
    zainstaluj: "Installer", odswiez: "Actualiser", wybor_dnia: "Choisir le jour", zmien_kraj: "Changer de pays", zmien_kraj_teraz: "Changer de pays (actuel : {kraj})",
    tylko_ulubieni: "★ Favoris uniquement", kraj_ligi: "Pays du championnat", wszystkie_ligi: "Tous les championnats", puchary: "Coupes / international",
    zak_mecze: "Matchs", zak_rankingi: "Classements", zak_transfery: "Transferts", zak_ulubieni: "Favoris",
    rankingi: "Classements", transfery: "Transferts", transfery_opis: "Changements de club et nouveaux joueurs dans la base.",
    ulubieni: "Favoris", ulubieni_opis: "Touchez un joueur dans un match ou cherchez-le ci-dessous et ajoutez une étoile.",
    szukaj_zawodnika: "Chercher un joueur", nazwisko: "Nom…", dni7: "7 jours", dni30: "30 jours", sezon: "Saison",
    wybor_tytul: "Les joueurs de quel pays suivez-vous ?", wybor_opis: "Nous afficherons les matchs et performances des joueurs du pays choisi évoluant à l'étranger. Modifiable à tout moment dans les réglages.",
    szukaj_kraju: "Chercher un pays…", zamknij: "Fermer",
    ios_tytul: "Installer NationFootball", ios_dotknij: "Touchez", ios_udostepnij: "Partager", ios_potem: ", puis", ios_ekran: "Sur l'écran d'accueil", ios_drobne: "Pas de bouton ? Touchez ⋯ en bas de Safari.",
    dzis: "Aujourd'hui", wczoraj: "Hier", jutro: "Demain", dzis_krotko: "auj.",
    brak_dnia: "Le serveur n'a pas encore de données pour ce jour", sprobuj: "Réessayez dans quelques minutes.",
    brak_polaczenia: "Pas de connexion au serveur", sprawdz_internet: "Vérifiez internet et touchez actualiser.",
    st_odwolany: "annulé", st_koniec: "terminé", st_trwa: "en cours", stan_z: "à {g}", bez_internetu: "hors ligne",
    nic_nie_pasuje: "Rien ne correspond aux filtres", zmien_filtr: "Modifiez ou désactivez le filtre en haut.",
    brak_meczow: "Aucun match des joueurs de : {kraj}", nikt_nie_gra: "Aucun d'eux ne joue ce jour-là.", wczytywanie: "Chargement…",
    mecze_l: { one: "match", other: "matchs" }, zawodnicy_l: { one: "joueur", other: "joueurs" },
    poz: ["G", "DÉF", "MIL", "ATT"], poz_pelne: ["Gardien", "Défenseur", "Milieu", "Attaquant"],
    gral: "a joué", z_lawki: " en sortie de banc", nie_gral: "n'a pas joué", brak_danych: "pas de données",
    do_min: "jusqu'à la {m}'", od_min: "à partir de la {m}'", od_do: "{a}'–{b}'", w_podstawie: "titulaire", rezerwowy_bez: "remplaçant, pas de données sur les changements",
    brak_ocen: "pas de notes", najblizszy: "Prochain match :", st_mecze: "Matchs", st_minuty: "Minutes", st_gole: "Buts", st_asysty: "Passes déc.",
    st_ocena: "Note moy.", st_podstawa: "Titulaire", poza_baza: "hors de la base (p. ex. retour au pays)", forma: "Forme", kartki: "Cartons",
    ostatnie_mecze: "Derniers matchs", historia_pusta: "L'historique apparaîtra après le premier match terminé.", dane_od: "Données depuis le {d}",
    rank_opis: "{z} ont joué · {g} buts · {a} passes déc.", rank_brak: "Pas encore de données", rank_brak_opis: "Les classements sont calculés à partir des matchs terminés ; ils apparaîtront après la prochaine journée.",
    legion7: "Équipe de la semaine", legion30: "Équipe du mois", legion0: "Équipe de la saison", legion_opis: "Meilleur match de chaque joueur selon sa note, en 4-3-3.",
    strzelcy: "Buteurs", asystenci: "Passeurs", kanadyjska: "Buts + passes", najw_minut: "Le plus de minutes", srednia: "Note moyenne (min. {n} m.)",
    nacje_ilu: "Pays : combien de joueurs ont joué", m_skrot: "m.", w_podst: "tit.", goli_n: "{n} buts",
    brak_zmian: "Aucun changement", transfery_pojawia: "Les transferts apparaîtront après la prochaine mise à jour de la base.", nowy_w_bazie: "nouveau dans la base",
    brak_ulub: "Pas encore de favoris", brak_ulub_opis: "Touchez un joueur puis l'étoile de son profil, ou cherchez-le ci-dessous.",
    brak_zapisanych: "Aucun match enregistré.", nastepny: "Prochain :", dni30_krotko: "30 jours :", sr: "moy.", brak_nazwiska: "Aucun joueur avec ce nom.",
    push_wl_btn: "🔕 Notifications silencieuses de buts et passes : <b>activées</b>", push_wlacz_btn: "🔔 Activer les notifications silencieuses des buts et passes de vos favoris",
    push_zablok: "Les notifications sont bloquées dans les réglages du téléphone.", push_blad: "Impossible d'activer les notifications. Sur iPhone, elles ne fonctionnent que dans l'app ajoutée à l'écran d'accueil.",
    rozgrywki: "Compétition (ID : {id})",
    ustawienia: "Réglages", jezyk: "Langue", kraj_zaw: "Pays des joueurs", zmien: "Changer", powiadomienia: "Notifications",
    push_opis: "Notification silencieuse (sans son ni vibration) quand un favori marque ou fait une passe décisive. Envoyée après le match.",
    push_brak_serwer: "Les notifications sont temporairement indisponibles.", push_brak_przegl: "Ce navigateur ne prend pas en charge les notifications.",
    push_ios: "Sur iPhone, les notifications fonctionnent après l'ajout de l'app à l'écran d'accueil.", push_ulubionych: "Joueurs favoris : {n}",
    push_bez_ulub: "Ajoutez des joueurs favoris (étoile dans leur profil) pour recevoir des notifications.",
    o_aplikacji: "Matchs et performances des footballeurs évoluant à l'étranger.",
  },
  pt: {
    zainstaluj: "Instalar", odswiez: "Atualizar", wybor_dnia: "Escolher dia", zmien_kraj: "Mudar país", zmien_kraj_teraz: "Mudar país (agora: {kraj})",
    tylko_ulubieni: "★ Só favoritos", kraj_ligi: "País da liga", wszystkie_ligi: "Todas as ligas", puchary: "Taças / internacional",
    zak_mecze: "Jogos", zak_rankingi: "Rankings", zak_transfery: "Transferências", zak_ulubieni: "Favoritos",
    rankingi: "Rankings", transfery: "Transferências", transfery_opis: "Mudanças de clube e novos jogadores na base de dados.",
    ulubieni: "Favoritos", ulubieni_opis: "Toque num jogador num jogo ou procure-o abaixo e marque com uma estrela.",
    szukaj_zawodnika: "Procurar jogador", nazwisko: "Apelido…", dni7: "7 dias", dni30: "30 dias", sezon: "Temporada",
    wybor_tytul: "De que país são os jogadores que segue?", wybor_opis: "Mostramos jogos e atuações de jogadores do país escolhido que atuam no estrangeiro. Pode mudar nas definições.",
    szukaj_kraju: "Procurar país…", zamknij: "Fechar",
    ios_tytul: "Instalar NationFootball", ios_dotknij: "Toque em", ios_udostepnij: "Partilhar", ios_potem: " e depois", ios_ekran: "Adicionar ao ecrã principal", ios_drobne: "Não vê o botão? Toque em ⋯ no fundo do Safari.",
    dzis: "Hoje", wczoraj: "Ontem", jutro: "Amanhã", dzis_krotko: "hoje",
    brak_dnia: "O servidor ainda não tem dados deste dia", sprobuj: "Tente de novo daqui a alguns minutos.",
    brak_polaczenia: "Sem ligação ao servidor", sprawdz_internet: "Verifique a internet e toque em atualizar.",
    st_odwolany: "cancelado", st_koniec: "final", st_trwa: "a decorrer", stan_z: "às {g}", bez_internetu: "sem ligação",
    nic_nie_pasuje: "Nada corresponde aos filtros", zmien_filtr: "Altere ou desligue o filtro acima.",
    brak_meczow: "Sem jogos de jogadores de {kraj}", nikt_nie_gra: "Nenhum deles joga neste dia.", wczytywanie: "A carregar…",
    mecze_l: { one: "jogo", other: "jogos" }, zawodnicy_l: { one: "jogador", other: "jogadores" },
    poz: ["GR", "DEF", "MED", "AV"], poz_pelne: ["Guarda-redes", "Defesa", "Médio", "Avançado"],
    gral: "jogou", z_lawki: " vindo do banco", nie_gral: "não jogou", brak_danych: "sem dados",
    do_min: "até aos {m}'", od_min: "desde os {m}'", od_do: "{a}'–{b}'", w_podstawie: "titular", rezerwowy_bez: "suplente, sem dados de substituições",
    brak_ocen: "sem notas", najblizszy: "Próximo jogo:", st_mecze: "Jogos", st_minuty: "Minutos", st_gole: "Golos", st_asysty: "Assistências",
    st_ocena: "Nota média", st_podstawa: "Titular", poza_baza: "fora da base (p. ex. regressou ao país)", forma: "Forma", kartki: "Cartões",
    ostatnie_mecze: "Últimos jogos", historia_pusta: "O histórico aparece após o primeiro jogo terminado.", dane_od: "Dados desde {d}",
    rank_opis: "{z} jogaram · {g} golos · {a} assistências", rank_brak: "Ainda sem dados", rank_brak_opis: "Os rankings contam jogos terminados - aparecem após a próxima jornada.",
    legion7: "Equipa da semana", legion30: "Equipa do mês", legion0: "Equipa da temporada", legion_opis: "Melhor jogo de cada jogador pela nota, 4-3-3.",
    strzelcy: "Marcadores", asystenci: "Assistências", kanadyjska: "Golos + assistências", najw_minut: "Mais minutos", srednia: "Nota média (mín. {n} j.)",
    nacje_ilu: "Países: quantos jogadores jogaram", m_skrot: "j.", w_podst: "titular", goli_n: "{n} golos",
    brak_zmian: "Sem alterações", transfery_pojawia: "As transferências aparecem após a próxima atualização da base de jogadores.", nowy_w_bazie: "novo na base",
    brak_ulub: "Ainda sem favoritos", brak_ulub_opis: "Toque num jogador e na estrela do perfil, ou procure abaixo.",
    brak_zapisanych: "Sem jogos guardados.", nastepny: "Próximo:", dni30_krotko: "30 dias:", sr: "média", brak_nazwiska: "Nenhum jogador com esse nome.",
    push_wl_btn: "🔕 Notificações silenciosas de golos e assistências: <b>ligadas</b>", push_wlacz_btn: "🔔 Ligar notificações silenciosas de golos e assistências dos favoritos",
    push_zablok: "As notificações estão bloqueadas nas definições do telemóvel.", push_blad: "Não foi possível ligar as notificações. No iPhone só funcionam na app adicionada ao ecrã principal.",
    rozgrywki: "Competição (ID: {id})",
    ustawienia: "Definições", jezyk: "Idioma", kraj_zaw: "País dos jogadores", zmien: "Mudar", powiadomienia: "Notificações",
    push_opis: "Notificação silenciosa (sem som nem vibração) quando um favorito marca ou assiste. Chega depois do jogo.",
    push_brak_serwer: "As notificações estão temporariamente indisponíveis.", push_brak_przegl: "Este navegador não suporta notificações.",
    push_ios: "No iPhone, as notificações funcionam depois de adicionar a app ao ecrã principal.", push_ulubionych: "Jogadores favoritos: {n}",
    push_bez_ulub: "Adicione jogadores favoritos (estrela no perfil) para receber notificações.",
    o_aplikacji: "Jogos e atuações de futebolistas que jogam no estrangeiro.",
  },
  it: {
    zainstaluj: "Installa", odswiez: "Aggiorna", wybor_dnia: "Scegli giorno", zmien_kraj: "Cambia paese", zmien_kraj_teraz: "Cambia paese (ora: {kraj})",
    tylko_ulubieni: "★ Solo preferiti", kraj_ligi: "Paese del campionato", wszystkie_ligi: "Tutti i campionati", puchary: "Coppe / internazionali",
    zak_mecze: "Partite", zak_rankingi: "Classifiche", zak_transfery: "Trasferimenti", zak_ulubieni: "Preferiti",
    rankingi: "Classifiche", transfery: "Trasferimenti", transfery_opis: "Cambi di squadra e nuovi giocatori nel database.",
    ulubieni: "Preferiti", ulubieni_opis: "Tocca un giocatore in una partita o cercalo qui sotto e aggiungi una stella.",
    szukaj_zawodnika: "Cerca giocatore", nazwisko: "Cognome…", dni7: "7 giorni", dni30: "30 giorni", sezon: "Stagione",
    wybor_tytul: "Di quale paese segui i giocatori?", wybor_opis: "Mostreremo partite e prestazioni dei giocatori del paese scelto che giocano all'estero. Puoi cambiarlo nelle impostazioni.",
    szukaj_kraju: "Cerca paese…", zamknij: "Chiudi",
    ios_tytul: "Installa NationFootball", ios_dotknij: "Tocca", ios_udostepnij: "Condividi", ios_potem: ", poi", ios_ekran: "Aggiungi alla schermata Home", ios_drobne: "Non vedi il pulsante? Tocca ⋯ in basso in Safari.",
    dzis: "Oggi", wczoraj: "Ieri", jutro: "Domani", dzis_krotko: "oggi",
    brak_dnia: "Il server non ha ancora dati per questo giorno", sprobuj: "Riprova tra qualche minuto.",
    brak_polaczenia: "Nessuna connessione al server", sprawdz_internet: "Controlla internet e tocca aggiorna.",
    st_odwolany: "annullata", st_koniec: "finale", st_trwa: "in corso", stan_z: "alle {g}", bez_internetu: "offline",
    nic_nie_pasuje: "Nessun risultato con questi filtri", zmien_filtr: "Cambia o disattiva il filtro in alto.",
    brak_meczow: "Nessuna partita di giocatori di {kraj}", nikt_nie_gra: "Nessuno di loro gioca in questo giorno.", wczytywanie: "Caricamento…",
    mecze_l: { one: "partita", other: "partite" }, zawodnicy_l: { one: "giocatore", other: "giocatori" },
    poz: ["POR", "DIF", "CEN", "ATT"], poz_pelne: ["Portiere", "Difensore", "Centrocampista", "Attaccante"],
    gral: "ha giocato", z_lawki: " dalla panchina", nie_gral: "non ha giocato", brak_danych: "nessun dato",
    do_min: "fino al {m}'", od_min: "dal {m}'", od_do: "{a}'–{b}'", w_podstawie: "titolare", rezerwowy_bez: "riserva, nessun dato sui cambi",
    brak_ocen: "nessun voto", najblizszy: "Prossima partita:", st_mecze: "Partite", st_minuty: "Minuti", st_gole: "Gol", st_asysty: "Assist",
    st_ocena: "Voto medio", st_podstawa: "Titolare", poza_baza: "fuori dal database (es. rientro in patria)", forma: "Forma", kartki: "Cartellini",
    ostatnie_mecze: "Ultime partite", historia_pusta: "Lo storico apparirà dopo la prima partita conclusa.", dane_od: "Dati dal {d}",
    rank_opis: "{z} hanno giocato · {g} gol · {a} assist", rank_brak: "Ancora nessun dato", rank_brak_opis: "Le classifiche si basano sulle partite concluse: appariranno dopo il prossimo turno.",
    legion7: "Top 11 della settimana", legion30: "Top 11 del mese", legion0: "Top 11 della stagione", legion_opis: "Miglior partita di ogni giocatore per voto, modulo 4-3-3.",
    strzelcy: "Marcatori", asystenci: "Assistman", kanadyjska: "Gol + assist", najw_minut: "Più minuti", srednia: "Voto medio (min. {n} p.)",
    nacje_ilu: "Paesi: quanti giocatori hanno giocato", m_skrot: "p.", w_podst: "tit.", goli_n: "{n} gol",
    brak_zmian: "Nessun cambiamento", transfery_pojawia: "I trasferimenti appariranno dopo il prossimo aggiornamento del database.", nowy_w_bazie: "nuovo nel database",
    brak_ulub: "Nessun preferito", brak_ulub_opis: "Tocca un giocatore e la stella nel suo profilo, oppure cercalo qui sotto.",
    brak_zapisanych: "Nessuna partita salvata.", nastepny: "Prossima:", dni30_krotko: "30 giorni:", sr: "media", brak_nazwiska: "Nessun giocatore con questo cognome.",
    push_wl_btn: "🔕 Notifiche silenziose di gol e assist: <b>attive</b>", push_wlacz_btn: "🔔 Attiva le notifiche silenziose di gol e assist dei preferiti",
    push_zablok: "Le notifiche sono bloccate nelle impostazioni del telefono.", push_blad: "Impossibile attivare le notifiche. Su iPhone funzionano solo nell'app aggiunta alla schermata Home.",
    rozgrywki: "Competizione (ID: {id})",
    ustawienia: "Impostazioni", jezyk: "Lingua", kraj_zaw: "Paese dei giocatori", zmien: "Cambia", powiadomienia: "Notifiche",
    push_opis: "Notifica silenziosa (senza suono né vibrazione) quando un preferito segna o fa assist. Arriva dopo la partita.",
    push_brak_serwer: "Le notifiche sono temporaneamente non disponibili.", push_brak_przegl: "Questo browser non supporta le notifiche.",
    push_ios: "Su iPhone le notifiche funzionano dopo aver aggiunto l'app alla schermata Home.", push_ulubionych: "Giocatori preferiti: {n}",
    push_bez_ulub: "Aggiungi giocatori preferiti (stella nel profilo) per ricevere notifiche.",
    o_aplikacji: "Partite e prestazioni dei calciatori che giocano all'estero.",
  },
  tr: {
    zainstaluj: "Yükle", odswiez: "Yenile", wybor_dnia: "Gün seç", zmien_kraj: "Ülke değiştir", zmien_kraj_teraz: "Ülke değiştir (şu an: {kraj})",
    tylko_ulubieni: "★ Sadece favoriler", kraj_ligi: "Lig ülkesi", wszystkie_ligi: "Tüm ligler", puchary: "Kupalar / uluslararası",
    zak_mecze: "Maçlar", zak_rankingi: "Sıralamalar", zak_transfery: "Transferler", zak_ulubieni: "Favoriler",
    rankingi: "Sıralamalar", transfery: "Transferler", transfery_opis: "Kulüp değişiklikleri ve veritabanındaki yeni oyuncular.",
    ulubieni: "Favoriler", ulubieni_opis: "Maçta bir oyuncuya dokunun ya da aşağıda arayıp yıldızla ekleyin.",
    szukaj_zawodnika: "Oyuncu ara", nazwisko: "Soyadı…", dni7: "7 gün", dni30: "30 gün", sezon: "Sezon",
    wybor_tytul: "Hangi ülkenin oyuncularını takip ediyorsunuz?", wybor_opis: "Seçilen ülkeden yurt dışında oynayan oyuncuların maçlarını ve performanslarını gösteririz. Ayarlardan istediğiniz zaman değiştirebilirsiniz.",
    szukaj_kraju: "Ülke ara…", zamknij: "Kapat",
    ios_tytul: "NationFootball'u yükle", ios_dotknij: "Dokunun:", ios_udostepnij: "Paylaş", ios_potem: ", ardından", ios_ekran: "Ana Ekrana Ekle", ios_drobne: "Düğmeyi göremiyor musunuz? Safari'nin altındaki ⋯ simgesine dokunun.",
    dzis: "Bugün", wczoraj: "Dün", jutro: "Yarın", dzis_krotko: "bugün",
    brak_dnia: "Sunucuda bu gün için henüz veri yok", sprobuj: "Birkaç dakika sonra tekrar deneyin.",
    brak_polaczenia: "Sunucuya bağlanılamıyor", sprawdz_internet: "İnterneti kontrol edip yenile düğmesine dokunun.",
    st_odwolany: "iptal", st_koniec: "MS", st_trwa: "canlı", stan_z: "{g} itibarıyla", bez_internetu: "çevrimdışı",
    nic_nie_pasuje: "Filtrelere uyan sonuç yok", zmien_filtr: "Yukarıdaki filtreyi değiştirin veya kapatın.",
    brak_meczow: "{kraj} oyuncularının maçı yok", nikt_nie_gra: "Bu gün hiçbiri oynamıyor.", wczytywanie: "Yükleniyor…",
    mecze_l: { one: "maç", other: "maç" }, zawodnicy_l: { one: "oyuncu", other: "oyuncu" },
    poz: ["KL", "DEF", "OS", "FV"], poz_pelne: ["Kaleci", "Defans", "Orta saha", "Forvet"],
    gral: "oynadı", z_lawki: " yedekten", nie_gral: "oynamadı", brak_danych: "veri yok",
    do_min: "{m}' kadar", od_min: "{m}' itibarıyla", od_do: "{a}'–{b}'", w_podstawie: "ilk 11", rezerwowy_bez: "yedek, değişiklik verisi yok",
    brak_ocen: "puan yok", najblizszy: "Sonraki maç:", st_mecze: "Maç", st_minuty: "Dakika", st_gole: "Gol", st_asysty: "Asist",
    st_ocena: "Ort. puan", st_podstawa: "İlk 11", poza_baza: "veritabanında değil (ör. ülkesine döndü)", forma: "Form", kartki: "Kartlar",
    ostatnie_mecze: "Son maçlar", historia_pusta: "Maç geçmişi ilk biten maçtan sonra görünecek.", dane_od: "{d} tarihinden itibaren",
    rank_opis: "{z} oyuncu oynadı · {g} gol · {a} asist", rank_brak: "Henüz veri yok", rank_brak_opis: "Sıralamalar biten maçlardan hesaplanır - bir sonraki haftadan sonra görünecek.",
    legion7: "Haftanın 11'i", legion30: "Ayın 11'i", legion0: "Sezonun 11'i", legion_opis: "Her oyuncunun puana göre en iyi maçı, 4-3-3 dizilişi.",
    strzelcy: "Gol krallığı", asystenci: "Asist krallığı", kanadyjska: "Gol + asist", najw_minut: "En çok dakika", srednia: "Ortalama puan (en az {n} maç)",
    nacje_ilu: "Ülkeler: kaç oyuncu oynadı", m_skrot: "m.", w_podst: "ilk 11", goli_n: "{n} gol",
    brak_zmian: "Değişiklik yok", transfery_pojawia: "Transferler bir sonraki oyuncu veritabanı güncellemesinden sonra görünecek.", nowy_w_bazie: "veritabanında yeni",
    brak_ulub: "Henüz favoriniz yok", brak_ulub_opis: "Maçta bir oyuncuya ve profilindeki yıldıza dokunun ya da aşağıda arayın.",
    brak_zapisanych: "Kayıtlı maç yok.", nastepny: "Sonraki:", dni30_krotko: "30 gün:", sr: "ort.", brak_nazwiska: "Bu soyadına sahip oyuncu yok.",
    push_wl_btn: "🔕 Gol ve asist için sessiz bildirimler: <b>açık</b>", push_wlacz_btn: "🔔 Favorilerin gol ve asistleri için sessiz bildirimleri aç",
    push_zablok: "Bildirimler telefon ayarlarında engellenmiş.", push_blad: "Bildirimler açılamadı. iPhone'da yalnızca ana ekrana eklenen uygulamada çalışır.",
    rozgrywki: "Turnuva (ID: {id})",
    ustawienia: "Ayarlar", jezyk: "Dil", kraj_zaw: "Oyuncuların ülkesi", zmien: "Değiştir", powiadomienia: "Bildirimler",
    push_opis: "Favori oyuncu gol attığında veya asist yaptığında sessiz bildirim (ses ve titreşim yok). Maçtan sonra gelir.",
    push_brak_serwer: "Bildirimler geçici olarak kullanılamıyor.", push_brak_przegl: "Bu tarayıcı bildirimleri desteklemiyor.",
    push_ios: "iPhone'da bildirimler, uygulama ana ekrana eklendikten sonra çalışır.", push_ulubionych: "Favori oyuncular: {n}",
    push_bez_ulub: "Bildirim almak için favori oyuncu ekleyin (profildeki yıldız).",
    o_aplikacji: "Yurt dışında oynayan futbolcuların maçları ve performansları.",
  },
};

// Kraje Wielkiej Brytanii - Intl ich nie zna (flagi gb-eng itd.)
const KRAJE_UK = {
  "gb-eng": { pl: "Anglia", en: "England", de: "England", es: "Inglaterra", fr: "Angleterre", pt: "Inglaterra", it: "Inghilterra", tr: "İngiltere" },
  "gb-sct": { pl: "Szkocja", en: "Scotland", de: "Schottland", es: "Escocia", fr: "Écosse", pt: "Escócia", it: "Scozia", tr: "İskoçya" },
  "gb-wls": { pl: "Walia", en: "Wales", de: "Wales", es: "Gales", fr: "Pays de Galles", pt: "País de Gales", it: "Galles", tr: "Galler" },
  "gb-nir": { pl: "Irlandia Płn.", en: "Northern Ireland", de: "Nordirland", es: "Irlanda del Norte", fr: "Irlande du Nord", pt: "Irlanda do Norte", it: "Irlanda del Nord", tr: "Kuzey İrlanda" },
};

function wykryjJezyk() {
  try { const z = localStorage.getItem("nf-jezyk"); if (JEZYKI[z]) return z; } catch (e) {}
  for (const l of navigator.languages || [navigator.language || ""]) {
    const k = String(l).slice(0, 2).toLowerCase();
    if (JEZYKI[k]) return k;
  }
  return "en";
}
let jezyk = wykryjJezyk();

// t("klucz", {zmienna: wartość}) - brakujące tłumaczenie: angielski, potem polski
function t(klucz, zmienne) {
  let s = (TEKSTY[jezyk] && TEKSTY[jezyk][klucz]) ?? TEKSTY.en[klucz] ?? TEKSTY.pl[klucz] ?? klucz;
  if (zmienne && typeof s === "string") s = s.replace(/\{(\w+)\}/g, (_, k) => zmienne[k] ?? "");
  return s;
}

// Liczba mnoga wg reguł języka: lm(5, "mecze_l") -> "meczów" / "matches"
function lm(n, klucz) {
  const formy = t(klucz);
  if (typeof formy !== "object") return formy;
  let kat = "other";
  try { kat = new Intl.PluralRules(jezyk).select(n); } catch (e) {}
  return formy[kat] ?? formy.other ?? formy.many ?? formy.one;
}

const _nazwyRegionow = {};
function nazwaRegionu(kod) {
  kod = String(kod || "").toLowerCase();
  if (KRAJE_UK[kod]) return KRAJE_UK[kod][jezyk] || KRAJE_UK[kod].en;
  try {
    if (!_nazwyRegionow[jezyk]) _nazwyRegionow[jezyk] = new Intl.DisplayNames([jezyk], { type: "region" });
    const n = _nazwyRegionow[jezyk].of(kod.toUpperCase());
    if (n && n.toUpperCase() !== kod.toUpperCase()) return n;
  } catch (e) {}
  return null;
}

// Teksty z serwera (po polsku) w wybranym języku
function tlumaczMinuty(tekst) {
  if (!tekst || jezyk === "pl") return tekst;
  let m;
  if ((m = tekst.match(/^od (\d+)' do (\d+)'$/))) return t("od_do", { a: m[1], b: m[2] });
  if ((m = tekst.match(/^od (\d+)'$/))) return t("od_min", { m: m[1] });
  if ((m = tekst.match(/^do (\d+)'$/))) return t("do_min", { m: m[1] });
  return { "nie grał": t("nie_gral"), "brak danych": t("brak_danych"), "w podstawie": t("w_podstawie"),
           "rezerwowy, brak danych o zmianach": t("rezerwowy_bez") }[tekst] ?? tekst;
}
function tlumaczLige(nazwa) {
  const m = String(nazwa || "").match(/^Rozgrywki \(ID: (.+)\)$/);
  return m ? t("rozgrywki", { id: m[1] }) : nazwa;
}

// Statyczne teksty strony: data-i18n (treść), data-i18n-html, data-i18n-ph (placeholder), data-i18n-aria
function przetlumaczStrone() {
  document.documentElement.lang = jezyk;
  document.querySelectorAll("[data-i18n]").forEach((e) => { e.textContent = t(e.dataset.i18n); });
  document.querySelectorAll("[data-i18n-ph]").forEach((e) => { e.placeholder = t(e.dataset.i18nPh); });
  document.querySelectorAll("[data-i18n-aria]").forEach((e) => { e.setAttribute("aria-label", t(e.dataset.i18nAria)); });
}
