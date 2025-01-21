from dataclasses import dataclass
from typing import List, Optional
from functools import lru_cache
import os
from dotenv import load_dotenv
from google.cloud import secretmanager
from firebase_admin import functions

@dataclass
class ConfigVars:
    """Data class to hold configuration variables"""
    supabase_url: str
    storage_bucketurl: str
    supabase_anon_key: str
    supabase_service_key: str
    youtube_api_key: str
    openai_api_key: str
    youtube_client_id: str
    youtube_client_key: str

class Config:
    """Configuration manager for both development and production environments"""
    
    # Define configuration keys
    CONFIG_VARS = {
        'supabase_url': ('SUPABASE_URL', 'supabase.url'),
        'storage_bucketurl': ('STORAGE_BUCKETURL', 'storage.bucketurl'),
        'youtube_client_id': ('YOUTUBE_CLIENT_ID', 'youtube.client.id'),
    }
    
    SECRET_KEYS = [
        'SUPABASE_ANON_KEY',
        'SUPABASE_SERVICE_KEY',
        'YOUTUBE_API_KEY',
        'OPENAI_API_KEY',
        'YOUTUBE_CLIENT_KEY'
    ]

    def __init__(self):
        """Initialize configuration based on environment"""
        # Explicitly define all attributes for better IDE support
        self.environment: str = self._get_environment()
        
        # Config variables
        self.supabase_url: str
        self.storage_bucketurl: str
        self.youtube_client_id: str
        
        # Secret keys
        self.supabase_anon_key: str
        self.supabase_service_key: str
        self.youtube_api_key: str
        self.openai_api_key: str
        self.youtube_client_key: str
        
        # Load the actual configuration
        self._load_environment()
        self._initialize_config()

    @staticmethod
    def _get_environment() -> str:
        """Get the current environment with a default of 'development'"""
        return os.getenv('ENVIRONMENT', 'development')

    def _load_environment(self) -> None:
        """Load environment variables based on environment type"""
        if not self.is_production:
            load_dotenv()

    def _initialize_config(self) -> None:
        """Initialize configuration based on environment"""
        config_loader = self._load_production_config if self.is_production else self._load_local_config
        config_vars = config_loader()
        # Set all configuration variables as instance attributes
        for key, value in config_vars.__dict__.items():
            setattr(self, key, value)

    def _load_local_config(self) -> ConfigVars:
        """Load configuration from .env file"""
        print(f"Loading local config")
        config_dict = {}
        
        # Load regular config vars
        for attr_name, (env_key, _) in self.CONFIG_VARS.items():
            config_dict[attr_name] = self._get_env_var(env_key)

        # Load secrets
        for secret_key in self.SECRET_KEYS:
            attr_name = secret_key.lower()
            config_dict[attr_name] = self._get_env_var(secret_key)
        
        # Use local supabase
        config_dict['supabase_url'] = 'http://127.0.0.1:54321'
        config_dict['supabase_anon_key'] = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZS1kZW1vIiwicm9sZSI6ImFub24iLCJleHAiOjE5ODM4MTI5OTZ9.CRXP1A7WOeoJeXxjNni43kdQwgnWNReilDMblYTn_I0'
        config_dict['supabase_service_key'] = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZS1kZW1vIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImV4cCI6MTk4MzgxMjk5Nn0.EGIM96RAZx35lJzdJsyH-qQwv8Hdp7fsn3W0YpN81IU'

        print(f">>>>>>  Config dict: {config_dict}")
        return ConfigVars(**config_dict)

    def _load_production_config(self) -> ConfigVars:
        """Load configuration from Firebase config and secrets"""
        config = functions.config()
        config_dict = {}
        
        # Load regular config vars
        for attr_name, (_, firebase_key) in self.CONFIG_VARS.items():
            config_dict[attr_name] = config[firebase_key]

        # Load secrets
        self._load_firebase_secrets(config_dict)

        return ConfigVars(**config_dict)

    def _load_firebase_secrets(self, config_dict: dict) -> None:
        """Load secrets from Firebase secrets manager"""
        for secret_key in self.SECRET_KEYS:
            attr_name = secret_key.lower()
            try:
                value = self._get_firebase_secret(secret_key)
                config_dict[attr_name] = value
            except Exception as e:
                self._handle_secret_error(secret_key, e)
                config_dict[attr_name] = None

    @staticmethod
    def _get_env_var(key: str) -> str:
        """Get environment variable with error handling"""
        value = os.getenv(key)
        if value is None:
            raise ValueError(f"Environment variable {key} not found")
        return value
    
    @staticmethod
    def _get_firebase_secret(key: str) -> str:
        """Get Firebase secret with error handling"""
        client = secretmanager.SecretManagerServiceClient()
        # The GCP_PROJECT environment variable is automatically set by Firebase
        name = f"projects/{os.environ.get('GCP_PROJECT')}/secrets/{key}/versions/latest"
        response = client.access_secret_version(request={"name": name})
        value = response.payload.data.decode("UTF-8")
        if value is None:
            raise ValueError(f"Firebase secret {key} not found")
        return value

    @staticmethod
    def _handle_secret_error(key: str, error: Exception) -> None:
        """Handle errors when loading secrets"""
        print(f"Error loading secret {key}: {str(error)}")

    @property
    def is_production(self) -> bool:
        """Check if running in production environment"""
        return self.environment != 'development'

    def __repr__(self) -> str:
        """String representation of Config instance"""
        env_type = "Production" if self.is_production else "Development"
        return f"<Config: {env_type} Environment>"

@lru_cache()
def get_config() -> Config:
    """Get or create singleton Config instance"""
    c = Config()
    print(f"Config: {c}")
    print(f"Database url: {c.supabase_url}")
    return c

# Export singleton instance
config = get_config()

"""
Configuration Management System
-----------------------------

This module provides a unified configuration management system that works across both
development and production environments. It handles both regular configuration variables
and secrets, with different loading mechanisms for each environment.

Usage:
------
    from utils.config import config
    
    # Access configuration values
    supabase_url = config.supabase_url
    api_key = config.openai_api_key

Adding New Configuration Variables:
--------------------------------
1. Regular Config Variables:
   a. Add a new entry to CONFIG_VARS dictionary:
      CONFIG_VARS = {
          'new_variable': ('ENV_VAR_NAME', 'firebase.config.path'),
          ...
      }
   b. Add the type hint in __init__
   c. Add the field to ConfigVars dataclass

2. Secret Variables:
   a. Add the secret name to SECRET_KEYS list:
      SECRET_KEYS = [
          'NEW_SECRET_NAME',
          ...
      ]
   b. Add the type hint in __init__
   c. Add the field to ConfigVars dataclass

Environment Setup:
----------------
1. Development:
   - Add variables to .env file:
     ENVIRONMENT=development
     ENV_VAR_NAME=value
     NEW_SECRET_NAME=secret_value

2. Production:
   - Regular configs: Set using Firebase config:
     firebase functions:config:set firebase.config.path="value"
   - Secrets: Add to Google Cloud Secret Manager:
     gcloud secrets create NEW_SECRET_NAME --replication-policy="automatic"
     echo -n "secret_value" | gcloud secrets versions add NEW_SECRET_NAME --data-file=-
"""
