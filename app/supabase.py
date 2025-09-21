"""Supabase client wrapper.

This module provides a safe, lazy initializer for the Supabase Python client.
If the client library is not installed or SUPABASE_URL/KEY are not configured,
it will expose `client = None` and log a warning. This keeps the app usable
without a hard dependency.
"""
from flask import current_app
import logging

client = None


def init_supabase(app=None):
    global client
    if app is None:
        from flask import current_app as _ca
        app = _ca

    url = app.config.get('SUPABASE_URL')
    key = app.config.get('SUPABASE_KEY')
    if not url or not key:
        app.logger.debug('Supabase not configured (SUPABASE_URL/SUPABASE_KEY missing)')
        client = None
        return None

    try:
        # Lazy import to avoid hard dependency for projects that don't use Supabase
        from supabase import create_client
        client = create_client(url, key)
        app.logger.info('Supabase client initialized')
        return client
    except Exception as e:
        app.logger.warning('Failed to initialize Supabase client: %s', str(e))
        client = None
        return None
