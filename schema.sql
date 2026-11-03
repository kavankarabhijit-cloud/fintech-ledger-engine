CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

DROP TABLE IF EXISTS ledger_entries CASCADE;
DROP TABLE IF EXISTS transactions CASCADE;
DROP TABLE IF EXISTS accounts CASCADE;

CREATE TABLE accounts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    account_number VARCHAR(50) UNIQUE NOT NULL,
    account_type VARCHAR(20) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE transactions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    reference_id VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE ledger_entries (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    transaction_id UUID NOT NULL REFERENCES transactions(id) ON DELETE CASCADE,
    account_id UUID NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    entry_type VARCHAR(10) NOT NULL CHECK (entry_type IN ('DEBIT', 'CREDIT')),
    amount BIGINT NOT NULL CHECK (amount > 0),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_ledger_account ON ledger_entries(account_id);
CREATE INDEX idx_ledger_transaction ON ledger_entries(transaction_id);

-- Test Accounts inject karein
INSERT INTO accounts (id, account_number, account_type) VALUES 
('a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11', 'ACC_SENDER_01', 'SAVINGS'),
('b0eebc99-9c0b-4ef8-bb6d-6bb9bd380a22', 'ACC_RECEIVER_01', 'SAVINGS');

-- Initial Balance Transaction (Sender ko 10,000 INR = 1000000 paisa)
WITH init_txn AS (
    INSERT INTO transactions (reference_id, description)
    VALUES ('TXN_INIT_001', 'Initial Funding')
    RETURNING id
)
INSERT INTO ledger_entries (transaction_id, account_id, entry_type, amount)
SELECT id, 'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11', 'CREDIT', 1000000
FROM init_txn;
