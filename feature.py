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