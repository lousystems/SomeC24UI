# Check24 Weather Application

Dieses Projekt besteht aus einem **Vue.js Frontend** und einem **Python/Django Backend** für historische Wetterdaten. Es wurde vollständig mit Docker (Docker Compose) containerisiert und beinhaltet eine automatisierte GitHub Actions CI-Pipeline.

## 📂 Projektstruktur
- `Frontend/`: Beinhaltet die Vue.js Applikation (gebaut mit Vite, TailwindCSS, und Chart.js).
- `Backend/`: Beinhaltet die Django REST Framework API, die Wetterdaten verwaltet und abruft.
- `docker-compose.yml`: Orchestriert das Frontend, Backend sowie die PostgreSQL Datenbank.
- `.env`: Beinhaltet die sicheren Zugangsdaten und Keys (aus Sicherheitsgründen nicht in Git versioniert).
- `.github/workflows/ci.yml`: GitHub Actions Pipeline für automatisches Testen und Validieren.

## 🚀 Voraussetzungen
- [Docker](https://www.docker.com/) & Docker Compose auf deinem Rechner installiert.

## 🛠 Lokale Installation & Start

### 1. Umgebungsvariablen einrichten
Da Passwörter nicht im Code stehen sollten, nutzt das Projekt eine `.env` Datei. 
Kopiere einfach die Vorlage:
```bash
cp .env.example .env
```
*(Optional: Du kannst die Werte in der neuen `.env` Datei noch anpassen, wenn du ein eigenes Passwort für die Datenbank setzen möchtest).*

### 2. Projekt mit Docker starten
Baue und starte alle benötigten Container (Datenbank, Backend, Frontend) mit einem einzigen Befehl:
```bash
docker-compose up --build -d
```
Docker lädt nun alle Abhängigkeiten herunter, baut die Images und startet die Dienste.

### 3. Applikation aufrufen
Sobald die Container laufen, kannst du die Anwendung im Browser öffnen:
- **Web-Interface (Frontend):** [http://localhost](http://localhost)
- **Backend API:** [http://localhost:8000/api/](http://localhost:8000/api/)
- **API Swagger/OpenAPI Dokumentation:** [http://localhost:8000/api/schema/swagger-ui/](http://localhost:8000/api/schema/swagger-ui/)

### 4. Herunterfahren
Um alle Server wieder zu stoppen, nutze:
```bash
docker-compose down
```
*Tipp: Möchtest du die Datenbank unwiderruflich löschen und komplett neu aufsetzen, ergänze das Flag `-v` (`docker-compose down -v`).*

## 🤖 CI/CD Pipeline (GitHub Actions)
Sobald du den Code auf GitHub pusht, startet automatisch die CI-Pipeline. Sie stellt Folgendes sicher:
1. **Backend Tests**: Führt alle Django Unit-Tests in einer sauberen Umgebung aus.
2. **Frontend Build**: Überprüft, ob sich die Vue.js Anwendung fehlerfrei kompilieren lässt.
3. **Integration & Health**: Fährt das gesamte Projekt testweise in Docker hoch und pingt die Healthcheck-Endpoints an, um sicherzustellen, dass keine Container abstürzen.

## 📖 Weitere Dokumentationen
Für tiefere technische Einblicke in die beiden Kernkomponenten lies bitte die separaten READMEs:
- [Backend Dokumentation](./Backend/README.md)
- [Frontend Dokumentation](./Frontend/README.md)
