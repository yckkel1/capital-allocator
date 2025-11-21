# Capital Allocator Web Dashboard

A modern, single-page web dashboard for monitoring the Capital Allocator automated trading system. Built with Next.js 14, TypeScript, and deployed on Vercel with PostgreSQL database on Railway.

## Table of Contents

1. [Features](#features)
2. [Tech Stack](#tech-stack)
3. [Project Structure](#project-structure)
4. [Setup & Installation](#setup--installation)
5. [Environment Variables](#environment-variables)
6. [Development](#development)
7. [Testing](#testing)
8. [Deployment](#deployment)
9. [API Routes](#api-routes)
10. [Security](#security)

---

## Features

### 1. P&L Visualization
- **Interactive time-series chart** showing portfolio value over time
- **Time range filters**: 1M, 3M, 6M, 1Y, 2Y, 5Y, YTD, ALL
- **Hover tooltips** displaying exact values, daily return, and cumulative return
- **Key metrics**: Total return, max drawdown, Sharpe ratio

### 2. Portfolio Holdings
- **Current positions** with real-time P&L calculations
- **Per-position metrics**: Market value, unrealized P&L, unrealized P&L %
- **Pending changes indicator**: Shows quantity changes from today's signal (e.g., +100/-100)
- **Summary stats**: Total value, total P&L, cash balance

### 3. Trading Configuration
- **Current and previous configs** displayed side-by-side
- **Highlighted changes** with percentage differences
- **Key parameters**: Regime thresholds, allocations, risk levels, circuit breakers
- **Toggle view**: Switch between key parameters and all parameters

### 4. Strategy Decision (D-1)
- **Yesterday's signal** showing planned action (BUY/SELL/HOLD)
- **Market analysis**: Regime (bullish/neutral/bearish), risk level, confidence score
- **Planned allocations** by asset with dollar amounts
- **Execution status**: Shows today's executed trades if available
- **Circuit breaker status**: Visual indicator if active

### 5. Historical Trades
- **Trade history table** with filtering by time range (1W, 2W, 1M, 3M)
- **Trade details**: Date/time, action, symbol, quantity, price, total amount
- **Default view**: Last 2 weeks of trades
- **Color-coded actions**: Green for BUY, red for SELL

---

## Tech Stack

### Frontend
- **Next.js 14** - React framework with App Router
- **TypeScript** - Type-safe JavaScript
- **Tailwind CSS** - Utility-first CSS framework
- **Recharts** - Chart library for data visualization

### Backend
- **Next.js API Routes** - Serverless API endpoints
- **PostgreSQL** - Relational database (hosted on Railway)
- **pg** - PostgreSQL client for Node.js

### Testing
- **Jest** - JavaScript testing framework
- **React Testing Library** - Component testing
- **Coverage threshold**: 80%+ on all metrics

### Deployment
- **Vercel** - Hosting platform with automatic deployments
- **Railway** - PostgreSQL database hosting

---

## Project Structure

```
web/
├── src/
│   ├── app/                      # Next.js App Router
│   │   ├── api/                  # API routes (serverless functions)
│   │   │   ├── pnl/              # P&L data endpoint
│   │   │   ├── portfolio/        # Portfolio data endpoint
│   │   │   ├── trades/           # Trade history endpoint
│   │   │   ├── signals/          # Trading signals endpoints
│   │   │   ├── config/           # Trading config endpoint
│   │   │   ├── prices/           # Price data endpoint
│   │   │   └── performance/      # Performance metrics endpoint
│   │   ├── layout.tsx            # Root layout with header/footer
│   │   ├── page.tsx              # Main dashboard page
│   │   └── globals.css           # Global styles
│   │
│   ├── components/               # React components
│   │   ├── ui/                   # Reusable UI components
│   │   │   ├── Card.tsx          # Card container
│   │   │   └── Badge.tsx         # Badge component
│   │   ├── PnLChart.tsx          # P&L chart component
│   │   ├── PortfolioHoldings.tsx # Portfolio display
│   │   ├── TradingConfig.tsx     # Config comparison
│   │   ├── StrategyDecision.tsx  # D-1 strategy display
│   │   └── TradesTable.tsx       # Trade history table
│   │
│   ├── services/                 # Business logic layer
│   │   ├── performance.service.ts # P&L and metrics data
│   │   ├── portfolio.service.ts   # Portfolio data
│   │   ├── trades.service.ts      # Trade data
│   │   ├── signals.service.ts     # Signal data
│   │   ├── config.service.ts      # Config data
│   │   └── prices.service.ts      # Price data
│   │
│   ├── types/                    # TypeScript type definitions
│   │   ├── models.ts             # Database models
│   │   └── api.ts                # API response types
│   │
│   ├── lib/                      # Shared utilities
│   │   ├── db.ts                 # Database connection pool
│   │   └── constants.ts          # App constants
│   │
│   ├── utils/                    # Utility functions
│   │   └── format.ts             # Formatting helpers
│   │
│   └── __tests__/                # Test files
│       ├── api/                  # API route tests
│       ├── services/             # Service tests
│       └── utils/                # Utility tests
│
├── public/                       # Static assets
├── .env.example                  # Example environment variables
├── package.json                  # Dependencies
├── tsconfig.json                 # TypeScript config
├── tailwind.config.js            # Tailwind CSS config
├── jest.config.js                # Jest config
├── next.config.js                # Next.js config
├── vercel.json                   # Vercel deployment config
└── README.md                     # This file
```

### Separation of Concerns

The codebase follows a clear **layered architecture**:

1. **Presentation Layer** (`/components`): React components for UI
2. **API Layer** (`/app/api`): Next.js API routes (controllers)
3. **Business Logic Layer** (`/services`): Data access and processing
4. **Data Access Layer** (`/lib/db`): Database connection and queries
5. **Types Layer** (`/types`): TypeScript interfaces
6. **Utilities Layer** (`/utils`): Helper functions

---

## Setup & Installation

### Prerequisites

- **Node.js** 18+ and npm/yarn
- **PostgreSQL** database (Railway or other hosting provider)
- **Git** for version control

### Installation Steps

1. **Clone the repository**:
   ```bash
   cd capital-allocator/web
   ```

2. **Install dependencies**:
   ```bash
   npm install
   ```

3. **Set up environment variables**:
   ```bash
   cp .env.example .env
   ```
   Edit `.env` and add your database connection string:
   ```
   DATABASE_URL=postgresql://user:password@host:port/database
   ```

4. **Run development server**:
   ```bash
   npm run dev
   ```

5. **Open browser**:
   Navigate to [http://localhost:3000](http://localhost:3000)

---

## Environment Variables

### Required Variables

Create a `.env` file in the `web/` directory:

```bash
# Database Configuration
DATABASE_URL=postgresql://username:password@host:port/database_name

# Application Settings (optional)
NODE_ENV=development
NEXT_PUBLIC_APP_NAME="Capital Allocator"
```

### Production Environment Variables (Vercel)

When deploying to Vercel, set environment variables in the Vercel dashboard:

1. Go to your project on [Vercel](https://vercel.com)
2. Navigate to **Settings > Environment Variables**
3. Add the following variables:
   - `DATABASE_URL`: Your Railway PostgreSQL connection string
   - `NODE_ENV`: Set to `production`

### Database URL Format

```
postgresql://[user]:[password]@[host]:[port]/[database]
```

Example:
```
postgresql://postgres:mypassword@myproject.railway.app:5432/railway
```

### Security Notes

- **NEVER** commit `.env` files to Git (already in `.gitignore`)
- Use Vercel's environment variable encryption
- Database credentials are only accessible server-side (API routes)
- Client-side code cannot access `DATABASE_URL`

---

## Development

### Running the Development Server

```bash
npm run dev
```

The app will be available at [http://localhost:3000](http://localhost:3000)

### Building for Production

```bash
npm run build
```

This creates an optimized production build in the `.next/` directory.

### Running Production Build Locally

```bash
npm run build
npm start
```

### Linting

```bash
npm run lint
```

---

## Testing

### Running Tests

```bash
# Run all tests
npm test

# Run tests in watch mode
npm run test:watch

# Run tests with coverage
npm run test:coverage
```

### Coverage Requirements

The project maintains **80%+ coverage** on all metrics:
- **Branches**: 80%
- **Functions**: 80%
- **Lines**: 80%
- **Statements**: 80%

### Test Structure

Tests are organized by layer:
- `__tests__/api/`: API route tests
- `__tests__/services/`: Business logic tests
- `__tests__/utils/`: Utility function tests

### Mocking

All database calls in tests are mocked using Jest:
```typescript
jest.mock('@/lib/db');
```

---

## Deployment

### Deploying to Vercel

#### Option 1: Vercel CLI

```bash
# Install Vercel CLI
npm install -g vercel

# Login to Vercel
vercel login

# Deploy
vercel
```

#### Option 2: Vercel Dashboard (Recommended)

1. Push your code to GitHub
2. Go to [Vercel](https://vercel.com) and click "New Project"
3. Import your GitHub repository
4. Configure environment variables:
   - `DATABASE_URL`: Your Railway PostgreSQL connection string
5. Click "Deploy"

#### Option 3: Automatic Deployments

Vercel will automatically deploy:
- **Production**: When you push to the `main` branch
- **Preview**: When you push to any other branch or create a PR

### Post-Deployment

After deployment:
1. Verify environment variables are set correctly
2. Test all API endpoints
3. Check database connectivity
4. Monitor Vercel logs for errors

### Custom Domain

To add a custom domain:
1. Go to your project on Vercel
2. Navigate to **Settings > Domains**
3. Add your domain and configure DNS

---

## API Routes

All API routes are read-only and return JSON responses in the format:
```typescript
{
  data: T | null,
  error: string | null
}
```

### Endpoints

#### 1. P&L Data
```
GET /api/pnl?timeRange=1Y
```
Returns portfolio value over time for the specified range.

**Query Parameters**:
- `timeRange`: `1M`, `3M`, `6M`, `1Y`, `2Y`, `5Y`, `YTD`, `ALL`

**Response**:
```json
{
  "data": {
    "data": [
      {
        "date": "2024-01-15",
        "value": 2000,
        "daily_return": 1.5,
        "cumulative_return": 25.3
      }
    ],
    "start_date": "2023-01-15",
    "end_date": "2024-01-15",
    "total_return": 500,
    "total_return_pct": 25,
    "max_drawdown": -8.5,
    "sharpe_ratio": 1.42
  },
  "error": null
}
```

#### 2. Portfolio Holdings
```
GET /api/portfolio
```
Returns current portfolio holdings with metrics.

**Response**:
```json
{
  "data": {
    "positions": [
      {
        "symbol": "SPY",
        "quantity": 10,
        "avg_cost": 400,
        "current_price": 420,
        "market_value": 4200,
        "unrealized_pnl": 200,
        "unrealized_pnl_pct": 5,
        "pending_quantity_change": 2
      }
    ],
    "total_value": 4200,
    "cash_balance": 1000
  },
  "error": null
}
```

#### 3. Trade History
```
GET /api/trades?days=14
```
Returns trade history for the specified number of days.

**Query Parameters**:
- `days`: Number of days to look back (default: 14)

#### 4. Latest Signal
```
GET /api/signals/latest
```
Returns the most recent trading signal.

#### 5. Yesterday's Decision (D-1)
```
GET /api/signals/yesterday
```
Returns yesterday's signal with today's executed trades.

#### 6. Trading Configuration
```
GET /api/config
GET /api/config?history=true&limit=12
```
Returns current config comparison or historical configs.

#### 7. Latest Prices
```
GET /api/prices/latest
```
Returns latest closing prices for all assets.

#### 8. Latest Performance Metrics
```
GET /api/performance/latest
```
Returns the most recent performance metrics.

---

## Security

### Design Principles

1. **Display-Only Mode**: The web interface is **read-only**. Users cannot modify data through the UI.
2. **No User Input**: All data modifications happen through the backend Python scripts.
3. **Server-Side Data Access**: Database credentials are only accessible in server-side code (API routes).
4. **Environment Variable Protection**: All sensitive credentials are stored in environment variables, never in code.

### Database Security

- **Connection Pooling**: Secure connection pool with SSL in production
- **Parameterized Queries**: All SQL queries use parameterized statements to prevent SQL injection
- **Read-Only Operations**: Web app only performs SELECT queries
- **No Direct Client Access**: Clients never interact directly with the database

### API Security

- **No Authentication Required**: Since the app is display-only and shows portfolio data for a single user
- **CORS**: Configured for same-origin requests only
- **Rate Limiting**: Handled by Vercel's infrastructure
- **Error Handling**: Errors are logged server-side, generic messages returned to client

### Environment Variables

**Production Setup**:
1. Set `DATABASE_URL` in Vercel dashboard (Settings > Environment Variables)
2. Use Railway's connection string with SSL enabled
3. Never commit `.env` files to Git

**Access Control**:
- `DATABASE_URL` is only accessible in server-side code (API routes)
- Client-side code cannot access `process.env.DATABASE_URL`
- Next.js automatically separates server and client environments

---

## Troubleshooting

### Common Issues

#### 1. Database Connection Errors

**Error**: `Error: connect ECONNREFUSED`

**Solution**:
- Verify `DATABASE_URL` is set correctly
- Check Railway database is running
- Ensure firewall allows connections

#### 2. Module Not Found Errors

**Error**: `Module not found: Can't resolve '@/...'`

**Solution**:
- Run `npm install` to install dependencies
- Check `tsconfig.json` paths are correct

#### 3. Build Errors

**Error**: `Type error: Cannot find module...`

**Solution**:
- Ensure all TypeScript files are properly typed
- Run `npm run lint` to check for errors

#### 4. API Route 500 Errors

**Error**: API routes returning 500 status

**Solution**:
- Check Vercel logs for detailed error messages
- Verify database connection is working
- Ensure environment variables are set in Vercel

---

## Future Enhancements

Potential improvements for future versions:

1. **Real-time Updates**: WebSocket support for live data updates
2. **Historical Config Comparison**: View parameter changes over time
3. **Advanced Filtering**: Filter trades by symbol, action, date range
4. **Export Functionality**: Download data as CSV/Excel
5. **Mobile Optimization**: Responsive design for mobile devices
6. **Performance Benchmarking**: Compare against SPY/QQQ/DIA benchmarks
7. **Alert System**: Email/SMS alerts for circuit breaker triggers
8. **Dark Mode**: Theme toggle for dark mode

---

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review Vercel deployment logs
3. Check Railway database logs
4. Refer to the main project README: `/capital-allocator/README.md`

---

## License

Same as parent project.

---

**Last Updated**: January 2025
**Version**: 1.0.0
