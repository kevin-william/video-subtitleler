"""Atualizações transacionais; SQLite não fornece uma fila durável."""

import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path
from uuid import UUID

from video_subtitleler.models.schema import Job, JobProgress, JobStatus


class JobNotFound(KeyError):
    pass


def updated(job: Job, progress: JobProgress, output_path: Path | None) -> Job:
    allowed = {
        JobStatus.QUEUED: {JobStatus.PROCESSING, JobStatus.FAILED},
        JobStatus.PROCESSING: {JobStatus.PROCESSING, JobStatus.COMPLETED, JobStatus.FAILED},
        JobStatus.COMPLETED: set(), JobStatus.FAILED: set(),
    }
    if progress.job_id != job.job_id or progress.status not in allowed[job.status]:
        raise ValueError("Transição de job inválida.")
    if job.progress and progress.progress_pct < job.progress.progress_pct:
        raise ValueError("Progresso não pode regredir.")
    if progress.status == JobStatus.COMPLETED and (progress.progress_pct != 100 or output_path is None):
        raise ValueError("Conclusão exige saída e progresso de 100%.")
    if progress.status != JobStatus.COMPLETED and progress.progress_pct == 100:
        raise ValueError("100% exige conclusão.")
    return Job(job_id=job.job_id, created_at=job.created_at, status=progress.status, progress=progress, output_path=output_path)


class MemoryJobStore:
    def __init__(self):
        self._jobs: dict[UUID, Job] = {}
        self._lock = threading.RLock()

    def create(self, job_id: UUID | None = None) -> Job:
        with self._lock:
            job = Job(**({"job_id": job_id} if job_id else {}))
            job = Job(job_id=job.job_id, created_at=job.created_at, progress=JobProgress(job_id=job.job_id))
            if job.job_id in self._jobs:
                raise ValueError("Job já existe.")
            self._jobs[job.job_id] = job
            return job.model_copy(deep=True)

    def get(self, job_id: UUID) -> Job:
        with self._lock:
            try:
                return self._jobs[job_id].model_copy(deep=True)
            except KeyError as exc:
                raise JobNotFound(job_id) from exc

    def update(self, progress: JobProgress, output_path: Path | None = None) -> Job:
        with self._lock:
            job = updated(self.get(progress.job_id), progress, output_path)
            self._jobs[job.job_id] = job.model_copy(deep=True)
            return job


class SQLiteJobStore:
    def __init__(self, database: Path):
        self.database = Path(database)
        self.database.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute("CREATE TABLE IF NOT EXISTS jobs (id TEXT PRIMARY KEY, payload TEXT NOT NULL)")

    @contextmanager
    def _connect(self):
        connection = sqlite3.connect(self.database, timeout=30)
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def create(self, job_id: UUID | None = None) -> Job:
        job = MemoryJobStore().create(job_id)
        try:
            with self._connect() as connection:
                connection.execute("INSERT INTO jobs VALUES (?, ?)", (str(job.job_id), job.model_dump_json()))
        except sqlite3.IntegrityError as exc:
            raise ValueError("Job já existe.") from exc
        return job

    def get(self, job_id: UUID) -> Job:
        with self._connect() as connection:
            row = connection.execute("SELECT payload FROM jobs WHERE id = ?", (str(job_id),)).fetchone()
        if row is None:
            raise JobNotFound(job_id)
        return Job.model_validate_json(row[0])

    def update(self, progress: JobProgress, output_path: Path | None = None) -> Job:
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute("SELECT payload FROM jobs WHERE id = ?", (str(progress.job_id),)).fetchone()
            if row is None:
                raise JobNotFound(progress.job_id)
            job = updated(Job.model_validate_json(row[0]), progress, output_path)
            connection.execute("UPDATE jobs SET payload = ? WHERE id = ?", (job.model_dump_json(), str(job.job_id)))
        return job
