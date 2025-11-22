#!/bin/bash
# Prepare seed data for Railway deployment

set -e  # Exit on error

echo "================================================"
echo "Capital Allocator - Deployment Preparation"
echo "================================================"
echo ""

# Check if we're in the right directory
if [ ! -f "requirements.txt" ]; then
    echo "Error: Must run from backend/ directory"
    exit 1
fi

# Check for required environment variables
if [ -z "$DATABASE_URL" ]; then
    echo "Error: DATABASE_URL must be set to export data from your local database"
    echo "Example: export DATABASE_URL='postgresql://user:pass@localhost:5432/capital_allocator'"
    exit 1
fi

echo "✓ Environment variables configured"
echo ""

# Create seed data directory
SEED_DIR="alembic/seed_data"
mkdir -p "$SEED_DIR"
echo "✓ Created seed data directory: $SEED_DIR"
echo ""

# Generate trading config (fast, no API calls needed)
echo "Step 1: Generating initial trading configuration..."
python scripts/train_initial_config.py

if [ ! -f "$SEED_DIR/trading_config_initial.sql" ]; then
    echo "Error: Failed to generate trading_config_initial.sql"
    exit 1
fi
echo "✓ Trading configuration generated"
echo ""

# Ask if user wants to fetch historical data
echo "Step 2: Historical price data"
echo ""

if [ -f "$SEED_DIR/price_history_10y.sql" ]; then
    echo "✓ price_history_10y.sql already exists"
    read -p "Do you want to regenerate it? (y/N): " REGENERATE
    if [ "$REGENERATE" != "y" ] && [ "$REGENERATE" != "Y" ]; then
        echo "  Skipping historical data fetch"
        SKIP_FETCH=true
    fi
fi

if [ "$SKIP_FETCH" != "true" ]; then
    echo "Exporting 10 years of historical data from local database..."
    echo "  This will read from your price_history table in DATABASE_URL"
    echo ""
    read -p "Continue? (Y/n): " CONTINUE

    if [ "$CONTINUE" == "n" ] || [ "$CONTINUE" == "N" ]; then
        echo "Skipped. You can run this later with:"
        echo "  python scripts/export_historical_data.py"
        echo ""
    else
        python scripts/export_historical_data.py

        if [ ! -f "$SEED_DIR/price_history_10y.sql" ]; then
            echo "Error: Failed to generate price_history_10y.sql"
            exit 1
        fi
        echo "✓ Historical price data exported"
        echo ""
    fi
fi

# Summary
echo "================================================"
echo "Deployment Preparation Complete!"
echo "================================================"
echo ""
echo "Generated files:"
ls -lh "$SEED_DIR"
echo ""
echo "Next steps:"
echo "  1. Review the generated SQL files in $SEED_DIR"
echo "  2. Commit to git:"
echo "       git add backend/alembic/seed_data/"
echo "       git commit -m 'Add seed data for initial deployment'"
echo "       git push"
echo "  3. Deploy to Railway"
echo ""
echo "See backend/DEPLOYMENT.md for detailed deployment instructions"
