CREATE TABLE transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    type TEXT NOT NULL,
    account TEXT NOT NULL,
    category TEXT NOT NULL,
    description TEXT,
    amount REAL NOT NULL,
    quantity INTEGER NOT NULL,
    total_amount REAL GENERATED ALWAYS AS (amount * quantity) STORED
);