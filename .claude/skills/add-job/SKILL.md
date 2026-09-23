---
name: add-job
description: Scaffold a new PhoneMatch ingestion job in jobs/ that is idempotent, resumable, rate-limited, logged to job_runs and cron-ready. Use when adding or rewriting any script under jobs/.
---

# Add an ingestion job

Follow `jobs/CLAUDE.md`. Every job has the same shape:

```python
# jobs/<name>.py
import typer
from jobs._common import job_run, get_session, logger  # shared helpers

app = typer.Typer()


@app.command()
def main(
    limit: int | None = typer.Option(None, help="Max rows to process"),
    phone_id: int | None = typer.Option(None, help="Process one phone only"),
    dry_run: bool = typer.Option(False, help="Do everything except write"),
    force: bool = typer.Option(False, help="Reprocess rows already done"),
) -> None:
    with job_run("<name>") as run:  # writes/updates job_runs
        for row in select_pending_rows(limit, phone_id, force):
            try:
                result = process(row)  # pure/importable, unit-tested
                if not dry_run:
                    upsert(result)  # ON CONFLICT on natural key
                    mark_status(row, "done")
                run.processed += 1
            except RateLimited:
                run.notes = "rate limited, stopping; next run resumes"
                break
            except Exception as exc:  # per-row isolation
                mark_status(row, "failed", error=str(exc))
                run.failed += 1


if __name__ == "__main__":
    app()
```

## Checklist

- [ ] Natural key for upsert identified; re-running twice produces no duplicates (write a test).
- [ ] Row `status` column drives what gets picked up; crash mid-run resumes correctly.
- [ ] External calls rate-limited (sleep, per-run cap) and stop cleanly on 429.
- [ ] Raw responses saved under `data/raw/<source>/` when they're expensive to refetch.
- [ ] `--limit`, `--phone-id`, `--dry-run`, `--force` work.
- [ ] Added to `scripts/run_nightly.sh` in the right order (if it's a scheduled job).
- [ ] Row added to the jobs table in `jobs/CLAUDE.md` and HLD §6 if it's new.
- [ ] `make lint` and `make test` pass.
