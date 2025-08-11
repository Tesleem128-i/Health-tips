from flask import Flask, jsonify, request, g, send_from_directory, render_template, redirect, url_for, session
import sqlite3
import datetime
import os
from werkzeug.utils import secure_filename
import random
import string
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, flash
from werkzeug.security import generate_password_hash
from flask import Flask, jsonify, request, send_file, abort
import sqlite3
import io



app = Flask(__name__, static_folder='static', template_folder='template')
DATABASE = 'health_tips.db'
app.secret_key = "yoursecretkey" 



UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'mp4', 'mov', 'avi'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ------------------- Database Connection -------------------
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

# ------------------- Create Tables -------------------
def init_db():
    with app.app_context():
        db = get_db()
        db.execute('''
            CREATE TABLE IF NOT EXISTS tips (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT NOT NULL,
                image_url TEXT,
                video_url TEXT,
                likes INTEGER DEFAULT 0,
                created_at TEXT
            )
        ''')
        db.commit()

# ------------------- Routes -------------------

import sqlite3
@app.route('/')
def index():
    conn = sqlite3.connect("health_tips.db")  # Tips DB
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # Attach the users DB
    cur.execute("ATTACH DATABASE ? AS users_db", ("healthtips.db",))

    # Fetch tips with counts
    cur.execute("""
        SELECT 
            t.*, 
            u.username,
            (SELECT COUNT(*) FROM comments c WHERE c.tip_id = t.id) AS comment_count,
            (SELECT COUNT(*) FROM shares s WHERE s.tip_id = t.id) AS share_count,
            (SELECT COUNT(*) FROM downloads d WHERE d.tip_id = t.id) AS download_count
        FROM tips t
        JOIN users_db.users u ON t.user_id = u.user_id
        ORDER BY t.created_at DESC
    """)
    tips = cur.fetchall()

    # Fetch comments for display
    cur.execute("""
        SELECT 
            c.tip_id, 
            c.comment, 
            c.created_at, 
            u.username
        FROM comments c
        JOIN users_db.users u ON c.user_id = u.user_id
        ORDER BY c.created_at DESC
    """)
    comments_data = cur.fetchall()

    conn.close()

    # Group comments by tip_id
    comments_by_tip = {}
    for c in comments_data:
        comments_by_tip.setdefault(c['tip_id'], []).append(c)

    return render_template('index.html', tips=tips, comments_by_tip=comments_by_tip)


@app.route('/tips', methods=['GET'])
def get_tips():
    db = get_db()
    tips_data = db.execute("""
        SELECT t.id, t.content, t.image_url, t.video_url, t.likes,
               COUNT(c.id) AS comment_count
        FROM tips t
        LEFT JOIN comments c ON t.id = c.tip_id
        GROUP BY t.id
        ORDER BY t.created_at DESC
    """).fetchall()

    tips_list = []
    for tip in tips_data:
        tips_list.append({
            'id': tip['id'],
            'content': tip['content'],
            'image_url': tip['image_url'],
            'video_url': tip['video_url'],
            'likes': tip['likes'],
            'comment_count': tip['comment_count']
        })

    return jsonify(tips_list)


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/add_tip', methods=['POST'])
def add_tip():
    if 'user_id' not in session:
        return jsonify({'error': 'You must be logged in to add a tip'}), 401

    content = request.form.get('content')
    created_at = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    user_id = session['user_id']  # Get current logged-in user ID

    image_url, video_url = None, None

    # Handle image upload
    if 'image' in request.files:
        image_file = request.files['image']
        if image_file and allowed_file(image_file.filename):
            filename = secure_filename(image_file.filename)
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            image_file.save(image_path)
            image_url = '/' + image_path

    # Handle video upload
    if 'video' in request.files:
        video_file = request.files['video']
        if video_file and allowed_file(video_file.filename):
            filename = secure_filename(video_file.filename)
            video_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            video_file.save(video_path)
            video_url = '/' + video_path

    db = get_db()
    db.execute('''
        INSERT INTO tips (content, image_url, video_url, created_at, user_id) 
        VALUES (?, ?, ?, ?, ?)
    ''', (content, image_url, video_url, created_at, user_id))
    db.commit()

    return jsonify({'message': 'Tip added!'})


def generate_user_id():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

# Signup route
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        age = request.form['age']
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        # Validate passwords
        if password != confirm_password:
            flash("Passwords do not match!", "error")
            return redirect(url_for('signup'))

        # Validate age
        if not age.isdigit() or int(age) < 13:
            flash("You must be at least 13 years old to sign up.", "error")
            return redirect(url_for('signup'))

        # Generate unique user_id
        user_id = generate_user_id()

        # Hash password
        hashed_password = generate_password_hash(password)

        # Save to database
        conn = sqlite3.connect("healthtips.db")
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT UNIQUE,
                username TEXT UNIQUE,
                age INTEGER,
                password TEXT
            )
        """)
        try:
            cur.execute("INSERT INTO users (user_id, username, age, password) VALUES (?, ?, ?, ?)",
                        (user_id, username, age, hashed_password))
            conn.commit()
            flash("Account created successfully! Please log in.", "success")
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash("Username already exists!", "error")
            return redirect(url_for('signup'))
        finally:
            conn.close()

    return render_template('signup.html')

from flask import session
from werkzeug.security import check_password_hash
import sqlite3

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = sqlite3.connect("healthtips.db")
        cur = conn.cursor()
        cur.execute("SELECT user_id, password FROM users WHERE username = ?", (username,))
        user = cur.fetchone()
        conn.close()

        if user:
            user_id, hashed_password = user
            if check_password_hash(hashed_password, password):
                session['user_id'] = user_id
                session['username'] = username
                flash("Login successful!", "success")
                return redirect(url_for('index'))  # Change 'home' to your homepage route
            else:
                flash("Incorrect password!", "error")
        else:
            flash("Username not found!", "error")

    return render_template('signup.html')

@app.route('/profile/<user_id>')
def profile(user_id):
    if 'user_id' not in session or session['user_id'] != user_id:
        flash("Unauthorized access!", "error")
        return redirect(url_for('login'))

    conn = sqlite3.connect("healthtips.db")
    cur = conn.cursor()
    cur.execute("SELECT username FROM users WHERE user_id = ?", (user_id,))
    user = cur.fetchone()
    conn.close()

    if not user:
        flash("User not found!", "error")
        return redirect(url_for('index'))

    return render_template('profile.html', user_id=user_id, username=user[0])



@app.route('/add_comment/<int:tip_id>', methods=['POST'])
def add_comment(tip_id):
    if 'user_id' not in session:
        flash("You must be logged in to comment.", "error")
        return redirect(url_for('login'))

    comment_text = request.form.get('comment', '').strip()
    if not comment_text:
        flash("Comment cannot be empty.", "error")
        return redirect(url_for('index'))

    created_at = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    db = get_db()
    db.execute(
        "INSERT INTO comments (tip_id, user_id, comment, created_at) VALUES (?, ?, ?, ?)",
        (tip_id, session['user_id'], comment_text, created_at)
    )
    db.commit()
    flash("Comment added!", "success")
    return redirect(url_for('index'))

@app.route('/comments/<int:tip_id>')
def get_comments(tip_id):
    try:
        db = sqlite3.connect('health_tips.db')  # assign the database here
        db.row_factory = sqlite3.Row
        comments = db.execute("""
            SELECT c.comment, u.username
            FROM comments c
            LEFT JOIN users u ON c.user_id = u.user_id
            WHERE c.tip_id = ?
            ORDER BY c.created_at DESC
        """, (tip_id,)).fetchall()
        db.close()  # close connection after use

        comments_list = [{'comment': c['comment'], 'username': c['username']} for c in comments]
        return jsonify(comments_list)

    except sqlite3.Error as e:
        # Log error if needed, e.g. print or use logging module
        print(f"Database error: {e}")
        return jsonify({"error": "Database error occurred", "details": str(e)}), 500

    except Exception as e:
        # Catch-all for other errors
        print(f"Unexpected error: {e}")
        return jsonify({"error": "An unexpected error occurred", "details": str(e)}), 500



DATABASE = 'health_tips.db'  # Updated database name

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

# Route to like a tip (increment likes count)
@app.route('/like/<int:tip_id>', methods=['POST'])
def like_tip(tip_id):
    conn = get_db_connection()
    tip = conn.execute('SELECT * FROM tips WHERE id = ?', (tip_id,)).fetchone()
    if tip is None:
        conn.close()
        return jsonify({'error': 'Tip not found'}), 404

    new_likes = tip['likes'] + 1 if tip['likes'] is not None else 1
    conn.execute('UPDATE tips SET likes = ? WHERE id = ?', (new_likes, tip_id))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Tip liked', 'likes': new_likes})

# Route to get tip content
@app.route('/tip/<int:tip_id>/content')
def get_tip_content(tip_id):
    conn = get_db_connection()
    tip = conn.execute('SELECT content FROM tips WHERE id = ?', (tip_id,)).fetchone()
    conn.close()
    if tip is None:
        return jsonify({'error': 'Tip not found'}), 404
    return jsonify({'content': tip['content']})

# Provide a download endpoint
@app.route('/download/<int:tip_id>')
def download_tip(tip_id):
    conn = get_db_connection()
    tip = conn.execute('SELECT content FROM tips WHERE id = ?', (tip_id,)).fetchone()
    conn.close()
    if tip is None:
        abort(404)
    content = tip['content']
    return send_file(
        io.BytesIO(content.encode('utf-8')),
        mimetype='text/plain',
        as_attachment=True,
        download_name='health_tip.txt'
    )
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


if __name__ == '__main__':
    if not os.path.exists(DATABASE):
        init_db()
    app.run(debug=True)
