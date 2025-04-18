from flask import Flask, render_template, request, redirect, session, flash, jsonify, redirect, url_for, send_file
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
from email.mime.text import MIMEText
import pandas as pd
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv
load_dotenv()
import os
from werkzeug.utils import secure_filename
from datetime import datetime, timezone
import tempfile

# Setting up the API key and model

import google.generativeai as genai


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
        number_of_workers = request.form.get('number_of_workers', 0)  # Default to 0 if not provided

        # Check if all required fields are filled
        if not username or not email or not password or not customer_type:
            flash("All fields are required!", "error")
            return redirect('/signup')

        # Check if passwords match
        if password != confirm_password:
            flash("Passwords do not match!", "error")
            return redirect('/signup')

        # Hash the password using Flask-Bcrypt
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
                'pin': pin,
                'number_of_workers': int(number_of_workers) if customer_type == 'company' else 0  # Store only if company
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
        if entered_pin == str(session['pending_user']['pin']):
            # Insert user into the database
            conn = sqlite3.connect("mydatabase.db")
            cursor = conn.cursor()
            try:
                cursor.execute('''
                    INSERT INTO users (username, fullname, profession, email, password, nationality, customer_type, number_of_workers)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    session['pending_user']['username'],
                    session['pending_user']['fullname'],
                    session['pending_user']['profession'],
                    session['pending_user']['email'],
                    session['pending_user']['password'],
                    session['pending_user']['nationality'],
                    session['pending_user']['customer_type'],
                    session['pending_user']['number_of_workers']  # Save the number of workers
                ))
                conn.commit()

                flash("Registration successful! You can now log in.", "success")
                return redirect('/login')
            except sqlite3.Error as e:
                print(f"An error occurred: {e}")
                flash("An error occurred while verifying your account. Please try again.", "error")
            finally:
                cursor.close()
                conn.close()
        else:
            flash("Invalid PIN. Please try again.", "error")
            return redirect('/verify_pin')

    return render_template('verify_pin.html')  # Ensure you return a valid response here



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
        username = request.form.get('username', '').strip()  # Use get() to avoid KeyError
        password = request.form.get('password', '').strip()

        if not username or not password:
            flash("Username and password are required!", "error")
            return redirect('/login')

        try:
            conn = sqlite3.connect("mydatabase.db")
            cursor = conn.cursor()
            
            # Query user by username, including email
            cursor.execute("SELECT id, username, email, password, customer_type FROM users WHERE username = ?", (username,))
            user = cursor.fetchone()

            if user:
                user_id, db_username, email, stored_password, customer_type = user
                print(f"User  found: {db_username}, {email}, {customer_type}")  # Debug print

                # Check if the password matches
                if bcrypt.check_password_hash(stored_password, password):
                    # Store user info in session
                    session['user_id'] = user_id
                    session['username'] = db_username
                    session['email'] = email  # Add email to session
                    session['customer_type'] = customer_type

                    print("Session set:", session)  # Debug print to check session data

                    flash("Login successful!", "success")

                    # Redirect based on customer type
                    return redirect('/home1' if customer_type.lower() == 'individual' else '/home1')
                else:
                    flash("Invalid password!", "error")
                    print("Invalid password")  # Debug print
            else:
                flash("User  not found!", "error")
                print("User  not found")  # Debug print

        except sqlite3.Error as e:
            flash(f"An error occurred while accessing the database: {e}", "error")
            print(f"Database error: {e}")  # Debug print
        finally:
            cursor.close()
            conn.close()

        # Redirect back to login on failure
        return redirect('/login')

    # Render the login page for GET requests
    return render_template('login.html')




def generate_welcome_message(username, customer_type):
    if customer_type.lower() == "individual":
        return f"Hi { username }, take control of your finances with your dashboard."
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
        user_id = session['user_id']  # Get the logged-in user's ID

        conn = sqlite3.connect("mydatabase.db")
        conn.row_factory = sqlite3.Row  # Enable dictionary-like access
        cursor = conn.cursor()

        try:
            # Fetch user's profit, cash balance, and card balance
            cursor.execute("""
                SELECT profit, cash_balance, card_balance 
                FROM users 
                WHERE id = ?
            """, (user_id,))
            user_data = cursor.fetchone()

            if user_data:
                profit = user_data['profit']
                cash_balance = user_data['cash_balance']
                card_balance = user_data['card_balance']
            else:
                profit = cash_balance = card_balance = 0

            # Fetch top five recent transactions
            cursor.execute("""
                SELECT type, category, amount, created_at 
                FROM transactions 
                WHERE user_id = ? 
                ORDER BY created_at DESC 
                LIMIT 5
            """, (user_id,))
            recent_transactions = cursor.fetchall()

            # Generate the welcome message
            welcome_message = generate_welcome_message(username, customer_type)

            # Pass chatbot data to the template
            return render_template(
                'home1.html',
                message=welcome_message,
                profit=profit,
                cash_balance=cash_balance,
                card_balance=card_balance,
                recent_transactions=recent_transactions,
                chatbot_enabled=True  # Enable chatbot on the home page
            )
        except sqlite3.Error as e:
            flash(f"An error occurred while fetching data: {e}", "error")
            return redirect('/error')
        finally:
            cursor.close()
            conn.close()
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

def add_expenses(submitter_name, expense_type, payment_method, category, description, amount, quantity, date):
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

            # Insert expense with user_id and date
            cursor.execute("""
                INSERT INTO transactions (user_id, name, type, account, category, description, amount, quantity, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (user_id, submitter_name, expense_type, payment_method, category, description, total_amount, quantity, date))

            # Update user profit
            cursor.execute("""
                UPDATE users
                SET profit = COALESCE(profit, 0) - ?,
                    total_expenses = COALESCE(total_expenses, 0) + ?
                WHERE id = ?
            """, (total_amount, total_amount, user_id))

            # Update cash or card balance
            if payment_method.lower() == 'cash':
                cursor.execute("""
                    UPDATE users
                    SET cash_balance = COALESCE(cash_balance, 0) - ?
                    WHERE id = ?
                """, (total_amount, user_id))
            elif payment_method.lower() == 'card':
                cursor.execute("""
                    UPDATE users
                    SET card_balance = COALESCE(card_balance, 0) - ?
                    WHERE id = ?
                """, (total_amount, user_id))

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
                flash("User  not logged in. Please log in to add expenses.", "error")
                return redirect('/login')

            expense_type = request.form['expense_type']
            account = request.form['account']
            category = request.form['category']
            description = request.form['description']
            amount = float(request.form['amount'])
            quantity = float(request.form['quantity'])
            date = request.form['date']  # Capture the date from the form

            add_expenses(submitter_name, expense_type, account, category, description, amount, quantity, date)
            update_profit(session.get('user_id'))  # Update user profit

            return redirect('/expenses') # Redirect after successful POST

        except (KeyError, ValueError):
            flash("Please fill in all fields correctly.", "error")
        except Exception as e:
            flash(f"An error occurred: {str(e)}", "error")

    # Handle GET request
    return render_template('expenses.html')  # Ensure this returns a valid response

    # Handle GET request
 
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

def add_income(submitter_name, income_type, payment_method, category, description, amount, quantity, date):
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

            # Insert income with user_id and created_at
            cursor.execute("""
                INSERT INTO transactions (user_id, name, type, account, category, description, amount, quantity, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (user_id, submitter_name, income_type, payment_method, category, description, total_amount, quantity, date))

            # Update user profit
            cursor.execute("""
                UPDATE users
                SET profit = COALESCE(profit, 0) + ?,
                    total_income = COALESCE(total_income, 0) + ?
                WHERE id = ?
            """, (total_amount, total_amount, user_id))

            # Update cash or card balance
            if payment_method.lower() == 'cash':
                cursor.execute("""
                    UPDATE users
                    SET cash_balance = COALESCE(cash_balance, 0) + ?
                    WHERE id = ?
                """, (total_amount, user_id))
            elif payment_method.lower() == 'card':
                cursor.execute("""
                    UPDATE users
                    SET card_balance = COALESCE(card_balance, 0) + ?
                    WHERE id = ?
                """, (total_amount, user_id))

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
                flash("User  not logged in. Please log in to add income.", "error")
                return redirect('/login')

            income_type = request.form['income_type']
            account = request.form['account']
            category = request.form['category']
            description = request.form['description']
            amount = float(request.form['amount'])
            quantity = float(request.form['quantity'])
            date = request.form['date']  # Capture the date from the form

            add_income(submitter_name, income_type, account, category, description, amount, quantity, date)
            update_profit(session.get('user_id'))  # Update user profit

            return redirect('/income')

        except (KeyError, ValueError):
            flash("Please fill in all fields correctly.", "error")
        except Exception as e:
            flash(f"An error occurred: {str(e)}", "error")

    return render_template('income.html')

# Function to calculate total income
def sum_total_income():
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT COALESCE(SUM(amount * quantity), 0) FROM transactions WHERE type='income'")
            return cursor.fetchone()[0]
        except sqlite3.Error as e:
            print(f"Error calculating total income: {e}")
            return 0
        finally:
            cursor.close()
            conn.close()

@app.route('/total_income')
def total_income():
    return render_template('total_income.html', total=sum_total_income())






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

@app.route('/get_profit')
def profit_page():
    """Display the profit for the logged-in user."""
    user_id = session.get('user_id')
    if not user_id:
        flash("Please log in to view profit.", "error")
        return redirect('/login')

    # Update profit before fetching
    update_profit(user_id)

    conn = get_db_connection()
    if conn is None:
        return "Database connection error", 500

    cursor = conn.cursor()
    try:
        # Fetch the updated profit for the logged-in user
        cursor.execute("SELECT COALESCE(profit, 0) FROM users WHERE id = ?", (user_id,))
        result = cursor.fetchone()
        total_profit = float(result[0]) if result else 0  # Convert to float

        return render_template("get_profit.html", total_profit=total_profit)
    except sqlite3.Error as e:
        print(f"Error fetching profit: {e}")
        return "Database error", 500
    finally:
        cursor.close()
        conn.close()
        
        


# Business suggestion function
def suggest_business(capital):
    businesses = {
        "Very Low Budget ($1 - $100)": [
            ("Dropshipping", "video1.mp4"),
            ("Freelance Writing", "writing.mp4"),
            ("Affiliate Marketing", "affiliate.mp4"),
            ("Social Media Management", "smm.mp4"),
            ("Tutoring", "tutoring.mp4"),
            ("Print-on-Demand", "printondemand.mp4"),
            ("Handmade Crafts", "handmade.mp4"),
        ],
        "Low Budget ($100 - $500)": [
            ("Mini Importation", "importation.mp4"),
            ("Local Snacks Business", "snacks.mp4"),
            ("Digital Marketing Agency", "digitalmarketing.mp4"),
            ("Graphic Design Services", "graphicdesign.mp4"),
            ("Car Wash Business", "carwash.mp4"),
            ("Online Course Selling", "onlinecourse.mp4"),
        ],
        "Lower Medium Budget ($500 - $2000)": [
            ("E-commerce Store", "ecommerce.mp4"),
            ("Photography/Videography", "photography.mp4"),
            ("Laundry Business", "laundry.mp4"),
            ("Clothing Brand", "clothing.mp4"),
            ("Barbershop or Salon Business", "barbershop.mp4"),
            ("Food Business", "food.mp4"),
        ],
        "Upper Medium Budget ($2000 - $5000)": [
            ("Small Scale Farming", "farming.mp4"),
            ("Car Rental Service", "carrental.mp4"),
            ("Tech Repairs & Services", "techrepair.mp4"),
            ("Cyber Café or Gaming Center", "gaming.mp4"),
            ("Event Planning & Rentals", "eventplanning.mp4"),
        ],
        "Lower High Budget ($5000 - $10,000)": [
            ("Logistics/Delivery Business", "logistics.mp4"),
            ("Fitness & Gym Center", "gym.mp4"),
            ("Real Estate Investment", "realestate.mp4"),
            ("Printing & Branding Business", "printing.mp4"),
            ("Mini Supermarket", "supermarket.mp4"),
        ],
        "Upper High Budget ($10,000 - $20,000)": [
            ("Import/Export Business", "importexport.mp4"),
            ("Restaurant & Lounge", "restaurant.mp4"),
            ("Auto Dealership", "autodealership.mp4"),
            ("Online Marketplace", "marketplace.mp4"),
            ("Tech Startup", "techstartup.mp4"),
        ],
        "Very High Budget ($20,000+)": [
            ("Large-Scale Real Estate", "largerealestate.mp4"),
            ("Hotel Business", "hotel.mp4"),
            ("Manufacturing", "manufacturing.mp4"),
            ("Automobile Dealership", "automobile.mp4"),
            ("Private School Business", "privateschool.mp4"),
        ],
    }

    if capital < 100:
        category = "Very Low Budget ($1 - $100)"
    elif 100 <= capital < 500:
        category = "Low Budget ($100 - $500)"
    elif 500 <= capital < 2000:
        category = "Lower Medium Budget ($500 - $2000)"
    elif 2000 <= capital < 5000:
        category = "Upper Medium Budget ($2000 - $5000)"
    elif 5000 <= capital < 10000:
        category = "Lower High Budget ($5000 - $10,000)"
    elif 10000 <= capital < 20000:
        category = "Upper High Budget ($10,000 - $20,000)"
    else:
        category = "Very High Budget ($20,000+)"

    return category, businesses[category]

@app.route("/Business_advice", methods=["GET", "POST"])
def Business_advice():
    if request.method == "POST":
        capital_input = request.form.get("capital")  # Use get to avoid KeyError
        if capital_input:
            try:
                capital = float(capital_input)
                if capital < 0:
                    return render_template("Business_advice.html", error="Capital cannot be negative.")
                
                category, suggestions = suggest_business(capital)
                return render_template("result.html", category=category, suggestions=suggestions)
            except ValueError:
                return render_template("Business_advice.html", error="Please enter a valid amount.")
        else:
            return render_template("Business_advice.html", error="Please enter a capital amount.")

    return render_template("Business_advice.html")

@app.route('/ana')
def ana():
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized access"}), 401

    user_id = session['user_id']
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Fetch user details
        cursor.execute("SELECT username, cash_balance, card_balance FROM users WHERE id = ?", (user_id,))
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

        # Fetch expenses
        cursor.execute("""
            SELECT category, SUM(amount) AS total_amount
            FROM transactions
            WHERE type = 'expense' AND user_id = ?
            GROUP BY category
        """, (user_id,))
        expenses = cursor.fetchall()

        # Fetch income
        cursor.execute("""
            SELECT category, SUM(amount) AS total_amount
            FROM transactions
            WHERE type = 'income' AND user_id = ?
            GROUP BY category
        """, (user_id,))
        income = cursor.fetchall()

        # Fetch income trends
        cursor.execute("""
            SELECT strftime('%Y-%m-%d', created_at) AS date, SUM(amount) AS total_amount
            FROM transactions
            WHERE type = 'income' AND user_id = ?
            GROUP BY date
            ORDER BY date
        """, (user_id,))
        income_trends = cursor.fetchall()

        # Fetch expense trends
        cursor.execute("""
            SELECT strftime('%Y-%m-%d', created_at) AS date, SUM(amount) AS total_amount
            FROM transactions
            WHERE type = 'expense' AND user_id = ?
            GROUP BY date
            ORDER BY date
        """, (user_id,))
        expense_trends = cursor.fetchall()

        # Prepare data for rendering
        expense_data = [{"category": row['category'], "amount": row['total_amount']} for row in expenses]
        income_data = [{"category": row['category'], "amount": row['total_amount']} for row in income]
        income_trend_data = [{"date": row['date'], "total_amount": row['total_amount']} for row in income_trends]
        expense_trend_data = [{"date": row['date'], "total_amount": row['total_amount']} for row in expense_trends]

        # Render the overview template with all data
        return render_template('ana.html', 
                               username=username,
                               cash_balance=cash_balance,
                               card_balance=card_balance,
                               total_income=total_income,
                               total_expenses=total_expenses,
                               expenses=expense_data,
                               income=income_data,
                               income_trends=income_trend_data,
                               expense_trends=expense_trend_data)
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return jsonify({"error": "Database error"}), 500

@app.route('/Analysis')
def Analysis():
    return render_template('Analysis.html')

@app.route('/IncomeOverview')  
def income_flow():
    return render_template('IncomeOverview.html')

@app.route('/ExpenseOverview')
def expense_flow(): 
    return render_template("ExpenseOverview.html")

@app.route('/income_trends', methods=['GET'])
def income_trends():
    return render_template('income_trends.html')

@app.route('/expenses_trends', methods=['GET'])
def expenses_trends():  
    return render_template('expenses_trends.html')

@app.route('/general_analysis', methods=['GET'])
def general_analysis():
    return render_template('general_analysis.html')


def check_column_exists(table_name, column_name):
    """Check if a column exists in a given SQLite table."""
    conn = sqlite3.connect("mydatabase.db")
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = [col[1] for col in cursor.fetchall()]
    conn.close()
    return column_name in columns

@app.route('/api/user_financials', methods=['GET'])
def fetch_user_financials():
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized access"}), 401

    user_id = session['user_id']
    
    try:
        with sqlite3.connect("mydatabase.db") as conn:
            cursor = conn.cursor()
            
            # Fetch user details
            cursor.execute("SELECT username, cash_balance, card_balance FROM users WHERE id = ?", (user_id,))
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
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized access"}), 401

    user_id = session['user_id']
    conn = sqlite3.connect("mydatabase.db")
    cursor = conn.cursor()

    date_filter = request.args.get('month')  # e.g., '2025-03'
    
    # Check if 'quantity' column exists
    has_quantity = check_column_exists("transactions", "quantity")
    sum_expression = "SUM(amount * quantity)" if has_quantity else "SUM(amount)"

    query = f"""
        SELECT category, {sum_expression} AS total_amount
        FROM transactions
        WHERE type = 'expense' AND user_id = ?
    """
    params = [user_id]

    if date_filter:
        query += " AND strftime('%Y-%m', created_at) = ?"
        params.append(date_filter)

    query += " GROUP BY category"

    print("Executing SQL:", query)
    print("With parameters:", params)

    cursor.execute(query, params)
    rows = cursor.fetchall()
    
    data = [{"category": row[0], "amount": row[1]} for row in rows]
    conn.close()
    return jsonify(data)


@app.route('/api/income', methods=['GET'])
def fetch_income():
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized access"}), 401

    user_id = session['user_id']
    conn = sqlite3.connect("mydatabase.db")
    cursor = conn.cursor()

    date_filter = request.args.get('month')  # e.g., '2025-03'
    
    # Check if 'quantity' column exists
    has_quantity = check_column_exists("transactions", "quantity")
    sum_expression = "SUM(amount * quantity)" if has_quantity else "SUM(amount)"

    query = f"""
        SELECT category, {sum_expression} AS total_amount
        FROM transactions
        WHERE type = 'income' AND user_id = ?
    """
    params = [user_id]

    if date_filter:
        query += " AND strftime('%Y-%m', created_at) = ?"
        params.append(date_filter)

    query += " GROUP BY category"

    print("Executing SQL:", query)
    print("With parameters:", params)

    cursor.execute(query, params)
    rows = cursor.fetchall()
    
    data = [{"category": row[0], "amount": row[1]} for row in rows]
    conn.close()
    return jsonify(data)




@app.route('/api/income_trends', methods=['GET'])
def fetch_income_trends():
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized access"}), 401

    user_id = session['user_id']
    
    try:
        with sqlite3.connect("mydatabase.db") as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT strftime('%Y-%m-%d', created_at) AS date, SUM(amount) AS total_amount
                FROM transactions
                WHERE type = 'income' AND user_id = ?
                GROUP BY date
                ORDER BY date
            """, (user_id,))
            rows = cursor.fetchall()
            
            data = [{"date": row[0], "total_amount": row[1]} for row in rows]
            return jsonify(data)
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return jsonify({"error": "Database error"}), 500

@app.route('/api/income_details', methods=['GET'])
def fetch_income_details():
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized access"}), 401

    user_id = session['user_id']
    
    try:
        with sqlite3.connect("mydatabase.db") as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT created_at, category, amount
                FROM transactions
                WHERE type = 'income' AND user_id = ?
                ORDER BY created_at
            """, (user_id,))
            rows = cursor.fetchall()
            
            # Create a list of dictionaries for each income record
            data = [{"created_at": row[0], "category": row[1], "amount": row[2]} for row in rows]
            return jsonify(data)
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return jsonify({"error": "Database error"}), 500

@app.route('/api/expenses_details', methods=['GET'])
def fetch_expense_details():
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized access"}), 401

    user_id = session['user_id']
    
    try:
        with sqlite3.connect("mydatabase.db") as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT created_at, category, amount
                FROM transactions
                WHERE type = 'expense' AND user_id = ?
                ORDER BY created_at
            """, (user_id,))
            rows = cursor.fetchall()
            
            # Create a list of dictionaries for each income record
            data = [{"created_at": row[0], "category": row[1], "amount": row[2]} for row in rows]
            return jsonify(data)
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return jsonify({"error": "Database error"}), 500
@app.route('/api/expenses_trends', methods=['GET'])
def fetch_expense_trends():
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized access"}), 401

    user_id = session['user_id']
    conn = sqlite3.connect("mydatabase.db")
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT strftime('%Y-%m-%d', created_at) AS date, SUM(amount) AS total_amount
            FROM transactions
            WHERE type = 'expense' AND user_id = ?
            GROUP BY date
            ORDER BY date
        """, (user_id,))
        rows = cursor.fetchall()
        
        data = [{"date": row[0], "total_amount": row[1]} for row in rows]
        return jsonify(data)
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return jsonify({"error": "Database error"}), 500
    finally:
        cursor.close()
        conn.close() 

# In-memory storage for posts


#Create folder if it doesn't exist

# In-memory storage for posts

def connect_db():
    return sqlite3.connect('mydatabase.db')


UPLOAD_FOLDER_IMG = r"C:\Users\USER 22\Projecttime\Fincom\static\img"
UPLOAD_FOLDER_VIDEO = r"C:\Users\USER 22\Projecttime\Fincom\static\video"


ALLOWED_VIDEO_EXTENSIONS = {'mp4', 'avi', 'mov', 'wmv'}  # Allowed video formats

posts = []



# Ensure directories exist
os.makedirs(UPLOAD_FOLDER_IMG, exist_ok=True)
os.makedirs(UPLOAD_FOLDER_VIDEO, exist_ok=True)

# Function to connect to the database

@app.route('/post', methods=['POST'])
def post():
    if 'username' not in session:
        return redirect(url_for('login'))

    username = session['username']
    title = request.form.get('title', '').strip()
    content = request.form.get('content', '').strip()
    media = request.files.get('media')

    media_filename = None
    media_type = None
    timestamp = datetime.now(timezone.utc)

    if media and media.filename:
        file_ext = media.filename.rsplit('.', 1)[-1].lower()
        safe_filename = secure_filename(media.filename)

        if file_ext in ['jpg', 'jpeg', 'png', 'gif']:
            media_type = "image"
            save_path = os.path.join(UPLOAD_FOLDER_IMG, safe_filename)
        elif file_ext in ['mp4', 'avi', 'mov', 'mkv']:
            media_type = "video"
            save_path = os.path.join(UPLOAD_FOLDER_VIDEO, safe_filename)
        else:
            return "Invalid file format", 400

        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        media.save(save_path)
        media_filename = safe_filename

    # Save post to the database
    conn = connect_db()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO posts (username, title, content, media_filename, media_type, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (username, title, content, media_filename, media_type, timestamp))

        conn.commit()
    except sqlite3.Error as e:
        print("Database error:", e)
        return "An error occurred while saving your post.", 500
    finally:
        conn.close()

    return redirect(url_for('community'))

def connect_db():
    return sqlite3.connect('mydatabase.db')

@app.route('/respond/<int:post_id>', methods=['POST'])
def respond(post_id):
    if 'username' not in session:
        return redirect(url_for('login'))

    response_content = request.form.get('response')
    username = session['username']

    conn = connect_db()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO responses (post_id, username, content, timestamp)
            VALUES (?, ?, ?, ?)
        ''', (post_id, username, response_content, datetime.now()))
        conn.commit()
    except sqlite3.Error as e:
        print("Database error:", e)
        return "An error occurred while saving your response.", 500
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for('community'))


@app.route('/community', methods=['GET'])
def community():
    conn = connect_db()
    conn.row_factory = sqlite3.Row  # Rows act like dictionaries
    cursor = conn.cursor()
    
    # Get the search query from the request arguments
    search_query = request.args.get('search', '').strip()

    # Fetch posts and their associated responses
    cursor.execute('''
        SELECT p.*, r.username AS response_username, r.content AS response_content, r.timestamp AS response_timestamp
        FROM posts p
        LEFT JOIN responses r ON p.id = r.post_id
        ORDER BY p.timestamp DESC
    ''')
    
    rows = cursor.fetchall()
    
    # Convert the timestamp string to a datetime object for formatting in the template.
    posts = {}
    for row in rows:
        post_id = row['id']
        
        # Create a new post entry if it doesn't exist
        if post_id not in posts:
            post = dict(row)
            try:
                # Convert the timestamp to a datetime object
                post['timestamp'] = datetime.datetime.strptime(post['timestamp'], '%Y-%m-%d %H:%M:%S')
            except Exception as e:
                print("Timestamp conversion error:", e)
            post['responses'] = []  # Initialize responses list
            posts[post_id] = post
        
        # If there is a response, add it to the post's responses
        if row['response_username'] is not None:
            response = {
                'username': row['response_username'],
                'content': row['response_content'],
                'timestamp': row['response_timestamp']
            }
            posts[post_id]['responses'].append(response)

    # Convert posts dictionary back to a list
    posts = list(posts.values())

    # Filter posts based on the search query
    if search_query:
        posts = [
            post for post in posts
            if search_query.lower() in post['content'].lower() or
               search_query.lower() in post['username'].lower() or
               search_query.lower() in post['title'].lower()
        ]

    conn.close()
    return render_template('community.html', posts=posts, search_query=search_query)

def get_db_connection():
    conn = sqlite3.connect('mydatabase.db')
    conn.row_factory = sqlite3.Row  # This allows us to access columns by name
    return conn

@app.route('/chatbox', methods=['GET'])
def chatbox():
    search_query = request.args.get('search', '').strip()  # Get search query from URL
    profession_query = request.args.get('profession', '').strip()  # Get profession query from URL
    conn = get_db_connection()

    # Build the SQL query dynamically based on search inputs
    query = "SELECT * FROM users WHERE 1=1"
    params = []

    if search_query:
        query += " AND username LIKE ?"
        params.append(f'%{search_query}%')

    if profession_query:
        query += " AND profession LIKE ?"
        params.append(f'%{profession_query}%')

    # Retrieve users based on the query
    users = conn.execute(query, params).fetchall()

    # Convert sqlite3.Row objects to dictionaries and add online status
    users = [dict(user) for user in users]
    for user in users:
        user['online'] = user['id'] % 2 == 0  # Example: Even IDs are online

    # Simulate the active user (replace with actual logic)
    active_user = {'username': 'JohnDoe', 'id': 1}

    conn.close()
    return render_template('chatbox.html', users=users, search_query=search_query, profession_query=profession_query, active_user=active_user)


# Initialize the Generative AI model
genai.configure(api_key="AIzaSyByWhip1y1g6VuCnCq0avs2QrabdAk3z68")  # Replace with your actual API key
model = genai.GenerativeModel("gemini-1.5-flash")  # Replace with the correct model name



def generate_response(prompt):
    # Prepend context about FinCom and finance
    context = "You are FinBot, a financial assistant for FinCom. You can provide financial insights and also engage in general conversation. Please provide concise and relevant responses to user queries."
    
    # Check if the user is logged in
    if 'user_id' not in session:
        return "Please log in to use FinBot's services."

    user_id = session['user_id']  # Get the logged-in user's ID

    # Keywords to trigger financial information retrieval and analysis
    keywords = ["financial summary", "financial information", "my finances", "income", "expenses", "profit", "balance", "business", "analysis", "breakdown", "insights"]

    # Check if the user's prompt contains any of the keywords
    if any(keyword in prompt.lower() for keyword in keywords):
        # Connect to the database and retrieve user-specific data
        conn = sqlite3.connect("mydatabase.db")
        conn.row_factory = sqlite3.Row  # Access columns by name
        cursor = conn.cursor()
        
        try:
            # Fetch data for the logged-in user
            cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
            user = cursor.fetchone()
            
            if user:
                # Format user data into a brief summary
                user_data = f":User  {user['fullname']} (Username: {user['username']})\n" \
                            f"Profit: {user['profit']}, Income: {user['total_income']}, Expenses: {user['total_expenses']}\n" \
                            f"Cash Balance: {user['cash_balance']}, Card Balance: {user['card_balance']}, Savings: {user['savings_balance']}"
                
                context += f"\nHere is your financial summary:\n{user_data}\n"
                
                # Perform financial analysis and insights
                analysis = perform_financial_analysis(user)
                context += f"\nFinancial Analysis:\n{analysis}\n"
            else:
                context += "\nNo financial data found for your account.\n"
        except sqlite3.Error as e:
            print(f"Database error: {e}")
            context += "\nUnable to retrieve financial data due to a database error.\n"
        finally:
            cursor.close()
            conn.close()
    else:
        # If no keywords are detected, provide a general chat response
        context += "\nHow can I assist you today? Feel free to ask me anything, whether it's about finances or general topics."

    # Combine the context with the user's prompt
    full_prompt = context + "\n" + prompt
    
    # Generate a response using the AI model
    response = model.generate_content(full_prompt)
    
    # Limit the response length to keep it concise
    return response.text[:500]

def perform_financial_analysis(user):
    # This function will perform various analyses based on user data
    analysis = []
    
    # Example calculations
    income = user['total_income']
    expenses = user['total_expenses']
    profit = user['profit']
    cash_balance = user['cash_balance']
    
    # Profit margin
    if income > 0:
        profit_margin = (profit / income) * 100
        analysis.append(f"Profit Margin: {profit_margin:.2f}%")
    else:
        analysis.append("No income recorded to calculate profit margin.")
    
    # Expense ratio
    if income > 0:
        expense_ratio = (expenses / income) * 100
        analysis.append(f"Expense Ratio: {expense_ratio:.2f}%")
    else:
        analysis.append("No income recorded to calculate expense ratio.")
    
    # Cash flow insights
    if cash_balance < 0:
        analysis.append("Warning: Your cash balance is negative. Consider reviewing your expenses.")
    else:
        analysis.append("Your cash balance is healthy.")
    
    # Add more analyses as needed
    return "\n".join(analysis)
    
def fetch_regional_trends(user_id):
    # Example: Fetch regional trends from an external API or database
    trends = [
        "Fuel prices have increased by 5% this week.",
        "Electricity tariffs are expected to rise by 10% next month.",
        "Local food prices have stabilized after recent fluctuations."
    ]
    return "Here are the latest regional economic trends:\n" + "\n".join(trends)

def fetch_bill_negotiation_tips(user_id):
    tips = [
        "1. Contact your service provider and request a payment plan for overdue bills.",
        "2. Ask for discounts or promotions on your current subscription.",
        "3. Highlight your loyalty as a long-term customer to negotiate better terms."
    ]
    return "Here are some tips for renegotiating your bills:\n" + "\n".join(tips)

def fetch_better_deals(user_id):
    conn = sqlite3.connect("mydatabase.db")
    cursor = conn.cursor()

    try:
        # Fetch top recurring expenses
        cursor.execute("""
            SELECT category, SUM(amount) AS total_spent
            FROM transactions
            WHERE user_id = ? AND type = 'expense'
            GROUP BY category
            ORDER BY total_spent DESC
            LIMIT 5
        """, (user_id,))
        expenses = cursor.fetchall()

        # Suggest alternatives for the top expenses
        suggestions = []
        for category, total_spent in expenses:
            suggestions.append(f"For {category}, consider switching to a more affordable option.")

        return "Here are some suggestions for finding better deals:\n" + "\n".join(suggestions)
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return "Sorry, I couldn't fetch better deal suggestions."
    finally:
        cursor.close()
        conn.close()
def fetch_investment_opportunities(user_id):
    conn = sqlite3.connect("mydatabase.db")
    cursor = conn.cursor()

    try:
        # Fetch user's savings balance
        cursor.execute("SELECT savings_balance FROM users WHERE id = ?", (user_id,))
        user = cursor.fetchone()
        savings = user[0] if user else 0

        # Suggest investments based on savings
        if savings < 1000:
            return "Consider low-risk investments like treasury bills or fixed deposits."
        elif savings < 5000:
            return "You can explore mutual funds or high-interest savings accounts."
        else:
            return "With your savings, you can consider real estate or tech stocks for higher returns."
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return "Sorry, I couldn't fetch investment suggestions."
    finally:
        cursor.close()
        conn.close()
        
def fetch_expense_reduction_tips(user_id):
    conn = sqlite3.connect("mydatabase.db")
    cursor = conn.cursor()

    try:
        # Fetch user's top expenses
        cursor.execute("""
            SELECT category, SUM(amount) AS total_spent
            FROM transactions
            WHERE user_id = ? AND type = 'expense'
            GROUP BY category
            ORDER BY total_spent DESC
            LIMIT 3
        """, (user_id,))
        expenses = cursor.fetchall()

        # Suggest alternatives for costly habits
        suggestions = []
        for category, total_spent in expenses:
            suggestions.append(f"Consider switching from {category} to a more affordable alternative.")

        return "Here are some expense reduction insights:\n" + "\n".join(suggestions)
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return "Sorry, I couldn't fetch expense reduction insights."
    finally:
        cursor.close()
        conn.close()
@app.route('/generate', methods=['POST'])
def generate():
    """
    API endpoint to handle chatbot requests and generate responses.
    """
    try:
        data = request.get_json()  # Parse JSON data from the request
        if not data or 'user_input' not in data:
            return jsonify({'error': 'user_input is required'}), 400

        user_input = data['user_input']
        print(f"Received user input: {user_input}")  # Debugging log

        # Generate a response
        response = generate_response(user_input)
        print(f"Generated response: {response}")  # Debugging log

        return jsonify({'response': response})
    except Exception as e:
        print(f"Error in /generate route: {e}")
        return jsonify({'error': 'Internal server error'}), 500
@app.route('/chatbot')
def chatbot():
    return render_template('chatbot.html')



def get_db_connection():
    conn = sqlite3.connect('mydatabase.db')
    conn.row_factory = sqlite3.Row  # This allows us to access columns by name
    return conn








@app.route('/chatroom/<username>')
def chatroom(username):
    return render_template('chatroom.html', username=username)

@socketio.on('send_message')
def handle_send_message(data):
    print("Message received:", data['message'])  # Log the received message
    emit('receive_message', data, broadcast=True)
def connect_db():
    return sqlite3.connect('mydatabase.db')
@app.route('/budget', methods=['GET', 'POST'])
def budget():
    print("Budget route accessed")  # Debugging line
    if request.method == 'POST':
        if 'user_id' not in session:
            flash("You need to log in first!", "error")
            return redirect('/login')

        user_id = session['user_id']
        category = request.form['category']
        amount = request.form['amount']

        # Save the budget to the database
        conn = connect_db()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO budgets (user_id, category, amount)
                VALUES (?, ?, ?)
            ''', (user_id, category, amount))
            conn.commit()
            flash("Budget set successfully!", "success")
        except sqlite3.Error as e:
            print("Database error:", e)
            flash("An error occurred while setting your budget.", "error")
        finally:
            cursor.close()
            conn.close()

        return redirect('/budget')

    # GET request: fetch and display budgets
    if 'user_id' not in session:
        flash("You need to log in first!", "error")
        return redirect('/login')

    user_id = session['user_id']
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM budgets WHERE user_id = ?", (user_id,))
    budgets = cursor.fetchall()
    cursor.close()
    conn.close()

    return render_template('budget.html', budgets=budgets)

@app.route('/update_budget/<int:budget_id>', methods=['POST'])
def update_budget(budget_id):
    update_amount = request.form.get('update_amount', type=float)
    
    # Fetch the current budget from the database
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT amount FROM budgets WHERE id = ?", (budget_id,))
    budget = cursor.fetchone()

    if budget:
        current_amount = budget[0]
        new_budget_amount = current_amount - update_amount  # Adjust as needed
        cursor.execute("UPDATE budgets SET amount = ? WHERE id = ?", (new_budget_amount, budget_id))
        conn.commit()
        flash('Budget updated successfully!', 'success')
    else:
        flash('Budget not found!', 'error')
    
    cursor.close()
    conn.close()
    return redirect(url_for('budget'))


@app.route('/chatbot_transaction', methods=['POST'])
def chatbot_transaction():
    if 'username' not in session:
        return jsonify({"error": "Unauthorized access"}), 401

    user_id = session['user_id']
    user_input = request.form.get('user_input', '')

    # Parse the transaction input
    amount, category, transaction_type, payment_method = parse_transaction_input(user_input)

    if amount is None or category is None or transaction_type is None:
        return jsonify({"error": "Invalid input format. Please specify the amount and category."}), 400

    # Add the transaction to the database
    if transaction_type == 'expense':
        add_expenses(session['username'], transaction_type, payment_method, category, '', amount, 1)
    elif transaction_type == 'income':
        add_income(session['username'], transaction_type, payment_method, category, '', amount, 1)

    return jsonify({"success": f"{transaction_type.capitalize()} of ${amount} added under category '{category}' using {payment_method}."})

def parse_transaction_input(input_string):
    """Parse the transaction input string to extract amount, category, and transaction type."""
    user_input = request.form.get('user_input', '')
    # Regular expression to find the amount
    amount_match = re.search(r'\$?(\d+(\.\d{1,2})?)', input_string)
    
    if amount_match:
        amount = float(amount_match.group(1))  # Extract the amount
    else:
        return None, None, None  # Return None if no amount is found

     # determine transaction type 
    input_string = input_string.lower()
    if 'spent' in input_string or 'expense' in input_string or 'from' in input_string:
        transaction_type = 'expense'
    elif 'gained' in input_string or 'earned' in input_string or 'through' in input_string:
        transaction_type = 'income'
 # simple keyword-based for category 
    categories = ['food', 'transport', 'shopping', 'bills', 'salary', 'investment']
    category = None
    for cat in categories:
        if cat in input_string:
            category = cat
            break
    if not category:
        category = 'other'  # Default if no known category found
 # Define payment methods
    payment_methods = {
    'cash': 'Cash',
    'card': 'Card',
    'credit': 'Card',
    'debit': 'Card'
}
    #check for payement method 
    payment_method = payment_methods.get(input_string, 'None')
    if 'cash' in input_string or 'card' in input_string:
        payment_method = 'Card' if 'card' in input_string else 'Cash'
    elif 'credit' in input_string or 'debit' in input_string:
        payment_method = 'Card'
    else:
        payment_method = "None"  # Return None if no payment method is found
    
    return amount, category, transaction_type, payment_method

    
    # This regex captures everything after the amount and any keywords
    category_match = re.split(r'\$?\d+(\.\d{1,2})?|\b(spent|gained|earned|from|through|on|as)\b', input_string, flags=re.IGNORECASE)
    
    if len(category_match) > 1:
        # Get the text after the amount and keywords, and clean it up
        category = category_match[-1].strip()  # Get the last part after the split
        if category:  # Check if category is not empty
            return amount, category, transaction_type, payment_method
        else:
            return None, None, None, None  # Return None if category is empty
    else:
        return None, None, None, None  # Return None if no category is found # Return None if no category is found


# Serializer for generating secure tokens
serializer = URLSafeTimedSerializer(app.secret_key)


    

@app.route('/send-query', methods=['POST'])
def send_query():
    name = request.form['name']
    user_email = request.form['email']
    query = request.form['query']
    topic = request.form['topic']

    # Email content
    subject = f"Query from {name} - Topic: {topic}"
    body = f"Name: {name}\nEmail: {user_email}\n\nQuery:\n{query}"

    # Email configuration
    sender_email = "projectfinodido@gmail.com"  # Your email
    sender_password = "csqv yavo jcwj bghz"  # Use the generated app password
    recipient_email = "projectfinodido@gmail.com"  # Recipient email# Replace with the recipient email

    # Create the email
    message = MIMEMultipart()
    message['From'] = sender_email
    message['To'] = recipient_email
    message['Subject'] = subject
    message.attach(MIMEText(body, 'plain'))

    try:
        # Connect to the Gmail SMTP server
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()  # Start TLS encryption
            server.login(sender_email, sender_password)  # Log in to the SMTP server
            server.sendmail(sender_email, recipient_email, message.as_string())  # Send the email
        flash("Query sent successfully!", "success")  # Flash success message
    except Exception as e:
        flash(f"Failed to send query: {e}", "error")  # Flash error message

    return redirect(url_for('index'))  # Redirect back to the contact page


def get_db_connection():
    conn = sqlite3.connect('mydatabase.db')
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/all_transactions')
def all_transactions():
    if 'username' not in session:
        return redirect(url_for('login'))  # Redirect to login if not logged in

    username = session['username']
    conn = get_db_connection()
    
    # Fetch transactions for the logged-in user
    transactions = conn.execute('SELECT type, category, amount, created_at FROM transactions WHERE name = ?', (username,)).fetchall()
    conn.close()
    
    # Debugging: Print the transactions to see their structure
    print(transactions)  # This will show you the structure of the data

    # Add a numbering column to the transactions
    transactions_with_numbering = []
    for i, transaction in enumerate(transactions):
        try:
            # Accessing by key if using sqlite3.Row
            transactions_with_numbering.append((
                i + 1, 
                transaction['type'], 
                transaction['category'], 
                transaction['amount'], 
                transaction['created_at']
            ))
        except KeyError as e:
            print(f"KeyError: {e} - Transaction: {transaction}")  # Print the error and the transaction causing it

    return render_template('all_transactions.html', transactions=transactions_with_numbering)

@app.route('/export/csv', methods=['GET'])
def export_csv():
    if 'username' not in session:
        return redirect(url_for('login'))

    username = session['username']
    conn = get_db_connection()
    transactions = pd.read_sql_query('SELECT * FROM transactions WHERE name = ?', conn, params=(username,))
    conn.close()

    # Add a numbering column to the DataFrame
    transactions['Number'] = range(1, len(transactions) + 1)
    transactions = transactions[['type', 'category', 'amount', 'created_at']]  # Reorder columns

    # Use a temporary file to save the CSV
    with tempfile.NamedTemporaryFile(delete=False, suffix='.csv') as tmp_file:
        csv_file = tmp_file.name
        transactions.to_csv(csv_file, index=False)

    # Check if the file was created successfully
    if not os.path.exists(csv_file):
        return "Error: File not created", 500

    return send_file(csv_file, as_attachment=True)

@app.route('/export/excel', methods=['GET'])
def export_excel():
    if 'username' not in session:
        return redirect(url_for('login'))

    username = session['username']
    conn = get_db_connection()
    transactions = pd.read_sql_query('SELECT * FROM transactions WHERE name = ?', conn, params=(username,))
    conn.close()

    # Add a numbering column to the DataFrame
    transactions['Number'] = range(1, len(transactions) + 1)
    transactions = transactions[['Number', 'type', 'category', 'amount', 'created_at']]  # Reorder columns

    # Use a temporary file to save the Excel file
    with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp_file:
        excel_file = tmp_file.name
        transactions.to_excel(excel_file, index=False)

    # Check if the file was created successfully
    if not os.path.exists(excel_file):
        return "Error: File not created", 500

    return send_file(excel_file, as_attachment=True)

@app.route('/logout')
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    
    return redirect('/login')


if __name__ == '__main__':
   socketio.run(app, host='0.0.0.0', port=5000, debug=True)