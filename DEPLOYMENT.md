# Railway Deployment Guide

Clean, simple guide for deploying to Railway with proper database setup.

---

## 🎯 Overview

This app uses **3 separate environments**:

1. **Testing** - Isolated `test_*` tables, drop/recreate every test run
2. **Local** - Your development database with real data for training
3. **Production** - Railway deployment with migrations

---

## 📦 Prerequisites

```bash
# Install dependencies
cd backend
pip install -r requirements.txt

# Set up environment
cp .env.example .env
# Edit .env with your DATABASE_URL
```

---

## 🧪 Testing (Isolated)

Tests use separate `test_*` tables that are completely isolated from your local development data.

```bash
# Setup test database (drops/recreates test_* tables)
python tests/setup_test_db.py

# Run tests
pytest

# Tests NEVER touch your real tables!
```

---

## 💻 Local Development

### 1. Get 10 Years of Historical Data

```bash
cd backend

# Fetch 10 years of price data (FREE via Yahoo Finance)
python scripts/fetch_data_yahoo.py --days 3650
```

This populates your local `price_history` table.

### 2. Train & Backtest Locally

```bash
# Train with aggressive params + 5Y/5Y split
python scripts/train_config_locally.py
```

This will:
- Create aggressive trading config in your LOCAL database
- Run 5-year backtest (2020-2025)
- Validate parameters work
- Generate `alembic/seed_data/trading_config_initial.sql` for Railway
- Save backtest report to `data/back-test/`

**Review the results** before deploying!

### 3. Export Data for Railway

```bash
# Export price history to SQL file
python scripts/export_historical_data.py
```

This generates `alembic/seed_data/price_history_10y.sql` from your LOCAL database.

---

## 🚀 Production (Railway)

### Step 1: Prepare Deployment

```bash
# Commit seed data
git add backend/alembic/seed_data/
git commit -m "Add validated seed data for Railway deployment"
git push
```

### Step 2: Deploy to Railway

1. **Create Railway Project**
   - Go to https://railway.app
   - Click "New Project" → "Deploy from GitHub"
   - Select your repository

2. **Add PostgreSQL**
   - Click "New" → "Database" → "PostgreSQL"
   - Railway automatically sets `DATABASE_URL`

3. **Set Environment Variables**
   ```
   ALPHAVANTAGE_API_KEY=your_key_here
   ```
   (DATABASE_URL is auto-set by Railway)

4. **Deploy**
   - Railway auto-detects `railway.json`
   - On startup, `main.py` runs migrations:
     - Creates all tables (first deploy only)
     - Loads seed data if tables are empty
     - Subsequent deploys: no-op unless schema changes

### Step 3: Verify

Check Railway logs for:
```
Running database migrations...
Creating tables...
Loading historical price data...
  ✓ Loaded 7500+ price history records
Loading initial trading configuration...
  ✓ Loaded initial trading configuration
✓ Database migrations completed successfully
```

---

## 🔄 Schema Changes

When you need to add a new column (e.g., `new_risk_param`):

```bash
cd backend

# Create new migration
python -m alembic revision -m "add_new_risk_param"
```

Edit the generated migration:

```python
def upgrade() -> None:
    op.add_column('trading_config',
        sa.Column('new_risk_param', sa.Float(),
                  nullable=False, server_default='0.5')
    )

def downgrade() -> None:
    op.drop_column('trading_config', 'new_risk_param')
```

Commit and push - Railway applies it automatically!

---

## 📁 Directory Structure

```
backend/
├── alembic/                    # Railway migrations (PROD ONLY)
│   ├── versions/
│   │   ├── cf868f7f5040_initial_schema.py
│   │   └── 27c553c12df9_seed_initial_data.py
│   └── seed_data/
│       ├── price_history_10y.sql      # Generated from LOCAL
│       └── trading_config_initial.sql # Generated from LOCAL
├── scripts/
│   ├── fetch_data_yahoo.py            # Get data (LOCAL)
│   ├── train_config_locally.py        # Train & backtest (LOCAL)
│   └── export_historical_data.py      # Export for Railway
├── tests/
│   ├── setup_test_db.py               # Standalone test setup
│   └── ...                            # Test files
└── main.py                             # Runs migrations on startup
```

---

## 🔑 Key Principles

1. **Testing**: Completely isolated `test_*` tables
2. **Local**: Train/validate with real data before deployment
3. **Production**: Migrations run once, seed once if empty, then hands-off

### On First Deploy:
- ✅ Creates all tables
- ✅ Loads 10 years of price data
- ✅ Loads validated trading config

### On Subsequent Deploys:
- ✅ Skips table creation (already exist)
- ✅ Skips seed data (tables not empty)
- ✅ Only applies new schema migrations (if any)

---

## 🐛 Troubleshooting

### Migration Failed
```bash
# Check Railway logs
railway logs

# Common issues:
# - Missing seed data files → commit them!
# - DATABASE_URL not set → Railway should auto-set it
```

### Want to Re-seed
```bash
# Connect to Railway DB
railway connect postgres

# Clear data
DELETE FROM price_history;
DELETE FROM trading_config;

# Redeploy - seed migration will run again
```

### Test Tables Interfering
```bash
# Tests are isolated! They use test_* tables only
# If confused, just reset:
python tests/setup_test_db.py
```

---

## 📊 Configuration Parameters

The aggressive config (generated by `train_config_locally.py`):

```python
regime_bullish_threshold: 0.1      # Easy to trigger bullish
regime_bearish_threshold: -0.1     # Easy to trigger bearish
allocation_low_risk: 1.0           # 100% capital deployment
allocation_medium_risk: 1.0        # 100% capital deployment
allocation_high_risk: 0.9          # 90% capital deployment
allocation_neutral: 0.7            # 70% even in neutral
min_confidence_threshold: 0.1      # Allow more trades (10%)
confidence_scaling_factor: 0.2     # Less penalty from low confidence
```

These are validated via 5-year backtest before deployment!

---

## ✅ Checklist

- [ ] Get 10 years of data: `python scripts/fetch_data_yahoo.py --days 3650`
- [ ] Train locally: `python scripts/train_config_locally.py`
- [ ] Review backtest results in `data/back-test/`
- [ ] Export for Railway: `python scripts/export_historical_data.py`
- [ ] Commit seed data: `git add backend/alembic/seed_data/ && git commit`
- [ ] Deploy to Railway
- [ ] Verify in Railway logs

Done! 🎉
