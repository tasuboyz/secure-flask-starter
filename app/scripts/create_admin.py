#!/usr/bin/env python3
"""
Script to create admin user.
"""

import sys
import os
from getpass import getpass

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app import create_app
from app.models import User
from app.extensions import db


def create_admin_user():
    """Create admin user interactively."""
    app = create_app()
    
    with app.app_context():
        print("=== Creazione Utente Admin ===")
        
        email = input("Email admin: ").strip().lower()
        if not email:
            print("Errore: Email richiesta")
            return
        
        # Check if user already exists
        if User.query.filter_by(email=email).first():
            print(f"Errore: Utente con email {email} già esiste")
            return
        
        password = getpass("Password admin: ")
        if len(password) < 8:
            print("Errore: Password deve essere di almeno 8 caratteri")
            return
        
        password2 = getpass("Conferma password: ")
        if password != password2:
            print("Errore: Le password non corrispondono")
            return
        
        # Create admin user
        admin = User(email=email, is_admin=True)
        admin.set_password(password)
        
        db.session.add(admin)
        db.session.commit()
        
        print(f"✅ Utente admin '{email}' creato con successo!")


if __name__ == '__main__':
    create_admin_user()