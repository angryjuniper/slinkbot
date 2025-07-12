#!/bin/bash
# Activation script for SlinkBot virtual environment

echo "Activating SlinkBot virtual environment..."
source venv/bin/activate

echo "Virtual environment activated!"
echo "Python version: $(python --version)"
echo "Pip version: $(pip --version)"

echo ""
echo "Available commands:"
echo "  python slinkbot_phase3.py          - Run the Phase 3 bot"
echo "  python test_phase3_structure.py    - Test the structure"
echo "  python migration/migrate_json_to_sqlite.py <json_file> - Migrate data"
echo ""
echo "To deactivate: deactivate"