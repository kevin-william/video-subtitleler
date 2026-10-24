from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import pytest

from video_subtitleler.models.schema import JobProgress
from video_subtitleler.storage.job_store import JobNotFound, MemoryJobStore, SQLiteJobStore


@pytest.fixture(params=["memory", "sqlite"])
def store(request, tmp_path):
    return MemoryJobStore() if request.param == "memory" else SQLiteJobStore(tmp_path / "jobs.db")


def test_lifecycle_and_immutable_reads(store, tmp_path):
    job = store.create()
    job.progress.steps.clear()
    assert len(store.get(job.job_id).progress.steps) == 5
    store.update(JobProgress(job_id=job.job_id, status="PROCESSING", progress_pct=30))
    with pytest.raises(ValueError):
        store.update(JobProgress(job_id=job.job_id, status="PROCESSING", progress_pct=20))
    store.update(JobProgress(job_id=job.job_id, status="COMPLETED", progress_pct=100), tmp_path / "out.mp4")
    assert store.get(job.job_id).status == "COMPLETED"
    with pytest.raises(ValueError):
        store.update(JobProgress(job_id=job.job_id, status="PROCESSING", progress_pct=100))


def test_missing_duplicate_and_invalid_transition(store):
    with pytest.raises(JobNotFound):
        store.get(uuid4())
    job = store.create()
    with pytest.raises(ValueError):
        store.create(job.job_id)
    with pytest.raises(ValueError):
        store.update(JobProgress(job_id=job.job_id, status="COMPLETED", progress_pct=100))


def test_concurrent_jobs(store):
    def work(_):
        job = store.create()
        store.update(JobProgress(job_id=job.job_id, status="PROCESSING", progress_pct=10))
        return store.get(job.job_id)
    with ThreadPoolExecutor(max_workers=4) as pool:
        jobs = list(pool.map(work, range(12)))
    assert len({job.job_id for job in jobs}) == 12
    assert all(job.status == "PROCESSING" for job in jobs)


def test_sqlite_reopen(tmp_path):
    path = tmp_path / "jobs.db"
    first = SQLiteJobStore(path)
    job = first.create()
    assert SQLiteJobStore(path).get(job.job_id) == job
