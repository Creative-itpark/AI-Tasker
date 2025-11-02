from flask import Flask, request, render_template
from llama_cpp import Llama
# from new_db_schema import get_schema_texts
from get_schema import get_schema_texts
import pymysql

app = Flask(__name__)

# ============================================================
# ✅ Load SQLCoder-7B-2 (GGUF) model once at startup
# ============================================================

# Option 1 — Load directly from Hugging Face (auto-download)
llm = Llama.from_pretrained(
    repo_id="MaziyarPanahi/sqlcoder-7b-2-GGUF",
    filename="sqlcoder-7b-2.Q6_K.gguf",
    n_ctx=4096,       # reduce a bit to fit in 8GB RAM
    n_threads=4,      # use all threads on i5-4300U
    n_batch=64,       # lower batch size for stability
    use_mmap=False,   # disable mmap (low memory safety)
    use_mlock=False,  # prevent memory locking issues
    verbose=False
)

# Option 2 — If already downloaded locally, comment the above and use:
# llm = Llama(
#     model_path="model/sqlcoder-7b-2.Q2_K.gguf",
#     n_ctx=2048,
#     n_threads=4,
#     n_batch=64,
#     use_mmap=False,
#     use_mlock=False,
#     verbose=False
# )

# ============================================================
# ✅ Load schema text once
# ============================================================
schema_text = get_schema_texts()

# ============================================================
# ✅ Database configuration
# ============================================================
DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "",
    "database": "creative_it_park"
}

# ============================================================
# ✅ Flask Routes
# ============================================================

@app.route("/")
def home():
    return render_template("index.html")


# ✅ Route 1: Generate SQL only
@app.route("/generate", methods=["POST"])
def generate_sql():
    user_prompt = request.form.get("prompt")

    prompt = f"""
    [INST]
    You are an expert SQL generator specialized in **MySQL** databases.

    Your goal is to convert natural language questions into **syntactically correct and semantically accurate MySQL queries**.

    Below is the simplified database schema with table hierarchy and relationships. 
    Use this structure to reason about joins and key mappings accurately.

    {schema_text}

    ----------------------------
    ### Rules and Guidelines:
    1. **Use only the tables and columns present in the schema.**
    2. **Use proper MySQL syntax.**
       - Use `LIKE` instead of `ILIKE`.
       - Use backticks (\`) around identifiers when needed.
       - Do **not** use PostgreSQL operators or casts (e.g., `::text`, `ILIKE`, `LIMIT ALL`).
    3. **Infer relationships** logically from the schema and use correct JOINs.
    4. Always choose the correct SQL type (**SELECT**, **INSERT**, **UPDATE**, **DELETE**, etc.) based on the user request.
    5. **Never include explanations, markdown, or text outside the SQL query.**
    6. **Output only a single SQL query.**

    Now generate a **MySQL query only** for the following request:
    {user_prompt}
    [/INST]
    """

    output = llm(prompt, max_tokens=1024, temperature=0.2)
    generated_sql = output["choices"][0]["text"].strip()

    return render_template("index.html", sql=generated_sql, prompt=user_prompt)


# ✅ Route 2: Execute SQL (runs separately)
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