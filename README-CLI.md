# TE Evaluation Tool — CLI Documentation

This README focuses on the CLI experience only (commands, models, options and examples).
The API documentation will be provided in a separate section/file later — a placeholder for the API is kept below.

---

## Quick structure (CLI first)
- Commands
- Models (supported runners)
- Options and examples (per model)

> Tip: CLI entrypoint is `CLI/src/main.py`. From the repository root you can run CLI commands under `/app/CLI` (or run them directly inside the `CLI/` folder).

---

## Getting started — quick setup (CLI)

1. Enter the CLI folder:

```bash
cd CLI
```

2. Run the CLI using the environment that has Python 3.9 (or the container):

```bash
# inside project (normal local use)
python3 src/main.py --help

# inside the project's container (ex: when running via docker-compose)
docker-compose exec te_eval_api_container bash
cd /app/CLI
python3 src/main.py --help
```

---

## Quick-start — hands-on (copy/paste) ✅

These step-by-step commands will get you from zero to a completed run using the built-in demo input. You can run the CLI locally (requires Python 3.9 and the CLI dependencies) or inside the project's docker container.

1) Quick local run (ClassifyTE) — runs a complete classification using the demo FASTA and writes outputs to ./data/results/run_demo_classifyte

```bash
cd CLI
python3 src/main.py run \
  --model classifyte \
  --input ./src/data/demo_features.fasta \
  --output $(pwd)/data/results/run_demo_classifyte \
  --model-file ClassifyTE_combined.pkl \
  --auto-label -v
```

Validation after run (check outputs):

```bash
ls -l data/results/run_demo_classifyte
head -n 5 data/results/run_demo_classifyte/predicted_results.csv
cat data/results/run_demo_classifyte/metrics_summary.json
```

2) Quick container run (YORO example) — run inside docker-compose environment where CLI lives at /app/CLI

```bash
docker-compose exec te_eval_api_container bash
cd /app/CLI
python3 src/main.py run \
  --model yoro \
  --input ./src/data/demo_features.fasta \
  --output /app/data/results/run_yoro_quick \
  --model-file ./src/models/YORO/models/AAqqYOLOqqdomainqqV25.hdf5 \
  --auto-label -v
```

Check results inside the container:

```bash
ls -la /app/data/results/run_yoro_quick
head -n 10 /app/data/results/run_yoro_quick/predicted_results.csv
```

3) Run TERL quickly (if TERL models are available in the repo)

```bash
cd CLI
python3 src/main.py run \
  --model terl \
  --input ./src/data/demo_features.fasta \
  --output $(pwd)/data/results/run_terl_quick \
  --model-file DS3 -v
```

If the demo run produces output files, the CLI will create `predicted_results.csv`, and may also produce metric files and an `evaluation_report.txt` when ground-truth labels are present or `--auto-label` is used.

---

## Commands (overview)

Primary commands of the CLI and examples of intent:

- run — execute classification using a model runner (classifyte, terl, yoro)
- map-labels — map FASTA headers to hierarchical labels or attach labels to predictions
- evaluate — compute evaluation metrics for a predictions CSV
- env — environment lifecycle: setup, list, clean
- compare, examples, validate, info — utility and diagnostic commands

Each command accepts a set of model-specific options and general options (like `--output`, `--verbose`, `--auto-label`, `--clean`). The `run` command is the main entrypoint for executing a model pipeline.

---

## Supported Models (runners)

The CLI supports multiple model runners. Each runner is invoked by `--model <model-name>`.

1) classifyte — ClassifyTE runner (stacking / hierarchical classifier)
2) terl — TERL runner (CNN-based)
3) yoro — YORO runner (deep-learning object detection pipeline for domains)

Below you find details and examples for each model.

---

## CLI Usage (common pattern)

The canonical invocation for classification is:

```bash
python3 src/main.py run \
  --model <model> \
  --input /abs/path/your_input.fasta \
  --output /abs/path/results_dir \
  [model-specific options]
```

Notes:
- `--input` accepts a FASTA file. When invoked from the API the CLI receives pre-saved uploaded files.
- `--output` is optional; the CLI will generate a timestamped directory under `data/results` if omitted.
Notifications (email) are provided through the API only — the CLI does not accept an email/notification flag.

---

## Model: ClassifyTE (example)

Purpose: hierarchical classification using stacked features.

Common options (run command):
- --model classifyte
- --input <FASTA>
- --output <DIR> (optional)
- --model-file <PKL> (default: ClassifyTE_combined.pkl)
- --algorithm <lcpnb|nllcpn> (hierarchical algorithm; default: lcpnb)
- --node-file <node.txt> (hierarchy nodes file)
- --auto-label (boolean; attempt to map FASTA headers to produce Actual_Label for evaluation)
- --skip-evaluation (boolean)

Example:

```bash
cd CLI
python3 src/main.py run \
  --model classifyte \
  --input ./src/data/demo_features.fasta \
  --output /app/data/results/run_classifyte_demo \
  --model-file ClassifyTE_combined.pkl \
  --algorithm lcpnb \
  --auto-label -v
```

What you get:
- predicted_results.csv
- predicted metrics (if evaluation runs)
- evaluation_report.txt and metrics_summary.json (if skip-evaluation not set and actual labels exist)

---

## Model: TERL (example)

Purpose: CNN-based classification pipeline that accepts a TERL model reference. TERL models can be a directory (e.g., DS3) or a path in `CLI/src/models/TERL/Models`.

Common options (run command):
- --model terl
- --model-file <DS_FOLDER | absolute_path_to_model_dir> (default: DS3 if omitted when model=terl)
- --input, --output, --auto-label, --skip-evaluation, --verbose as usual

Example using DS3:

```bash
cd CLI
python3 src/main.py run \
  --model terl \
  --input ./src/data/demo_features.fasta \
  --output /app/data/results/run_terl_demo \
  --model-file DS3 \
  --auto-label -v
```

Notes:
- If you pass `--model-file DS1..DS5` the CLI will resolve the path under `CLI/src/models/TERL/Models`.

---

## Model: YORO (example)

Purpose: object detection style neural pipeline that detects domains (suitable for LTR-retrotransposon domain detection).

Important YORO-specific options (run command):
- --model yoro
- --model-file <path-to-hdf5> (default in repo: `./src/models/YORO/models/AAqqYOLOqqdomainqqV25.hdf5`)
- --window <int> (default 50000) — detection window size
- --threads <int> — number of processing threads (if omitted, pipeline uses all cores)
- --threshold <float> (default 0.8) — presence threshold for detection
- --cycles <int> (default 1) — number of cycles to run detection
- --auto-label — enable automatic mapping of predicted labels back to FASTA headers

Example:

```bash
cd CLI
python3 src/main.py run \
  --model yoro \
  --input ./src/data/demo_features.fasta \
  --output /app/data/results/run_yoro_demo \
  --model-file ./src/models/YORO/models/AAqqYOLOqqdomainqqV25.hdf5 \
  --window 50000 \
  --threads 4 \
  --threshold 0.8 \
  --cycles 1 \
  --auto-label -v
```

What to expect:
- YORO writes `yoro_temp/output.tab` in the output path
- the runner converts to `predicted_results.csv` and optionally maps actual labels and runs evaluation

---

## Common options (summary)

- `--input` — path to input FASTA (required)
- `--output` — directory where outputs are placed (optional; auto-generated under `data/results`)
- `--model-file` — model or model path (model-specific default values apply)
Note: email notifications are available through the API only; the CLI does not include a `--notification-email` flag.
- `--verbose` / `-v` — more detailed console output
- `--clean` / `--clean-temp` — remove temporary files after run (CAN be forced by the API)
- `--auto-label` — attempt to derive Actual_Label values from the FASTA
- `--skip-evaluation` — do not calculate metrics after predictions

### Flags reference (quick table)

Flag | Type | Default | Applies to | Description
---|---:|:---:|:---:|---
`--model` | string | `classifyte` | run | Choose runner: classifyte, terl, yoro
`--input` | path | — | all | Input FASTA or CSV (required)
`--output` | path | auto under `data/results` | all | Output directory for run artifacts
`--model-file` | path/string | per-run default | all | Path or reference to the chosen model (e.g., V25.hdf5 or DS3)
`--node-file` | file | `node.txt` | classifyte | Hierarchy nodes file used by classifiers
`--algorithm` | choice | `lcpnb` | classifyte | Hierarchical algorithm (lcpnb|nllcpn)
`--auto-label` | flag | false | all | Attempt automatic mapping from FASTA headers
`--skip-evaluation` | flag | false | all | Skip post-run evaluation/metrics
`--clean` / `--clean-temp` | flag | false | all | Remove temporary working files after run
`--verbose` / `-v` | flag | false | all | Increase console output verbosity
`--format` | choice | `fasta` | validate | Specify validation input format (fasta|csv)
`--validate-only` | flag | false | map-labels | Run mapping checks without writing outputs

YORO-specific flags:

Flag | Type | Default | Description
---|---:|:---:|---
`--window` | int | 50000 | Detection window size (bases)
`--threads` | int | all cores | Number of threads for detection
`--threshold` | float | 0.8 | Detection confidence threshold
`--cycles` | int | 1 | How many detection cycles to run

TERL-specific notes:
- `--model-file` accepts either a DS reference (DS1..DS5) resolved under `CLI/src/models/TERL/Models` or an absolute model directory.


---

## Notes & best practices

- Use absolute paths when passing `--input` and `--output` (especially in containerized environments).
- `--auto-label` only works when FASTA headers contain recognizable labels or when the runner can map them.

---

## FASTA header formats (map-labels)

The `map-labels` command is used to attach ground-truth labels to prediction CSV files by parsing FASTA headers. The CLI supports three common header styles — structured (new), legacy (pipe-separated) and simple/named headers (for which the mapper attempts an inference).

How mapping works
- The mapper reads FASTA headers and extracts a "pure" sequence id (the first token after the '>' character). It then attempts to parse structured classification fields from the header.
- The command will create an augmented predictions CSV where the columns `Actual_Label` and `Actual_Code` are added when a mapping is found. It joins on `Sequence ID` (column name expected in the predictions CSV) — predictions must include a `Sequence ID` column with values matching the FASTA IDs.

Supported header styles and examples

1) New (colon-separated) format — recommended when available

Format: >ID:Class:Order:Family

Example header lines:
```
>ATRAN:ClassI:LTR:Copia
>BEL-7_Adi-I:ClassI:LTR:Bel-Pao
>hAT-236_Ami:ClassII:TIR:hAT
```

Effect: Values are parsed into class/order/family exactly as typed and mapped to a hierarchical code (via `src/nodes/tree.txt`) when available.

2) Legacy/pipe-separated format

Format: >ID|Class|Order|Family

Example header lines:
```
>AACOPIA1_I|ClassI|LTR|Copia
>hAT-9_XT|ClassII|TIR|hAT
```

Effect: Behaves like the colon format — fields are picked up using the '|' separator.

3) Simple or minimal headers — inference fallback

Format: >ID or >ID <free text>

Example headers:
```
>ATRAN
>TE_family_Copia_XYZ
>LINE1_element
```

Effect: When no explicit classification is present, the mapper uses a small set of string patterns and heuristics to guess the class/order/family. Common patterns include (non-exhaustive):
- copia, gypsy, bel, pao, erv -> LTR families (ClassI)
- line, l1, rte, jockey -> LINE family (ClassI)
- sine, trna, 5s, 7sl -> SINE family (ClassI)
- hat, tc1, mariner, piggyb, mutator, pif, merlin, transib -> TIR / ClassII families

If no patterns match, the mapper will mark the classification as `Unknown`, and the resulting prediction file will not contain an `Actual_Code` for those records.

What the predictions CSV must contain
- The predictions CSV expected by `map-labels` should include an ID column named `Sequence ID` (or a column your runner produces that you map to `Sequence ID` before merging). The mapper will perform a left-join: all predictions are preserved and matching FASTA 'Sequence ID' rows will receive `Actual_Label` and `Actual_Code`.

Example usage (map-labels):
```
python3 src/main.py map-labels \
  --fasta /path/to/headers.fasta \
  --predictions /path/to/predictions.csv \
  --output /app/data/results/mapped_predictions.csv
```

The command will return (and write) an updated CSV where each prediction row has `Actual_Label` and `Actual_Code` when a mapping was found.

Validation-only mode
- Use `--validate-only` to run the header parsing and mapping checks without writing an output CSV. This is useful for verifying your headers are consumable before merging with predictions.

Troubleshooting and best practices
- Use well-structured headers whenever possible — colon (:) or pipe (|) formats produce the most reliable mappings.
- Keep FASTA IDs stable (avoid changing the first token) so mapping by `Sequence ID` succeeds.
- When mapping fails, inspect the FASTA header lines and `src/nodes/tree.txt` (hierarchy) to ensure labels are present and match expected names.


---

## Result files — what the CLI produces

When you run a model the CLI and model runners produce several artifacts. Below is a quick breakdown of the most common output files, where to find them and what they contain.

Top-level layout (per run):
- {output_dir}/                         # directory you passed via --output, or auto-generated under data/results/run_<timestamp>
  - predicted_results.csv               # unified CSV with predictions (and mapped actual labels when available)
  - metrics_summary.json                # small JSON summary of high-level metrics (accuracy / f1 / counts)
  - detailed_metrics.json               # large JSON with every computed metric and per-class stats
  - evaluation_report.txt               # human-readable text report with executive summary and metric tables
  - yoro_temp/                          # (YORO only) temporary working files for the YORO pipeline
    - output.tab                        # raw YORO tabular detection output
    - sanitized_input.fasta             # sanitized FASTA used by YORO
    - test/testResults_*.csv            # YORO test reports (internal, optional)

Notes for each file
- predicted_results.csv
  - CSV produced by runners in a common format: at least these columns: `Sequence ID`, `Predicted label`, `Final_Confidence_Score`.
  - When `--auto-label` or map-labels are used, rows will include `Actual_Label` and `Actual_Code` columns.

- metrics_summary.json
  - Small JSON summarizing key metrics (accuracy, f1_macro, recall_macro, num_classes, total_samples).
  - Useful for dashboards and quick comparisons.

- detailed_metrics.json
  - Full metrics dump (per-class precision/recall/F1, confusion matrix, hierarchical metrics, auROC/mAP when available).
  - Format is JSON, values may include matrices and nested objects per-class.

- evaluation_report.txt
  - Human-friendly, formatted text file with: executive summary (overall accuracy, hierarchical metrics), per-class tables, additional notes.
  - Ideal to attach to reports or to include in supplementary materials.

- YORO-specific: yoro_temp/
  - The YORO runner performs several preprocessing steps and writes a small working folder `yoro_temp` inside output_dir.
  - raw `output.tab` is the first produced file (the detection pipeline output). The runner converts this to `predicted_results.csv` and optionally does automatic mapping and evaluation.

---

## Workflows — end-to-end examples (run → map-labels → evaluate) 🧭

These practical workflows contain commands you can copy/paste to run full experiments, validate results, debug common problems (especially YORO), and mix work between API and CLI.

1) Typical full workflow — run, map labels, evaluate

```bash
# 1) Run the model (classifyte example)
cd CLI
python3 src/main.py run \
  --model classifyte \
  --input ./src/data/demo_features.fasta \
  --output $(pwd)/data/results/e2e_classifyte \
  --auto-label -v

# 2) Map labels (if you ran without --auto-label or want to ensure ground-truth merge)
python3 src/main.py map-labels \
  --fasta ./src/data/demo_features.fasta \
  --predictions $(pwd)/data/results/e2e_classifyte/predicted_results.csv \
  --output $(pwd)/data/results/e2e_classifyte/predicted_results_mapped.csv

# 3) Evaluate (explicit evaluate command — useful when mapping or inputs are separate)
python3 src/main.py evaluate \
  --predictions $(pwd)/data/results/e2e_classifyte/predicted_results_mapped.csv \
  --output $(pwd)/data/results/e2e_classifyte

# Quick checks
ls -la data/results/e2e_classifyte
tail -n +1 data/results/e2e_classifyte/predicted_results_mapped.csv | head -n 5
cat data/results/e2e_classifyte/metrics_summary.json
```

2) Debugging / inspecting YORO internals (useful if runs fail or predictions look odd)

```bash
# run the YORO job (keeps temp by default only if --clean avoided)
cd CLI
python3 src/main.py run \
  --model yoro \
  --input ./src/data/demo_features.fasta \
  --output $(pwd)/data/results/e2e_yoro_debug \
  --model-file ./src/models/YORO/models/AAqqYOLOqqdomainqqV25.hdf5 \
  -v

# Inspect YORO internals
ls -la data/results/e2e_yoro_debug/yoro_temp
head -n 10 data/results/e2e_yoro_debug/yoro_temp/output.tab
head -n 30 data/results/e2e_yoro_debug/yoro_temp/sanitized_input.fasta
# Inspect test outputs (if present)
ls -la data/results/e2e_yoro_debug/yoro_temp/test || true
```

3) Reproduce & debug runs using CLI only — (local & container) ✅

If you use the API in production, a common debugging step is to reproduce the same job locally with the CLI so you can inspect files, logs and intermediate outputs. The examples below show how to reproduce and compare runs entirely with the CLI (no API commands).

```bash
# 1) Reproduce a run locally using the absolute path to the original FASTA
cd CLI
python3 src/main.py run \
  --model classifyte \
  --input /absolute/path/to/original/my_fasta.fasta \
  --output /absolute/path/to/debug/output_dir \
  --auto-label -v

# 2) Re-map labels and re-evaluate (useful after reproducing or modifying headers)
python3 src/main.py map-labels --fasta /absolute/path/to/original/my_fasta.fasta --predictions /absolute/path/to/debug/output_dir/predicted_results.csv --output /absolute/path/to/debug/output_dir/predicted_results_mapped.csv
python3 src/main.py evaluate --predictions /absolute/path/to/debug/output_dir/predicted_results_mapped.csv --output /absolute/path/to/debug/output_dir

# 3) Re-run inside container (if you need the exact container environment)
docker-compose exec te_eval_api_container bash
cd /app/CLI
python3 src/main.py run --model yoro --input /app/CLI/src/data/demo_features.fasta --output /app/data/results/debug_yoro_repro --model-file ./src/models/YORO/models/AAqqYOLOqqdomainqqV25.hdf5 -v

# 4) Compare artifacts between your debug run and the production results (copy both to a shared location if needed)
ls -la /absolute/path/to/debug/output_dir
ls -la /app/data/results/debug_yoro_repro
```

Validation tips after any run
- Verify `predicted_results.csv` exists and contains `Sequence ID`, `Predicted label`, `Final_Confidence_Score`.
- If results include `Actual_Label` and `Actual_Code`, the evaluation will run automatically (unless `--skip-evaluation` was passed).
- For YORO inspect `yoro_temp/output.tab` to ensure the detection pipeline produced rows (and check for header/format issues).

---

Examples — check these locations after a run:
```
/app/data/results/run_1701000000000/predicted_results.csv
/app/data/results/run_1701000000000/detailed_metrics.json
/app/data/results/run_1701000000000/evaluation_report.txt
/app/data/results/run_1701000000000/yoro_temp/output.tab
```
