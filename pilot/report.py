#!/usr/bin/env python3
"""Produce an aggregate Markdown report without publishing raw page snippets."""
import argparse
import collections
import json
from pathlib import Path
import evaluate as core

def metrics(rows):
    m=core.summarize(rows)
    return f"{m['items']} | {m['coverage']:.1%} | {m['normalized_match_all']:.1%} | {m['latency_ms_p50']:.0f} | {m['latency_ms_p95']:.0f}"

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--rules',default='pilot/results/runs/rules');p.add_argument('--cascade',default='pilot/results/runs/cascade');p.add_argument('--collection',default='pilot/data/collection.json');p.add_argument('--out',default='pilot/results/INITIAL_PILOT.md');a=p.parse_args()
    runs={name:[json.loads(l) for l in (Path(path)/'predictions.jsonl').read_text().splitlines() if l] for name,path in [('Rules',a.rules),('Cascade',a.cascade)]}
    meta=json.loads((Path(a.cascade)/'metadata.json').read_text());collection=json.loads(Path(a.collection).read_text())
    rows=runs['Cascade'];baseline=runs['Rules']
    if {r['id'] for r in rows}!={r['id'] for r in baseline} or len(rows)!=collection['records']:raise ValueError('Incomplete or mismatched runs')
    if not (Path(a.cascade)/'summary.json').exists():raise ValueError('Cascade run has not finished')
    errors=collections.Counter(r['error'] for r in rows if r['error']);kinds=collections.Counter(r['kind'] for r in rows)
    accepted=[r for r in rows if r['accepted']];high=[r for r in accepted if r['confidence']>=.9]
    highmatch=sum(core.normalized(r['prediction'])==core.normalized(r['reference']) for r in high)/len(high) if high else 0
    table=['| Run | Items | Accepted coverage | Normalized match, all items | p50 ms | p95 ms |','| --- | ---: | ---: | ---: | ---: | ---: |']+[f'| {name} | {metrics(rs)} |' for name,rs in runs.items()]
    groups=['| Group | Items | Accepted coverage | Normalized match, all items | p50 ms | p95 ms |','| --- | ---: | ---: | ---: | ---: | ---: |']
    for name,group in [('Images (markup only)',[r for r in rows if r['kind']=='img']),('Controls',[r for r in rows if r['kind']!='img']),('Top 1,000',[r for r in rows if r['source']['stratum']=='top']),('Long tail',[r for r in rows if r['source']['stratum']=='long-tail'])]:
        groups.append(f'| {name} | {metrics(group)} |')
    manifest={'ranking':collection['list_id'],'attempted_domains':len(collection['attempts']),'accepted_pages':sum(bool(r.get('accepted')) for r in collection['attempts']),'exclusion_reasons':dict(collections.Counter(r.get('error','') for r in collection['attempts'] if not r.get('accepted'))),'element_kinds':dict(kinds),'model':meta['config']['model'],'model_digest':meta['config'].get('model_digest'),'ollama_version':meta['config'].get('ollama_version'),'dataset_sha256':meta['config']['dataset_sha256'],'prompt_sha256':meta['config']['prompt_sha256'],'code_sha256':meta['config']['code_sha256'],'platform':meta['platform'],'cpu_requested':meta['config']['cpu_requested']}
    report=f'''# Initial HandRail quality pilot

**Phase 0 status: automated text pilot finished; final decision pending human review.**

The fixed benchmark contains {len(rows):,} masked elements from {manifest['accepted_pages']} public homepages, split equally between Tranco's top 1,000 and lower-ranked domains. The run compares a small icon/tooltip baseline with that baseline plus Qwen2.5 1.5B Q4_K_M through local Ollama. No labels were injected into live pages.

## Results

{chr(10).join(table)}

{chr(10).join(groups)}

“Normalized match” is lexical agreement with the site's original label after Unicode normalization, case folding, punctuation removal, and whitespace normalization. It is **not semantic accuracy**: different valid wording can mismatch, and an original site label may itself be poor. Accepted coverage means the harness would accept the label under its confidence rule; it does not mean the label is correct.

There were {len(high)} accepted predictions with confidence >=0.9; their normalized reference match was {highmatch:.1%}. Self-reported confidence alone is not sufficient evidence of correctness. The small rules baseline is not the proposed 1,500-icon production map, so its coverage does not validate or refute the design's full Tier 0 coverage estimate.

Latency is single-request wall time on this Mac in **CPU mode**, including validation and any model-load time. It is not extension end-to-end latency or a GPU benchmark. The interrupted top-stratum run was reused only after checking exact configuration and inputs; already measured rows were not regenerated. A warm-up smoke run preceded the benchmark.

## Rejected outputs and failures

```json
{json.dumps(dict(errors),indent=2)}
```

Validation rejections are withheld predictions, not transport failures. Both remain in the denominator. Confidence thresholds are 0.8 generally and 0.9 when the English destructive-action heuristic fires. These uncalibrated thresholds are experimental.

## Interpretation and next decision

Do not enable automatic label injection based on this run. The experiment exposes a need to evaluate semantics and confidence calibration before shipping. Image descriptions cannot be established reliably from markup alone; {kinds.get('img',0)} items in this sample are images, and no vision model saw their pixels. Controls and images should be assessed separately in the next iteration.

The 200-item fixed random review sheet is at `runs/cascade/review.csv`. Open `../review.html`, load that CSV, and have screen reader users rate it. The required gate is >=75% rated 4/5 or better and <5% misleading; no such ratings have been supplied or invented. The script will remain PENDING until the review is complete. Automated judge/BERTScore adapters are implemented but were not run because their separate models and dependencies are not installed.

After the human review, decide whether to refine the prompt/rules and evaluate on a fresh holdout, add the vision tier for image cases, or stop automatic injection and retain report-only suggestions. Do not tune on this benchmark and report a re-run as independent validation.

## Collection limitations

Only public static HTML was used, with scripts disabled and robots restrictions observed. Pages without ten eligible explicit-name examples were excluded; unreachable, blocked, redirected, and resource-heavy pages were also excluded. This biases the sample toward accessible server-rendered pages. External CSS, dynamic states, shadow DOM, browser frames, actual focus behavior, and screen reader interaction are untested. The original label is a reference, not human-verified ground truth.

Raw snippets and model outputs remain in ignored local files. This report contains aggregates only. Model assets and raw samples should not be committed by a blanket force-add.

## Reproduction record

```json
{json.dumps(manifest,indent=2,ensure_ascii=False)}
```

See [pilot instructions](../README.md) for commands, scoring rubric, and run artifacts. The collected corpus is required for exact inference reproduction; re-crawling can produce different data as sites change.
'''
    Path(a.out).write_text(report);print(a.out)
if __name__=='__main__':main()
