from flask import Flask, render_template, redirect, request, url_for 
# Web framework core → Flask, Template rendering → render_template, HTTP control → request, redirect, url_for → generates URLs dynamically based on route function names
from flask_login import LoginManager, login_user, login_required, logout_user
# Authentication engine → LoginManager, Session control → login_user, logout_user, Route protection → login_required
from werkzeug.security import generate_password_hash, check_password_hash
# Password security → hashing functions
from models import db, User, DetectionHistory
# Database access → db, User entity → User
from flask_login import current_user
from flask import flash
from flask import Response
from ultralytics import YOLO
import time
from flask import jsonify
#Detection Queue
from queue import Queue
#To scale detection queue
from dataclasses import dataclass
import numpy as np
import cv2

@dataclass
class DetectionEvent:

    username: str
    object_name: str
    distance: float
    confidence: float

def database_logger():

    while True:

        event = detection_queue.get()

        with app.app_context():
            db.create_all()

            new_detection = DetectionHistory(
                username=event.username,
                object_name=event.object_name,
                distance=event.distance,
                confidence=event.confidence
            )

            db.session.add(new_detection)
            db.session.commit()

        detection_queue.task_done()

camera_status = "Not Connected"
model_status = "Loading..."
audio_status = "Enabled"
fps_value = 0

model = YOLO("yolov8n.pt")
model_status = "Loaded"

FOCAL_LENGTH = 800  # Approximate (tune later)
KNOWN_WIDTHS = {
    "person": 0.45,
    "laptop": 0.35,
    "bottle": 0.07,
    "chair": 0.5,
    "cell phone": 0.07,
    "car": 1.8,
    "tv": 1.0,
    "dog": 0.5,
    "cat": 0.35,
    "backpack": 0.3,
    "book": 0.2,
}

last_detected_label = None

detection_count = 0
last_detected_object = "None"

detection_enabled = True

last_saved_times = {}
SAVE_DELAY = 5
detection_queue = Queue()

app = Flask(__name__)
# creates the actual Flask application instance.

app.config['SECRET_KEY'] = 'supersecretkey'
# activates session security and authentication integrity (signs cookies with this secret key)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
# configure the database connection

db.init_app(app)
# This links SQLAlchemy to our Flask app

from datetime import datetime, timedelta

@app.route('/history')
@login_required
def history():

    selected_user = request.args.get("user", "all")
    selected_object = request.args.get("object", "all")
    selected_time = request.args.get("time", "all")

    query = DetectionHistory.query

    # User restriction
    if current_user.role != "admin":
        query = query.filter_by(username=current_user.username)

    elif selected_user != "all":
        query = query.filter_by(username=selected_user)

    # Object filter
    if selected_object != "all":
        query = query.filter_by(object_name=selected_object)

    # Time filter
    now = datetime.now()

    if selected_time == "today":
        query = query.filter(
            DetectionHistory.timestamp >= now.replace(
                hour=0,
                minute=0,
                second=0,
                microsecond=0
            )
        )

    elif selected_time == "week":
        query = query.filter(
            DetectionHistory.timestamp >= now - timedelta(days=7)
        )

    elif selected_time == "month":
        query = query.filter(
            DetectionHistory.timestamp >= now - timedelta(days=30)
        )

    page = request.args.get("page", 1, type=int)

    history = query.order_by(
        DetectionHistory.timestamp.desc()
    ).paginate(
        page=page,
        per_page=20,
        error_out=False
    )

    users = User.query.order_by(User.username).all()

    objects = db.session.query(
        DetectionHistory.object_name
    ).distinct().all()

    objects = [obj[0] for obj in objects]

    return render_template(
        "history.html",
        history=history,
        users=users,
        objects=objects,
        selected_user=selected_user,
        selected_object=selected_object,
        selected_time=selected_time
    )

login_manager=LoginManager()
# creates an instance of the LoginManager class from Flask-Login
login_manager.init_app(app)

login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':

        username = request.form['username']
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        if password != confirm_password:
            flash("Passwords do not match", "danger")
            return redirect(url_for('register'))

        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash("Username already exists", "warning")
            return redirect(url_for('register'))

        hashed_password = generate_password_hash(password)

        new_user = User(username=username, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()

        flash("Registration successful! Please login.", "success")
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':

        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password, password):
            login_user(user)

            flash("Login successful!", "success")

            if user.role == "admin":
                return redirect(url_for('admin_dashboard'))

            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)

            return redirect(url_for('dashboard'))

        flash("Invalid username or password", "danger")
        return redirect(url_for('login'))

    return render_template('login.html')

@app.route('/admin')
@login_required
def admin_dashboard():

    if current_user.role != "admin":
        return "Unauthorized Access"

    users = User.query.all()
    return render_template('admin.html', users=users)

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html', user=current_user)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

with app.app_context():
    admin = User.query.filter_by(username="admin").first()
    if not admin:
        from werkzeug.security import generate_password_hash
        new_admin = User(
            username="admin",
            password=generate_password_hash("admin123"),
            role="admin"
        )
        db.session.add(new_admin)
        db.session.commit()

@app.route('/delete/<int:id>', methods=['POST'])
@login_required
def delete_user(id):

    if current_user.role != "admin":
        flash("Unauthorized action", "danger")
        return redirect(url_for('dashboard'))

    user = User.query.get(id)

    if user.role == "admin":
        flash("Cannot delete admin user", "warning")
        return redirect(url_for('admin_dashboard'))

    db.session.delete(user)
    db.session.commit()

    flash("User deleted successfully", "success")
    return redirect(url_for('admin_dashboard'))

@app.route('/profile')
@login_required
def profile():
    return render_template('profile.html')

@app.route('/stats')
@login_required
def stats():
    return jsonify({
        "count": detection_count,
        "last": last_detected_object
    })
        
@app.route('/system_info')
@login_required
def system_info():
    return jsonify({
        "camera": camera_status,
        "model": model_status,
        "audio": audio_status,
        "fps": fps_value
    })

@app.route('/toggle_detection', methods=['POST'])
@login_required
def toggle_detection():
    global detection_enabled

    detection_enabled = not detection_enabled

    return jsonify({
        "detection_enabled": detection_enabled
    })

#NEW ARCHITECTURE
@app.route("/detect", methods=["POST"])
@login_required
def detect():

    image = request.files.get("image")

    if image is None:
        return {"status":"no image"}

    file_bytes = np.frombuffer(
        image.read(),
        np.uint8
    )

    frame = cv2.imdecode(
        file_bytes,
        cv2.IMREAD_COLOR
    )

    results = model(frame)
    objects = []
    for r in results:
        for box in r.boxes:
            x1, y1, x2, y2 = map(
                int,
                box.xyxy[0]
            )
            cls = int(box.cls[0])
            label = model.names[cls]
            confidence = round(
                float(box.conf[0]) * 100,
                2
            )

            width_in_frame = x2 - x1
            distance = None
            if label in KNOWN_WIDTHS and width_in_frame > 0:
                real_width = KNOWN_WIDTHS[label]
                distance = round(
                    (real_width * FOCAL_LENGTH) / width_in_frame,
                    2
                )

            current_time = time.time()

            if label not in last_saved_times:
                last_saved_times[label] = 0

            if current_time - last_saved_times[label] > SAVE_DELAY:

                event = DetectionEvent(
                    username=current_user.username,
                    object_name=label,
                    distance=distance,
                    confidence=confidence
                )

                detection_queue.put(event)

                last_saved_times[label] = current_time

            objects.append({
                "label":label,
                "confidence":confidence,
                "distance":distance,
                "x1":x1,
                "y1":y1,
                "x2":x2,
                "y2":y2
})
    return {
        "status": "success",
        "objects": objects
    }

@app.route("/browser-camera")
def browser_camera():
    return render_template("browser_camera.html")

if __name__ == "__main__":
    app.run(debug=True)