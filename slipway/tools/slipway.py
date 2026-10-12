#!/usr/bin/env python3
"""Slipway: take small iOS apps from idea to the App Store, one checkable phase at a time.

    slipway.py doctor [--api]           is this Mac (and phone) ready to ship?
    slipway.py new <app-dir>            start an app folder from the templates
    slipway.py check <app-dir>          check what the app's current phase needs
    slipway.py check <app-dir> --only submit   check one phase's rules without moving
    slipway.py status <dir>             every app under <dir> and where it stands

Phases: pick → build → phone → submit → review → live (or retired).
`check` and `status` are offline and read-only. `doctor` runs local, read-only commands; with
--api it also makes one read-only App Store Connect call. Nothing here uploads, submits or
writes to Apple. Standard library only.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import os
import plistlib
import re
import shutil
import struct
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent.parent
TEMPLATES = ROOT / "templates"

PHASES = ["pick", "build", "phone", "submit", "review", "live", "retired"]
RANK = {p: i for i, p in enumerate(PHASES)}
RANK["retired"] = RANK["live"]

APPLE_STATES = {
    "PREPARE_FOR_SUBMISSION", "WAITING_FOR_REVIEW", "IN_REVIEW", "PENDING_DEVELOPER_RELEASE",
    "PENDING_APPLE_RELEASE", "PROCESSING_FOR_APP_STORE", "READY_FOR_SALE", "REJECTED",
    "METADATA_REJECTED", "DEVELOPER_REJECTED", "INVALID_BINARY", "UNRESOLVED_ISSUES",
    "REMOVED_FROM_SALE", "DEVELOPER_REMOVED_FROM_SALE",
}

# Apple screenshot sizes (portrait; landscape is the pair swapped). Checked 2026-10-10:
# https://developer.apple.com/help/app-store-connect/reference/app-information/screenshot-specifications/
SCREENSHOT_SIZES = {
    (1320, 2868): "iPhone 6.9\"", (1290, 2796): "iPhone 6.9\"", (1260, 2736): "iPhone 6.9\"",
    (1284, 2778): "iPhone 6.5\"", (1242, 2688): "iPhone 6.5\"",
    (1206, 2622): "iPhone 6.3\"", (1179, 2556): "iPhone 6.3\"",
    (2064, 2752): "iPad 13\"", (2048, 2732): "iPad 13\"",
}
LARGE_IPHONE = {"iPhone 6.9\"", "iPhone 6.5\""}

NOTES_TOPICS = {
    1: ("device", "record"),
    2: ("purpose", "audience", "business"),
    3: ("setup", "access"),
    4: ("external", "service"),
    5: ("region",),
    6: ("regulated", "material"),
}

# Words that don't, on their own, make an app "meaningfully different" (guideline 4.3(b)).
WEAK_WORDS = {
    "free", "no", "ads", "ad", "ad-free", "tracking", "subscription", "subscriptions", "paywall",
    "paywalls", "account", "accounts", "privacy", "private", "simple", "simply", "clean", "minimal",
    "open", "source", "and", "or", "a", "an", "the", "with", "without", "nothing", "to", "unlock",
    "of", "app", "it", "is", "just", "works", "work", "better", "best", "great", "easy", "fast",
    "beautiful", "really", "very", "that", "for", "you", "your", "all", "in", "on", "one", "more",
    "less", "never", "always", "everything", "anything", "way", "like", "nicer", "good",
}

PRICE_WORDS = re.compile(r"\b(free|\$\d|sale|discount|cheap)\b", re.I)
MARKDOWN = re.compile(r"(\*\*|__|^#{1,6}\s|^\s*[-*]\s\[[ x]\]|`)", re.M)
PLACEHOLDER = re.compile(r"\[[A-Z][A-Z /,.&'-]{3,}\]|<[A-Za-z][^<>\n]{0,40}>|\bTODO\b")
# Template values that mean "not filled in yet".
TEMPLATE_VALUE = re.compile(r"example\.com|com\.example\.|\bexample-|\bExample [A-Z]|\bYYYY\b|\bx\.y\b|iPhone model|"
                            r"not tested|unknown|\bTBD\b", re.I)

PERMISSION_CHECKS = {
    "microphone": ["permissionDenied", "interruptionRecovers"],
    "camera": ["permissionDenied", "interruptionRecovers"],
    "photos": ["permissionDenied"],
    "location": ["permissionDenied"],
    "notifications": ["permissionDenied"],
}


class Report:
    def __init__(self) -> None:
        self.passes: list[str] = []
        self.warnings: list[str] = []
        self.failures: list[str] = []

    def ok(self, cond: bool, good: str, bad: str, warn: bool = False) -> bool:
        if cond:
            self.passes.append(good)
        elif warn:
            self.warnings.append(bad)
        else:
            self.failures.append(bad)
        return cond


# ---------------------------------------------------------------- helpers

def load_json(path: Path | None, r: Report, label: str):
    if path is None:
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        r.failures.append(f"{label}: missing ({path})")
    except Exception as exc:  # noqa: BLE001
        r.failures.append(f"{label}: unreadable ({exc})")
    return None


def https(url: object) -> bool:
    if not isinstance(url, str) or TEMPLATE_VALUE.search(url):
        return False
    p = urlparse(url)
    return p.scheme == "https" and bool(p.netloc)


def words(text: str) -> set[str]:
    return {w for w in re.split(r"[^a-z0-9]+", text.lower()) if w}


def filled(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip()) and not TEMPLATE_VALUE.search(value)


def is_date(value: object) -> bool:
    if not isinstance(value, str):
        return False
    try:
        dt.date.fromisoformat(value[:10])
        return True
    except ValueError:
        return False


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def image_info(path: Path) -> tuple[int, int, bool] | None:
    """(width, height, has_alpha) for PNG or JPEG, else None."""
    data = path.read_bytes()
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        width, height, _depth, color = struct.unpack(">IIBB", data[16:26])
        alpha = color in (4, 6)
        pos = 8
        while pos + 8 <= len(data):
            length, kind = struct.unpack(">I4s", data[pos:pos + 8])
            if kind == b"tRNS":
                alpha = True
            if kind == b"IDAT":
                break
            pos += 12 + length
        return width, height, alpha
    if data[:2] == b"\xff\xd8":
        pos = 2
        while pos + 4 <= len(data):
            if data[pos] != 0xFF:
                pos += 1
                continue
            marker = data[pos + 1]
            if marker in (0xD8, 0x01) or 0xD0 <= marker <= 0xD7:
                pos += 2
                continue
            (length,) = struct.unpack(">H", data[pos + 2:pos + 4])
            if 0xC0 <= marker <= 0xCF and marker not in (0xC4, 0xC8, 0xCC):
                height, width = struct.unpack(">HH", data[pos + 5:pos + 9])
                return width, height, False
            pos += 2 + length
    return None


def movie_duration(path: Path) -> float | None:
    """Duration in seconds of a QuickTime/MP4 file, read from its mvhd atom; None if not a movie."""
    with path.open("rb") as f:
        head = f.read(12)
        if len(head) < 12 or head[4:8] not in (b"ftyp", b"wide", b"mdat", b"moov", b"free"):
            return None
        data = head + f.read()
    i = data.find(b"mvhd")
    if i < 0:
        return None
    version = data[i + 4]
    if version == 1:
        timescale, duration = struct.unpack(">IQ", data[i + 24:i + 36])
    else:
        timescale, duration = struct.unpack(">II", data[i + 16:i + 24])
    return duration / timescale if timescale else None


def numbered_sections(text: str) -> tuple[list[int], dict[int, str]]:
    matches = list(re.finditer(r"(?m)^\s*([1-6])[.)]\s+", text))
    seq = [int(m.group(1)) for m in matches]
    sections = {}
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        sections[int(m.group(1))] = text[m.start():end]
    return seq, sections


def resolve(app_dir: Path, rel: object, r: Report, label: str) -> Path | None:
    if not isinstance(rel, str) or not rel.strip():
        r.failures.append(f"{label}: path not set in app.json")
        return None
    p = Path(rel).expanduser()
    return p if p.is_absolute() else (app_dir / p)


def find_catalog(app_dir: Path, explicit: Path | None) -> Path | None:
    if explicit:
        return explicit
    for d in [app_dir, *app_dir.parents]:
        c = d / "catalog.csv"
        if c.is_file():
            return c
    return None


def scan_placeholders(path: Path, label: str, r: Report) -> str | None:
    if not r.ok(path.is_file(), f"{label} exists", f"{label} not found at {path}"):
        return None
    text = path.read_text(encoding="utf-8")
    left = PLACEHOLDER.findall(text)
    r.ok(not left, f"{label} has no placeholders",
         f"{label} still has placeholders: {', '.join(sorted(set(left))[:5])}")
    return text


# ---------------------------------------------------------------- phase checks

def check_pick(app: dict, app_dir: Path, r: Report, catalog: Path | None) -> None:
    ident = app.get("app", {})
    name = ident.get("storeName", "")
    r.ok(filled(name) and 2 <= len(name) <= 30, "store name is 2-30 characters",
         f"app.storeName must be a real name of 2-30 characters (is {name!r})")

    nc = ident.get("nameCheck") or {}
    if r.ok(filled(nc.get("method")) and is_date(nc.get("at")) and nc.get("result") in ("free", "taken", "unclear"),
            "name check recorded", "app.nameCheck: record how you checked the store name (method, at, result: "
            "free | taken | unclear). A taken name blocks app-record creation on ship day"):
        r.ok(nc["result"] != "taken" or filled(nc.get("fallback")), "taken name has a fallback",
             "nameCheck.result is taken: pick the fallback store name now")
        r.ok(filled(nc.get("fallback")), "fallback store name chosen",
             "nameCheck.fallback: choose a fallback store name now, before icons and screenshots", warn=True)
        if nc.get("method") != "app-store-connect":
            r.warnings.append("name checked by public search only; App Store Connect confirms it when the app "
                              "record is created (phase 4). Keep the fallback ready")

    diff = app.get("differentiation", "")
    r.ok(filled(diff) and len(diff.strip()) >= 20, "differentiation sentence written",
         "differentiation: one sentence on what is meaningfully better (guideline 4.3(b))")
    if filled(diff):
        r.ok(len(words(diff) - WEAK_WORDS) >= 4, "differentiation names a concrete improvement",
             "differentiation leans on price, ads, privacy or filler; name a concrete improvement to the core job",
             warn=True)
    r.ok(isinstance(app.get("incumbents"), list) and bool(app["incumbents"]), "incumbent names listed",
         "incumbents: list the competitor apps so they stay out of your metadata", warn=True)
    idea = resolve(app_dir, app.get("files", {}).get("idea") or "idea.md", r, "files.idea")
    if idea:
        scan_placeholders(idea, "idea.md", r)

    path = find_catalog(app_dir, catalog)
    if not path:
        r.warnings.append(f"no catalog.csv in {app_dir} or any folder above it; keep one at the root of your apps "
                          "folder to check similarity (guideline 4.3)")
        return
    kind = ident.get("kind", "")
    category = ident.get("category", "")
    with path.open(newline="", encoding="utf-8") as f:
        all_rows = list(csv.DictReader(f))
    own = [row for row in all_rows if row.get("slug") == ident.get("slug")]
    if own:
        r.ok(own[0].get("kind") == kind, "catalog kind matches app.json",
             f"catalog says kind {own[0].get('kind')!r}, app.json says {kind!r}; make them agree", warn=True)
    rows = [row for row in all_rows if row.get("slug") != ident.get("slug")]
    active = [row for row in rows if row.get("status") in ("submitted", "review", "in-review", "approved", "live")]
    same_kind = [row["slug"] for row in active if kind and row.get("kind") == kind]
    r.ok(not same_kind, "no active app of the same kind",
         f"catalog: same kind ({kind}) as {', '.join(same_kind)}; consider a mode of that app, or space the submissions",
         warn=True)
    recent = []
    today = dt.date.today()
    for row in rows:
        try:
            when = dt.date.fromisoformat((row.get("submitted") or "")[:10])
        except ValueError:
            continue
        if category and row.get("category") == category and (today - when).days <= 14:
            recent.append(row["slug"])
    r.ok(not recent, "no same-category submission in the last 14 days",
         f"catalog: {', '.join(recent)} went to Apple in the same category ({category}) within 14 days; "
         "space the submissions", warn=True)


SOURCE_PATTERNS = {
    "network": re.compile(r"https?://[^\s\"')]+|URLSession|URLRequest|WKWebView|NWConnection"),
    "links out": re.compile(r"\bopenURL\b|\bLink\(|UIApplication\.shared\.open|SFSafariViewController"),
    "payments": re.compile(r"StoreKit|SKPayment|Product\.products|\bpurchase\(|checkout|underwrit|donat|stripe", re.I),
}
APPLE_HOSTS = re.compile(r"https?://([a-z0-9-]+\.)*(apple\.com|w3\.org)\b", re.I)


def scan_source(app: dict, app_dir: Path, r: Report) -> None:
    """Look through the app's Swift sources (and any shared packages listed) for network calls,
    links out, payments and competitor names, and hold them against the decisions."""
    dirs = app.get("files", {}).get("source") or []
    if isinstance(dirs, str):
        dirs = [dirs]
    if not dirs:
        r.warnings.append("files.source not set: list the app's source folders (and shared packages) so the "
                          "checker can look for network calls, payment links and competitor names")
        return
    found: dict[str, set[str]] = {k: set() for k in SOURCE_PATTERNS}
    names: set[str] = set()
    incumbents = [i.lower() for i in app.get("incumbents", []) if isinstance(i, str) and len(i) > 3]
    for d in dirs:
        root = resolve(app_dir, d, r, "files.source")
        if not root or not r.ok(root.is_dir(), f"source folder {d} found", f"source folder not found: {root}"):
            continue
        for f in root.rglob("*.swift"):
            if "/Tests" in str(f) or "Tests/" in str(f.relative_to(root)):
                continue
            text = f.read_text(encoding="utf-8", errors="ignore")
            for kind, pat in SOURCE_PATTERNS.items():
                for m in pat.finditer(text):
                    if kind == "network" and APPLE_HOSTS.match(m.group(0)):
                        continue
                    found[kind].add(f"{f.name}: {m.group(0)[:60]}")
            low = text.lower()
            names.update(f"{f.name}: {i}" for i in incumbents if i in low)
    dec = app.get("decisions", {})
    r.ok(not found["network"] or dec.get("network") != "none", "no undeclared network calls",
         "decisions.network is 'none' but the source makes network calls: " + "; ".join(sorted(found["network"])[:4]))
    r.ok(not found["payments"] or dec.get("payments") != "none", "no undeclared payment code",
         "decisions.payments is 'none' but the source mentions payments: " + "; ".join(sorted(found["payments"])[:4]))
    if found["links out"]:
        r.warnings.append("the app opens links out (check none of them lead to paying, guideline 3.1.1): "
                          + "; ".join(sorted(found["links out"])[:4]))
    r.ok(not names, "no competitor names in the source", "competitor names in the app's source: " + "; ".join(sorted(names)[:4]))


def check_build(app: dict, app_dir: Path, r: Report) -> None:
    ident = app.get("app", {})
    dec = app.get("decisions", {})
    files = app.get("files", {})
    r.ok(bool(re.fullmatch(r"[A-Za-z0-9-]+(\.[A-Za-z0-9-]+)+", ident.get("bundleId", ""))) and filled(ident.get("bundleId")),
         "bundle ID is set", "app.bundleId must be your real reverse-DNS ID (it can't change after the first upload)")
    r.ok(filled(ident.get("displayName")), "Home Screen name set",
         "app.displayName: the Home Screen name exactly as it should look (CFBundleDisplayName)")
    r.ok(bool(re.fullmatch(r"\d+\.\d+\.\d+", ident.get("version", ""))), "version is x.y.z",
         "app.version must be x.y.z and match App Store Connect exactly")
    r.ok(ident.get("orientation") in ("portrait", "landscape", "both"), "orientation set",
         "app.orientation must be portrait, landscape or both")
    for key, allowed in {
        "privacy": None, "network": None, "signIn": ("none", "required"),
        "contentRights": ("none", "third-party-licensed"), "ageRating": None,
        "releaseType": ("AFTER_APPROVAL", "MANUAL", "SCHEDULED"), "payments": None,
    }.items():
        val = dec.get(key)
        r.ok(filled(val) and (allowed is None or val in allowed), f"decision recorded: {key}",
             f"decisions.{key} missing or invalid" + (f" (one of {', '.join(allowed)})" if allowed else ""))
    for key in ("supportUrl", "privacyUrl"):
        r.ok(https(dec.get(key)), f"{key} set", f"decisions.{key} must be your real HTTPS URL")
    for key in ("network", "payments"):
        val = dec.get(key) or ""
        if val != "none":
            r.ok(len(val) >= 25, f"decisions.{key} explains itself",
                 f"decisions.{key} isn't 'none': say what it does, where it goes, and why it's needed")
    scan_source(app, app_dir, r)

    brief = resolve(app_dir, files.get("brief") or "brief.md", r, "files.brief")
    text = scan_placeholders(brief, "brief", r) if brief else None
    if text is not None:
        r.ok(re.search(r"(?im)^#{2,3}\s+(\d+[.)]\s+)?acceptance (tests|criteria)", text) is not None
             and re.search(r"(?m)^\s*([-*]|\d+[.)])\s+\S", text) is not None,
             "brief has acceptance tests", "brief needs an 'Acceptance tests' section with a list of tests")

    look = app.get("look") or {}
    r.ok(filled(look.get("motif")) and filled(look.get("palette")), "look recorded",
         "look.motif and look.palette: record the icon motif and palette (they go in the catalog)")
    if look.get("new", True):
        r.ok(filled(look.get("approvedAt")), "new look approved",
             "look.approvedAt: a new look needs a human to approve one picture before the build goes far")

    plist_path = resolve(app_dir, files.get("infoPlist"), r, "files.infoPlist")
    if plist_path and r.ok(plist_path.is_file(), "archived Info.plist found", f"Info.plist not found at {plist_path}"):
        if ".xcarchive" not in str(plist_path):
            r.warnings.append("files.infoPlist isn't inside an .xcarchive; point it at the ARCHIVED Info.plist")
        try:
            info = plistlib.loads(plist_path.read_bytes())
        except Exception as exc:  # noqa: BLE001
            r.failures.append(f"Info.plist unreadable: {exc}")
            info = None
        if info is not None:
            def same(key: str, want: str, why: str) -> None:
                got = info.get(key)
                if isinstance(got, str) and got.startswith("$("):
                    r.warnings.append(f"Info.plist {key} is a build variable ({got}); check the ARCHIVED Info.plist")
                else:
                    r.ok(got == want, f"Info.plist {key} matches", f"Info.plist {key} is {got!r}, expected {want!r} ({why})")
            r.ok(info.get("CFBundlePackageType") == "APPL", "CFBundlePackageType is APPL",
                 "Info.plist CFBundlePackageType must be APPL (without it the upload fails processing: ITMS-90183)")
            r.ok(isinstance(info.get("ITSAppUsesNonExemptEncryption"), bool), "export-compliance key present",
                 "Info.plist ITSAppUsesNonExemptEncryption missing (false if you use no or only exempt encryption)")
            same("CFBundleDisplayName", ident.get("displayName", ""), "Home Screen name")
            same("CFBundleShortVersionString", ident.get("version", ""), "must equal the App Store Connect version")
            same("CFBundleVersion", str(ident.get("build", "")), "the archive must be the build in app.json")
            same("CFBundleIdentifier", ident.get("bundleId", ""), "bundle ID")
            for k, v in info.items():
                if k.endswith("UsageDescription"):
                    r.ok(isinstance(v, str) and len(v) >= 20, f"{k} explains itself",
                         f"{k} is too short to explain why the permission is needed")
    manifest = resolve(app_dir, files.get("privacyManifest"), r, "files.privacyManifest")
    if manifest and r.ok(manifest.is_file(), "privacy manifest found", f"PrivacyInfo.xcprivacy not found at {manifest}"):
        try:
            pm = plistlib.loads(manifest.read_bytes())
            if dec.get("privacy") == "data-not-collected":
                r.ok(pm.get("NSPrivacyTracking") is False and not pm.get("NSPrivacyCollectedDataTypes"),
                     "privacy manifest matches Data Not Collected",
                     "privacy manifest declares tracking or collected data, but decisions.privacy is data-not-collected")
        except Exception as exc:  # noqa: BLE001
            r.failures.append(f"privacy manifest unreadable: {exc}")


def check_screenshots(app: dict, app_dir: Path, r: Report) -> None:
    ident = app.get("app", {})
    shots = resolve(app_dir, app.get("files", {}).get("screenshots"), r, "files.screenshots")
    if shots and r.ok(shots.is_dir(), "screenshots folder exists", f"screenshots folder not found at {shots}"):
        by_class: dict[str, int] = {}
        orientation = ident.get("orientation", "portrait")
        for img in sorted(p for p in shots.iterdir() if p.suffix.lower() in (".png", ".jpg", ".jpeg")):
            info = image_info(img)
            if not info:
                r.failures.append(f"screenshot {img.name}: not a readable PNG/JPEG")
                continue
            w, h, alpha = info
            portrait, landscape = (w, h) in SCREENSHOT_SIZES, (h, w) in SCREENSHOT_SIZES
            if not r.ok(portrait or landscape, f"{img.name} size accepted", f"screenshot {img.name} is {w}x{h}, not an App Store size"):
                continue
            r.ok(not alpha, f"{img.name} has no alpha",
                 f"screenshot {img.name} has an alpha channel; convert it: sips -s format jpeg {img.name} --out {img.stem}.jpg")
            if orientation == "portrait":
                r.ok(portrait, f"{img.name} portrait", f"screenshot {img.name} is landscape but the app is portrait")
            elif orientation == "landscape":
                r.ok(landscape, f"{img.name} landscape", f"screenshot {img.name} is portrait but the app is landscape")
            cls = SCREENSHOT_SIZES[(w, h) if portrait else (h, w)]
            by_class[cls] = by_class.get(cls, 0) + 1
        r.ok(any(c in LARGE_IPHONE for c in by_class), "6.9\" or 6.5\" iPhone screenshots present",
             "no 6.9\" (1320x2868) or 6.5\" iPhone screenshots; add a 6.9\" set")
        r.ok(all(n <= 10 for n in by_class.values()), "at most 10 per size", "more than 10 screenshots for one size")
        r.ok(sum(n for c, n in by_class.items() if c.startswith("iPhone")) >= 3, "three or more iPhone screenshots",
             "fewer than three iPhone screenshots", warn=True)


def check_phone(app: dict, app_dir: Path, r: Report) -> None:
    ident = app.get("app", {})
    path = resolve(app_dir, app.get("files", {}).get("deviceCheck"), r, "files.deviceCheck")
    dc = load_json(path, r, "device check")
    if dc is None:
        return
    build = str(ident.get("build", ""))
    carry = dc.get("carryForward") or {}
    if str(dc.get("build")) == build:
        r.passes.append("device check is on the build in app.json")
    elif str(carry.get("toBuild")) == build and filled(carry.get("why")):
        r.warnings.append(f"device check was on build {dc.get('build')}, carried to {build}: {carry['why']} "
                          "(re-run launch and the core flow on the new build if you can)")
    else:
        r.failures.append(f"device check is for build {dc.get('build')!r}, app.build is {build!r}; re-check, or add "
                          "carryForward {toBuild, why} if the change can't affect behavior")
    r.ok(filled(dc.get("device")), "device recorded", "device check: record the real device model")
    r.ok(filled(dc.get("osVersion")), "iOS version recorded", "device check: record the real iOS version")
    r.ok(is_date(dc.get("testedAt")), "test date recorded", "device check: testedAt must be a real date")
    r.ok(dc.get("observedBy") in ("human", "agent"), "observer recorded",
         "device check: observedBy must be human or agent (some checks need a person)")
    checks = dc.get("checks", {})
    required = ["launchFromHomeScreen", "coreFlow", "relaunchKeepsData", "voiceOverCoreFlow", "largestTextSize"]
    if ident.get("audio"):
        required += ["audioThroughSpeaker", "audioWhenLocked", "interruptionRecovers"]
    for perm in ident.get("permissions", []) or []:
        required += PERMISSION_CHECKS.get(perm, ["permissionDenied"])
    for key in dict.fromkeys(required):
        r.ok(checks.get(key) == "pass", f"phone: {key} passes", f"device check '{key}' is {checks.get(key)!r}, needs 'pass'")

    video = dc.get("video") or {}
    vpath = resolve(path.parent, video.get("file"), r, "device check video.file")
    if vpath and r.ok(vpath.is_file(), "recording exists", f"screen recording not found at {vpath}"):
        r.ok(video.get("sha256") == sha256(vpath), "recording hash matches", "video.sha256 doesn't match the file")
        seconds = movie_duration(vpath)
        if r.ok(seconds is not None, "recording is a real movie file", f"{vpath.name} isn't a QuickTime/MP4 movie"):
            r.ok(5 <= seconds <= 180, f"recording is {seconds:.0f}s", f"recording is {seconds:.0f}s; keep it 5-180s")
    r.ok(video.get("startsOnHomeScreen") is True, "recording starts on the Home Screen",
         "video.startsOnHomeScreen must be true (Apple asks to see the launch)")
    if ident.get("audio"):
        r.ok(video.get("hasAudio") is True, "recording has sound",
             "this app plays sound but the recording is silent; record on the phone with the mic on", warn=True)
    check_screenshots(app, app_dir, r)


def load_listing(app: dict, app_dir: Path, r: Report) -> dict | None:
    """store/metadata in asc's layout (app-info/<locale>.json + version/<version>/<locale>.json),
    or a single listing.json via files.listing."""
    files = app.get("files", {})
    if files.get("listing"):
        return load_json(resolve(app_dir, files["listing"], r, "files.listing"), r, "listing")
    root = resolve(app_dir, files.get("metadataDir"), r, "files.metadataDir")
    if not root:
        return None
    locale = app.get("app", {}).get("locale", "en-US")
    version = app.get("app", {}).get("version", "")
    info = load_json(root / "app-info" / f"{locale}.json", r, "metadata app-info")
    ver = load_json(root / "version" / version / f"{locale}.json", r, f"metadata version {version}")
    if info is None or ver is None:
        return None
    listing = {**ver, **info}
    listing.setdefault("privacyUrl", info.get("privacyPolicyUrl", ""))
    listing.setdefault("copyright", app.get("decisions", {}).get("copyright", ""))
    return listing


def check_text_file(path: Path, label: str, r: Report) -> dict[int, str] | None:
    try:
        raw = path.read_bytes()
        text = raw.decode("utf-8")
    except FileNotFoundError:
        r.failures.append(f"{label}: missing ({path})")
        return None
    r.ok(len(raw) <= 4000, f"{label} within 4,000 bytes",
         f"{label} is {len(raw)} bytes; Apple's limit is 4,000 bytes (curly quotes and dashes count extra)")
    r.ok(not MARKDOWN.search(text), f"{label} is plain text", f"{label} has Markdown; App Store Connect shows it literally")
    left = PLACEHOLDER.findall(text) + TEMPLATE_VALUE.findall(text)
    r.ok(not left, f"{label} has no placeholders", f"{label} still has placeholders: {', '.join(sorted(set(left))[:4])}")
    seq, sections = numbered_sections(text)
    if not r.ok(seq == [1, 2, 3, 4, 5, 6], f"{label} has the six numbered answers",
                f"{label} must have answers numbered 1-6, once each, in order"):
        return None
    for n, terms in NOTES_TOPICS.items():
        missing = [t for t in terms if t not in sections[n].lower()]
        r.ok(not missing, f"{label} answer {n} on topic", f"{label} answer {n} should mention: {', '.join(missing)}", warn=True)
    return sections


def check_submit(app: dict, app_dir: Path, r: Report) -> None:
    ident = app.get("app", {})
    files = app.get("files", {})
    incumbents = [i for i in app.get("incumbents", []) if isinstance(i, str) and i.strip()]
    listing = load_listing(app, app_dir, r)
    if listing:
        name, sub = listing.get("name", ""), listing.get("subtitle", "")
        r.ok(name == ident.get("storeName"), "listing name matches app.storeName",
             f"listing name {name!r} differs from app.storeName {ident.get('storeName')!r}")
        r.ok(len(sub) <= 30, "subtitle within 30 characters", f"subtitle is {len(sub)} characters (max 30)")
        desc = listing.get("description", "")
        r.ok(0 < len(desc) <= 4000, "description 1-4,000 characters", "description must be 1-4,000 characters")
        r.ok(len(listing.get("promotionalText", "")) <= 170, "promotional text within 170", "promotional text over 170 characters")
        kw = listing.get("keywords", "")
        r.ok(0 < len(kw.encode("utf-8")) <= 100, "keywords within 100 bytes", f"keywords are {len(kw.encode('utf-8'))} bytes (1-100)")
        dup = sorted({k.strip().lower() for k in kw.split(",") if k.strip()} & (words(name) | words(sub)))
        r.ok(not dup, "keywords don't repeat the name", f"keywords repeat name/subtitle words (wasted space): {', '.join(dup)}", warn=True)
        r.ok(not (PRICE_WORDS.search(name) or PRICE_WORDS.search(sub)), "no price words in name/subtitle",
             "name or subtitle mentions price (guideline 2.3.7)", warn=True)
        for field in ("supportUrl", "privacyUrl"):
            r.ok(https(listing.get(field)), f"listing {field} set", f"listing {field} must be your real HTTPS URL")
            r.ok(listing.get(field) == app.get("decisions", {}).get(field), f"listing {field} matches decisions",
                 f"listing {field} differs from decisions.{field}", warn=True)
        r.ok(filled(listing.get("copyright")), "copyright set", "copyright missing")
        blob = " ".join(str(listing.get(k, "")) for k in ("name", "subtitle", "keywords", "description", "promotionalText")).lower()
        hits = [i for i in incumbents if i.lower() in blob]
        r.ok(not hits, "no competitor names in metadata", f"competitor names in metadata (guidelines 2.3.7, 4.1): {', '.join(hits)}")

    notes_path = resolve(app_dir, files.get("reviewNotes"), r, "files.reviewNotes")
    notes = check_text_file(notes_path, "review notes", r) if notes_path else None
    reply_path = resolve(app_dir, files.get("reviewReply"), r, "files.reviewReply")
    reply = check_text_file(reply_path, "review reply", r) if reply_path else None
    if notes and reply:
        def first_para(s: str) -> str:
            return re.sub(r"\s+", " ", re.split(r"\n\s*\n", s.strip())[0]).strip()
        differ = [n for n in (3, 4, 6) if first_para(notes[n]) != first_para(reply[n])]
        r.ok(not differ, "reply matches the notes", f"reply answers {differ} differ from the notes; they must say the same "
             "thing (copy the notes into the reply)", warn=True)
    if notes:
        text = " ".join(notes.values()).lower()
        hits = [i for i in incumbents if i.lower() in text]
        r.ok(not hits, "no competitor names in review notes", f"competitor names in review notes: {', '.join(hits)}", warn=True)



def check_review(app: dict, r: Report) -> None:
    apple = app.get("apple", {})
    r.ok(bool(re.fullmatch(r"\d{9,12}", str(apple.get("appId", "")))), "Apple app ID recorded",
         "apple.appId: the numeric Apple ID of the app record")
    r.ok(apple.get("state") in APPLE_STATES, "Apple state recorded",
         f"apple.state must be one of Apple's states as read back (e.g. WAITING_FOR_REVIEW), not {apple.get('state')!r}")
    r.ok(is_date(apple.get("checkedAt")), "Apple state read date recorded", "apple.checkedAt: when you last read Apple's state")


PHASE_CHECKS = ["pick", "build", "phone", "submit", "review"]


def check_urls_online(app: dict, r: Report) -> None:
    import urllib.request
    for key in ("supportUrl", "privacyUrl"):
        url = app.get("decisions", {}).get(key)
        if not https(url):
            continue
        try:
            req = urllib.request.Request(url, method="GET", headers={"User-Agent": "slipway-check"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                r.ok(resp.status == 200, f"{key} answers 200", f"{key} {url} answered {resp.status}")
        except Exception as exc:  # noqa: BLE001
            r.failures.append(f"{key} {url} didn't load: {exc}")


def check(app_dir: Path, catalog: Path | None, only: str | None = None, online: bool = False) -> dict:
    r = Report()
    app = load_json(app_dir / "app.json", r, "app.json")
    if app is None:
        return {"status": "blocked", "phase": None, "passes": [], "warnings": [], "failures": r.failures}
    phase = app.get("phase", app.get("stage"))
    if phase not in RANK:
        r.failures.append(f"phase must be one of: {', '.join(PHASES)}")
        return {"status": "blocked", "phase": phase, "passes": [], "warnings": [], "failures": r.failures}
    run = [only] if only else [p for p in PHASE_CHECKS if RANK[p] <= RANK[phase]]
    for p in run:
        if p == "pick":
            check_pick(app, app_dir, r, catalog)
        elif p == "build":
            check_build(app, app_dir, r)
        elif p == "phone":
            check_phone(app, app_dir, r)
        elif p == "submit":
            check_submit(app, app_dir, r)
            if online:
                check_urls_online(app, r)
            else:
                r.warnings.append("support and privacy URLs not loaded (offline check); run with --online before submitting")
        elif p == "review":
            check_review(app, r)
    return {"status": "ready" if not r.failures else "blocked", "phase": phase, "checked": run,
            "passes": r.passes, "warnings": r.warnings, "failures": r.failures}


# ---------------------------------------------------------------- doctor

def run_cmd(args: list[str], timeout: int = 30) -> tuple[int, str]:
    try:
        p = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
        return p.returncode, (p.stdout + p.stderr).strip()
    except FileNotFoundError:
        return 127, "not installed"
    except subprocess.TimeoutExpired:
        return 124, "timed out"


def list_phones() -> list[dict] | None:
    """Physical iPhones from devicectl's JSON (Xcode 15-27 field names). None if devicectl failed."""
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        out = Path(d) / "devices.json"
        run_cmd(["xcrun", "devicectl", "list", "devices", "--json-output", str(out)], timeout=60)
        if not out.is_file():
            return None
        try:
            doc = json.loads(out.read_text())
        except Exception:  # noqa: BLE001
            return None
    if doc.get("info", {}).get("outcome") != "success":
        return None
    phones = []
    for dev in doc.get("result", {}).get("devices", []):
        props = dev.get("properties", {})
        hw = props.get("hardware") or dev.get("hardwareProperties", {})
        conn = props.get("connection") or dev.get("connectionProperties", {})
        dm = (props.get("state") or {}).get("developerModeStatus")
        if dm is None:
            dm = dev.get("deviceProperties", {}).get("developerModeStatus")
        if hw.get("platform") != "iOS" or hw.get("reality") != "physical" or hw.get("deviceType", "iPhone") != "iPhone":
            continue
        os_version = ((props.get("software") or {}).get("osVersionNumber") or {}).get("stringValue") \
            or dev.get("deviceProperties", {}).get("osVersionNumber", "?")
        phones.append({
            "model": hw.get("marketingName") or hw.get("productType") or "iPhone",
            "os": os_version,
            "paired": conn.get("pairingState") == "paired",
            "transport": conn.get("transportType"),
            "devMode": (isinstance(dm, dict) and "enabled" in dm) or dm == "enabled",
        })
    return phones


def doctor(api: bool) -> dict:
    r = Report()
    code, out = run_cmd(["xcodebuild", "-version"])
    m = re.search(r"Xcode (\d+)", out)
    r.ok(code == 0 and m and int(m.group(1)) >= 26, f"Xcode {m.group(1) if m else '?'} installed",
         "Xcode 26 or newer is required to upload (since April 28, 2026)")
    code, out = run_cmd(["xcode-select", "-p"])
    r.ok(code == 0 and "Xcode" in out, "Xcode command-line tools point at Xcode",
         f"xcode-select points at {out!r}; run: sudo xcode-select -s /Applications/Xcode.app")

    asc = shutil.which("asc")
    if r.ok(bool(asc), "asc CLI installed", "asc not found: brew install asc (or use fastlane)", warn=True):
        _, out = run_cmd([asc, "--version"])
        v = re.match(r"(\d+)\.(\d+)", out)
        r.ok(bool(v) and (int(v.group(1)), int(v.group(2))) >= (5, 9), f"asc {out.split()[0] if out else '?'}",
             f"asc {out[:20]!r} is older than 5.9; the commands in these docs were checked on 5.9+", warn=True)
    have_env = all(os.environ.get(k) for k in ("ASC_KEY_ID", "ASC_ISSUER_ID", "ASC_PRIVATE_KEY_PATH"))
    r.ok(have_env, "API key variables set", "ASC_KEY_ID / ASC_ISSUER_ID / ASC_PRIVATE_KEY_PATH not set in this shell "
         "(run doctor through your wrapper, e.g. asc-env, or export them)", warn=True)
    key = os.environ.get("ASC_PRIVATE_KEY_PATH")
    if key:
        kp = Path(key).expanduser()
        if r.ok(kp.is_file(), "API private key file exists", f"ASC_PRIVATE_KEY_PATH points at a missing file"):
            r.ok(kp.stat().st_mode & 0o077 == 0, "API key file is private (chmod 600)",
                 f"{kp.name} is readable by others: chmod 600 it", warn=True)
    if api and asc and have_env:
        code, out = run_cmd([asc, "apps", "list", "--limit", "1"], timeout=60)
        r.ok(code == 0, "App Store Connect API answers (read-only)", f"API read failed: {out[:200]}")

    code, out = run_cmd(["security", "find-identity", "-v", "-p", "codesigning"])
    n = re.search(r"(\d+) valid identities found", out)
    r.ok(code == 0 and n and int(n.group(1)) > 0, f"{n.group(1) if n else 0} code-signing identities in the keychain",
         "no code-signing identity: sign in under Xcode > Settings > Accounts once, or let automatic signing create one",
         warn=True)
    code, out = run_cmd(["security", "show-keychain-info"])
    r.ok(code == 0, "default keychain information is readable (not a signing probe)",
         "default keychain information unavailable; inspect the configured signing keychain", warn=True)

    phones = list_phones()
    if r.ok(phones is not None and bool(phones), f"{len(phones or [])} iPhone(s) known to this Mac",
            "device discovery failed or returned no iPhone; pairing and reachability are unverified", warn=True):
        best = max(phones, key=lambda p: (bool(p["transport"]), p["paired"], p["devMode"]))
        r.ok(best["paired"], "iPhone is paired", "iPhone not paired: cable in, unlock, tap Trust, then Pair in Xcode", warn=True)
        r.ok(best["devMode"], "Developer Mode is on",
             "Developer Mode is off: Settings > Privacy & Security > Developer Mode, then restart", warn=True)
        r.ok(bool(best["transport"]), f"{best['model']} reports transport {best['transport']} (iOS {best['os']}); verify with a device operation",
             f"{best['model']} (iOS {best['os']}) has no reported transport; diagnose availability before requesting USB", warn=True)

    code, out = run_cmd(["xcrun", "devicectl", "device", "capture", "--help"])
    r.ok(code == 0 and "screen-record" in out, "devicectl advertises screen-record; device support and recording consent remain unverified",
         "this Xcode has no devicectl screen recorder; use the phone's own recorder or QuickTime", warn=True)
    r.ok(Path("/System/Applications/QuickTime Player.app").exists() or Path("/Applications/QuickTime Player.app").exists(),
         "QuickTime Player present (USB screen recording)", "QuickTime Player missing", warn=True)
    r.ok(Path("/System/Applications/iPhone Mirroring.app").exists(), "iPhone Mirroring present",
         "iPhone Mirroring not available on this Mac", warn=True)
    if not have_env:
        r.warnings.append("can't confirm you're ready to submit until the API key checks run (use your wrapper's shell)")
    return {"status": "blocked" if r.failures else "incomplete" if r.warnings else "local-checks-pass", "passes": r.passes,
            "warnings": r.warnings, "failures": r.failures}


# ---------------------------------------------------------------- commands

def cmd_new(target: Path) -> int:
    if target.exists() and any(target.iterdir()):
        print(f"{target} exists and isn't empty; not overwriting", file=sys.stderr)
        return 1
    shutil.copytree(TEMPLATES / "app", target, dirs_exist_ok=True)
    print(f"Started {target}.\nNext: fill in idea.md and app.json (phase 1, Pick), then run:\n"
          f"  python3 {Path(__file__).resolve()} check {target}")
    return 0


def cmd_status(root: Path) -> int:
    rows = []
    for path in sorted(root.rglob("app.json")):
        try:
            app = json.loads(path.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            continue
        if "slipway" not in app:
            continue
        rows.append((app.get("app", {}).get("storeName") or path.parent.name, app.get("phase", app.get("stage", "?")),
                     app.get("apple", {}).get("state", ""), app.get("next", "")))
    if not rows:
        print("No Slipway apps found.")
        return 0
    width = max(len(r[0]) for r in rows)
    for name, phase, state, nxt in rows:
        print(f"{name:<{width}}  {phase:<8} {state:<22} {nxt}")
    return 0


def print_report(report: dict, title: str) -> None:
    label = 'CHECKS PASS' if report['status'] == 'ready' else report['status'].upper()
    print(f"{label}  {title}")
    for f in report["failures"]:
        print(f"  ✗ {f}")
    for w in report["warnings"]:
        print(f"  ! {w}")
    print(f"  {len(report['passes'])} checks passed")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)
    p_doc = sub.add_parser("doctor", help="check this Mac and phone are ready")
    p_doc.add_argument("--api", action="store_true", help="also make one read-only App Store Connect API call")
    p_doc.add_argument("--json", action="store_true")
    p_new = sub.add_parser("new", help="start an app folder from the templates")
    p_new.add_argument("dir", type=Path)
    p_check = sub.add_parser("check", help="check an app folder against its phase")
    p_check.add_argument("dir", type=Path)
    p_check.add_argument("--only", choices=PHASE_CHECKS, help="run one phase's rules without moving the app")
    p_check.add_argument("--catalog", type=Path, help="catalog.csv (default: nearest one above the app folder)")
    p_check.add_argument("--online", action="store_true", help="also load the support and privacy URLs")
    p_check.add_argument("--json", action="store_true")
    p_status = sub.add_parser("status", help="list apps and phases under a folder")
    p_status.add_argument("dir", type=Path)
    args = parser.parse_args(argv)

    if args.cmd == "new":
        return cmd_new(args.dir.expanduser())
    if args.cmd == "status":
        return cmd_status(args.dir.expanduser())
    if args.cmd == "doctor":
        report = doctor(args.api)
        print(json.dumps(report, indent=2)) if args.json else print_report(report, "(this Mac)")
        return 0 if report["status"] == "local-checks-pass" else 1
    report = check(args.dir.expanduser().resolve(), args.catalog, args.only, args.online)
    title = f"(phase: {report['phase']}" + (f", only {args.only})" if args.only else ")")
    print(json.dumps(report, indent=2)) if args.json else print_report(report, title)
    return 0 if report["status"] == "ready" else 1


if __name__ == "__main__":
    sys.exit(main())
