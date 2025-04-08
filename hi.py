import sqlite3

def create_tables():
    conn = sqlite3.connect("mydatabase.db")
    cursor = conn.cursor()

    # Create users table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL UNIQUE,
        fullname TEXT,
        email TEXT NOT NULL UNIQUE,
        password TEXT NOT NULL,
        nationality TEXT,
        customer_type TEXT,
        profit REAL DEFAULT 0,
        total_income REAL DEFAULT 0,
        total_expenses REAL DEFAULT 0,
        cash_balance REAL DEFAULT 0,
        card_balance REAL DEFAULT 0
    )
    """)

    # Create transactions table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        name TEXT,
        type TEXT,
        account TEXT,
        category TEXT,
        description TEXT,
        amount REAL,
        quantity REAL,
        transaction_type TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )
    """)

    conn.commit()
    cursor.close()
    conn.close()

if __name__ == "__main__":
    create_tables()
    print("Database and tables created successfully.")
    
    
import sqlite3

def delete_user(user_id):
    # Connect to the SQLite database
    conn = sqlite3.connect('mydatabase.db')
    cursor = conn.cursor()

    # SQL command to delete a user by ID
    try:
        cursor.execute("DELETE FROM users WHERE id = ?;", (user_id,))
        if cursor.rowcount > 0:
            print(f"User  with ID {user_id} deleted successfully.")
        else:
            print(f"No user found with ID {user_id}.")
    except sqlite3.Error as e:
        print(f"An error occurred: {e}")

    # Commit the changes and close the connection
    conn.commit()
    conn.close()

# Example usage
delete_user(7)  # Replace 1 with the ID of the user you want to delete


