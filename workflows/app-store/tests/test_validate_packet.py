from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "tools" / "validate_packet.py"


class ValidatePacketTests(unittest.TestCase):
    def make_packet(self) -> tuple[tempfile.TemporaryDirectory[str], Path, dict[str, object]]:
        temporary = tempfile.TemporaryDirectory()
        root = Path(temporary.name)
        numbered = """1. Physical-device testing and recording\nDevice recording.\n
2. Purpose, target audience, value, and business model\nPurpose audience value business.\n
3. Setup and access\nSetup and access.\n
4. External services and tools\nExternal service.\n
5. Regional differences\nSame in every region.\n
6. Regulated activity and protected material\nNo regulated activity or protected material.\n"""
        (root / "review-notes.txt").write_text(numbered, encoding="utf-8")
        (root / "reviewer-response.txt").write_text(numbered, encoding="utf-8")
        video = root / "device-demo.mov"
        video.write_bytes(b"test-video")
        (root / "physical-device-tests.json").write_text(json.dumps({
            "result": "Passed",
            "device": "iPhone",
            "osVersion": "iOS",
            "passedTests": 1,
        }), encoding="utf-8")
        packet: dict[str, object] = {
            "schemaVersion": 1,
            "appName": "Open Example",
            "bundleId": "com.example.openexample",
            "platform": "IOS",
            "version": "1.0.0",
            "buildNumber": "1",
            "supportUrl": "https://example.com/support/",
            "privacyUrl": "https://example.com/privacy/",
            "releaseType": "MANUAL",
            "reviewNotesFile": "review-notes.txt",
            "reviewResponseFile": "reviewer-response.txt",
            "physicalDeviceTestSummaryFile": "physical-device-tests.json",
            "reviewVideo": {
                "file": "device-demo.mov",
                "sha256": hashlib.sha256(video.read_bytes()).hexdigest(),
                "durationSeconds": 30,
                "device": "iPhone",
                "osVersion": "iOS",
                "demonstrates": "Home Screen, launch, and core flow",
            },
        }
        manifest = root / "submission.json"
        manifest.write_text(json.dumps(packet), encoding="utf-8")
        return temporary, manifest, packet

    def run_validator(self, manifest: Path) -> tuple[subprocess.CompletedProcess[str], dict[str, object]]:
        result = subprocess.run(
            [sys.executable, str(SCRIPT), str(manifest)],
            check=False,
            capture_output=True,
            text=True,
        )
        return result, json.loads(result.stdout)

    def test_ready_packet(self) -> None:
        temporary, manifest, _ = self.make_packet()
        self.addCleanup(temporary.cleanup)
        result, report = self.run_validator(manifest)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(report["status"], "ready")

    def test_rejects_path_escape(self) -> None:
        temporary, manifest, packet = self.make_packet()
        self.addCleanup(temporary.cleanup)
        packet["reviewNotesFile"] = "../private.txt"
        manifest.write_text(json.dumps(packet), encoding="utf-8")
        result, report = self.run_validator(manifest)
        self.assertEqual(result.returncode, 1)
        self.assertTrue(any("must not escape" in failure for failure in report["failures"]))

    def test_rejects_oversized_notes(self) -> None:
        temporary, manifest, _ = self.make_packet()
        self.addCleanup(temporary.cleanup)
        (manifest.parent / "review-notes.txt").write_text("x" * 4001, encoding="utf-8")
        result, report = self.run_validator(manifest)
        self.assertEqual(result.returncode, 1)
        self.assertTrue(any("at most 4000 bytes" in failure for failure in report["failures"]))

    def test_rejects_video_hash_mismatch(self) -> None:
        temporary, manifest, packet = self.make_packet()
        self.addCleanup(temporary.cleanup)
        packet["reviewVideo"]["sha256"] = "0" * 64  # type: ignore[index]
        manifest.write_text(json.dumps(packet), encoding="utf-8")
        result, report = self.run_validator(manifest)
        self.assertEqual(result.returncode, 1)
        self.assertTrue(any("SHA-256 matches" in failure for failure in report["failures"]))

    def test_rejects_duplicate_or_out_of_order_sections(self) -> None:
        temporary, manifest, _ = self.make_packet()
        self.addCleanup(temporary.cleanup)
        notes = (manifest.parent / "review-notes.txt").read_text(encoding="utf-8")
        (manifest.parent / "review-notes.txt").write_text(notes.replace("3. Setup", "2. Setup"), encoding="utf-8")
        result, report = self.run_validator(manifest)
        self.assertEqual(result.returncode, 1)
        self.assertTrue(any("exactly once and in order" in failure for failure in report["failures"]))


if __name__ == "__main__":
    unittest.main()
