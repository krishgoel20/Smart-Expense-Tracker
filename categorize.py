import os
from dotenv import load_dotenv
from groq import Groq
import mysql.connector
from ingest import DB_CONFIG, get_connection

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def get_categories():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name FROM categories")
    categories = cursor.fetchall()  # list of (id, name) tuples
    cursor.close()
    conn.close()
    return categories

def get_uncategorized_transactions(user_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, raw_description FROM transactions WHERE category_id IS NULL AND user_id = %s",
        (user_id,)
    )
    transactions = cursor.fetchall()
    cursor.close()
    conn.close()
    return transactions

import json

def categorize_transaction(description, category_names):
    category_list_str = ", ".join(category_names)

    prompt = f"""You are a financial transaction analyzer.
Given a transaction description, extract two things:
1. The most likely merchant/company name (clean, human-readable, no codes or IDs)
2. The single most appropriate category from this exact list: {category_list_str}

Rules:
- Respond with ONLY valid JSON, nothing else.
- Format: {{"merchant_name": "...", "category": "..."}}
- category must be an exact match from the list provided.
- If nothing fits well, use "Other" for category.
- If no merchant is identifiable, use null for merchant_name.

Transaction description: "{description}"
JSON:"""

    try:
        response = client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            response_format={"type": "json_object"}
        )
        result = json.loads(response.choices[0].message.content)
        return result.get("merchant_name"), result.get("category")

    except Exception as e:
        print(f"[ERROR] Groq API call failed for '{description}': {e}")
        return None, "Other"

def update_transaction_category(transaction_id, category_id, merchant_name):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE transactions SET category_id = %s, category_source = 'ai', merchant_name = %s WHERE id = %s",
        (category_id, merchant_name, transaction_id)
    )
    conn.commit()
    cursor.close()
    conn.close()

def correct_transaction_category(transaction_id, corrected_category_name):
    categories = get_categories()
    name_to_id = {name: cat_id for cat_id, name in categories}

    if corrected_category_name not in name_to_id:
        print(f"[ERROR] '{corrected_category_name}' is not a valid category.")
        return

    conn = get_connection()
    cursor = conn.cursor()

    # get the current (original) category before overwriting it
    cursor.execute("SELECT category_id FROM transactions WHERE id = %s", (transaction_id,))
    result = cursor.fetchone()
    original_category_id = result[0] if result else None

    corrected_category_id = name_to_id[corrected_category_name]

    # log the correction
    cursor.execute(
        """INSERT INTO correction_log (transaction_id, original_category_id, corrected_category_id)
           VALUES (%s, %s, %s)""",
        (transaction_id, original_category_id, corrected_category_id)
    )

    # apply the correction
    cursor.execute(
        "UPDATE transactions SET category_id = %s, category_source = 'manual' WHERE id = %s",
        (corrected_category_id, transaction_id)
    )

    conn.commit()
    cursor.close()
    conn.close()
    print(f"Txn {transaction_id} corrected to '{corrected_category_name}'.")

def run_categorization(user_id):
    categories = get_categories()
    name_to_id = {name: cat_id for cat_id, name in categories}
    category_names = list(name_to_id.keys())

    transactions = get_uncategorized_transactions(user_id)

    if not transactions:
        print("No uncategorized transactions found.")
        return

    for txn_id, description in transactions:
        merchant_name, predicted_name = categorize_transaction(description, category_names)

        if predicted_name not in name_to_id:
            print(f"[WARNING] Unrecognized category '{predicted_name}' for txn {txn_id}, defaulting to 'Other'")
            predicted_name = "Other"

        category_id = name_to_id[predicted_name]
        update_transaction_category(txn_id, category_id, merchant_name)
        print(f"Txn {txn_id}: '{description}' -> {predicted_name} | merchant: {merchant_name}")

if __name__ == "__main__":
    run_categorization()