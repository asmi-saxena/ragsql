from db_config import get_connection
from gemini_generator import generate_answer, generate_sql, explain_sql_result
import os
from typing import List, Tuple, Any
import re

_STOPWORDS = {"who","is","what","the","a","an","of","in","on","at","for","to"}


def parse_intent(query: str) -> dict:
    """Parse user query for explicit list or aggregate intents and map to SQL.

    Returns a dict with keys:
      - action: 'sql' or None
      - sql: SQL string to execute
      - explain: short description for summarization
    """
    q = query.lower()

    # LIST intents
    if any(k in q for k in ("name", "names", "list names", "just tell me the names", "tell me the names", "all the people")):
        return {"action": "sql", "sql": "SELECT id, name FROM people_info;", "explain": "list of names"}
    if any(k in q for k in ("company", "companies", "list companies", "which companies")):
        return {"action": "sql", "sql": "SELECT DISTINCT company FROM people_info WHERE company IS NOT NULL AND company != '';", "explain": "distinct companies"}
    if any(k in q for k in ("role", "roles", "list roles", "what roles")):
        return {"action": "sql", "sql": "SELECT DISTINCT role FROM people_info WHERE role IS NOT NULL AND role != '';", "explain": "distinct roles"}
    if any(k in q for k in ("age", "ages", "list ages", "show ages")) and any(w in q for w in ("list", "show", "names", "just")):
        return {"action": "sql", "sql": "SELECT id, name, age FROM people_info;", "explain": "names and ages"}

    # AGGREGATE intents
    # detect column mentions
    if "count" in q or re.search(r"how many|total number|number of", q):
        return {"action": "sql", "sql": "SELECT COUNT(*) FROM people_info;", "explain": "count"}
    # sum of ages
    if any(k in q for k in ("sum of age", "sum of ages", "total age", "total of ages", "sum ages")):
        return {"action": "sql", "sql": "SELECT SUM(age) FROM people_info;", "explain": "sum of ages"}
    if any(k in q for k in ("average age", "avg age", "average of ages", "mean age")):
        return {"action": "sql", "sql": "SELECT AVG(age) FROM people_info;", "explain": "average age"}
    if any(k in q for k in ("max age", "maximum age", "oldest")):
        return {"action": "sql", "sql": "SELECT MAX(age) FROM people_info;", "explain": "maximum age"}
    if any(k in q for k in ("min age", "minimum age", "youngest")):
        return {"action": "sql", "sql": "SELECT MIN(age) FROM people_info;", "explain": "minimum age"}

    return {"action": None}

# ---------- Query Type Detector ----------
def detect_query_type(query: str) -> str:
    analytical_keywords = [
        "how many", "count", "average", "sum", "total",
        "rows", "maximum", "minimum", "number of", "total number", "age", "salary"
    ]
    if any(word in query.lower() for word in analytical_keywords):
        return "sql_query"
    return "retrieval"

# ---------- Retrieve documents (RAG flow) ----------
def retrieve_from_db(query: str, cursor: Any) -> List[Tuple]:
    sql_query = """
        SELECT * FROM people_info
        WHERE name LIKE %s
        OR company LIKE %s
        OR role LIKE %s
        OR background LIKE %s;
    """
    # If user explicitly asks for names/list of people, run a focused SQL to get names
    normalized = query.lower()
    if ("name" in normalized or "names" in normalized) and any(k in normalized for k in ("all", "list", "tell", "show", "just")):
        cursor.execute("SELECT id, name FROM people_info;")
        return cursor.fetchall()

    # Try a broad LIKE search first
    wildcard = f"%{query}%"
    cursor.execute(sql_query, (wildcard, wildcard, wildcard, wildcard))
    results = cursor.fetchall()

    # If nothing found for the full query, try a fallback using tokens (strip punctuation/stopwords)
    if not results:
        # ignore very short tokens (like 'me') to avoid accidental substring matches
        tokens = [t for t in re.findall(r"\w+", query) if t.lower() not in _STOPWORDS and len(t) > 2]
        found = {}
        for token in tokens:
            w = f"%{token}%"
            cursor.execute(sql_query, (w, w, w, w))
            for row in cursor.fetchall():
                # use first column (id) for deduplication when available
                key = row[0] if len(row) > 0 else row
                found[key] = row

        # if we found matches via tokens, return them as a list
        if found:
            return list(found.values())

    return results

# ---------- Execute SQL safely ----------
def execute_sql(sql: str, cursor: Any) -> List[Tuple] | str:
    if not sql.lower().startswith("select"):
        return " Only SELECT queries are allowed for safety."
    try:
        cursor.execute(sql)
        result = cursor.fetchall()
        return result
    except Exception as e:
        return f"⚠️SQL Error: {e}"

# ---------- Main pipeline ----------
def rag_pipeline(user_query: str) -> None:
    conn = get_connection()
    cursor = conn.cursor()

    query_type = detect_query_type(user_query)

    if query_type == "retrieval":
        # First check for explicit intents (lists, aggregates) that we can answer directly with SQL
        intent = parse_intent(user_query)
        if intent.get("action") == "sql":
            sql = intent.get("sql")
            print(f"\n--- Generated SQL ---\n{sql}")
            result = execute_sql(sql, cursor)
            print("\n--- SQL Query Result ---")
            print(result)
            # Summarize via explain_sql_result (uses LLM)
            if isinstance(result, list):
                answer = explain_sql_result(result, user_query)
                print("\n--- Model Answer ---")
                print(answer)
            cursor.close()
            conn.close()
            return

        results = retrieve_from_db(user_query, cursor)
        if not results:
            print("No relevant data found.")
        else:
            # Keep raw results (list of tuples) and also print a compact console view
            context_results = results
            readable = "\n".join(str(r) for r in results)
            print("\n--- Retrieved Context ---")
            print(readable)

            # Ask the generator to summarize structured results (it will format nicely)
            answer = generate_answer(user_query, context_results)
            print("\n--- Model Answer ---")
            print(answer)

    elif query_type == "sql_query":
        sql = generate_sql(user_query)  # Using centralized SQL generation
        print(f"\n--- Generated SQL ---\n{sql}")
        result = execute_sql(sql, cursor)
        print("\n--- SQL Query Result ---")
        print(result)
        # Generate natural language explanation of SQL results
        if isinstance(result, list):
            answer = explain_sql_result(result, user_query)
            print("\n--- Model Answer ---")
            print(answer)

    cursor.close()
    conn.close()


def run_query(user_query: str) -> dict:
    """Run the pipeline for a query and return structured results instead of printing.

    Returns a dict containing keys that may include:
      - generated_sql: str or None
      - sql_result: list or str or None
      - retrieved_context: list of tuples or None
      - model_answer: str or None
      - error: str if any error occurred
    """
    out = {
        "generated_sql": None,
        "sql_result": None,
        "retrieved_context": None,
        "model_answer": None,
        "error": None,
    }

    try:
        conn = get_connection()
        cursor = conn.cursor()

        query_type = detect_query_type(user_query)

        if query_type == "retrieval":
            intent = parse_intent(user_query)
            if intent.get("action") == "sql":
                sql = intent.get("sql")
                out["generated_sql"] = sql
                result = execute_sql(sql, cursor)
                out["sql_result"] = result
                if isinstance(result, list):
                    out["model_answer"] = explain_sql_result(result, user_query)
                cursor.close()
                conn.close()
                return out

            results = retrieve_from_db(user_query, cursor)
            if not results:
                out["model_answer"] = "No relevant data found."
            else:
                out["retrieved_context"] = results
                out["model_answer"] = generate_answer(user_query, results)

        elif query_type == "sql_query":
            sql = generate_sql(user_query)
            out["generated_sql"] = sql
            result = execute_sql(sql, cursor)
            out["sql_result"] = result
            if isinstance(result, list):
                out["model_answer"] = explain_sql_result(result, user_query)

        cursor.close()
        conn.close()
    except Exception as e:
        out["error"] = str(e)

    return out

# ---------- Run ----------
if __name__ == "__main__":
    print("\nRAG + MySQL setup is working fine ✅")
    user_query = input("Enter your query: ")
    print(f"You entered: {user_query}")
    rag_pipeline(user_query)
