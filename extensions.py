import logging
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from sqlalchemy.exc import OperationalError

# Instantiate extensions without app object
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()

# Configure logging
logger = logging.getLogger(__name__)

# Helper function to verify database connection
def verify_db_connection():
    """Verify that the database connection is working.
    
    Returns:
        tuple: (bool, str) - Success flag and error message if any
    """
    try:
        # Simple query to test connection
        db.session.execute("SELECT 1")
        db.session.commit()
        return True, ""
    except OperationalError as e:
        logger.error(f"Database connection error: {e}")
        # Try to recover the session
        db.session.rollback()
        return False, str(e)
    except Exception as e:
        logger.error(f"Unexpected database error: {e}")
        db.session.rollback()
        return False, str(e)
