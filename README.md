# RAG + MySQL Project

Small RAG (Retrieval-Augmented Generation) demo that:
- Connects to a MySQL database (`people_info` table)
- Uses Google Generative AI (Gemini) to 1) convert natural language to SQL and 2) summarize results

This README shows how to activate the venv, install dependencies, set environment variables, list available models, and run the app.

## Prerequisites
- macOS / Linux
- Python 3.8+ (this repo uses a virtualenv at `./venv`)
- A running MySQL server and a database with a `people_info` table
- A Gemini API key with access to the Generative AI models

## Quick start
Open a terminal and cd to the project root:

```bash
cd /Users/asmi/Desktop/Projects/rag_mysql_project
```

### 1) Activate the virtual environment
If your repo already contains a venv, activate it:

```bash
source venv/bin/activate
```

If you don't have a venv, create one and activate it:

```bash
python3 -m venv venv
source venv/bin/activate
```

> Important: when the venv is activated, use `python` (not `python3`) to install packages and run the app. On some systems `python3` still points to the system/Homebrew Python and will not reference the venv.

### 2) Install dependencies (into the venv)

```bash
python -m pip install --upgrade pip
python -m pip install mysql-connector-python google-generativeai python-dotenv
```

### 3) Add environment variables
Create a `.env` file in the project root (or export these values in your shell):

```
GEMINI_API_KEY=your_gemini_api_key_here
MYSQL_HOST=localhost
MYSQL_USER=your_db_user
MYSQL_PASSWORD=your_db_password
MYSQL_DATABASE=your_database_name
```

The code uses `python-dotenv` to load `.env`.

### 4) (Optional) List available Gemini models
To see which models your API key supports, run:

```bash
python list_models.py
```

Pick a model from the list (e.g. `models/gemini-2.5-flash`) if you need to change `GEMINI_MODEL` in `gemini_generator.py`.

### 5) Run the app (interactive)

```bash
python main.py
```

The script will prompt:

```
Enter your query:
```

Try queries such as:
- `what are the total number of rows in people_info table?`
- `count how many people have "engineer" in their role`
- `who works at Acme Corp?`

### 6) Run the app non-interactively (useful for quick tests)

```bash
echo "what are the total number of rows in people_info table?" | python main.py
```

## Troubleshooting
- ModuleNotFoundError: No module named 'mysql'
  - Make sure the venv is activated and you installed `mysql-connector-python` into that venv.
  - Confirm the interpreter with:

```bash
which python
python -c "import sys; print(sys.executable)"
```

- Pip errors mentioning "externally managed environment":
  - That happens when you try to install into the system/Homebrew Python. Activate the venv and use `python -m pip install ...` as shown above.

- Database connection errors:
  - Verify `MYSQL_*` values in your `.env` and that the MySQL server allows connections from your host.

- Model NotFound errors from the Generative AI client:
  - Run `python list_models.py` to see available model names and update `gemini_generator.py` if needed.

## Files of interest
- `main.py` — CLI entrypoint and pipeline orchestration
- `db_config.py` — MySQL connection helper (reads env vars)
- `gemini_generator.py` — centralized model utilities (generate SQL, answer, list models)
- `list_models.py` — small utility that prints available Gemini models

## Next steps / improvements
- Add unit tests for SQL sanitization
- Add logging and retries for model calls
- Add a small integration test that runs main.py non-interactively against a test DB

---
If you want, I can add a small `requirements.txt` or a `.github/workflows` CI test to run the non-interactive smoke test. Tell me which and I'll add it.