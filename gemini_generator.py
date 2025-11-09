import google.generativeai as genai
from dotenv import load_dotenv
import os
from typing import List, Tuple, Optional, Union

load_dotenv()

# Configure Gemini
GEMINI_MODEL = "gemini-2.5-flash"  # Default model for all operations
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# Initialize model (singleton pattern)
_model = None

def get_model():
    """Get or create the Gemini model instance."""
    global _model
    if _model is None:
        _model = genai.GenerativeModel(GEMINI_MODEL)
    return _model

def generate_answer(user_query: str, context: Union[str, List[Tuple]]) -> str:
    """Generate a natural language answer using context from the database.

    The context can be either a plain string or a list of DB tuples. If it's a list
    of tuples we format them into readable records before sending to the model so
    the LLM doesn't simply echo raw tuples.
    """
    # If context is structured (list of tuples), format into readable records
    if isinstance(context, list):
        # Expected table columns for people_info: id, name, age, height, weight, company, role, background
        cols = ["id", "name", "age", "height", "weight", "company", "role", "background"]
        formatted_rows = []
        for row in context:
            # map available values to columns; if row shorter/longer, handle gracefully
            items = []
            for i, val in enumerate(row):
                col = cols[i] if i < len(cols) else f"col{i}"
                items.append(f"{col}: {val}")
            formatted_rows.append(
                ", ".join(items)
            )
        readable_context = "\n".join(formatted_rows)
    else:
        readable_context = str(context)

    prompt = f"""
You are a helpful AI assistant. Use the following context from the MySQL database to answer the question concisely.

Context (structured):
{readable_context}

Question: {user_query}

Please answer in natural language. Do not repeat raw tuples; summarize the most relevant record(s) as a short paragraph.
"""

    model = get_model()
    response = model.generate_content(prompt)
    return response.text

def generate_sql(query: str) -> str:
    """Convert natural language to SQL query."""
    prompt = f"""
    You are an expert MySQL assistant. 
    Convert the following natural language question into a valid SQL query 
    for a table named `people_info` with columns: name, age, company, role, background.
    
    Question: {query}
    Return only the SQL query, nothing else.
    """
    model = get_model()
    response = model.generate_content(prompt)
    
    # Sanitize response: strip Markdown fences and language tags
    sql_text = response.text.strip()
    # remove triple-backtick fences if present
    if sql_text.startswith("```"):
        lines = sql_text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        sql_text = "\n".join(lines).strip()
    # remove an initial 'sql' language tag
    if sql_text.lower().startswith("sql\n"):
        sql_text = sql_text.split("\n", 1)[1].strip()
    
    return sql_text.split(';')[0].strip() + ';'

def explain_sql_result(result: List[Tuple], query: str) -> str:
    """Generate natural language explanation of SQL query results."""
    prompt = f"Based on this SQL result {result}, answer the question: {query}"
    model = get_model()
    response = model.generate_content(prompt)
    return response.text

def list_available_models() -> List[str]:
    """List all available Gemini models for the configured API key."""
    try:
        models = genai.list_models()
        return [str(model.name) for model in models]
    except Exception as e:
        return [f"Error listing models: {str(e)}"]
