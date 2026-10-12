import contextlib
import hashlib
import io
import json
import plistlib
import shutil
import struct
import sys
import tempfile
import unittest
import zlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import slipway  # noqa: E402

TEMPLATES = Path(__file__).resolve().parent.parent / "templates"


def png(path: Path, width: int, height: int, alpha: bool = False) -> None:
    color, channels = (6, 4) if alpha else (2, 3)

    def chunk(kind: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))

    raw = b"".join(b"\x00" + b"\x00" * (width * channels) for _ in range(height))
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, color, 0, 0, 0))
                     + chunk(b"IDAT", zlib.compress(raw, 1)) + chunk(b"IEND", b""))


def movie(path: Path, seconds: int) -> None:
    """A minimal QuickTime file: ftyp + moov/mvhd with the given duration."""
    ftyp = struct.pack(">I4s4sI4s", 20, b"ftyp", b"qt  ", 0, b"qt  ")
    mvhd_body = struct.pack(">B3sIIII", 0, b"\0\0\0", 0, 0, 600, 600 * seconds) + b"\0" * 80
    mvhd = struct.pack(">I4s", 8 + len(mvhd_body), b"mvhd") + mvhd_body
    moov = struct.pack(">I4s", 8 + len(mvhd), b"moov") + mvhd
    path.write_bytes(ftyp + moov)


NOTES = """1. Physical-device testing and recording
Build 1.0.0 (3) was tested on an iPhone 17 running iOS 26.1. The attached recording starts on the Home Screen.

2. Purpose, target audience, and business model
Tally Board is a counter for anyone keeping score. Business model: free.

3. Setup and access
No setup or login is needed to access anything.

4. External services
The app uses no external services.

5. Regional differences
The same in every region.

6. Regulated activity and protected material
Not regulated. All material is original.
"""


class SlipwayTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        self.app_dir = self.tmp / "tally-board"
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(slipway.main(["new", str(self.app_dir)]), 0)
        self.make_ready()

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp)

    # A complete app, ready to submit.
    def make_ready(self) -> None:
        d = self.app_dir
        app = json.loads((d / "app.json").read_text())
        app["phase"] = "submit"
        app["app"].update(slug="tally-board", storeName="Tally Board", displayName="Tally Board",
                          bundleId="com.studio.tallyboard", sku="tally-board", build="3",
                          nameCheck={"method": "app-store-connect", "at": "2026-10-01", "result": "free",
                                     "fallback": "Tally Board: Counter"})
        app["differentiation"] = "Counters open ready, survive restarts, and step with haptics one-handed in a pocket."
        app["incumbents"] = ["Count That Fast"]
        app["decisions"].update(supportUrl="https://studio.dev/tally-board/support/",
                                privacyUrl="https://studio.dev/tally-board/privacy/", copyright="2026 Studio")
        app["look"] = {"new": True, "motif": "stacked tally marks", "palette": "paper and rust", "approvedAt": "2026-10-01"}
        app["files"]["infoPlist"] = "build/3/App.xcarchive/Info.plist"
        app["files"]["privacyManifest"] = "PrivacyInfo.xcprivacy"
        (d / "app.json").write_text(json.dumps(app))

        (d / "idea.md").write_text("# Idea: Tally Board\n\nPeople want to count without a paywall.\n")
        (d / "Sources").mkdir()
        (d / "Sources/App.swift").write_text("struct Counter { var count = 0 }\n")
        brief = (TEMPLATES / "app/brief.md").read_text().replace("[APP NAME]", "Tally Board").replace("[APPETITE]", "two days")
        (d / "brief.md").write_text(brief)

        meta = d / "store/metadata"
        (meta / "app-info/en-US.json").write_text(json.dumps(
            {"name": "Tally Board", "subtitle": "Count anything, one tap", "privacyPolicyUrl": "https://studio.dev/tally-board/privacy/"}))
        (meta / "version/1.0.0/en-US.json").write_text(json.dumps(
            {"description": "Tally Board opens ready to count.", "keywords": "clicker,inventory,habit,score",
             "supportUrl": "https://studio.dev/tally-board/support/"}))

        (d / "build/3/App.xcarchive").mkdir(parents=True)
        self.info = {
            "CFBundlePackageType": "APPL", "CFBundleDisplayName": "Tally Board", "CFBundleVersion": "3",
            "CFBundleShortVersionString": "1.0.0", "CFBundleIdentifier": "com.studio.tallyboard",
            "ITSAppUsesNonExemptEncryption": False,
        }
        self.write_info()
        shutil.copy(TEMPLATES / "ios/PrivacyInfo.xcprivacy", d / "PrivacyInfo.xcprivacy")

        video = d / "store/device-demo.mov"
        movie(video, 24)
        dc = json.loads((d / "store/device-check.json").read_text())
        dc.update(build="3", device="iPhone 17", osVersion="iOS 26.1", testedAt="2026-10-02", observedBy="human")
        for k in ("launchFromHomeScreen", "coreFlow", "relaunchKeepsData", "voiceOverCoreFlow", "largestTextSize"):
            dc["checks"][k] = "pass"
        dc["video"].update(sha256=hashlib.sha256(video.read_bytes()).hexdigest(), startsOnHomeScreen=True)
        (d / "store/device-check.json").write_text(json.dumps(dc))

        (d / "store/review-notes.txt").write_text(NOTES)
        (d / "store/review-reply.txt").write_text("Hello App Review,\n\n" + NOTES + "\nThank you.\n")
        for i in range(3):
            png(d / f"store/screenshots/0{i}.png", 1320, 2868)

    def write_info(self) -> None:
        (self.app_dir / "build/3/App.xcarchive/Info.plist").write_bytes(plistlib.dumps(self.info))

    def check(self, only=None) -> dict:
        return slipway.check(self.app_dir, None, only)

    def edit(self, rel: str, fn) -> None:
        p = self.app_dir / rel
        data = json.loads(p.read_text())
        fn(data)
        p.write_text(json.dumps(data))

    def failing(self, needle: str, only=None) -> bool:
        return any(needle in f for f in self.check(only)["failures"])

    def warning(self, needle: str) -> bool:
        return any(needle in w for w in self.check()["warnings"])

    def test_complete_app_is_ready(self) -> None:
        report = self.check()
        self.assertEqual(report["failures"], [])
        self.assertEqual(report["status"], "ready")

    # pick
    def test_name_check_required(self) -> None:
        self.edit("app.json", lambda a: a["app"].update(nameCheck={}))
        self.assertTrue(self.failing("nameCheck"))

    def test_public_search_name_check_warns(self) -> None:
        self.edit("app.json", lambda a: a["app"]["nameCheck"].update(method="public-search"))
        self.assertTrue(self.warning("public search"))

    def test_weak_differentiation_warns(self) -> None:
        self.edit("app.json", lambda a: a.update(differentiation="A free counter with no ads that just works."))
        self.assertTrue(self.warning("filler"))

    def test_idea_placeholders_block(self) -> None:
        (self.app_dir / "idea.md").write_text("# Idea: [APP NAME]\n")
        self.assertTrue(self.failing("idea.md still has placeholders"))

    def test_catalog_same_kind_and_recent_category_warn(self) -> None:
        import datetime as dt
        today = dt.date.today().isoformat()
        (self.tmp / "catalog.csv").write_text(
            "slug,store_name,category,kind,core_job,motif,palette,status,submitted,notes\n"
            f"other,Other Counter,UTILITIES,counter,count,tally,grey,submitted,{today},\n")
        warnings = self.check()["warnings"]
        self.assertTrue(any("same kind" in w for w in warnings))
        self.assertTrue(any("within 14 days" in w for w in warnings))

    # build
    def test_template_values_block(self) -> None:
        self.edit("app.json", lambda a: a["decisions"].update(supportUrl="https://example.com/x/support/"))
        self.assertTrue(self.failing("supportUrl"))

    def test_missing_package_type_blocks(self) -> None:
        del self.info["CFBundlePackageType"]
        self.write_info()
        self.assertTrue(self.failing("ITMS-90183"))

    def test_wrong_archive_build_blocks(self) -> None:
        self.info["CFBundleVersion"] = "1"
        self.write_info()
        self.assertTrue(self.failing("CFBundleVersion"))

    def test_display_name_mismatch_blocks(self) -> None:
        self.info["CFBundleDisplayName"] = "TallyBoard"
        self.write_info()
        self.assertTrue(self.failing("CFBundleDisplayName"))

    def test_existing_look_needs_no_approval(self) -> None:
        self.edit("app.json", lambda a: a["look"].update(new=False, approvedAt=""))
        self.assertEqual(self.check()["failures"], [])
        self.edit("app.json", lambda a: a["look"].update(new=True))
        self.assertTrue(self.failing("approvedAt"))

    def test_numbered_acceptance_criteria_heading_accepted(self) -> None:
        (self.app_dir / "brief.md").write_text("# Brief\n\n## 7. Acceptance criteria\n\n1. Launch shows the board.\n")
        self.assertFalse(self.failing("Acceptance"))

    # phone
    def test_fake_movie_blocks(self) -> None:
        video = self.app_dir / "store/device-demo.mov"
        video.write_bytes(b"not a movie at all")
        self.edit("store/device-check.json", lambda d: d["video"].update(sha256=hashlib.sha256(video.read_bytes()).hexdigest()))
        self.assertTrue(self.failing("isn't a QuickTime"))

    def test_long_movie_blocks(self) -> None:
        video = self.app_dir / "store/device-demo.mov"
        movie(video, 240)
        self.edit("store/device-check.json", lambda d: d["video"].update(sha256=hashlib.sha256(video.read_bytes()).hexdigest()))
        self.assertTrue(self.failing("keep it 5-180s"))

    def test_template_device_values_block(self) -> None:
        self.edit("store/device-check.json", lambda d: d.update(device="iPhone model", testedAt="YYYY-MM-DD"))
        failures = self.check()["failures"]
        self.assertTrue(any("device model" in f for f in failures))
        self.assertTrue(any("testedAt" in f for f in failures))

    def test_other_build_blocks_unless_carried(self) -> None:
        self.edit("store/device-check.json", lambda d: d.update(build="2"))
        self.assertTrue(self.failing("device check is for build"))
        self.edit("store/device-check.json", lambda d: d.update(carryForward={"toBuild": "3", "why": "only the name changed"}))
        self.assertFalse(self.failing("device check is for build"))
        self.assertTrue(self.warning("carried to 3"))

    def test_audio_and_permission_checks(self) -> None:
        self.edit("app.json", lambda a: a["app"].update(audio=True, permissions=["microphone"]))
        failures = self.check()["failures"]
        self.assertTrue(any("audioWhenLocked" in f for f in failures))
        self.assertTrue(any("permissionDenied" in f for f in failures))
        self.assertTrue(self.warning("recording is silent"))

    # submit
    def test_competitor_name_in_metadata_blocks(self) -> None:
        p = "store/metadata/version/1.0.0/en-US.json"
        self.edit(p, lambda m: m.update(description="Better than Count That Fast."))
        self.assertTrue(self.failing("competitor"))

    def test_keywords_over_100_bytes_block(self) -> None:
        self.edit("store/metadata/version/1.0.0/en-US.json", lambda m: m.update(keywords="x" * 101))
        self.assertTrue(self.failing("keywords"))

    def test_markdown_and_byte_limit_in_notes(self) -> None:
        (self.app_dir / "store/review-notes.txt").write_text(NOTES.replace("Physical-device", "**Physical-device**") + "–" * 2000)
        failures = self.check()["failures"]
        self.assertTrue(any("Markdown" in f for f in failures))
        self.assertTrue(any("4,000" in f for f in failures))

    def test_reply_must_match_notes(self) -> None:
        (self.app_dir / "store/review-reply.txt").write_text(
            "Hello,\n\n" + NOTES.replace("The app uses no external services.", "The app fetches a feed from studio.dev."))
        self.assertTrue(self.warning("differ from the notes"))

    def test_small_screenshots_only_block(self) -> None:
        for p in (self.app_dir / "store/screenshots").glob("*.png"):
            p.unlink()
        for i in range(3):
            png(self.app_dir / f"store/screenshots/0{i}.png", 1206, 2622)
        self.assertTrue(self.failing("6.9"))

    def test_alpha_and_orientation(self) -> None:
        png(self.app_dir / "store/screenshots/09.png", 2868, 1320, alpha=True)
        failures = self.check()["failures"]
        self.assertTrue(any("alpha" in f for f in failures))
        self.assertTrue(any("landscape but the app is portrait" in f for f in failures))

    def test_only_runs_one_phase(self) -> None:
        self.edit("app.json", lambda a: a.update(phase="phone"))
        (self.app_dir / "store/review-notes.txt").write_text("not numbered")
        self.assertFalse(self.failing("numbered 1-6"))
        self.assertTrue(self.failing("numbered 1-6", only="submit"))

    # review
    def test_review_needs_real_apple_state(self) -> None:
        self.edit("app.json", lambda a: a.update(phase="review"))
        self.edit("app.json", lambda a: a["apple"].update(appId="1234567890", state="waiting", checkedAt="2026-10-03"))
        self.assertTrue(self.failing("apple.state"))
        self.edit("app.json", lambda a: a["apple"].update(state="WAITING_FOR_REVIEW"))
        self.assertEqual(self.check()["failures"], [])

    def test_fresh_app_does_not_pass(self) -> None:
        fresh = self.tmp / "fresh"
        with contextlib.redirect_stdout(io.StringIO()):
            slipway.main(["new", str(fresh)])
        p = fresh / "app.json"
        a = json.loads(p.read_text())
        a["phase"] = "submit"
        p.write_text(json.dumps(a))
        self.assertGreater(len(slipway.check(fresh, None)["failures"]), 10)

    # source scan (the dry-run Bench case)
    def write_source(self, swift: str) -> None:
        src = self.app_dir / "Sources"
        src.mkdir(exist_ok=True)
        (src / "Bench.swift").write_text(swift)
        self.edit("app.json", lambda a: a["files"].update(source=["Sources"]))

    def test_undeclared_network_and_payments_block(self) -> None:
        self.write_source('let feed = URL(string: "https://home.example.net/api/bench")!\n'
                          'Link("Underwrite this feature", destination: payURL)\n'
                          'let note = "one-star reviews of Count That Fast"\n')
        failures = self.check()["failures"]
        self.assertTrue(any("makes network calls" in f for f in failures))
        self.assertTrue(any("mentions payments" in f for f in failures))
        self.assertTrue(any("competitor names in the app's source" in f for f in failures))
        self.assertTrue(self.warning("opens links out"))

    def test_declared_network_passes_with_reason(self) -> None:
        self.write_source('let feed = URL(string: "https://studio.dev/bench.json")!\n')
        self.edit("app.json", lambda a: a["decisions"].update(network="optional GET of a static JSON feed on studio.dev; works offline"))
        self.assertFalse(self.failing("network"))

    def test_short_network_reason_blocks(self) -> None:
        self.edit("app.json", lambda a: a["decisions"].update(network="feed"))
        self.assertTrue(self.failing("decisions.network isn't 'none'"))

    def test_reply_signoff_is_not_a_difference(self) -> None:
        (self.app_dir / "store/review-reply.txt").write_text("Hello,\n\n" + NOTES + "\nPlease let us know.\n\nThank you.\n")
        self.assertFalse(self.warning("differ from the notes"))

    def test_template_names_and_untested_device_block(self) -> None:
        self.edit("app.json", lambda a: a["app"].update(storeName="Example Counter"))
        self.edit("store/device-check.json", lambda d: d.update(device="not tested (phone unreachable)"))
        failures = self.check()["failures"]
        self.assertTrue(any("storeName" in f for f in failures))
        self.assertTrue(any("device model" in f for f in failures))

    def test_offline_check_says_urls_unverified(self) -> None:
        self.assertTrue(self.warning("not loaded"))

    def test_new_refuses_nonempty(self) -> None:
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(slipway.main(["new", str(self.app_dir)]), 1)


if __name__ == "__main__":
    unittest.main()
