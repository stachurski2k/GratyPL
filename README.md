# gratyPL (demo)

Projekt społeczny dokumentujący porzucone i rozbierane samochody („graty”) w Gliwicach, Zabrzu i okolicach.
Mieszkańcy zgłaszają wraki (zdjęcie + lokalizacja), zgłoszenia trafiają na mapę i do listy postów,
a raz w tygodniu powstaje raport podsumowujący.

To jest **wersja demonstracyjna (proof of concept)**: pokazuje ideę, nie jest gotowym produktem.
Nie ma kont użytkowników, logowania ani zabezpieczeń, więc nie wystawiaj jej publicznie w tej postaci.

## Co potrafi

- dodawanie zgłoszenia ze zdjęciami (1–5), z punktem wybranym na mapie, z geolokalizacji przeglądarki
  albo z danych GPS zapisanych w zdjęciu (EXIF),
- strumień postów: zgłoszenia i raporty tygodniowe w jednym feedzie,
- mapa wszystkich zgłoszeń (OpenStreetMap) z podglądem po kliknięciu,
- usuwanie zgłoszeń po potwierdzeniu,
- ręczne generowanie raportu za wybrany tydzień (poniedziałek–niedziela, czas polski),
- serwer MCP, przez który agent AI może czytać zgłoszenia i raporty oraz usuwać zgłoszenia.

## Uruchomienie

Wymagany jest Docker z Docker Compose.

```bash
docker compose up -d --build
docker compose exec backend python -m scripts.seed
```

Potem otwórz:

| Adres | Co to jest |
| --- | --- |
| http://localhost:5173 | aplikacja (frontend) |
| http://localhost:8000/docs | dokumentacja REST API |
| http://localhost:8000/mcp | serwer MCP dla agentów AI |

Baza PostgreSQL + PostGIS jest dostępna z hosta na porcie `5433` (użytkownik, hasło i baza: `gratypl`).
Migracje uruchamiają się same przy starcie backendu.

### Dane demo

Seeder tworzy ok. 15 przykładowych zgłoszeń w Gliwicach i Zabrzu z ostatnich trzech tygodni oraz raporty
tygodniowe dla tych tygodni. Zdjęcia to wygenerowane obrazki z napisem „DEMO”, a w interfejsie zgłoszenia
są oznaczone jako „Dane przykładowe”.

```bash
docker compose exec backend python -m scripts.seed           # pomija, jeśli dane demo już są
docker compose exec backend python -m scripts.seed --reset   # usuwa dane demo i tworzy je od nowa
```

`--reset` usuwa tylko dane demo; zgłoszenia dodane ręcznie zostają.

Żeby wyczyścić wszystko (bazę i zdjęcia): `docker compose down -v`.

## Agent AI przez MCP

Serwer MCP udostępnia narzędzia: `list_feed`, `get_report`, `get_reports_in_area`, `get_weekly_summary`
i `delete_report`. Dodawania zgłoszeń przez MCP celowo nie ma.

Przykład dla Claude Code:

```bash
claude mcp add --transport http gratypl http://localhost:8000/mcp
```

Serwer przyjmuje połączenia tylko z `localhost` (ochrona przed DNS rebinding z SDK MCP).

## Rozwój i testy

Stos: PostgreSQL + PostGIS, Python (FastAPI, SQLAlchemy 2, GeoAlchemy2, Alembic, Pillow, SDK `mcp`),
React + TypeScript (Vite, Leaflet). Kod frontendu jest zamontowany w kontenerze, więc zmiany przeładowują się
na żywo.

Testy backendu działają na prawdziwej bazie PostGIS (osobny kontener `db-test`):

```bash
docker compose --profile test up -d db-test
cd backend && uv run pytest
# albo w kontenerze:
docker compose --profile test run --rm backend pytest
```

Frontend:

```bash
cd frontend
npm install
npx vitest run
npm run build
```

Konwencje projektu (format współrzędnych `[lng, lat]`, strefa czasowa raportów, soft delete itd.)
są opisane w [`CLAUDE.md`](CLAUDE.md).

## Mapy

Mapy korzystają z kafelków © [OpenStreetMap](https://www.openstreetmap.org/copyright) contributors,
zgodnie z [zasadami użycia kafelków OSM](https://operations.osmfoundation.org/policies/tiles/).
