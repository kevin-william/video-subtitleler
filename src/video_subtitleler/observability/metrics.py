"""Coletor de métricas nativo com suporte a exportação em formato Prometheus e JSON."""

from __future__ import annotations

import threading
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any


@dataclass
class _Distribution:
    count: int = 0
    total_sum: float = 0.0
    min_val: float = float("inf")
    max_val: float = 0.0

    def add(self, value: float) -> None:
        self.count += 1
        self.total_sum += value
        if value < self.min_val:
            self.min_val = value
        if value > self.max_val:
            self.max_val = value

    @property
    def avg(self) -> float:
        return (self.total_sum / self.count) if self.count > 0 else 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "count": self.count,
            "sum": round(self.total_sum, 4),
            "min": round(self.min_val, 4) if self.count > 0 else 0.0,
            "max": round(self.max_val, 4),
            "avg": round(self.avg, 4),
        }


def _format_labels(labels: dict[str, str]) -> str:
    if not labels:
        return ""
    pairs = [f'{k}="{v}"' for k, v in sorted(labels.items())]
    return "{" + ",".join(pairs) + "}"


class MetricsCollector:
    """Coletor thread-safe de métricas do sistema."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._jobs_total: dict[tuple[str, str, str], int] = defaultdict(int)
        self._jobs_active: int = 0
        self._job_durations: dict[str, _Distribution] = defaultdict(_Distribution)
        self._step_durations: dict[str, _Distribution] = defaultdict(_Distribution)
        self._step_transitions: dict[tuple[str, str], int] = defaultdict(int)
        self._http_requests_total: dict[tuple[str, str, int], int] = defaultdict(int)
        self._http_request_durations: dict[tuple[str, str], _Distribution] = defaultdict(_Distribution)

    def job_started(self) -> None:
        with self._lock:
            self._jobs_active += 1

    def job_finished(self) -> None:
        with self._lock:
            if self._jobs_active > 0:
                self._jobs_active -= 1

    def record_job(self, *, status: str, mode: str, preset: str, duration: float) -> None:
        with self._lock:
            self._jobs_total[(status, mode, preset)] += 1
            self._job_durations[status].add(duration)

    def record_step(self, *, step: str, status: str, duration: float | None = None) -> None:
        with self._lock:
            self._step_transitions[(step, status)] += 1
            if duration is not None:
                self._step_durations[step].add(duration)

    def record_http_request(self, *, method: str, path: str, status: int, duration: float) -> None:
        with self._lock:
            self._http_requests_total[(method, path, status)] += 1
            self._http_request_durations[(method, path)].add(duration)

    def reset(self) -> None:
        """Limpa as métricas coletadas (útil para testes)."""
        with self._lock:
            self._jobs_total.clear()
            self._jobs_active = 0
            self._job_durations.clear()
            self._step_durations.clear()
            self._step_transitions.clear()
            self._http_requests_total.clear()
            self._http_request_durations.clear()

    def as_dict(self) -> dict[str, Any]:
        """Exporta as métricas em formato dicionário (JSON)."""
        with self._lock:
            return {
                "jobs": {
                    "active": self._jobs_active,
                    "total": [
                        {"status": s, "mode": m, "preset": p, "count": c}
                        for (s, m, p), c in self._jobs_total.items()
                    ],
                    "durations": {s: dist.to_dict() for s, dist in self._job_durations.items()},
                },
                "steps": {
                    "transitions": [
                        {"step": s, "status": st, "count": c}
                        for (s, st), c in self._step_transitions.items()
                    ],
                    "durations": {s: dist.to_dict() for s, dist in self._step_durations.items()},
                },
                "http": {
                    "requests_total": [
                        {"method": m, "path": p, "status": st, "count": c}
                        for (m, p, st), c in self._http_requests_total.items()
                    ],
                    "durations": {
                        f"{m} {p}": dist.to_dict()
                        for (m, p), dist in self._http_request_durations.items()
                    },
                },
            }

    def to_prometheus_text(self) -> str:
        """Exporta as métricas no formato padrão de texto do Prometheus."""
        lines: list[str] = []

        with self._lock:
            # video_subtitles_jobs_active
            lines.append("# HELP video_subtitles_jobs_active Número de jobs atualmente em execução.")
            lines.append("# TYPE video_subtitles_jobs_active gauge")
            lines.append(f"video_subtitles_jobs_active {self._jobs_active}")

            # video_subtitles_jobs_total
            lines.append("# HELP video_subtitles_jobs_total Total de jobs processados por status, modo e preset.")
            lines.append("# TYPE video_subtitles_jobs_total counter")
            for (status, mode, preset), count in sorted(self._jobs_total.items()):
                labels = _format_labels({"status": status, "mode": mode, "preset": preset})
                lines.append(f"video_subtitles_jobs_total{labels} {count}")

            # video_subtitles_job_duration_seconds
            lines.append("# HELP video_subtitles_job_duration_seconds Duração total de processamento dos jobs em segundos.")
            lines.append("# TYPE video_subtitles_job_duration_seconds summary")
            for status, dist in sorted(self._job_durations.items()):
                labels_count = _format_labels({"status": status})
                lines.append(f"video_subtitles_job_duration_seconds_count{labels_count} {dist.count}")
                lines.append(f"video_subtitles_job_duration_seconds_sum{labels_count} {round(dist.total_sum, 4)}")

            # video_subtitles_step_transitions_total
            lines.append("# HELP video_subtitles_step_transitions_total Transições de etapas do pipeline.")
            lines.append("# TYPE video_subtitles_step_transitions_total counter")
            for (step, status), count in sorted(self._step_transitions.items()):
                labels = _format_labels({"step": step, "status": status})
                lines.append(f"video_subtitles_step_transitions_total{labels} {count}")

            # video_subtitles_step_duration_seconds
            lines.append("# HELP video_subtitles_step_duration_seconds Duração das etapas individuais do pipeline em segundos.")
            lines.append("# TYPE video_subtitles_step_duration_seconds summary")
            for step, dist in sorted(self._step_durations.items()):
                labels = _format_labels({"step": step})
                lines.append(f"video_subtitles_step_duration_seconds_count{labels} {dist.count}")
                lines.append(f"video_subtitles_step_duration_seconds_sum{labels} {round(dist.total_sum, 4)}")

            # video_subtitles_http_requests_total
            lines.append("# HELP video_subtitles_http_requests_total Total de requisições HTTP tratadas pela API.")
            lines.append("# TYPE video_subtitles_http_requests_total counter")
            for (method, path, status), count in sorted(self._http_requests_total.items()):
                labels = _format_labels({"method": method, "path": path, "status": str(status)})
                lines.append(f"video_subtitles_http_requests_total{labels} {count}")

            # video_subtitles_http_request_duration_seconds
            lines.append("# HELP video_subtitles_http_request_duration_seconds Duração das requisições HTTP em segundos.")
            lines.append("# TYPE video_subtitles_http_request_duration_seconds summary")
            for (method, path), dist in sorted(self._http_request_durations.items()):
                labels = _format_labels({"method": method, "path": path})
                lines.append(f"video_subtitles_http_request_duration_seconds_count{labels} {dist.count}")
                lines.append(f"video_subtitles_http_request_duration_seconds_sum{labels} {round(dist.total_sum, 4)}")

        return "\n".join(lines) + "\n"


# Instância global padrão
metrics = MetricsCollector()
