from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_socketio import SocketIO, emit, join_room, leave_room, disconnect, rooms
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = 'a-very-secret-key-that-you-should-change'
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:@localhost/eye_mouse_db?charset=utf8mb4'
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
socketio = SocketIO(app)

# --- Database Model (Unchanged) ---
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(256))

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- Web Routes (Unchanged) ---
@app.route('/')
def index():
    return render_template('index.html')

# --- REPLACE THE ENTIRE LOGIN FUNCTION WITH THIS ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        # --- NEW DEBUG PRINTS ---
        print(f"\n--- LOGIN ATTEMPT ---")
        print(f"Form Username: {username}")
        print(f"Form Password: {password}")
        
        user = User.query.filter_by(username=username).first()
        
        if not user:
            print("DEBUG: User not found in database.")
            return 'Invalid credentials'
        
        print(f"DEBUG: Found user. Checking password...")
        print(f"DEBUG: Hash in DB: {user.password_hash}")
        
        is_valid = user.check_password(password)
        
        print(f"DEBUG: Password check result: {is_valid}")
        print(f"---------------------\n")
        # --- END DEBUG PRINTS ---

        if is_valid:
            login_user(user)
            return redirect(url_for('dashboard'))
        
        return 'Invalid credentials'
        
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        if User.query.filter_by(username=username).first():
            return "Username already exists"
            
        new_user = User(username=username)
        new_user.set_password(password)
        
        # --- NEW DEBUG PRINT ---
        print(f"\n--- REGISTERING USER ---")
        print(f"Username: {username}")
        print(f"Password: {password}")
        print(f"GENERATED HASH: {new_user.password_hash}")
        print(f"----------------------\n")
        # --- END DEBUG PRINT ---
        
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('login'))
        
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html', username=current_user.username)

# --- WebSocket Events (UPDATED) ---

# We will use the user's ID as the "room" name
# to send messages between their agent and their web UI.

# Called by the Web UI (dashboard.html) when it connects
@socketio.on('register_web')
@login_required
def register_web():
    room = str(current_user.id)
    join_room(room)
    print(f"Web UI for user {current_user.username} joined room: {room}")

# Called by the Agent (agent.py) when it connects
@socketio.on('register_agent')
def register_agent(data):
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        print(f"Agent {request.sid} connected without credentials. Disconnecting.")
        disconnect()
        return

    # Find the user in the database
    user = User.query.filter_by(username=username).first()
    
    # Check if user exists AND password is correct
    if user and user.check_password(password):
        # If valid, add the agent to their room
        room = str(user.id)
        join_room(room)
        print(f"Agent {request.sid} (for user '{username}') joined room: {room}")
    else:
        # If user or password invalid, reject the agent
        print(f"Agent {request.sid} failed auth as user '{username}'. Disconnecting.")
        disconnect()
        
        
# Called by the Web UI (Start/Stop buttons)
@socketio.on('start_script')
@login_required
def handle_start():
    room = str(current_user.id)
    print(f'User {current_user.username} requested START in room {room}')
    emit('command', {'action': 'start'}, to=room) # Send *only* to user's room

@socketio.on('stop_script')
@login_required
def handle_stop():
    room = str(current_user.id)
    print(f'User {current_user.username} requested STOP in room {room}')
    emit('command', {'action': 'stop'}, to=room) # Send *only* to user's room

# Called by the Agent (streaming video)
@socketio.on('video_frame')
def handle_video_frame(data):
    print("DEBUG: Received frame from agent")
    # This assumes the agent is in a room
    # We just relay the frame to all web UIs in that same room
    for room in rooms(request.sid):
        # ...but we ONLY send the frame to the room that is NOT its personal ID.
        if room != request.sid: 
            print(f"DEBUG: Relaying frame to user room {room}") # This will now say "room 1"
            emit('new_frame', data, to=room)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    socketio.run(app, debug=True, port=5000)