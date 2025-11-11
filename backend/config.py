from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings from environment variables"""
    
    # Database - REQUIRED
    database_url: str
    
    # Alpha Vantage API - REQUIRED
    alphavantage_api_key: str
    
    # API
    api_title: str = "Capital Allocator API"
    api_version: str = "1.0.0"
    
    # Trading Parameters - can override in .env
    daily_capital: float = 1000.0
    assets: list[str] = ["SPY", "QQQ", "DIA"]
    
    # Model Settings
    lookback_days: int = 252  # 1 year of trading days
    model_type: str = "momentum"  # momentum, mean_reversion, risk_parity
    
    # Data Fetch
    market_close_time: str = "16:30"  # 4:30 PM ET
    signal_generation_time: str = "06:00"  # 6:00 AM ET
    
    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings():
    """Cached settings instance"""
    return Settings()