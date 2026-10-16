# I tried to starve Codex of context. It still fixed every bug, and paid more for it

*Draft. Tech in General experiment #014. Numbers are from 66 headless Codex runs on 2026-10-14/15. All $ figures are estimates at API list price.*

A common idea for making coding agents cheaper: give them less context. Summarize the history early, or cut the file and command output they read down to a sliver. The worry is that the agent then makes worse edits. I tested both on Codex CLI.

## The setup

Eleven small JavaScript edit tasks: fix a bug, delete a duplicate block, handle tabs, change several spots in one file, and so on. Each has a `test.js` that must pass without being edited. Codex CLI 0.162.1 (gpt-6.1-sol, ChatGPT Plus login) ran each task twice in three ways:

- **default**: no changes
- **aggressive compaction**: summarize the conversation once it passes 14K tokens, which is about where a fresh session starts, so it compacts after nearly every step
- **truncated output**: a rule that every shell command can return at most 24 tokens of output, so the agent sees files a few words at a time

## What happened

All 66 runs passed. Not one broken edit, not one touched test.

| | Pass | Tokens per run | Model calls | Est. cost per run | Time |
|---|---|---|---|---|---|
| default | 22/22 | 61K | 4.1 | $0.0215 | 23 s |
| compact at 14K | 22/22 | 59K | 7.0 | $0.0228 | 52 s |
| ≤24 tokens per command | 22/22 | 79K | 5.2 | $0.0257 | 29 s |

Neither trick saved money:

- **Compaction** summarized the history three times in every run. Each summary is an extra model call, so runs went from 4 calls to 7, took twice as long, and cost 6% more, even though total tokens dipped slightly.
- **Truncation** made Codex re-read files in small `sed -n` line ranges, about one extra call per run. Tokens went up 29% and cost 20%. It hurt most on the multi-edit task (+71% tokens), where the agent had to see several parts of the file.

## Why there was nothing to save

A fresh Codex session's first request is already about 13–15K tokens before it has read a single file. That's the system prompt and tool definitions. These tasks only add a few thousand tokens on top. So compression is squeezing the smallest part of the bill, and every squeeze costs another round trip that re-reads the big fixed part.

## The takeaway

On small edits, Codex is robust to losing context. It just works around it. That makes compression useless here, not dangerous. Save compaction for long sessions, where the history really is the big part (in #012 it cut a 14-turn session's cost by 22%). Leave file output alone unless it's genuinely huge.

*Caveats: tiny tasks, 2 reps each, and the truncation arm uses a prompt rule because the config key for it does nothing in this build (#008). Full tables, raw logs and the exact commands are in the repo README.*
