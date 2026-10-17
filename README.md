# gratyPL

**gratyPL** to projekt społeczny dokumentujący porzucone i rozbierane samochody („graty”) w Gliwicach, Zabrzu i okolicach.

Nielegalne „warsztaty” i handlarze pozbywają się rozebranych aut, zostawiając je na parkingach, nieużytkach i w lasach. Pojedyncze zgłoszenia łatwo zbyć, ale zebrane razem, na mapie i w czasie, pokazują skalę problemu i wzorce, których nie da się zignorować. gratyPL zbiera fakty (miejsce, czas, zdjęcie, stan pojazdu) i przekazuje je właściwym służbom. Nie wskazuje winnych.

> **Status:** wersja demo (proof of concept). Pokazuje ideę i podstawowy przepływ danych. Nie jest przeznaczona do użytku produkcyjnego: nie ma kont użytkowników ani zabezpieczeń.

## Co potrafi demo

- **Zgłaszanie grata** ze zdjęciami i lokalizacją (wybór punktu na mapie, geolokalizacja przeglądarki albo GPS z EXIF zdjęcia).
- **Feed postów**: zgłoszenia i raporty tygodniowe w jednym strumieniu, w stylu mediów społecznościowych.
- **Mapa zgłoszeń** na podkładzie OpenStreetMap.
- **Usuwanie zgłoszeń** po potwierdzeniu.
- **Raporty tygodniowe** generowane ręcznie. Każdy raport jest samodzielną migawką danych z danego tygodnia.
- **Serwer MCP**, przez który agenci AI mogą przeglądać zgłoszenia i raporty oraz usuwać zgłoszenia.
- **Strona o projekcie** z krótkim wideo.

## Stack

| Warstwa | Technologia |
| --- | --- |
| Baza danych | PostgreSQL + PostGIS |
| Backend | Python, FastAPI, SQLAlchemy 2, GeoAlchemy2, Alembic, Pillow |
| Agenci AI | MCP (oficjalne SDK `mcp` 2.x, `MCPServer`) w tej samej aplikacji co API |
| Frontend | React + TypeScript (Vite), Leaflet + OpenStreetMap |
| Uruchamianie | Docker Compose |

Projekt nie korzysta z zewnętrznych usług poza kafelkami mapy OpenStreetMap.

## Architektura

```
React (SPA)  ──HTTP──►  FastAPI ─┐
Agent AI     ──MCP───►  MCP ─────┼──►  services/  ──►  PostgreSQL + PostGIS
                                  │                    + pliki zdjęć (MEDIA_ROOT)
```

Logika biznesowa znajduje się w jednej warstwie serwisowej, z której korzystają zarówno endpointy REST, jak i narzędzia MCP.

Najważniejsze konwencje:
- współrzędne w API zawsze w kolejności GeoJSON/PostGIS, `[lng, lat]`, SRID 4326,
- tygodnie raportów liczone od poniedziałku w strefie `Europe/Warsaw`,
- usuwanie zgłoszeń to soft delete, a raporty tygodniowe przechowują kopię danych, więc późniejsze usunięcie zgłoszenia ich nie zmienia.

Szczegółowa specyfikacja (model danych, endpointy, testy) jest w [`CLAUDE.md`](CLAUDE.md).

## Szybki start

Wymagania: Docker z Docker Compose.

```bash
git clone <adres-repozytorium> gratypl
cd gratypl
docker compose up -d --build   # migracje bazy uruchamiają się same przy starcie backendu

# dane demo (zgłoszenia z zastępczymi zdjęciami „DEMO” i raporty tygodniowe)
docker compose exec backend python -m scripts.seed
```

Seeder pomija tworzenie, jeśli dane demo już są. `--reset` usuwa poprzednie dane demo (tylko je, ręczne zgłoszenia
zostają) i tworzy je od nowa: `docker compose exec backend python -m scripts.seed --reset`.
Pełne wyczyszczenie bazy i zdjęć: `docker compose down -v`.

Po uruchomieniu (domyślne porty, do zmiany w `docker-compose.yml`):
- frontend: http://localhost:5173
- API i dokumentacja OpenAPI: http://localhost:8000/docs
- MCP: http://localhost:8000/mcp
- baza PostGIS z hosta: `localhost:5433` (użytkownik, hasło i baza: `gratypl`)

Kod frontendu jest zamontowany w kontenerze, więc zmiany przeładowują się na żywo.

> Geolokalizacja przeglądarki działa tylko na HTTPS lub `localhost`. Przy testach z telefonu w sieci lokalnej wybieraj punkt na mapie.

## API w skrócie

| Metoda | Ścieżka | Opis |
| --- | --- | --- |
| `POST` | `/api/reports` | nowe zgłoszenie (multipart: zdjęcia, współrzędne, opis) |
| `GET` | `/api/reports/{id}` | jedno zgłoszenie |
| `DELETE` | `/api/reports/{id}` | usunięcie zgłoszenia |
| `GET` | `/api/reports/geojson?bbox=…` | zgłoszenia w obszarze mapy jako GeoJSON |
| `GET` | `/api/feed` | strumień postów (zgłoszenia + raporty), paginacja kursorowa |
| `GET` | `/api/summaries/{week_start}` | raport tygodniowy |
| `POST` | `/api/summaries/generate?week_start=…` | ręczne wygenerowanie raportu |

## Narzędzia MCP

`list_feed`, `get_report`, `get_reports_in_area`, `get_weekly_summary`, `delete_report`.

W demo zgłoszenia dodaje się wyłącznie przez frontend.

Podłączenie agenta, np. w Claude Code:

```bash
claude mcp add --transport http gratypl http://localhost:8000/mcp
```

Serwer przyjmuje połączenia tylko z `localhost` (ochrona przed DNS rebinding w SDK MCP).

## Struktura repozytorium

```
backend/    FastAPI, serwisy, MCP, migracje, seeder, testy
frontend/   aplikacja React, wideo o projekcie w public/
docker-compose.yml
CLAUDE.md   specyfikacja projektu
```

## Testy

Backend (testy działają na prawdziwej bazie PostGIS w osobnym kontenerze `db-test`):

```bash
docker compose --profile test up -d db-test
docker compose --profile test run --rm backend pytest
# albo lokalnie: cd backend && uv run pytest
```

Frontend:

```bash
cd frontend && npm install && npx vitest run && npm run build
```

## Planowane w pełnej wersji

Demo celowo pomija wiele elementów. W pełnej wersji planujemy:

**Użytkownicy i bezpieczeństwo**
- konta użytkowników, role (zgłaszający, moderator, administrator) i uprawnienia do usuwania,
- uwierzytelnianie API i MCP, ochrona przed spamem i nadużyciami (limity zgłoszeń, walidacja treści),
- dwuetapowe usuwanie przez agentów AI (podgląd i potwierdzenie) oraz traktowanie treści zgłoszeń jako danych, a nie poleceń.

**Moderacja i jakość danych**
- statusy zgłoszeń (oczekujące, zatwierdzone, odrzucone) i kolejka moderacji,
- automatyczne odrzucanie zgłoszeń bez zdjęcia lub lokalizacji,
- wykrywanie duplikatów tego samego wraku (podobieństwo zdjęć + odległość geograficzna).

**Prywatność**
- automatyczne rozmywanie tablic rejestracyjnych i twarzy przed publikacją,
- minimalny zakres przechowywanych danych zgodnie z RODO.

**Analiza**
- wykrywanie skupisk zgłoszeń (np. DBSCAN) i mapa ciepła,
- rozkład zgłoszeń w czasie (dni tygodnia, godziny),
- śledzenie stanu tego samego wraku w kolejnych zgłoszeniach (przyjechał rozebrany czy jest rozbierany na miejscu).

**Raporty i kontakt ze służbami**
- automatyczne generowanie raportów tygodniowych według harmonogramu,
- gotowy tekst podsumowania i obraz mapy do publikacji w grupie na Facebooku,
- wskazywanie właściwego organu dla zgłoszenia (straż miejska, gmina, WIOŚ, zarządca terenu, policja),
- zestawienia dla służb i śledzenie statusu odpowiedzi.

**Zgłaszanie**
- dodawanie zgłoszeń przez MCP i ewentualnie inne kanały,
- wygodniejsza wersja mobilna.

## Wkład i kontakt

Projekt jest na wczesnym etapie. Pomysły i uwagi mile widziane w zgłoszeniach (issues) repozytorium.
