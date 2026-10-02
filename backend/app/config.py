import os

DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql+psycopg://disputes:disputes@localhost:5432/disputes"
)
JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret-change-me")
JWT_ALG = "HS256"
JWT_TTL_MIN = int(os.getenv("JWT_TTL_MIN", "60"))
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000").split(",")
