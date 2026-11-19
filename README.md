# Precedent

**A decision memory for teams and AI agents, built on [Relate](https://relatedb.ai).**
Turn a folder of meeting and decision notes into a graph, then ask: *is this still in force, what replaced it, and does my new proposal contradict anything we already decided?*

> Status: work in progress for the Relate by Neo4j hackathon. See [PRODUCT.md](PRODUCT.md) for the plan.

## Use case
Teams make decisions in meetings and forget them. New proposals quietly contradict old ones, decisions rest on choices that were later replaced, and owners leave. Searching notes for keywords finds old text, not what is *currently* true. Precedent models decisions as a graph, so questions about replacement chains, dependencies, scoped conflicts and ownership become queries.

## How it uses Relate
- **Mode:** single file (`store/precedent.rl`). Why: one portable file judges can inspect and query; in-memory is used only for tests.
- **What the graph models:** `Decision`, `Meeting`, `Person`, `Project`, `Technology` nodes. Edges: `DECIDED_IN`, `MADE_BY`, `OWNED_BY`, `AFFECTS`, `CONSTRAINS` (properties `stance` and `scope`), `SUPERSEDES`, `DEPENDS_ON`, `ATTENDED_BY`.
- A decision is *active* when nothing supersedes it, derived from the graph rather than stored.

## Setup and run
Requires Python 3.9+.
```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
python scenario/fernwood.py                         # regenerate the fictional vault and answer key
python -m precedent.store vault store/precedent.rl  # build the Relate store from the vault
python eval/verify_graph.py store/precedent.rl eval/answer_key_v3.json   # reference queries match the key
```
Try the CLI (no API key needed):
```bash
python -m precedent conflicts
python -m precedent stale
python -m precedent why D17
python -m precedent check --tech "Sentra Lidar" --scope outdoor
python -m precedent active --project Beacon
```
Run the evaluation (needs `ANTHROPIC_API_KEY` in `.env`, see `.env.example`):
```bash
python eval/run_eval.py --arm graph --model claude-haiku-5-5 --key eval/answer_key_v3.json
python eval/run_eval.py --arm files --model claude-haiku-5-5 --key eval/answer_key_v3.json
python eval/summarize.py --by-type results/<run folder>
```
Larger vaults for the scaling test: `sh scale/build.sh`.

## Where the data lives
- `vault/`: the markdown notes (fictional company "Fernwood Robotics"; no real data).
- `store/precedent.rl`: the persistent Relate store built from the vault.
- `eval/answer_key.json`: answers computed in plain Python, independent of Cypher.

## Evaluation
_Results to come:_ agent with file search vs agent with the graph, per question type, with committed transcripts for replay.

## Credits and license
Apache-2.0 (see LICENSE). Built with Relate by Neo4j (Apache-2.0). All data is synthetic.
