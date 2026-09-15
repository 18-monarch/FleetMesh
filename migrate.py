"""Apply the versioned cloud schema using a direct PostgreSQL connection."""
import os
from cloud_storage import CloudDatabase

if __name__ == '__main__':
    url = os.environ.get('DATABASE_URL_UNPOOLED') or os.environ.get('DATABASE_URL')
    if not url:
        raise SystemExit('DATABASE_URL_UNPOOLED or DATABASE_URL is required')
    db = CloudDatabase(url=url)
    try:
        db.migrate()
        print('FleetMesh schema version 1 applied successfully.')
    except Exception:
        raise SystemExit('Migration failed; connection details redacted. Verify credentials and database availability.')
    finally:
        db.close()
