# gratyPL — demo (proof of concept)

gratyPL to projekt społeczny dokumentujący porzucone i rozbierane samochody („graty”) w Gliwicach, Zabrzu i okolicach. Mieszkańcy zgłaszają wraki (zdjęcie + lokalizacja), zgłoszenia trafiają na mapę i do listy postów, a raz w tygodniu powstaje raport podsumowujący.

To repozytorium to **wersja demo**: działający PoC pokazujący ideę, a nie produkt.

**Stan (2026-10-17):** wszystkie etapy 1–6 zrealizowane. Instrukcja uruchomienia dla ludzi jest w `README.md`.

## Zakres

**W demo:**
- dodawanie zgłoszenia (tylko przez frontend),
- lista postów: zgłoszenia + raporty tygodniowe w jednym strumieniu, w stylu feedu z mediów społecznościowych,
- mapa zgłoszeń,
- usuwanie zgłoszeń po potwierdzeniu w oknie dialogowym,
- ręczne generowanie raportu tygodniowego,
- serwer MCP dla agentów AI (odczyt + usuwanie),
- strona główna przedstawiająca ideę projektu, z wideo.

**Poza zakresem (nie implementować):**
- konta użytkowników, logowanie, role, uprawnienia,
- zabezpieczenia (auth, rate limiting, CSRF itp.),
- weryfikacja i moderacja zgłoszeń,
- analiza danych (klastrowanie, deduplikacja, rozmywanie tablic i twarzy),
- automatyczne (harmonogramowane) generowanie raportów,
- publikowanie wyników postępowań i integracje z Facebookiem,
- dodawanie zgłoszeń przez MCP.

## Stack

- **Baza:** PostgreSQL + PostGIS (obraz `postgis/postgis`)
- **Backend:** Python, FastAPI, SQLAlchemy 2 + GeoAlchemy2, Alembic, Pillow (EXIF, miniatury)
- **MCP:** oficjalne SDK `mcp` 2.x (`MCPServer` z `mcp.server.mcpserver`; w 2.x tak nazywa się dawny FastMCP), zamontowane w tej samej aplikacji FastAPI (streamable HTTP, tryb bezstanowy)
- **Frontend:** React + TypeScript (Vite), Leaflet z kafelkami OpenStreetMap
- **Uruchamianie:** `docker-compose` (db, backend, frontend)

Zasada: żadnych zewnętrznych usług poza kafelkami OSM. Biblioteki są w porządku. Kafelki OSM wymagają widocznej atrybucji „© OpenStreetMap contributors” i przestrzegania ich zasad użycia.

## Kolejność prac

**Backend first.** Najpierw działający i przetestowany backend, potem frontend.

1. ✅ `docker-compose` z PostGIS, szkielet FastAPI, Alembic, pierwsza migracja.
2. ✅ Warstwa serwisowa + REST dla zgłoszeń (tworzenie, feed, GeoJSON, usuwanie) + testy.
3. ✅ Raporty tygodniowe (generowanie ręczne) + testy.
4. ✅ Serwer MCP na bazie tej samej warstwy serwisowej.
5. ✅ Skrypt seedujący dane demo.
6. ✅ Frontend.

Tryb pracy: po każdym etapie lub większej zmianie zatrzymać się i dać właścicielowi do przeglądu; commit (i push) dopiero po akceptacji.

## Architektura

```
React (SPA)  ──HTTP──►  FastAPI routers ─┐
Agent AI     ──MCP───►  MCP tools ───────┼──►  services/  ──►  PostgreSQL + PostGIS
                                          │                    + MEDIA_ROOT (pliki)
```

- Cała logika biznesowa siedzi w `services/`. Routery REST i narzędzia MCP są cienkie i wołają te same funkcje serwisowe. Nigdy nie duplikujemy logiki między REST a MCP.
- MCP nie odpytuje REST przez HTTP, tylko woła serwisy bezpośrednio.

- Serwisy zgłaszają błędy wyjątkami z `services/errors.py` (`InvalidInput` → 422, `NotFound` → 404, `Conflict` → 409). REST mapuje je w `main.py`, MCP zamienia na `ToolError` z tym samym komunikatem.
- Serwisy zwracają obiekty ORM; serializacja (dla REST i MCP) jest w `schemas.py` (`ReportOut.from_model`, `SummaryOut.from_model`, `feature_collection`, `feed_item`).

Struktura:

```
backend/
  app/
    main.py            # FastAPI, routery, obsługa błędów, /media, MCP pod /mcp
    config.py          # ustawienia z env (DATABASE_URL, MEDIA_ROOT, CORS_ORIGINS) + strefa WARSAW
    db.py
    models.py          # Report.lng/lat to column_property liczone przez PostGIS
    schemas.py         # Pydantic: jedyne miejsce definicji formatu współrzędnych (Point, BBox)
    services/
      errors.py
      reports.py
      summaries.py
      feed.py
      media.py         # walidacja i zapis zdjęć, miniatury, odczyt EXIF
    api/
      reports.py
      feed.py
      summaries.py
    mcp_server.py
  alembic/             # migracje pisane ręcznie (0001_initial)
  scripts/
    seed.py            # python -m scripts.seed [--reset]
    demo_images.py     # obrazki DEMO i EXIF (używane też w testach)
  tests/
frontend/
  public/gratypl.mp4   # wideo o projekcie
  src/
    geo.ts             # jedyna konwersja [lng, lat] <-> [lat, lng]
    api.ts             # klient REST
    types.ts
    format.ts          # daty i tygodnie w Europe/Warsaw
    components/        # posty, galeria, okno potwierdzenia, mapy, kafelki OSM
    pages/             # HomePage, FeedPage, MapPage, NewReportPage
docker-compose.yml
```

## Konwencje (ważne)

- **Współrzędne: backend jest źródłem prawdy.** API przyjmuje i zwraca współrzędne wyłącznie w konwencji GeoJSON/PostGIS: `[lng, lat]`, SRID 4326. Frontend konwertuje do `[lat, lng]` Leafleta **w jednym helperze** (np. `src/geo.ts`) i nigdzie indziej. Test backendu sprawdza, że punkt w Gliwicach (ok. lng 18.67, lat 50.29) wraca jako `[18.67, 50.29]`.
- **Czas:** w bazie `timestamptz` (UTC). Tygodnie raportów liczone w strefie `Europe/Warsaw`, od poniedziałku 00:00 do następnego poniedziałku 00:00.
- **Usuwanie zgłoszeń to soft delete** (`deleted_at`). Usunięte zgłoszenia nie pojawiają się w feedzie, na mapie ani w nowych raportach. `DELETE` jest idempotentny (ponowne usunięcie zwraca 204).
- **Raporty tygodniowe są self-contained**: kopiują potrzebne dane w momencie generowania, bez relacji do tabeli zgłoszeń. Późniejsze usunięcie zgłoszenia nie zmienia raportu.

## Model danych

**`reports`**
- `id uuid PK`
- `created_at timestamptz`
- `location geography(Point, 4326) NOT NULL` + indeks GiST
- `description text NULL`
- `has_plates boolean NULL` (nieznane = NULL)
- `source text` — `'web'` albo `'seed'` (dane demo)
- `deleted_at timestamptz NULL`

**`report_photos`**
- `id uuid PK`, `report_id uuid FK → reports`
- `path text`, `thumb_path text` (względem `MEDIA_ROOT`)
- `taken_at timestamptz NULL` (z EXIF)
- `position int` (kolejność)

**`weekly_summaries`**
- `id uuid PK`
- `week_start date UNIQUE` (poniedziałek, czas warszawski)
- `generated_at timestamptz`
- `report_count int`
- `bbox jsonb NULL` (`[minLng, minLat, maxLng, maxLat]`)
- `snapshot jsonb` — lista zgłoszeń z tygodnia, każde: `id`, `created_at`, `location [lng, lat]`, `description`, `has_plates`, `thumbs` (ścieżki do **skopiowanych** miniatur)

Miniatury do raportu są kopiowane do `MEDIA_ROOT/summaries/{week_start}/{summary_id}/`, żeby raport działał także po usunięciu zgłoszenia. Osobny katalog na wersję raportu sprawia, że przy `force` stare pliki znikają dopiero po zapisaniu nowej wersji w bazie. `week_start` musi być poniedziałkiem; tygodnia, który się jeszcze nie zaczął, nie da się wygenerować (422).

## Zdjęcia

- 1–5 zdjęć na zgłoszenie, formaty JPEG/PNG/WebP, maks. 10 MB każde.
- Zapis: `MEDIA_ROOT/reports/{report_id}/`. Miniatura o dłuższym boku 480 px.
- Pliki serwowane statycznie pod `/media/...`.
- Zdjęć nie trzymamy w bazie (`bytea`), tylko ścieżki.

## Lokalizacja zgłoszenia

Lokalizacja jest wymagana. Kolejność źródeł:
1. współrzędne z formularza (kliknięcie na mapie albo geolokalizacja przeglądarki),
2. jeśli brak: GPS z EXIF pierwszego zdjęcia, które go ma,
3. jeśli brak obu: `422` z czytelnym komunikatem.

Uwaga: geolokalizacja przeglądarki działa tylko na HTTPS lub `localhost`, dlatego wybór punktu na mapie musi być zawsze dostępny.

## REST API

| Metoda | Ścieżka | Opis |
| --- | --- | --- |
| `POST` | `/api/reports` | multipart: `photos[]`, opcjonalnie `lng`, `lat`, `description`, `has_plates` → 201 + zgłoszenie |
| `GET` | `/api/reports/{id}` | jedno zgłoszenie (404 dla usuniętego) |
| `DELETE` | `/api/reports/{id}` | soft delete → 204 |
| `GET` | `/api/reports/geojson?bbox=minLng,minLat,maxLng,maxLat` | `FeatureCollection` aktywnych zgłoszeń w obszarze (`&&` + `ST_MakeEnvelope`) |
| `GET` | `/api/feed?cursor=&limit=` | strumień postów, patrz niżej |
| `GET` | `/api/summaries/{week_start}` | jeden raport |
| `POST` | `/api/summaries/generate?week_start=YYYY-MM-DD&force=false` | generuje raport; `409`, jeśli istnieje, chyba że `force=true` (wtedy zastępuje) |

Szczegóły:
- Pole uploadu nazywa się `photos` i powtarza się dla każdego pliku (`formData.append('photos', file)`).
- `DELETE` zwraca 204 dla istniejącego zgłoszenia (także już usuniętego), 404 dla id, którego nigdy nie było.
- Odpowiedź raportu zawiera `week_end` (wyłączny, następny poniedziałek) i `reports[]` ze snapshotu, gdzie miniatury są już adresami (`thumb_urls`, `/media/...`).
- Czas z EXIF bez strefy traktujemy jako czas polski. Współrzędne z EXIF zaokrąglamy do 7 miejsc po przecinku.
- Opis do 2000 znaków; GeoJSON zwraca maks. 1000 punktów.

**Feed:** jeden strumień z dwoma typami elementów, `{"type": "report", ...}` i `{"type": "summary", ...}`, posortowany malejąco po czasie (`created_at` dla zgłoszeń, `generated_at` dla raportów). Paginacja kursorowa (kursor = czas + id), bez `OFFSET`.

## MCP

Narzędzia, każde wołające `services/`:
- `list_feed(limit, cursor)`
- `get_report(id)`
- `get_reports_in_area(min_lng, min_lat, max_lng, max_lat)`
- `get_weekly_summary(week_start)`
- `delete_report(id)`

Brak `create_report`: w PoC zgłoszenia dodaje się wyłącznie przez frontend, bo przesyłanie zdjęć przez argumenty narzędzi MCP jest niepraktyczne.

Endpoint: `http://localhost:8000/mcp`. SDK ma włączoną ochronę przed DNS rebinding, więc akceptuje tylko nagłówek `Host` z localhost (w testach HTTP trzeba go ustawić). Testy narzędzi używają klienta in-process `mcp.Client(mcp)`; jednego klienta nie da się otworzyć dwa razy.

## Frontend

- **Strona główna / o projekcie:** krótki opis problemu i idei + wideo z `public/gratypl.mp4`.
- **Feed:** posty jak w mediach społecznościowych. Zgłoszenie: miniatury, data, opis, mała mapka lub link do punktu na mapie, przycisk usuwania. Raport tygodniowy: tytuł z zakresem dat, liczba zgłoszeń, mapa z punktami ze `snapshot`, galeria miniatur.
- **Mapa:** wszystkie aktywne zgłoszenia, ładowane po `bbox` widoku; kliknięcie w pinezkę pokazuje podgląd zgłoszenia.
- **Dodawanie zgłoszenia:** zdjęcia, wybór punktu na mapie (z opcją „użyj mojej lokalizacji”), opis, pytanie o tablice.
- **Usuwanie:** zawsze przez okno potwierdzenia.
- **Generowanie raportu:** przycisk z wyborem tygodnia (demo, ręcznie).
- Interfejs po polsku.

Szczegóły implementacji:
- Mini-mapa tylko w raportach tygodniowych; zgłoszenie w feedzie ma link „Pokaż na mapie” (`/mapa?zgloszenie=<id>`), żeby nie obciążać kafelków OSM.
- Pinezki to `CircleMarker` (bez domyślnych ikon Leafleta); dane demo w innym kolorze.
- Vite (dev server) przekazuje `/api` i `/media` do backendu (`BACKEND_URL`), więc CORS nie jest potrzebny.
- Leaflet nie działa w Node, więc testy `vitest` nie importują go w czasie wykonania (tylko typy).

## Dane demo

`scripts/seed.py` tworzy ok. 15 zgłoszeń w okolicach Gliwic i Zabrza (`source = 'seed'`, kilka skupionych blisko siebie) rozłożonych na 2–3 tygodnie, oraz generuje raporty tygodniowe dla tych tygodni. Dane demo są wyraźnie oznaczone jako przykładowe, także w interfejsie.

**Zdjęcia w seederze:** seeder generuje zastępcze obrazki w Pillow, bez pobierania czegokolwiek z sieci:
- 1–3 obrazki na zgłoszenie, JPEG, np. 1280×960,
- prosta sylwetka auta (np. bez kół) na jednolitym tle, z lekką losową wariacją koloru i położenia (deterministycznie, ze stałym ziarnem),
- wyraźny napis „DEMO” i numer zgłoszenia na obrazku, żeby nikt nie pomylił go z prawdziwym zdjęciem,
- współrzędne GPS zgłoszenia zapisane w EXIF części obrazków; te zgłoszenia seeder tworzy **bez** współrzędnych w formularzu, żeby przy okazji przetestować ścieżkę „lokalizacja z EXIF”,
- obrazki przechodzą przez tę samą ścieżkę co upload z frontendu (serwis `media`: zapis, miniatura, odczyt EXIF), a nie są wpisywane bezpośrednio do bazy.

Uwaga: wbudowany font Pillow nie ma polskich znaków, dlatego podpis na obrazkach jest bez diakrytyków („Dane demo - nr 12”). Opisy zgłoszeń demo zaczynają się od „[DEMO]”.

## Uruchamianie

Porty na hoście: baza `5433` (5432 bywa zajęty), baza testowa `5434`, backend `8000`, frontend `5173`.

```
docker compose up -d --build                                  # db, backend (migracje przy starcie), frontend
docker compose exec backend python -m scripts.seed [--reset]  # dane demo
docker compose --profile test up -d db-test                   # baza do testów
cd backend && uv run pytest                                   # albo: docker compose --profile test run --rm backend pytest
cd frontend && npx vitest run && npm run build
```

Seeder uruchamiać w kontenerze: lokalnie zapisałby pliki do `backend/media/`, którego kontener nie serwuje.

## Testy

- `pytest` na prawdziwej bazie PostGIS (kontener `db-test`, dane w tmpfs), nie na SQLite. Schemat budowany z migracji Alembica.
- Testy generowania raportów muszą używać tygodni z przeszłości (przyszłego tygodnia nie da się wygenerować).
- Minimum: tworzenie zgłoszenia z lokalizacją z formularza i z EXIF, `422` bez lokalizacji, kolejność współrzędnych, filtr `bbox`, soft delete (zniknięcie z feedu i mapy), idempotentny `DELETE`, granice tygodnia w `Europe/Warsaw`, generowanie raportu i jego niezmienność po usunięciu zgłoszenia, `409`/`force`, paginacja feedu.
