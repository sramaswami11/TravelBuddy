from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    groq_api_key: str = ""
    duffel_api_key: str = ""
    ticketmaster_api_key: str = ""
    frontend_url: str = ""
    travelpayouts_token: str = ""
    travelpayouts_marker: str = ""


settings = Settings()
