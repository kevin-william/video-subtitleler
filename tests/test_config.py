import os
import subprocess
import sys

import pytest
from pydantic import ValidationError

from video_subtitleler.config import Settings


@pytest.fixture(autouse=True)
def isolated_environment(monkeypatch):
    for key in list(os.environ):
        if key.startswith("SUBTITLE_"):
            monkeypatch.delenv(key)


def test_defaults_do_not_create_files(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    settings = Settings(_env_file=None)
    assert settings.whisper_device == "cpu"
    assert settings.llm_timeout == 30
    assert settings.llm_base_url is None
    assert not settings.work_dir.exists()
    assert list(tmp_path.iterdir()) == []


def test_settings_precedence_and_unicode_path(tmp_path, monkeypatch):
    env = tmp_path / ".env"
    env.write_text('SUBTITLE_LLM_MODEL=dotenv-model\nSUBTITLE_WORK_DIR="pasta com acento/áudio"\n', encoding="utf-8")
    assert Settings(_env_file=env).llm_model == "dotenv-model"
    monkeypatch.setenv("SUBTITLE_LLM_MODEL", "environment-model")
    assert Settings(_env_file=env).llm_model == "environment-model"
    settings = Settings(_env_file=env, llm_model="explicit-model")
    assert settings.llm_model == "explicit-model"
    assert str(settings.work_dir).endswith("áudio")


def test_key_hidden_in_repr_and_serialization(monkeypatch):
    key = "test-only-secret-value"
    monkeypatch.setenv("SUBTITLE_LLM_API_KEY", key)
    settings = Settings(_env_file=None)
    assert settings.llm_api_key.get_secret_value() == key
    assert key not in repr(settings)
    assert key not in settings.model_dump_json()
    assert "llm_api_key" not in settings.model_dump()


@pytest.mark.parametrize("kwargs", [
    {"llm_timeout": 0}, {"llm_timeout": float('nan')},
    {"media_timeout": float('inf')}, {"max_upload_bytes": -1},
    {"llm_base_url": "not-a-url"}, {"ffmpeg_path": " "},
    {"whisper_model": ""}, {"work_dir": ""},
])
def test_invalid_configuration(kwargs):
    with pytest.raises(ValidationError):
        Settings(_env_file=None, **kwargs)


def test_import_without_network_processes_or_heavy_modules():
    code = '''
import sys
def forbid_external(event, args):
    if event in ("socket.connect", "socket.getaddrinfo", "subprocess.Popen", "os.system"):
        raise AssertionError("import attempted external operation")
sys.addaudithook(forbid_external)
import video_subtitleler
from video_subtitleler.config import Settings
from video_subtitleler.models.schema import SubtitleRequest
Settings(_env_file=None)
assert not any(x in sys.modules for x in ("faster_whisper", "langchain_openai", "torch"))
'''
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
