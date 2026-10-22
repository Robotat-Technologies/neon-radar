"""`neonradar ingest build` with the ICIJ builder (PHASE-2.md M2.5): the gate, strict validation
and a counts-only summary, on a synthetic archive (invented ids and names, `QQ` postcodes)."""

import io
import json
import zipfile
from typing import Any

import yaml
from typer.testing import CliRunner

from neonradar_cli.main import app
from neonradar_ingest.data import layout
from neonradar_ingest.data.project import REPO_ROOT

runner = CliRunner()
MEMBERS = {
    "nodes-entities.csv": "node_id,name,note\n9920000001,Myrtle Leat Formations Ltd,SYN\n",
    "nodes-officers.csv": "node_id,name\n9930000001,Zafer Velqasimi\n9930000002,Yazan Zubeirono\n",
    "nodes-intermediaries.csv": "node_id,name\n",
    "nodes-others.csv": "node_id,name\n",
    "nodes-addresses.csv": 'node_id,name,address\n9910000001,,"1 Synthetic Row, QQ1 1AA"\n',
    "relationships.csv": "node_id_start,node_id_end,rel_type,link\n"
    "9920000001,9910000001,registered_address,registered address\n"
    "9930000001,9920000001,officer_of,synthetic role; of\n"
    "9930000001,9930000002,same_name_as,same name as\n",
}


def test_ingest_build_icij_writes_a_counts_only_summary(data_env: Any) -> None:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as zf:
        for name, text in MEMBERS.items():
            zf.writestr(name, text)
    folder = layout.sources_dir("icij_offshore_leaks", "main", "2099-01-01")
    folder.mkdir(parents=True)
    (folder / "full-oldb.LATEST.zip").write_bytes(buffer.getvalue())
    entry = {"name": "full-oldb.LATEST.zip", "version": "2099-01-01",
             "url": "https://archive.test/full-oldb.LATEST.zip"}  # fmt: skip
    download = {"files": [entry], "complete": True, "completed_at": "2099-01-01T00:00:00Z"}
    (folder / "download.json").write_text(json.dumps(download), encoding="utf-8")
    sample = yaml.safe_load((REPO_ROOT / "ingest/profiles/uk-sample.yaml").read_text("utf-8"))
    companies_house = sample["sources"]["gb_companies_house"]
    companies_house["companies"]["postcode_districts"] = ["QQ1"]
    icij = {"enabled": True, "mode": "district-linked", "max_nodes": 10, "sample_seed": 1}
    sources = {"gb_companies_house": companies_house, "icij_offshore_leaks": icij}
    data_env.write_profile("icij-cli", real_data=True, sources=sources)
    args = ["ingest", "build", "--profile", "icij-cli", "--dataset", "icij_offshore_leaks"]
    assert runner.invoke(app, args).exit_code == 3  # the gate first
    data_env.allow_real("icij-cli")
    result = runner.invoke(app, args)
    assert result.exit_code == 0, result.output
    assert "Myrtle" not in result.output and "Velqasimi" not in result.output
    report = json.loads(next((data_env.cache / "reports" / "icij-cli").iterdir()).read_text())
    counts = report["datasets"]["icij_offshore_leaks"]
    assert counts["status"] == "ok" and counts["mode"] == "district-linked"
    assert counts["nodes_by_level"] == {"level_0": 1, "level_1": 1, "level_2": 1}
    assert counts["records_by_schema"] == {"address": 1, "company": 1, "legalentity": 1,
                                           "unknownlink": 1}  # fmt: skip
    assert counts["unknown_links_by_value"] == {}  # one value: folded into the rare count
    assert counts["unknown_links_by_value_rare"] == 1
    assert counts["hints_outside_slice"] == 1  # the second officer is not in the slice
    records = layout.records_dir("icij-cli", "icij_offshore_leaks")
    assert sorted(p.name.split("-", 2)[-1] for p in records.iterdir()) == [
        "hints.csv", "records.ftm.jsonl", "records.manifest.json"]  # fmt: skip
