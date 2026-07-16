import os
from datetime import timedelta


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-me")
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        "postgresql+psycopg2://acctsys:acctsys_dev_pw@localhost:5432/acctsys_dev",
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}

    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "dev-jwt-secret-change-me")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=30)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=14)
    JWT_TOKEN_LOCATION = ["headers"]

    CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "http://localhost:5173").split(",")

    # Super-admin bootstrap credentials (ETG-only cross-tenant layer). Only
    # used to seed the first super-admin; rotate/remove after initial setup.
    SUPERADMIN_BOOTSTRAP_EMAIL = os.environ.get("SUPERADMIN_BOOTSTRAP_EMAIL")
    SUPERADMIN_BOOTSTRAP_PASSWORD = os.environ.get("SUPERADMIN_BOOTSTRAP_PASSWORD")

    # Base URL this app is served at, used to build OAuth redirect URIs.
    APP_BASE_URL = os.environ.get("APP_BASE_URL", "http://localhost:5173")
    API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:5000")

    # Phase 9 integrations -- all optional. None of these are set in this
    # dev sandbox; every integration must check *_configured() and report
    # plainly rather than fabricate a connection/charge when they're unset.
    MICROSOFT_CLIENT_ID = os.environ.get("MICROSOFT_CLIENT_ID")
    MICROSOFT_CLIENT_SECRET = os.environ.get("MICROSOFT_CLIENT_SECRET")
    MICROSOFT_TENANT = os.environ.get("MICROSOFT_TENANT", "common")

    GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID")
    GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET")

    AUTHORIZE_NET_API_LOGIN_ID = os.environ.get("AUTHORIZE_NET_API_LOGIN_ID")
    AUTHORIZE_NET_TRANSACTION_KEY = os.environ.get("AUTHORIZE_NET_TRANSACTION_KEY")
    AUTHORIZE_NET_PUBLIC_CLIENT_KEY = os.environ.get("AUTHORIZE_NET_PUBLIC_CLIENT_KEY")
    AUTHORIZE_NET_SIGNATURE_KEY = os.environ.get("AUTHORIZE_NET_SIGNATURE_KEY")


class DevelopmentConfig(Config):
    DEBUG = True


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "TEST_DATABASE_URL",
        "postgresql+psycopg2://acctsys:acctsys_dev_pw@localhost:5432/acctsys_test",
    )


class ProductionConfig(Config):
    DEBUG = False


config_by_name = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}
