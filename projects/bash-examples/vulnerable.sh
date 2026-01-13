#!/bin/bash

# Command injection vulnerability
read -p "Enter filename: " filename
cat $filename  # Shell injection if filename contains commands

# Unsafe use of eval
read -p "Enter expression: " expr
eval "result=$expr"  # Dangerous!

# Password in script
PASSWORD="mysecretpassword123"
echo "Password is: $PASSWORD"

# Unsafe temporary file
TMPFILE="/tmp/tempfile"
echo "data" > $TMPFILE
cat $TMPFILE
# No cleanup

# World-writable file
touch /tmp/world_writable.txt
chmod 777 /tmp/world_writable.txt

# Using uninitialized variable
echo "Value: $UNINITIALIZED_VAR"
