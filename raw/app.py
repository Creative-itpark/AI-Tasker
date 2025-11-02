from flask import Flask, request, render_template
from llama_cpp import Llama
# from new_db_schema import get_schema_texts
from get_schema import get_schema_texts
import pymysql

app = Flask(__name__)

# Load model once
llm = Llama(
    model_path="model/codellama-7b-instruct.Q4_K_M.gguf",
    n_ctx=4096,
    n_threads=2,
    n_batch=256,
    use_mlock=False,
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
    You are an expert in MySQL.
    Below is the database schema with table hierarchy and relationships.
    Use it to generate accurate and efficient SQL queries.
    Generate only a valid SQL command (no text, markdown, or explanation)
    based strictly on this database schema:

    {schema_text}

    Follow these rules:
    - Use only tables/columns from the schema.
    - Ensure correct MySQL syntax.
    - Choose the right SQL type (SELECT, INSERT, UPDATE, DELETE, CREATE, DROP, ALTER) based on the request.

    User request:
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