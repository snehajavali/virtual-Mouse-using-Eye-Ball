// server.js
const express = require('express');
const http = require('http');
const { Server } = require("socket.io");
const mysql = require('mysql2');
const path = require('path');

const app = express();
const server = http.createServer(app);
const io = new Server(server);

const PORT = 3000;

// --- Insecure MySQL Connection (as requested) ---
const db = mysql.createConnection({
  host: 'localhost',
  user: 'root', // Your MySQL username
  password: '', // Your MySQL password
  database: 'eye_mouse_db' // Your database
});

db.connect((err) => {
  if (err) throw err;
  console.log('Connected to MySQL database.');
  // Using the more compatible CREATE TABLE syntax
  const createTableQuery = 'CREATE TABLE IF NOT EXISTS users (id INT AUTO_INCREMENT, username VARCHAR(100) NOT NULL, password VARCHAR(100) NOT NULL, PRIMARY KEY (id));';
  db.query(createTableQuery, (err) => {
    if (err) throw err;
    console.log("Table 'users' is ready.");
  });
});

// --- Middleware ---
app.use(express.static(path.join(__dirname, 'public')));
app.use(express.urlencoded({ extended: true }));

// --- HTTP Routes ---

// Serve the login page as the root
app.get('/', (req, res) => {
  res.sendFile(path.join(__dirname, 'public', 'login.html'));
});
// Serve register page explicitly
app.get('/register.html', (req, res) => {
    res.sendFile(path.join(__dirname, 'public', 'register.html'));
});
// Serve login page explicitly
app.get('/login.html', (req, res) => {
    res.sendFile(path.join(__dirname, 'public', 'login.html'));
});
// Serve dashboard page explicitly
app.get('/dashboard.html', (req, res) => {
    res.sendFile(path.join(__dirname, 'public', 'dashboard.html'));
});


// Register a new user (plain text)
app.post('/register', (req, res) => {
  const { username, password } = req.body;
  if (!username || !password) {
    // Redirect back to register page with error
    return res.redirect('/register.html?error=Please+fill+all+fields');
  }
  const query = 'INSERT INTO users (username, password) VALUES (?, ?)';
  db.query(query, [username, password], (err) => {
    if (err) {
       // Redirect back to register page with error
      return res.redirect('/register.html?error=Username+already+taken');
    }
    // Success! Send to dashboard.
    res.redirect('/dashboard.html');
  });
});

// Log in a user (plain text)
app.post('/login', (req, res) => {
  const { username, password } = req.body;
  const query = 'SELECT * FROM users WHERE username = ? AND password = ?';
  db.query(query, [username, password], (err, results) => {
    if (err || results.length === 0) {
      // Redirect back to login page with error
      return res.redirect('/login.html?error=Invalid+credentials');
    }
    // Success! Send to dashboard.
    res.redirect('/dashboard.html');
  });
});

// --- Socket.IO (for the Agent) ---
io.on('connection', (socket) => {
  console.log('A client connected. ID:', socket.id);
  
  socket.on('start_script', () => {
    console.log('Browser clicked START. Sending command to agent...');
    io.emit('command', { action: 'start' });
  });

  socket.on('stop_script', () => {
    console.log('Browser clicked STOP. Sending command to agent...');
    io.emit('command', { action: 'stop' });
  });

  // --- ADDED: Listen for frames FROM the agent ---
  socket.on('video_frame', (data) => {
    // Relay the frame ONLY to browsers (not back to the agent itself)
    socket.broadcast.emit('new_frame', data);
  });
  // --- END ADDED SECTION ---

  socket.on('disconnect', () => {
    console.log('A client disconnected. ID:', socket.id);
  });
});

// --- Start the server ---
server.listen(PORT, () => {
  console.log(`Server running at http://localhost:${PORT}`);
});