# Database Migration & Deployment Guide

This guide explains how to deploy the capital allocator application to Railway with proper database migrations.

## Overview

The application uses **Alembic** for database migrations, which automatically run on startup. This ensures:
1. Tables are created on first deployment
2. Schema changes are applied on subsequent deployments
3. Seed data is loaded only once (idempotent)

## Migration System

### Files Structure

```
backend/
├── alembic/
│   ├── versions/
│   │   ├── cf868f7f5040_initial_schema.py        # Creates all tables
│   │   └── 27c553c12df9_seed_initial_data.py     # Loads seed data
│   ├── seed_data/                                 # SQL files for seeding
│   │   ├── price_history_10y.sql                 # 10 years of price data
│   │   └── trading_config_initial.sql            # Initial config
│   ├── env.py                                     # Alembic environment
│   └── script.py.mako                             # Migration template
├── alembic.ini                                    # Alembic configuration
├── run_migrations.py                              # Migration runner
└── scripts/
    ├── export_historical_data.py                  # Fetch 10 years data
    └── train_initial_config.py                    # Generate initial config
```

## First Deployment Setup

### Step 1: Generate Seed Data Locally

Before deploying to Railway, you need to generate the seed data files:

#### 1.1 Export Historical Price Data

```bash
cd backend

# Set up environment variables
export DATABASE_URL="postgresql://user:pass@localhost:5432/dbname"
export ALPHAVANTAGE_API_KEY="your_api_key_here"

# Fetch 10 years of historical data for SPY, QQQ, DIA
python scripts/export_historical_data.py
```

This will create `backend/alembic/seed_data/price_history_10y.sql` with approximately 7,500+ records.

**Note:** Alpha Vantage free tier allows 5 API calls/minute, so this will take ~45 seconds to complete.

#### 1.2 Generate Initial Trading Configuration

```bash
# Generate default trading configuration
python scripts/train_initial_config.py
```

This creates `backend/alembic/seed_data/trading_config_initial.sql` with the default configuration.

**Optional:** To train with actual backtesting (requires price data in database):
```bash
RUN_FULL_TUNING=true python scripts/train_initial_config.py
```

### Step 2: Commit Seed Data Files

```bash
git add backend/alembic/seed_data/
git commit -m "Add seed data for initial deployment"
git push origin main
```

### Step 3: Deploy to Railway

1. **Create Railway Project**
   - Go to https://railway.app
   - Click "New Project"
   - Select "Deploy from GitHub repo"
   - Choose your repository

2. **Add PostgreSQL Database**
   - In your Railway project, click "New"
   - Select "Database" → "PostgreSQL"
   - Railway will automatically set `DATABASE_URL` environment variable

3. **Configure Environment Variables**
   - Go to your service settings
   - Add the following variables:
     ```
     ALPHAVANTAGE_API_KEY=your_api_key_here
     ```
   - `DATABASE_URL` is automatically set by Railway

4. **Deploy**
   - Railway will automatically detect the `railway.json` configuration
   - It will install dependencies from `backend/requirements.txt`
   - On startup, `main.py` will run migrations automatically:
     - Creates all tables (if first deployment)
     - Loads seed data (if tables are empty)
   - The API will start on the assigned port

## Subsequent Deployments

For subsequent deployments, migrations will:
- **Skip** creating tables (they already exist)
- **Skip** loading seed data (tables already have data)
- **Apply** any new schema changes

This is handled automatically - no manual intervention needed!

## Adding New Migrations

When you need to add a new column or change schema:

### Example: Adding a new column to trading_config

```bash
cd backend

# Create a new migration
python -m alembic revision -m "add_new_parameter_to_config"
```

Edit the generated file in `backend/alembic/versions/`:

```python
def upgrade() -> None:
    op.add_column('trading_config',
        sa.Column('new_parameter', sa.Float(), nullable=False, server_default='0.5')
    )

def downgrade() -> None:
    op.drop_column('trading_config', 'new_parameter')
```

Commit and push - Railway will apply this automatically on next deployment:

```bash
git add backend/alembic/versions/
git commit -m "Add new_parameter to trading_config"
git push origin main
```

## Migration Commands

### Check Current Migration Status

```bash
cd backend
python run_migrations.py --check
```

### Run Migrations Manually

```bash
cd backend
python run_migrations.py
```

### Rollback Last Migration

```bash
cd backend
python -m alembic downgrade -1
```

### View Migration History

```bash
cd backend
python -m alembic history
```

## Railway-Specific Considerations

### No Public Database Access

Railway PostgreSQL databases are **private** by default (no egress costs). This migration system:
- ✅ Runs migrations **inside** Railway's private network
- ✅ No need for public database URLs
- ✅ Seed data is bundled in the repository
- ✅ No external database connections needed during deployment

### Migration Runs on Every Startup

The application runs migrations on **every** startup. This is safe because:
- Alembic tracks which migrations have run
- Already-applied migrations are skipped
- Seed data checks if tables are empty before loading

### Zero Downtime Deployments

For zero-downtime deployments:
1. **Backward-compatible migrations**: New columns should have defaults
2. **Two-phase changes**: For breaking changes, deploy in two steps:
   - Phase 1: Add new column with default
   - Phase 2: Remove old column (after code is updated)

## Troubleshooting

### Migration Fails on Railway

Check Railway logs for errors:
```
railway logs
```

Common issues:
- **Missing seed data files**: Ensure `backend/alembic/seed_data/*.sql` are committed
- **Database connection failed**: Check `DATABASE_URL` is set correctly
- **Permission errors**: Ensure database user has CREATE/ALTER permissions

### Seed Data Not Loading

The seed migration checks if tables are empty. If you need to re-seed:

```bash
# Connect to Railway database (use Railway CLI)
railway connect postgres

# Clear tables
DELETE FROM price_history;
DELETE FROM trading_config;

# Redeploy - seed migration will run again
```

### Migration Out of Sync

If migrations are out of sync between local and Railway:

```bash
# Check current revision on Railway
railway run python backend/run_migrations.py --check

# Manually set revision (use with caution!)
railway run python -m alembic stamp head
```

## Best Practices

1. **Always test migrations locally first**
   ```bash
   # Use a local PostgreSQL database
   export DATABASE_URL="postgresql://localhost:5432/capital_allocator_test"
   python run_migrations.py
   ```

2. **Make migrations reversible**
   - Always implement `downgrade()` function
   - Test rollback before deploying

3. **Use server defaults for new columns**
   ```python
   sa.Column('new_column', sa.Float(), nullable=False, server_default='1.0')
   ```

4. **Keep seed data in version control**
   - Seed data files should be committed to git
   - This ensures consistent first deployment

5. **Monitor deployment logs**
   - Watch Railway logs during deployment
   - Verify migrations completed successfully

## Additional Resources

- [Alembic Documentation](https://alembic.sqlalchemy.org/)
- [Railway Documentation](https://docs.railway.app/)
- [FastAPI Deployment](https://fastapi.tiangolo.com/deployment/)
