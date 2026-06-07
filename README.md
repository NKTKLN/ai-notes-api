# ⚡ AI Notes API

**AI Notes API** is a production-oriented FastAPI backend for managing AI-related notes, prompts, conversations, and LLM workflows. The project demonstrates clean architecture, async development, PostgreSQL integration, and practical backend patterns for AI engineering.

## 📦 Dependencies

* [Python 3.13+](https://www.python.org/downloads/)
* [uv](https://docs.astral.sh/uv/getting-started/installation/)
* [Docker](https://docs.docker.com/get-docker/)
* [Task](https://taskfile.dev/)

## 📌 API endpoints

The API is mounted under `/api/v1`.

* `GET /api/v1/health` - healthcheck
* `POST /api/v1/notes` - create a note
* `GET /api/v1/notes` - list notes with pagination and filters
* `GET /api/v1/notes/{note_id}` - get a note by ID
* `PATCH /api/v1/notes/{note_id}` - update a note by ID
* `DELETE /api/v1/notes/{note_id}` - delete a note by ID

Documentation is available at:

* Swagger UI: `http://127.0.0.1:8000/docs`
* Redoc: `http://127.0.0.1:8000/redoc`

## 🚀 Local development

1. Install dependencies and development tools:

```bash
task sync
```

2. Install Git hooks:

```bash
task init
```

3. Start the application locally:

```bash
task run
```

## 🐳 Docker

Build and run the Docker services:

```bash
task docker
```

Stop Docker services:

```bash
task docker-down
```

## 🧪 Tests and quality checks

* Run tests:

```bash
task test
```

* Run tests with coverage:

```bash
task test-cov
```

* Run linting and type checking:

```bash
task lint
```

* Run full quality gate:

```bash
task check
```

## 🛠 Database migrations

* Create a new Alembic revision:

```bash
task alembic-revision -- "<message>"
```

* Apply migrations:

```bash
task alembic-upgrade
```

* Downgrade one revision:

```bash
task alembic-downgrade
```

## 📜 License

This project is licensed under the MIT License. See [LICENSE.md](./LICENSE.md) for details.
