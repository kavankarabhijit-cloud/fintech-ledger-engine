from ledger_engine import get_db_connection, DoubleEntryLedgerEngine, InsufficientFundsError

if __name__ == "__main__":
    with get_db_connection() as connection:
        engine = DoubleEntryLedgerEngine(connection)
        
        user_wallet = "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11"
        merchant_account = "b0eebc99-9c0b-4ef8-bb6d-6bb9bd380a22"

        try:
            result = engine.execute_double_entry_transfer(
                reference_id="TXN_TEST_001",
                description="Merchant Checkout Settlement",
                from_account_id=user_wallet,
                to_account_id=merchant_account,
                amount_paisa=50000  # ₹500.00
            )
            print("\n==========================================")
            print("Transfer Executed Successfully!")
            print(result)
            print("==========================================\n")
        except InsufficientFundsError as e:
            print("\nFailed due to balance:", e)
        except Exception as e:
            print("\nTransaction rolled back automatically:", e)
            
            