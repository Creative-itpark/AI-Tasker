from flask import Flask, request, render_template
from llama_cpp import Llama
# from new_db_schema import get_schema_texts
from get_schema import get_schema_texts
import pymysql

app = Flask(__name__)

# Load model once
llm = Llama.from_pretrained(
    repo_id="TheBloke/Mistral-7B-Instruct-v0.2-GGUF",
    filename="mistral-7b-instruct-v0.2.Q4_K_M.gguf",
    n_ctx=4096,       # reduce a bit to fit in 8GB RAM
    n_threads=4,      # use all threads on i5-4300U
    n_batch=64,       # lower batch size for stability
    use_mmap=False,   # disable mmap (low memory safety)
    use_mlock=False,  # prevent memory locking issues
    verbose=False
)

# Load schema once
schema_text = get_schema_texts()

# Database config
DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "",
    "database": "creative_it_park"
}


@app.route("/")
def home():
    return render_template("index.html")


# ✅ Route 1: Generate SQL only
@app.route("/generate", methods=["POST"])
def generate_sql():
    user_prompt = request.form.get("prompt")

    prompt = f"""
    [INST]
    You are a professional MySQL query generator.

    Below is the exact database schema with all tables, columns, and relationships.

    SCHEMA:
    {schema_text}

    TASK:
    Write one valid MySQL query that fulfills the user's request.

    RULES:
    1. Use only the tables and columns listed in the schema above.
    2. Never invent or assume any table, column, or relationship that does not exist.
    3. Choose the correct SQL command type:
       - "create" or "add" → INSERT
       - "get", "list", or "show" → SELECT
       - "update" or "modify" → UPDATE
       - "remove" or "delete" → DELETE
    4. Use JOINs or subqueries only if the schema shows a real relationship.
    5. Output only the SQL query — no markdown, no explanations, no comments.
    6. Do not include any column or table not present in the schema.
    7. If something is ambiguous, make no assumption; use only verifiable relations from the schema.

    USER REQUEST:
    {user_prompt}
    [/INST]
    """

    output = llm(prompt, max_tokens=2048, temperature=0.2)
    generated_sql = output["choices"][0]["text"].strip()

    # Show generated SQL and "Execute" button
    return render_template("index.html", sql=generated_sql, prompt=user_prompt)


# ✅ Route 2: Execute SQL (separate from generation)
@app.route("/execute", methods=["POST"])
def execute_sql():
    generated_sql = request.form.get("generated_sql")

    if not generated_sql:
        return render_template("index.html", error="⚠️ No SQL query to execute. Please generate one first.")

    try:
        conn = pymysql.connect(**DB_CONFIG)
        cursor = conn.cursor(pymysql.cursors.DictCursor)

        if generated_sql.lower().startswith(("select", "show")):
            cursor.execute(generated_sql)
            rows = cursor.fetchall()
            columns = list(rows[0].keys()) if rows else []
            conn.close()
            return render_template("index.html", sql=generated_sql, rows=rows, columns=columns)
        else:
            cursor.execute(generated_sql)
            conn.commit()
            conn.close()
            return render_template("index.html", sql=generated_sql, message="✅ SQL command executed successfully!")

    except Exception as e:
        return render_template("index.html", sql=generated_sql, error=str(e))


if __name__ == "__main__":
    app.run(debug=True)