#!/bin/bash
# Startup script for the document editing agent backend

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
elif [ -d "env" ]; then
    source env/bin/activate
fi

# Run the server
python main.py

