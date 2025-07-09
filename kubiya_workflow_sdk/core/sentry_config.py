"""
Sentry configuration and initialization for the Kubiya Workflow SDK.

This module provides optional Sentry integration for error tracking and performance monitoring.
Sentry is enabled via environment variables and is completely optional.
"""

import os
import logging
from typing import Optional, Dict, Any, List
from kubiya_workflow_sdk.core.constants import (
    ENV_VARS,
    SENTRY_DEFAULT_TRACES_SAMPLE_RATE,
    SENTRY_DEFAULT_PROFILES_SAMPLE_RATE,
    SENTRY_DEFAULT_ENVIRONMENT,
)
from ..__version__ import __version__

logger = logging.getLogger(__name__)

# Global flag to track if Sentry is initialized
_sentry_initialized = False


def is_sentry_enabled() -> bool:
    """Check if Sentry is enabled via environment variables."""
    return os.getenv(ENV_VARS["SENTRY_ENABLED"], "false").lower() in ("true", "1", "yes", "on")


def get_sentry_dsn() -> Optional[str]:
    """Get Sentry DSN from environment variables."""
    return os.getenv(ENV_VARS["SENTRY_DSN"])


def get_sentry_environment() -> str:
    """Get Sentry environment from environment variables."""
    return os.getenv(ENV_VARS["SENTRY_ENVIRONMENT"], SENTRY_DEFAULT_ENVIRONMENT)


def get_sentry_release() -> Optional[str]:
    """Get Sentry release from environment variables or package version."""
    release = os.getenv(ENV_VARS["SENTRY_RELEASE"])
    if release:
        return release
    
    # Use package version as release if not explicitly set
    return f"kubiya-workflow-sdk@{__version__}"


def get_sentry_config() -> Dict[str, Any]:
    """Get complete Sentry configuration from environment variables."""
    config = {
        "dsn": get_sentry_dsn(),
        "environment": get_sentry_environment(),
        "release": get_sentry_release(),
        "traces_sample_rate": float(os.getenv("KUBIYA_SENTRY_TRACES_SAMPLE_RATE", str(SENTRY_DEFAULT_TRACES_SAMPLE_RATE))),
        "profiles_sample_rate": float(os.getenv("KUBIYA_SENTRY_PROFILES_SAMPLE_RATE", str(SENTRY_DEFAULT_PROFILES_SAMPLE_RATE))),
        "attach_stacktrace": True,
        "send_default_pii": False,
        "max_breadcrumbs": 50,
        "debug": os.getenv("KUBIYA_SENTRY_DEBUG", "false").lower() in ("true", "1", "yes", "on"),
    }
    
    return config


def get_sentry_tags() -> Dict[str, str]:
    """Get tags to be set after Sentry initialization."""
    return {
        "component": "kubiya-workflow-sdk",
        "environment": get_sentry_environment(),
    }


def setup_sentry_integrations() -> List[Any]:
    """Setup Sentry integrations based on available packages."""
    integrations = []
    
    try:
        import sentry_sdk
        from sentry_sdk.integrations.logging import LoggingIntegration
        from sentry_sdk.integrations.stdlib import StdlibIntegration
        from sentry_sdk.integrations.excepthook import ExcepthookIntegration
        from sentry_sdk.integrations.dedupe import DedupeIntegration
        from sentry_sdk.integrations.atexit import AtexitIntegration
        from sentry_sdk.integrations.modules import ModulesIntegration
        from sentry_sdk.integrations.argv import ArgvIntegration
        from sentry_sdk.integrations.threading import ThreadingIntegration
        
        # Core integrations
        integrations.extend([
            LoggingIntegration(
                level=logging.INFO,        # Capture info and above as breadcrumbs
                event_level=logging.ERROR  # Send errors as events
            ),
            StdlibIntegration(),
            ExcepthookIntegration(always_run=True),
            DedupeIntegration(),
            AtexitIntegration(),
            ModulesIntegration(),
            ArgvIntegration(),
            ThreadingIntegration(propagate_hub=True),
        ])
        
        # Optional integrations - each wrapped in individual try/except
        # HTTP client integrations
        try:
            from sentry_sdk.integrations.httpx import HttpxIntegration
            integrations.append(HttpxIntegration())
        except (ImportError, Exception) as e:
            logger.debug(f"HTTPX integration not available: {e}")
        
        # Async integrations
        try:
            from sentry_sdk.integrations.asyncio import AsyncioIntegration
            integrations.append(AsyncioIntegration())
        except (ImportError, Exception) as e:
            logger.debug(f"Asyncio integration not available: {e}")
        
        # FastAPI integration - temporarily disabled due to initialization issues
        try:
            import fastapi  # Check if FastAPI is installed
            from sentry_sdk.integrations.fastapi import FastApiIntegration
            integrations.append(FastApiIntegration())
            logger.debug("FastAPI integration added successfully")
        except (ImportError, Exception) as e:
            logger.debug(f"FastAPI integration not available: {e}")
        
    except ImportError:
        logger.debug("Sentry SDK not available, skipping integration setup")
    except Exception as e:
        logger.warning(f"Error setting up Sentry integrations: {e}")
    
    return integrations


def initialize_sentry(
    dsn: Optional[str] = None,
    environment: Optional[str] = None,
    release: Optional[str] = None,
    enabled: Optional[bool] = None,
    **kwargs
) -> bool:
    """
    Initialize Sentry with optional configuration override.
    
    Args:
        dsn: Sentry DSN (overrides environment)
        environment: Environment name (overrides environment)
        release: Release version (overrides environment)
        enabled: Force enable/disable (overrides environment)
        **kwargs: Additional Sentry configuration
    
    Returns:
        True if Sentry was successfully initialized, False otherwise
    """
    global _sentry_initialized
    
    if _sentry_initialized:
        logger.debug("Sentry already initialized, skipping")
        return True
    
    # Check if Sentry is enabled
    if enabled is None:
        enabled = is_sentry_enabled()
    
    if not enabled:
        logger.debug("Sentry integration is disabled")
        return False
    
    # Get DSN
    if dsn is None:
        dsn = get_sentry_dsn()
    
    if not dsn:
        logger.warning("Sentry is enabled but no DSN provided")
        return False
    
    try:
        import sentry_sdk
        
        # Get base configuration
        config = get_sentry_config()
        
        # Override with parameters
        if dsn:
            config["dsn"] = dsn
        if environment:
            config["environment"] = environment
        if release:
            config["release"] = release
        
        # Apply additional kwargs
        config.update(kwargs)
        
        # Setup integrations
        config["integrations"] = setup_sentry_integrations()
        
        # Initialize Sentry
        sentry_sdk.init(**config)
        
        # Set tags after initialization
        tags = get_sentry_tags()
        if environment:
            tags["environment"] = environment
        
        for key, value in tags.items():
            sentry_sdk.set_tag(key, value)
        
        _sentry_initialized = True
        logger.info(f"Sentry initialized successfully for environment: {config['environment']}")
        
        # Set user context
        sentry_sdk.set_tag("sdk_version", __version__)
        sentry_sdk.set_context("runtime", {
            "name": "kubiya-workflow-sdk",
            "version": __version__,
        })
        
        return True
        
    except ImportError:
        logger.debug("Sentry SDK not available, skipping initialization")
        return False
    except Exception as e:
        logger.error(f"Failed to initialize Sentry: {e}")
        return False


def capture_exception(exception: Exception, **kwargs) -> Optional[str]:
    """
    Capture an exception to Sentry if initialized.
    
    Args:
        exception: The exception to capture
        **kwargs: Additional context
    
    Returns:
        Event ID if captured, None otherwise
    """
    if not _sentry_initialized:
        return None

    try:
        import sentry_sdk
        with sentry_sdk.isolation_scope() as scope:
            for key, value in kwargs.items():
                if isinstance(value, (str, int, float, bool)):
                    scope.set_extra(key, value)
                else:
                    scope.set_context(key, value)
            return sentry_sdk.capture_exception(exception)
    except ImportError:
        return None


def capture_message(message: str, level: str = "info", **kwargs) -> Optional[str]:
    """
    Capture a message to Sentry if initialized.
    
    Args:
        message: The message to capture
        level: Log level (debug, info, warning, error, fatal)
        **kwargs: Additional context
    
    Returns:
        Event ID if captured, None otherwise
    """
    if not _sentry_initialized:
        return None
    
    try:
        import sentry_sdk

        # Convert level to Sentry's expected literal types
        level_lower = level.lower()
        if level_lower == "debug":
            return sentry_sdk.capture_message(message, "debug", **kwargs)
        elif level_lower == "info":
            return sentry_sdk.capture_message(message, "info", **kwargs)
        elif level_lower == "warning":
            return sentry_sdk.capture_message(message, "warning", **kwargs)
        elif level_lower == "error":
            return sentry_sdk.capture_message(message, "error", **kwargs)
        elif level_lower in ("fatal", "critical"):
            return sentry_sdk.capture_message(message, "fatal", **kwargs)
        else:
            # Default to info for unknown levels
            return sentry_sdk.capture_message(message, "info", **kwargs)
    except ImportError:
        return None


def add_breadcrumb(crumb: Dict[str, Any], hint: Dict[str, Any], **kwargs) -> None:
    """
    Add a breadcrumb to Sentry if initialized.
    
    Args:
        crumb: Breadcrumb crumb
        hint: Breadcrumb hint
        **kwargs: Additional data
    """
    if not _sentry_initialized:
        return
    
    try:
        import sentry_sdk
        sentry_sdk.add_breadcrumb(
            crumb=crumb,
            hint=hint,
            **kwargs
        )
    except ImportError:
        pass


def set_workflow_context(workflow_id: str, workflow_name: str, **kwargs) -> None:
    """
    Set workflow context for Sentry if initialized.
    
    Args:
        workflow_id: Workflow execution ID
        workflow_name: Workflow name
        **kwargs: Additional workflow data
    """
    if not _sentry_initialized:
        return
    
    try:
        import sentry_sdk
        sentry_sdk.set_context("workflow", {
            "id": workflow_id,
            "name": workflow_name,
            **kwargs
        })
    except ImportError:
        pass


def is_initialized() -> bool:
    """Check if Sentry is initialized."""
    return _sentry_initialized


def shutdown_sentry() -> None:
    """Shutdown Sentry client."""
    global _sentry_initialized
    
    if not _sentry_initialized:
        return
    
    try:
        import sentry_sdk
        sentry_sdk.get_client().close()
        _sentry_initialized = False
        logger.info("Sentry client shut down successfully")
    except ImportError:
        pass
    except Exception as e:
        logger.error(f"Failed to shutdown Sentry client: {e}") 