"""Each detector's QUERIES names exactly the query files its candidate steps run (PHASE-3.md 7.1.2).

`detect run` hashes these files into the alert's `detector.query_sha256` (C4), so the list must be
complete. The check is static: the `source.<method>(...)` calls in the detector module and in the
functions it imports from other detector modules, plus `paid_hop` when it uses the path expansion.
"""

import ast
import importlib
import inspect
import textwrap
from importlib import resources

from neonradar_detect import catalog, runner

FILES = {
    "paid_time_range": ("paid_time_range",),
    "paid_starts": ("paid_starts",),
    "paid_hop": ("paid_hop",),
    "flows_by_inbound": ("flows_by_inbound",),
    "flows_by_outbound": ("flows_by_outbound",),
    "counterparty_info": ("counterparty_info",),
    "paid_times": ("paid_times",),
    "payments_from": ("payments_from",),
    "payments_into": ("payments_into",),
    "payments_among": ("payments_among",),
    "activity_counts": ("activity_counts",),
    "holder_cash_deposits": ("holder_cash_deposits",),
    "quiet_account_histories": ("quiet_account_histories",),
    "company_account_histories": ("company_account_histories",),
    "recent_account_components": (
        "recent_account_edges",
        "recent_account_components_project",
        "recent_account_components_wcc",
        "recent_account_components_drop",
    ),
    "entities": ("entities",),
    "links_into": ("links_into",),
    "links_from": ("links_from",),
    "appointment_counts": ("appointment_counts",),
    "ownership_paths": ("ownership_paths",),
    "ownership_cycles": ("ownership_cycles",),
    "registered_clusters": ("registered_clusters",),
    "registered_count_quantile": ("registered_count_quantile",),
    "listed_entities": ("listed_entities",),
    "flagged_ids": ("flagged_ids",),
    "hubs": ("hubs",),
    "cash_profiles": ("cash_profiles",),
}


def _calls(tree: ast.AST) -> set[str]:
    found = set()
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "source"
        ):
            found.add(node.func.attr)
        if isinstance(node, ast.Call) and getattr(node.func, "id", "") == "expand":
            found.add("paid_hop")
    return found


def _methods(module) -> set[str]:
    tree = ast.parse(inspect.getsource(module))
    found = _calls(tree)
    for node in tree.body:
        if isinstance(node, ast.ImportFrom) and (node.module or "").startswith(
            "neonradar_detect.detectors."
        ):
            other = importlib.import_module(node.module)
            for alias in node.names:
                obj = getattr(other, alias.name)
                if inspect.isfunction(obj):
                    found |= _calls(ast.parse(textwrap.dedent(inspect.getsource(obj))))
    return found


def test_queries_lists_are_exact_and_the_files_exist():
    existing = {
        p.name for p in resources.files("neonradar_detect.queries").iterdir() if p.is_file()
    }
    for slug, module in runner.detectors(catalog.load()).items():
        methods = _methods(module)
        assert methods <= set(FILES), (slug, methods - set(FILES))
        expected = sorted({f"{name}.cypher" for m in methods for name in FILES[m]})
        assert list(module.QUERIES) == expected, slug
        assert set(module.QUERIES) <= existing, slug
