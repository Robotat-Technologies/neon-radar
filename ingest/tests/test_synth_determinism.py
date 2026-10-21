"""Same seed, same bytes (PHASE-1.md M1.8e deliverable 1, GC-09), and the committed fixture."""

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

from neonradar_ingest.synth.demo import DEMO_SEED, STEM, write_demo_mini

FIXTURE = Path(__file__).resolve().parents[2] / "data" / "fixtures" / "demo-mini"
OUTPUTS = (f"{STEM}.ftm.jsonl", "labels/transactions.csv", "labels/scenarios.csv")


def _digests(folder: Path) -> dict[str, str]:
    return {name: hashlib.sha256((folder / name).read_bytes()).hexdigest() for name in OUTPUTS}


def _manifest(folder: Path) -> dict[str, object]:
    data = json.loads((folder / f"{STEM}.manifest.json").read_text(encoding="utf-8"))
    data.pop("created_at")
    return dict(data)


def test_same_seed_gives_the_same_bytes(tmp_path: Path) -> None:
    write_demo_mini(tmp_path / "a", DEMO_SEED)
    write_demo_mini(tmp_path / "b", DEMO_SEED)
    assert _digests(tmp_path / "a") == _digests(tmp_path / "b")
    assert _manifest(tmp_path / "a") == _manifest(tmp_path / "b")


def test_another_seed_gives_other_data(tmp_path: Path) -> None:
    write_demo_mini(tmp_path / "a", DEMO_SEED)
    write_demo_mini(tmp_path / "b", 7)
    assert _digests(tmp_path / "a")[OUTPUTS[0]] != _digests(tmp_path / "b")[OUTPUTS[0]]


def test_output_does_not_depend_on_the_hash_seed(tmp_path: Path) -> None:
    """Set or dict ordering that leaked into the output would differ between these runs."""
    for hash_seed in ("0", "4242"):
        code = (
            "import sys; from pathlib import Path;"
            "from neonradar_ingest.synth.demo import write_demo_mini;"
            f"write_demo_mini(Path(sys.argv[1]), {DEMO_SEED})"
        )
        env = {**os.environ, "PYTHONHASHSEED": hash_seed}
        subprocess.run(  # noqa: S603
            [sys.executable, "-c", code, str(tmp_path / hash_seed)], check=True, env=env
        )
    assert _digests(tmp_path / "0") == _digests(tmp_path / "4242")


def test_committed_fixture_equals_a_fresh_generation(tmp_path: Path) -> None:
    """Fails when the code, Faker or numpy changed the output: run `make fixtures`, then check
    every new name against the Companies House search before committing (OD-12)."""
    write_demo_mini(tmp_path, DEMO_SEED)
    assert _digests(FIXTURE) == _digests(tmp_path)
    assert _manifest(FIXTURE) == _manifest(tmp_path)
