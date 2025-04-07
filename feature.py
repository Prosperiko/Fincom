from flask import Flask, render_template, request, redirect, session, flash, jsonify, redirect, url_for
import mysql.connector
from mysql.connector import Error
from flask_bcrypt import Bcrypt
import sqlite3
import re
from flask_mail import Mail, Message
import random
from itsdangerous import URLSafeTimedSerializer
from datetime import datetime
import os
from flask_socketio import SocketIO, emit


app = Flask(__name__, template_folder='template', static_folder='static')
bcrypt = Bcrypt(app)

socketio = SocketIO(app)
app.secret_key = "your_secret_key"


app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False
app.config['MAIL_USERNAME'] = 'projectfinodido@gmail.com'  # email address
app.config['MAIL_PASSWORD'] = 'csqv yavo jcwj bghz'  # email password
app.config['MAIL_DEFAULT_SENDER'] = 'FINCOM'  # 
 

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "mydatabase.db")

mail = Mail(app)


@app.route('/')
def index():
    return render_template("index.html")

@app.route('/about')
def about():
    return render_template("about.html")

@app.route('/contact')
def contact():
    return render_template("contact.html")

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        fullname = request.form['fullname']
        profession = request.form['profession']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        nationality = request.form['nationality']
        customer_type = request.form['customer_type']

        # Check if all required fields are filled
        if not username or not email or not password or not customer_type:
            flash("All fields are required!", "error")
            return redirect('/signup')

        # Check if passwords match
        if password != confirm_password:
            flash("Passwords do not match!", "error")
            return redirect('/signup')

        # Hash the password
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')

        conn = sqlite3.connect("mydatabase.db")
        cursor = conn.cursor()

        try:
            # Check if the username or email already exists
            cursor.execute("SELECT * FROM users WHERE username = ? OR email = ?", (username, email))
            existing_user = cursor.fetchone()
            if existing_user:
                flash("Username or email already exists!", "error")
                return redirect('/signup')

            # Generate a verification PIN
            pin = random.randint(100000, 999999)

            # Send the verification email
            msg = Message("Email Verification", recipients=[email])
            msg.body = f"Your verification PIN is: {pin}"
            mail.send(msg)

            # Store user data temporarily
            session['pending_user'] = {
                'username': username,
                'fullname': fullname,
                'profession': profession,
                'email': email,
                'password': hashed_password,
                'nationality': nationality,
                'customer_type': customer_type,
                'pin': pin
            }

            flash("A verification PIN has been sent to your email. Please check your inbox.", "success")
            return redirect('/verify_pin')

        except sqlite3.Error as e:
            print(f"An error occurred: {e}")
            flash("An error occurred while signing up. Please try again.", "error")
        
        finally:
            cursor.close()
            conn.close()

    return render_template('signup.html')


@app.route('/verify_pin', methods=['GET', 'POST'])
def verify_pin():
    if request.method == 'POST':
        entered_pin = request.form['pin']
        pending_user = session.get('pending_user')
        print(f"Entered PIN: {entered_pin}, Pending User: {pending_user}")  # Debugging line

        if pending_user and str(pending_user['pin']) == entered_pin:
            # Check if the user already exists before inserting
            conn = sqlite3.connect("mydatabase.db")
            cursor = conn.cursor()
            try:
                cursor.execute("SELECT * FROM users WHERE email = ?", (pending_user['email'],))
                existing_user = cursor.fetchone()
                if existing_user:
                    flash("This email is already registered. Please log in.", "error")
                    return redirect('/login')

                # Insert new user into the database
                cursor.execute("""
                    INSERT INTO users (username, fullname, email, password, nationality, customer_type)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (pending_user['username'], pending_user['fullname'], pending_user['email'],
                      pending_user['password'], pending_user['nationality'], pending_user['customer_type']))
                conn.commit()
                flash("Signup successful! You can now log in.", "success")
                session.pop('pending_user', None)  # Clear the pending user data
                return redirect('/login')
            except sqlite3.Error as e:
                print(f"An error occurred: {e}")
                flash("An error occurred while signing up. Please try again.", "error")
            finally:
                cursor.close()
                conn.close()
        else:
            flash("Invalid PIN. Please try again.", "error")

    return render_template('verify_pin.html')

from itsdangerous import URLSafeTimedSerializer

# Flask-Mail Configuration (Already in your code)
app.config['MAIL_DEFAULT_SENDER'] = 'projectfinodido@gmail.com'

# Serializer for token generation
serializer = URLSafeTimedSerializer(app.secret_key)


@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form['email']

        try:
            conn = sqlite3.connect("mydatabase.db")
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
            user = cursor.fetchone()
            conn.close()
        except Exception as e:
            flash("An error occurred while accessing the database.", "error")
            return render_template('forgot_password.html')

        if user:
            # Generate a secure token
            token = serializer.dumps(email, salt='password-reset')

            # Create reset link
            reset_url = f"http://127.0.0.1:5000/reset_password/{token}"

            # Send reset link via email
            msg = Message("Password Reset Request", recipients=[email])
            msg.body = f"Click the link below to reset your password:\n\n{reset_url}\n\nThis link expires in 10 minutes."

            try:
                mail.send(msg)
                flash("A password reset link has been sent to your email.", "success")
            except Exception as e:
                flash("Failed to send email. Please try again later.", "error")
        else:
            flash("No account found with that email!", "error")

    return render_template('forgot_password.html')


@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    try:
        # Verify the token
        email = serializer.loads(token, salt='password-reset', max_age=600)  # 10 minutes expiration
    except Exception as e:
        flash("The password reset link is invalid or has expired.", "error")
        return render_template('forgot_password.html')

    if request.method == 'POST':
        new_password = request.form['new_password']
        hashed_password = bcrypt.generate_password_hash(new_password).decode('utf-8')  # Hash the new password
        
        try:
            conn = sqlite3.connect("mydatabase.db")
            cursor = conn.cursor()
            # Update the user's password in the database
            cursor.execute("UPDATE users SET password = ? WHERE email = ?", (hashed_password, email))
            conn.commit()
            cursor.close()
            conn.close()
            flash("Your password has been updated successfully.", "success")
            return redirect('/login')  # Redirect to login page after successful reset
        except Exception as e:
            flash("An error occurred while updating the password.", "error")

    return render_template('reset_password.html', token=token)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        try:
            conn = sqlite3.connect("mydatabase.db")
            cursor = conn.cursor()
            
            # Query user by username
            cursor.execute("SELECT id, username, password, customer_type FROM users WHERE username = ?", (username,))
            user = cursor.fetchone()

            if user:
                user_id, db_username, stored_password, customer_type = user
                print(f"User found: {db_username}, {stored_password}, {customer_type}")  # Debug print

                if bcrypt.check_password_hash(stored_password, password):
                    # Store user info in session
                    session['user_id'] = user_id
                    session['username'] = db_username
                    session['customer_type'] = customer_type

                    flash("Login successful!", "success")

                    # Redirect based on customer type
                    return redirect('/home1' if customer_type.lower() == 'individual' else '/home')
                else:
                    flash("Invalid password!", "error")
                    print("Invalid password")  # Debug print
            else:
                flash("User not found!", "error")
                print("User not found")  # Debug print

        except sqlite3.Error as e:
            flash(f"An error occurred: {e}", "error")
            print(f"Database error: {e}")  # Debug print
        finally:
            cursor.close()
            conn.close()

        return redirect('/login')  # Redirect back to login on failure

    # Render the login page for GET requests
    return render_template('login.html')




def generate_welcome_message(username, customer_type):
    if customer_type.lower() == "individual":
        return f"Welcome, {username}! Enjoy your personal finance dashboard."
    else:
        return f"Welcome, {username}! Manage your business transactions efficiently."

    
@app.route('/home')
def home():
    if 'username' in session:
        username = session['username']
        customer_type = session['customer_type']
        welcome_message = generate_welcome_message(username, customer_type)
        return render_template('home.html', message=welcome_message)
    else:
        flash("You need to log in first!", "error")
        return redirect('/login')

@app.route('/home1')
def home1():
    if 'username' in session:
        username = session['username']
        customer_type = session['customer_type']
        welcome_message = generate_welcome_message(username, customer_type)
        return render_template('home1.html', message=welcome_message)  # Render a different template for home1
    else:
        flash("You need to log in first!", "error")
        return redirect('/login')


@app.route('/balances')
def balances():
    if 'user_id' not in session:
        flash("Please log in to view your balance.", "error")
        return redirect('/login')

    conn = get_db_connection()
    conn.row_factory = sqlite3.Row  # Enables dictionary-like access
    cursor = conn.cursor()

    user_id = session.get('user_id')

    try:
        cursor.execute("""
            SELECT 
                COALESCE(SUM(CASE WHEN t.transaction_type = 'cash' THEN t.amount ELSE 0 END), 0) AS cash_balance,
                COALESCE(SUM(CASE WHEN t.transaction_type = 'card' THEN t.amount ELSE 0 END), 0) AS card_balance
            FROM 
                transactions t 
            WHERE 
                t.user_id = ?;
        """, (user_id,))
        
        balance = cursor.fetchone()

        # Convert SQLite Row to dictionary
        balance_dict = dict(balance) if balance else {"cash_balance": 0, "card_balance": 0}

        # Determine home page dynamically
        customer_type = session.get("customer_type", "individual").lower()
        user_home = "home1" if customer_type == "individual" else "home"

        return render_template('balances.html', balance=balance_dict, user_home=user_home)

    except sqlite3.Error as e:
        flash(f"An error occurred: {e}", "error")
        return redirect('/error')  
    
    finally:
        cursor.close()
        conn.close()
        




def update_profit(user_id):
    """Calculate and update profit based on transactions for a user."""
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        try:
            # Calculate total income
            cursor.execute("""
                SELECT COALESCE(SUM(amount), 0) FROM transactions 
                WHERE user_id = ? AND type = 'income';
            """, (user_id,))
            total_income = cursor.fetchone()[0]  # Fetch first value
            
            # Calculate total expenses
            cursor.execute("""
                SELECT COALESCE(SUM(amount), 0) FROM transactions 
                WHERE user_id = ? AND type = 'expense';
            """, (user_id,))
            total_expenses = cursor.fetchone()[0]  # Fetch first value

            # Update the users table with the calculated profit
            profit = total_income - total_expenses
            cursor.execute("UPDATE users SET profit = ? WHERE id = ?", (profit, user_id))
            conn.commit()
        except sqlite3.Error as e:
            print(f"Error updating profit: {e}")
            conn.rollback()
        finally:
            cursor.close()
            conn.close()

def add_expenses(submitter_name, expense_type, account, category, description, amount, quantity):
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        try:
            # Fetch the user_id based on the username
            cursor.execute("SELECT id FROM users WHERE username = ?", (submitter_name,))
            user_row = cursor.fetchone()
            if not user_row:
                flash("User  not found. Please log in again.", "error")
                return
            user_id = user_row[0]

            # Calculate total amount
            total_amount = amount * quantity  # Total amount is calculated here

            # Insert expense with user_id
            cursor.execute("""
                INSERT INTO transactions (user_id, name, type, account, category, description, amount, quantity)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (user_id, submitter_name, expense_type, account, category, description, total_amount, quantity))

            # Update user profit
            cursor.execute("""
                UPDATE users
                SET profit = COALESCE(profit, 0) - ?,
                    total_expenses = COALESCE(total_expenses, 0) + ?
                WHERE id = ?
            """, (total_amount, total_amount, user_id))

            conn.commit()
            flash("Expense added successfully!", "success")

        except sqlite3.Error as e:
            flash(f"Error inserting expense: {e}", "error")
            conn.rollback()
        finally:
            cursor.close()
            conn.close()
@app.route('/expenses', methods=['GET', 'POST'])
def expenses():
    if request.method == 'POST':
        try:
            submitter_name = session.get('username')
            if not submitter_name:
                flash("User not logged in. Please log in to add expenses.", "error")
                return redirect('/login')

            expense_type = request.form['expense_type']
            account = request.form['account']
            category = request.form['category']
            description = request.form['description']
            amount = float(request.form['amount'])
            quantity = float(request.form['quantity'])

            add_expenses(submitter_name, expense_type, account, category, description, amount, quantity)
            update_profit(session.get('user_id'))  # Update user profit

            return redirect('/home1')

        except (KeyError, ValueError):
            flash("Please fill in all fields correctly.", "error")
        except Exception as e:
            flash(f"An error occurred: {str(e)}", "error")

    return render_template('expenses.html')
# Function to calculate total expenses
def sum_total_expenses():
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT COALESCE(SUM(amount * quantity), 0) FROM transactions WHERE type='expense'")
            return cursor.fetchone()[0]
        except sqlite3.Error as e:
            print(f"Error calculating total expenses: {e}")
            return 0
        finally:
            cursor.close()
            conn.close()

@app.route('/total_expenses')
def total_expenses():
    return render_template('total_expenses.html', total=sum_total_expenses())

# Function to add an income
def add_income(submitter_name, income_type, account, category, description, amount, quantity):
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        try:
            # Fetch the user_id based on the username
            cursor.execute("SELECT id FROM users WHERE username = ?", (submitter_name,))
            user_row = cursor.fetchone()
            if not user_row:
                flash("User  not found. Please log in again.", "error")
                return
            user_id = user_row[0]

            # Calculate total amount
            total_amount = amount * quantity  # Total amount is calculated here

            # Insert income with user_id
            cursor.execute("""
                INSERT INTO transactions (user_id, name, type, account, category, description, amount, quantity)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (user_id, submitter_name, income_type, account, category, description, total_amount, quantity))

            # Update user profit
            cursor.execute("""
                UPDATE users
                SET profit = COALESCE(profit, 0) + ?,
                    total_income = COALESCE(total_income, 0) + ?
                WHERE id = ?
            """, (total_amount, total_amount, user_id))

            conn.commit()
            flash("Income added successfully!", "success")

        except sqlite3.Error as e:
            flash(f"Error inserting income: {e}", "error")
            conn.rollback()
        finally:
            cursor.close()
            conn.close()

@app.route('/income', methods=['GET', 'POST'])
def income():
    if request.method == 'POST':
        try:
            submitter_name = session.get('username')
            if not submitter_name:
                flash("User not logged in. Please log in to add income.", "error")
                return redirect('/login')

            income_type = request.form['income_type']
            account = request.form['account']
            category = request.form['category']
            description = request.form['description']
            amount = float(request.form['amount'])
            quantity = float(request.form['quantity'])

            add_income(submitter_name, income_type, account, category, description, amount, quantity)
            update_profit(session.get('user_id'))  # Update user profit

            return redirect('/home1')

        except (KeyError, ValueError):
            flash("Please fill in all fields correctly.", "error")
               user = cursor.fetchone()
            if user:
                username, cash_balance, card_balance = user
            else:
                return jsonify({"error": "User  not found"}), 404

            # Fetch total income and expenses from transactions
            cursor.execute("""
                SELECT 
                    SUM(CASE WHEN type = 'income' THEN amount ELSE 0 END) AS total_income,
                    SUM(CASE WHEN type = 'expense' THEN amount ELSE 0 END) AS total_expenses
                FROM transactions
                WHERE user_id = ?
            """, (user_id,))
            transaction_row = cursor.fetchone()
            total_income = transaction_row[0] or 0
            total_expenses = transaction_row[1] or 0

            # Combine user data with income and expenses
            comparison_data = {
                "username": username,
                "cash_balance": cash_balance or 0,
                "card_balance": card_balance or 0,
                "total_income": total_income,
                "total_expenses": total_expenses
            }

            return jsonify(comparison_data)
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return jsonify({"error": "Database error"}), 500

@app.route('/api/expenses', methods=['GET'])
def fetch_expenses():
