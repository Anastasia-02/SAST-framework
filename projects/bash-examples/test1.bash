#!/bin/bash

# Shell injection vulnerability
read -p "Enter filename: " filename
cat $filename

# Command injection
read -p "Enter command: " cmd
eval $cmd

# Password in script
PASSWORD="secret123"
echo "Password: $PASSWORD"