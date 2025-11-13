"""
Routes package for the Energy Monitoring API
Imports all route blueprints to be registered in the app
"""

from . import dashboard
from . import plants
from . import analytics
from . import regions
from . import alerts
from . import db_admin

__all__ = [
    'dashboard',
    'plants',
    'analytics',
    'regions',
    'alerts'
    , 'db_admin'
]
