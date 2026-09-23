-- Runs once, only when the pgdata volume is empty (Postgres image entrypoint behaviour).
-- Integration tests use this database; they never touch the main one.
-- On an older volume, create it by hand: make db-shell, then CREATE DATABASE phonematch_test;
CREATE DATABASE phonematch_test;
