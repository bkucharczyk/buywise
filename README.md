# BuyWise (MVP foundation)

Bazowy szkielet backendu dla platformy porównywania ofert:
- FastAPI API,
- Celery (broker Redis + backend wyników MongoDB),
- MongoDB (shared collections pod multi-tenant),
- Qdrant + R2R pod RAG,
- przygotowanie pod embeddingi OpenAI i Google Auth.

## Uruchomienie lokalne

1. Skopiuj konfigurację:
   ```bash
   cp .env.example .env
   ```
2. Uruchom stack:
   ```bash
   docker compose up --build
   ```
3. Healthcheck API:
   ```bash
   curl http://localhost:8000/health
   ```

## Tenant enforcement (MVP)

Endpointy kolejkowania wymagają nagłówka `x-tenant-id`.

Przykład:
```bash
curl -X POST http://localhost:8000/v1/offers/ingest \
  -H "Content-Type: application/json" \
  -H "x-tenant-id: tenant-acme" \
  -d '{"document_id":"doc-1","source_url":"https://example.com/oferta.pdf"}'
```

## Job tracking (Sprint A)

Każdy request enqueue tworzy rekord w kolekcji `jobs` i zwraca `job_id` + `task_id`.

Sprawdzenie statusu:
```bash
curl http://localhost:8000/v1/jobs/<job_id> -H "x-tenant-id: tenant-acme"
```

Statusy:
- `queued`
- `running`
- `succeeded`
- `failed`

## Zadania Celery

- `ingest_offer`: wysyła dokument do R2R ingest,
- `embed_chunks`: odpala embedding dla dokumentu,
- `compare_offers`: odpala retrieval pod porównanie ofert.

Każdy task przekazuje `tenant_id` do metadata/filter i aktualizuje status joba w MongoDB.
