"""The P6 tools under eval/amounts_v2: the pinned parser and the stand-alone reproduction script."""

from __future__ import annotations

import email.parser
import email.policy
import importlib.util
import json
import struct
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import ClassVar

import pytest

from samajh.clients.gnani.client import _stt_fields
from samajh.clients.gnani.types import PrismaV25, PrismaV30

TOOLS = Path(__file__).resolve().parents[2] / "eval" / "amounts_v2"


def _module(name: str):
    spec = importlib.util.spec_from_file_location(name, TOOLS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_frozen_parser_is_the_pinned_copy_and_parses(tmp_path: Path) -> None:
    frozen = _module("frozen_parser")
    amounts = frozen.load(tmp_path)
    assert Path(amounts.__file__).is_relative_to(tmp_path)
    assert amounts.__name__ == "samajh_amounts_59c12d9"
    result = amounts.parse_amount("तीन लाख दो सौ रुपये")
    assert isinstance(result, amounts.Parsed) and result.rupees == 300_200
    # Exporting again into the same directory changes nothing.
    assert frozen.fingerprint(frozen.export(tmp_path)) == amounts.FINGERPRINT
    assert not any("samajh.amounts" in p.read_text() for p in (tmp_path / amounts.__name__).glob("*.py"))


def _bad_wav() -> bytes:
    """A 16 kHz mono WAV whose RIFF and data sizes are 0xFFFFFFFF, as Timbre sends them."""
    fmt = struct.pack("<HHIIHH", 1, 1, 16000, 32000, 2, 16)
    samples = b"\x00\x00" * 160
    return (
        b"RIFF"
        + b"\xff" * 4
        + b"WAVE"
        + b"fmt "
        + struct.pack("<I", 16)
        + fmt
        + b"data"
        + b"\xff" * 4
        + samples
    )


class _Recorder(BaseHTTPRequestHandler):
    seen: ClassVar[list[tuple[str, dict[str, str], bytes]]] = []

    def do_POST(self) -> None:
        body = self.rfile.read(int(self.headers["Content-Length"]))
        # Header names are case-insensitive (urllib sends "X-api-key-id").
        _Recorder.seen.append((self.path, {k.lower(): v for k, v in self.headers.items()}, body))
        if self.path == "/api/v1/tts/inference":
            payload, kind = _bad_wav(), "audio/wav"
        else:
            payload, kind = (
                json.dumps({"success": True, "transcript": "x 3,40,000 y"}).encode(),
                "application/json",
            )
        self.send_response(200)
        self.send_header("Content-Type", kind)
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, *args) -> None:
        pass


@pytest.fixture
def server():
    _Recorder.seen = []
    httpd = HTTPServer(("127.0.0.1", 0), _Recorder)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{httpd.server_port}"
    httpd.shutdown()


def test_repro_sends_what_the_project_client_sends(server: str) -> None:
    repro = _module("repro_number_formatting")
    repro.BASE_URL = server
    wav = repro.tts("कुछ", "hi-IN", "timbre-v3.0", "Kalpana", "k-test")
    assert struct.unpack_from("<I", wav, 4)[0] == len(wav) - 8
    assert struct.unpack_from("<I", wav, 40)[0] == len(wav) - 44
    reply = repro.stt(wav, "prisma-v3.0", "transcribe", "k-test")
    assert reply["transcript"] == "x 3,40,000 y"
    repro.stt(wav, "prisma-v2.5", "transcribe", "k-test")

    (tts_path, tts_headers, tts_body), *stt_calls = _Recorder.seen
    assert tts_path == "/api/v1/tts/inference" and tts_headers["x-api-key-id"] == "k-test"
    assert json.loads(tts_body) == {
        "text": "कुछ",
        "voice": "Kalpana",
        "model": "timbre-v3.0",
        "language": "hi-IN",
        "speed": 1.0,
        "audio_config": {"sample_rate": 16000, "container": "wav"},
    }
    expected = [
        _stt_fields(PrismaV30(language="hi-IN", format="transcribe")),
        _stt_fields(PrismaV25(language="hi-IN", format="transcribe")),
    ]
    for (path, headers, body), fields in zip(stt_calls, expected, strict=True):
        assert path == "/stt/v3"
        message = email.parser.BytesParser(policy=email.policy.HTTP).parsebytes(
            f"Content-Type: {headers['content-type']}\r\n\r\n".encode() + body
        )
        parts = {part.get_param("name", header="content-disposition"): part for part in message.iter_parts()}
        assert {k: parts[k].get_content() for k in fields} == fields
        assert set(parts) == {*fields, "audio_file"}
        assert parts["audio_file"].get_filename() == "audio.wav"
        assert parts["audio_file"].get_content() == wav


def test_repro_reads_digits_and_writes_indian_grouping() -> None:
    repro = _module("repro_number_formatting")
    assert repro.digits("प्रीमियम ₹3,00,040 होगा") == [300_040]
    assert repro.digits("किस्त 56,82 रुपये") == [5682]
    assert repro.digits("कोई अंक नहीं") == []
    assert [repro.indian(n) for n in (2012, 300_040, 50_026_000, 500)] == [
        "2,012",
        "3,00,040",
        "5,00,26,000",
        "500",
    ]
    assert all(rupees > 0 for *_, rupees, _ in repro.SENTENCES)
