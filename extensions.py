from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager

# Instantiate extensions without app object
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
