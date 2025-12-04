import sqlite3

# Connect to SQLite (this will create chat.db if it doesn't exist)
conn = sqlite3.connect("chat.db")
cursor = conn.cursor()

# Create table
cursor.execute("""
    CREATE TABLE IF NOT EXISTS chat_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        question TEXT,
        answer TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )
""")

conn.commit()
conn.close()

print("✅ Database and table 'chat_history' created successfully.")
