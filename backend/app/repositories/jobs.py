from datetime import UTC, datetime
from typing import Any

from bson import ObjectId
from pymongo.database import Database


class JobRepository:
    def __init__(self, db: Database):
        self.collection = db["jobs"]

    def create_job(self, tenant_id: str, job_type: str, payload: dict[str, Any]) -> str:
        now = datetime.now(UTC)
        document = {
            "tenant_id": tenant_id,
            "job_type": job_type,
            "status": "queued",
            "payload": payload,
            "task_id": None,
            "result": None,
            "error_message": None,
            "created_at": now,
            "updated_at": now,
        }
        inserted = self.collection.insert_one(document)
        return str(inserted.inserted_id)

    def set_task_id(self, tenant_id: str, job_id: str, task_id: str) -> bool:
        updated = self.collection.update_one(
            {"_id": ObjectId(job_id), "tenant_id": tenant_id},
            {"$set": {"task_id": task_id, "updated_at": datetime.now(UTC)}},
        )
        return updated.modified_count == 1

    def update_status(
        self,
        tenant_id: str,
        job_id: str,
        status: str,
        result: dict[str, Any] | None = None,
        error_message: str | None = None,
    ) -> bool:
        update_fields: dict[str, Any] = {
            "status": status,
            "updated_at": datetime.now(UTC),
            "error_message": error_message,
        }
        if result is not None:
            update_fields["result"] = result
        updated = self.collection.update_one(
            {"_id": ObjectId(job_id), "tenant_id": tenant_id},
            {"$set": update_fields},
        )
        return updated.modified_count == 1

    def get_job(self, tenant_id: str, job_id: str) -> dict[str, Any] | None:
        document = self.collection.find_one({"_id": ObjectId(job_id), "tenant_id": tenant_id})
        if not document:
            return None
        document["id"] = str(document.pop("_id"))
        return document
