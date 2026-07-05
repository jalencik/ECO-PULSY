"""Shared Flask extension instances.

Kept in their own module to avoid circular imports between
the app factory and the models.
"""
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
login_manager = LoginManager()
