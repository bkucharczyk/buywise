from dataclasses import dataclass

from fastapi.testclient import TestClient

from app.main import app, get_job_service


@dataclass
class TaskResult:
    id: str


class FakeDelay:
    def __init__(self, task_id: str):
        self.task_id = task_id

    def delay(self, **kwargs):
        return TaskResult(id=self.task_id)


class FakeJobService:
    def __init__(self):
        self.jobs: dict[str, dict] = {}
        self.counter = 0

    def enqueue_job(self, tenant_id: str, job_type: str, payload: dict):
        self.counter += 1
        job_id = f"job-{self.counter}"
        self.jobs[job_id] = {
            "id": job_id,
            "tenant_id": tenant_id,
            "job_type": job_type,
            "status": "queued",
            "payload": payload,
            "task_id": None,
        }
        return job_id

    def attach_task(self, tenant_id: str, job_id: str, task_id: str):
        self.jobs[job_id]["task_id"] = task_id
        return True

    def get_job(self, tenant_id: str, job_id: str):
        job = self.jobs.get(job_id)
        if not job or job["tenant_id"] != tenant_id:
            return None
        return job


fake_service = FakeJobService()
app.dependency_overrides[get_job_service] = lambda: fake_service
client = TestClient(app)


def test_requires_tenant_header():
    response = client.post("/v1/offers/embed", json={"document_id": "doc-1"})
    assert response.status_code == 400


def test_enqueue_ingest_and_get_job(monkeypatch):
    monkeypatch.setattr("app.main.ingest_offer", FakeDelay(task_id="task-123"))

    enqueue = client.post(
        "/v1/offers/ingest",
        headers={"x-tenant-id": "tenant-a"},
        json={"document_id": "doc-1", "source_url": "https://example.com/a.pdf"},
    )

    assert enqueue.status_code == 200
    body = enqueue.json()
    assert body["status"] == "queued"
    assert body["task_id"] == "task-123"

    job_response = client.get(f"/v1/jobs/{body['job_id']}", headers={"x-tenant-id": "tenant-a"})
    assert job_response.status_code == 200
    job = job_response.json()
    assert job["task_id"] == "task-123"
    assert job["tenant_id"] == "tenant-a"


def test_job_tenant_isolation():
    fake_service.jobs["job-shared"] = {
        "id": "job-shared",
        "tenant_id": "tenant-a",
        "job_type": "ingest_offer",
        "status": "queued",
        "payload": {},
        "task_id": "task-999",
    }

    response = client.get("/v1/jobs/job-shared", headers={"x-tenant-id": "tenant-b"})
    assert response.status_code == 404
