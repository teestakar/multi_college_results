from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str
    JWT_SECRET: str
    
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRY_MINUTES: int = 1
    ENVIRONMENT: str = "development"
    
    class Config:
        env_file = ".env"




settings = Settings()