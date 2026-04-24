from datetime import UTC, datetime
from typing import Any

import requests
from bson.errors import InvalidId

from app.celery_app import celery_app
from app.config import settings
from app.db import get_db
from app.repositories.jobs import JobRepository


def _post_to_r2r(endpoint: str, payload: dict[str, Any]) -> dict[str, Any]:
    response = requests.post(
        f"{settings.r2r_url.rstrip('/')}/{endpoint.lstrip('/')}",
        json=payload,
        timeout=60,
    )
    response.raise_for_status()
    return response.json()


def _job_repository() -> JobRepository:
    return JobRepository(get_db())


def _mark_running(tenant_id: str, job_id: str) -> None:
    try:
        _job_repository().update_status(tenant_id=tenant_id, job_id=job_id, status="running")
    except InvalidId:
        return


def _mark_failed(tenant_id: str, job_id: str, error: str) -> None:
    try:
        _job_repository().update_status(
            tenant_id=tenant_id,
            job_id=job_id,
            status="failed",
            error_message=error,
        )
    except InvalidId:
        return


def _mark_succeeded(tenant_id: str, job_id: str, result: dict[str, Any]) -> None:
    try:
        _job_repository().update_status(
            tenant_id=tenant_id,
            job_id=job_id,
            status="succeeded",
            result=result,
            error_message=None,
        )
    except InvalidId:
        return


@celery_app.task(bind=True, autoretry_for=(requests.RequestException,), retry_backoff=True, max_retries=4)
def ingest_offer(self, tenant_id: str, job_id: str, document_id: str, source_url: str) -> dict[str, Any]:
    _mark_running(tenant_id=tenant_id, job_id=job_id)
    payload = {
        "document_id": document_id,
        "source_url": source_url,
        "metadata": {
            "tenant_id": tenant_id,
            "ingested_at": datetime.now(UTC).isoformat(),
            "pipeline": "offer_ingestion",
        },
    }
    try:
        result = _post_to_r2r("v1/documents/ingest", payload)
        final = {"tenant_id": tenant_id, "document_id": document_id, "result": result}
        _mark_succeeded(tenant_id=tenant_id, job_id=job_id, result=final)
        return final
    except requests.RequestException as exc:
        _mark_failed(tenant_id=tenant_id, job_id=job_id, error=str(exc))
        raise


@celery_app.task(bind=True, autoretry_for=(requests.RequestException,), retry_backoff=True, max_retries=4)
def embed_chunks(self, tenant_id: str, job_id: str, document_id: str) -> dict[str, Any]:
    _mark_running(tenant_id=tenant_id, job_id=job_id)
    payload = {
        "document_id": document_id,
        "embedding_provider": "openai",
        "embedding_model": settings.openai_embedding_model,
        "metadata_filter": {"tenant_id": tenant_id},
    }
    try:
        result = _post_to_r2r("v1/documents/embed", payload)
        final = {"tenant_id": tenant_id, "document_id": document_id, "result": result}
        _mark_succeeded(tenant_id=tenant_id, job_id=job_id, result=final)
        return final
    except requests.RequestException as exc:
        _mark_failed(tenant_id=tenant_id, job_id=job_id, error=str(exc))
        raise


@celery_app.task(bind=True, autoretry_for=(requests.RequestException,), retry_backoff=True, max_retries=4)
def compare_offers(self, tenant_id: str, job_id: str, offer_ids: list[str]) -> dict[str, Any]:
    _mark_running(tenant_id=tenant_id, job_id=job_id)
    payload = {
        "tenant_id": tenant_id,
        "offer_ids": offer_ids,
        "top_k": 20,
        "strategy": "price_quality_delivery",
    }
    try:
        result = _post_to_r2r("v1/retrieval/query", payload)
        final = {"tenant_id": tenant_id, "offer_ids": offer_ids, "result": result}
        _mark_succeeded(tenant_id=tenant_id, job_id=job_id, result=final)
        return final
    except requests.RequestException as exc:
        _mark_failed(tenant_id=tenant_id, job_id=job_id, error=str(exc))
        raise
