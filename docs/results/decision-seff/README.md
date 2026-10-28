# Seff vs Jev, 2026-10-28: one episode per agent

`records-2026-10-28.tar.gz` holds the eight Harbor-shaped job folders behind the Jev and Seff columns of
[the six-agent table](../../benchmarks.md#six-agents-one-episode-each), plus the Millionaire ladder draw
(`evals/millionaire/questions.json`) those runs played.

Unpack at the repository root and aggregate:

```bash
tar -xzf docs/results/decision-seff/records-2026-10-28.tar.gz
uv run python -m evals.table evals/results
```

## Runs

| scenario | flags |
|---|---|
| `ticket_router` | `--model jev\|seff --rethink off --episodes 1 --seed 0` |
| `game2048` | `--model jev\|seff --rethink on --episodes 1 --seed 0 --max-steps 20` |
| `millionaire` | `--model jev\|seff --rethink off --episodes 1 --seed 0` |
| `blackjack` | `--model jev\|seff --rethink off --episodes 1 --seed 0` |

Jev is `typesafe/jev-1.13` through OpenRouter's `/api/alpha/decisions`. Seff is `seff-1.0` at the `SEFF_API_URL`
host, with `SEFF_TIMEOUT_S=5`. Seff is free and text-only.

Seff's host returns no `usage`, so its job folders record `cost_usd: null` (unknown, not zero). The chat-model
share is zero because no Seff run called the chat model; the table's `$0.00‡` is that share.

## Machine

Linux x86_64 (WSL2), Python 3.13, headless Chromium through `@playwright/mcp@0.0.78`. The checkout's
`PLAYWRIGHT_MCP_ARGS` points at a Windows CDP endpoint; these runs set it empty so the page games used the local
headless browser. The Seff host is remote; the Jev endpoint is OpenRouter. One episode per agent, seed 0, one run,
no repetitions: these are task outcomes and wall times, not rates.

## Licence

`questions.json` is a draw from the [Open Trivia Database](https://opentdb.com), CC BY-SA 4.0, fetched by
`evals/millionaire/fetch_questions.py`. The archive includes it so the Millionaire ladder is reproducible.
