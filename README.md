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

## Use it from an agent
Precedent ships a small read-only MCP server and an agent skill, so any MCP-capable agent can check a proposal against the
decisions in force. See [docs/mcp.md](docs/mcp.md) and [skill/precedent/SKILL.md](skill/precedent/SKILL.md).
```bash
python -m precedent.mcp_server --store store/precedent.rl
```

## Where the data lives
- `vault/`: the markdown notes (fictional company "Fernwood Robotics"; no real data).
- `store/precedent.rl`: the persistent Relate store built from the vault.
- `eval/answer_key.json`: answers computed in plain Python, independent of Cypher.

## Evaluation
Same 26 questions, same prompts and tools for both agents, answer key computed independently of Cypher. One agent
searches and reads the markdown notes (**files**); the other writes read-only Cypher on the Relate store (**graph**).

| Model | Notes | Arm | Correct | Tokens | Est. cost |
|---|---|---|---|---|---|
| Haiku 5.5 (3 runs) | 82 | graph / files | 77/78 / 77/78 | 0.42M / 1.48M | $0.06 / $0.19 |
| Haiku 5.5 (3 runs) | 416 | graph / files | 77/78 / 76/78 | 0.77M / 3.99M | $0.10 / $0.48 |
| Haiku 5.5 (3 runs) | 1,116 | graph / files | 77/78 / 72/78 | 0.80M / 12.33M | $0.10 / $1.42 |
| Sonnet 5.5 (1 run) | 416 | graph / files | 26/26 / 24/26 | 0.10M / 1.01M | $0.26 / $2.23 |

On a small vault the two agents are about equally accurate. As the vault grows, the graph agent's cost stays flat while
file search gets costlier and less reliable. These are small samples; read the caveats in [docs/results.md](docs/results.md).
Raw transcripts for every run are in `results/`.

## Credits and license
Apache-2.0 (see LICENSE). Built with Relate by Neo4j (Apache-2.0). All data is synthetic.
