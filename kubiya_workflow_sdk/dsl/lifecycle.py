"""Lifecycle handlers and notifications."""

from typing import Dict, Any, Optional


class HandlerOn:
    """Lifecycle handlers."""

    def __init__(
        self,
        success: Optional[str] = None,
        failure: Optional[str] = None,
        exit: Optional[str] = None,
        cancel: Optional[str] = None,
    ):
        self.handlers = {}
        if success:
            self.handlers["success"] = {"command": success}
        if failure:
            self.handlers["failure"] = {"command": failure}
        if exit:
            self.handlers["exit"] = {"command": exit}
        if cancel:
            self.handlers["cancel"] = {"command": cancel}


class MailOn:
    """Email notification settings."""

    def __init__(self, failure: bool = True, success: bool = False):
        self.settings = {"failure": failure, "success": success}


class Notifications:
    """Notification configuration."""

    def __init__(self, mail_on: Optional[MailOn] = None, smtp: Optional[Dict[str, str]] = None):
        self.mail_on = mail_on or MailOn()
        self.smtp = smtp
