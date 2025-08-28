# 📊 Server Dashboard

Ein leichtgewichtiges, Flask-basiertes Dashboard zur Überwachung eines Home- oder Root-Servers.  
Zeigt Systemressourcen, Netzwerk, Dienste, Docker-Container, Prozesse und Logs an – alles in einer sauberen Weboberfläche.  

## ✨ Features

- **Systeminfos**: Hostname, OS, Uptime, aktuelle Uhrzeit
- **Ressourcen**: CPU-Last, RAM, Swap, CPU-Temperatur
- **Charts**: Historische CPU- & RAM-Auslastung (Chart.js)
- **Netzwerk**: Up/Downspeed, gesendete & empfangene Daten
- **Datenträger**: Übersicht über Mounts, Belegung und Prozente
- **Dienste**: Status beliebiger systemd-Services (`config.toml`)
- **Docker**: Laufende Container & Status
- **Top-Prozesse**: CPU/RAM-intensive Prozesse
- **Logs**: Letzte Einträge aus `/var/log/syslog` oder `/var/log/messages`
- **🔎 LAN-Scanner**: Integrierter Port- & Hostscanner (läuft auf Port `5051`, eingebettet als iFrame)
- **☀️ Wetter-Widget**: Zeigt aktuelle Temperatur und Wetterlage am Server-Standort (oben rechts)

## 🚀 Installation

1. Repository klonen:
   ```bash
   git clone https://github.com/laurinhuebner/server-dashboard.git
   cd server-dashboard
