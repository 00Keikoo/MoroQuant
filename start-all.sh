#!/bin/bash
# MoroQuant - Start All Services
# Launches ML backend and Next.js frontend together

echo "🚀 Starting MoroQuant Platform..."
echo ""

# Check if we're in the right directory
if [ ! -d "ml_service" ] || [ ! -f "package.json" ]; then
    echo "❌ Error: Must run from project root directory (~/trade-dashboard)"
    exit 1
fi

# Check if Python venv exists
if [ ! -d "ml_service/venv" ]; then
    echo "⚠️  Python virtual environment not found"
    echo "   Creating venv..."
    cd ml_service
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    cd ..
    echo "   ✓ Virtual environment created"
fi

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo "⚠️  Node modules not found"
    echo "   Installing dependencies..."
    npm install
    echo "   ✓ Dependencies installed"
fi

# Check if config.yaml exists
if [ ! -f "ml_service/config.yaml" ]; then
    echo "⚠️  config.yaml not found"
    echo "   Please create ml_service/config.yaml from config.example.yaml"
    echo "   cp ml_service/config.example.yaml ml_service/config.yaml"
    echo "   Then edit with your API keys"
    exit 1
fi

echo "📊 Starting ML Backend (FastAPI)..."
cd ml_service
./start.sh &
ML_PID=$!
cd ..

# Wait for ML service to be ready
echo "⏳ Waiting for ML service to initialize..."
sleep 5

# Check if ML service is running
if ! curl -s http://127.0.0.1:8000/db/info > /dev/null 2>&1; then
    echo "⚠️  ML service may not be ready yet, continuing anyway..."
fi

echo "🌐 Starting Next.js Frontend..."
npm run dev &
NEXT_PID=$!

echo ""
echo "✓ Services started!"
echo ""
echo "📍 URLs:"
echo "   Frontend:  http://localhost:3000"
echo "   ML API:    http://127.0.0.1:8000"
echo "   API Docs:  http://127.0.0.1:8000/docs"
echo ""
echo "💡 Tips:"
echo "   • Fetch data: cd ml_service && python cli.py fetch --all --days 730"
echo "   • Train models: python cli.py train --symbol BTCUSDT --timeframe 1h"
echo "   • View logs: tail -f ml_service/storage/logs/*.log"
echo ""
echo "🛑 To stop: Press Ctrl+C or run:"
echo "   kill $ML_PID $NEXT_PID"
echo ""

# Keep script running and handle Ctrl+C
trap "echo ''; echo '🛑 Stopping services...'; kill $ML_PID $NEXT_PID 2>/dev/null; exit 0" INT

# Wait for processes
wait
