# Notes Backend (Flask) – note-organizer-223027-223077

A simple Flask backend for a notes application with SQLite persistence, CRUD endpoints, tags/categories organization, and search/filter. OpenAPI/Swagger docs available.

- Base URL: http://localhost:3001
- Docs: http://localhost:3001/docs

## Quick Start

1. Install dependencies
   - From the backend folder:
     ```
     pip install -r requirements.txt
     ```

2. (Optional) Configure environment
   - Copy `.env.example` to `.env` and adjust:
     - `DATABASE_PATH` path to sqlite file (defaults to backend/instance/notes.db)
     - `SEED_ON_STARTUP=true` to auto-seed sample notes

3. Run the server
   ```
   python run.py
   ```
   The server listens on port 3001.

## API Overview

- Health
  - GET `/` -> `{ "message": "Healthy" }`

- Notes
  - GET `/api/notes` – List notes with optional search/filter
    - Query params:
      - `q`: text search in title and content
      - `tag`: filter by tag name
      - `category`: filter by category
    - 200 Response: Array of Note
  - POST `/api/notes` – Create a note
    - Request JSON:
      ```
      {
        "title": "My Title",
        "content": "Body...",
        "category": "work",
        "tags": ["tag1", "tag2"]
      }
      ```
    - 201 Response: Note

  - GET `/api/notes/{id}` – Retrieve a note
    - 200 Response: Note
    - 404 if not found

  - PATCH `/api/notes/{id}` – Update fields
    - Request JSON (any subset):
      ```
      {
        "title": "New Title",
        "content": "Updated content",
        "category": "personal",
        "tags": ["updated", "tags"]
      }
      ```
    - 200 Response: Note
    - 404 if not found

  - DELETE `/api/notes/{id}`
    - 204 Response on success
    - 404 if not found

- Tags
  - GET `/api/tags` – List all known tags
    - 200 Response:
      ```
      { "tags": ["errands", "ideas", "list", "welcome", ...] }
      ```

### Note Schema

```
{
  "id": number,
  "title": string,
  "content": string,
  "category": string | null,
  "tags": string[],
  "created_at": ISODateTime,
  "updated_at": ISODateTime
}
```

## Seed Data

When `SEED_ON_STARTUP=true` and if DB is empty, the app inserts three sample notes:
- "Welcome to Notes" (tags: welcome, getting-started)
- "Grocery List" (tags: list, errands)
- "Project Ideas" (tags: ideas, work)

## Error Handling

- 400 on validation or bad requests
- 404 when resources are not found

## Development Notes

- SQLite file defaults to `backend/instance/notes.db` and is created automatically.
- OpenAPI is powered by flask-smorest at `/docs`.
- CORS is enabled for all origins to simplify local development.