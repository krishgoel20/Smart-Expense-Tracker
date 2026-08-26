import io
import csv
from auth import hash_password, verify_password, create_access_token, decode_access_token, get_user_by_username, create_user
from fastapi import FastAPI, UploadFile, File, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from ingest import get_connection, ingest_rows
from pydantic import BaseModel, Field, field_validator
from datetime import date
from categorize import run_categorization, correct_transaction_category

class UserRegister(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6)

class UserLogin(BaseModel):
    username: str
    password: str

class TransactionCreate(BaseModel):
    txn_date: date
    raw_description: str = Field(..., min_length=1, max_length=255)
    amount: float = Field(..., gt=0)
    txn_type: str          # "debit" or "credit"
    payment_method: str = "Other"

    @field_validator("txn_type")
    @classmethod
    def validate_txn_type(cls, v):
        if v not in ("debit", "credit"):
            raise ValueError("txn_type must be 'debit' or 'credit'")
        return v

    @field_validator("txn_date")
    @classmethod
    def validate_txn_date(cls, v):
        if v > date.today():
            raise ValueError("txn_date cannot be in the future")
        return v

app = FastAPI(title="Smart Expense Tracker API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBearer()

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return {"id": int(payload["sub"]), "username": payload["username"]}

@app.post("/auth/register")
def register(user: UserRegister):
    existing = get_user_by_username(user.username)
    if existing:
        raise HTTPException(status_code=400, detail="Username already taken")

    user_id = create_user(user.username, user.password)
    token = create_access_token(user_id, user.username)
    return {"access_token": token, "token_type": "bearer"}

@app.post("/auth/login")
def login(credentials: UserLogin):
    user = get_user_by_username(credentials.username)
    if not user or not verify_password(credentials.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    token = create_access_token(user["id"], user["username"])
    return {"access_token": token, "token_type": "bearer"}

@app.get("/")
def root():
    return {"message": "Smart Expense Tracker API is running"}

@app.get("/transactions")
def list_transactions(page: int = 1, page_size: int = 20, current_user: dict = Depends(get_current_user)):
    offset = (page - 1) * page_size
    user_id = current_user["id"]

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT COUNT(*) AS total FROM transactions WHERE user_id = %s", (user_id,))
    total = cursor.fetchone()["total"]

    cursor.execute("""
        SELECT t.id, t.txn_date, t.raw_description, t.merchant_name,
               t.amount, t.txn_type, t.payment_method,
               c.name AS category, t.category_source
        FROM transactions t
        LEFT JOIN categories c ON t.category_id = c.id
        WHERE t.user_id = %s
        ORDER BY t.txn_date DESC
        LIMIT %s OFFSET %s
    """, (user_id, page_size, offset))
    transactions = cursor.fetchall()

    cursor.close()
    conn.close()

    return {
        "page": page,
        "page_size": page_size,
        "total": total,
        "total_pages": (total + page_size - 1) // page_size,
        "transactions": transactions
    }

@app.post("/transactions")
def create_transaction(txn: TransactionCreate, current_user: dict = Depends(get_current_user)):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """INSERT INTO transactions
               (txn_date, raw_description, amount, txn_type, payment_method, user_id)
           VALUES (%s, %s, %s, %s, %s, %s)""",
        (txn.txn_date, txn.raw_description, txn.amount, txn.txn_type, txn.payment_method, current_user["id"])
    )
    conn.commit()
    new_id = cursor.lastrowid
    cursor.close()
    conn.close()
    return {"id": new_id, "message": "Transaction created", **txn.model_dump()}

@app.get("/summary/by-category")
def summary_by_category():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT c.name AS category, SUM(t.amount) AS total_spent
        FROM transactions t
        JOIN categories c ON t.category_id = c.id
        WHERE t.txn_type = 'debit'
        GROUP BY c.name
        ORDER BY total_spent DESC
    """)
    result = cursor.fetchall()
    cursor.close()
    conn.close()
    return result

@app.get("/summary/monthly")
def summary_monthly():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT
            DATE_FORMAT(t.txn_date, '%Y-%m') AS month,
            SUM(CASE WHEN t.txn_type = 'debit' THEN t.amount ELSE 0 END) AS total_spent,
            SUM(CASE WHEN t.txn_type = 'credit' THEN t.amount ELSE 0 END) AS total_income
        FROM transactions t
        GROUP BY month
        ORDER BY month
    """)
    result = cursor.fetchall()
    cursor.close()
    conn.close()
    return result

@app.get("/summary/top-merchants")
def summary_top_merchants():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT t.merchant_name, COUNT(*) AS num_transactions, SUM(t.amount) AS total_spent
        FROM transactions t
        WHERE t.txn_type = 'debit' AND t.merchant_name IS NOT NULL
        GROUP BY t.merchant_name
        ORDER BY total_spent DESC
        LIMIT 5
    """)
    result = cursor.fetchall()
    cursor.close()
    conn.close()
    return result

class CategoryCorrection(BaseModel):
    corrected_category: str

@app.put("/transactions/{transaction_id}/category")
def correct_category(transaction_id: int, correction: CategoryCorrection):
    correct_transaction_category(transaction_id, correction.corrected_category)
    return {"message": f"Transaction {transaction_id} corrected to '{correction.corrected_category}'"}

@app.post("/categorize")
def categorize_pending(current_user: dict = Depends(get_current_user)):
    run_categorization(current_user["id"])
    return {"message": "Categorization run complete"}

@app.post("/upload")
async def upload_csv(file: UploadFile = File(...), current_user: dict = Depends(get_current_user)):
    contents = await file.read()
    decoded = contents.decode("utf-8")
    reader = csv.DictReader(io.StringIO(decoded))
    rows_inserted = ingest_rows(reader, current_user["id"])
    return {"message": f"Inserted {rows_inserted} transactions", "filename": file.filename}