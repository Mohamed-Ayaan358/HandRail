# Quality pilot (Phase 0)

This is an experiment, not the browser extension. It measures reconstruction of missing accessible names from public static HTML. Phase 0 stays open until the benchmark and screen-reader-user review are complete.

## Run locally

On this Mac, dependencies are already installed. `./pilot/run.sh test` and `./pilot/run.sh collect --list-id PY96J` use the existing Codex Node runtime when `node` is not on PATH. Inference commands below use the installed `python3`. For other machines, install the standard prerequisites first.

Requirements: Node.js 20+, pnpm 11.19.0, Python 3.11+, and Ollama. No Python packages are needed for the core experiment. Node dependencies are pinned in `pnpm-lock.yaml`.

```sh
pnpm install --frozen-lockfile
pnpm test
```

On this Mac, Ollama 0.34.2 was installed in the ignored `.local/ollama` directory and Qwen2.5 1.5B Q4_K_M downloaded into `.local/models`. Nothing was installed system-wide. Start the server in one terminal:

```sh
./pilot/serve.sh --cpu
```

CPU mode worked in the initial Codex session; Metal initialization failed there. In a normal terminal you can omit `--cpu` to try hardware acceleration. Do not mix backend settings within one result directory. To download the model on a fresh installation, use `.local/ollama/ollama pull qwen2.5:1.5b` (or `ollama pull qwen2.5:1.5b` for a system installation) while the server is running.

Then, from another terminal:

```sh
python3 pilot/evaluate.py run --mode rules --out pilot/results/runs/rules
python3 pilot/evaluate.py run --mode cascade --cpu --out pilot/results/runs/cascade
# Optional ablation: bypass deterministic rules for every item.
python3 pilot/evaluate.py run --mode text --cpu --out pilot/results/runs/text
```

A repeated command resumes a matching run. `--reuse path/to/prior-run` can reuse already measured rows from a smaller dataset with the exact same configuration; inputs and references are checked before reuse. A changed dataset, code, prompt, model digest, threshold, or backend requires a new output directory. Each row is flushed to disk; a partially written final JSON line should be removed before resuming after an interrupted disk write. Errors are recorded and counted, never silently turned into successful labels. Use a fresh output directory to retry failed inference.

## Collect a benchmark

The initial ranking is Tranco list **PY96J**. The download is an explicit network operation; inference calls only `127.0.0.1:11434` and ignores HTTP proxy environment variables.

```sh
curl -fL https://tranco-list.eu/download/PY96J/1000000 -o pilot/data/tranco.csv
pnpm pilot:collect --list-id PY96J
```

The collector uses a fixed seed of 42 and aims for 50 homepages from ranks 1-1000 and 50 from ranks 1001-1,000,000, with 10 unique eligible elements per page (1,000 total). It samples up to 600 candidate domains per stratum and records every success or exclusion. `corpus.jsonl` and `collection.json` are checkpointed and collection resumes from them. Use `--out` with a new directory to start over. A shortfall remains a shortfall; no generated fixtures fill the quota.

Requests use an identifiable user agent and respect the starting page's robots policy. Robots errors other than 404 skip a domain. Cross-domain redirects are excluded. Fetch sizes, network timeouts, worker memory, and extraction time are bounded. No cookies, logged-in sessions, scripts, external stylesheets, or page actions are used.

The extractor computes names using `dom-accessibility-api`, saves the original reference separately, removes `aria-label`, `aria-labelledby`, and `alt` from the candidate subtree, and recomputes the name. Only elements now unnamed enter the corpus. It preserves naturally named controls, skips hidden/inert elements, removes scripts and handlers from model input, and strips URL query strings and fragments. Repeated identical sanitized controls within one page are deduplicated. Model input is an explicit allowlist of kind, masked markup, and context; the reference never enters the generation prompt.

These filters bias the sample toward accessible, server-rendered sites with at least ten explicit labels. The reference is an existing author label, not verified ground truth. This is not a representative measurement of all web controls. Visibility based on external CSS, dynamic state, shadow DOM, rendered frames, and non-standard clickable elements is not evaluated. Image elements are tested from markup only; **no vision model is evaluated**.

## What is measured

- Exact and normalized reference-label match over **all** items.
- Coverage at a configurable confidence threshold (default 0.8), plus normalized match among accepted labels.
- Per-tier counts, errors, and wall-clock p50/p95; cold starts remain included and model load time is retained separately.
- A small deterministic icon/tooltip baseline, and a rules-to-Qwen cascade. This is not the planned 1,500-icon production dictionary.

Confidence is the model's own uncalibrated estimate. English destructive-action hints raise the threshold to 0.9; this heuristic is incomplete and is not a production safety guarantee. The harness never applies labels to a live page. Empty, generic, malformed, overlong, truncated, and invalid-confidence outputs are withheld. Potential prompt injection text is treated as untrusted evidence by the system prompt.

## Human review and decision

Each run writes `review.csv` with up to 200 items sampled with seed 42, including abstentions. Open `pilot/review.html` in a browser and load that CSV for an offline, keyboard-accessible review form, or edit the CSV directly. Download your edits and pass the downloaded path to `--csv`; the form does not save automatically. Have screen reader users fill `rating`, `misleading` (`yes` or `no`), a reviewer identifier, and optional notes. Identifiers should be pseudonyms. Formula-like source strings are escaped for spreadsheet safety.

Use the reference and markup/context to assess intent; where the reference is itself wrong or context insufficient, record that in notes. Do not fabricate intent to favor a prediction.

| Rating | Meaning |
| --- | --- |
| 1 | No accepted label, unusable, or wrong action |
| 2 | Major information missing or likely confusing |
| 3 | Partially useful, but important context missing |
| 4 | Correct and useful, with minor wording issues |
| 5 | Correct, concise, and natural |

"""
Tranco
(big ranked list of websites)
↓
collect.mjs
(picks websites + downloads their HTML)
↓
extract.mjs
(finds labeled controls, hides their labels, creates test examples)
↓
corpus.jsonl
(the 1,000-item test dataset)
↓
evaluate.py
(runs HandRail on the dataset)
↓
rules/
(rules only)

text/
(Qwen only)

cascade/
(rules first, Qwen if rules fail)
↓
predictions.jsonl
(all predictions for every item)
↓
summary.json
(overall scores + timing + coverage)
↓
report.md
(readable experiment summary)
↓
review.csv
(200 random examples for human review)
↓
review.html
(simple browser form to rate those 200)
↓
evaluate.py review
(reads human ratings and decides GO / NO-GO)
"""

