from fastapi import Depends, FastAPI, Header, HTTPException, status
from pydantic import BaseModel, Field

from app.config import settings
from app.db import get_db
from app.repositories.jobs import JobRepository
from app.services.jobs import JobService
from app.tasks import compare_offers, embed_chunks, ingest_offer

app = FastAPI(title=settings.app_name)


class IngestRequest(BaseModel):
    document_id: str = Field(min_length=1)
    source_url: str = Field(min_length=1)


class EmbedRequest(BaseModel):
    document_id: str = Field(min_length=1)


class CompareRequest(BaseModel):
    offer_ids: list[str] = Field(min_length=2)


def require_tenant(x_tenant_id: str | None = Header(default=None)) -> str:
    if not x_tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing x-tenant-id header",
        )
    return x_tenant_id


def get_job_service() -> JobService:
    return JobService(JobRepository(get_db()))


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": settings.app_name}


@app.post("/v1/offers/ingest")
def enqueue_ingest(
    payload: IngestRequest,
    tenant_id: str = Depends(require_tenant),
    jobs: JobService = Depends(get_job_service),
) -> dict[str, str]:
    job_id = jobs.enqueue_job(tenant_id=tenant_id, job_type="ingest_offer", payload=payload.model_dump())
    task = ingest_offer.delay(
        tenant_id=tenant_id,
        job_id=job_id,
        document_id=payload.document_id,
        source_url=payload.source_url,
    )
    jobs.attach_task(tenant_id=tenant_id, job_id=job_id, task_id=task.id)
    return {"job_id": job_id, "task_id": task.id, "status": "queued"}


@app.post("/v1/offers/embed")
def enqueue_embed(
    payload: EmbedRequest,
    tenant_id: str = Depends(require_tenant),
    jobs: JobService = Depends(get_job_service),
) -> dict[str, str]:
    job_id = jobs.enqueue_job(tenant_id=tenant_id, job_type="embed_chunks", payload=payload.model_dump())
    task = embed_chunks.delay(tenant_id=tenant_id, job_id=job_id, document_id=payload.document_id)
    jobs.attach_task(tenant_id=tenant_id, job_id=job_id, task_id=task.id)
    return {"job_id": job_id, "task_id": task.id, "status": "queued"}


@app.post("/v1/offers/compare")
def enqueue_compare(
    payload: CompareRequest,
    tenant_id: str = Depends(require_tenant),
    jobs: JobService = Depends(get_job_service),
) -> dict[str, str]:
    job_id = jobs.enqueue_job(tenant_id=tenant_id, job_type="compare_offers", payload=payload.model_dump())
    task = compare_offers.delay(tenant_id=tenant_id, job_id=job_id, offer_ids=payload.offer_ids)
    jobs.attach_task(tenant_id=tenant_id, job_id=job_id, task_id=task.id)
    return {"job_id": job_id, "task_id": task.id, "status": "queued"}


@app.get("/v1/jobs/{job_id}")
def get_job(
    job_id: str,
    tenant_id: str = Depends(require_tenant),
    jobs: JobService = Depends(get_job_service),
) -> dict:
    job = jobs.get_job(tenant_id=tenant_id, job_id=job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return job
