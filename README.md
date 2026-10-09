# MUST Swap

An English campus marketplace built with Python, Flask and SQLite.

Project team: Class 1, Group 14.

## Included capabilities

- A responsive marketplace with public listing and seller pages, SQLite setup, and preserved project licensing.

## Setup

Requires Python 3.10 or newer.

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
python -c "import secrets; print(secrets.token_hex(32))"
```

Set SECRET_KEY in .env to the generated value, then run:

```powershell
python init_db.py
python app.py
```

Open http://127.0.0.1:5000. Demo administrator: admin@must.edu.mo / Admin12345. Demo students: lily.wong@student.must.edu.mo and wang.hao@student.must.edu.mo / Password123.
On macOS/Linux, activate with source .venv/bin/activate and copy configuration with cp .env.example .env.

## Database upgrades

Keep your existing .env, SQLite database, and static/uploads directory when replacing the source files. Startup applies schema migrations automatically and backs up existing databases before migration. Do not reset your database.
For a separate copy of an original or earlier database:

```powershell
python init_db.py --migrate-from "C:\path\to\old.db" --database must_swap.db
```

The destination must contain no accounts. The original database is preserved; compatible uploads are copied and unknown historical sale prices are not invented.

## Project origin

Built on [College-Marketplace](https://github.com/kaustubh29032004/College-Marketplace) by kaustubh29032004. Original MIT attribution is preserved in LICENSE.
