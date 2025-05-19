import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from extensions import db

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    name = db.Column(db.String(100), nullable=True)
    bio = db.Column(db.Text, nullable=True) # Added bio field
    is_whitelisted = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    
    conversations = db.relationship('Conversation', backref='user', lazy=True, cascade="all, delete-orphan")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.email}>'

class Conversation(db.Model):
    __tablename__ = 'conversations'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False, default=lambda: f"Chat from {datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M')}")
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    filename = db.Column(db.String(255), nullable=False, unique=True) # Assumes ChatManager filenames are unique
    messages = db.relationship('Message', backref='conversation', lazy=True, cascade="all, delete-orphan")

    def __repr__(self):
        return f'<Conversation {self.id} by User {self.user_id}>'

class Message(db.Model):
    __tablename__ = 'messages'
    id = db.Column(db.Integer, primary_key=True)
    conv_id = db.Column(db.Integer, db.ForeignKey('conversations.id'), nullable=False)
    role = db.Column(db.String(20))  # 'user', 'assistant', 'system', 'tool'
    content = db.Column(db.Text, nullable=False)
    tool_call_id = db.Column(db.String(100), nullable=True) # For linking tool responses to calls
    tool_name = db.Column(db.String(100), nullable=True) # For identifying the tool used
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    def __repr__(self):
        return f'<Message {self.id} in Conv {self.conv_id} by {self.role}>'


class UserMemory(db.Model):
    """Model for storing persistent user memories.
    
    This backs up the in-memory MCP memory server to ensure important memories
    are not lost if the memory server restarts. Critical memories should be saved
    to both the memory server and this database table.
    """
    __tablename__ = 'user_memories'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    key = db.Column(db.String(255), nullable=False)  # Memory key
    value = db.Column(db.Text, nullable=False)  # Memory value (stored as text/JSON)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    # Establish relationship with User model
    user = db.relationship('User', backref=db.backref('memories', lazy=True, cascade="all, delete-orphan"))
    
    # Composite unique constraint to ensure each user has unique memory keys
    __table_args__ = (db.UniqueConstraint('user_id', 'key', name='unique_user_memory_key'),)
    
    def __repr__(self):
        return f'<UserMemory {self.id} for User {self.user_id}: {self.key}>'
