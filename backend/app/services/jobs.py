from typing import Any

from bson.errors import InvalidId

from app.repositories.jobs import JobRepository


class JobService:
    def __init__(self, repository: JobRepository):
        self.repository = repository

    def enqueue_job(self, tenant_id: str, job_type: str, payload: dict[str, Any]) -> str:
        return self.repository.create_job(tenant_id=tenant_id, job_type=job_type, payload=payload)

    def attach_task(self, tenant_id: str, job_id: str, task_id: str) -> bool:
        try:
            return self.repository.set_task_id(tenant_id=tenant_id, job_id=job_id, task_id=task_id)
        except InvalidId:
            return False

    def get_job(self, tenant_id: str, job_id: str) -> dict[str, Any] | None:
        try:
            return self.repository.get_job(tenant_id=tenant_id, job_id=job_id)
        except InvalidId:
            return None
