from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "Pump Station Optimization"
    db_url_read: str = (
        "postgresql://postgres:password@localhost:5432/pump_station_optimization"
    )
    db_url_write: str = (
        "postgresql://postgres:password@localhost:5432/pump_station_optimization"
    )

    class Config:
        env_file = ".env"


settings = Settings()
