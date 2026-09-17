#!/usr/bin/env bash
# Quick start script for The Judge

set -e

echo "🔍 The Judge - Quick Start"
echo "=========================="
echo ""

# Check if Python is installed
if ! command -v python &> /dev/null && ! command -v python3 &> /dev/null; then
    echo "❌ Python is not installed. Please install Python 3.9 or higher."
    exit 1
fi

PYTHON_CMD="python3"
if ! command -v python3 &> /dev/null; then
    PYTHON_CMD="python"
fi

echo "✓ Found Python: $($PYTHON_CMD --version)"
echo ""

# Check if in virtual environment
if [ -z "$VIRTUAL_ENV" ]; then
    echo "⚠️  Not in a virtual environment. Creating one..."
    $PYTHON_CMD -m venv .venv

    if [ -f ".venv/bin/activate" ]; then
        source .venv/bin/activate
    elif [ -f ".venv/Scripts/activate" ]; then
        source .venv/Scripts/activate
    fi

    echo "✓ Virtual environment created and activated"
    echo ""
fi

# Install the package
echo "📦 Installing The Judge..."
pip install -e ".[dev]" -q
echo "✓ The Judge installed"
echo ""

# Run a quick test
echo "🧪 Running quick verification..."
judge --version
echo ""

# Show next steps
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "  1. Run demo:       judge demo"
echo "  2. Verify code:    judge verify ."
echo "  3. Improve code:   judge improve ."
echo "  4. See help:       judge --help"
echo ""
echo "Documentation:"
echo "  • Quick Start:     docs/QUICK_START.md"
echo "  • API Reference:   docs/API.md"
echo "  • Integration:     PLUGIN_GUIDE.md"
echo ""
echo "Happy coding! 🚀"
