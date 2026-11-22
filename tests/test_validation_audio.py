from __future__ import annotations

import os
import re
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

from live_clipper.config import Settings
from live_clipper.resource_store import ResourceError
from live_clipper.resource_validation import validate_asr
from live_clipper.validation_audio import ValidationAudioUnavailable, open_validation_audio, readable_wav

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / "src/live_clipper/validation_audio.wav"
MESSAGE = "应用缺少可读取的内置验证音频，无法检查本机语音模型。已下载的模型文件已保留。"


def test_source_sample_is_a_readable_wav():
    with open_validation_audio() as sample:
        assert sample == SAMPLE
        assert readable_wav(sample)
        assert sample.read_bytes().startswith(b"RIFF")


def test_missing_sample_raises_a_specific_code(monkeypatch):
    monkeypatch.setattr("live_clipper.validation_audio._stable_candidates", lambda: [])
    monkeypatch.setattr(
        "live_clipper.validation_audio.resources.files",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(FileNotFoundError()),
    )
    with pytest.raises(ValidationAudioUnavailable) as caught:
        with open_validation_audio():
            pass
    assert caught.value.code == "validation_audio_unavailable"


def test_asr_check_transcribes_the_packaged_sample(monkeypatch):
    seen = []

    def transcribe(sample, _destination, _settings):
        seen.append(Path(sample))
        return {"segments": [{"start": 0.0, "end": 1.0, "text": "测试"}]}

    monkeypatch.setattr("live_clipper.transcribe.transcribe_audio", transcribe)
    validate_asr(Settings(), local=False)
    assert seen == [SAMPLE]
    assert readable_wav(seen[0])


def test_asr_check_reports_missing_audio_without_transcribing(monkeypatch):
    def forbidden(*_args, **_kwargs):
        pytest.fail("transcription started without validation audio")

    monkeypatch.setattr("live_clipper.transcribe.transcribe_audio", forbidden)
    monkeypatch.setattr(
        "live_clipper.resource_validation.open_validation_audio",
        lambda: (_ for _ in ()).throw(ValidationAudioUnavailable()),
    )
    with pytest.raises(ResourceError) as caught:
        validate_asr(Settings(), local=False)
    assert caught.value.code == "validation_audio_unavailable"


def test_preparation_keeps_the_model_and_names_the_missing_audio(tmp_path, monkeypatch):
    from live_clipper import asr_models, jobs
    from live_clipper.project_storage import ProjectRepository
    from live_clipper.resource_api import MESSAGES, ResourceAPI
    from live_clipper.resource_store import ResourceStore

    assert MESSAGES["validation_audio_unavailable"] == MESSAGE
    assert MESSAGE in (ROOT / "frontend/src/ResourcesPage.tsx").read_text(encoding="utf-8")
    monkeypatch.setattr(asr_models, "models_root", lambda: tmp_path / "models")
    monkeypatch.setattr(asr_models, "model_entry", lambda _model: {})
    monkeypatch.setattr(asr_models, "local_path_for", lambda _model: tmp_path / "model")
    monkeypatch.setattr(asr_models, "download_model", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        "live_clipper.resource_validation.open_validation_audio",
        lambda: (_ for _ in ()).throw(ValidationAudioUnavailable()),
    )
    with ProjectRepository(tmp_path / "service") as repository:
        resource = ResourceStore(repository).save(
            {"name": "隔离模型", "kind": "local_asr", "config": {"model": "test-model", "purposes": ["asr"]}},
            request_id="local-model",
        )
        work = []
        monkeypatch.setattr(jobs, "start_job", lambda _root, **kwargs: work.append(kwargs["fn"]) or {"id": "isolated-job"})
        status, result = ResourceAPI(repository, Settings()).dispatch(
            "POST", ["api", "resources", resource["resource_id"], "prepare"], {"expected_revision": 1}
        )
        failure = work[0]()
    assert status == 202
    assert failure["ok"] is False
    assert failure["code"] == "validation_audio_unavailable"
    assert failure["message"] == MESSAGE
    assert not result["ok"] or result["job"]["id"] == "isolated-job"


def test_backend_build_copies_validation_audio_into_the_package():
    script = (ROOT / "desktop/scripts/build-backend.sh").read_text(encoding="utf-8")
    marker = '--add-data "$PWD/src/live_clipper/validation_audio.wav:live_clipper"'
    command = script.split(".venv/bin/pyinstaller", 1)[1].split("desktop/backend_entry.py", 1)[0]
    assert marker in command


def _freeze(tmp_path: Path, name: str, *, include_audio: bool) -> subprocess.CompletedProcess[str]:
    probe = tmp_path / f"{name}.py"
    probe.write_text(
        textwrap.dedent(
            """
            import sys
            from live_clipper.validation_audio import ValidationAudioUnavailable, open_validation_audio
            try:
                with open_validation_audio() as sample:
                    data = sample.read_bytes()
            except ValidationAudioUnavailable as exc:
                print(exc.code)
                raise SystemExit(2)
            print(getattr(sys, "_MEIPASS", ""))
            print(sample)
            print(data[:12].hex())
            print(len(data))
            """
        ),
        encoding="utf-8",
    )
    command = [
        sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--log-level", "WARN",
        "--name", name, "--distpath", str(tmp_path / name / "dist"), "--workpath", str(tmp_path / name / "work"),
        "--specpath", str(tmp_path / name / "spec"), "--paths", str(ROOT / "src"),
    ]
    if include_audio:
        command.extend(["--add-data", f"{SAMPLE}{os.pathsep}live_clipper"])
    command.append(str(probe))
    return subprocess.run(command, cwd=tmp_path, check=False, capture_output=True, text=True, timeout=180)


def _run_frozen(tmp_path: Path, name: str) -> subprocess.CompletedProcess[str]:
    binary = tmp_path / name / "dist" / name / name
    return subprocess.run([str(binary)], cwd=tmp_path, check=False, capture_output=True, text=True, timeout=30)


def test_pyinstaller_omits_validation_audio_unless_add_data_is_set(tmp_path: Path):
    missing = _freeze(tmp_path, "without-audio", include_audio=False)
    assert missing.returncode == 0, missing.stderr
    without = _run_frozen(tmp_path, "without-audio")
    assert without.returncode == 2
    assert "validation_audio_unavailable" in without.stdout
    packaged = tmp_path / "without-audio/dist/without-audio"
    assert list(packaged.rglob("validation_audio.wav")) == []

    included = _freeze(tmp_path, "with-audio", include_audio=True)
    assert included.returncode == 0, included.stderr
    with_audio = _run_frozen(tmp_path, "with-audio")
    assert with_audio.returncode == 0, with_audio.stderr
    meipass, located, header, size = with_audio.stdout.splitlines()
    assert meipass
    assert Path(located).is_relative_to(meipass)
    assert header == SAMPLE.read_bytes()[:12].hex()
    assert int(size) == SAMPLE.stat().st_size
    bundled = list((tmp_path / "with-audio/dist/with-audio").rglob("validation_audio.wav"))
    assert len(bundled) == 1
    assert bundled[0].read_bytes() == SAMPLE.read_bytes()
    assert re.search(r"live_clipper[/\\]validation_audio\.wav$", bundled[0].as_posix())
