#!/bin/bash
#
# Monthly Strategy Tuning Wrapper Script
# Run this on the 1st trading day of each month
#
# Usage:
#   ./run_monthly_tuning.sh                    # Normal run (checks if 1st trading day)
#   ./run_monthly_tuning.sh --force            # Force run
#   ./run_monthly_tuning.sh --lookback 6       # Custom lookback period

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/backend"

cd "$BACKEND_DIR"

echo "======================================================================"
echo "🗓️  Monthly Strategy Tuning"
echo "======================================================================"
echo ""

# Parse arguments
FORCE_FLAG=""
LOOKBACK=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --force)
            FORCE_FLAG="--force"
            shift
            ;;
        --lookback)
            LOOKBACK="--lookback-months $2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--force] [--lookback N]"
            exit 1
            ;;
    esac
done

# Run the tuning script
python run_monthly_tuning.py $FORCE_FLAG $LOOKBACK

echo ""
echo "======================================================================"
echo "✅ Tuning complete! Review reports in data/strategy-tuning/"
echo "======================================================================"
