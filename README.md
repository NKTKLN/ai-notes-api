# ⚡ AI Notes API

**AI Notes API** is a production-oriented FastAPI backend for managing AI-related notes, prompts, conversations, and LLM workflows. The project demonstrates clean architecture, async development, PostgreSQL integration, and practical backend patterns for AI engineering.

## 📦 Dependencies

* [Python 3.13+](https://www.python.org/downloads/)
* [uv](https://docs.astral.sh/uv/getting-started/installation/)
* [Docker](https://docs.docker.com/get-docker/)
* [Task](https://taskfile.dev/)

## 🛠️ Installation & Usage

### 💻 Local Setup

1. Make sure you have **Python 3.13 or newer** installed.

2. Sync dependencies (including dev group):

```bash
task sync
```

3. Install Git hooks:

```bash
task init
```

4. Run the application (example module `app.main`):

```bash
task run
```

## 🐳 Docker

Build and run:

```bash
task docker
```

## 📜 License

This project is licensed under the MIT License. See the [LICENSE](./LICENSE) file for details.
