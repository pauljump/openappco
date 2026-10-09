#!/usr/bin/env python3
"""Mirror App Store Connect review state onto the openappco tracking issues.

Read-only against Apple. For every App Store Connect app whose name matches an
open `app` issue, it reads the newest App Store version and, when something
changed, rewrites that issue's status label, `App Store:` line and `Next:` line.
The issue edit triggers .github/workflows/status.yml, which re-renders the site.

  asc-status.py            dry run: print what would change
  asc-status.py --apply    edit the issues (needs authenticated gh)

Credentials come from ~/.secrets via the shared release tool; nothing is written
anywhere else. Run with /Users/mini-home/projects/asc-venv/bin/python.
"""
from __future__ import annotations

import datetime as dt
import importlib.util
import json
import re
import shutil
import subprocess
import sys

REPO = "pauljump/openappco"
TOOL = "/Users/mini-home/projects/_factory/brain/tools/appstore-connect.py"
# Rejections stay in-review: the app is still in Apple's process and stays on
# the public site as "Changes requested" rather than disappearing.
REVIEW = {"WAITING_FOR_REVIEW", "IN_REVIEW", "PENDING_DEVELOPER_RELEASE", "PENDING_APPLE_RELEASE",
          "PROCESSING_FOR_APP_STORE", "ACCEPTED", "REJECTED", "METADATA_REJECTED", "INVALID_BINARY"}
LIVE = {"READY_FOR_SALE", "READY_FOR_DISTRIBUTION"}


def next_line(state: str, version: str, build: str | None) -> str | None:
    b = f" (build {build})" if build else ""
    return {
        "WAITING_FOR_REVIEW": f"Await Apple review of version {version}{b}.",
        "IN_REVIEW": f"Apple is reviewing version {version}{b}.",
        "PENDING_DEVELOPER_RELEASE": f"Approved by Apple. Release version {version}.",
        "PENDING_APPLE_RELEASE": f"Approved by Apple. Version {version} is releasing.",
        "PROCESSING_FOR_APP_STORE": f"Approved by Apple. Version {version} is processing for the App Store.",
        "READY_FOR_SALE": "Live on the App Store. Collect feedback and maintain.",
        "REJECTED": f"Address Apple's review feedback for version {version}, then resubmit.",
        "METADATA_REJECTED": f"Fix the App Store listing Apple flagged for version {version}, then resubmit.",
    }.get(state)


def label_for(state: str) -> str:
    return "status:live" if state in LIVE else "status:in-review" if state in REVIEW else "status:building"


def gh(*args: str) -> str:
    return subprocess.run([shutil.which("gh") or "/opt/homebrew/bin/gh", *args], check=True, capture_output=True, text=True).stdout


def main() -> int:
    apply = "--apply" in sys.argv
    spec = importlib.util.spec_from_file_location("asc", TOOL)
    asc = importlib.util.module_from_spec(spec)
    sys.modules["asc"] = asc
    spec.loader.exec_module(asc)
    client = asc.ASCClient(asc.load_vault())

    issues = json.loads(gh("issue", "list", "--repo", REPO, "--label", "app", "--state", "open",
                           "--limit", "200", "--json", "number,title,body,labels"))
    by_name = {i["title"]: i for i in issues}
    today = dt.date.today().isoformat()

    for app in client.request("GET", "/apps", params={"limit": "200", "fields[apps]": "name"})["data"]:
        issue = by_name.get(app["attributes"]["name"])
        if not issue:
            continue
        versions = client.request("GET", f"/apps/{app['id']}/appStoreVersions", params={
            "limit": "1", "include": "build", "fields[appStoreVersions]": "versionString,appStoreState,build",
            "fields[builds]": "version"})
        if not versions["data"]:
            continue
        v = versions["data"][0]["attributes"]
        state, version = v["appStoreState"], v["versionString"]
        build = next((b["attributes"]["version"] for b in versions.get("included", []) if b["type"] == "builds"), None)
        if state == "PREPARE_FOR_SUBMISSION":
            continue  # not submitted yet; the issue's own Next line stays authoritative

        body = issue["body"]
        old = re.search(r"^App Store: ([A-Z_]+) · checked (\S+)$", body, re.M)
        current = [l["name"] for l in issue["labels"] if l["name"].startswith("status:")]
        want = label_for(state)
        if old and old.group(1) == state and current == [want]:
            continue

        line = f"App Store: {state} · checked {today}"
        body = re.sub(r"^App Store: .*$", line, body, flags=re.M) if old else re.sub(
            r"^(Next: .*)$", lambda m: f"{m.group(1)}\n\n{line}", body, count=1, flags=re.M)
        if (n := next_line(state, version, build)):
            body = re.sub(r"^Next: .*$", f"Next: {n}", body, count=1, flags=re.M)

        print(f"#{issue['number']} {issue['title']}: {current} -> {want}; {state} {version}{' build ' + build if build else ''}")
        if apply:
            args = ["issue", "edit", str(issue["number"]), "--repo", REPO, "--body", body]
            for label in current:
                if label != want:
                    args += ["--remove-label", label]
            if want not in current:
                args += ["--add-label", want]
            gh(*args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
