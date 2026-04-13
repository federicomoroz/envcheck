# envcheck

A zero-dependency CLI tool that validates your `.env` file against `.env.example` — catches missing, empty, and undeclared variables before they cause runtime errors.

---

## The problem

Every project has a `.env.example` that declares which variables are required. In practice, developers forget to add new variables to their local `.env`, or leave them empty. These omissions only surface at runtime — often in production.

`envcheck` catches them in one command.

---

## Usage

```bash
python envcheck.py
```

Default behavior: compares `.env` against `.env.example` in the current directory.

```bash
python envcheck.py --env .env.staging --example .env.example
```

**Output:**

```
Checking: .env  vs  .env.example

  MISSING   SMTP_HOST
  EMPTY     SECRET_KEY
  OK        DATABASE_URL
  OK        DEBUG
  OK        PORT
  OK        API_KEY
  EXTRA     EXTRA_VAR  (not in .env.example)

  1 missing  1 empty  4 ok
```

**Exit codes:**
- `0` — all required variables are present and non-empty
- `1` — one or more variables are missing or empty

Exit code `1` makes it usable in CI pipelines — add it as a pre-deploy check and the build fails before a misconfigured environment reaches production.

---

## Try it

```bash
git clone https://github.com/federicomoroz/envcheck.git
cd envcheck

# Use the included sample to see all cases
cp .env.sample .env
python envcheck.py
```

---

## What each status means

| Status | Meaning |
|--------|---------|
| `MISSING` | Key exists in `.env.example` but not in `.env` |
| `EMPTY` | Key exists in `.env` but has no value |
| `OK` | Key exists and has a value |
| `EXTRA` | Key exists in `.env` but not declared in `.env.example` |

---

## Requirements

Python 3.9+. No external dependencies.
