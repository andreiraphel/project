from datetime import datetime
from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit
import sqlite3

# Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app)

def get_db_connection():
    """Helper function to connect to the database."""
    conn = sqlite3.connect('attendance.db')
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn

@app.route('/get_users', methods=['GET'])
def get_users():
    """Fetch all users."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, first_name, last_name FROM users ORDER BY first_name ASC, last_name ASC")
    users = cursor.fetchall()
    conn.close()
    return jsonify([dict(user) for user in users])

@socketio.on('fetch_attendance')
def handle_fetch_attendance(data):
    """Handle WebSocket event to fetch attendance records and emit updates every second."""
    start_date = data.get('start_date')
    end_date = data.get('end_date')
    user_id = data.get('user_id')  # Update: filter by user_id instead of name
    page = int(data.get('page', 1))
    per_page = int(data.get('per_page', 10))

    while True:
        offset = (page - 1) * per_page

        conn = get_db_connection()
        cursor = conn.cursor()
        query = """
            SELECT users.first_name, users.last_name, attendance.timestamp, attendance.type
            FROM attendance
            JOIN users ON attendance.user_id = users.id
            WHERE attendance.timestamp BETWEEN ? AND ?
        """

        params = [start_date, end_date]

        if user_id:
            query += " AND users.id = ?"
            params.append(user_id)

        query += " ORDER BY attendance.timestamp ASC LIMIT ? OFFSET ?"
        params.extend([per_page, offset])

        cursor.execute(query, tuple(params))
        records = cursor.fetchall()

        count_query = """
            SELECT COUNT(*)
            FROM attendance
            JOIN users ON attendance.user_id = users.id
            WHERE attendance.timestamp BETWEEN ? AND ?
        """

        if user_id:
            count_query += " AND users.id = ?"
            count_params = [start_date, end_date, user_id]
        else:
            count_params = [start_date, end_date]

        cursor.execute(count_query, tuple(count_params))
        total_records = cursor.fetchone()[0]

        conn.close()

        # Emit the data back to the client
        emit('attendance_update', {
            'data': [dict(record) for record in records],
            'total_records': total_records,
            'page': page,
            'per_page': per_page,
            'last_refreshed': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })

        socketio.sleep(1)  # Sleep for 1 second before sending the next update

@app.route('/')
def index():
    """Render the main HTML page."""
    return render_template('index.html')

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
