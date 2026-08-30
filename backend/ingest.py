import csv
import os
from dotenv import load_dotenv
import mysql.connector

load_dotenv()

# --- DB connection config ---
DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "database": os.getenv("DB_NAME")
}

def get_connection():
    return mysql.connector.connect(**DB_CONFIG)

def ingest_rows(reader, user_id):
    conn = get_connection()
    cursor = conn.cursor()
    rows_inserted = 0

    for row in reader:
        insert_query = """
            INSERT INTO transactions
                (txn_date, raw_description, amount, txn_type, payment_method, user_id)
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        values = (
            row["date"], row["description"], float(row["amount"]),
            row["type"], row["payment_method"], user_id
        )
        cursor.execute(insert_query, values)
        rows_inserted += 1

    conn.commit()
    cursor.close()
    conn.close()
    return rows_inserted

def ingest_csv(filepath, user_id):
    with open(filepath, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        count = ingest_rows(reader, user_id)
    print(f"Inserted {count} transactions.")

if __name__ == "__main__":
    ingest_csv("data/mock_transactions.csv", user_id=1)