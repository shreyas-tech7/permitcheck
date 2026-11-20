"""Part 1 sections 9 to 12 (quality bar, study kit, release), checked by code."""

import re
import struct
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent

REQUIRED = ["LICENSE", "CHANGELOG.md", "CONTRIBUTING.md", ".github/ISSUE_TEMPLATE/bug_report.md",
            ".github/ISSUE_TEMPLATE/feature_request.md", ".github/workflows/ci.yml", ".github/workflows/record.yml",
            "docs/GITHUB_ABOUT.md", "docs/topics.txt", "docs/social-preview.png", "docs/index.html", "docs/DEMO.md",
            "docs/PROPOSALS.md", "docs/build/BUILD_PROMPT.md", ".env.example", ".pre-commit-config.yaml"]
STUDY = ["docs/WALKTHROUGH.md", "docs/INTERVIEW_QA.md", "DECISIONS.md"]
RELEASE = ["docs/RELEASE_CHECK.md", "docs/HUMAN_STEPS.md", "docs/handoff/COWORK_PROMPT.md", "HANDOVER.md"]
BANNED = ["it is important to note", "testament", "not just", "pivotal", "seamless", "delve"]


def test_required_files_exist():
    assert [f for f in REQUIRED if not (ROOT / f).is_file()] == []


def test_license_is_mit_for_shreyas():
    text = (ROOT / "LICENSE").read_text()
    assert text.startswith("MIT License") and "Copyright (c) 2026 Shreyas" in text


def test_social_preview_size():
    data = (ROOT / "docs/social-preview.png").read_bytes()
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    assert struct.unpack(">II", data[16:24]) == (1280, 640)


def test_topics_are_valid():
    topics = (ROOT / "docs/topics.txt").read_text().split()
    assert 5 <= len(topics) <= 20
    assert all(re.fullmatch(r"[a-z0-9][a-z0-9-]{0,24}", t) for t in topics)


def test_ci_workflow_follows_the_rules():
    ci = (ROOT / ".github/workflows/ci.yml").read_text()
    for need in ("workflow_dispatch", "pull_request", "cancel-in-progress: true", "paths-ignore",
                 'python-version: "3.11"', "./init.sh", "timeout-minutes: 5"):
        assert need in ci, need
    record = (ROOT / ".github/workflows/record.yml").read_text()
    assert "workflow_dispatch" in record and "push:" not in record and "pull_request" not in record


def test_site_and_preview_show_committed_numbers():
    import json
    held = json.loads((ROOT / "results/eval_heldout_rule.json").read_text())
    page = (ROOT / "docs/index.html").read_text()
    fa = held["false_approve_critical_violations"]
    assert f"{fa['k']} of {fa['n']}" in page and "SYNTHETIC DATA ONLY" in page


def _prose(text: str) -> str:
    text = re.sub(r"```.*?```", "", text, flags=re.S)
    text = re.sub(r"`[^`\n]*`", "", text)
    text = re.sub(r"<!--.*?-->", "", text, flags=re.S)
    return "\n".join(ln for ln in text.splitlines() if not ln.lstrip().startswith(("|", ">")))


def _docs() -> list[Path]:
    skip = {"BUILD_PROMPT.md", "DEMO.md"}
    files = [ROOT / "README.md", ROOT / "CONTRIBUTING.md", ROOT / "CHANGELOG.md"] + sorted(ROOT.glob("docs/**/*.md"))
    files += [ROOT / f for f in ("DECISIONS.md", "HANDOVER.md") if (ROOT / f).exists()]
    return [f for f in files if f.name not in skip]


@pytest.mark.parametrize("path", _docs(), ids=lambda p: str(p.relative_to(ROOT)))
def test_writing_rules(path):
    """No em dashes, no dashes as punctuation, no semicolons in prose, no listed filler words."""
    prose = _prose(path.read_text(encoding="utf-8"))
    assert "—" not in prose and "–" not in prose, "em or en dash"
    assert " - " not in prose.replace("\n- ", "\n"), "dash as punctuation"
    assert ";" not in prose, "semicolon"
    low = prose.lower()
    assert [w for w in BANNED if w in low] == []


def test_link_checker_passes():
    proc = subprocess.run([sys.executable, str(ROOT / "scripts/check_links.py")], capture_output=True, text=True,
                          timeout=60)
    assert proc.returncode == 0, proc.stdout[-2000:]


def test_study_kit_exists():
    assert [f for f in STUDY if not (ROOT / f).is_file()] == []


def test_study_interview_qa_covers_the_points():
    qa = (ROOT / "docs/INTERVIEW_QA.md").read_text().lower()
    assert qa.count("\n## ") >= 12
    for point in ("model extracts", "false approve cost", "needs-human", "synthetic data not show"):
        assert point in qa, point
    assert "src/permitcheck/" in qa and "results/" in qa


def test_study_walkthrough_tours_every_source_file():
    text = (ROOT / "docs/WALKTHROUGH.md").read_text()
    for f in sorted((ROOT / "src/permitcheck").glob("*.py")):
        assert f.name in text, f.name


def test_release_files_exist():
    assert [f for f in RELEASE if not (ROOT / f).is_file()] == []


def _release_line(path: Path) -> str:
    m = re.search(r"^Release commit: (.+)$", path.read_text(), flags=re.M)
    assert m, f"no release commit line in {path.name}"
    return m.group(1).strip()


def test_release_sha_is_recorded():
    """The release commit says "this commit". The next commit records the full SHA, and only hand-off
    files change after it, so the tagged tree passes its own tests."""
    lines = {_release_line(ROOT / "CHANGELOG.md"), _release_line(ROOT / "docs/HUMAN_STEPS.md")}
    assert len(lines) == 1
    line = lines.pop()
    steps = (ROOT / "docs/HUMAN_STEPS.md").read_text()
    assert "v0.1.0-rc1" in steps and "public" in steps.lower()
    if line.startswith("this commit"):
        return
    assert re.fullmatch(r"[0-9a-f]{40}", line), line
    if not (ROOT / ".git").exists():
        return
    git = ["git", "-C", str(ROOT)]
    if subprocess.run(git + ["cat-file", "-e", line + "^{commit}"], capture_output=True, timeout=30).returncode:
        pytest.skip("shallow clone: the release commit is not fetched")
    ok = subprocess.run(git + ["merge-base", "--is-ancestor", line, "HEAD"], capture_output=True, timeout=30)
    assert ok.returncode == 0, "the release commit is not in the history of HEAD"
    changed = subprocess.run(git + ["diff", "--name-only", line, "HEAD"], capture_output=True, text=True,
                             timeout=30).stdout.split()
    handoff = {"CHANGELOG.md", "docs/HUMAN_STEPS.md", "HANDOVER.md", "PROGRESS.md", "docs/RELEASE_CHECK.md"}
    assert set(changed) <= handoff, set(changed) - handoff


def test_release_check_lists_every_tool():
    text = (ROOT / "docs/RELEASE_CHECK.md").read_text()
    assert "PENDING" not in text
    for tool in ("gitleaks", "pip-audit", "ruff check --select S", "actionlint", "check_links", "Outside check"):
        assert tool in text, tool
