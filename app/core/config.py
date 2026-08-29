from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    alpaca_api_key: str
    alpaca_api_secret: str

    alpaca_data_url: str = "https://data.alpaca.markets"
    alpaca_trading_url: str = "https://paper-api.alpaca.markets"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()