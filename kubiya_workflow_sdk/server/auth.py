"""
Authentication handlers for Kubiya Workflow SDK Server.

Supports:
- UserKey header for API keys
- Bearer token for JWT tokens
- Optional authentication (no persistent key required)
"""

from fastapi import HTTPException, Request, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional, Union
import logging

logger = logging.getLogger(__name__)


class KubiyaAuth:
    """Authentication handler for Kubiya API."""
    
    def __init__(self, require_auth: bool = False):
        self.require_auth = require_auth
        self.bearer_scheme = HTTPBearer(auto_error=False)
    
    async def __call__(
        self, 
        request: Request,
        bearer_credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False))
    ) -> Optional[str]:
        """Extract authentication token from request."""
        
        # Check UserKey header first (API key)
        user_key = request.headers.get("UserKey")
        if user_key:
            logger.debug("Found UserKey header")
            return user_key
        
        # Check Bearer token (JWT)
        if bearer_credentials:
            logger.debug("Found Bearer token")
            return bearer_credentials.credentials
        
        # No authentication provided
        if self.require_auth:
            raise HTTPException(
                status_code=401,
                detail="Authentication required. Provide either UserKey header or Bearer token.",
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        logger.debug("No authentication provided, proceeding without token")
        return None


# Default auth dependency (optional auth)
auth = KubiyaAuth(require_auth=False)

# Required auth dependency
auth_required = KubiyaAuth(require_auth=True) 