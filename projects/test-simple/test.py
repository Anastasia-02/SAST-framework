import os
import subprocess
import sqlite3

# Hardcoded password - CWE-798
password = "admin123"

# SQL injection - CWE-89
def get_user(user_id):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    query = "SELECT * FROM users WHERE id = " + user_id  # SQL injection!
    cursor.execute(query)
    return cursor.fetchall()

# Command injection - CWE-78
def run_backup():
    user_input = input("Enter backup command: ")
    os.system("backup " + user_input)  # Command injection!

# Weak cryptographic algorithm - CWE-327
import hashlib
def hash_password(password):
    return hashlib.md5(password.encode()).hexdigest()  # Weak MD5

# Hardcoded API key - CWE-798
API_KEY = "sk_live_1234567890abcdef"