-- Seed the reviewer channels from config/channels.yaml (docs/HLD.md §5).
-- id = priority: 1 is the highest (core 1-5, then backup 1-3), same order as the YAML.
-- Idempotent: re-running updates name/tier/language by handle (ids stay), never duplicates.
-- Run: docker compose exec -T db psql -U phonematch -d phonematch -f - < scripts/seed_channels.sql
-- Superseded by `python -m jobs.sync_channels` (M2), which reads channels.yaml directly.
BEGIN;

INSERT INTO channels (id, handle, name, tier, language) VALUES
  (1, 'Geekyranjit', 'Geekyranjit',  'core',   'en'),
  (2, 'C4ETech',     'C4ETech',      'core',   'en'),
  (3, 'beebomco',    'Beebom',       'core',   'en'),
  (4, 'Gadgets360',  'Gadgets 360',  'core',   'en'),
  (5, 'TrakinTech',  'Trakin Tech',  'core',   'hi'),
  (6, 'TechnoRuhez', 'Techno Ruhez', 'backup', 'hi'),
  (7, 'TechBar',     'TechBar',      'backup', 'hi'),
  (8, 'TechBurner',  'Tech Burner',  'backup', 'hi')
ON CONFLICT (handle) DO UPDATE
  SET name = EXCLUDED.name, tier = EXCLUDED.tier, language = EXCLUDED.language,
      is_active = true;

-- Explicit ids bypass the SERIAL sequence; move it past them so future inserts don't collide.
SELECT setval(pg_get_serial_sequence('channels', 'id'), (SELECT max(id) FROM channels));

COMMIT;
