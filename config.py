from pathlib import Path

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(ROOT / ".env"), extra="ignore")
    env: str = "dev"
    database_url: str = "postgresql+psycopg://modelledger:modelledger@localhost:5432/modelledger"
    chain_rpc_url: str = "http://127.0.0.1:8545"
    chain_id: int = 31337
    contract_address: str = ""
    issuer_key: str = ""
    gateway_key: str = ""
    registrar_key: str = ""
    dev_api_key: str = ""
    public_url: str = "http://localhost:8080"
    cors_origins: str = "http://localhost:5173,http://localhost:8080"
    allow_simulated: bool = False
    enable_demo: bool = False
    rate_limit_per_minute: int = 60

    @model_validator(mode="after")
    def validate_environment(self):
        if self.env not in ("dev", "test", "production"):
            raise ValueError("ENV must be dev, test or production")
        if self.env != "test" and not self.database_url.startswith("postgresql"):
            raise ValueError("PostgreSQL is mandatory outside isolated tests")
        if self.env == "production":
            if self.allow_simulated or self.enable_demo or self.dev_api_key:
                raise ValueError("Production cannot enable demo, simulated evidence or dev API authentication")
            if not self.issuer_key or not self.gateway_key or not self.contract_address:
                raise ValueError("Production requires issuer, gateway and registry configuration")
            if not self.public_url.startswith("https://"):
                raise ValueError("Production PUBLIC_URL must use HTTPS")
        return self


settings = Settings()
