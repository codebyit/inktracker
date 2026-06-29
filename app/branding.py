"""Branding configuration. Public defaults are sanitized; Prod overrides via env.

Set APP_NAME / APP_OWNER in the environment to rebrand without code changes.
Social handle and Ko-fi link are intentionally hardcoded in templates.
"""
import os

APP_NAME = os.getenv("APP_NAME", "InkTrack")
APP_OWNER = os.getenv("APP_OWNER", "")
APP_TITLE = f"{APP_NAME} — {APP_OWNER}" if APP_OWNER else APP_NAME
