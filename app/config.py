from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "AI Product Studio Reference Editing"
    ENV: str = "dev"
    DATABASE_URL: str = "sqlite:///./app.db"
    STORAGE_DIR: str = "storage"
    LOG_LEVEL: str = "INFO"

    VISUAL_PROVIDER_CHAIN: str = "gemini_image,replicate_flux,mock"

    GEMINI_API_KEY: str | None = None
    GEMINI_IMAGE_MODEL: str = "gemini-3.1-flash-image-preview"

    REPLICATE_API_TOKEN: str | None = None
    REPLICATE_FLUX_MODEL: str = "black-forest-labs/flux-kontext-pro"

    LLM_PROVIDER_CHAIN: str = "gemini_text,mock"
    GEMINI_TEXT_MODEL: str = "gemini-2.5-flash-lite"

    DEFAULT_VARIANTS: int = 2
    REQUEST_TIMEOUT_SECONDS: int = 120

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
