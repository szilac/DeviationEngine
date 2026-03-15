"""
API router modules for Deviation Engine.

This package contains all API endpoint routers organized by domain.
"""

# Migrated routers
from app.api import health  # ✅ Migrated (2 endpoints)
from app.api import historical  # ✅ Migrated (3 endpoints)
from app.api import translation  # ✅ Migrated (5 endpoints)

# Router modules will be imported here after migration
# from app.api import settings, import_export, images, audio, skeletons, timelines
