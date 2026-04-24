from datetime import UTC, datetime
from typing import Any

import requests

from app.celery_app import celery_app
from app.config import settings


def _post_to_r2r(endpoint: str, payload: dict[str, Any]) -> dict[str, Any]:
    response = requests.post(
        f"{settings.r2r_url.rstrip('/')}/{endpoint.lstrip('/')}",
        json=payload,
        timeout=60,
    )
    response.raise_for_status()
    return response.json()


@celery_app.task(bind=True, autoretry_for=(requests.RequestException,), retry_backoff=True, max_retries=4)
def ingest_offer(self, tenant_id: str, document_id: str, source_url: str) -> dict[str, Any]:
    payload = {
        "document_id": document_id,
        "source_url": source_url,
        "metadata": {
            "tenant_id": tenant_id,
            "ingested_at": datetime.now(UTC).isoformat(),
            "pipeline": "offer_ingestion",
        },
    }
    result = _post_to_r2r("v1/documents/ingest", payload)
    return {"tenant_id": tenant_id, "document_id": document_id, "result": result}


@celery_app.task(bind=True, autoretry_for=(requests.RequestException,), retry_backoff=True, max_retries=4)
def embed_chunks(self, tenant_id: str, document_id: str) -> dict[str, Any]:
    payload = {
        "document_id": document_id,
        "embedding_provider": "openai",
        "embedding_model": settings.openai_embedding_model,
        "metadata_filter": {"tenant_id": tenant_id},
    }
    result = _post_to_r2r("v1/documents/embed", payload)
    return {"tenant_id": tenant_id, "document_id": document_id, "result": result}


@celery_app.task(bind=True, autoretry_for=(requests.RequestException,), retry_backoff=True, max_retries=4)
def compare_offers(self, tenant_id: str, offer_ids: list[str]) -> dict[str, Any]:
    payload = {
        "tenant_id": tenant_id,
        "offer_ids": offer_ids,
        "top_k": 20,
        "strategy": "price_quality_delivery",
    }
    result = _post_to_r2r("v1/retrieval/query", payload)
    return {"tenant_id": tenant_id, "offer_ids": offer_ids, "result": result}
