---
name: add-migration
description: Make a PhoneMatch database schema change safely with Alembic - update SQLAlchemy models, generate and review the migration, apply it, and sync docs/HLD.md §8. Use for any table, column, index or pgvector change.
---

# Add a database migration

1. Change the SQLAlchemy model(s) in `app/db/models.py` first.
2. Generate: `uv run alembic revision --autogenerate -m "<short description>"`.
3. **Review the generated file by hand.** Autogenerate misses or gets wrong:
   - pgvector columns and HNSW indexes (`USING hnsw (embedding vector_cosine_ops)`) → write with `op.execute`
   - GIN / expression indexes (e.g. `to_tsvector` on titles)
   - `CREATE EXTENSION IF NOT EXISTS vector` (must be in the first migration)
   - CHECK constraints and server defaults
   - renames (autogenerate emits drop + add, which loses data)
4. Make `downgrade()` actually reverse `upgrade()`.
5. Apply: `make migrate`. Then downgrade one step and upgrade again to prove it's reversible.
6. Never edit a migration that's already committed — create a new one (a hook blocks this anyway).
7. Update the SQL in `docs/HLD.md` §8 so the design doc matches the real schema.
8. If the embedding dimension changes: new column/table + full re-embed job; don't alter in place.
