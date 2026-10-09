#!/usr/bin/env python3
"""Validate a local App Store review packet without contacting Apple."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlparse


REQUIRED_FIELDS = {
    "schemaVersion",
    "appName",
    "bundleId",
    "platform",
    "version",
    "buildNumber",
    "supportUrl",
    "privacyUrl",
    "releaseType",
    "reviewNotesFile",
    "reviewResponseFile",
    "physicalDeviceTestSummaryFile",
    "reviewVideo",
}

SECTION_TERMS = {
    1: ("device", "record"),
    2: ("purpose", "audience", "value", "business"),
    3: ("setup", "access"),
    4: ("external", "service"),
    5: ("region",),
    6: ("regulated", "material"),
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def split_sections(text: str) -> tuple[list[int], dict[int, str]]:
    matches = list(re.finditer(r"(?m)^\s*([1-6])[.)]\s+", text))
    sequence = [int(match.group(1)) for match in matches]
    sections: dict[int, str] = {}
    for index, match in enumerate(matches):
        number = int(match.group(1))
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        sections[number] = text[match.start():end].lower()
    return sequence, sections


def validate_numbered_text(path: Path, label: str, failures: list[str], passes: list[str]) -> None:
    try:
        raw = path.read_bytes()
        text = raw.decode("utf-8")
    except Exception as exc:
        failures.append(f"{label} readable as UTF-8: {exc}")
        return

    if len(raw) > 4000:
        failures.append(f"{label} is {len(raw)} bytes; Apple Notes-compatible text must be at most 4000 bytes")
    else:
        passes.append(f"{label} is within 4000 bytes")

    sequence, sections = split_sections(text)
    if sequence != list(range(1, 7)):
        failures.append(f"{label} contains numbered sections 1 through 6 exactly once and in order")
        return

    for number, terms in SECTION_TERMS.items():
        missing = [term for term in terms if term not in sections[number]]
        if missing:
            failures.append(f"{label} section {number} is missing: {', '.join(missing)}")
    if not any(f.startswith(f"{label} section") for f in failures):
        passes.append(f"{label} contains all six required topics")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path, help="Path to submission.json")
    args = parser.parse_args()

    failures: list[str] = []
    passes: list[str] = []
    warnings: list[str] = []
    manifest_path = args.manifest.resolve()

    try:
        packet = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception as exc:
        print(json.dumps({"status": "blocked", "failures": [f"manifest readable: {exc}"]}, indent=2))
        return 1

    packet_root = manifest_path.parent.resolve()

    def resolve_local(value: object, label: str) -> Path | None:
        if not isinstance(value, str) or not value.strip():
            failures.append(f"{label} is a non-empty relative path")
            return None
        candidate = Path(value)
        if candidate.is_absolute():
            failures.append(f"{label} must be relative to the packet directory")
            return None
        resolved = (packet_root / candidate).resolve()
        if resolved != packet_root and packet_root not in resolved.parents:
            failures.append(f"{label} must not escape the packet directory")
            return None
        return resolved

    missing = sorted(REQUIRED_FIELDS - packet.keys())
    if missing:
        failures.append(f"manifest is missing fields: {', '.join(missing)}")
    else:
        passes.append("manifest contains all required fields")

    if packet.get("schemaVersion") != 1:
        failures.append("schemaVersion must be 1")

    for field in ("appName", "platform", "version", "buildNumber", "releaseType"):
        if not isinstance(packet.get(field), str) or not packet[field].strip():
            failures.append(f"{field} is required")

    bundle_id = packet.get("bundleId", "")
    if not isinstance(bundle_id, str) or not re.fullmatch(r"[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+", bundle_id):
        failures.append("bundleId must be a reverse-DNS identifier")

    for field in ("supportUrl", "privacyUrl"):
        value = packet.get(field, "")
        parsed = urlparse(value) if isinstance(value, str) else None
        if not parsed or parsed.scheme != "https" or not parsed.netloc:
            failures.append(f"{field} must be an absolute HTTPS URL")

    for field, label in (
        ("reviewNotesFile", "review notes"),
        ("reviewResponseFile", "reviewer response"),
    ):
        path = resolve_local(packet.get(field), field)
        if path and path.is_file():
            validate_numbered_text(path, label, failures, passes)
        elif path:
            failures.append(f"{label} file exists")

    summary_path = resolve_local(packet.get("physicalDeviceTestSummaryFile"), "physicalDeviceTestSummaryFile")
    if summary_path and summary_path.is_file():
        try:
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
            if summary.get("result") != "Passed":
                failures.append("physical-device test result must be Passed")
            if not isinstance(summary.get("passedTests"), int) or summary["passedTests"] < 1:
                failures.append("physical-device test summary must report at least one passed test")
            for field in ("device", "osVersion"):
                if not isinstance(summary.get(field), str) or not summary[field].strip():
                    failures.append(f"physical-device test summary requires {field}")
            if not any(f.startswith("physical-device test") for f in failures):
                passes.append("physical-device test summary passed")
        except Exception as exc:
            failures.append(f"physical-device test summary readable: {exc}")
    elif summary_path:
        failures.append("physical-device test summary file exists")

    video = packet.get("reviewVideo")
    if not isinstance(video, dict):
        failures.append("reviewVideo must be an object")
    else:
        video_path = resolve_local(video.get("file"), "reviewVideo.file")
        if video_path and not video_path.is_file():
            failures.append("physical-device review video exists")
        elif video_path:
            if video_path.suffix.lower() not in {".mov", ".mp4"}:
                failures.append("review video uses .mov or .mp4")
            if video_path.stat().st_size == 0:
                failures.append("review video is not empty")
            expected_hash = video.get("sha256", "")
            if not isinstance(expected_hash, str) or not re.fullmatch(r"[0-9a-f]{64}", expected_hash):
                failures.append("reviewVideo.sha256 must be 64 lowercase hexadecimal characters")
            elif sha256(video_path) != expected_hash:
                failures.append("review video SHA-256 matches the manifest")
            else:
                passes.append("review video SHA-256 matches the manifest")

        duration = video.get("durationSeconds")
        if not isinstance(duration, (int, float)) or not 5 <= duration <= 180:
            failures.append("reviewVideo.durationSeconds must be between 5 and 180")
        for field in ("device", "osVersion", "demonstrates"):
            if not isinstance(video.get(field), str) or not video[field].strip():
                failures.append(f"reviewVideo.{field} is required")
        warnings.append("Video metadata is declared by the manifest; inspect the actual recording before submission")

    report = {
        "status": "ready" if not failures else "blocked",
        "passes": passes,
        "warnings": warnings,
        "failures": failures,
    }
    print(json.dumps(report, indent=2))
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
