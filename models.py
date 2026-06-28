from flask_sqlalchemy import SQLAlchemy # A database model of the user (SQLAlchemy)
from flask_login import UserMixin # A session identity system
from datetime import datetime, timedelta #It captures exact date time of the frame

db = SQLAlchemy() # creating a database integration object

class User(db.Model, UserMixin): # actual user identity structure of system
    id=db.Column(db.Integer, primary_key=True)
    username=db.Column(db.String(100), unique=True, nullable=False)
    password=db.Column(db.String(100), nullable=False)
    role=db.Column(db.String(20), default='user')

class DetectionHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), nullable=False)
    object_name = db.Column(db.String(100), nullable=False)
    distance = db.Column(db.Float)
    confidence = db.Column(db.Float)
    timestamp = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )