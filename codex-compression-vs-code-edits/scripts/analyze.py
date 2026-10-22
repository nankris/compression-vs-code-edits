#!/usr/bin/env python3
"""Summary + chart. Needs results/runs.csv and results/rollout_extra.csv (scripts/rollout_extra.py)."""
import os
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
df = pd.read_csv(os.path.join(HERE, "results", "runs.csv"))
ex = pd.read_csv(os.path.join(HERE, "results", "rollout_extra.csv"))
df = df.merge(ex[["cond", "task", "rep", "tool_output_chars", "truncation_markers", "compacted_records"]], on=["cond", "task", "rep"], how="left")
order = ["default", "compact14k", "trunc24"]
labels = {"default": "default", "compact14k": "compact\n(auto at 14K)", "trunc24": "truncate output\n(<=24 tok/call)"}
g = df.groupby("cond")
s = pd.DataFrame({"runs": g.size(), "passes": g.passed.sum(), "pass_rate": g.passed.mean().round(3),
    "total_tokens_mean": g.total_tokens.mean().round(0), "total_tokens_sd": g.total_tokens.std().round(0),
    "cached_mean": g.cached_input_tokens.mean().round(0), "uncached_mean": g.uncached_input_tokens.mean().round(0),
    "output_mean": g.output_tokens.mean().round(0), "cache_share": (g.cached_input_tokens.sum() / g.input_tokens.sum()).round(3),
    "peak_context_mean": g.peak_context_tokens.mean().round(0), "model_calls_mean": g.model_calls.mean().round(2),
    "compactions_mean": g.compacted_records.mean().round(2), "tool_output_chars_mean": g.tool_output_chars.mean().round(0),
    "truncation_notices_mean": g.truncation_markers.mean().round(2), "wall_s_mean": g.wall_s.mean().round(1),
    "cost_total_usd": g.est_cost_usd.sum().round(4), "cost_mean_usd": g.est_cost_usd.mean().round(4),
    "cost_sd_usd": g.est_cost_usd.std().round(4)}).reindex(order)
s["cost_per_success_usd"] = (s.cost_total_usd / s.passes).round(4)
s.to_csv(os.path.join(HERE, "results", "summary.csv"))
pt = df.pivot_table(index="task", columns="cond", values="passed", aggfunc="sum").reindex(columns=order)
pt.to_csv(os.path.join(HERE, "results", "per_task_passes.csv"))
ptok = df.pivot_table(index="task", columns="cond", values="total_tokens", aggfunc="mean").reindex(columns=order).round(0)
ptok.to_csv(os.path.join(HERE, "results", "per_task_tokens.csv"))
print(s.T.to_string()); print(pt.to_string()); print(ptok.to_string())
fig, axes = plt.subplots(1, 4, figsize=(18, 5))
cols = ["#4c72b0", "#c44e52", "#55a868"]
for ax, col, title, sc in [(axes[0], "passed", "Pass rate (22 runs per arm)", 100), (axes[1], "total_tokens", "Total tokens per run (K)", 1e-3),
                           (axes[2], "est_cost_usd", "Est. API cost per run (US cents)", 100), (axes[3], "model_calls", "Model calls per run", 1)]:
    means = [df[df.cond == c][col].mean() * sc for c in order]
    ax.bar(range(3), means, color=cols, alpha=0.55, width=0.6)
    if col != "passed":
        for i, c in enumerate(order):
            v = df[df.cond == c][col] * sc
            ax.scatter([i + (j - len(v) / 2) * 0.02 for j in range(len(v))], v, color="black", s=8, zorder=3)
    else:
        for i, m in enumerate(means):
            ax.text(i, m + 1, f"{m:.0f}%", ha="center", fontsize=10)
        ax.set_ylim(0, 112)
    ax.set_xticks(range(3)); ax.set_xticklabels([labels[c] for c in order], fontsize=9)
    ax.set_title(title, fontsize=11); ax.grid(axis="y", alpha=0.3)
fig.suptitle("Codex 0.162.1 (gpt-6.1-sol): context compression vs code-edit success, 11 edit tasks x 2 reps per arm. Bars = mean, dots = runs", fontsize=11)
fig.tight_layout(); fig.savefig(os.path.join(HERE, "results", "chart.png"), dpi=130); print("wrote chart")
