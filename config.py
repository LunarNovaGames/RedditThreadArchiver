"""
Configuration - Handle credentials and settings.
"""

import os
from typing import Optional
from dotenv import load_dotenv


# Load .env file if present
load_dotenv()


class Config:
    """Configuration container for Reddit API credentials."""
    
    DEFAULT_USER_AGENT = "RedditThreadArchiver/1.0.0 (by /u/your_username)"
    
    def __init__(
        self,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        user_agent: Optional[str] = None
    ):
        """
        Initialize configuration.
        
        Credentials can be passed directly or loaded from environment variables.
        
        Args:
            client_id: Reddit API client ID
            client_secret: Reddit API client secret
            username: Reddit username
            password: Reddit password
            user_agent: Custom user agent string
        """
        self.client_id = client_id or os.getenv("REDDIT_CLIENT_ID")
        self.client_secret = client_secret or os.getenv("REDDIT_CLIENT_SECRET")
        self.username = username or os.getenv("REDDIT_USERNAME")
        self.password = password or os.getenv("REDDIT_PASSWORD")
        self.user_agent = user_agent or os.getenv("REDDIT_USER_AGENT", self.DEFAULT_USER_AGENT)
        
        self._validate()
    
    def _validate(self):
        """Validate that all required credentials are present."""
        missing = []
        
        if not self.client_id:
            missing.append("REDDIT_CLIENT_ID")
        if not self.client_secret:
            missing.append("REDDIT_CLIENT_SECRET")
        if not self.username:
            missing.append("REDDIT_USERNAME")
        if not self.password:
            missing.append("REDDIT_PASSWORD")
        
        if missing:
            raise ValueError(
                f"Missing required credentials: {', '.join(missing)}. "
                "Set them as environment variables or pass them directly."
            )
    
    def __repr__(self) -> str:
        return (
            f"Config(client_id={self.client_id[:8]}..., "
            f"username={self.username}, "
            f"user_agent={self.user_agent})"
        )
