"""Shared Flask extension instances.

Kept in their own module to avoid circular imports between
the app factory, the models and the services.
"""
from flask_apscheduler import APScheduler
from flask_caching import Cache
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
login_manager = LoginManager()
cache = Cache()          # in-memory data cache (SimpleCache)
scheduler = APScheduler()  # background prefetch job
