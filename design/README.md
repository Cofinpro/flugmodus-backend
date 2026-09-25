# Flugmodus Design Language

Der Look der Flugmodus-Startseite zum Mitnehmen: Idee, Regeln, Tokens, Bausteine. Gedacht vor allem dafür, **eine bestehende App umzustylen**, ohne an ihrer Funktion etwas zu ändern.

| Datei | Wofür |
|---|---|
| `flugmodus.css` | Tokens (CSS-Variablen `--fm-*`), Skin für normales HTML (`fm-skin`) und Bausteine (Klassen `fm-*`) |
| `sky.js` | Nachthimmel: Sterne, Flugroute, Sternschnuppen, Pixel-Funkeln |
| `styleguide.html` | Alles live: Farben, Schrift, Bausteine, normales HTML mit Skin, drei Beispiel-Screens. Direkt im Browser öffnen. |

Kein Build, kein Framework. Vom Backend werden die Dateien auch unter `/design/…` ausgeliefert, z. B. `http://localhost:8001/design/styleguide.html`.

## 0. Bestehende App umstylen, in 4 Schritten

Nur Optik, keine Logik: Es werden eine CSS-Datei, ein Skript und ein paar Klassen ergänzt. JavaScript, Routen und Datenfluss der App bleiben unangetastet.

**1. Dateien einbinden.** `flugmodus.css` und `sky.js` ins Projekt kopieren und im `<head>` **nach** dem bisherigen CSS laden:

```html
<link rel="stylesheet" href="…/app.css">          <!-- bestehendes CSS -->
<link rel="stylesheet" href="…/flugmodus.css">    <!-- danach -->
<script src="…/sky.js" defer></script>
```

**2. Himmel und Skin an die Wurzel.** Am `<body>` bzw. am Wurzelelement der App:

```html
<body class="fm-page fm-skin">
```

`fm-page` malt den Nachthimmel, `fm-skin` gibt normalen Elementen den Look: Überschriften, Absätze, Links, Buttons (`type="submit"` wird Amber), Eingaben, Selects, Checkboxen, Tabellen, Dialoge. Wie das aussieht, zeigt der Abschnitt „Bestehende App“ im Styleguide.

**3. Inhalt auf Papier legen.** Das ist der wichtigste Schritt. Text ist dunkel und gehört nie direkt auf den Himmel. Den Container, der den Inhalt eines Screens hält, zur Karte machen und mittig setzen:

```html
<div id="app" class="fm-center">          <!-- bisheriger Wrapper -->
  <main class="fm-card">…bisheriger Inhalt…</main>
</div>
```

Für Screens mit QR-Code (Zahlung anfordern, Münze zeigen) statt `fm-card` ein Ticket mit Abriss verwenden, siehe `fm-ticket` unten und Beispiel 1 im Styleguide.

**4. Alte Farben und Schriften entfernen.** Wo das bisherige CSS Hintergründe, Schriftarten, Button-Farben oder Rahmen setzt, diese Regeln löschen oder durch die Tokens ersetzen (`var(--fm-ink)`, `var(--fm-amber)` …). Die Skin hat bewusst **niedrige Spezifität**: Klassen der App gewinnen immer. So geht nichts kaputt, aber alte Farben überdecken die neuen, bis sie weg sind.

Danach nach Geschmack aufwerten: den großen Betrag mit `fm-amount`, Label-Wert-Paare mit `fm-fields`, Status mit `fm-status`. Alles unter „Bausteine“.

**Wenn die App React, Vue oder Svelte nutzt:** gleiches Vorgehen. `class` wird dann zu `className` o. Ä., und die CSS-Datei wird in der Einstiegsdatei importiert. **Wenn es eine native App ist** (Swift, Kotlin, Flutter): Das CSS lässt sich dort nicht verwenden. Dann gelten die Tokens und Regeln aus dieser Datei, und die Bausteine müssen nachgebaut werden.

---

## 1. Die Idee

**Flugmodus = Bargeld, das auch ohne Netz funktioniert.** Darum ist jeder Screen ein **Reisedokument auf Papier unter einem Nachthimmel**: Boarding Pass, Ticket, Beleg.

## 2. Fünf Regeln

1. **Zwei Flächen, nie mehr.** Der *Himmel* ist Bühne und trägt nie Inhalt. Alles, was man lesen oder anfassen soll, liegt auf *Papier* (`fm-ticket`, `fm-card`). Kein Text direkt auf dem Himmel. Einzige Ausnahme sind Feier-Momente wie das Nyan-Flugzeug.
2. **Ticket-Grammatik.** Labels klein in Mono-Versalien (`PASSAGIER`), Werte darunter groß. Große Codes für das Wichtigste (`ONL → OFF`, `3 €`). Die **Perforation** trennt „das behalte ich“ (Hauptteil) von „das zeige oder gebe ich her“ (Stub, z. B. mit QR-Code).
3. **Genau ein Akzent.** Amber heißt „hier passiert was“: die eine Hauptaktion, der eine heiße Wert, die QR-Ecken. Pro Screen **höchstens ein** `fm-btn--accent`. Grün und Rot nur für Status, nie als Deko.
4. **Drei Schriften, feste Rollen.** Space Grotesk für alles, JetBrains Mono nur für Labels und Status, Instrument Serif *kursiv* nur für einen emotionalen Halbsatz („*auch ohne Netz.*“).
5. **Ruhig, mit einem Wow-Moment.** Der Himmel bewegt sich langsam. Pro Ereignis (Zahlung gesendet, Münze empfangen) gibt es **einen** kurzen Effekt, z. B. Funkeln. Bei „Bewegung reduzieren“ fällt alles Bewegte weg, und das ist in CSS und `sky.js` schon eingebaut.

## 3. Tokens

### Farben

| Token | Wert | Rolle |
|---|---|---|
| `--fm-sky-top` → `--fm-sky` | `#0d1533` → `#070911` | Himmel-Verlauf (plus blaue und amberfarbene Glows) |
| `--fm-paper` | `#f3eee4` | Papier, jede Inhaltsfläche |
| `--fm-paper-edge` | `#e4dccd` | Perforation, zarte Linien |
| `--fm-ink` | `#121419` | Text, Linien, dunkle Buttons |
| `--fm-ink-soft` | `#6b6457` | Labels, Nebentext |
| `--fm-amber` | `#ffb547` | Akzent auf dunklem Grund, Accent-Button |
| `--fm-amber-deep` | `#e8891c` | Akzent auf Papier (heißer Wert, QR-Ecken, Fokus) |
| `--fm-green` | `#1fbf6a` | Status „läuft / ok“ |
| `--fm-red` | `#c2381f` | Fehler |

Der QR-Code ist **immer dunkel auf Weiß**, sonst scannt er schlecht.
Das QR-SVG braucht eine `viewBox`, damit `fm-qr` es auf die richtige Größe skalieren kann. Mit `segno` heißt das `svg_inline(..., omitsize=True)`, mit anderen Bibliotheken entsprechend.

### Schrift

| Rolle | Stil |
|---|---|
| Code / Betrag | Space Grotesk 700, 48–96 px, Laufweite −0.045em, Zeilenhöhe 0.82 |
| Titel | Space Grotesk 700, 26 px, −0.02em |
| Wert / Fließtext | Space Grotesk 500, 16–19 px |
| Label | JetBrains Mono 10–11 px, VERSALIEN, Laufweite 0.16–0.2em, `--fm-ink-soft` |
| Emotion | Instrument Serif *kursiv*, 1.2× der Umgebung, nur ein Halbsatz pro Screen |

### Form und Abstand

- **Radien:** Ticket und Karte `22px`, Buttons `14px`, Hinweise `10px`, Tags voll rund. Die Kerben an der Perforation haben einen Radius von `15px`.
- **Linien:** immer `1.5px` in Tinte, Perforation `2px` gestrichelt in `--fm-paper-edge`.
- **Abstände:** in 4er-Schritten. Innenabstand von Papier 24 px am Handy, 36–40 px am Desktop. Zwischen Blöcken 24–30 px.
- **Schatten:** nur Papier bekommt einen Schatten (`--fm-shadow-ticket`), sonst nichts.

## 4. Bausteine

Alles live in `styleguide.html`. Die wichtigsten:

| Klasse | Was |
|---|---|
| `fm-page`, `fm-center`, `fm-stack` | Seite mit Himmel und Filmkorn; Inhalt mittig; Abstand zwischen mehreren Papieren |
| `fm-skin` | Look für normales HTML ohne Klassen (siehe Abschnitt 0) |
| `fm-ticket` + `fm-ticket-main` + `fm-ticket-stub` | Ticket mit Perforation. Standard hochkant (Handy); `fm-ticket--wide` ab 761 px quer; `fm-ticket--arrive` = Einflug-Animation. Ohne Stub wird es ein normales Papier mit runden Ecken. |
| `fm-card` | Papier ohne Perforation (Listen, Formulare) |
| `fm-ticket-head`, `fm-brand`, `fm-logo`, `fm-tag` | Kopfzeile: Logo und Name links, Dokumentart rechts („BOARDING PASS“, „ZAHLUNG“) |
| `fm-route`, `fm-port`, `fm-port--to`, `fm-route-path` | „A → B“ in großen Codes; das Ziel nur als Kontur |
| `fm-fields` (`--2`), `fm-field`, `fm-hot` | Label-Wert-Raster mit Linie oben, 3 oder 2 Spalten |
| `fm-amount` | Großer Betrag, `<small>€</small>` für die Währung |
| `fm-kicker`, `fm-label`, `fm-title`, `fm-tagline`, `fm-muted` | Texte |
| `fm-qr` | Weißer QR-Rahmen mit Amber-Ecken (für `svg`, `img` oder `canvas`) |
| `fm-status` (`--wait`, `--error`, `--idle`) | Mono-Status mit pulsierendem Punkt |
| `fm-btn` (`--accent`, `--ghost`, `--block`), `fm-actions` (`--row`) | Buttons: dunkel = normal, Amber = die eine Hauptaktion, Kontur = zurück/abbrechen |
| `fm-input` (`--invalid`) | Eingabe mit Mono-Label und Linie statt Kasten |
| `fm-notice` (`--ok`, `--warn`, `--error`) | Hinweisbox |
| `fm-rule` (`--perforated`) | Trennlinie |
| `fm-segmented` | Umschalter mit zwei Optionen: Pille mit dunklem Schieber, der dem Knopf mit `aria-pressed="true"` folgt (reines CSS). Aktive Beschriftung in Amber. |
| `fm-log` (`--wide`) | Live-Tabelle wie eine Abflugtafel auf Papier: Kopf mit Titel und Status, Spalten per `--fm-log-cols`. Zeilen `fm-log-row > fm-log-cells` mit `-time`, `-code` (`--new` Amber, `--pay` Grün, `--alert` Rot), `-who`, `-what`, `-amount` (`--in` / `--out`). `fm-log-row--fresh` klappt eine neue Zeile auf (alles darüber rutscht weich mit), `--leaving` klappt sie zu. Am Handy nur Code, Wer, Betrag – darum auch in der Kopfzeile `fm-log-time` / `fm-log-what` an die Zellen. |

### `sky.js`

Erzeugt den Himmel von selbst. Einzelne Teile abschalten:

```html
<body class="fm-page" data-fm-meteors="off" data-fm-route="off">
```

Für eigene Wow-Momente:

```js
FlugmodusSky.sparkle(x, y)             // ein Pixel-Funken an Bildschirmkoordinaten
FlugmodusSky.sparkleAround(element)    // Funken rund um ein Element, z. B. im Intervall
FlugmodusSky.shoot()                   // sofort eine Sternschnuppe
```

## 5. Sprache

- **Deutsch, kurz, per Du.** Aus der Luftfahrt borgen, wo es trägt, aber nie auf Kosten der Klarheit. Der Betrag heißt „Betrag“.

| Situation | So | Nicht so |
|---|---|---|
| Aufforderung zum Scannen | „Scannen & einsteigen“, „Scannen & bezahlen“ | „Bitte QR-Code einlesen“ |
| Wartet | „Boarding jetzt“, „Wartet auf Scan“ | „Loading…“ |
| Erfolg | „Gelandet. 3 € sind angekommen.“ | „Transaktion erfolgreich“ |
| Fehler | „Diese Münze wurde schon ausgegeben.“ | „Error 400: double_spend“ |

- **Keine URLs, IDs oder Hex-Werte im UI.** Technisches bleibt im Code.

## 6. Bewegung

| Effekt | Wo | Dauer |
|---|---|---|
| `fm-arrive`: Ticket fliegt leicht gedreht ein | das Haupt-Papier eines Screens, einmal | 900 ms, `--fm-ease-arrive` |
| Sterne leuchten bei Mausnähe | Himmel (`sky.js`) | 0.5 s |
| Sternschnuppe | alle 2.5–7 s (`sky.js`) | ~1.2 s |
| Pixel-Funkeln | Feier-Momente | 0.9 s pro Funken |
| Puls am Status-Punkt | „läuft gerade“ | 1.6 s, endlos |
| Fallblatt im Log | neue Tabellenzeile, einmal | 0.6 s aufklappen, 2.6 s Amber-Leuchten |

Mehr nicht. Neue Effekte nur für echte Ereignisse, nie als Dauer-Deko.

## 7. Grenzen, die man kennen muss

- **Schriften kommen von Google Fonts.** Ohne Netz fällt die Seite auf Systemschriften zurück. Sie funktioniert, sieht aber schlichter aus. Für eine Wallet, die offline laufen soll, die drei Schriften selbst hosten und das `@import` oben in `flugmodus.css` durch eigene `@font-face`-Regeln ersetzen.
- **Nur fürs Web.** Die Klassen funktionieren in jeder Web-Oberfläche (reines HTML, React, Vue, PWA). Bei einer nativen App (Swift, Kotlin, Flutter) gelten die Tokens und Regeln aus dieser Datei, die Bausteine müssen dort nachgebaut werden.
- **Browser:** aktuelles Chrome, Safari und Firefox. Genutzt werden `mask-composite`, `color-mix()` und `paint-order`.
