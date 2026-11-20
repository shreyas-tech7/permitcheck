"""The README and every command line output say: synthetic data, no legal advice, not for production."""

import json
from pathlib import Path

import pytest

from permitcheck.cli import main
from permitcheck.disclaimer import DISCLAIMER

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "data" / "applications" / "LH-APP-0018.txt"
PARTS = ("SYNTHETIC DATA ONLY", "no legal advice", "Not for production use")


def test_disclaimer_has_all_three_parts():
    for part in PARTS:
        assert part in DISCLAIMER


def test_readme_carries_the_disclaimer():
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    assert DISCLAIMER in text
    assert "fictional" in text.lower()


@pytest.mark.parametrize("argv", [
    ["generate", "--n", "4", "--seed", "7"],
    ["check", str(APP)],
    ["eval", "--split", "dev"],
    ["readme"],
])
def test_every_command_prints_the_disclaimer_first(argv, tmp_path, capsys, monkeypatch):
    if argv[0] == "generate":
        argv = argv + ["--out", str(tmp_path / "gen")]
    elif argv[0] == "check":
        argv = argv + ["--out", str(tmp_path / "out")]
    elif argv[0] == "eval":
        argv = argv + ["--out", str(tmp_path / "res")]
    else:
        readme = tmp_path / "README.md"
        readme.write_text((ROOT / "README.md").read_text(encoding="utf-8"), encoding="utf-8")
        argv = argv + ["--readme", str(readme)]
    assert main(argv) == 0
    out = capsys.readouterr().out
    assert out.splitlines()[0] == DISCLAIMER


def test_help_output_carries_the_disclaimer(capsys):
    with pytest.raises(SystemExit):
        main(["--help"])
    assert "SYNTHETIC DATA ONLY" in capsys.readouterr().out


def test_every_written_output_carries_the_disclaimer(tmp_path):
    main(["check", str(APP), "--out", str(tmp_path)])
    d = tmp_path / "LH-APP-0018"
    assert DISCLAIMER in (d / "checklist.md").read_text()
    assert DISCLAIMER in (d / "letter.md").read_text()
    assert json.loads((d / "queue.json").read_text())["disclaimer"] == DISCLAIMER
    assert all(json.loads(line)["synthetic"] for line in (d / "audit.jsonl").read_text().splitlines())


def test_missing_application_gives_a_clear_error(tmp_path, capsys):
    assert main(["check", str(tmp_path / "nope.txt")]) == 2
    out = capsys.readouterr().out
    assert out.splitlines()[0] == DISCLAIMER and "no application file" in out
