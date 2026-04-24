from fastapi import Depends, FastAPI, Header, HTTPException, status
from pydantic import BaseModel, Field

from app.config import settings
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


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": settings.app_name}


@app.post("/v1/offers/ingest")
def enqueue_ingest(payload: IngestRequest, tenant_id: str = Depends(require_tenant)) -> dict[str, str]:
    task = ingest_offer.delay(tenant_id=tenant_id, document_id=payload.document_id, source_url=payload.source_url)
    return {"task_id": task.id, "status": "queued"}


@app.post("/v1/offers/embed")
def enqueue_embed(payload: EmbedRequest, tenant_id: str = Depends(require_tenant)) -> dict[str, str]:
    task = embed_chunks.delay(tenant_id=tenant_id, document_id=payload.document_id)
    return {"task_id": task.id, "status": "queued"}


@app.post("/v1/offers/compare")
def enqueue_compare(payload: CompareRequest, tenant_id: str = Depends(require_tenant)) -> dict[str, str]:
    task = compare_offers.delay(tenant_id=tenant_id, offer_ids=payload.offer_ids)
    return {"task_id": task.id, "status": "queued"}
