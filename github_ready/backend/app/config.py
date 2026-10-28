from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    supabase_url: str = "https://your-project.supabase.co"
    supabase_anon_key: str = "placeholder-anon-key"
    supabase_service_role_key: str = "placeholder-service-role-key"
    jwt_secret: str = "placeholder-jwt-secret"
    allowed_origins: str = "http://localhost:8081,exp://localhost:8081"

    @property
    def origins_list(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",")]

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
