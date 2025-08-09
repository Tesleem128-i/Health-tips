from flask import Flask, jsonify, request, g
import sqlite3
import datetime
import os

app = Flask(__name__, static_folder='static', template_folder='templates')
DATABASE = 'health_tips.db'

# -------------------
# Database Connection
# -------------------
def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

# -------------------
# Create Tables if Not Exists
# -------------------
def init_db():
    with app.app_context():
        db = get_db()
        db.execute('''
            CREATE TABLE IF NOT EXISTS tips (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT NOT NULL,
                image_url TEXT,
                likes INTEGER DEFAULT 0,
                created_at TEXT
            )
        ''')
        db.commit()

# -------------------
# Routes
# -------------------

# Get all tips
@app.route('/tips', methods=['GET'])
def get_tips():
    db = get_db()
    tips = db.execute('SELECT * FROM tips ORDER BY created_at DESC').fetchall()
    return jsonify([dict(t) for t in tips])

# Like a tip
@app.route('/like/<int:tip_id>', methods=['POST'])
def like_tip(tip_id):
    db = get_db()
    db.execute('UPDATE tips SET likes = likes + 1 WHERE id = ?', (tip_id,))
    db.commit()
    likes = db.execute('SELECT likes FROM tips WHERE id = ?', (tip_id,)).fetchone()['likes']
    return jsonify({'message': 'Liked!', 'likes': likes})

# Add a tip (for testing)
@app.route('/add_tip', methods=['POST'])
def add_tip():
    data = request.json
    content = data.get('content')
    image_url = data.get('image_url', None)
    created_at = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    db = get_db()
    db.execute('INSERT INTO tips (content, image_url, created_at) VALUES (?, ?, ?)',
               (content, image_url, created_at))
    db.commit()
    return jsonify({'message': 'Tip added!'})

# -------------------
# Run the App
# -------------------
if __name__ == '__main__':
    if not os.path.exists(DATABASE):
        init_db()
    app.run(debug=True)
