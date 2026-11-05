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
  fr: { nazwa: "Francuzi", kraj: "Francja", flaga: "fr", formy: ["Francuz", "Francuzów", "Francuzów"], dopelniacz: "Francuzów" },
  en: { nazwa: "Anglicy", kraj: "Anglia", flaga: "gb-eng", formy: ["Anglik", "Anglików", "Anglików"], dopelniacz: "Anglików" },
  sc: { nazwa: "Szkoci", kraj: "Szkocja", flaga: "gb-sct", formy: ["Szkot", "Szkotów", "Szkotów"], dopelniacz: "Szkotów" },
  wl: { nazwa: "Walijczycy", kraj: "Walia", flaga: "gb-wls", formy: ["Walijczyk", "Walijczyków", "Walijczyków"], dopelniacz: "Walijczyków" },
  ni: { nazwa: "Północnoirlandczycy", kraj: "Irlandia Północna", flaga: "gb-nir", formy: ["Północnoirlandczyk", "Północnoirlandczyków", "Północnoirlandczyków"], dopelniacz: "Północnoirlandczyków" },
  tz: { nazwa: "Tanzańczycy", kraj: "Tanzania", flaga: "tz", formy: ["Tanzańczyk", "Tanzańczyków", "Tanzańczyków"], dopelniacz: "Tanzańczyków" },
  it: { nazwa: "Włosi", kraj: "Włochy", flaga: "it", formy: ["Włoch", "Włochów", "Włochów"], dopelniacz: "Włochów" },
  mm: { nazwa: "Birmańczycy", kraj: "Mjanma", flaga: "mm", formy: ["Birmańczyk", "Birmańczyków", "Birmańczyków"], dopelniacz: "Birmańczyków" },
  za: { nazwa: "Południowoafrykańczycy", kraj: "RPA", flaga: "za", formy: ["Południowoafrykańczyk", "Południowoafrykańczyków", "Południowoafrykańczyków"], dopelniacz: "Południowoafrykańczyków" },
  ke: { nazwa: "Kenijczycy", kraj: "Kenia", flaga: "ke", formy: ["Kenijczyk", "Kenijczyków", "Kenijczyków"], dopelniacz: "Kenijczyków" },
  kr: { nazwa: "Koreańczycy", kraj: "Korea Południowa", flaga: "kr", formy: ["Koreańczyk", "Koreańczyków", "Koreańczyków"], dopelniacz: "Koreańczyków" },
  co: { nazwa: "Kolumbijczycy", kraj: "Kolumbia", flaga: "co", formy: ["Kolumbijczyk", "Kolumbijczyków", "Kolumbijczyków"], dopelniacz: "Kolumbijczyków" },
  sd: { nazwa: "Sudańczycy", kraj: "Sudan", flaga: "sd", formy: ["Sudańczyk", "Sudańczyków", "Sudańczyków"], dopelniacz: "Sudańczyków" },
  es: { nazwa: "Hiszpanie", kraj: "Hiszpania", flaga: "es", formy: ["Hiszpan", "Hiszpanów", "Hiszpanów"], dopelniacz: "Hiszpanów" },
  ar: { nazwa: "Argentyńczycy", kraj: "Argentyna", flaga: "ar", formy: ["Argentyńczyk", "Argentyńczyków", "Argentyńczyków"], dopelniacz: "Argentyńczyków" },
  ug: { nazwa: "Ugandyjczycy", kraj: "Uganda", flaga: "ug", formy: ["Ugandyjczyk", "Ugandyjczyków", "Ugandyjczyków"], dopelniacz: "Ugandyjczyków" },
  dz: { nazwa: "Algierczycy", kraj: "Algieria", flaga: "dz", formy: ["Algierczyk", "Algierczyków", "Algierczyków"], dopelniacz: "Algierczyków" },
  ua: { nazwa: "Ukraińcy", kraj: "Ukraina", flaga: "ua", formy: ["Ukrainiec", "Ukraińców", "Ukraińców"], dopelniacz: "Ukraińców" },
  iq: { nazwa: "Irakijczycy", kraj: "Irak", flaga: "iq", formy: ["Irakijczyk", "Irakijczyków", "Irakijczyków"], dopelniacz: "Irakijczyków" },
  af: { nazwa: "Afgańczycy", kraj: "Afganistan", flaga: "af", formy: ["Afgańczyk", "Afgańczyków", "Afgańczyków"], dopelniacz: "Afgańczyków" },
  ca: { nazwa: "Kanadyjczycy", kraj: "Kanada", flaga: "ca", formy: ["Kanadyjczyk", "Kanadyjczyków", "Kanadyjczyków"], dopelniacz: "Kanadyjczyków" },
  ma: { nazwa: "Marokańczycy", kraj: "Maroko", flaga: "ma", formy: ["Marokańczyk", "Marokańczyków", "Marokańczyków"], dopelniacz: "Marokańczyków" },
  sa: { nazwa: "Saudyjczycy", kraj: "Arabia Saudyjska", flaga: "sa", formy: ["Saudyjczyk", "Saudyjczyków", "Saudyjczyków"], dopelniacz: "Saudyjczyków" },
  ao: { nazwa: "Angolczycy", kraj: "Angola", flaga: "ao", formy: ["Angolczyk", "Angolczyków", "Angolczyków"], dopelniacz: "Angolczyków" },
  my: { nazwa: "Malezyjczycy", kraj: "Malezja", flaga: "my", formy: ["Malezyjczyk", "Malezyjczyków", "Malezyjczyków"], dopelniacz: "Malezyjczyków" },
  gh: { nazwa: "Ghańczycy", kraj: "Ghana", flaga: "gh", formy: ["Ghańczyk", "Ghańczyków", "Ghańczyków"], dopelniacz: "Ghańczyków" },
  pe: { nazwa: "Peruwiańczycy", kraj: "Peru", flaga: "pe", formy: ["Peruwiańczyk", "Peruwiańczyków", "Peruwiańczyków"], dopelniacz: "Peruwiańczyków" },
  mz: { nazwa: "Mozambijczycy", kraj: "Mozambik", flaga: "mz", formy: ["Mozambijczyk", "Mozambijczyków", "Mozambijczyków"], dopelniacz: "Mozambijczyków" },
  uz: { nazwa: "Uzbecy", kraj: "Uzbekistan", flaga: "uz", formy: ["Uzbek", "Uzbeków", "Uzbeków"], dopelniacz: "Uzbeków" },
  ye: { nazwa: "Jemeńczycy", kraj: "Jemen", flaga: "ye", formy: ["Jemeńczyk", "Jemeńczyków", "Jemeńczyków"], dopelniacz: "Jemeńczyków" },
  np: { nazwa: "Nepalczycy", kraj: "Nepal", flaga: "np", formy: ["Nepalczyk", "Nepalczyków", "Nepalczyków"], dopelniacz: "Nepalczyków" },
  ve: { nazwa: "Wenezuelczycy", kraj: "Wenezuela", flaga: "ve", formy: ["Wenezuelczyk", "Wenezuelczyków", "Wenezuelczyków"], dopelniacz: "Wenezuelczyków" },
  cm: { nazwa: "Kameruńczycy", kraj: "Kamerun", flaga: "cm", formy: ["Kameruńczyk", "Kameruńczyków", "Kameruńczyków"], dopelniacz: "Kameruńczyków" },
  ci: { nazwa: "Iworyjczycy", kraj: "Wybrzeże Kości Słoniowej", flaga: "ci", formy: ["Iworyjczyk", "Iworyjczyków", "Iworyjczyków"], dopelniacz: "Iworyjczyków" },
  mg: { nazwa: "Malgasze", kraj: "Madagaskar", flaga: "mg", formy: ["Malgasz", "Malgaszów", "Malgaszów"], dopelniacz: "Malgaszów" },
  au: { nazwa: "Australijczycy", kraj: "Australia", flaga: "au", formy: ["Australijczyk", "Australijczyków", "Australijczyków"], dopelniacz: "Australijczyków" },
  kp: { nazwa: "Północnokoreańczycy", kraj: "Korea Północna", flaga: "kp", formy: ["Północnokoreańczyk", "Północnokoreańczyków", "Północnokoreańczyków"], dopelniacz: "Północnokoreańczyków" },
  ne: { nazwa: "Nigerczycy", kraj: "Niger", flaga: "ne", formy: ["Nigerczyk", "Nigerczyków", "Nigerczyków"], dopelniacz: "Nigerczyków" },
  tw: { nazwa: "Tajwańczycy", kraj: "Tajwan", flaga: "tw", formy: ["Tajwańczyk", "Tajwańczyków", "Tajwańczyków"], dopelniacz: "Tajwańczyków" },
  lk: { nazwa: "Lankijczycy", kraj: "Sri Lanka", flaga: "lk", formy: ["Lankijczyk", "Lankijczyków", "Lankijczyków"], dopelniacz: "Lankijczyków" },
  bf: { nazwa: "Burkińczycy", kraj: "Burkina Faso", flaga: "bf", formy: ["Burkińczyk", "Burkińczyków", "Burkińczyków"], dopelniacz: "Burkińczyków" },
  sy: { nazwa: "Syryjczycy", kraj: "Syria", flaga: "sy", formy: ["Syryjczyk", "Syryjczyków", "Syryjczyków"], dopelniacz: "Syryjczyków" },
  mw: { nazwa: "Malawijczycy", kraj: "Malawi", flaga: "mw", formy: ["Malawijczyk", "Malawijczyków", "Malawijczyków"], dopelniacz: "Malawijczyków" },
  ml: { nazwa: "Malijczycy", kraj: "Mali", flaga: "ml", formy: ["Malijczyk", "Malijczyków", "Malijczyków"], dopelniacz: "Malijczyków" },
  zm: { nazwa: "Zambijczycy", kraj: "Zambia", flaga: "zm", formy: ["Zambijczyk", "Zambijczyków", "Zambijczyków"], dopelniacz: "Zambijczyków" },
  kz: { nazwa: "Kazachowie", kraj: "Kazachstan", flaga: "kz", formy: ["Kazach", "Kazachów", "Kazachów"], dopelniacz: "Kazachów" },
  ro: { nazwa: "Rumuni", kraj: "Rumunia", flaga: "ro", formy: ["Rumun", "Rumunów", "Rumunów"], dopelniacz: "Rumunów" },
  cl: { nazwa: "Chilijczycy", kraj: "Chile", flaga: "cl", formy: ["Chilijczyk", "Chilijczyków", "Chilijczyków"], dopelniacz: "Chilijczyków" },
  td: { nazwa: "Czadyjczycy", kraj: "Czad", flaga: "td", formy: ["Czadyjczyk", "Czadyjczyków", "Czadyjczyków"], dopelniacz: "Czadyjczyków" },
  sn: { nazwa: "Senegalczycy", kraj: "Senegal", flaga: "sn", formy: ["Senegalczyk", "Senegalczyków", "Senegalczyków"], dopelniacz: "Senegalczyków" },
  nl: { nazwa: "Holendrzy", kraj: "Holandia", flaga: "nl", formy: ["Holender", "Holendrów", "Holendrów"], dopelniacz: "Holendrów" },
  gt: { nazwa: "Gwatemalczycy", kraj: "Gwatemala", flaga: "gt", formy: ["Gwatemalczyk", "Gwatemalczyków", "Gwatemalczyków"], dopelniacz: "Gwatemalczyków" },
  ec: { nazwa: "Ekwadorczycy", kraj: "Ekwador", flaga: "ec", formy: ["Ekwadorczyk", "Ekwadorczyków", "Ekwadorczyków"], dopelniacz: "Ekwadorczyków" },
  kh: { nazwa: "Kambodżanie", kraj: "Kambodża", flaga: "kh", formy: ["Kambodżanin", "Kambodżan", "Kambodżan"], dopelniacz: "Kambodżan" },
  zw: { nazwa: "Zimbabweńczycy", kraj: "Zimbabwe", flaga: "zw", formy: ["Zimbabweńczyk", "Zimbabweńczyków", "Zimbabweńczyków"], dopelniacz: "Zimbabweńczyków" },
  bj: { nazwa: "Beninczycy", kraj: "Benin", flaga: "bj", formy: ["Beninczyk", "Beninczyków", "Beninczyków"], dopelniacz: "Beninczyków" },
  gn: { nazwa: "Gwinejczycy", kraj: "Gwinea", flaga: "gn", formy: ["Gwinejczyk", "Gwinejczyków", "Gwinejczyków"], dopelniacz: "Gwinejczyków" },
  rw: { nazwa: "Rwandyjczycy", kraj: "Rwanda", flaga: "rw", formy: ["Rwandyjczyk", "Rwandyjczyków", "Rwandyjczyków"], dopelniacz: "Rwandyjczyków" },
  bi: { nazwa: "Burundyjczycy", kraj: "Burundi", flaga: "bi", formy: ["Burundyjczyk", "Burundyjczyków", "Burundyjczyków"], dopelniacz: "Burundyjczyków" },
  so: { nazwa: "Somalijczycy", kraj: "Somalia", flaga: "so", formy: ["Somalijczyk", "Somalijczyków", "Somalijczyków"], dopelniacz: "Somalijczyków" },
  bo: { nazwa: "Boliwijczycy", kraj: "Boliwia", flaga: "bo", formy: ["Boliwijczyk", "Boliwijczyków", "Boliwijczyków"], dopelniacz: "Boliwijczyków" },
  tn: { nazwa: "Tunezyjczycy", kraj: "Tunezja", flaga: "tn", formy: ["Tunezyjczyk", "Tunezyjczyków", "Tunezyjczyków"], dopelniacz: "Tunezyjczyków" },
  be: { nazwa: "Belgowie", kraj: "Belgia", flaga: "be", formy: ["Belg", "Belgów", "Belgów"], dopelniacz: "Belgów" },
  ss: { nazwa: "Południowosudańczycy", kraj: "Sudan Południowy", flaga: "ss", formy: ["Południowosudańczyk", "Południowosudańczyków", "Południowosudańczyków"], dopelniacz: "Południowosudańczyków" },
  ht: { nazwa: "Haitańczycy", kraj: "Haiti", flaga: "ht", formy: ["Haitańczyk", "Haitańczyków", "Haitańczyków"], dopelniacz: "Haitańczyków" },
  cu: { nazwa: "Kubańczycy", kraj: "Kuba", flaga: "cu", formy: ["Kubańczyk", "Kubańczyków", "Kubańczyków"], dopelniacz: "Kubańczyków" },
  jo: { nazwa: "Jordańczycy", kraj: "Jordania", flaga: "jo", formy: ["Jordańczyk", "Jordańczyków", "Jordańczyków"], dopelniacz: "Jordańczyków" },
  do: { nazwa: "Dominikańczycy", kraj: "Dominikana", flaga: "do", formy: ["Dominikańczyk", "Dominikańczyków", "Dominikańczyków"], dopelniacz: "Dominikańczyków" },
  gr: { nazwa: "Grecy", kraj: "Grecja", flaga: "gr", formy: ["Grek", "Greków", "Greków"], dopelniacz: "Greków" },
  se: { nazwa: "Szwedzi", kraj: "Szwecja", flaga: "se", formy: ["Szwed", "Szwedów", "Szwedów"], dopelniacz: "Szwedów" },
  az: { nazwa: "Azerowie", kraj: "Azerbejdżan", flaga: "az", formy: ["Azer", "Azerów", "Azerów"], dopelniacz: "Azerów" },
  pt: { nazwa: "Portugalczycy", kraj: "Portugalia", flaga: "pt", formy: ["Portugalczyk", "Portugalczyków", "Portugalczyków"], dopelniacz: "Portugalczyków" },
  ae: { nazwa: "Emiratczycy", kraj: "ZEA", flaga: "ae", formy: ["Emiratczyk", "Emiratczyków", "Emiratczyków"], dopelniacz: "Emiratczyków" },
  il: { nazwa: "Izraelczycy", kraj: "Izrael", flaga: "il", formy: ["Izraelczyk", "Izraelczyków", "Izraelczyków"], dopelniacz: "Izraelczyków" },
  hu: { nazwa: "Węgrzy", kraj: "Węgry", flaga: "hu", formy: ["Węgier", "Węgrów", "Węgrów"], dopelniacz: "Węgrów" },
  pg: { nazwa: "Papuańczycy", kraj: "Papua-Nowa Gwinea", flaga: "pg", formy: ["Papuańczyk", "Papuańczyków", "Papuańczyków"], dopelniacz: "Papuańczyków" },
  hn: { nazwa: "Honduranie", kraj: "Honduras", flaga: "hn", formy: ["Honduranin", "Honduran", "Honduran"], dopelniacz: "Honduran" },
  tj: { nazwa: "Tadżycy", kraj: "Tadżykistan", flaga: "tj", formy: ["Tadżyk", "Tadżyków", "Tadżyków"], dopelniacz: "Tadżyków" },
  at: { nazwa: "Austriacy", kraj: "Austria", flaga: "at", formy: ["Austriak", "Austriaków", "Austriaków"], dopelniacz: "Austriaków" },
  sl: { nazwa: "Sierraleończycy", kraj: "Sierra Leone", flaga: "sl", formy: ["Sierraleończyk", "Sierraleończyków", "Sierraleończyków"], dopelniacz: "Sierraleończyków" },
  ch: { nazwa: "Szwajcarzy", kraj: "Szwajcaria", flaga: "ch", formy: ["Szwajcar", "Szwajcarów", "Szwajcarów"], dopelniacz: "Szwajcarów" },
  tg: { nazwa: "Togijczycy", kraj: "Togo", flaga: "tg", formy: ["Togijczyk", "Togijczyków", "Togijczyków"], dopelniacz: "Togijczyków" },
  la: { nazwa: "Laotańczycy", kraj: "Laos", flaga: "la", formy: ["Laotańczyk", "Laotańczyków", "Laotańczyków"], dopelniacz: "Laotańczyków" },
  py: { nazwa: "Paragwajczycy", kraj: "Paragwaj", flaga: "py", formy: ["Paragwajczyk", "Paragwajczyków", "Paragwajczyków"], dopelniacz: "Paragwajczyków" },
  hk: { nazwa: "Hongkończycy", kraj: "Hongkong", flaga: "hk", formy: ["Hongkończyk", "Hongkończyków", "Hongkończyków"], dopelniacz: "Hongkończyków" },
  ly: { nazwa: "Libijczycy", kraj: "Libia", flaga: "ly", formy: ["Libijczyk", "Libijczyków", "Libijczyków"], dopelniacz: "Libijczyków" },
  bg: { nazwa: "Bułgarzy", kraj: "Bułgaria", flaga: "bg", formy: ["Bułgar", "Bułgarów", "Bułgarów"], dopelniacz: "Bułgarów" },
  rs: { nazwa: "Serbowie", kraj: "Serbia", flaga: "rs", formy: ["Serb", "Serbów", "Serbów"], dopelniacz: "Serbów" },
  sv: { nazwa: "Salwadorczycy", kraj: "Salwador", flaga: "sv", formy: ["Salwadorczyk", "Salwadorczyków", "Salwadorczyków"], dopelniacz: "Salwadorczyków" },
  nic: { nazwa: "Nikaraguańczycy", kraj: "Nikaragua", flaga: "ni", formy: ["Nikaraguańczyk", "Nikaraguańczyków", "Nikaraguańczyków"], dopelniacz: "Nikaraguańczyków" },
  kg: { nazwa: "Kirgizi", kraj: "Kirgistan", flaga: "kg", formy: ["Kirgiz", "Kirgizów", "Kirgizów"], dopelniacz: "Kirgizów" },
  er: { nazwa: "Erytrejczycy", kraj: "Erytrea", flaga: "er", formy: ["Erytrejczyk", "Erytrejczyków", "Erytrejczyków"], dopelniacz: "Erytrejczyków" },
  sg: { nazwa: "Singapurczycy", kraj: "Singapur", flaga: "sg", formy: ["Singapurczyk", "Singapurczyków", "Singapurczyków"], dopelniacz: "Singapurczyków" },
  dk: { nazwa: "Duńczycy", kraj: "Dania", flaga: "dk", formy: ["Duńczyk", "Duńczyków", "Duńczyków"], dopelniacz: "Duńczyków" },
  tm: { nazwa: "Turkmeni", kraj: "Turkmenistan", flaga: "tm", formy: ["Turkmen", "Turkmenów", "Turkmenów"], dopelniacz: "Turkmenów" },
  fi: { nazwa: "Finowie", kraj: "Finlandia", flaga: "fi", formy: ["Fin", "Finów", "Finów"], dopelniacz: "Finów" },
  no: { nazwa: "Norwegowie", kraj: "Norwegia", flaga: "no", formy: ["Norweg", "Norwegów", "Norwegów"], dopelniacz: "Norwegów" },
  cg: { nazwa: "Kongijczycy (Kongo)", kraj: "Kongo", flaga: "cg", formy: ["Kongijczyk", "Kongijczyków", "Kongijczyków"], dopelniacz: "Kongijczyków" },
  cf: { nazwa: "Środkowoafrykańczycy", kraj: "Republika Środkowoafrykańska", flaga: "cf", formy: ["Środkowoafrykańczyk", "Środkowoafrykańczyków", "Środkowoafrykańczyków"], dopelniacz: "Środkowoafrykańczyków" },
  sk: { nazwa: "Słowacy", kraj: "Słowacja", flaga: "sk", formy: ["Słowak", "Słowaków", "Słowaków"], dopelniacz: "Słowaków" },
  lr: { nazwa: "Liberyjczycy", kraj: "Liberia", flaga: "lr", formy: ["Liberyjczyk", "Liberyjczyków", "Liberyjczyków"], dopelniacz: "Liberyjczyków" },
  lb: { nazwa: "Libańczycy", kraj: "Liban", flaga: "lb", formy: ["Libańczyk", "Libańczyków", "Libańczyków"], dopelniacz: "Libańczyków" },
  ie: { nazwa: "Irlandczycy", kraj: "Irlandia", flaga: "ie", formy: ["Irlandczyk", "Irlandczyków", "Irlandczyków"], dopelniacz: "Irlandczyków" },
  cr: { nazwa: "Kostarykańczycy", kraj: "Kostaryka", flaga: "cr", formy: ["Kostarykańczyk", "Kostarykańczyków", "Kostarykańczyków"], dopelniacz: "Kostarykańczyków" },
  nz: { nazwa: "Nowozelandczycy", kraj: "Nowa Zelandia", flaga: "nz", formy: ["Nowozelandczyk", "Nowozelandczyków", "Nowozelandczyków"], dopelniacz: "Nowozelandczyków" },
  ge: { nazwa: "Gruzini", kraj: "Gruzja", flaga: "ge", formy: ["Gruzin", "Gruzinów", "Gruzinów"], dopelniacz: "Gruzinów" },
  pa: { nazwa: "Panamczycy", kraj: "Panama", flaga: "pa", formy: ["Panamczyk", "Panamczyków", "Panamczyków"], dopelniacz: "Panamczyków" },
  hr: { nazwa: "Chorwaci", kraj: "Chorwacja", flaga: "hr", formy: ["Chorwat", "Chorwatów", "Chorwatów"], dopelniacz: "Chorwatów" },
  mr: { nazwa: "Mauretańczycy", kraj: "Mauretania", flaga: "mr", formy: ["Mauretańczyk", "Mauretańczyków", "Mauretańczyków"], dopelniacz: "Mauretańczyków" },
  ba: { nazwa: "Bośniacy", kraj: "Bośnia i Hercegowina", flaga: "ba", formy: ["Bośniak", "Bośniaków", "Bośniaków"], dopelniacz: "Bośniaków" },
  om: { nazwa: "Omańczycy", kraj: "Oman", flaga: "om", formy: ["Omańczyk", "Omańczyków", "Omańczyków"], dopelniacz: "Omańczyków" },
  uy: { nazwa: "Urugwajczycy", kraj: "Urugwaj", flaga: "uy", formy: ["Urugwajczyk", "Urugwajczyków", "Urugwajczyków"], dopelniacz: "Urugwajczyków" },
  md: { nazwa: "Mołdawianie", kraj: "Mołdawia", flaga: "md", formy: ["Mołdawianin", "Mołdawian", "Mołdawian"], dopelniacz: "Mołdawian" },
  mn: { nazwa: "Mongołowie", kraj: "Mongolia", flaga: "mn", formy: ["Mongoł", "Mongołów", "Mongołów"], dopelniacz: "Mongołów" },
  pr: { nazwa: "Portorykańczycy", kraj: "Portoryko", flaga: "pr", formy: ["Portorykańczyk", "Portorykańczyków", "Portorykańczyków"], dopelniacz: "Portorykańczyków" },
  al: { nazwa: "Albańczycy", kraj: "Albania", flaga: "al", formy: ["Albańczyk", "Albańczyków", "Albańczyków"], dopelniacz: "Albańczyków" },
  am: { nazwa: "Ormianie", kraj: "Armenia", flaga: "am", formy: ["Ormianin", "Ormian", "Ormian"], dopelniacz: "Ormian" },
  jm: { nazwa: "Jamajczycy", kraj: "Jamajka", flaga: "jm", formy: ["Jamajczyk", "Jamajczyków", "Jamajczyków"], dopelniacz: "Jamajczyków" },
  na: { nazwa: "Namibijczycy", kraj: "Namibia", flaga: "na", formy: ["Namibijczyk", "Namibijczyków", "Namibijczyków"], dopelniacz: "Namibijczyków" },
  lt: { nazwa: "Litwini", kraj: "Litwa", flaga: "lt", formy: ["Litwin", "Litwinów", "Litwinów"], dopelniacz: "Litwinów" },
  qa: { nazwa: "Katarczycy", kraj: "Katar", flaga: "qa", formy: ["Katarczyk", "Katarczyków", "Katarczyków"], dopelniacz: "Katarczyków" },
  gm: { nazwa: "Gambijczycy", kraj: "Gambia", flaga: "gm", formy: ["Gambijczyk", "Gambijczyków", "Gambijczyków"], dopelniacz: "Gambijczyków" },
  bw: { nazwa: "Botswańczycy", kraj: "Botswana", flaga: "bw", formy: ["Botswańczyk", "Botswańczyków", "Botswańczyków"], dopelniacz: "Botswańczyków" },
  ga: { nazwa: "Gabończycy", kraj: "Gabon", flaga: "ga", formy: ["Gabończyk", "Gabończyków", "Gabończyków"], dopelniacz: "Gabończyków" },
  ls: { nazwa: "Lesothyjczycy", kraj: "Lesotho", flaga: "ls", formy: ["Lesothyjczyk", "Lesothyjczyków", "Lesothyjczyków"], dopelniacz: "Lesothyjczyków" },
  mk: { nazwa: "Macedończycy", kraj: "Macedonia Północna", flaga: "mk", formy: ["Macedończyk", "Macedończyków", "Macedończyków"], dopelniacz: "Macedończyków" },
  si: { nazwa: "Słoweńcy", kraj: "Słowenia", flaga: "si", formy: ["Słoweniec", "Słoweńców", "Słoweńców"], dopelniacz: "Słoweńców" },
  gw: { nazwa: "Gwinejczycy (Bissau)", kraj: "Gwinea Bissau", flaga: "gw", formy: ["Gwinejczyk", "Gwinejczyków", "Gwinejczyków"], dopelniacz: "Gwinejczyków" },
  ps: { nazwa: "Palestyńczycy", kraj: "Palestyna", flaga: "ps", formy: ["Palestyńczyk", "Palestyńczyków", "Palestyńczyków"], dopelniacz: "Palestyńczyków" },
  xk: { nazwa: "Kosowianie", kraj: "Kosowo", flaga: "xk", formy: ["Kosowianin", "Kosowian", "Kosowian"], dopelniacz: "Kosowian" },
  lv: { nazwa: "Łotysze", kraj: "Łotwa", flaga: "lv", formy: ["Łotysz", "Łotyszy", "Łotyszy"], dopelniacz: "Łotyszy" },
  gq: { nazwa: "Gwinejczycy (Równikowa)", kraj: "Gwinea Równikowa", flaga: "gq", formy: ["Gwinejczyk", "Gwinejczyków", "Gwinejczyków"], dopelniacz: "Gwinejczyków" },
  bh: { nazwa: "Bahrajńczycy", kraj: "Bahrajn", flaga: "bh", formy: ["Bahrajńczyk", "Bahrajńczyków", "Bahrajńczyków"], dopelniacz: "Bahrajńczyków" },
  mu: { nazwa: "Maurytyjczycy", kraj: "Mauritius", flaga: "mu", formy: ["Maurytyjczyk", "Maurytyjczyków", "Maurytyjczyków"], dopelniacz: "Maurytyjczyków" },
  tl: { nazwa: "Timorczycy", kraj: "Timor Wschodni", flaga: "tl", formy: ["Timorczyk", "Timorczyków", "Timorczyków"], dopelniacz: "Timorczyków" },
  tt: { nazwa: "Trynidadczycy", kraj: "Trynidad i Tobago", flaga: "tt", formy: ["Trynidadczyk", "Trynidadczyków", "Trynidadczyków"], dopelniacz: "Trynidadczyków" },
  cy: { nazwa: "Cypryjczycy", kraj: "Cypr", flaga: "cy", formy: ["Cypryjczyk", "Cypryjczyków", "Cypryjczyków"], dopelniacz: "Cypryjczyków" },
  ee: { nazwa: "Estończycy", kraj: "Estonia", flaga: "ee", formy: ["Estończyk", "Estończyków", "Estończyków"], dopelniacz: "Estończyków" },
  sz: { nazwa: "Suazi", kraj: "Eswatini", flaga: "sz", formy: ["Suazi", "Suazich", "Suazich"], dopelniacz: "Suazich" },
  dj: { nazwa: "Dżibutyjczycy", kraj: "Dżibuti", flaga: "dj", formy: ["Dżibutyjczyk", "Dżibutyjczyków", "Dżibutyjczyków"], dopelniacz: "Dżibutyjczyków" },
  fj: { nazwa: "Fidżyjczycy", kraj: "Fidżi", flaga: "fj", formy: ["Fidżyjczyk", "Fidżyjczyków", "Fidżyjczyków"], dopelniacz: "Fidżyjczyków" },
  km: { nazwa: "Komoryjczycy", kraj: "Komory", flaga: "km", formy: ["Komoryjczyk", "Komoryjczyków", "Komoryjczyków"], dopelniacz: "Komoryjczyków" },
  gy: { nazwa: "Gujańczycy", kraj: "Gujana", flaga: "gy", formy: ["Gujańczyk", "Gujańczyków", "Gujańczyków"], dopelniacz: "Gujańczyków" },
  sb: { nazwa: "Salomończycy", kraj: "Wyspy Salomona", flaga: "sb", formy: ["Salomończyk", "Salomończyków", "Salomończyków"], dopelniacz: "Salomończyków" },
  lu: { nazwa: "Luksemburczycy", kraj: "Luksemburg", flaga: "lu", formy: ["Luksemburczyk", "Luksemburczyków", "Luksemburczyków"], dopelniacz: "Luksemburczyków" },
  mo: { nazwa: "Makańczycy", kraj: "Makau", flaga: "mo", formy: ["Makańczyk", "Makańczyków", "Makańczyków"], dopelniacz: "Makańczyków" },
  sr: { nazwa: "Surinamczycy", kraj: "Surinam", flaga: "sr", formy: ["Surinamczyk", "Surinamczyków", "Surinamczyków"], dopelniacz: "Surinamczyków" },
  me: { nazwa: "Czarnogórcy", kraj: "Czarnogóra", flaga: "me", formy: ["Czarnogórzec", "Czarnogórców", "Czarnogórców"], dopelniacz: "Czarnogórców" },
  cv: { nazwa: "Kabowerdeńczycy", kraj: "Republika Zielonego Przylądka", flaga: "cv", formy: ["Kabowerdeńczyk", "Kabowerdeńczyków", "Kabowerdeńczyków"], dopelniacz: "Kabowerdeńczyków" },
  mt: { nazwa: "Maltańczycy", kraj: "Malta", flaga: "mt", formy: ["Maltańczyk", "Maltańczyków", "Maltańczyków"], dopelniacz: "Maltańczyków" },
  is: { nazwa: "Islandczycy", kraj: "Islandia", flaga: "is", formy: ["Islandczyk", "Islandczyków", "Islandczyków"], dopelniacz: "Islandczyków" },
  vu: { nazwa: "Vanuatczycy", kraj: "Vanuatu", flaga: "vu", formy: ["Vanuatczyk", "Vanuatczyków", "Vanuatczyków"], dopelniacz: "Vanuatczyków" },
  ad: { nazwa: "Andorczycy", kraj: "Andora", flaga: "ad", formy: ["Andorczyk", "Andorczyków", "Andorczyków"], dopelniacz: "Andorczyków" },
  ag: { nazwa: "Antiguańczycy", kraj: "Antigua i Barbuda", flaga: "ag", formy: ["Antiguańczyk", "Antiguańczyków", "Antiguańczyków"], dopelniacz: "Antiguańczyków" },
  aw: { nazwa: "Arubańczycy", kraj: "Aruba", flaga: "aw", formy: ["Arubańczyk", "Arubańczyków", "Arubańczyków"], dopelniacz: "Arubańczyków" },
  bb: { nazwa: "Barbadosyjczycy", kraj: "Barbados", flaga: "bb", formy: ["Barbadosyjczyk", "Barbadosyjczyków", "Barbadosyjczyków"], dopelniacz: "Barbadosyjczyków" },
  bm: { nazwa: "Bermudczycy", kraj: "Bermudy", flaga: "bm", formy: ["Bermudczyk", "Bermudczyków", "Bermudczyków"], dopelniacz: "Bermudczyków" },
  bq: { nazwa: "Bonairczycy", kraj: "Bonaire", flaga: "bq", formy: ["Bonairczyk", "Bonairczyków", "Bonairczyków"], dopelniacz: "Bonairczyków" },
  cw: { nazwa: "Curaçaoczycy", kraj: "Curaçao", flaga: "cw", formy: ["Curaçaoczyk", "Curaçaoczyków", "Curaçaoczyków"], dopelniacz: "Curaçaoczyków" },
  gi: { nazwa: "Gibraltarczycy", kraj: "Gibraltar", flaga: "gi", formy: ["Gibraltarczyk", "Gibraltarczyków", "Gibraltarczyków"], dopelniacz: "Gibraltarczyków" },
  gd: { nazwa: "Grenadyjczycy", kraj: "Grenada", flaga: "gd", formy: ["Grenadyjczyk", "Grenadyjczyków", "Grenadyjczyków"], dopelniacz: "Grenadyjczyków" },
  gl: { nazwa: "Grenlandczycy", kraj: "Grenlandia", flaga: "gl", formy: ["Grenlandczyk", "Grenlandczyków", "Grenlandczyków"], dopelniacz: "Grenlandczyków" },
  gf: { nazwa: "Gujańczycy (Francuska)", kraj: "Gujana Francuska", flaga: "gf", formy: ["Gujańczyk", "Gujańczyków", "Gujańczyków"], dopelniacz: "Gujańczyków" },
  gp: { nazwa: "Gwadelupczycy", kraj: "Gwadelupa", flaga: "gp", formy: ["Gwadelupczyk", "Gwadelupczyków", "Gwadelupczyków"], dopelniacz: "Gwadelupczyków" },
  ky: { nazwa: "Kajmańczycy", kraj: "Kajmany", flaga: "ky", formy: ["Kajmańczyk", "Kajmańczyków", "Kajmańczyków"], dopelniacz: "Kajmańczyków" },
  li: { nazwa: "Liechtensteińczycy", kraj: "Liechtenstein", flaga: "li", formy: ["Liechtensteińczyk", "Liechtensteińczyków", "Liechtensteińczyków"], dopelniacz: "Liechtensteińczyków" },
  mq: { nazwa: "Martynikańczycy", kraj: "Martynika", flaga: "mq", formy: ["Martynikańczyk", "Martynikańczyków", "Martynikańczyków"], dopelniacz: "Martynikańczyków" },
  ms: { nazwa: "Montserratczycy", kraj: "Montserrat", flaga: "ms", formy: ["Montserratczyk", "Montserratczyków", "Montserratczyków"], dopelniacz: "Montserratczyków" },
  nu: { nazwa: "Niuejczycy", kraj: "Niue", flaga: "nu", formy: ["Niuejczyk", "Niuejczyków", "Niuejczyków"], dopelniacz: "Niuejczyków" },
  mp: { nazwa: "Marianczycy", kraj: "Mariany Północne", flaga: "mp", formy: ["Marianczyk", "Marianczyków", "Marianczyków"], dopelniacz: "Marianczyków" },
  nc: { nazwa: "Nowokaledończycy", kraj: "Nowa Kaledonia", flaga: "nc", formy: ["Nowokaledończyk", "Nowokaledończyków", "Nowokaledończyków"], dopelniacz: "Nowokaledończyków" },
  ws: { nazwa: "Samoańczycy", kraj: "Samoa", flaga: "ws", formy: ["Samoańczyk", "Samoańczyków", "Samoańczyków"], dopelniacz: "Samoańczyków" },
  as: { nazwa: "Samoańczycy (Amerykańskie)", kraj: "Samoa Amerykańskie", flaga: "as", formy: ["Samoańczyk", "Samoańczyków", "Samoańczyków"], dopelniacz: "Samoańczyków" },
  sm: { nazwa: "Sanmaryńczycy", kraj: "San Marino", flaga: "sm", formy: ["Sanmaryńczyk", "Sanmaryńczyków", "Sanmaryńczyków"], dopelniacz: "Sanmaryńczyków" },
  syc: { nazwa: "Seszelczycy", kraj: "Seszele", flaga: "sc", formy: ["Seszelczyk", "Seszelczyków", "Seszelczyków"], dopelniacz: "Seszelczyków" },
  sx: { nazwa: "Sint Maarteńczycy", kraj: "Sint Maarten", flaga: "sx", formy: ["Sint Maarteńczyk", "Sint Maarteńczyków", "Sint Maarteńczyków"], dopelniacz: "Sint Maarteńczyków" },
  mf: { nazwa: "Saint-Martińczycy", kraj: "Saint-Martin", flaga: "mf", formy: ["Saint-Martińczyk", "Saint-Martińczyków", "Saint-Martińczyków"], dopelniacz: "Saint-Martińczyków" },
  kn: { nazwa: "Kittyjczycy", kraj: "Saint Kitts i Nevis", flaga: "kn", formy: ["Kittyjczyk", "Kittyjczyków", "Kittyjczyków"], dopelniacz: "Kittyjczyków" },
  lc: { nazwa: "Lucyjczycy", kraj: "Saint Lucia", flaga: "lc", formy: ["Lucyjczyk", "Lucyjczyków", "Lucyjczyków"], dopelniacz: "Lucyjczyków" },
  vc: { nazwa: "Vincentczycy", kraj: "Saint Vincent i Grenadyny", flaga: "vc", formy: ["Vincentczyk", "Vincentczyków", "Vincentczyków"], dopelniacz: "Vincentczyków" },
  to: { nazwa: "Tongijczycy", kraj: "Tonga", flaga: "to", formy: ["Tongijczyk", "Tongijczyków", "Tongijczyków"], dopelniacz: "Tongijczyków" },
  tc: { nazwa: "Turkskaikosowie", kraj: "Turks i Caicos", flaga: "tc", formy: ["Turkskaikos", "Turkskaikosów", "Turkskaikosów"], dopelniacz: "Turkskaikosów" },
  tv: { nazwa: "Tuvaluańczycy", kraj: "Tuvalu", flaga: "tv", formy: ["Tuvaluańczyk", "Tuvaluańczyków", "Tuvaluańczyków"], dopelniacz: "Tuvaluańczyków" },
  ck: { nazwa: "Cookowie", kraj: "Wyspy Cooka", flaga: "ck", formy: ["Cook", "Cooków", "Cooków"], dopelniacz: "Cooków" },
  fo: { nazwa: "Farerczycy", kraj: "Wyspy Owcze", flaga: "fo", formy: ["Farerczyk", "Farerczyków", "Farerczyków"], dopelniacz: "Farerczyków" },
  st: { nazwa: "Santomejczycy", kraj: "Wyspy Świętego Tomasza i Książęca", flaga: "st", formy: ["Santomejczyk", "Santomejczyków", "Santomejczyków"], dopelniacz: "Santomejczyków" },
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
