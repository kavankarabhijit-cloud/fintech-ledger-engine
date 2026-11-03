import psycopg2
import psycopg2.extras
from decimal import Decimal
import os

class InsufficientFundsError(Exception):
    pass

class LedgerInvariantViolationError(Exception):
    pass

def get_db_connection():
    return psycopg2.connect(
        dbname=os.getenv("DB_NAME", "fintech_ledger"),
        user=os.getenv("DB_USER", "anike"),
        password=os.getenv("DB_PASSWORD", "password123"),
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", 5432))
    )

class DoubleEntryLedgerEngine:
    def __init__(self, connection):
        self.conn = connection

    def get_account_balance(self, cursor, account_id):
        cursor.execute(
            """
            SELECT COALESCE(
                SUM(CASE WHEN entry_type = 'CREDIT' THEN amount ELSE -amount END), 
                0
            ) AS balance
            FROM ledger_entries
            WHERE account_id = %s;
            """,
            (account_id,)
        )
        row = cursor.fetchone()
        return row['balance'] if row else Decimal('0')

    def execute_double_entry_transfer(self, reference_id, description, from_account_id, to_account_id, amount_paisa):
        if amount_paisa <= 0:
            raise ValueError("Transfer amount must be positive.")

        with self.conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            accounts_to_lock = sorted([from_account_id, to_account_id])
            cur.execute(
                "SELECT id, account_number, account_type FROM accounts WHERE id IN %s FOR UPDATE;",
                (tuple(accounts_to_lock),)
            )
            locked_accounts = {row['id']: row for row in cur.fetchall()}

            if len(locked_accounts) < 2:
                raise ValueError("One or both accounts do not exist.")

            sender_balance = self.get_account_balance(cur, from_account_id)
            if sender_balance < amount_paisa:
                raise InsufficientFundsError(f"Insufficient funds. Available: {sender_balance}, Required: {amount_paisa}")

            cur.execute(
                """
                INSERT INTO transactions (reference_id, description)
                VALUES (%s, %s)
                RETURNING id;
                """,
                (reference_id, description)
            )
            txn_id = cur.fetchone()['id']

            cur.execute(
                """
                INSERT INTO ledger_entries (transaction_id, account_id, entry_type, amount)
                VALUES (%s, %s, 'DEBIT', %s), (%s, %s, 'CREDIT', %s);
                """,
                (txn_id, from_account_id, amount_paisa, txn_id, to_account_id, amount_paisa)
            )

            cur.execute(
                """
                SELECT 
                    SUM(CASE WHEN entry_type = 'DEBIT' THEN amount ELSE 0 END) as total_debit,
                    SUM(CASE WHEN entry_type = 'CREDIT' THEN amount ELSE 0 END) as total_credit
                FROM ledger_entries
                WHERE transaction_id = %s;
                """,
                (txn_id,)
            )
            check = cur.fetchone()
            if check['total_debit'] != check['total_credit']:
                raise LedgerInvariantViolationError("Double-entry invariant broken: DEBIT != CREDIT")

            self.conn.commit()
            return {
                "status": "SUCCESS",
                "transaction_id": str(txn_id),
                "transferred_paisa": amount_paisa,
                "reference_id": reference_id
            }
