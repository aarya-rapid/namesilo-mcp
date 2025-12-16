from __future__ import annotations

import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass
class ServerSettings:
    host: str = os.getenv("HOST", "0.0.0.0")
    port: int = int(os.getenv("PORT", "8000"))


@dataclass
class NameSiloSettings:
    api_key: str = os.getenv("NAMESILO_API_KEY", "")
    base_url: str = os.getenv("NAMESILO_BASE_URL", "https://www.namesilo.com/api/")

    def validate(self) -> None:
        if not self.api_key:
            raise RuntimeError("NAMESILO_API_KEY is not set")


server_settings = ServerSettings()
namesilo_settings = NameSiloSettings()
namesilo_settings.validate()
