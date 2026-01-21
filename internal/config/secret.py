from dotenv import load_dotenv
from enum import Enum
import os
import json


load_dotenv()

class Environment(Enum):
    LOCAL = "local"
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"

    @property
    def is_local(self):
        return self in {Environment.LOCAL, Environment.DEVELOPMENT}

    @classmethod
    def from_string(cls, env_str: str):
        try:
            return cls[env_str.upper()]
        except KeyError:
            raise ValueError(f"Unknown environment: {env_str}")



class SecretManager:

    PORT : str = os.environ.get("PORT", "8000")
    ENV : Environment = Environment.from_string(os.environ.get("ENV", "local"))
    GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
    PG_URI : str =  os.environ.get("PG_URI")
    ALLOWED_ORIGINS = json.loads(os.environ.get("ALLOWED_ORIGINS", '["*"]'))
    OPENAI_KEY  :  str | None  = os.environ.get("OPENAI_KEY")
    GOOGLE_CSE_ID = os.environ.get("GOOGLE_CSE_ID", "")