import sqlite3

# Initialize the database connection
conn = sqlite3.connect('health_tips.db')  # Replace with your actual DB file
cursor = conn.cursor()

# Delete all rows from the tips table
cursor.execute('DELETE FROM tips')

# Commit changes and close connection
conn.commit()
conn.close()

print("All tips deleted successfully")
