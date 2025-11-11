from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from datetime import date, datetime, timedelta
from typing import List, Dict
import models
from database import get_db, init_db, engine
from config import get_settings

settings = get_settings()

# Create tables
models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.api_title,
    version=settings.api_version
)

# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Update with your Vercel domain in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    """Health check endpoint"""
    return {
        "status": "online",
        "app": settings.api_title,
        "version": settings.api_version
    }


@app.get("/api/prices/latest")
def get_latest_prices(db: Session = Depends(get_db)):
    """Get latest prices for all assets"""
    latest_date = db.query(models.PriceHistory.date).order_by(
        models.PriceHistory.date.desc()
    ).first()
    
    if not latest_date:
        return {"prices": [], "date": None}
    
    prices = db.query(models.PriceHistory).filter(
        models.PriceHistory.date == latest_date[0]
    ).all()
    
    return {
        "date": latest_date[0].isoformat(),
        "prices": [
            {
                "symbol": p.symbol,
                "close": p.close_price,
                "open": p.open_price,
                "high": p.high_price,
                "low": p.low_price,
                "volume": p.volume
            }
            for p in prices
        ]
    }


@app.get("/api/prices/history/{symbol}")
def get_price_history(
    symbol: str,
    days: int = 30,
    db: Session = Depends(get_db)
):
    """Get historical prices for a symbol"""
    start_date = date.today() - timedelta(days=days)
    
    prices = db.query(models.PriceHistory).filter(
        models.PriceHistory.symbol == symbol.upper(),
        models.PriceHistory.date >= start_date
    ).order_by(models.PriceHistory.date.asc()).all()
    
    return {
        "symbol": symbol,
        "data": [
            {
                "date": p.date.isoformat(),
                "close": p.close_price,
                "open": p.open_price,
                "high": p.high_price,
                "low": p.low_price,
                "volume": p.volume
            }
            for p in prices
        ]
    }


@app.get("/api/signals/latest")
def get_latest_signal(db: Session = Depends(get_db)):
    """Get latest allocation signal"""
    signal = db.query(models.DailySignal).order_by(
        models.DailySignal.trade_date.desc()
    ).first()
    
    if not signal:
        return {"signal": None, "message": "No signals generated yet"}
    
    return {
        "trade_date": signal.trade_date.isoformat(),
        "generated_at": signal.generated_at.isoformat(),
        "allocations": signal.allocations,
        "model_type": signal.model_type,
        "confidence": signal.confidence_score
    }


@app.get("/api/portfolio")
def get_portfolio(db: Session = Depends(get_db)):
    """Get current portfolio holdings"""
    holdings = db.query(models.Portfolio).all()
    
    total_value = 0
    positions = []
    
    for holding in holdings:
        if holding.quantity > 0:
            # Get latest price
            latest_price = db.query(models.PriceHistory).filter(
                models.PriceHistory.symbol == holding.symbol
            ).order_by(models.PriceHistory.date.desc()).first()
            
            if latest_price:
                current_value = holding.quantity * latest_price.close_price
                total_value += current_value
                
                positions.append({
                    "symbol": holding.symbol,
                    "quantity": holding.quantity,
                    "avg_cost": holding.avg_cost,
                    "current_price": latest_price.close_price,
                    "current_value": current_value,
                    "unrealized_pnl": current_value - (holding.quantity * holding.avg_cost)
                })
    
    return {
        "positions": positions,
        "total_value": total_value
    }


@app.get("/api/trades/history")
def get_trade_history(
    days: int = 30,
    db: Session = Depends(get_db)
):
    """Get trade history"""
    start_date = date.today() - timedelta(days=days)
    
    trades = db.query(models.Trade).filter(
        models.Trade.trade_date >= start_date
    ).order_by(models.Trade.trade_date.desc()).all()
    
    return {
        "trades": [
            {
                "date": t.trade_date.isoformat(),
                "symbol": t.symbol,
                "action": t.action.value,
                "quantity": t.quantity,
                "price": t.price,
                "amount": t.amount
            }
            for t in trades
        ]
    }


@app.get("/api/performance")
def get_performance(
    days: int = 90,
    db: Session = Depends(get_db)
):
    """Get performance metrics"""
    start_date = date.today() - timedelta(days=days)
    
    metrics = db.query(models.PerformanceMetrics).filter(
        models.PerformanceMetrics.date >= start_date
    ).order_by(models.PerformanceMetrics.date.asc()).all()
    
    if not metrics:
        return {"performance": [], "summary": None}
    
    latest = metrics[-1]
    
    return {
        "performance": [
            {
                "date": m.date.isoformat(),
                "portfolio_value": m.portfolio_value,
                "total_value": m.total_value,
                "daily_return": m.daily_return,
                "cumulative_return": m.cumulative_return
            }
            for m in metrics
        ],
        "summary": {
            "total_return": latest.cumulative_return,
            "sharpe_ratio": latest.sharpe_ratio,
            "max_drawdown": latest.max_drawdown
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)