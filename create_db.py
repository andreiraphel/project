import sqlite3

def recreate_database():
    conn = sqlite3.connect("attendance.db")
    cursor = conn.cursor()
    
    cursor.execute("DROP TABLE IF EXISTS attendance")
    cursor.execute("DROP TABLE IF EXISTS users")
    
    cursor.execute("""
        CREATE TABLE users(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            finger_id INTEGER NOT NULL UNIQUE,
            pin INTEGER NOT NULL UNIQUE,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            user_type TEXT CHECK(user_type IN ('admin', 'normal')) NOT NULL
        )
    """)
    
    cursor.execute("""
        CREATE TABLE attendance(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            timestamp DATETIME NOT NULL,
            type TEXT CHECK(type IN ('time-in', 'time-out')) NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)
    
    conn.commit()
    conn.close()
    print("Database created successfully")
    
if __name__ == "__main__":
    recreate_database()