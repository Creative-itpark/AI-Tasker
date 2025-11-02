from sqlalchemy import create_engine, inspect

# Database connection
DB_CONFIG = {
    "user": "root",
    "password": "",
    "host": "localhost",
    "database": "creative_it_park"
}

# Target tables to inspect
# "roles", "role_user" ,
TARGET_TABLES = ["users",  "projects",  "project_members", "tasks"]


def get_schema_texts():
    """Fetch schema info + relationships as readable text for the LLM (with datatypes)"""
    engine = create_engine(
        f"mysql+pymysql://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}/{DB_CONFIG['database']}"
    )
    inspector = inspect(engine)

    schema_description = "Database Schema:\n"

    # --- 1️⃣ Extract columns (with datatypes) for each target table ---
    all_columns = {}
    for table in TARGET_TABLES:
        columns_info = inspector.get_columns(table)
        all_columns[table] = columns_info

    for table in TARGET_TABLES:
        schema_description += f"\nTable: {table}\nColumns:\n"

        for col in all_columns[table]:
            col_name = col["name"]
            col_type = str(col["type"])
            nullable = "NULL" if col["nullable"] else "NOT NULL"
            default = f" DEFAULT {col['default']}" if col["default"] is not None else ""
            schema_description += f"  - {col_name} ({col_type}, {nullable}{default})\n"

        # --- 2️⃣ Extract explicit foreign key relationships ---
        fks = inspector.get_foreign_keys(table)
        if fks:
            schema_description += "Relationships (from FK):\n"
            for fk in fks:
                referred_table = fk.get("referred_table")
                constrained_columns = ", ".join(fk.get("constrained_columns", []))
                referred_columns = ", ".join(fk.get("referred_columns", []))
                schema_description += f"  - {table}.{constrained_columns} → {referred_table}.{referred_columns}\n"

        # --- 3️⃣ Infer relationships based on naming convention ---
        inferred = []
        for col in [c["name"] for c in all_columns[table]]:
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
