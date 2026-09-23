# jobs/ — ingestion job rules

Design reference: `docs/HLD.md` §4 (data sources), §5 (YouTube reviewers), §6 (pipeline), §7 (LLM phases).

## The jobs (run in this order)

| # | Module | Does |
|---|---|---|
| 1 | `sync_catalog` | Flipkart top sellers / seed YAML + GSMArena specs → `phones`, `phone_prices` |
| 2 | `sync_channels` | yt-dlp `--flat-playlist` per channel in `config/channels.yaml` → `channel_videos` |
| 3 | `match_videos` | phones × channel_videos → `review_videos` (strict token match + filters) |
| 4 | `fetch_transcripts` | youtube-transcript-api → `data/raw/transcripts/<video_id>.json` + `transcripts` |
| 5 | `build_digests` | LLM map-reduce → `phone_digests` (only phones whose video set changed) |
| 6 | `embed_chunks` | 75 s windows / 15 s overlap, aspect tags, bge-small → `review_chunks` |

## Every job must

- Be a Typer CLI runnable as `python -m jobs.<name>` with `--limit`, `--phone-id`, `--dry-run`, `--force`.
- Be **idempotent**: upsert on natural keys (`phones.slug`, `video_id`, `(phone_id, video_id)`).
- Be **resumable**: process only rows in the right `status`; update status per row, not per batch;
  commit after each row (or small batch) so a crash loses almost nothing.
- Write a `job_runs` row at start and update it at the end (processed, failed, status, notes).
- Catch per-row errors: set `status='failed'`, store `error`, continue with the next row.
- Never delete raw files in `data/raw/`; digests and chunks must be rebuildable from them.
- Respect external services: sleep between requests (YouTube 3–5 s, GSMArena 5 s), cap requests per
  run, stop cleanly on HTTP 429 and let the next cron run continue.
- Put shared logic (normalisation, matching, chunking) in importable functions with unit tests;
  the job module only orchestrates.

## Matching rules (job 3)

- Normalise: lowercase, remove "5g", `+` → " plus", strip punctuation/emoji.
- All phone tokens must be in the title; the title must not contain a variant token the phone lacks
  (pro, plus, max, ultra, lite, fe, neo, mini).
- Reject titles with: unboxing, first look, first impressions, vs, #shorts, launch, leaks.
  Duration must be 6–35 min. Max 1 video per channel, core channels first, max 5 per phone.
- `match_score < 90` → `status='needs_review'`. Keep `tests/test_matcher.py` with 30+ tricky pairs.

## LLM jobs (job 5)

- Use `LLMClient` with a JSON schema, `temperature=0`, explicit `num_ctx=8192`.
- Map per transcript → store in `transcripts.map_json`; reduce per phone → `phone_digests`.
- Store `source_hash`, `prompt_version`, `model` on every digest. Skip phones whose hash is unchanged
  unless `--force`.
