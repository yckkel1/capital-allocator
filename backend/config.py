"""
Application Configuration
Loads sensitive credentials from .env files and trading parameters from database
"""
from datetime import date
from typing import Optional
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """
    Application settings for sensitive credentials only
    Trading parameters are now loaded from database via get_trading_config()
    """

    # Database - REQUIRED (kept in .env.local / .env.production)
    database_url: str

    # Alpha Vantage API - REQUIRED (kept in .env.local / .env.production)
    alphavantage_api_key: str

    # API metadata
    api_title: str = "Capital Allocator API"
    api_version: str = "1.0.0"

    # Model type (rarely changes, kept in env)
    model_type: str = "momentum"  # momentum, mean_reversion, risk_parity

    # Data Fetch timing (rarely changes, kept in env)
    market_close_time: str = "16:30"  # 4:30 PM ET
    signal_generation_time: str = "06:00"  # 6:00 AM ET

    class Config:
        # This will look for .env, .env.local, or .env.production
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance (sensitive credentials only)"""
    return Settings()


def get_trading_config(as_of_date: Optional[date] = None):
    """
    Get trading configuration from database

    Args:
        as_of_date: Date to get config for. Defaults to today.

    Returns:
        TradingConfig instance with all trading parameters

    Example:
        config = get_trading_config()
        print(f"Daily capital: ${config.daily_capital}")
        print(f"Assets: {config.assets}")
    """
    from config_loader import get_active_trading_config
    return get_active_trading_config(as_of_date)