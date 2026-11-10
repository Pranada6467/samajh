"""The operating layer between a rule result and someone acting on it: a sampler over a synthetic
loan book, the attempt log, the reviewer queue with recorded decisions, and the half-yearly report.

Everything here is simulated: the book, the customers and the calls. Every view says so.

    uv run python -m samajh.ops book      # regenerate data/loanbook/ byte for byte (seed 85)
    uv run python -m samajh.ops init      # start a batch over the book in the state directory
    uv run python -m samajh.ops draw --as-of 2027-02-08   # draw 40% of the sales since the last draw (--rate)
    uv run python -m samajh.ops run       # simulate and analyse the calls (--analysis scripted|llm, --workers N)
    uv run python -m samajh.ops ingest    # bring finished phone sessions (case files) into the batch
    uv run python -m samajh.ops verify    # recompute every draw from the book
    uv run python -m samajh.ops report    # print the report as JSON
    uv run python -m samajh.ops demo --state DIR   # all of the above, scripted, into DIR

`init`, `draw`, `run`, `ingest`, `verify`, `report` and `demo` take `--state` (default: `.samajh`). The
review pages read the same directory through `samajh/server/review_routes.py`.

Modules: `model` (types), `book` (generator), `sampler`, `simulate`, `store`, `triage` (the one
place a tier is read), `sessions` (phone sessions in), `batch` (the joined read), `views` (the pages' JSON), `report`, `wording`.
"""
