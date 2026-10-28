#!/bin/bash
# Backend: install dependencies and run dev server

set -e

echo "=== Setting up FastAPI backend ==="

cd backend

# Create virtual environment if not exists
if [ ! -d "venv" ]; then
  python -m venv venv
fi

# Activate
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate  # Windows (uncomment for PowerShell)

# Install dependencies
pip install -r requirements.txt

echo ""
echo "=== Backend ready. Copy .env.example to .env and fill in credentials. ==="
echo "=== Then run: uvicorn app.main:app --reload ==="
