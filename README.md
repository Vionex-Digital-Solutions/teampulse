# Vionex TeamPulse

Internal team check-in & kudos app. This is the codebase you will build during Vionex onboarding.

## Get started (on your VM)

```bash
cd ~
git clone https://github.com/Vionex-Digital-Solutions/teampulse.git
cd teampulse/backend

python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

cp .env.example .env
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

API docs at http://localhost:8000/api/docs

## Layout

```
backend/
  app/
    main.py          entry point
    api/v1/          routes (pulse, kudos, standup, users, digest)
    models/          database models
    schemas/         request/response validation
    services/        business logic
    core/            config, database, security
  tests/             pytest tests
  migrations/        database schema migrations (Alembic)
  pyproject.toml     Python dependencies
  .env.example       environment variable template
```

## Stack

- Python 3.11+
- FastAPI
- SQLAlchemy (async)
- SQLite for local development, PostgreSQL later

## Your tasks

Onboarding tasks are on Jira as `ONB-1` through `ONB-N`. Take them in order.

## Getting help

- Ask on Discord in `#interns-help`
- DM Ahmed directly
- For code questions, ask Claude on the VM first: run `claude`

## License

MIT — see [LICENSE](LICENSE).
