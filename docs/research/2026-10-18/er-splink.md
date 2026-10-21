# NeonRadar phase 2: entity resolution stack (Splink 5, DuckDB, phonetic keys, evaluation)

Research date: Sunday 18 October 2026. Every fact was checked on 2026-10-18 unless stated. Facts carry source tags [E1] to [E24]; the "Sources" list at the end gives the URL, or the command that produced the fact. Anything that could not be confirmed is marked UNVERIFIED. Background: phase 1 `kit/research/stack.md` section 4 (Splink 5.0.0, rigour, jellyfish, rapidfuzz, Python 3.14 wheels); this note re-checks its time-sensitive parts and goes deeper [E24].

How this was verified:
- Versions: PyPI JSON API [E1]. Splink history: read-only clone of the GitHub repository (tags, `CHANGELOG.md`, docs sources, CI workflows, lockfile) [E2]. API facts: the installed splink 5.0.0 wheel [E3].
- Code was run in a CPython 3.14.6 venv made with `uv venv --python 3.14` (the container's uv offers 3.14.6; 3.14.8 is the current patch per stack.md) with splink 5.0.0, duckdb 1.5.6, pyarrow 26.0.0, sqlglot 30.23.0, metaphone 0.6, jellyfish 1.3.0 and rapidfuzz 3.14.6, and without pandas or numpy [E4]. Machine: Linux x86_64 container, 2 vCPU, 7 GiB RAM; all timings are from it.
- HTML outputs were opened in headless Chromium 153 (npm `@sparticuz/chromium` 153.0.0 driven by `puppeteer-core` 25.14.0), logging and aborting every request that was not `file:`, `data:` or `blob:` [E19].
- Blocked from the shell on 2026-10-18: gist.github.com and the gist API, community-extensions.duckdb.org, googlechromelabs.github.io. The upgrade gist was read through the web fetch tool, which returns summaries and short quotes only [E6].

## 0. Answers for the spec writer

1. **Versions.** splink **5.0.0** (2026-09-28) is still the newest; there is no 5.0.x patch, but master holds an unreleased u-estimation change (PR #3338, merged 2026-10-12) that will shift trained u values. splink needs only `duckdb>=0.9.2`, `pyarrow>=18.0.0`, `sqlglot>=17.6.0` (no caps; upstream's lockfile tests 1.5.5, 25.0.1, 30.18.0). Newest today, all working on 3.14.6: duckdb **1.5.6** (cp314), sqlglot **30.23.0** (pure Python), pyarrow **26.0.0** (cp314), jellyfish **1.3.0** (new, changes Metaphone keys), rapidfuzz **3.14.6**. Treat any splink, duckdb or jellyfish lock bump as a model change. [E1][E2][E4]
2. **API (section 2).** `DuckDBAPI(connection=":memory:" | path | DuckDBPyConnection, output_schema=None, *, materialisation="table" | "parquet", ...)` has no memory or thread options: pass a `duckdb.connect(":memory:", config={...})` connection. Register inputs first with `db_api.register(table, *, dataset_display_name=None, table_name=None)`, reload a model with `Linker(sdf, "model.json")`, and read results without pandas via `as_record_list()`, `as_pyarrow_table()`, `as_duckdbpyrelation()` or `query_sql("... {this} ...")`. Verified traps: `NameComparison` has TF on by default and `configure(term_frequency_adjustments=False)` does not remove it; empty arrays are not NULL; `DateOfBirthComparison` misfiles `YYYY-MM` strings. [E3][E4]
3. **Spike (section 3).** On 2,942 invented people (1,350 entities) the full pipeline (blocking analysis, prior, u, two EM sessions, predict, cluster, evaluate, save, reload, predict) took 5.8 s wall and 220 MB peak RSS on 2 threads; u estimation was 71 percent of it. Pairwise precision/recall was 0.991/0.980 at p >= 0.5 and 1.000/0.946 at p >= 0.95. Reloading the JSON reproduced every pair and weight exactly. Bitwise identical across fresh processes and 1, 2 or 4 threads: prior, u, blocking counts, pair sets, clusters (also with `seed=None`). EM m values (up to 2e-15) and weights (up to 3.3e-14) differ when threads > 1; `threads=1` is bitwise. [E4]
4. **Constraints (section 4).** Splink 5 has no cannot-link or must-link support. `cluster_pairwise_predictions_at_threshold` is connected components over edges with `match_probability >= threshold`, so a chain A-B-C merges A and C even when they conflict. Every record is returned, and singletons get `cluster_id` equal to their own unique_id (576 of 576 checked). The only clustering constraint is `cluster_using_single_best_links(df, duplicate_free_datasets=[...])`, one record per source dataset, so NeonRadar needs its own constrained clustering step. [E3][E4]
5. **Upgrade guidance (section 5).** Release post: https://moj-analytical-services.github.io/splink/blog/2026/09/28/splink-500-released.html. LLM prompt: appendix of https://gist.github.com/RobinL/c6d56a27d8f83c40b6b09643c0fa5d14 (last active 2026-09-15, before the release). Rules: register inputs and drop `db_api=`; `as_record_dict` becomes `as_record_list`; `bf_` becomes `mw_` (log2); `set_up_basic_logging` becomes `log_level`; drop salting, `use_cache`, `materialise_blocked_pairs` and `overwrite=`; use the renamed blocking functions; use `score_pair`, `score_pairs` and `predict_between`. Point agents at `/splink/llms.txt`, not the v4 docs. [E5][E6][E20]
6. **Labelling and HTML (section 6).** The labelling tool remains (`linker.evaluation.labelling_tool_for_specific_record`, "still in development") but needs pandas and numpy. The comparison viewer, cluster studio and labelling tool inline their JavaScript but fetch a Google Fonts stylesheet (plus two preconnects). Plain `chart.save("x.html")` fetches Vega from cdn.jsdelivr.net and renders blank offline, while `save(..., inline=True)` and `save_offline_chart()` are self-contained. In headless Chromium, stripping the three font `<link>` tags left zero external requests. [E3][E19]
7. **Performance (section 7).** The docs advise about 20M comparisons at most on a modest laptop, with DuckDB linking "up to around 5 million records on a modern laptop (4 core/16GB RAM)". Set `memory_limit`, and chunk or use Parquet only when needed. Measured (2 vCPU, 3.7 GiB limit): 1M records with 11.3M comparisons took 91 s. With 174M comparisons, unchunked predict and exact blocking counts ran out of memory; 4x4 chunks finished predict in 650 s. Laptop config: `memory_limit="6GiB"`, `threads=4`, SSD `temp_directory`, `preserve_insertion_order=False`. [E7][E8][E11][E13][E23]
8. **Phonetic keys (section 8).** No maintained MIT/BSD package with cp314 wheels has Double Metaphone: jellyfish 1.3.0 and `rigour.text` have single Metaphone only. Use `Metaphone` 0.6 (BSD, pure Python, 2016; `from metaphone import doublemetaphone`; works on 3.14.6), or `phonetics` 1.0.5 (MIT, pure Python) as a fallback. Avoid DoubleMetaphone (Artistic, no cp314), abydos (GPL), and the `splink_udfs` DuckDB extension unless vendored. `dmeta_col_name` wants a LIST(VARCHAR) of one or two codes; strip empty codes, or `''` matches unrelated names. [E1][E3][E4][E9][E16]
9. **Wilson interval (section 9).** centre = (p + z^2/(2n)) / (1 + z^2/n); half-width = z / (1 + z^2/n) * sqrt(p(1-p)/n + z^2/(4n^2)); z = 1.959964 for 95 percent (NIST/SEMATECH e-Handbook 7.2.4.1; Wilson 1927). Example: 180/200 gives **[0.851, 0.934]**. For plus or minus 5 points you need 381 labels at p = 0.5, 245 at 0.8 and 141 at 0.9; plan **400** random pairs per published precision figure. [E17][E18][E4]
10. **Without labels (section 10).** Use `unlinkables_chart()`, `match_weights_histogram(df_predict)`, `match_weights_chart()`, `parameter_estimate_comparisons_chart()` and spot checks in the comparison viewer. `predict(threshold_match_probability=...)` shrinks only the output: every blocked pair is still built and scored. TF tables are computed and cached automatically; `compute_tf_table()` and `register_term_frequency_lookup()` precompute or reuse them, and `predict_within()`/`predict_between()` need them supplied. [E3][E6][E8][E22]

## 1. Versions and dependency ranges (question 1)

PyPI on 2026-10-18 [E1]:

| Package | Latest (first upload) | Python 3.14 | Licence | Notes |
|---|---|---|---|---|
| splink | 5.0.0 (2026-09-28) | pure-Python wheel (`py3-none-any`); upstream CI tests 3.10 to 3.14 [E2] | MIT | releases since phase 1: none. 4.0.17 (2026-09-03) is the last v4 |
| duckdb | 1.5.6 (2026-09-28) | cp314 wheel (cp310 to cp314; no cp315) | MIT | `2.0.0.devN` pre-releases are on PyPI (latest 2.0.0.dev2610162032, 2026-10-17); do not let `--prerelease` pick them up |
| sqlglot | 30.23.0 (2026-10-14) | pure Python | MIT | 30.18.0 to 30.23.0 all came out between 2026-09-03 and 2026-10-14 |
| pyarrow | 26.0.0 (2026-10-09) | cp314 and cp314t wheels | Apache-2.0 | requires Python >= 3.11 |
| jellyfish | 1.3.0 (2026-10-16) | cp314 (cp311 to cp315) | MIT | new since phase 1 (1.2.1); see section 8 |
| rapidfuzz | 3.14.6 (2026-08-30) | cp314 and cp314t | MIT | unchanged since phase 1 |
| rigour | 2.5.0 (2026-09-10) | cp314 | MIT | unchanged since phase 1 |

What splink 5.0.0 requires (wheel METADATA and `pyproject.toml` at tag v5.0.0) [E2][E3]: `duckdb>=0.9.2`, `pyarrow>=18.0.0`, `sqlglot>=17.6.0`, Python `>=3.10.0,<4.0.0`; extras `altair` (altair>=5.0.1), `igraph` (igraph>=0.11.2), `postgres`, `pyspark`/`spark`, `sqlite` (rapidfuzz>=3.10.0). There are no upper bounds. The lockfile at v5.0.0 (unchanged on master) pins duckdb 1.5.5, pyarrow 25.0.1, sqlglot 30.18.0, and a daily "Dependency canary" workflow runs `uv lock --upgrade` plus the DuckDB tests on Python 3.13 [E2]. Our runs used duckdb 1.5.6, pyarrow 26.0.0 and sqlglot 30.23.0 without any failure [E4].

Changelog highlights for 5.0.0 [E2]: chunked `predict()` with progress and runtime estimates; optional direct Parquet materialisation in DuckDB; experimental `predict_within()`/`predict_between()`; `score_pair()`/`score_pairs()`; SQL pipeline profiling (`DuckDBAPIWithProfiling`); u estimation in chunks with early stopping; EM `max_pairs`; record sampling for the prior and for blocking analysis ("Blocking counts are sampled by default"); explicit input registration; only DuckDB, PyArrow and SQLGlot required at runtime; charts as `SplinkChart` without Altair; match weights (`mw_`) instead of Bayes factors (`bf_`); `DateOfBirthComparison` uses standard Levenshtein on all backends. Removed: Python 3.9, Amazon Athena, `compare_two_records()`, `find_matches_to_new_records()`, implicit caching and `use_cache`, salting, `materialise_blocked_pairs`, the similarity-analysis helpers.

Since 5.0.0 [E2]: the changelog's "Unreleased" section is empty, but master has PR #3338 ("Spread u-estimation samples across both sides while retaining early stopping", merged 2026-10-12; files `estimate_u.py`, `training.py`) and typing overloads for `query_sql`. #3338 replaces the right-hand-side-only chunking with a hash equi-join across both sides, so a future 5.0.1 will produce different u values for the same seed.

Pinning advice: keep `splink==5.0.*` and `duckdb==1.5.*` in `pyproject.toml` (uv.lock pins the exact versions); record the exact splink and duckdb versions in each saved model's run metadata; re-baseline golden m/u values and pair counts whenever either changes, because both the sampling code and DuckDB's `hash()` feed the u sample [E3][E6].

## 2. Exact signatures (question 2; read from the installed 5.0.0 wheel [E3], checked by `inspect.signature` [E4])

### 2.1 DuckDBAPI and registration

```python
from splink import DuckDBAPI            # lazy import of splink.internals.duckdb.database_api.DuckDBAPI
DuckDBAPI(connection: Union[str, duckdb.DuckDBPyConnection] = ":memory:", output_schema: str | None = None, *,
          materialisation: Literal["table", "parquet"] = "table",
          materialisation_dir: str | PathLike[str] | None = None,
          parquet_materialisation_options: ParquetWriteOptions | None = None)
DuckDBAPI.register(self, table: AcceptableInputTableType | str, *, dataset_display_name: Optional[str] = None,
                   table_name: Optional[str] = None) -> SplinkDataFrame
DuckDBAPI.register_from_csv(self, path: str) -> SplinkDataFrame
DuckDBAPI.query_sql(self, sql: str, output_type: Literal["splink_df", "splinkdf", "pandas"] = "splink_df")
DuckDBAPI.duckdb_con            # property: the underlying DuckDBPyConnection
DuckDBAPI.delete_tables_created_by_splink_from_db(self)
# splink.backends.duckdb also exports:
ParquetWriteOptions(*, compression: str | None = None, compression_level: int | None = None,
                    per_thread_output: bool = True, file_size_bytes: str | int | None = None,
                    row_group_size: int | None = None)
DuckDBAPIWithProfiling(connection=":memory:", output_schema=None, query_profiling_dir="tmp_query_profiling",
                       enable_profiling="json", profiling_mode="standard", profiling_coverage="ALL", *,
                       materialisation="table", materialisation_dir=None, parquet_materialisation_options=None)
```

- `connection` may be `":memory:"`, `":temporary:"`, `":default:"`, a database file path (an info log is emitted unless it ends in `.duckdb` or `.db`), or an existing `DuckDBPyConnection` used as is. `":temporary:"` creates a `.duckdb` file inside a `tempfile.TemporaryDirectory(dir="")`, that is, in the current working directory. `materialisation="parquet"` requires `materialisation_dir` (a local path, not S3) [E3][E7].
- There are no memory, thread or temp-directory arguments. Configure DuckDB on the connection; this was verified by reading `duckdb_settings()` back [E4]:

```python
con = duckdb.connect(":memory:", config={"memory_limit": "6GiB", "threads": 4,
                                         "temp_directory": "/data/duckdb_tmp", "preserve_insertion_order": False})
db_api = DuckDBAPI(connection=con)        # or later: db_api.duckdb_con.execute("SET threads = 4")
```

- `register()` accepts a pyarrow Table, a pandas DataFrame (when pandas is installed), a list of dicts, a dict of lists, or a string. A string is taken as the name of a table that already exists on the connection and is wrapped, not copied. Other inputs become DuckDB views through `con.register()`, so keep the Arrow table alive. `dataset_display_name` doubles as `table_name` when the latter is omitted, and a second registration under the same name raises `ValueError("A table has already been registered with table_name=...")`; so does a name that already exists as a table in the database. For `link_only` and `link_and_dedupe`, `dataset_display_name` is the `source_dataset` value [E3][E6].

### 2.2 SettingsCreator

```python
SettingsCreator(link_type: Literal["link_only", "link_and_dedupe", "dedupe_only"],          # required
                comparisons: List[ComparisonCreator | dict[str, Any]] = [],
                blocking_rules_to_generate_predictions: List[BlockingRuleCreator | dict[str, Any]] = [],
                probability_two_random_records_match: float = 0.0001,
                em_convergence: float = 0.0001, max_iterations: int = 25,
                retain_matching_columns: bool = True, retain_intermediate_calculation_columns: bool = False,
                additional_columns_to_retain: List[str] = [],
                unique_id_column_name: str = "unique_id", source_dataset_column_name: str = "source_dataset",
                match_weight_column_prefix: str = "mw_", term_frequency_adjustment_column_prefix: str = "tf_",
                comparison_vector_value_column_prefix: str = "gamma_", linker_uid: str | None = None)
SettingsCreator.from_path_or_dict(path_or_dict: Path | str | dict[str, Any]) -> SettingsCreator
```

There is no global TF switch: TF is a per-level setting (`tf_adjustment_column`, `tf_adjustment_weight`, `tf_minimum_u_value`). With `retain_intermediate_calculation_columns=True`, predict output has `match_weight`, `match_probability`, `unique_id_l/_r`, `<col>_l/_r`, `gamma_<comparison>`, `mw_<comparison>`, `tf_<col>_l/_r`, `mw_tf_adj_<col>`, the retained extra columns and `match_key` (index of the blocking rule that produced the pair) [E4]. `retain_matching_columns=True` is required by the labels-table evaluation; both retain flags are required by the comparison viewer and cluster studio [E3].

### 2.3 Blocking rules and comparisons

```python
block_on(*col_names_or_exprs: Union[str, ColumnExpression], arrays_to_explode: list[str] | None = None) -> BlockingRuleCreator
# splink.blocking_rule_library exports CustomRule, And, Not, block_on (no Or; the docs say OR turns the join into a filter)

import splink.comparison_library as cl
cl.NameComparison(col_name, *, jaro_winkler_thresholds: float | list[float] = [0.92, 0.88, 0.7], dmeta_col_name: str | None = None)
cl.ForenameSurnameComparison(forename_col_name, surname_col_name, *, jaro_winkler_thresholds=[0.92, 0.88],
                             forename_surname_concat_col_name: str | None = None)
cl.ExactMatch(col_name: str)                                   # cl.ExactMatch("x").configure(term_frequency_adjustments=True)
cl.ArrayIntersectAtSizes(col_name: str, size_threshold_or_thresholds: Iterable[int] | int = [1])
cl.PostcodeComparison(col_name, *, invalid_postcodes_as_null: bool = False, lat_col=None, long_col=None,
                      km_thresholds: float | List[float] = [1, 10, 100])
cl.DateOfBirthComparison(col_name, *, input_is_string: bool, datetime_thresholds=[1, 1, 10],
                         datetime_metrics=["month", "year", "year"], datetime_format: str | None = None,
                         invalid_dates_as_null: bool = True)      # input_is_string is required
cl.JaroWinklerAtThresholds(col_name: str, score_threshold_or_thresholds: Iterable[float] | float = [0.9, 0.7])
cl.LevenshteinAtThresholds(col_name: str, distance_threshold_or_thresholds: Iterable[int] | int = [1, 2])
cl.CustomComparison(comparison_levels: List[ComparisonLevelCreator | dict[str, Any]],
                    output_column_name: str | None = None, comparison_description: str | None = None)
ComparisonCreator.configure(*, term_frequency_adjustments=..., m_probabilities=..., u_probabilities=...)

import splink.comparison_level_library as cll
cll.NullLevel(col_name, valid_string_pattern: str | None = None)
cll.ExactMatchLevel(col_name, term_frequency_adjustments: bool = False)
cll.ArrayIntersectLevel(col_name, min_intersection: int = 1)
cll.ArraySubsetLevel(col_name, empty_is_subset: bool = False)
cll.JaroWinklerLevel(col_name, distance_threshold: int | float)
cll.LevenshteinLevel(col_name, distance_threshold: int)
cll.ColumnsReversedLevel(col_name_1, col_name_2, symmetrical: bool = False)
cll.AbsoluteDateDifferenceLevel(col_name, *, input_is_string: bool, threshold: int | float, metric, datetime_format=None)
cll.LiteralMatchLevel(col_name, literal_value: str, literal_datatype: str, side_of_comparison: str = "both")
cll.CustomLevel(sql_condition: str, label_for_charts: str | None = None, base_dialect_str: str | None = None)
cll.ElseLevel()
cll.And(*levels), cll.Or(*levels), cll.Not(level)
ComparisonLevelCreator.configure(*, m_probability, u_probability, tf_adjustment_column, tf_adjustment_weight,
    tf_minimum_u_value, is_null_level, label_for_charts, disable_tf_exact_match_detection,
    fix_m_probability, fix_u_probability)
```

Other library classes: `AbsoluteDateDifferenceAtThresholds` and `AbsoluteTimeDifferenceAtThresholds` (keyword-only `input_is_string`, `metrics`, `thresholds` all required), `DamerauLevenshteinAtThresholds`, `JaccardAtThresholds`, `JaroAtThresholds`, `DistanceFunctionAtThresholds`, `PairwiseStringDistanceFunctionAtThresholds` (`distance_function_name` required), `DistanceInKMAtThresholds(lat_col, long_col, km_thresholds)`, `EmailComparison`, `CosineSimilarityAtThresholds` [E3].

Verified behaviours that the spec must state (generated SQL printed with `get_comparison("duckdb").human_readable_description` and `as_dict()`) [E4]:
- **TF defaults.** `NameComparison`, `ForenameSurnameComparison` and `EmailComparison` set `tf_adjustment_column` (weight 1.0) on their exact-match levels by default. `.configure(term_frequency_adjustments=False)` leaves it on, because the flag only adds TF and never removes it. A TF-free name comparison must be written as a `CustomComparison` with the same levels (done for `forename` in 3.4). `ExactMatch`, `JaroWinklerAtThresholds`, `PostcodeComparison` and `DateOfBirthComparison` have no TF unless configured.
- **Levels generated.** `NameComparison`: null, exact, JW >= 0.92, JW >= 0.88, [dmeta intersect >= 1], JW >= 0.7, else. `PostcodeComparison`: null, full, sector, district, area (regex extracts), else. `ArrayIntersectAtSizes([2, 1])`: null, intersect >= 2, >= 1, else.
- **Empty arrays.** The null level is `col_l IS NULL OR col_r IS NULL`, and in DuckDB `[] IS NULL` is false, so an empty array falls to the ELSE level and counts as evidence against a match. Write empty arrays as NULL during preparation.
- **Month-year dates.** `DateOfBirthComparison(..., input_is_string=True, datetime_format="%Y-%m")` parses fine (`try_strptime('1980-05', '%Y-%m')` gives 1980-05-01), but its levels misfile month-year data. `levenshtein('1980-05', '1990-05')` is 1, so a ten-year gap lands in "Levenshtein <= 1". The "<= 1 month" level is `ABS(EPOCH(a) - EPOCH(b)) <= 2629800` seconds (30.44 days), so 1980-12 vs 1981-01 (31 days) misses it. In our run that level never got an m value ("m values not fully trained"). The custom month-year comparison in 3.4 removes the warning and improved precision and recall slightly (table in 3.2).
- `CustomLevel` SQL refers to columns as `<col>_l` and `<col>_r`. Splink v3 function names (`exact_match`, `levenshtein_at_thresholds`, `else_level`) and `DateComparison` do not exist; every `cl` and `cll` name in v4.0.17 still exists in 5.0.0 (diff of `__all__`) [E2].

### 2.4 Linker and its components

```python
Linker(splink_dataframe_or_dataframes: SplinkDataFrame | Sequence[SplinkDataFrame],
       settings: SettingsCreator | dict[str, Any] | Path | str,       # a path loads a saved model JSON
       log_level: int | str | None = 20, validate_settings: bool = True)
# components: linker.training, .inference, .clustering, .evaluation, .table_management, .misc,
#             .visualisations, .blocking_analysis
linker.training.estimate_probability_two_random_records_match(deterministic_matching_rules: List[str | BlockingRuleCreator],
    recall: float, record_sample_proportion: float = 1.0) -> None
linker.training.estimate_u_using_random_sampling(max_pairs: float = 1e6, seed: int | None = None,
    min_count_per_level: int | None = 100, num_chunks: int = 10) -> None
linker.training.estimate_parameters_using_expectation_maximisation(blocking_rule: str | BlockingRuleCreator,
    estimate_without_term_frequencies: bool = False, fix_probability_two_random_records_match: bool = False,
    fix_m_probabilities: bool = False, fix_u_probabilities: bool = True,
    populate_probability_two_random_records_match_from_trained_values: bool = False, *,
    max_pairs: float | None = None, record_sample_proportion: float = 0.01) -> EMTrainingSession
linker.training.estimate_m_from_label_column(label_colname: str) -> None
linker.training.estimate_m_from_pairwise_labels(labels_splinkdataframe_or_table_name)
linker.inference.predict(threshold_match_probability: float | None = None, threshold_match_weight: float | None = None,
    num_chunks_left: int | None = None, num_chunks_right: int | None = None,
    warning_mode: Literal["auto", "always", "never"] = "auto") -> SplinkDataFrame
linker.inference.predict_chunk(left_chunk=None, right_chunk=None, threshold_match_probability=None,
    threshold_match_weight=None, warning_mode="auto") -> SplinkDataFrame
linker.inference.deterministic_link() -> SplinkDataFrame          # pairs from blocking rules, no scoring
linker.inference.score_pair(record_left, record_right, include_found_by_blocking_rules=False) -> SplinkDataFrame
linker.inference.score_pairs(records_left, records_right, include_found_by_blocking_rules=False) -> SplinkDataFrame
linker.inference.predict_within(...); linker.inference.predict_between(left, right, *, link_type=None,
    blocking_rules_to_generate_predictions=None, threshold_match_probability=None, ...)   # experimental
linker.clustering.cluster_pairwise_predictions_at_threshold(df_predict: SplinkDataFrame,
    threshold_match_probability: float | None = None, threshold_match_weight: float | None = None) -> SplinkDataFrame
linker.clustering.cluster_using_single_best_links(df_predict, duplicate_free_datasets: List[str],
    threshold_match_probability=None, threshold_match_weight=None, ties_method: str = "lowest_id") -> SplinkDataFrame
linker.clustering.compute_graph_metrics(df_predict, df_clustered, *, threshold_match_probability=None) -> GraphMetricsResults
linker.evaluation.accuracy_analysis_from_labels_column(labels_column_name: str, *, threshold_match_probability: float = 0.5,
    match_weight_round_to_nearest: float = 0.1,
    output_type: Literal["threshold_selection", "roc", "precision_recall", "table", "accuracy"] = "threshold_selection",
    add_metrics: List[Literal["specificity", "npv", "accuracy", "f1", "f2", "f0_5", "p4", "phi"]] = [],
    positives_not_captured_by_blocking_rules_scored_as_zero: bool = True)
linker.evaluation.accuracy_analysis_from_labels_table(labels_splinkdataframe_or_table_name: str | SplinkDataFrame, *,
    threshold_match_probability=0.5, match_weight_round_to_nearest=0.1, output_type="threshold_selection", add_metrics=[])
linker.evaluation.prediction_errors_from_labels_column(label_colname: str, include_false_positives: bool = True,
    include_false_negatives: bool = True, threshold_match_probability: float = 0.5) -> SplinkDataFrame
linker.evaluation.prediction_errors_from_labels_table(labels_splinkdataframe_or_table_name, include_false_positives=True,
    include_false_negatives=True, threshold_match_probability=0.5) -> SplinkDataFrame
linker.evaluation.unlinkables_chart(x_col: Literal["match_weight", "match_probability"] = "match_weight",
    name_of_data_in_title: str | None = None)
linker.evaluation.labelling_tool_for_specific_record(unique_id, source_dataset=None, out_path="labelling_tool.html",
    overwrite=False, match_weight_threshold=-4, view_in_jupyter=False, show_splink_predictions_in_interface=True)
linker.table_management.register_labels_table(input_data: SplinkDataFrame) -> SplinkDataFrame
linker.table_management.compute_tf_table(column_name: str) -> SplinkDataFrame
linker.table_management.register_term_frequency_lookup(input_data: SplinkDataFrame, col_name: str) -> SplinkDataFrame
linker.table_management.register_table_predict(input_data: SplinkDataFrame) -> SplinkDataFrame
linker.table_management.register_blocked_pairs_for_predict(input_data: SplinkDataFrame) -> SplinkDataFrame
linker.misc.save_model_to_json(out_path: str | None = None, overwrite: bool = False) -> dict[str, Any]
linker.misc.query_sql(sql, output_type="splink_df")
```

Notes [E3][E4]:
- The `seed` argument exists. In 5.0.0 the u sample is a deterministic hash filter on the unique-id columns (the seed is appended to the hashed string; modulus 1e9), not `TABLESAMPLE`. Results are therefore repeatable for fixed ids, data, seed and DuckDB version, and `seed=None` is repeatable too, just a different sample. The docstring's remark that seeding "will have performance implications" describes the old design. Whether DuckDB's `hash()` stays stable across DuckDB releases is UNVERIFIED; the gist says the same seed does not give the same sample across backends [E6].
- `estimate_u_using_random_sampling` warns when `max_pairs` is left at 1e6. Its docstring says 1e7 "is often adequate whilst testing" and at least 1e9 "gives best results". `min_count_per_level=None` disables early stopping.
- EM: the blocking rule should give blocked pairs where matches are "between about 1% and 99%"; comparisons used in the rule are not estimated in that session. `max_pairs` caps the pairs with a deterministic hash filter.
- The evaluation component class is spelled `LinkerEvalution` upstream (typo); not a public import.
- `accuracy_analysis_from_labels_column(..., output_type="table")` returns a SplinkDataFrame with `truth_threshold` (match weight, rounded to `match_weight_round_to_nearest`), `match_probability`, `p`, `n`, `tp`, `tn`, `fp`, `fn`, `precision`, `recall`, `specificity`, `npv`, `accuracy`, `f1`, `f2`, `f0_5`, `p4`, `phi`. Rounding means a pair just below a threshold (for example at weight -0.04) counts as positive at 0.0; in the final run Splink counted 2,715 true positives at weight 0.0 against our own 2,714 at p >= 0.5. Labels tables need `unique_id_l`, `unique_id_r`, `clerical_match_score` (plus `source_dataset_l/_r` for link jobs).

### 2.5 Blocking analysis and outputs without pandas

```python
from splink.blocking_analysis import (count_comparisons_from_blocking_rules, chart_comparisons_from_blocking_rules,
                                      n_largest_blocks)
count_comparisons_from_blocking_rules(splink_dataframe_or_dataframes, *, blocking_rules, link_type,
    unique_id_column_name="unique_id", source_dataset_column_name=None,
    record_sample_proportion: float = 0.05) -> list[CumulativeComparisonRecord]
chart_comparisons_from_blocking_rules(...same arguments...) -> CumulativeBlockingRuleComparisonsGeneratedChart
n_largest_blocks(splink_dataframe_or_dataframes, *, blocking_rule, link_type, n_largest: int = 5) -> SplinkDataFrame
linker.blocking_analysis.count_comparisons_from_blocking_rules(blocking_rules=None, *, record_sample_proportion=0.05)
# record keys: blocking_rule, equi_join_conditions, filter_conditions, link_type_join_condition,
#   marginal_comparison_count, cumulative_comparison_count, total_possible_comparison_count, match_key,
#   record_sample_proportion, is_estimate.  n_largest_blocks columns: key_0.., count_l, count_r, block_count

sdf.as_record_list(limit=None) -> list[dict]       sdf.as_dict(limit=None) -> dict[str, list]
sdf.as_pyarrow_table(limit=None) -> pa.Table       sdf.as_duckdbpyrelation(limit=None) -> DuckDBPyRelation
sdf.query_sql("select ... from {this} where ...") -> SplinkDataFrame    # {{this}} inside f-strings
sdf.physical_name, sdf.templated_name, sdf.columns, sdf.to_parquet(path, overwrite=False), sdf.to_csv(...)
sdf.drop_table_from_database_and_remove_from_cache(); sdf.as_pandas_dataframe(limit=None)   # pandas only
```

Counts are 5 percent sampled estimates by default, with a `UserWarning` when fewer than 1,000 sampled comparisons support a rule; pass `record_sample_proportion=1.0` for exact counts. The 2,942-record spike ran everything without pandas or numpy [E4].

Names removed since v4.0.17 (diff of public `__all__` and method signatures) [E2]: `count_comparisons_from_blocking_rule`, `cumulative_comparisons_to_be_scored_from_blocking_rules_chart`/`_data`, `splink.exploratory.similarity_analysis`, `compare_two_records`, `find_matches_to_new_records`, `register_table_input_nodes_concat_with_tf`, `predict(materialise_after_computing_term_frequencies=, materialise_blocked_pairs=)`, `estimate_probability_two_random_records_match(max_rows_limit=)` (now `record_sample_proportion`), every `overwrite=` on `register_*`, every `as_dict=` on chart methods, and `SplinkDataFrame.as_record_dict`. New: the `splink.logging` module and `linker.blocking_analysis`.

## 3. End-to-end spike (question 3)

### 3.1 What it does

`er_spike.py` (3.4) generates 1,350 invented people (names built from invented syllables, Zipf-like surname frequencies with the top surname at about 2.5 percent, 3 percent namesakes) with one to five noisy records each: typos, missing or shifted month-year dates of birth, house moves, partial country and company-number lists. It writes `unique_id`, `true_cluster`, `forename`, `surname`, `name_norm`, `surname_dm`, `dob_ym`, `dob_year`, `postcode`, `countries`, `company_numbers`, registers the data, then runs exact blocking counts and `n_largest_blocks`, the prior, u (seeded), and two EM sessions. It predicts at p >= 0.01, scores pairwise precision and recall at four thresholds, clusters at 0.95, runs `accuracy_analysis_from_labels_column`, saves the model, reloads it into a new Linker on a fresh connection and predicts again. `--extras` also writes the HTML outputs and a 200-pair labels-table evaluation. `compare_runs.py` (same folder) diffs two runs. Run: `python -I er_spike.py OUT --seed 42 --u-seed 42 --threads 2 [--dob custom] [--extras]`.

### 3.2 Results [E4]

| Metric | Built-in `DateOfBirthComparison` (run A1) | Custom month-year DOB (run F) |
|---|---|---|
| Records, true entities, true pairs | 2,942; 1,350; 2,769 | same |
| Exact comparisons from the five rules (marginal per rule) | 12,662 (2,348; 244; 356; 9,706; 8) | same |
| Largest surname block (`n_largest_blocks`) | 93 records, 8,649 pairs | same |
| `probability_two_random_records_match` | 0.000464 | same |
| EM iterations (session 1, session 2) | 7, 5 | 6, 5 |
| Pairwise precision / recall at p >= 0.5 | 0.9905 / 0.9801 | 0.9938 / 0.9848 |
| at p >= 0.9 | 0.9992 / 0.9531 | 0.9989 / 0.9632 |
| at p >= 0.95 | 0.9996 / 0.9462 | 0.9992 / 0.9556 |
| at p >= 0.99 | 0.9996 / 0.9274 | 0.9996 / 0.9285 |
| Clusters at 0.95: pairwise P / R; clusters; singletons | 0.9989 / 0.9726; 1,386; 576 | 0.9982 / 0.9805; 1,376; 562 |
| Splink truth table at weight 0.0 (p = 0.5): tp / fp / fn | 2,715 / 26 / 54 | 2,728 / 17 / 41 |
| `prediction_errors_from_labels_column` rows at 0.9 | 132 | 105 |
| Levels left untrained (warnings) | DOB "<= 1 month" (never observed); postcode "area" | postcode "area" |
| Reload from JSON on a fresh connection | same pairs, weight difference 0.0 | same |
| Seconds: generate, blocking analysis, prior, u, EM, predict, cluster | 0.08, 0.14, 0.04, 4.08, 0.26, 0.16, 0.07 | 0.06, 0.10, 0.02, 3.39, 0.20, 0.13, 0.06 |
| Wall in script; process time incl. imports; peak RSS | 5.8 s; 6.7 s; 220 MB | 4.7 s; 5.1 s; 225 MB |

Labels-table path (`--extras`): 200 pairs spread across the weight range, registered with `register_labels_table`, gave a 173-row accuracy table and 3 errors at p = 0.5. The self-contained HTML files were 0.8 to 2.1 MB each (the CDN-loading chart 38 KB). With pandas and numpy installed (run G) every metric was the same (weights within 2.1e-14) and peak RSS was 269 MB. The synthetic noise is mild, so these accuracy figures say nothing about real Companies House or sanctions data.

### 3.3 Determinism (fresh processes, same data seed) [E4]

| Runs compared (same data seed) | u bitwise equal | m bitwise equal | max abs m or u diff | prior and blocking counts | pair set at p >= 0.01 | max abs weight diff | cluster metrics |
|---|---|---|---|---|---|---|---|
| seed 42, 2 threads: run 1 vs run 2 | 28/28 | 1/27 | 1.6e-15 | equal | identical | 3.3e-14 | equal |
| seed 42, 2 threads: run 1 vs run 3 | 28/28 | 0/27 | 1.2e-15 | equal | identical | 2.9e-14 | equal |
| seed 42, 1 thread: run 1 vs run 2 | 28/28 | 27/27 | 0 | equal | identical | 0 (bitwise) | equal |
| `seed=None`, 2 threads: run 1 vs run 2 | 28/28 | 4/27 | 2.0e-15 | equal | identical | 2.3e-14 | equal |
| 2 threads vs 1 thread | 28/28 | 10/27 | 1.1e-16 | equal | identical | 7.1e-15 | equal |
| 2 threads vs 4 threads | 28/28 | 0/27 | 1.3e-15 | equal | identical | 3.2e-14 | equal |
| without vs with pandas installed | 28/28 | 1/27 | 1.2e-15 | equal | identical | 2.1e-14 | equal |
| seed 42 vs `seed=None` | 0/28 | 0/27 | 0.0071 | equal | 7 pairs differ | 1.3 | differ |
| seed 42 vs seed 7 | 0/28 | 0/27 | 0.0068 | equal | 5 pairs differ | 0.55 | equal |

(27 m and 28 u values are all the non-null levels; the DOB "<= 1 month" level has a u value but no m value.)

What this means for the spec:
- Reproducible by design: data generation (seeded `random.Random`), blocking counts, the prior, u values (hash sampling, with or without a seed), the set of predicted pairs and hence the connected components. Cluster ids are deterministic too (minimum unique_id in each component).
- Not bitwise reproducible with threads > 1: EM-trained m values and therefore every match weight, at the 1e-15 level (parallel floating-point summation order). For golden tests either run DuckDB with `threads=1` (bitwise identical m, u and weights in our runs) or compare floats with a tolerance such as 1e-9 and compare pair sets exactly.
- The saved model JSON contains `linker_uid` (8 random characters, used as a cache id). Strip it before diffing models, or set `SettingsCreator(linker_uid=...)` explicitly (not tested).
- The u sample depends on the unique_id values, so keep ids stable (derive them from source keys, not row order). Changing the seed changes u by up to 0.007 and weights by up to 1.3 (5 to 7 pairs crossed p = 0.01).

### 3.4 Script (final version, as run)

```python
"""NeonRadar phase 2 ER spike: Splink 5.0.0 + DuckDB on synthetic people (invented names only).

python -I er_spike.py OUT_DIR [--seed 42] [--u-seed 42|none] [--threads 2] [--dob builtin|custom] [--extras]
"""
from __future__ import annotations

import argparse, hashlib, json, logging, random, resource, string, time
from itertools import combinations
from pathlib import Path

import duckdb
import pyarrow as pa
import splink.comparison_level_library as cll
import splink.comparison_library as cl
from splink import DuckDBAPI, Linker, SettingsCreator, block_on
from splink.blocking_analysis import count_comparisons_from_blocking_rules, n_largest_blocks
from metaphone import doublemetaphone  # pure-Python Double Metaphone (BSD), see section 8

SYL = ["ka", "lo", "mir", "dan", "vel", "tor", "sa", "ri", "bel", "qu", "zan", "fen", "or", "ith", "ul",
       "mar", "nev", "ost", "pra", "sil", "tem", "vor", "yen", "zul", "bra", "cor", "dro", "eli", "fae", "gor"]
ISO = ["GB"] * 6 + ["IE", "FR", "DE", "NL", "ES", "IT", "PL", "CY", "MT", "AE", "CH", "LU", "US", "NG", "IN", "SG"]


def pool(rng: random.Random, n: int, parts: tuple[int, ...]) -> list[str]:
    out: dict[str, None] = {}
    while len(out) < n:
        out["".join(rng.choice(SYL) for _ in range(rng.choice(parts))).capitalize()] = None
    return list(out)


def typo(rng: random.Random, s: str) -> str:
    i = rng.randrange(1, len(s) - 1)
    op = rng.choice("sdt")
    if op == "s":
        return s[:i] + rng.choice(string.ascii_lowercase) + s[i + 1:]
    return s[:i] + s[i + 1:] if op == "d" else s[:i] + s[i + 1] + s[i] + s[i + 2:]


def postcode(rng: random.Random, district: str | None = None) -> str:
    district = district or "".join(rng.choices(string.ascii_uppercase, k=rng.choice([1, 2]))) + str(rng.randint(1, 29))
    return f"{district} {rng.randint(0, 9)}{''.join(rng.choices(string.ascii_uppercase, k=2))}"


def make_people(seed: int, n_entities: int = 1350) -> list[dict]:
    rng = random.Random(seed)
    forenames, surnames = pool(rng, 200, (2, 3)), pool(rng, 300, (2, 3))
    fw = [1 / (r + 5) for r in range(len(forenames))]  # top forename about 5 percent of people
    sw = [1 / (r + 10) for r in range(len(surnames))]  # top surname about 2.5 percent, so TF matters
    rows, uid, entities = [], 0, []
    for e in range(n_entities):
        if entities and rng.random() < 0.03:  # namesake: same name, different person
            fn, sn = entities[rng.randrange(len(entities))][:2]
        else:
            fn, sn = rng.choices(forenames, fw)[0], rng.choices(surnames, sw)[0]
        year, month = rng.randint(1940, 2002), rng.randint(1, 12)
        pc = postcode(rng)
        ctry = sorted(set(rng.sample(ISO, rng.choice([1, 1, 2, 3]))))
        cos = [f"{rng.randint(0, 99_999_999):08d}" for _ in range(rng.choice([0, 1, 1, 2, 3, 4]))]
        entities.append((fn, sn))
        for k in range(rng.choices([1, 2, 3, 4, 5], [0.38, 0.27, 0.17, 0.11, 0.07])[0]):
            noisy = k > 0
            f = typo(rng, fn.lower()) if noisy and rng.random() < 0.12 else fn.lower()
            s = typo(rng, sn.lower()) if noisy and rng.random() < 0.10 else sn.lower()
            y, m = year + (rng.choice([-1, 1]) if noisy and rng.random() < 0.03 else 0), month
            if noisy and rng.random() < 0.05:
                m = min(12, max(1, m + rng.choice([-1, 1])))
            r = rng.random()
            dob_ym, dob_year = (None, None) if r < 0.08 else ((None, y) if r < 0.12 else (f"{y:04d}-{m:02d}", y))
            r = rng.random()
            p = None if r < 0.08 else (postcode(rng, pc.split()[0] if r < 0.18 else None) if noisy and r < 0.28 else pc)
            c = None if rng.random() < 0.10 else sorted(set(rng.sample(ctry, rng.randint(1, len(ctry)))
                                                            + ([rng.choice(ISO)] if rng.random() < 0.1 else [])))
            co = sorted(rng.sample(cos, rng.randint(1, len(cos)))) if cos and rng.random() > 0.35 else None
            dm = [x for x in doublemetaphone(s) if x]
            rows.append(dict(unique_id=uid, true_cluster=f"E{e:05d}", forename=f, surname=s, name_norm=f"{f} {s}",
                             surname_dm=dm or None, dob_ym=dob_ym, dob_year=dob_year, postcode=p,
                             countries=c, company_numbers=co))
            uid += 1
    return rows


SCHEMA = pa.schema([("unique_id", pa.int64()), ("true_cluster", pa.string()), ("forename", pa.string()),
                    ("surname", pa.string()), ("name_norm", pa.string()), ("surname_dm", pa.list_(pa.string())),
                    ("dob_ym", pa.string()), ("dob_year", pa.int32()), ("postcode", pa.string()),
                    ("countries", pa.list_(pa.string())), ("company_numbers", pa.list_(pa.string()))])

BLOCKING = [block_on("surname", "dob_year"), block_on("forename", "dob_ym"), block_on("postcode"),
            block_on("substr(forename, 1, 2)", "substr(surname, 1, 2)"),
            block_on("company_numbers", arrays_to_explode=["company_numbers"])]


def make_settings(dob_mode: str) -> SettingsCreator:
    if dob_mode == "builtin":
        dob = cl.DateOfBirthComparison("dob_ym", input_is_string=True, datetime_format="%Y-%m")
    else:  # month-year data: avoid Levenshtein on "1980-05" vs "1990-05"
        ym = "abs(date_diff('month', strptime(dob_ym_l, '%Y-%m'), strptime(dob_ym_r, '%Y-%m'))) <= 1"
        dob = cl.CustomComparison(output_column_name="dob", comparison_levels=[
            cll.NullLevel("dob_year"), cll.ExactMatchLevel("dob_ym"),
            cll.CustomLevel(ym, label_for_charts="within 1 month"),
            cll.ExactMatchLevel("dob_year"),
            cll.CustomLevel("abs(dob_year_l - dob_year_r) <= 1", label_for_charts="year within 1"),
            cll.ElseLevel()])
    companies = cl.CustomComparison(output_column_name="company_numbers", comparison_levels=[
        cll.CustomLevel("company_numbers_l IS NULL OR company_numbers_r IS NULL",
                        label_for_charts="company_numbers null").configure(is_null_level=True),
        cll.ArrayIntersectLevel("company_numbers", min_intersection=2),
        cll.ArrayIntersectLevel("company_numbers", min_intersection=1),
        cll.ElseLevel()])
    # NameComparison always puts TF on its exact level and configure(term_frequency_adjustments=False)
    # does not remove it (section 2.3), so a TF-free name comparison must be built from levels:
    forename = cl.CustomComparison(output_column_name="forename", comparison_levels=[
        cll.NullLevel("forename"), cll.ExactMatchLevel("forename"), cll.JaroWinklerLevel("forename", 0.92),
        cll.JaroWinklerLevel("forename", 0.88), cll.JaroWinklerLevel("forename", 0.7), cll.ElseLevel()])
    return SettingsCreator(
        link_type="dedupe_only",
        unique_id_column_name="unique_id",
        comparisons=[
            forename,
            cl.NameComparison("surname", dmeta_col_name="surname_dm").configure(term_frequency_adjustments=True),
            dob, cl.PostcodeComparison("postcode"), cl.ArrayIntersectAtSizes("countries", [2, 1]), companies],
        blocking_rules_to_generate_predictions=BLOCKING,
        retain_matching_columns=True, retain_intermediate_calculation_columns=True,
        additional_columns_to_retain=["true_cluster"])


def pr(pred: set, truth: set) -> dict:
    tp = len(pred & truth)
    return {"pairs": len(pred), "tp": tp, "precision": round(tp / max(len(pred), 1), 4),
            "recall": round(tp / len(truth), 4)}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("out"); ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--u-seed", default="42"); ap.add_argument("--threads", type=int, default=2)
    ap.add_argument("--dob", default="builtin"); ap.add_argument("--extras", action="store_true")
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    u_seed = None if a.u_seed == "none" else int(a.u_seed)
    t, T = {}, time.perf_counter()

    rows = make_people(a.seed); t["generate"] = time.perf_counter() - T
    table = pa.Table.from_pylist(rows, schema=SCHEMA)
    by_cluster: dict[str, list[int]] = {}
    for r in rows:
        by_cluster.setdefault(r["true_cluster"], []).append(r["unique_id"])
    truth = {p for ids in by_cluster.values() for p in combinations(sorted(ids), 2)}

    cfg = {"threads": a.threads, "memory_limit": "2GB", "preserve_insertion_order": False,
           "temp_directory": str(out / "duckdb_tmp")}
    db_api = DuckDBAPI(connection=duckdb.connect(":memory:", config=cfg))
    people = db_api.register(table, dataset_display_name="people")

    s = time.perf_counter()
    counts = count_comparisons_from_blocking_rules(people, blocking_rules=BLOCKING, link_type="dedupe_only",
                                                   record_sample_proportion=1.0)
    largest = n_largest_blocks(people, blocking_rule=block_on("surname"), link_type="dedupe_only", n_largest=3)
    t["blocking_analysis"] = time.perf_counter() - s

    linker = Linker(people, make_settings(a.dob), log_level=logging.WARNING)
    s = time.perf_counter()
    linker.training.estimate_probability_two_random_records_match(
        [block_on("forename", "surname", "dob_ym")], recall=0.7)
    t["train_prior"], s = time.perf_counter() - s, time.perf_counter()
    linker.training.estimate_u_using_random_sampling(max_pairs=2e6, seed=u_seed)
    t["train_u"], s = time.perf_counter() - s, time.perf_counter()
    em1 = linker.training.estimate_parameters_using_expectation_maximisation(block_on("forename", "surname"))
    em2 = linker.training.estimate_parameters_using_expectation_maximisation(block_on("dob_ym"))
    t["train_em"] = time.perf_counter() - s

    s = time.perf_counter()
    preds = linker.inference.predict(threshold_match_probability=0.01)
    t["predict"] = time.perf_counter() - s
    recs = preds.as_record_list()  # no pandas needed
    scored = {(r["unique_id_l"], r["unique_id_r"]): (r["match_weight"], r["match_probability"]) for r in recs}
    metrics = {f"p>={th}": pr({k for k, v in scored.items() if v[1] >= th}, truth) for th in (0.5, 0.9, 0.95, 0.99)}

    s = time.perf_counter()
    clusters = linker.clustering.cluster_pairwise_predictions_at_threshold(preds, threshold_match_probability=0.95)
    t["cluster"] = time.perf_counter() - s
    cl_rows = clusters.as_pyarrow_table().select(["cluster_id", "unique_id"]).to_pylist()
    members: dict = {}
    for r in cl_rows:
        members.setdefault(r["cluster_id"], []).append(r["unique_id"])
    cl_pairs = {p for ids in members.values() for p in combinations(sorted(ids), 2)}
    singletons = [ids for ids in members.values() if len(ids) == 1]
    metrics["clusters@0.95"] = pr(cl_pairs, truth) | {
        "n_records": len(cl_rows), "n_clusters": len(members), "n_true_entities": len(by_cluster),
        "singletons": len(singletons),
        "singleton_cluster_id_equals_uid": all(cid == ids[0] for cid, ids in members.items() if len(ids) == 1)}

    truth_tbl = linker.evaluation.accuracy_analysis_from_labels_column(
        "true_cluster", output_type="table", add_metrics=["f1"])
    tt = truth_tbl.as_record_list()
    metrics["splink_truth_table"] = [
        {k: (round(v, 4) if isinstance(v, float) else v) for k, v in min(
            tt, key=lambda x: abs(x["match_probability"] - th)).items()
         if k in ("truth_threshold", "match_probability", "tp", "fp", "fn", "precision", "recall", "f1")}
        for th in (0.5, 0.9, 0.99)]
    errs = linker.evaluation.prediction_errors_from_labels_column("true_cluster", threshold_match_probability=0.9)
    metrics["prediction_errors@0.9"] = errs.as_duckdbpyrelation().count("*").fetchone()[0]

    model_path = out / "model.json"
    model = linker.misc.save_model_to_json(str(model_path), overwrite=True)
    db2 = DuckDBAPI(connection=duckdb.connect(":memory:", config=cfg))  # fresh connection, reload model
    linker2 = Linker(db2.register(table, dataset_display_name="people"), str(model_path), log_level=logging.WARNING)
    recs2 = linker2.inference.predict(threshold_match_probability=0.01).as_record_list()
    scored2 = {(r["unique_id_l"], r["unique_id_r"]): r["match_weight"] for r in recs2}
    reload = {"same_pairs": set(scored2) == set(scored),
              "max_abs_mw_diff": max(abs(scored2[k] - scored[k][0]) for k in scored)}

    mu = {c["output_column_name"]: [[lv["label_for_charts"], lv.get("m_probability"), lv.get("u_probability")]
                                    for lv in c["comparison_levels"]] for c in model["comparisons"]}
    pair_key = sorted(scored)
    result = {
        "versions": {"duckdb": duckdb.__version__, "pyarrow": pa.__version__, "python": __import__("sys").version},
        "args": vars(a), "n_records": len(rows), "n_true_pairs": len(truth),
        "blocking_counts": [(c["blocking_rule"], c["marginal_comparison_count"]) for c in counts],
        "largest_surname_blocks": largest.as_record_list(),
        "prob_two_random": model["probability_two_random_records_match"],
        "em_iterations": [len(em1._core_model_settings_history), len(em2._core_model_settings_history)],
        "metrics": metrics, "reload": reload, "seconds": {k: round(v, 3) for k, v in t.items()},
        "wall_seconds": round(time.perf_counter() - T, 2),
        "peak_rss_mb": round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 1),
        "sha_pairs": hashlib.sha256(repr(pair_key).encode()).hexdigest()[:16],
        "sha_weights_exact": hashlib.sha256(repr([scored[k][0] for k in pair_key]).encode()).hexdigest()[:16],
    }
    (out / "mu.json").write_text(json.dumps(mu, indent=1))
    (out / "pairs.json").write_text(json.dumps([[*k, scored[k][0]] for k in pair_key]))
    (out / "result.json").write_text(json.dumps(result, indent=1, default=str))
    if a.extras:
        extras(linker, db_api, preds, clusters, out)
    print(json.dumps(result, indent=1, default=str))


def extras(linker: Linker, db_api: DuckDBAPI, preds, clusters, out: Path) -> None:
    """HTML outputs (section 6) and a labels-table evaluation (section 2.6)."""
    v = linker.visualisations
    v.comparison_viewer_dashboard(preds, str(out / "comparison_viewer.html"), overwrite=True)
    v.cluster_studio_dashboard(preds, clusters, str(out / "cluster_studio.html"),
                               sampling_method="by_cluster_size", overwrite=True)
    try:  # needs pandas + numpy even in Splink 5 (section 6)
        linker.evaluation.labelling_tool_for_specific_record(
            unique_id=3, out_path=str(out / "labelling_tool.html"), overwrite=True)
    except ModuleNotFoundError as e:
        (out / "labelling_tool.error.txt").write_text(repr(e))
    chart = v.match_weights_chart()
    chart.save(str(out / "chart_default.html"))
    chart.save(str(out / "chart_inline.html"), inline=True)
    linker.evaluation.unlinkables_chart().save_offline_chart(str(out / "unlinkables_offline.html"),
                                                             overwrite=True, print_msg=False)
    v.match_weights_histogram(preds).save(str(out / "mw_histogram.html"), inline=True)
    rel = preds.as_duckdbpyrelation().order("match_weight")
    rows, cols = rel.fetchall(), rel.columns
    sample = rows[:: max(1, len(rows) // 200)][:200]  # spread across the match-weight range
    labels = [{"unique_id_l": r[cols.index("unique_id_l")], "unique_id_r": r[cols.index("unique_id_r")],
               "clerical_match_score": float(r[cols.index("true_cluster_l")] == r[cols.index("true_cluster_r")])}
              for r in sample]
    lab = linker.table_management.register_labels_table(db_api.register(labels, table_name="labels_sample"))
    tbl = linker.evaluation.accuracy_analysis_from_labels_table(lab, output_type="table").as_record_list()
    errs = linker.evaluation.prediction_errors_from_labels_table(lab, threshold_match_probability=0.5)
    (out / "labels_eval.json").write_text(json.dumps(
        {"n_labels": len(labels), "rows": len(tbl), "first": tbl[0], "last": tbl[-1],
         "errors@0.5": errs.as_duckdbpyrelation().count("*").fetchone()[0]}, indent=1, default=str))


if __name__ == "__main__":
    main()
```

## 4. Constraints and clustering (question 4)

- No cannot-link or must-link API exists in 5.0.0: a search of the code and docs found none (only `cluster_using_single_best_links`) [E2][E3].
- `cluster_pairwise_predictions_at_threshold` builds nodes from every input record and edges from `df_predict` filtered by `match_probability >= threshold` (inclusive; no filter when the threshold is None), then runs connected components in SQL: each node starts as its own representative, takes the minimum representative among its neighbours each iteration, and stable clusters are set aside until no cross-cluster edges remain. The final `cluster_id` is the minimum (composite) node id in the component; the output is joined back to all input columns [E3].
- Singletons: every record appears in the output. A record with no edge above the threshold is its own cluster with `cluster_id` equal to its own id (`source_dataset-__-unique_id` in link jobs). In the spike, 576 records were singletons at 0.95 and every one had `cluster_id == unique_id` [E3][E4].
- The only constrained clustering: `cluster_using_single_best_links(df_predict, duplicate_free_datasets=["A", "B"], ties_method="lowest_id" | "drop")` adds a record to a cluster only if it is the mutual best link and the cluster would not hold two records from a duplicate-free source dataset. It is per source dataset, not per identifier [E3].
- Pairwise-only mitigations inside Splink: a strong negative ELSE weight on a hard identifier (learned, or fixed with `cll.<Level>.configure(m_probability=..., u_probability=..., fix_m_probability=True, fix_u_probability=True)`). This lowers the pair score only; transitivity can still join conflicting records through a third record.
- What the spec should require: a NeonRadar step after `predict()` that builds clusters from edges above the threshold with cannot-link rules (for example different non-null company numbers for the same officer role, or dates of birth more than a year apart). It should split offending components by dropping their weakest edges, record each split as an audit event, and test against fixtures with known conflicts. `compute_graph_metrics()` gives node degree, cluster size, density and centralisation (the `is_bridge` edge metric needs `splink[igraph]`), which helps flag chained clusters for review [E3].

## 5. v4 to v5 upgrade guidance and the LLM prompt (question 5)

URLs: release post https://moj-analytical-services.github.io/splink/blog/2026/09/28/splink-500-released.html (repository source `docs/blog/posts/2026-09-28-splink-5-release.md`) [E5]; "comprehensive note of changes" with "Appendix: LLM agent prompt for upgrading Splink 4 code to Splink 5": https://gist.github.com/RobinL/c6d56a27d8f83c40b6b09643c0fa5d14#appendix-llm-agent-prompt-for-upgrading-splink-4-code-to-splink-5 [E6]. The gist was "Last active September 15, 2026" (12 revisions) and says it is valid through commit `2d57cd67` of 10 September 2026, so it predates the 28 September release; anything changed later is not in it. The fetched copy was truncated inside rule 8, so the end of the prompt is UNVERIFIED [E6].

The release post says there is "no change to the statistical model", models saved in v4 JSON "can be loaded directly into Splink 5", but "Splink 5 syntax is not fully backwards compatible" [E5]. Key rules of the prompt, summarised, with short quotes from the fetched text [E6]:
1. Register every input with `db_api.register(df, dataset_display_name=...)` before building the Linker; "The `db_api=` kwarg is REMOVED". Source-dataset names come from `dataset_display_name`, not input order; use `table_name=` only to control the internal name; register DuckDB relations created on the same connection.
2. Do not assume pandas: "replace every `.as_record_dict(...)` with `.as_record_list(...)`"; prefer `as_record_list()`, `as_dict()` (unchanged, columnar) or `as_pyarrow_table()`.
3. `query_sql` returns a SplinkDataFrame by default; pass `output_type="pandas"` for the old behaviour; `{this}` names the frame.
4. Rename `bf_` columns to `mw_`: "Values are now log-base-2 match weights" (Bayes factor = 2 ** mw).
5. Logging: "passing `set_up_basic_logging=` to the Linker now raises `TypeError`"; use `log_level`, and remove root-logger workarounds.
6. Delete `salting_partitions`, `materialise_blocked_pairs`, `use_cache` and `overwrite=`; `AthenaAPI` is gone; rename `count_comparisons_from_blocking_rule` and `cumulative_comparisons_to_be_scored_from_blocking_rules_data`/`_chart` to `count_comparisons_from_blocking_rules`/`chart_comparisons_from_blocking_rules`.
7. Replace `compare_two_records` with `score_pair` ("This does NOT filter rows"), and `find_matches_to_new_records` with `score_pairs` plus a filter, or `predict_between` when blocking is needed; `predict_within`/`predict_between` need TF tables registered or `tf_*` columns supplied.
8. Optional performance levers (chunking, persisted blocked pairs, `estimate_u` settings) only when the old code struggled; early stopping in `estimate_u` is on by default (`min_count_per_level=None` restores full processing).
The prompt asks the agent to work file by file, preserve behaviour, explain each change and leave non-Splink code alone [E6].

For Claude Code: the docs site publishes `https://moj-analytical-services.github.io/splink/llms.txt` (an index of Markdown pages), configured with the note "Agents should fetch /llms.txt first as a compact map of the documentation" [E20]. The site banner links the legacy v4 docs at https://moj-analytical-services.github.io/splink4_legacy_docs/; tell agents not to use them [E21].

## 6. Labelling and HTML outputs; offline check (question 6)

| Output | How produced | Requirements | External requests when opened (headless Chromium, requests blocked) |
|---|---|---|---|
| Labelling tool | `linker.evaluation.labelling_tool_for_specific_record(unique_id=3, out_path=..., overwrite=True)` | pandas and numpy (fails with `ModuleNotFoundError: No module named 'numpy'` on a minimal install); logs "still in development" | Google Fonts stylesheet only; renders (9 table elements) |
| Comparison viewer | `linker.visualisations.comparison_viewer_dashboard(df_predict, out_path, overwrite=False, num_example_rows=2, minimum_comparison_vector_count=0, return_html_as_string=False)` | both retain flags True | Google Fonts stylesheet only; renders (2.1 MB file) |
| Cluster studio | `linker.visualisations.cluster_studio_dashboard(df_predict, df_clustered, out_path, sampling_method="random" or "by_cluster_size" or "lowest_density_clusters_by_size", sample_size=10, cluster_ids=None, cluster_names=None, overwrite=False, return_html_as_string=False)` | both retain flags True | Google Fonts stylesheet only; renders (1.3 MB file) |
| Any chart, default | `chart.save("x.html")` or `chart.to_html()` | none | `https://cdn.jsdelivr.net/npm/vega@5.31.0?noext` (with SRI hashes); **renders nothing offline** |
| Any chart, offline | `chart.save("x.html", inline=True)`, `chart.to_html(inline=True)`, `chart.save_offline_chart(filename, overwrite=False, print_msg=True)` | none | none; renders (about 850 KB, Vega 5.31.0, Vega-Lite 5.2.0, vega-embed 6.20.2 inlined) |

Details [E3][E4][E19]:
- The dashboard and labelling templates inline the Observable stdlib 5.8.3, d3 7.8.5 and the Vega bundles from `splink/internals/files/external_js/`, with the comment "it is inlined so the bundled notebook does not fetch its dependencies from CDNs". Each still contains `<link rel="preconnect" href="https://fonts.googleapis.com">`, `<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>` and a Source Sans Pro stylesheet `<link>`. Preconnects open connections without appearing as requests, so request interception alone under-reports them.
- Grep results: no file has a `<script src="http...">` tag, because the default chart builds its `<script>` elements at run time from a `paths` JSON (`https://cdn.jsdelivr.net/npm/vega@5.31.0?noext`, and the same for vega-lite 5.2.0 and vega-embed 6.20.2). A grep for script tags therefore misses the one real CDN dependency. The bundles also contain dormant loaders (`import(`${cdn}${arrow11.resolve()}`)`, DuckDB-WASM, `https://cdn.jsdelivr.net/npm/`, `https://unpkg.com/`) that did not fire on load, so a "no https:// in file" grep fails on every dashboard. Test behaviour in a browser, not strings.
- Recommended wrapper for NeonRadar: save charts only with `inline=True` or `save_offline_chart`; post-process dashboards with `re.sub(r'<link\b[^>]*\bhref="https://fonts\.(?:googleapis|gstatic)\.com[^>]*>\s*', "", html)` (removed exactly three tags per file); add a CI test that opens each generated file in the project's browser test runner with all non-file requests aborted and asserts zero requests. A Content-Security-Policy `<meta>` tag is an extra guard (UNVERIFIED that it does not break the inline module scripts).
- Labels exported from the labelling tool UI: format UNVERIFIED (not exercised; the template has a CSV download cell). For NeonRadar's own review UI, the input Splink expects is a table of `unique_id_l`, `unique_id_r`, `clerical_match_score` registered with `register_labels_table`.

## 7. Performance and sizing (question 7)

From the Splink docs [E7][E8]:
- "For linkages in DuckDB on a modest laptop, we suggest using blocking rules that create no more than about 20 million comparisons" (blocking tutorial). DuckDB backend: "Link up to around 5 million records on a modern laptop (4 core/16GB RAM)".
- The main runtime driver is the number of pairs, then comparison complexity (more levels, expensive functions, TF). Use equi-join (`block_on`) rules; never OR inside a rule, give two rules instead. Check skew with `n_largest_blocks` and `profile_columns`.
- Use an in-memory connection and keep everything in RAM; if the job spills, materialise to Parquet (`DuckDBAPI(connection=con, materialisation="parquet", materialisation_dir=...)`) or chunk `predict()` (`num_chunks_left`, `num_chunks_right`; "Only use chunking if you need it"). "Explicitly set `memory_limit`" leaving headroom for Python. Prefer SSD. DuckDB 2.0 is recommended on machines with more than about 64 cores.
- `max_pairs` for u: 1e7 for iteration, 1e8 to 1e9 for the final model; EM `max_pairs` and `record_sample_proportion` cap training work; filtering with a predict threshold reduces what is written.

From the DuckDB 1.5 docs [E11][E12][E13]: `memory_limit` defaults to 80 percent of RAM; `threads` defaults to the number of cores; `temp_directory` defaults to `<database>.tmp`, or `.tmp` (a relative path) for in-memory databases; `max_temp_directory_size` defaults to 90 percent of free disk; `preserve_insertion_order` defaults to true, and false "potentially reducing memory usage". The docs say "Aim for 1-4 GB memory per thread" ("join-heavy workloads require 3-4 GB memory per thread"; minimum 125 MB) and limit threads in memory-constrained environments. Joins, aggregates, sorts and windows can spill, but "If multiple blocking operators appear in the same query, DuckDB may still throw an out-of-memory exception", and `list()`/`string_agg()` aggregates cannot spill. Also measured: `memory_limit="4GB"` is read as decimal and shows as 3.7 GiB, so write `GiB` [E4].

Measured with `scale_spike.py` (same generator idea, name pools growing with the data, custom DOB comparison, five equi-join rules, `memory_limit="4GB"`, 2 threads) [E23]:

| Run | Records | Comparisons (exact; 5 percent sample) | Prior | u (`max_pairs=1e7`) | EM x2 (`max_pairs=2e6`) | Predict | Wall | Peak RSS | P / R at p >= 0.5 |
|---|---|---|---|---|---|---|---|---|---|
| 45k entities | 99,969 | 306,553; 314,000 | 0.0 s | 15.0 s | 0.8 s | 1.0 s | 18.3 s | 427 MB | 0.9974 / 0.9748 |
| 450k entities | 998,299 | 11,260,347; 11,117,200 | 0.7 s | 27.3 s | 10.6 s | 31.3 s | 90.6 s | 2,429 MB | 0.9972 / 0.9743 |
| 450k + loose rule `block_on("substr(surname, 1, 3)", "dob_year")`, exact count | 998,299 | exact: out of memory (3.7 GiB) | | | | | failed at 24 s | | |
| same, unchunked predict | 998,299 | not run; 174,090,400 | 0.4 s | | | out of memory in `__splink__blocked_id_pairs` | failed at 58 s | | |
| same, `num_chunks_left=num_chunks_right=4` | 998,299 | not run; 174,090,400 | 0.4 s | 26.4 s | 10.2 s | 650.2 s | 702.1 s | 2,312 MB | 0.9969 / 0.9792 |

Throughput on 2 vCPU: about 0.36M comparisons per second unchunked (1M records) and 0.27M per second chunked. Peak RSS includes the Python-side generator (lists of 1M rows), so DuckDB's own share is lower. Blocking counts took 0.2 s sampled against 6.4 s exact at 11M comparisons.

Sizing rules for the spec:
- Target at most 20M comparisons per run on a 16 GB laptop. Always check counts with the default 5 percent sample: exact counting of 174M pairs ran out of memory where sampling took 0.2 s.
- Never block on a single name column at millions of records: one surname at 2.5 percent of 3M records is 75,000 records and 2.8 billion pairs. Combine keys (surname + birth year, forename + month-year, full postcode, forename + surname, exploded company numbers) and gate releases on `n_largest_blocks`.
- DuckDB connection for a 16 GB laptop that also runs Neo4j and a browser: `memory_limit="6GiB"`, `threads=4` (1.5 GiB per thread, below DuckDB's join guidance, so expect spilling on big jobs), `temp_directory` on SSD inside the project data folder (not the repository), `preserve_insertion_order=False`. If predict fails with an out-of-memory error in `__splink__blocked_id_pairs`, first tighten blocking, then chunk (`num_chunks_left=num_chunks_right=4`), then add Parquet materialisation. The failure at 3.7 GiB with 174M pairs implies more than about 20 bytes per blocked pair (a rough lower bound, not measured directly).
- u estimation dominates training on small and medium data (15 s of 18 s at 100k records with `max_pairs=1e7`); EM with `max_pairs=2e6` took 11 s at 1M records.

## 8. Phonetic keys (question 8)

| Package | Version (date) | Licence | Wheels / 3.14 | Double Metaphone? | Verdict |
|---|---|---|---|---|---|
| jellyfish | 1.3.0 (2026-10-16) | MIT | cp311 to cp315 | no: `metaphone`, `soundex`, `nysiis`, `match_rating_codex` only | fine for single Metaphone; pin exactly |
| rigour (`rigour.text`) | 2.5.0 (2026-09-10) | MIT | cp310 to cp314 | no: `metaphone`, `soundex` (Rust, LRU-cached) | already planned for names; needs PyICU via normality |
| Metaphone (`import metaphone`) | 0.6 (2016-08-24) | BSD (3-clause text in LICENSE) | sdist only, pure Python; built and ran on 3.14.6 | yes: `doublemetaphone(s) -> (primary, secondary)`, `''` when no secondary | **recommended**; unmaintained, so vendor or pin and test |
| phonetics | 1.0.5 (2018-03-23) | MIT (setup.py) | sdist only, pure Python | yes: `dmetaphone` | fallback; alpha status, no LICENSE file in the sdist |
| DoubleMetaphone | 1.2 (2025-05-11) | Artistic | C extension, wheels to cp313 only | yes | avoid (licence, no cp314) |
| Fuzzy | 1.2.2 (2017) | Artistic and MIT classifiers | sdist, C extension | yes (DMetaphone) | avoid (stale, build needed) |
| abydos | 0.5.0 (2020) | GPL-3.0-or-later | pure Python | yes | avoid (GPL) |
| pyphonetics | 0.5.3 (2020) | MIT | pure Python | no (Soundex, Metaphone, MRA, Lein, Refined/Fuzzy Soundex) | avoid (depends on GPL `unidecode`) |
| splink_udfs (DuckDB extension) | branch main (repo) | MIT (Ministry of Justice) | DuckDB binary per version and platform | yes: `double_metaphone(VARCHAR) -> LIST(VARCHAR)` | `INSTALL splink_udfs FROM community` downloads `http://community-extensions.duckdb.org/v1.5.6/linux_amd64/splink_udfs.duckdb_extension.gz` (refused here); only with a pre-installed, pinned extension directory |

Sources: [E1][E9][E10][E14][E15][E16]; behaviour verified by running [E4].

Facts verified by running [E4]:
- The jellyfish 1.3.0 changelog lists a fix for Metaphone emitting a spurious KH for word-final GH [E14]. Invented examples: `zanvogh` gives `SNFKH` in 1.2.1 and `SNF` in 1.3.0; `kelbrugh` gives `KLBRKH` and `KLBR`. Persisted phonetic keys must be rebuilt when this library changes.
- `metaphone.doublemetaphone("velthorn")` returns `('FL0RN', 'FLTRN')`, and `doublemetaphone("kalomir")` returns `('KLMR', '')`.
- What `dmeta_col_name` expects (docstring: "a column containing arrays of dmetaphone values, which are of length 1 or 2"): a LIST(VARCHAR) column. The level SQL is `array_length(list_intersect("<dm>_l", "<dm>_r")) >= 1`, inserted after the JW >= 0.88 levels and before JW >= 0.7. A NULL side makes the level NULL, which falls through to the next level. In DuckDB, `list_intersect(['KLMR',''], ['TRFN',''])` has length 1, so **drop empty codes** (`[c for c in doublemetaphone(s) if c] or None`) or two unrelated names with no secondary code will match. Compute codes in Python at ingest, store them as a list column, and use them in comparisons and blocking (`block_on("surname_dm[1]")`-style expressions are possible; not tested here).

## 9. Wilson score interval (question 9)

Formula (two-sided, confidence 1 - alpha, p = k/n, z = z_{1-alpha/2}; z = 1.959964 for 95 percent) [E17][E18]:

```text
centre     = (p + z^2 / (2n)) / (1 + z^2 / n)
half-width = (z / (1 + z^2 / n)) * sqrt( p(1 - p)/n + z^2 / (4 n^2) )
interval   = [centre - half-width, centre + half-width]
```

Authority: NIST/SEMATECH e-Handbook of Statistical Methods, section 7.2.4.1 "Confidence intervals", which gives these limits and notes that the method it once called Agresti-Coull is now called the Wilson method, citing Wilson (1927) and the recommendations of Agresti and Coull (1998) and Brown, Cai and DasGupta (2001) [E17]. Original: E. B. Wilson, "Probable Inference, the Law of Succession, and Statistical Inference", Journal of the American Statistical Association 22(158), 209 to 212, June 1927, doi:10.1080/01621459.1927.10502953 [E18].

Worked example, computed with `wilson.py` [E4]: 180 correct out of 200 labelled pairs, p = 0.900, z^2/n = 0.019207, centre = 0.90960 / 1.01921 = **0.8925**, half-width = **0.0419**, 95 percent interval **[0.8506, 0.9343]** (not centred on 0.900; the Wald interval would be the symmetric 0.900 plus or minus 0.042, [0.858, 0.942], and the handbook's cited authors recommend Wilson over it). As a check, the same code reproduces NIST's own one-sided example (p = 0.13, n = 200, lower limit 0.09577).

```python
from math import sqrt
from statistics import NormalDist

def wilson(k: int, n: int, conf: float = 0.95) -> tuple[float, float]:
    z = NormalDist().inv_cdf(1 - (1 - conf) / 2)
    p = k / n
    centre = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = (z / (1 + z * z / n)) * sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return centre - half, centre + half
```

Sample size for plus or minus 5 points at 95 percent (smallest n with Wilson half-width <= 0.05; Wald formula n = z^2 p(1-p)/0.05^2 in brackets) [E4]: p = 0.5: 381 (385); p = 0.7: 320 (323); p = 0.8: 245 (246); p = 0.9: 141 (139). Half-widths at p = 0.9: n = 100: 0.060; 200: 0.042; 400: 0.030. Recommendation: **label 400 pairs drawn uniformly at random from the pairs (or cluster memberships) above the threshold being published**, which covers the worst case. If precision is reported per score band or per source, each band needs its own 400. Publish k, n, the threshold and the interval, not just the point estimate.

## 10. Evaluating without labels, output size, TF tables (question 10)

- Without labels the docs offer heuristics, not metrics ("Evaluating a trained model is not an exact science") [E22]. Tools: `linker.evaluation.unlinkables_chart()` (share of records that cannot match themselves at each threshold, which shows data quality and gives a lower bound on missed links), `linker.visualisations.match_weights_histogram(df_predict, target_bins=30)`, `match_weights_chart()`, `m_u_parameters_chart()`, `parameter_estimate_comparisons_chart()` (stability across EM sessions), the EM session's `match_weights_interactive_history_chart()` (convergence), the comparison viewer for spot checks either side of the threshold, and cluster studio [E3][E22]. The threshold-selection tool needs labels.
- `predict(threshold_match_probability=0.5)` returns only pairs at or above the threshold (verified: the spike's output holds only p >= 0.01). The docs list this as a way to make Splink faster because it writes less [E8]. It does not reduce blocking cost: every blocked pair is still built in `__splink__blocked_id_pairs` and scored, which is where the 174M-pair run ran out of memory [E23]. Keep a low threshold (for example 0.01) only when the review UI or evaluation needs near-misses.
- TF tables need no separate registration for normal training and prediction: `ensure_term_frequencies_for_linker` computes `__splink__df_tf_<col>` the first time a TF column is needed and caches it on the linker [E3]. `compute_tf_table(col)` precomputes (and can be saved with `to_parquet`); `register_term_frequency_lookup(sdf, col)` reuses a stored table, for example to keep frequencies from the full population when scoring a small batch. The gist says TF is now joined at predict time, and `predict_within`/`predict_between` need TF tables registered or `tf_*` columns supplied [E6]. EM with `estimate_without_term_frequencies=True` is faster [E3].

## Sources

- [E1] PyPI JSON API, `https://pypi.org/pypi/<name>/json`, for splink, duckdb, sqlglot, pyarrow, jellyfish, rapidfuzz, rigour, metaphone, doublemetaphone, fuzzy, phonetics, pyphonetics, abydos, phonetic, phonetisch, talisman (versions, upload times, wheel tags, licences, requires_dist). Checked 2026-10-18.
- [E2] Splink GitHub repository, read-only clone of https://github.com/moj-analytical-services/splink (tags v4.0.17, v5.0.0; master at 12aee3fd, 2026-10-12): `CHANGELOG.md`, `pyproject.toml`, `uv.lock`, `.github/workflows/*.yml`, `mkdocs.yml`, `docs/` sources, `git log v5.0.0..origin/master`, `git diff v5.0.0 origin/master -- splink/`, and a v4.0.17 to v5.0.0 diff of public names and method signatures. Checked 2026-10-18.
- [E3] splink 5.0.0 wheel, https://pypi.org/project/splink/5.0.0/, installed and read: `splink/internals/duckdb/database_api.py`, `database_api.py`, `settings_creator.py`, `comparison_library.py`, `comparison_creator.py`, `linker.py`, `linker_components/*.py`, `estimate_u.py`, `dialects.py`, `connected_components.py`, `one_to_one_clustering.py`, `labelling_tool.py`, `html_utils.py`, `charts.py`, `term_frequencies.py`, `files/` templates. Checked 2026-10-18.
- [E4] Verified by running scripts in Python 3.14.6 (uv-managed CPython) with splink 5.0.0, duckdb 1.5.6, pyarrow 26.0.0, sqlglot 30.23.0, metaphone 0.6, jellyfish 1.3.0 (and 1.2.1 in a separate venv), rapidfuzz 3.14.6; pandas 3.0.6 and numpy 2.5.4 only in a second venv for the labelling tool: `sigs.py`, `sigs2.py`, `inspect_comparisons.py`, `er_spike.py`, `compare_runs.py`, `predict_columns.py`, `wilson.py` (kept in `/tmp/claude-0/-home-claude/0b4b6737-68ec-5e27-9a94-821f67f5d857/scratchpad/p2-er/scripts/`; run outputs in `.../p2-er/det2/`). Run 2026-10-18.
- [E5] Splink 5.0.0 release post, https://moj-analytical-services.github.io/splink/blog/2026/09/28/splink-500-released.html (source `docs/blog/posts/2026-09-28-splink-5-release.md`). Checked 2026-10-18.
- [E6] "Splink 5 changes so far" gist with the LLM agent prompt appendix, https://gist.github.com/RobinL/c6d56a27d8f83c40b6b09643c0fa5d14 (read via the web fetch tool; summaries and short quotes only). Checked 2026-10-18.
- [E7] Splink docs, Optimising DuckDB, https://moj-analytical-services.github.io/splink/topic_guides/performance/optimising_duckdb.html (live page and repository source). Checked 2026-10-18.
- [E8] Splink docs read from repository sources at master 12aee3fd (the blocking-tutorial and backends quotes also confirmed on the live pages): drivers of performance https://moj-analytical-services.github.io/splink/topic_guides/performance/drivers_of_performance.html ; blocking performance https://moj-analytical-services.github.io/splink/topic_guides/blocking/performance.html ; blocking tutorial https://moj-analytical-services.github.io/splink/demos/tutorials/03_Blocking.html ; backends https://moj-analytical-services.github.io/splink/topic_guides/splink_fundamentals/backends/backends.html ; parameter estimation tutorial https://moj-analytical-services.github.io/splink/demos/tutorials/04_Estimating_model_parameters.html . Checked 2026-10-18.
- [E9] Splink docs, phonetic algorithms https://moj-analytical-services.github.io/splink/topic_guides/comparisons/phonetic.html and feature engineering https://moj-analytical-services.github.io/splink/topic_guides/data_preparation/feature_engineering.html (repository sources). Checked 2026-10-18.
- [E10] splink_udfs repository, https://github.com/moj-analytical-services/splink_udfs (`LICENSE`, `README.md` via raw.githubusercontent.com); `INSTALL splink_udfs FROM community` attempted in duckdb 1.5.6. Checked 2026-10-18.
- [E11] DuckDB docs (1.5), Configuration overview, https://duckdb.org/docs/current/configuration/overview . Checked 2026-10-18.
- [E12] DuckDB docs (1.5), Tuning workloads, https://duckdb.org/docs/current/guides/performance/how_to_tune_workloads . Checked 2026-10-18.
- [E13] DuckDB docs (1.5), Environment, https://duckdb.org/docs/current/guides/performance/environment . Checked 2026-10-18.
- [E14] jellyfish changelog, https://github.com/jamesturk/jellyfish/blob/main/docs/changelog.md . Checked 2026-10-18.
- [E15] rigour 2.5.0 cp314 wheel, https://pypi.org/project/rigour/2.5.0/ (`rigour/text/phonetics.py`, `rigour/_core.pyi`). Checked 2026-10-18.
- [E16] Metaphone 0.6 sdist and LICENSE, https://pypi.org/project/Metaphone/0.6/ ; phonetics 1.0.5 sdist, https://pypi.org/project/phonetics/1.0.5/ ; pyphonetics 0.5.3 wheel, https://pypi.org/project/pyphonetics/0.5.3/ . Checked 2026-10-18.
- [E17] NIST/SEMATECH e-Handbook of Statistical Methods, 7.2.4.1 Confidence intervals, https://www.itl.nist.gov/div898/handbook/prc/section2/prc241.htm . Checked 2026-10-18.
- [E18] Wilson (1927), Crossref record https://api.crossref.org/works/10.1080/01621459.1927.10502953 (DOI https://doi.org/10.1080/01621459.1927.10502953). Checked 2026-10-18.
- [E19] Verified by running `netcheck.mjs` (same scripts folder) in Node 22.22.0 with headless Chromium 153 (`@sparticuz/chromium` 153.0.0, `puppeteer-core` 25.14.0 from the npm registry) on HTML generated by `er_spike.py --extras` in Python 3.14.6. Run 2026-10-18.
- [E20] Splink docs llms.txt, https://moj-analytical-services.github.io/splink/llms.txt , and `mkdocs.yml` `llmstxt` plugin settings. Checked 2026-10-18.
- [E21] Splink docs blog index and banner, https://moj-analytical-services.github.io/splink/blog/index.html (legacy docs https://moj-analytical-services.github.io/splink4_legacy_docs/). Checked 2026-10-18.
- [E22] Splink evaluation docs (repository sources): https://moj-analytical-services.github.io/splink/topic_guides/evaluation/model.html , .../topic_guides/evaluation/edge_overview.html , .../charts/unlinkables_chart.html ; the clerical labelling page says "This page is under construction". Checked 2026-10-18.
- [E23] Scale probes, verified by running `scale_spike.py` (same scripts folder; outputs in `.../p2-er/scale/`) in Python 3.14.6 with the package versions of [E4], on 2 vCPU and 7 GiB RAM. Run 2026-10-18.
- [E24] NeonRadar phase 1 research note `/home/claude/neonradar-phase1/kit/research/stack.md`, section 4 (written 2026-10-16).
