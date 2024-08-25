from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from flask_swagger_ui import get_swaggerui_blueprint

# Initialize Flask app
app = Flask(__name__)

# Configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///tasks.db'  # Use your preferred database
app.config['JWT_SECRET_KEY'] = 'your_secret_key'  # Change this to a secure secret key

# Initialize extensions
db = SQLAlchemy(app)
jwt = JWTManager(app)

# Swagger UI setup
SWAGGER_URL = '/swagger'
API_URL = '/static/swagger.json'  # Ensure this path is correct and accessible

swaggerui_bp = get_swaggerui_blueprint(
    SWAGGER_URL,
    API_URL,
    config={'app_name': "My Flask App"}
)
app.register_blueprint(swaggerui_bp, url_prefix=SWAGGER_URL)

# Database Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)

class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), nullable=False)
    description = db.Column(db.String(500), nullable=True)
    status = db.Column(db.String(20), nullable=False, default="Todo")
    priority = db.Column(db.String(20), nullable=False, default="Low")
    due_date = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

# Routes

# User Registration
@app.route('/api/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data['username']
    password = generate_password_hash(data['password'])

    if User.query.filter_by(username=username).first():
        return jsonify({"message": "User already exists!"}), 400

    new_user = User(username=username, password_hash=password)
    db.session.add(new_user)
    db.session.commit()

    return jsonify({"message": "User registered successfully!"}), 201

# User Login
@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data['username']
    password = data['password']

    user = User.query.filter_by(username=username).first()

    if user and check_password_hash(user.password_hash, password):
        access_token = create_access_token(identity=user.id)
        return jsonify(access_token=access_token), 200

    return jsonify({"message": "Invalid credentials!"}), 401

# Create Task (requires authentication)
@app.route('/api/tasks', methods=['POST'])
@jwt_required()
def create_task():
    user_id = get_jwt_identity()
    data = request.get_json()

    new_task = Task(
        title=data['title'],
        description=data['description'],
        status=data['status'],
        priority=data['priority'],
        due_date=datetime.strptime(data['due_date'], '%Y-%m-%d'),
        user_id=user_id
    )
    db.session.add(new_task)
    db.session.commit()

    return jsonify({"message": "Task created successfully!"}), 201

@app.route('/')
def home():
    return "Welcome to the Task Management API!"

# Get Tasks (requires authentication)
@app.route('/api/tasks', methods=['GET'])
@jwt_required()
def get_tasks():
    user_id = get_jwt_identity()
    tasks = Task.query.filter_by(user_id=user_id).all()

    task_list = [
        {
            "id": task.id,
            "title": task.title,
            "description": task.description,
            "status": task.status,
            "priority": task.priority,
            "due_date": task.due_date.strftime('%Y-%m-%d'),
            "created_at": task.created_at,
            "updated_at": task.updated_at
        }
        for task in tasks
    ]
    return jsonify(task_list), 200

# Update Task (requires authentication)
@app.route('/api/tasks/<int:task_id>', methods=['PUT'])
@jwt_required()
def update_task(task_id):
    user_id = get_jwt_identity()
    task = Task.query.filter_by(id=task_id, user_id=user_id).first()

    if not task:
        return jsonify({"message": "Task not found!"}), 404

    data = request.get_json()
    task.title = data.get('title', task.title)
    task.description = data.get('description', task.description)
    task.status = data.get('status', task.status)
    task.priority = data.get('priority', task.priority)
    task.due_date = datetime.strptime(data.get('due_date', task.due_date.strftime('%Y-%m-%d')), '%Y-%m-%d')

    db.session.commit()
    return jsonify({"message": "Task updated successfully!"}), 200

if __name__ == '__main__':
    app.run(debug=True)
