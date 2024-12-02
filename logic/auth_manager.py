from dataclasses import dataclass
from datetime import datetime
import json
import uuid
import logging
from pathlib import Path
from typing import Optional, Dict, Any
import httplib2
from oauth2client.client import OAuth2WebServerFlow

logger = logging.getLogger(__name__)

@dataclass
class SessionData:
    email: str
    name: str
    picture: str
    session_token: str
    created_at: datetime

class AuthenticationManager:
    def __init__(self, storage_path: str = 'data.json'):
        self.storage_path = Path(storage_path)
        self.persistent_data: Dict[str, Dict] = self._load_storage()
        self.sessions: Dict[str, SessionData] = {}

    def _load_storage(self) -> Dict[str, Dict]:
        try:
            if self.storage_path.exists():
                with open(self.storage_path, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Error loading storage: {e}")
        return {"users": {}, "search_history": {}}

    def _save_storage(self) -> None:
        try:
            with open(self.storage_path, 'w') as f:
                json.dump(self.persistent_data, f)
        except Exception as e:
            logger.error(f"Error saving storage: {e}")

    def process_oauth_callback(self, code: str, flow: OAuth2WebServerFlow) -> Optional[SessionData]:
        try:
            credentials = flow.step2_exchange(code)
            user_email = credentials.id_token['email']

            user_data = {
                "name": credentials.id_token.get('name', 'Unknown'),
                "picture": credentials.id_token.get('picture', ''),
                "refresh_token": credentials.refresh_token or
                                 self.persistent_data["users"].get(user_email, {}).get("refresh_token"),
                "credentials": credentials.to_json()
            }

            self.persistent_data["users"][user_email] = user_data
            if user_email not in self.persistent_data["search_history"]:
                self.persistent_data["search_history"][user_email] = []

            self._save_storage()
            return self.create_session(user_email, user_data)

        except Exception as e:
            logger.error(f"Error in OAuth callback: {e}")
            return None

    def create_session(self, email: str, user_data: Dict[str, Any]) -> SessionData:
        session_data = SessionData(
            email=email,
            name=user_data["name"],
            picture=user_data["picture"],
            session_token=str(uuid.uuid4()),
            created_at=datetime.now()
        )
        self.sessions[session_data.session_token] = session_data
        return session_data

    def validate_session(self, session_token: str) -> Optional[SessionData]:
        return self.sessions.get(session_token)

    def end_session(self, session_token: str) -> None:
        if session_token in self.sessions:
            del self.sessions[session_token]