#!/usr/bin/env python3
"""
Script to generate secret keys for the application.
Run this script and copy the output to your .env file.
"""

import secrets


def generate_secret_key():
    """Generate a 32-byte hex secret key."""
    return secrets.token_hex(32)


if __name__ == '__main__':
    print("=== Pro Project Secret Key Generator ===")
    print()
    print("Copy these values to your .env file:")
    print()
    print(f"SECRET_KEY={generate_secret_key()}")
    print(f"SECURITY_PASSWORD_SALT={generate_secret_key()}")
    print()
    print("=== Important ===")
    print("- Never commit these secrets to version control")
    print("- Use different secrets for production")
    print("- Store production secrets in a secure secret manager")