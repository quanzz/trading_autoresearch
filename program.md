# Trading Autoresearch

A quantitative trading strategy optimization experiment where an AI agent autonomously iterates on trading strategies, backtests them, and optimizes for risk-adjusted returns.

## Setup

To set up a new experiment:

1. **Agree on a run tag**: propose a tag based on today's date (e.g. `jun6`). The branch `autoresearch/<tag>` must not already exist — this is a fresh run.
2. **Create the branch**: `git checkout -b autoresearch/<tag>` from current master.
3. **Read the in-scope files**: These are the files you need to understand:
   - `config.yaml` — user-provided configuration (fees, slippage, multiplier, weights). Read-only.
   - `prepare.py` — data loading from CSV files. Read-only.
   - `backtest/account.py` — Order, Trade, Position, Account classes. Read-only.
   - `backtest/engine.py` — bar-by-bar backtest loop. Read-only.
   - `backtest/metrics.py` — Max Drawdown, Sharpe Ratio, combined score. Read-only.
   - `strategy.py` — the file YOU modify. Strategy classes and parameters.
   - `run.py` — single-backtest entry point. Runs backtest, prints metrics, and generates artifacts (strategy copy, equity chart, summary report) in `results/`.
- `results/` — directory where post-backtest artifacts are saved automatically.
4. **Verify data exists**: Check that `data/` contains CSV files for the configured symbols. If the data files don't exist, tell the human to provide them.
5. **Initialize results.tsv**: Create `results.tsv` with just the header row:

```
commit	score	mdd	sharpe	total_return	trades	status	description
```

6. **Confirm and go**: Confirm setup looks good, then kick off the experimentation.

Once you get confirmation, start the experiment loop.

## Experimentation

Each experiment runs a single backtest on CPU. The backtest iterates bar-by-bar through minute-level OHLCV data, executing the strategy's trading signals.

**What you CAN do:**
- Modify `strategy.py` — this is the only file you edit. Everything is fair game: strategy type, parameters, indicator periods, position sizing, entry/exit logic, filters, stop-loss/take-profit rules. You can write entirely new strategy classes.
- Change the active strategy in `create_strategy()`.
- Add helper functions for technical indicators.

**What you CANNOT do:**
- Modify `backtest/`, `prepare.py`, `config.yaml`, or `run.py`. They are read-only.
- Install new packages or add dependencies. You can only use what's already in `pyproject.toml` (numpy, pandas, pyyaml, and Python stdlib).
- Modify the evaluation harness. The `compute_all_metrics` function in `backtest/metrics.py` is the ground truth.

**The goal is simple: get the highest `score`.** The score is a weighted combination:
- `score = -mdd_weight × MDD + sharpe_weight × min(Sharpe, 3) / 3`
- Default weights: MDD = 0.6, Sharpe = 0.4
- Higher score is better. MDD contributes negatively (lower drawdown = better score).

**Key strategy design principles:**
- **No look-ahead bias**: Your strategy only sees `lookback[:i+1]` on bar `i`. Orders execute at the NEXT bar's open price.
- **Risk management**: Protecting capital (low MDD) is the highest priority. A strategy that makes 50% return with 40% drawdown will score worse than one making 20% with 5% drawdown.
- **Robustness**: Strategies that work across different market regimes (trending, ranging, volatile) score better.
- **Simplicity criterion**: All else being equal, simpler is better. A small score improvement that adds 50 lines of complex logic is not worth it. Removing code and getting equal/better results is a great outcome.

**The first run**: Your very first run should always establish a baseline. Run as-is with the default strategy first.

## Output format

Once the backtest finishes it prints a summary:

```
---
score:            0.4521
max_drawdown:     0.1234
sharpe_ratio:     1.89
total_return:     0.2345
total_trades:     156
win_rate:         0.5200
bars_processed:   10000
elapsed_seconds:  2.3
round_trips:      45
```

Extract the key metric from the log:

```
grep "^score:" run.log
```

## Logging results

When an experiment is done, log it to `results.tsv` (tab-separated, NOT comma-separated).

The TSV has a header row and 7 columns:

```
commit	score	mdd	sharpe	total_return	trades	status	description
```

1. git commit hash (short, 7 chars)
2. score achieved (e.g. 0.4521) — use 0.0 for crashes
3. max_drawdown (e.g. 0.1234) — use 0.0 for crashes
4. sharpe_ratio (e.g. 1.89) — use 0.0 for crashes
5. total_return (e.g. 0.2345) — use 0.0 for crashes
6. total_trades — use 0 for crashes
7. status: `keep`, `discard`, or `crash`
8. short text description of what this experiment tried

Example:

```
commit	score	mdd	sharpe	total_return	trades	status	description
a1b2c3d	0.4521	0.1234	1.89	0.2345	156	keep	baseline SMA crossover (20, 60)
b2c3d4e	0.4612	0.1102	1.92	0.2511	142	keep	increase fast MA to 30, slow to 90
c3d4e5f	0.3910	0.1801	1.55	0.1500	200	discard	add RSI filter - too many false signals
d4e5f6g	0.0000	0.0000	0.00	0.0000	0	crash	typo in parameter name
```

## Research Log

Also maintain `research_log.md` with human-readable entries. Each entry should include:

```markdown
## YYYY-MM-DD HH:MM | Experiment #N

**Strategy**: <strategy name and key parameters>
**Score**: X.XXXX | **MDD**: X.XX% | **Sharpe**: X.XX | **Return**: X.XX%
**Hypothesis**: <what you thought would improve>
**Finding**: <what actually happened and why you think it happened>
**Decision**: KEEP / DISCARD / CRASH — <brief reason>
```

The research log is the user's window into your thinking. Be insightful. Note patterns, market behaviors, edge cases, and generalizable lessons.

## The experiment loop

The experiment runs on a dedicated branch (e.g. `autoresearch/jun6`).

LOOP FOREVER:

1. Look at the git state: the current branch/commit we're on
2. Read `strategy.py`, `results.tsv`, and `research_log.md` to understand current state and past experiments
3. Formulate a hypothesis for improvement based on past results
4. Modify `strategy.py` with your experimental idea
5. git commit with a descriptive message
6. Run the experiment: `python run.py > run.log 2>&1`
7. Read the results: `grep "^score:\|^max_drawdown:\|^sharpe_ratio:\|^total_return:\|^total_trades:\|^win_rate:" run.log`
8. If the grep output is empty, the run crashed. Run `tail -n 50 run.log` to read the Python stack trace and attempt a fix. If you can't get things to work after a few attempts, give up.
9. Record the results in `results.tsv` (NOTE: do NOT commit `results.tsv`, leave it untracked)
10. If score improved (higher), you "advance" the branch, keeping the git commit. Write a detailed entry to `research_log.md`.
11. If score is equal or worse, git reset back to where you started
12. Write a brief discard entry to `research_log.md`.

Note: each run automatically generates three artifacts in `results/`:
- `results/strategy_<timestamp>.py` — a copy of the strategy script used
- `results/equity_<timestamp>_<name>.png` — equity curve chart with drawdown panel
- `results/report_<timestamp>_<name>.md` — full markdown summary report

The idea is that you are a completely autonomous quantitative researcher trying things out. If they work, keep. If they don't, discard. You're advancing the branch so you can iterate. If you feel stuck, think harder — read the strategy code for new angles, combine elements from previous near-misses, try more radical strategy changes.

**Timeout**: Each backtest should complete quickly (seconds to a few minutes). If a run exceeds 10 minutes, kill it and treat it as a crash.

**Crashes**: If a run crashes (bug, data issue, etc.), use your judgment: if it's a simple fix (typo, missing import), fix and re-run. If the idea is fundamentally broken, skip it, log "crash", and move on.

**NEVER STOP**: Once the experiment loop has begun, do NOT pause to ask the human if you should continue. Do NOT ask "should I keep going?" or "is this a good stopping point?". The human might be asleep or away from the computer. You are autonomous. If you run out of ideas, think harder — try different strategy families (trend following, mean reversion, breakout, momentum, pattern-based), adjust parameters more aggressively, add risk management overlays, combine multiple signals, experiment with position sizing. The loop runs until the human interrupts you, period.

A user might leave you running while they sleep. If each experiment takes ~1-2 minutes, you can run 30-60 experiments per hour, for hundreds overnight.

## Strategy design space

Here are dimensions you can explore:

- **Trend following**: Moving average crossovers, MACD, ADX, channel breakouts
- **Mean reversion**: Bollinger Bands, RSI extremes, statistical arbitrage
- **Momentum**: Rate of change, relative strength, volume-price analysis
- **Breakout**: Support/resistance levels, volatility breakouts, opening range
- **Patterns**: Candlestick patterns, price action setups
- **Filters**: Volume confirmation, volatility regime, time-of-day
- **Risk management**: Stop-loss, take-profit, trailing stops, max positions
- **Position sizing**: Fixed, volatility-adjusted, Kelly criterion
- **Exit rules**: Time-based, signal-based, trailing, profit target
- **Multi-timeframe**: Use multiple lookback periods to confirm signals
