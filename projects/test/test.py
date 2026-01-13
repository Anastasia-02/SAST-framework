
# Test file for SAST scanning
import os

def insecure_function(password):
    # Hardcoded password - security issue
    secret = "password123"
    return password == secret

def sql_injection(user_input):
    # SQL injection vulnerability
    query = "SELECT * FROM users WHERE id = " + user_input
    return query

# Command injection vulnerability
def run_command(cmd):
    os.system(cmd)
