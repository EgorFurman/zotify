__version__ = "0.9.32"

# Headless OAuth API
from zotify.headless_auth import (
    ZotifyAuth,
    ZotifyCredentials,
    AuthenticationError,
    generate_auth_url,
    exchange_code_for_credentials
)

__all__ = [
    '__version__',
    'ZotifyAuth',
    'ZotifyCredentials', 
    'AuthenticationError',
    'generate_auth_url',
    'exchange_code_for_credentials'
]
