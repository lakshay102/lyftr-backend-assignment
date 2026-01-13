import os


class Config:
    """Configuration loaded from environment variables."""
    
    def __init__(self):
        # DATABASE_URL is required
        self.DATABASE_URL = os.getenv("DATABASE_URL")
        if not self.DATABASE_URL:
            raise ValueError("DATABASE_URL environment variable is required")
        
        # WEBHOOK_SECRET - store even if empty/missing
        self.WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "")
        
        # LOG_LEVEL is optional with default
        self.LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    
    def is_webhook_secret_valid(self) -> bool:
        """Check if WEBHOOK_SECRET is present and non-empty."""
        return bool(self.WEBHOOK_SECRET)


# Global config instance
config = Config()
