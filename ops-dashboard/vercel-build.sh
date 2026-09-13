#!/bin/bash
# Vercel build script for Python Flask app
echo "🚀 Starting Vercel build for Autonomous Email Inbox..."

# Install dependencies
echo "📦 Installing Python dependencies..."
pip install -r requirements.txt

# Verify installation
echo "✅ Dependencies installed successfully"
echo "📋 Installed packages:"
pip list

echo "🎉 Build completed successfully!"
