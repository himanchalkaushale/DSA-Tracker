import sqlite3
import json
import os
import pandas as pd

def get_db_connection():
    """Create a connection to the SQLite database"""
    conn = sqlite3.connect('dsa_tracker.db')
    conn.row_factory = sqlite3.Row
    return conn

def initialize_database():
    """Initialize the database with necessary tables"""
    conn = get_db_connection()
    
    # Create tables
    conn.execute('''
    CREATE TABLE IF NOT EXISTS topics (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE
    )
    ''')
    
    conn.execute('''
    CREATE TABLE IF NOT EXISTS questions (
        id INTEGER PRIMARY KEY,
        title TEXT NOT NULL,
        leetcode_url TEXT NOT NULL,
        gfg_url TEXT,
        difficulty TEXT NOT NULL,
        topic_id INTEGER NOT NULL,
        FOREIGN KEY (topic_id) REFERENCES topics (id)
    )
    ''')
    
    # Create users table for authentication
    conn.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL UNIQUE,
        password TEXT NOT NULL,
        email TEXT UNIQUE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_login TIMESTAMP
    )
    ''')
    
    # Create progress table with user_id to track per-user progress
    conn.execute('''
    CREATE TABLE IF NOT EXISTS progress (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        question_id INTEGER NOT NULL,
        user_id INTEGER DEFAULT 1,
        completed BOOLEAN NOT NULL DEFAULT 0,
        completed_at TIMESTAMP,
        FOREIGN KEY (question_id) REFERENCES questions (id),
        FOREIGN KEY (user_id) REFERENCES users (id),
        UNIQUE(question_id, user_id)
    )
    ''')
    
    # Create admin table if it doesn't exist
    conn.execute('''
    CREATE TABLE IF NOT EXISTS admin (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL UNIQUE,
        password TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Check if gfg_url column exists in the questions table
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(questions)")
    columns = [column[1] for column in cursor.fetchall()]
    
    # If gfg_url column doesn't exist, add it
    if 'gfg_url' not in columns:
        try:
            conn.execute("ALTER TABLE questions ADD COLUMN gfg_url TEXT")
            print("Added gfg_url column to questions table")
        except Exception as e:
            print(f"Error adding gfg_url column: {e}")
            
    # Check if users table has any records, and add default user if not
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
    if cursor.fetchone():  # Table exists
        cursor.execute("SELECT COUNT(*) FROM users")
        user_count = cursor.fetchone()[0]
        
        if user_count == 0:
            # Add default user
            cursor.execute("""
            INSERT INTO users (username, password, email)
            VALUES ('demo', 'demo123', 'demo@example.com')
            """)
            print("Added default user: demo/demo123")
    
    # Add default admin if none exists
    cursor.execute("SELECT COUNT(*) FROM admin")
    admin_count = cursor.fetchone()[0]
    
    if admin_count == 0:
        # Default admin: username=admin, password=admin123
        conn.execute("""
        INSERT INTO admin (username, password)
        VALUES ('admin', 'admin123')
        """)
        print("Added default admin user: admin/admin123")
    
    # Check if we need to migrate progress data to include user_id
    cursor.execute("PRAGMA table_info(progress)")
    progress_columns = [column[1] for column in cursor.fetchall()]
    
    # If progress table doesn't have user_id, we need to migrate the data
    if 'user_id' not in progress_columns:
        print("Migrating progress data to include user_id...")
        
        # Create new progress table with user_id
        conn.execute('''
        CREATE TABLE IF NOT EXISTS progress_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question_id INTEGER NOT NULL,
            user_id INTEGER DEFAULT 1,
            completed BOOLEAN NOT NULL DEFAULT 0,
            completed_at TIMESTAMP,
            FOREIGN KEY (question_id) REFERENCES questions (id),
            FOREIGN KEY (user_id) REFERENCES users (id),
            UNIQUE(question_id, user_id)
        )
        ''')
        
        # Move data from old progress table to new one
        conn.execute('''
        INSERT INTO progress_new (question_id, completed)
        SELECT question_id, completed FROM progress
        ''')
        
        # Drop old table and rename new one
        conn.execute("DROP TABLE progress")
        conn.execute("ALTER TABLE progress_new RENAME TO progress")
        
        print("Progress data migration completed.")
    
    conn.commit()
    conn.close()

def load_initial_data():
    """Load initial data from questions.json into the database if it's not already there"""
    conn = get_db_connection()
    
    # Check if we already have data
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM questions")
    count = cur.fetchone()[0]
    
    if count > 0:
        conn.close()
        return  # Data already exists, don't reload
    
    # Load data from JSON file
    with open('questions.json', 'r') as f:
        questions_data = json.load(f)
    
    # Insert topics
    for topic_name in questions_data.keys():
        conn.execute("INSERT INTO topics (name) VALUES (?)", (topic_name,))
        conn.commit()
    
    # Get topic IDs
    topic_ids = {}
    cur = conn.cursor()
    cur.execute("SELECT id, name FROM topics")
    for row in cur.fetchall():
        topic_ids[row['name']] = row['id']
    
    # Insert questions
    for topic_name, questions in questions_data.items():
        topic_id = topic_ids[topic_name]
        for question in questions:
            # Check if gfg_url exists in the question data
            gfg_url = question.get('gfg_url', None)
            
            conn.execute("""
                INSERT INTO questions (id, title, leetcode_url, gfg_url, difficulty, topic_id)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                question['id'],
                question['title'],
                question['leetcode_url'],
                gfg_url,  # May be None for existing data
                question['difficulty'],
                topic_id
            ))
            
            # Initialize progress for each question
            conn.execute("""
                INSERT INTO progress (question_id, completed)
                VALUES (?, 0)
            """, (question['id'],))
    
    conn.commit()
    conn.close()

def get_topics():
    """Get all topics from the database"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name FROM topics ORDER BY name")
    topics = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return topics

def get_questions_by_topic(topic_id, search_query=None, difficulty=None, user_id=1):
    """Get questions for a specific topic with optional filtering
    
    Args:
        topic_id: The ID of the topic to get questions for
        search_query: Optional search query to filter questions by title
        difficulty: Optional difficulty level to filter questions by
        user_id: User ID to get progress for (defaults to 1 for backward compatibility)
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    query = """
    SELECT q.id, q.title, q.leetcode_url, q.gfg_url, q.difficulty, 
           COALESCE(p.completed, 0) as completed,
           p.notes, p.solution, COALESCE(p.bookmarked, 0) as bookmarked
    FROM questions q
    LEFT JOIN (
        SELECT * FROM progress WHERE user_id = ?
    ) p ON q.id = p.question_id
    WHERE q.topic_id = ?
    """
    
    params = [user_id, topic_id]
    
    if search_query:
        query += " AND q.title LIKE ?"
        params.append(f'%{search_query}%')
    
    if difficulty and difficulty != "All":
        query += " AND q.difficulty = ?"
        params.append(difficulty)
    
    cursor.execute(query, params)
    questions = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return questions

def get_topic_stats(topic_id, user_id=1):
    """Get completion statistics for a topic for a specific user
    
    Args:
        topic_id: ID of the topic to get statistics for
        user_id: ID of the user (defaults to 1 for backward compatibility)
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
    SELECT COUNT(*) as total,
           SUM(CASE WHEN p.completed = 1 THEN 1 ELSE 0 END) as completed
    FROM questions q
    LEFT JOIN (
        SELECT * FROM progress WHERE user_id = ?
    ) p ON q.id = p.question_id
    WHERE q.topic_id = ?
    """, (user_id, topic_id))
    
    stats = dict(cursor.fetchone())
    conn.close()
    
    return stats

def update_question_progress(question_id, completed, user_id=1):
    """Update the completion status of a question for a specific user
    
    Args:
        question_id: ID of the question to update
        completed: Boolean indicating whether the question is completed
        user_id: ID of the user (defaults to 1 for backward compatibility)
    """
    conn = get_db_connection()
    
    # Check if a progress record exists for this user and question
    cursor = conn.cursor()
    cursor.execute(
        "SELECT COUNT(*) FROM progress WHERE question_id = ? AND user_id = ?",
        (question_id, user_id)
    )
    record_exists = cursor.fetchone()[0] > 0
    
    # Get current timestamp if the question is being marked as completed
    completed_at = None
    if completed:
        from datetime import datetime
        completed_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    if record_exists:
        # Update existing record
        conn.execute(
            "UPDATE progress SET completed = ?, completed_at = ? WHERE question_id = ? AND user_id = ?",
            (1 if completed else 0, completed_at, question_id, user_id)
        )
    else:
        # Insert new record
        conn.execute(
            "INSERT INTO progress (question_id, user_id, completed, completed_at) VALUES (?, ?, ?, ?)",
            (question_id, user_id, 1 if completed else 0, completed_at)
        )
    
    conn.commit()
    conn.close()

def update_question_notes(question_id, notes, user_id=1):
    """Update the notes for a question for a specific user
    
    Args:
        question_id: ID of the question to update
        notes: Text notes for the question
        user_id: ID of the user
    """
    conn = get_db_connection()
    
    # Check if a progress record exists for this user and question
    cursor = conn.cursor()
    cursor.execute(
        "SELECT COUNT(*) FROM progress WHERE question_id = ? AND user_id = ?",
        (question_id, user_id)
    )
    record_exists = cursor.fetchone()[0] > 0
    
    if record_exists:
        # Update existing record
        conn.execute(
            "UPDATE progress SET notes = ? WHERE question_id = ? AND user_id = ?",
            (notes, question_id, user_id)
        )
    else:
        # Insert new record with default values
        conn.execute(
            "INSERT INTO progress (question_id, user_id, completed, notes) VALUES (?, ?, 0, ?)",
            (question_id, user_id, notes)
        )
    
    conn.commit()
    conn.close()

def update_question_solution(question_id, solution, user_id=1):
    """Update the solution for a question for a specific user
    
    Args:
        question_id: ID of the question to update
        solution: Solution text for the question
        user_id: ID of the user
    """
    conn = get_db_connection()
    
    # Check if a progress record exists for this user and question
    cursor = conn.cursor()
    cursor.execute(
        "SELECT COUNT(*) FROM progress WHERE question_id = ? AND user_id = ?",
        (question_id, user_id)
    )
    record_exists = cursor.fetchone()[0] > 0
    
    if record_exists:
        # Update existing record
        conn.execute(
            "UPDATE progress SET solution = ? WHERE question_id = ? AND user_id = ?",
            (solution, question_id, user_id)
        )
    else:
        # Insert new record with default values
        conn.execute(
            "INSERT INTO progress (question_id, user_id, completed, solution) VALUES (?, ?, 0, ?)",
            (question_id, user_id, solution)
        )
    
    conn.commit()
    conn.close()

def toggle_bookmark(question_id, user_id=1):
    """Toggle the bookmark status for a question for a specific user
    
    Args:
        question_id: ID of the question to update
        user_id: ID of the user
        
    Returns:
        The new bookmark status (True if bookmarked, False if not)
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get current bookmark status
    cursor.execute(
        "SELECT bookmarked FROM progress WHERE question_id = ? AND user_id = ?",
        (question_id, user_id)
    )
    result = cursor.fetchone()
    
    if result is not None:
        # Toggle the existing bookmark status
        current_status = result[0]
        new_status = 1 if current_status == 0 else 0
        
        conn.execute(
            "UPDATE progress SET bookmarked = ? WHERE question_id = ? AND user_id = ?",
            (new_status, question_id, user_id)
        )
    else:
        # Create a new record with bookmarked=1
        conn.execute(
            "INSERT INTO progress (question_id, user_id, completed, bookmarked) VALUES (?, ?, 0, 1)",
            (question_id, user_id)
        )
        new_status = 1
    
    conn.commit()
    conn.close()
    
    return new_status == 1  # Return True if bookmarked, False if not

def get_bookmarked_questions(user_id=1):
    """Get all bookmarked questions for a specific user
    
    Args:
        user_id: ID of the user
        
    Returns:
        List of questions that are bookmarked by the user
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT q.id, q.title, q.leetcode_url, q.gfg_url, q.difficulty, t.name as topic,
               p.completed, p.notes, p.solution, p.bookmarked
        FROM questions q
        JOIN topics t ON q.topic_id = t.id
        JOIN progress p ON q.id = p.question_id
        WHERE p.user_id = ? AND p.bookmarked = 1
        ORDER BY t.name, q.difficulty
    """, (user_id,))
    
    questions = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return questions

def get_overall_progress(user_id=1):
    """Get overall progress statistics across all topics for a specific user
    
    Args:
        user_id: ID of the user (defaults to 1 for backward compatibility)
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
    SELECT t.name as topic, 
           COUNT(q.id) as total,
           SUM(CASE WHEN p.completed = 1 THEN 1 ELSE 0 END) as completed
    FROM topics t
    JOIN questions q ON t.id = q.topic_id
    LEFT JOIN (
        SELECT * FROM progress WHERE user_id = ?
    ) p ON q.id = p.question_id
    GROUP BY t.id
    ORDER BY t.name
    """, (user_id,))
    
    results = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return results

def get_questions_dataframe(user_id=1):
    """Get all questions with their progress as a pandas DataFrame for a specific user
    
    Args:
        user_id: ID of the user (defaults to 1 for backward compatibility)
    """
    conn = get_db_connection()
    
    query = """
    SELECT t.name as topic, q.id, q.title, q.leetcode_url, q.gfg_url, q.difficulty, 
           COALESCE(p.completed, 0) as completed
    FROM questions q
    JOIN topics t ON q.topic_id = t.id
    LEFT JOIN (
        SELECT * FROM progress WHERE user_id = ?
    ) p ON q.id = p.question_id
    ORDER BY t.name, q.id
    """
    
    df = pd.read_sql_query(query, conn, params=(user_id,))
    conn.close()
    
    return df

def export_progress(user_id=1):
    """Export progress data to a JSON file for a specific user
    
    Args:
        user_id: ID of the user (defaults to 1 for backward compatibility)
    """
    df = get_questions_dataframe(user_id)
    export_data = df.to_dict(orient='records')
    
    # Add username to the filename for user-specific exports
    if user_id != 1:
        user_info = get_user_info(user_id)
        filename = f"progress_export_{user_info['username'] if user_info else user_id}.json"
    else:
        filename = 'progress_export.json'
    
    with open(filename, 'w') as f:
        json.dump(export_data, f, indent=2)
    
    return filename

def get_next_question_id():
    """Get the next available question ID"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT MAX(id) FROM questions")
    result = cursor.fetchone()
    conn.close()
    return (result[0] or 0) + 1

def add_question(title, leetcode_url, gfg_url, difficulty, topic_id):
    """Add a single question to the database"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get next question ID
    next_id = get_next_question_id()
    
    # Insert the question (handle empty URLs)
    conn.execute("""
        INSERT INTO questions (id, title, leetcode_url, gfg_url, difficulty, topic_id)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (next_id, title, leetcode_url or "", gfg_url or "", difficulty, topic_id))
    
    # Initialize progress for each user in the system
    cursor.execute("SELECT id FROM users")
    user_ids = [row[0] for row in cursor.fetchall()]
    
    if user_ids:
        # If we have users, create progress records for each
        for user_id in user_ids:
            conn.execute("""
                INSERT INTO progress (question_id, user_id, completed)
                VALUES (?, ?, 0)
            """, (next_id, user_id))
    else:
        # Otherwise, create a default progress record (for backward compatibility)
        conn.execute("""
            INSERT INTO progress (question_id, user_id, completed)
            VALUES (?, 1, 0)
        """, (next_id,))
    
    conn.commit()
    conn.close()
    
    return next_id

def add_questions_batch(questions, topic_id):
    """Add multiple questions to the database
    
    questions: List of dictionaries with the following keys:
        - title
        - leetcode_url
        - gfg_url (optional)
        - difficulty
    topic_id: ID of the topic to add the questions to
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get next question ID
    next_id = get_next_question_id()
    
    # Get all user IDs
    cursor.execute("SELECT id FROM users")
    user_ids = [row[0] for row in cursor.fetchall()]
    
    # Insert all questions
    for i, question in enumerate(questions):
        question_id = next_id + i
        
        conn.execute("""
            INSERT INTO questions (id, title, leetcode_url, gfg_url, difficulty, topic_id)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            question_id,
            question['title'],
            question.get('leetcode_url', ""),
            question.get('gfg_url', ""),
            question['difficulty'],
            topic_id
        ))
        
        # Initialize progress for all users
        if user_ids:
            # If we have users, create progress records for each
            for user_id in user_ids:
                conn.execute("""
                    INSERT INTO progress (question_id, user_id, completed)
                    VALUES (?, ?, 0)
                """, (question_id, user_id))
        else:
            # Otherwise, create a default progress record (for backward compatibility)
            conn.execute("""
                INSERT INTO progress (question_id, user_id, completed)
                VALUES (?, 1, 0)
            """, (question_id,))
    
    conn.commit()
    conn.close()
    
    return len(questions)

def verify_admin(username, password):
    """Verify admin credentials
    
    Returns True if credentials are valid, False otherwise
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id FROM admin 
        WHERE username = ? AND password = ?
    """, (username, password))
    
    result = cursor.fetchone()
    conn.close()
    
    return result is not None

def change_admin_password(username, old_password, new_password):
    """Change admin password
    
    Returns True if password was changed successfully, False otherwise
    """
    if not verify_admin(username, old_password):
        return False
    
    conn = get_db_connection()
    conn.execute("""
        UPDATE admin SET password = ?
        WHERE username = ?
    """, (new_password, username))
    
    conn.commit()
    conn.close()
    
    return True

def delete_question(question_id):
    """Delete a question and all of its progress records across all users
    
    Returns True if successful, False otherwise
    """
    conn = get_db_connection()
    try:
        # First delete from progress table for all users (due to foreign key constraint)
        conn.execute("DELETE FROM progress WHERE question_id = ?", (question_id,))
        
        # Then delete from questions table
        conn.execute("DELETE FROM questions WHERE id = ?", (question_id,))
        
        conn.commit()
        success = True
    except Exception as e:
        print(f"Error deleting question: {e}")
        conn.rollback()
        success = False
    finally:
        conn.close()
    
    return success

def get_detailed_progress_by_difficulty(user_id=1):
    """Get detailed progress breakdown by difficulty level for a specific user
    
    Args:
        user_id: ID of the user (defaults to 1 for backward compatibility)
    
    Returns a dictionary with completion stats for each difficulty level
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
    SELECT q.difficulty,
           COUNT(*) as total,
           SUM(CASE WHEN p.completed = 1 THEN 1 ELSE 0 END) as completed
    FROM questions q
    LEFT JOIN (
        SELECT * FROM progress WHERE user_id = ?
    ) p ON q.id = p.question_id
    GROUP BY q.difficulty
    ORDER BY 
        CASE 
            WHEN q.difficulty = 'Easy' THEN 1
            WHEN q.difficulty = 'Medium' THEN 2
            WHEN q.difficulty = 'Hard' THEN 3
            ELSE 4
        END
    """, (user_id,))
    
    results = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return results

def register_user(username, password, email=None):
    """Register a new user
    
    Args:
        username: Username for the new user
        password: Password for the new user
        email: Optional email address
        
    Returns:
        Tuple of (success, message)
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Check if username already exists
        cursor.execute("SELECT COUNT(*) FROM users WHERE username = ?", (username,))
        if cursor.fetchone()[0] > 0:
            conn.close()
            return (False, "Username already exists")
        
        # Check if email already exists (if provided)
        if email:
            cursor.execute("SELECT COUNT(*) FROM users WHERE email = ?", (email,))
            if cursor.fetchone()[0] > 0:
                conn.close()
                return (False, "Email already in use")
        
        # Insert new user
        from datetime import datetime
        cursor.execute("""
            INSERT INTO users (username, password, email, created_at)
            VALUES (?, ?, ?, ?)
        """, (username, password, email, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
        
        user_id = cursor.lastrowid
        
        # Initialize progress records for all questions for this user
        cursor.execute("SELECT id FROM questions")
        question_ids = [row[0] for row in cursor.fetchall()]
        
        for q_id in question_ids:
            cursor.execute("""
                INSERT INTO progress (question_id, user_id, completed)
                VALUES (?, ?, 0)
            """, (q_id, user_id))
        
        conn.commit()
        conn.close()
        return (True, "User registered successfully")
    
    except Exception as e:
        conn.rollback()
        conn.close()
        return (False, f"Error registering user: {str(e)}")

def verify_user(username, password):
    """Verify user credentials
    
    Args:
        username: Username to verify
        password: Password to verify
        
    Returns:
        Tuple of (success, user_id, message)
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT id FROM users WHERE username = ? AND password = ?", (username, password))
    result = cursor.fetchone()
    
    if result:
        user_id = result[0]
        
        # Update last login time
        from datetime import datetime
        cursor.execute(
            "UPDATE users SET last_login = ? WHERE id = ?",
            (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), user_id)
        )
        conn.commit()
        conn.close()
        
        return (True, user_id, "Login successful")
    else:
        conn.close()
        return (False, None, "Invalid username or password")

def get_user_info(user_id):
    """Get user information
    
    Args:
        user_id: ID of the user
        
    Returns:
        Dictionary with user information
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT id, username, email, created_at, last_login FROM users WHERE id = ?", (user_id,))
    result = cursor.fetchone()
    
    conn.close()
    
    if result:
        return dict(result)
    else:
        return None

def get_user_progress(user_id):
    """Get progress statistics for a specific user
    
    Args:
        user_id: ID of the user
        
    Returns:
        Dictionary with progress statistics
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT COUNT(*) as total,
               SUM(CASE WHEN completed = 1 THEN 1 ELSE 0 END) as completed
        FROM progress
        WHERE user_id = ?
    """, (user_id,))
    
    result = dict(cursor.fetchone())
    
    # Get stats by difficulty
    cursor.execute("""
        SELECT q.difficulty,
               COUNT(*) as total,
               SUM(CASE WHEN p.completed = 1 THEN 1 ELSE 0 END) as completed
        FROM questions q
        JOIN progress p ON q.id = p.question_id
        WHERE p.user_id = ?
        GROUP BY q.difficulty
    """, (user_id,))
    
    result['by_difficulty'] = [dict(row) for row in cursor.fetchall()]
    
    # Get stats by topic
    cursor.execute("""
        SELECT t.name as topic,
               COUNT(*) as total,
               SUM(CASE WHEN p.completed = 1 THEN 1 ELSE 0 END) as completed
        FROM topics t
        JOIN questions q ON t.id = q.topic_id
        JOIN progress p ON q.id = p.question_id
        WHERE p.user_id = ?
        GROUP BY t.id
    """, (user_id,))
    
    result['by_topic'] = [dict(row) for row in cursor.fetchall()]
    
    conn.close()
    return result

def get_progress_by_week(user_id=1):
    """Get progress over the last few weeks for a specific user
    
    Args:
        user_id: ID of the user (defaults to 1 for backward compatibility)
    
    This is a placeholder - in a real app, you would track when questions were completed
    """
    # Since we don't track when questions were completed, we'll generate some sample data
    # In a real app, you would store completion dates and query based on those
    
    # For demonstration purposes only
    import random
    from datetime import datetime, timedelta
    
    weeks = []
    today = datetime.now()
    
    # Generate the last 12 weeks
    for i in range(12):
        week_start = today - timedelta(days=today.weekday() + 7*i)
        week_label = f"{week_start.strftime('%b %d')}"
        
        # Generate data by difficulty
        easy = random.randint(2, 8)
        medium = random.randint(1, 6)
        hard = random.randint(0, 3)
        total = easy + medium + hard
        
        weeks.append({
            "week": week_label,
            "questions_completed": total,
            "easy": easy,
            "medium": medium,
            "hard": hard
        })
    
    # Reverse to show oldest to newest
    weeks.reverse()
    
    return weeks

def get_all_users():
    """Get all user accounts from the database
    
    Returns:
        List of dictionaries with user information (id, username, email, created_at)
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id, username, email, created_at, last_login
        FROM users
        ORDER BY id
    """)
    
    users = []
    for row in cursor.fetchall():
        users.append({
            'id': row[0],
            'username': row[1],
            'email': row[2] or "Not provided",
            'created_at': row[3],
            'last_login': row[4] or "Never"
        })
    
    conn.close()
    return users

def add_admin(username, password, update_if_exists=False):
    """Add a new admin or update existing admin credentials
    
    Args:
        username: Username for the admin
        password: Password for the admin
        update_if_exists: If True, update the password if the username already exists
        
    Returns:
        Tuple of (success, message)
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Check if admin already exists
    cursor.execute("SELECT COUNT(*) FROM admin WHERE username = ?", (username,))
    admin_exists = cursor.fetchone()[0] > 0
    
    try:
        if admin_exists:
            if update_if_exists:
                # Update existing admin password
                cursor.execute("""
                    UPDATE admin SET password = ?
                    WHERE username = ?
                """, (password, username))
                message = f"Updated admin '{username}' successfully"
            else:
                conn.close()
                return (False, f"Admin '{username}' already exists")
        else:
            # Insert new admin
            cursor.execute("""
                INSERT INTO admin (username, password)
                VALUES (?, ?)
            """, (username, password))
            message = f"Added new admin '{username}' successfully"
        
        conn.commit()
        conn.close()
        return (True, message)
    except Exception as e:
        conn.close()
        return (False, f"Error: {str(e)}")
