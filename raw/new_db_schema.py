from sqlalchemy import create_engine, inspect

# Database connection
DB_CONFIG = {
    "user": "root",
    "password": "",
    "host": "localhost",
    "database": "creative_it_park"
}

# target_tables = ["employees", "clients", "projects", "tasks", "project_assignments", "abc"]
# TARGET_TABLES = ["projects", "project_members", "tasks", "task_category", "task_users", "task_labels", "users"]
TARGET_TABLES = ["users", "projects", "tasks", "project_members"]


def get_schema_texts():
    """Fetch schema info + relationships as readable text for the LLM"""
    engine = create_engine(f"mysql+pymysql://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}/{DB_CONFIG['database']}")
    inspector = inspect(engine)

    schema_description = "Database Schema:\n"

    # --- 1️⃣ Extract columns for each target table ---
    all_columns = {}
    for table in TARGET_TABLES:
        all_columns[table] = [col['name'] for col in inspector.get_columns(table)]

    for table in TARGET_TABLES:
        schema_description += f"\nTable: {table}\nColumns:\n"
        for column in all_columns[table]:
            schema_description += f"  - {column}\n"

        # --- 2️⃣ Extract explicit foreign key relationships ---
        fks = inspector.get_foreign_keys(table)
        if fks:
            schema_description += "Relationships (from FK):\n"
            for fk in fks:
                referred_table = fk.get('referred_table')
                constrained_columns = ", ".join(fk.get('constrained_columns', []))
                referred_columns = ", ".join(fk.get('referred_columns', []))
                schema_description += f"  - {table}.{constrained_columns} → {referred_table}.{referred_columns}\n"

        # --- 3️⃣ Infer relationships based on naming convention ---
        inferred = []
        for col in all_columns[table]:
            if col.endswith("_id"):
                ref_table = col[:-3]
                if ref_table in TARGET_TABLES:
                    inferred.append(f"{table}.{col} → {ref_table}.id")
        if inferred:
            schema_description += "Relationships (inferred):\n"
            for r in inferred:
                schema_description += f"  - {r}\n"

    return schema_description.strip()

if __name__ == "__main__":
    print(get_schema_texts())
