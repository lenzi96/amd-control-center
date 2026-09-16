# AMD Software: Adrenalin Edition for Linux
### Modernes AMD Radeon Control Center mit Adrenalin Look & Feel

Ein leistungsstarkes und optisch an die offizielle **AMD Software: Adrenalin Edition** (Radeon Software) angelehntes Kontrollzentrum für Linux. Entwickelt mit **PyQt6** und nativer Anbindung an den Linux-Kernel (`amdgpu` Sysfs & HWMON).

---

## 🌟 Hauptfunktionen

### 1. 🏠 Startseite (Home)
- **Zuletzt gespielt / Top-Spiel:** Automatische Erkennung des zuletzt aktiven Steam-Spiels (z. B. Cyberpunk 2077) mit originalen Cover-Artworks aus dem lokalen Steam-Cache.
- **Direktstart:** Starten von Spielen direkt mit den vorkonfigurierten Radeon-Grafikprofilen.
- **Schnellschalter:** Direkter Zugriff auf Radeon Anti-Lag, Radeon Super Resolution (FSR), Radeon Boost (VRS) und MangoHud.
- **Treiber- & Softwarestatus:** Erkennung von Mesa, RADV ACO, Vulkan 1.4 und Kernel mit "Auf dem neuesten Stand"-Status.
- **Live-Telemetrie-Snapshot:** Schnellübersicht über Temperatur, Hotspot, GPU-Auslastung, VRAM-Belegung und Taktfrequenz.

### 2. 🎮 Gaming (Spiele & Profile)
- **Multi-Drive Steam-Erkennung:** Findet automatisch alle installierten Steam-Spiele über beliebig viele Festplatten und Bibliotheken (`libraryfolders.vdf`).
- **Suchfunktion:** Blitzschnelle Filterung in Echtzeit nach Spieletiteln.
- **Detaillierte Spieleprofile:**
  - **Radeon Anti-Lag:** Minimiert Eingabeverzögerungen über den Mesa Vulkan WSI Mailbox-Modus.
  - **Radeon Super Resolution (RSR / FSR):** Upscaling und Schärfegrad-Regler.
  - **Radeon Boost / Dynamic VRS:** Variable Rate Shading (2x2) für maximale Frameraten bei schnellen Bewegungen.
  - **MangoHud Integration:** Hardware-Telemetrie direkt im Spiel.
  - **Gamescope Wrapper:** Start von Spielen in einem isolierten Wayland Micro-Compositor.
  - **DPM Power Profile Mode:** Automatisches Umschalten auf `3D_FULL_SCREEN` während des Spielens.

### 3. ⚡ Leistung (Performance: Metriken & Tuning)
- **Metriken (Metrics):**
  - 6 große Adrenalin-Metrikkacheln: GPU-Auslastung, Core-Takt, Edge- und Junction/Hotspot-Temperatur, VRAM-Nutzung, Board-Leistungsaufnahme (Watt) und Lüfterdrehzahl (RPM).
  - **Echtzeit-Graph:** Hochperformante Multi-Kurven-Grafik (Custom QPainter) mit Radeon-Red Glow-Effekt und umschaltbaren Datenreihen.
  - Konfigurierbare Abtastrate (0.5s, 1.0s, 2.0s).
  - **Floating HUD Overlay:** Kompaktes, transluzentes und verschiebbares Performance-Overlay ("Always on Top").
- **Tuning (Overclocking & Undervolting):**
  - Adrenalin-Sicherheitshinweis mit Freischaltungs-Schalter.
  - **GPU-Tuning:** Takt-Offset Slider (-500 bis +1000 MHz), Undervolting Slider (-200 bis 0 mV).
  - **VRAM-Tuning:** Speichertakt-Regler (97 bis 1500 MHz).
  - **Lüftersteuerung:** Zero-RPM Modus (Lüfterstopp im Leerlauf), manuelle Drehzahl oder **interaktiver 5-Punkte-Lüfterkurven-Editor**.
  - **Power Limit (PPT):** Anpassung der Board-Leistungsgrenze (z. B. 231W bis 374W).
  - Sichere Anwendung über `pkexec` oder udev-Regeln.

### 4. ⚙️ Einstellungen (Settings)
- **Systeminfo:** Detaillierte Übersicht über GPU-Modell, Device ID, VBIOS-Version, VRAM-Hersteller (Samsung GDDR6), PCIe-Link-Geschwindigkeit (Gen 4/5 x16) und Software-Stack.
- **Anzeige:** Monitor-Erkennung (DP-1, 3840x2160 @ 144Hz), FreeSync / Adaptive Sync Status und HDR.
- **Optionen:** Autostart, System-Tray Minimierung, 1-Klick udev-Regel für passwortloses Tuning.

---

## 🚀 Installation & Start

### Schnellstart (ohne Installation)
```bash
cd /run/media/julian/HDD/Linux/amd-control-center
./main.py
```

### Systemweite Benutzerinstallation
```bash
cd /run/media/julian/HDD/Linux/amd-control-center
./install.sh
```
Danach steht der Befehl `amd-control-center` im Terminal bereit und das Control Center erscheint im Anwendungsmenü ("AMD Software: Adrenalin Edition").

---

## 🛡️ Berechtigungen (Tuning ohne Passwort)
Um Overclocking- und Lüftereinstellungen ohne Root-Passwortabfrage anwenden zu können, kann in den **Einstellungen → Optionen** mit einem Klick die passende udev-Regel installiert werden:
```bash
/etc/udev/rules.d/99-amdgpu-tuning.rules
```
