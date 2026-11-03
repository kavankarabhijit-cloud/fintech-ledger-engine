from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field
import psycopg2.extras
from ledger_engine import (
    get_db_connection,
    DoubleEntryLedgerEngine,
    InsufficientFundsError,
    LedgerInvariantViolationError
)

app = FastAPI(title="Distributed FinTech Ledger API")

class TransferRequest(BaseModel):
    reference_id: str = Field(..., example="TXN_API_001")
    description: str = Field(..., example="Online Merchant Payout")
    from_account_id: str = Field(..., example="a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11")
    to_account_id: str = Field(..., example="b0eebc99-9c0b-4ef8-bb6d-6bb9bd380a22")
    amount_inr: float = Field(..., gt=0, example=150.00)

@app.get("/")
def home():
    return {"status": "ONLINE", "service": "FinTech Ledger Engine"}

@app.get("/balance/{account_id}")
def get_balance(account_id: str):
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                engine = DoubleEntryLedgerEngine(conn)
                balance_raw = engine.get_account_balance(cur, account_id)
                balance_paisa = int(balance_raw)
                return {
                    "account_id": account_id,
                    "balance_inr": round(balance_paisa / 100.0, 2),
                    "balance_paisa": balance_paisa
                }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/transfer")
def transfer_money(payload: TransferRequest):
    amount_paisa = int(round(payload.amount_inr * 100))
    try:
        with get_db_connection() as conn:
            engine = DoubleEntryLedgerEngine(conn)
            result = engine.execute_double_entry_transfer(
                reference_id=payload.reference_id,
                description=payload.description,
                from_account_id=payload.from_account_id,
                to_account_id=payload.to_account_id,
                amount_paisa=amount_paisa
            )
            return result
    except InsufficientFundsError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
