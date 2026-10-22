# Does compressing context hurt Codex's code edits?

**Question.** If you squeeze what a coding agent keeps in context, either by compacting (summarizing) the history aggressively or by truncating the file and tool output it reads, does it get worse at making code edits? And what does it do to tokens? (Originally planned on Claude; run on Codex CLI here.)

**Short answer (this build, these tasks).** **No success cost: 66/66 runs passed** (22/22 per arm). Neither form of compression saved anything either:
- **Aggressive compaction** (auto-compact at 14K tokens) compacted 3 times in every run, so each run made 7 model calls instead of 4. Total tokens fell 4% (61.1K → 58.7K) but estimated cost rose 6% ($0.0215 → $0.0228 per run) and wall time more than doubled (23 s → 52 s).
- **Truncated file/tool output** (prompt rule: every shell call's `max_output_tokens` ≤ 24) made the agent read files in slices: 5.2 calls instead of 4.1, total tokens **+29%** (78.8K), estimated cost **+20%** ($0.0257), with much higher spread.

On small edit tasks the context is mostly Codex's fixed ~13–15K-token system prompt, so there's nothing to compress. Compression only adds calls. All $ figures are *estimates*.

## Setup

- Codex CLI `codex-cli 0.162.1`, model `gpt-6.1-sol`, default reasoning effort, ChatGPT Plus login. Headless `codex exec --json --skip-git-repo-check --dangerously-bypass-approvals-and-sandbox -C <fresh temp copy>`, one fresh session per run.
- Tasks: the 11 edit tasks `T01`–`T11` from the shared harness (`scripts/harness/fixtures/suite/T*`): happy-path fix, duplicate block, whitespace, tabs, stale snapshot, near-duplicate lines, multi-hunk, insert, delete, replace-all, short-context. Each is one small `broken.js` plus `test.js`.
- Pass = `node test.js` exits 0 in the run's copy **and** `test.js` is unchanged (hash check).
- Arms (11 tasks × 2 reps = 22 runs each, interleaved and run 3 at a time):
  - `default`: prompt ``Make `node test.js` pass by fixing the code. Do not edit test.js.``
  - `compact14k`: same prompt, `-c model_auto_compact_token_limit=14000`. A fresh session's first request is ~13–15K tokens, so 14K forces compaction after almost every step. Picked after a 1-run probe (`results/probe/`, excluded).
  - `trunc24`: same prompt plus ``Hard rule: every exec_command call must set max_output_tokens to 24 or less.`` This is the way to truncate file/tool output that actually works in this build: my [tool-output caps experiment](https://github.com/nankris/tool-output-caps) showed the `tool_output_token_limit` config key has no effect here, because the model sets `max_output_tokens` on every call. The model obeyed in every run (requested values logged in `results/rollout_extra.csv`), and Codex inserted ~3 "truncated output" notices per run.
- Cost estimate: gpt-6.1-sol API list price $2.00/M uncached input, $0.10/M cached input, $10.00/M output (https://developers.openai.com/api/docs/models/gpt-6.1-sol, checked 2026-10-14). **Estimates only**; Plus is a flat subscription.

## Exact commands

```bash
# optional: activate your own Python/Codex environment first
# one run
python3 scripts/harness/run_one.py --exp . --cond compact14k --task scripts/harness/fixtures/suite/T07_multihunk --rep 1 \
  --cfg model_auto_compact_token_limit=14000 --timeout 420
# all 66 runs (scripts/jobs.txt), 3 in parallel
scripts/harness/driver.sh scripts/jobs.txt 3 results/driver.log
# per-run extras from the session rollouts, then tables + chart
python3 scripts/rollout_extra.py results/runs.csv results/rollout_extra.csv
python3 scripts/analyze.py
```

## Results (66 runs, 2026-10-14 19:34–19:47 UTC / 2026-10-15 01:04–01:17 IST)

| Arm | Runs | Pass | Total tokens (mean ± sd) | Cached | Uncached | Output | Model calls | Compactions | Peak context | Wall | Est. cost / run (sd) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| default | 22 | 22/22 | 61.1K ± 5.4K | 54.2K | 6.6K | 293 | 4.09 | 0 | 15.4K | 22.6 s | $0.0215 ($0.0043) |
| compact14k | 22 | 22/22 | 58.7K ± 2.8K | 51.1K | 7.3K | 312 | 7.00 | 3.0 | 14.8K | 51.6 s | $0.0228 ($0.0041) |
| trunc24 | 22 | 22/22 | 78.8K ± 16.1K | 71.1K | 7.3K | 392 | 5.18 | 0 | 15.8K | 28.8 s | $0.0257 ($0.0108) |

Mean total tokens per task (K):

| Task | default | compact14k | trunc24 |
|---|---|---|---|
| T01_happy | 66.6 | 58.0 | 58.3 |
| T02_duplicate | 59.0 | 64.7 | 82.8 |
| T03_whitespace | 58.8 | 57.8 | 66.3 |
| T04_tabs | 58.9 | 57.9 | 73.7 |
| T05_stale | 58.8 | 58.4 | 81.6 |
| T06_neardup | 59.2 | 58.2 | 89.5 |
| T07_multihunk | 58.9 | 58.1 | 100.6 |
| T08_insert | 58.8 | 58.1 | 66.2 |
| T09_delete | 66.6 | 58.0 | 73.5 |
| T10_replace_all | 59.2 | 58.1 | 82.1 |
| T11_shortctx | 66.8 | 58.0 | 92.2 |

Chart: `results/chart.png` (pass rate, total tokens, est. cost, model calls per arm; dots are runs).

### What the numbers say
1. **Success didn't move.** 100% in every arm. Even when every shell call got only 24 tokens of output and the history was summarized three times per run, Codex still made correct edits without touching the tests.
2. **Compaction swapped context for calls.** Each compaction is an extra model call that re-reads the ~14K prefix. Total tokens fell slightly because the post-compaction requests were shorter, but uncached input rose (6.6K → 7.3K), so cost went up 6%. The run took twice as long.
3. **Truncation backfired on tokens.** With 24-token slices the agent had to read files a piece at a time, adding about one call per run and 18K tokens. It hit hardest on tasks with longer files or several edit sites (T07 multi-hunk +71%, T11 +38%, T06 +51%). This is the "cut tool output, pay more" effect that [tool-output caps experiment](https://github.com/nankris/tool-output-caps) couldn't reproduce with a 256-token cap. At 24 it shows up.
4. **The baseline is already mostly fixed overhead.** Peak context was ~15K in every arm, nearly all of it Codex's system prompt and tool definitions, which compression can't touch.

## Caveats
- Ceiling effect: these are tiny, one-file edits. Compression could hurt success on long sessions or big files, where the summary drops something the agent needs. My [early-vs-late compaction experiment](https://github.com/nankris/early-vs-late-compaction) is the long-session counterpart (compaction at 25K over 14 turns: no failures, 22% cheaper).
- The `trunc24` arm changes the prompt as well as the output size; there's no config key that truncates in this build.
- 2 reps per task; the cost gaps (6%, 20%) are within about one standard deviation of a single run, though the token and call differences are consistent across tasks.
- The machine restarted at ~19:48 UTC, after all 66 runs had been recorded; analysis outputs were regenerated afterwards.
- Another Codex experiment (my [JSON-schema reliability test](https://github.com/nankris/json-schema-reliability)) ran on the same account at the same time; rate-limit percentages in `runs.csv` include them.

## Files
- `scripts/harness/`: copy of the shared harness (`run_one.py`, `driver.sh`, `chain.sh`, `backfill.py`, fixtures)
- `scripts/jobs.txt` (exact run list), `scripts/rollout_extra.py` (tool output size, truncation notices, requested `max_output_tokens`, compaction records from the session rollouts), `scripts/analyze.py`
- `results/runs.csv` (one row per run), `results/rollout_extra.csv`, `results/summary.csv`, `results/per_task_passes.csv`, `results/per_task_tokens.csv`, `results/driver.log`
- `results/raw/*.jsonl`: raw `codex exec --json` streams; `results/probe/`: the two pre-run probes (excluded)
