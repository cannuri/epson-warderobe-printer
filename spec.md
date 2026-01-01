# Garderoben-Ticketsystem Spezifikation

## Übersicht

Ein automatisches Garderoben-Ticketsystem für Veranstaltungen im FUNKHAUS. Das System druckt nummerierte Garderobenmarken auf Knopfdruck (Fußpedal) und läuft vollständig autonom auf einem Raspberry Pi 4.

---

## Hardware

| Komponente | Details |
|------------|---------|
| Computer | Raspberry Pi 4 |
| IP-Adresse | 172.20.10.2 |
| Benutzername | pi |
| Drucker | Epson TM-T88V (USB-Anschluss) |
| Auslöser | USB-Fußpedal |

### SSH-Zugang

```bash
ssh pi@172.20.10.2
```

---

## Software

| Komponente | Details |
|------------|---------|
| Betriebssystem | Raspberry Pi OS mit Desktop |
| Programmiersprache | Python (empfohlen) |
| Ausführung | Hintergrund-Dienst (systemd) |

---

## Funktionsweise

### Druck-Logik

1. Erster Fußpedal-Druck → Druckt Nummer (z.B. 500)
2. Zweiter Fußpedal-Druck → Druckt gleiche Nummer (500)
3. Dritter Fußpedal-Druck → Druckt nächste Nummer (501)
4. Vierter Fußpedal-Druck → Druckt gleiche Nummer (501)
5. usw.

**Jede Nummer wird exakt zweimal gedruckt**, dann wird zur nächsten Nummer gewechselt.

### Nummerierung

- **Startnummer:** 500
- **Verhalten:** Fortlaufend inkrementell (kein automatischer Reset)
- **Persistenz:** Aktuelle Nummer wird gespeichert und nach Neustart fortgesetzt

---

## Ticket-Layout

```
┌─────────────────────────┐
│                         │
│        FUNKHAUS         │  ← Überschrift
│                         │
│    01.01.2025  20:15    │  ← Datum/Uhrzeit (klein)
│                         │
│          500            │  ← Nummer (groß, fett)
│                         │
└─────────────────────────┘
```

- **FUNKHAUS:** Überschrift, zentriert
- **Datum/Uhrzeit:** Klein, zentriert
- **Nummer:** Groß und fett, gut lesbar, zentriert
- **Ausrichtung:** Alles zentriert

---

## Papierschnitt

Nach jedem Ticket-Druck erfolgt ein automatischer Schnitt:

- **Teilschnitt (Standard):** Ticket hängt noch, leichtes Abreißen möglich
- **Vollschnitt (optional):** Ticket fällt komplett ab

Der Schnittmodus ist über die Konfigurationsdatei einstellbar.

---

## Konfigurationsdatei

Eine einfache Konfigurationsdatei ermöglicht folgende Einstellungen:

```ini
# Beispiel: /home/pi/garderobe/config.ini

[general]
# Aktuelle Ticketnummer (kann manuell angepasst werden)
current_number = 500

# Schnittmodus: "partial" (Teilschnitt) oder "full" (Vollschnitt)
cut_mode = partial
```

### Anpassbare Parameter

| Parameter | Beschreibung | Standardwert |
|-----------|--------------|--------------|
| `current_number` | Aktuelle/nächste Ticketnummer | 500 |
| `cut_mode` | Schnittmodus (`partial` / `full`) | `partial` |

---

## Fehlerbehandlung

### Bei Fehlern (z.B. kein Papier, USB-Verbindung unterbrochen):

1. Fußpedal-Eingaben werden ignoriert
2. Fehler wird in Log-Datei geschrieben (`/home/pi/garderobe/error.log`)
3. System wartet auf Fehlerbehebung
4. Nach Behebung funktioniert das System automatisch wieder

### Log-Format

```
[2025-01-01 20:15:30] ERROR: Drucker nicht erreichbar - USB-Verbindung prüfen
[2025-01-01 20:16:45] INFO: Drucker wieder verbunden
```

---

## Autostart

### Systemd-Dienst

Das System startet automatisch als Hintergrund-Dienst beim Hochfahren des Raspberry Pi:

- **Dienstname:** `garderobe.service`
- **Startverhalten:** Automatisch nach Boot
- **Ausführung:** Unsichtbar im Hintergrund (kein Desktop-Fenster)

### Befehle zur Verwaltung

```bash
# Status prüfen
sudo systemctl status garderobe

# Dienst stoppen
sudo systemctl stop garderobe

# Dienst starten
sudo systemctl start garderobe

# Dienst neustarten
sudo systemctl restart garderobe
```

---

## Dateistruktur

```
/home/pi/garderobe/
├── garderobe.py          # Hauptprogramm
├── config.ini            # Konfigurationsdatei
├── state.json            # Persistente Speicherung (aktuelle Nummer, Druck-Zähler)
└── error.log             # Fehler-Log
```

---

## Zusammenfassung

| Anforderung | Umsetzung |
|-------------|-----------|
| Drucker | Epson TM-T88V via USB |
| Auslöser | USB-Fußpedal |
| Plattform | Raspberry Pi 4, Raspberry Pi OS mit Desktop |
| Druck pro Nummer | 2x (zwei Tickets pro Nummer) |
| Startnummer | 500 |
| Persistenz | Ja, Nummer bleibt nach Neustart erhalten |
| Schnittmodus | Konfigurierbar (Teil-/Vollschnitt) |
| Autostart | Ja, als systemd-Hintergrund-Dienst |
| Feedback | Keins (Druckvorgang ist Bestätigung) |
| Fehlerbehandlung | Logging + Eingaben ignorieren |
