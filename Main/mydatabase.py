import sqlite3

def init_db():
    # Connect to the SQLite database (it will be created if it doesn't exist)
    conn = sqlite3.connect("mydatabase.db")
    cursor = conn.cursor()

    # Create the users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            fullname TEXT,
            profession TEXT,
            email TEXT UNIQUE,
            password TEXT,
            nationality TEXT,
            customer_type TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Create the workers table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS workers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            worker_name TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')

    # Commit the changes and close the connection
    conn.commit()
    cursor.close()
    conn.close()

import sqlite3
import bcrypt

# Connect to the database (or create it if it doesn't exist)
connection = sqlite3.connect('mydatabase.db')

# Create a cursor object to execute SQL commands
cursor = connection.cursor()

# Create the users table if it doesn't already exist
cursor.execute('''
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    fullname TEXT NOT NULL,
    profession TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    password TEXT NOT NULL,
    nationality TEXT NOT NULL,
    customer_type TEXT NOT NULL
)
''')

# List of users to insert into the table
users = [
    
    ('michaelbrown', 'Michael Brown', 'DevOps Engineer', 'michaelbrown@example.com', 'devops123', 'American', 'Premium'),
    ('sarahwhite', 'Sarah White', 'Marketing Specialist', 'sarahwhite@example.com', 'marketing456', 'Canadian', 'Standard'),
    ('davidlee', 'David Lee', 'Business Analyst', 'davidlee@example.com', 'business789', 'Singaporean', 'Premium'),
    ('lauragarcia', 'Laura Garcia', 'Graphic Designer', 'lauragarcia@example.com', 'designpass654', 'Mexican', 'Standard'),
    ('robertwilson', 'Robert Wilson', 'Cybersecurity Expert', 'robertwilson@example.com', 'cybersecure321', 'British', 'Premium'),
    ('angelawright', 'Angela Wright', 'HR Manager', 'angelawright@example.com', 'hrmanager123', 'Australian', 'Standard')
]

# Encrypt passwords and prepare data for insertion
encrypted_users = [
    (user[0], user[1], user[2], user[3], bcrypt.hashpw(user[4].encode('utf-8'), bcrypt.gensalt()).decode('utf-8'), user[5], user[6])
    for user in users
]

# Insert users into the table
cursor.executemany('''
INSERT INTO users (username, fullname, profession, email, password, nationality, customer_type)
VALUES (?, ?, ?, ?, ?, ?, ?)
''', encrypted_users)

# Commit the changes and close the connection
connection.commit()
connection.close()

print("Users table populated successfully!")

if __name__ == '__main__':
    init_db()  # Call the function to initialize the database
    
    
