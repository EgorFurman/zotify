"""
Headless OAuth module for Zotify.
Provides Python API for server-side authentication without browser interaction.
"""

import base64
import hashlib
import json
import os
import secrets
from pathlib import Path
from urllib.parse import urlencode

import requests

from zotify.const import SCOPES


class ZotifyAuth:
    """
    Handles headless OAuth authentication for Zotify.
    
    Usage:
        # Generate OAuth URL
        auth = ZotifyAuth(
            client_id='your_client_id',
            redirect_uri='https://mybot.com/callback'
        )
        oauth_url = auth.get_auth_url()
        code_verifier = auth.code_verifier  # Save this!
        
        # After receiving the authorization code
        credentials = auth.exchange_code(code='AQD...', code_verifier=code_verifier)
        credentials.save('/path/to/credentials.json')
        
        # With proxy support
        auth = ZotifyAuth(
            client_id='your_client_id',
            redirect_uri='https://mybot.com/callback',
            proxy='http://user:pass@host:port'
        )
    """
    
    TOKEN_URL = "https://accounts.spotify.com/api/token"
    AUTH_URL = "https://accounts.spotify.com/authorize"
    USER_URL = "https://api.spotify.com/v1/me"
    
    def __init__(self, client_id: str, redirect_uri: str, proxy: str = None):
        self.client_id = client_id
        self.redirect_uri = redirect_uri
        self.code_verifier = None
        self._code_challenge = None
        
        # Proxy support: explicit param or environment variables
        self.proxies = None
        if proxy:
            self.proxies = {"http": proxy, "https": proxy}
        elif os.getenv('HTTPS_PROXY'):
            self.proxies = {
                "http": os.getenv('HTTP_PROXY'),
                "https": os.getenv('HTTPS_PROXY')
            }
    
    def _generate_pkce(self) -> tuple[str, str]:
        """Generate PKCE code_verifier and code_challenge."""
        # Generate code_verifier (43-128 characters)
        code_verifier = secrets.token_urlsafe(64)
        
        # Generate code_challenge from code_verifier using S256
        code_challenge = base64.urlsafe_b64encode(
            hashlib.sha256(code_verifier.encode()).digest()
        ).decode().rstrip('=')
        
        return code_verifier, code_challenge
    
    def get_auth_url(self) -> str:
        """
        Generate OAuth authorization URL.
        Also generates and stores code_verifier for later use.
        
        Returns:
            str: The OAuth authorization URL to redirect user to
        """
        self.code_verifier, self._code_challenge = self._generate_pkce()
        
        params = {
            'client_id': self.client_id,
            'response_type': 'code',
            'redirect_uri': self.redirect_uri,
            'code_challenge_method': 'S256',
            'code_challenge': self._code_challenge,
            'scope': ' '.join(SCOPES)
        }
        
        return f"{self.AUTH_URL}?{urlencode(params)}"
    
    def exchange_code(self, code: str, code_verifier: str = None) -> 'ZotifyCredentials':
        """
        Exchange authorization code for access token.
        
        Args:
            code: The authorization code received from Spotify callback
            code_verifier: The PKCE code_verifier (uses stored one if not provided)
        
        Returns:
            ZotifyCredentials: Credentials object that can be saved and used
        """
        verifier = code_verifier or self.code_verifier
        if not verifier:
            raise ValueError("code_verifier is required. Either pass it or call get_auth_url() first.")
        
        data = {
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': self.redirect_uri,
            'client_id': self.client_id,
            'code_verifier': verifier
        }
        
        response = requests.post(self.TOKEN_URL, data=data, proxies=self.proxies, timeout=30)
        token_data = response.json()
        
        if 'error' in token_data:
            raise AuthenticationError(
                f"Token exchange failed: {token_data.get('error_description', token_data['error'])}"
            )
        
        # Get user info
        headers = {'Authorization': f'Bearer {token_data["access_token"]}'}
        user_response = requests.get(self.USER_URL, headers=headers, proxies=self.proxies, timeout=30)
        user_data = user_response.json()
        
        return ZotifyCredentials(
            username=user_data.get('id', user_data.get('email', 'unknown')),
            access_token=token_data['access_token'],
            refresh_token=token_data.get('refresh_token'),
            expires_in=token_data.get('expires_in', 3600)
        )


class ZotifyCredentials:
    """Stores and manages Zotify credentials."""
    
    def __init__(self, username: str, access_token: str, refresh_token: str = None, expires_in: int = 3600):
        self.username = username
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.expires_in = expires_in
    
    def save(self, path: str) -> None:
        """
        Save credentials to a JSON file compatible with Zotify/librespot.
        
        Args:
            path: Path to save the credentials file
        """
        credentials_path = Path(path)
        credentials_path.parent.mkdir(parents=True, exist_ok=True)
        
        # ВАЖНО: access_token должен быть в base64!
        # librespot делает base64.b64decode(credentials) при чтении
        credentials_b64 = base64.b64encode(self.access_token.encode()).decode()
        
        creds_data = {
            "username": self.username,
            "credentials": credentials_b64,
            "type": "AUTHENTICATION_SPOTIFY_TOKEN"
        }
        
        with open(credentials_path, 'w') as f:
            json.dump(creds_data, f)
    
    @classmethod
    def load(cls, path: str) -> 'ZotifyCredentials':
        """
        Load credentials from a JSON file.
        Supports current format (credentials in base64) and legacy format.
        
        Args:
            path: Path to the credentials file
        
        Returns:
            ZotifyCredentials: Loaded credentials object
        """
        with open(path, 'r') as f:
            data = json.load(f)
        
        # Current format: username, credentials (base64), type
        if 'username' in data and 'credentials' in data and 'type' in data:
            # Decode base64 credentials
            access_token = base64.b64decode(data['credentials']).decode()
            return cls(
                username=data.get('username', 'unknown'),
                access_token=access_token
            )
        
        # Legacy format: base64 wrapped entire object
        if 'credentials' in data and 'username' not in data:
            decoded = json.loads(base64.b64decode(data['credentials']).decode('ascii'))
            return cls(
                username=decoded.get('username', 'unknown'),
                access_token=decoded.get('credentials', '')
            )
        
        raise ValueError("Invalid credentials file format")
    
    def to_dict(self) -> dict:
        """Convert credentials to dictionary."""
        return {
            'username': self.username,
            'access_token': self.access_token,
            'refresh_token': self.refresh_token,
            'expires_in': self.expires_in
        }


class AuthenticationError(Exception):
    """Raised when authentication fails."""
    pass


def generate_auth_url(client_id: str, redirect_uri: str) -> tuple[str, str]:
    """
    Convenience function to generate OAuth URL and code_verifier.
    
    Args:
        client_id: Spotify application client ID
        redirect_uri: Redirect URI configured in Spotify app
    
    Returns:
        tuple: (oauth_url, code_verifier)
    """
    auth = ZotifyAuth(client_id, redirect_uri)
    oauth_url = auth.get_auth_url()
    return oauth_url, auth.code_verifier


def exchange_code_for_credentials(
    client_id: str,
    redirect_uri: str,
    code: str,
    code_verifier: str
) -> ZotifyCredentials:
    """
    Convenience function to exchange authorization code for credentials.
    
    Args:
        client_id: Spotify application client ID
        redirect_uri: Redirect URI configured in Spotify app
        code: Authorization code from Spotify callback
        code_verifier: PKCE code_verifier from generate_auth_url()
    
    Returns:
        ZotifyCredentials: Credentials object
    """
    auth = ZotifyAuth(client_id, redirect_uri)
    return auth.exchange_code(code, code_verifier)
