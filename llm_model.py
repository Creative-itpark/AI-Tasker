from flask import Flask, request, render_template
from llama_cpp import Llama
from get_schema import get_schema_texts
import pymysql

app = Flask(__name__)

# ============================================================
# ✅ Load SQLCoder-7B-2 (GGUF) model once at startup
# ============================================================

# Option 1 — Load directly from Hugging Face (auto-download)
llm = Llama.from_pretrained(
    repo_id="MaziyarPanahi/Mistral-7B-Instruct-v0.3-GGUF",
    filename="Mistral-7B-Instruct-v0.3.Q4_K_M.gguf",
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
    You are a professional MySQL query generator trained to work strictly within a given database schema.

    Below is the complete database schema with all tables, columns, and foreign key relationships:
    {schema_text}

    Your task:
    Generate ONE valid, syntactically correct, and optimized MySQL query that exactly fulfills the user's request.

    Guidelines:
    1. Use ONLY the tables, columns, and relationships defined in the schema above.
    2. The query must be 100% executable — no placeholders, assumptions, or extra commentary.
    3. Do NOT include markdown, explanations, or code fences.
    4. Output only the SQL command itself (nothing else).
    5. If JOINs are needed, use proper foreign key relationships.
    6. Support SELECT, INSERT, UPDATE, and DELETE operations as appropriate.
    7. Use correct MySQL syntax and data types (e.g., strings in quotes, correct date formats).
    8. If any data must be looked up by name (like a project or user), use subqueries based on the schema.

    User Request:
    {user_prompt}
    [/INST]
    """

    output = llm(prompt, max_tokens=1024, temperature=0.2)
    text = output["choices"][0]["text"]
    generated_sql = text.split("<SQL>")[-1].split("</SQL>")[0].strip()

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