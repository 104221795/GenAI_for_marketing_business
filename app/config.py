from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    APP_NAME: str = "AI Product Studio Reference Editing"
    ENV: str = "dev"
    DATABASE_URL: str = "sqlite:///./app.db"
    STORAGE_DIR: str = "storage"
    LOG_LEVEL: str = "INFO"

    VISUAL_PROVIDER_CHAIN: str = "cloudflare_flux,original"

    CLOUDFLARE_ACCOUNT_ID: str | None = None
    CLOUDFLARE_API_TOKEN: str | None = None
    CLOUDFLARE_IMAGE_MODEL: str = "@cf/black-forest-labs/flux-2-klein-4b"
    CLOUDFLARE_IMAGE_WIDTH: int = 1024
    CLOUDFLARE_IMAGE_HEIGHT: int = 1024

    GEMINI_API_KEY: str | None = None
    GEMINI_IMAGE_MODEL: str = "gemini-2.5-flash-image"
    GEMINI_IMAGE_MODEL_CHAIN: str = "gemini-2.5-flash-image,gemini-3-pro-image-preview"
    GOOGLE_IMAGEN_MODEL: str = "imagen-4.0-generate-001"
    GOOGLE_IMAGEN_ASPECT_RATIO: str = "1:1"

    REPLICATE_API_TOKEN: str | None = None
    REPLICATE_FLUX_MODEL: str = "black-forest-labs/flux-kontext-pro"
    REPLICATE_FLUX_MODEL_CHAIN: str = "black-forest-labs/flux-kontext-max,black-forest-labs/flux-kontext-pro"
    REPLICATE_FLUX_REFERENCE_MODEL_CHAIN: str = "flux-kontext-apps/multi-image-kontext-max,flux-kontext-apps/multi-image-kontext-pro"
    REPLICATE_FLUX_ASPECT_RATIO: str = "match_input_image"

    LLM_PROVIDER_CHAIN: str = "gemini_text,mock"
    GEMINI_TEXT_MODEL: str = "gemini-2.5-flash-lite"
    GEMINI_TEXT_MODEL_CHAIN: str = "gemini-2.5-flash-lite,gemini-2.5-flash"

    DEFAULT_VARIANTS: int = 2
    REQUEST_TIMEOUT_SECONDS: int = 120
    MAX_UPLOAD_MB: int = 12

settings = Settings()
