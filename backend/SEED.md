# Seeding

- If `SEED_ON_STARTUP=true`, sample notes are inserted when the DB is empty.
- To seed manually, you can delete the sqlite file at `backend/instance/notes.db` and restart with `SEED_ON_STARTUP=true`.
