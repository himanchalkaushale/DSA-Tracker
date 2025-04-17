import psycopg2
from psycopg2 import sql
import json
import pandas as pd
from datetime import datetime

# Replace with your Neon PostgreSQL connection URL
DB_URL = "postgresql://dsatracker_owner:npg_aTJN6H8lGjvV@ep-cold-poetry-a4g2htwv-pooler.us-east-1.aws.neon.tech/dsatracker?sslmode=require"

def get_db_connection():
    """Create a connection to the PostgreSQL database using a connection URL"""
    conn = psycopg2.connect(DB_URL)
    return conn

def initialize_database():
    """Initialize the database with necessary tables"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Create tables
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS topics (
        id SERIAL PRIMARY KEY,
        name TEXT NOT NULL UNIQUE
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS questions (
        id SERIAL PRIMARY KEY,
        title TEXT NOT NULL,
        leetcode_url TEXT NOT NULL,
        gfg_url TEXT,
        difficulty TEXT NOT NULL,
        topic_id INTEGER NOT NULL,
        FOREIGN KEY (topic_id) REFERENCES topics (id)
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
        username TEXT NOT NULL UNIQUE,
        password TEXT NOT NULL,
        email TEXT UNIQUE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_login TIMESTAMP
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS progress (
        id SERIAL PRIMARY KEY,
        question_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        completed BOOLEAN NOT NULL DEFAULT FALSE,
        completed_at TIMESTAMP,
        FOREIGN KEY (question_id) REFERENCES questions (id),
        FOREIGN KEY (user_id) REFERENCES users (id),
        UNIQUE (question_id, user_id)
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS admin (
        id SERIAL PRIMARY KEY,
        username TEXT NOT NULL UNIQUE,
        password TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    # Add default admin if none exists
    cursor.execute("SELECT COUNT(*) FROM admin")
    admin_count = cursor.fetchone()[0]

    if admin_count == 0:
        cursor.execute('''
        INSERT INTO admin (username, password)
        VALUES ('admin', 'admin123')
        ''')
        print("Added default admin user: admin/admin123")

    conn.commit()
    cursor.close()
    conn.close()

def load_initial_data():
    """Load initial data from questions.json into the database if it's not already there"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Check if we already have data
    cursor.execute("SELECT COUNT(*) FROM questions")
    count = cursor.fetchone()[0]
    
    if count > 0:
        cursor.close()
        conn.close()
        return  # Data already exists, don't reload

    # Load data from JSON file
    with open('questions.json', 'r') as f:
        questions_data = json.load(f)

    # Insert topics
    for topic_name in questions_data.keys():
        cursor.execute("INSERT INTO topics (name) VALUES (%s) ON CONFLICT (name) DO NOTHING", (topic_name,))
        conn.commit()

    # Get topic IDs
    cursor.execute("SELECT id, name FROM topics")
    topic_ids = {row[1]: row[0] for row in cursor.fetchall()}

    # Insert questions
    for topic_name, questions in questions_data.items():
        topic_id = topic_ids[topic_name]
        for question in questions:
            gfg_url = question.get('gfg_url', None)
            cursor.execute('''
                INSERT INTO questions (title, leetcode_url, gfg_url, difficulty, topic_id)
                VALUES (%s, %s, %s, %s, %s)
            ''', (
                question['title'],
                question['leetcode_url'],
                gfg_url,
                question['difficulty'],
                topic_id
            ))

    conn.commit()
    cursor.close()
    conn.close()


def get_topics():
    """Get all topics from the database"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name FROM topics ORDER BY name")
    topics = [{'id': row[0], 'name': row[1]} for row in cursor.fetchall()]
    conn.close()
    return topics

def get_questions_by_topic(topic_id, search_query=None, difficulty=None, user_id=1):
    """Get questions for a specific topic with optional filtering"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    query = '''
    SELECT q.id, q.title, q.leetcode_url, q.gfg_url, q.difficulty, 
           COALESCE(p.completed, FALSE) as completed
    FROM questions q
    LEFT JOIN progress p ON q.id = p.question_id AND p.user_id = %s
    WHERE q.topic_id = %s
    '''
    params = [user_id, topic_id]
    
    if search_query:
        query += " AND q.title ILIKE %s"
        params.append(f'%{search_query}%')
    
    if difficulty and difficulty != "All":
        query += " AND q.difficulty = %s"
        params.append(difficulty)
    
    cursor.execute(query, params)
    questions = [{'id': row[0], 'title': row[1], 'leetcode_url': row[2], 'gfg_url': row[3], 'difficulty': row[4], 'completed': row[5]} for row in cursor.fetchall()]
    conn.close()
    return questions

def update_question_progress(question_id, completed, user_id=1):
    """Update the completion status of a question for a specific user"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get current timestamp if the question is being marked as completed
    completed_at = datetime.now() if completed else None

    cursor.execute('''
        INSERT INTO progress (question_id, user_id, completed, completed_at)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (question_id, user_id) DO UPDATE
        SET completed = EXCLUDED.completed, completed_at = EXCLUDED.completed_at
    ''', (question_id, user_id, completed, completed_at))
    
    conn.commit()
    cursor.close()
    conn.close()

def get_questions_dataframe(user_id=1):
    """Get questions and their progress as a DataFrame for a specific user"""
    conn = get_db_connection()
    query = '''
    SELECT q.id, q.title, q.leetcode_url, q.gfg_url, q.difficulty, 
           COALESCE(p.completed, FALSE) as completed
    FROM questions q
    LEFT JOIN progress p ON q.id = p.question_id AND p.user_id = %s
    '''
    df = pd.read_sql_query(query, conn, params=(user_id,))
    conn.close()
    return df

def get_overall_progress(user_id=1):
    """Get overall progress statistics for a specific user"""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
    SELECT 
        COUNT(*) as total_questions,
        SUM(CASE WHEN p.completed = TRUE THEN 1 ELSE 0 END) as completed_questions
    FROM questions q
    LEFT JOIN progress p ON q.id = p.question_id AND p.user_id = %s
    ''', (user_id,))

    stats = cursor.fetchone()
    conn.close()

    return {
        'total_questions': stats[0],
        'completed_questions': stats[1],
        'completion_percentage': (stats[1] / stats[0]) * 100 if stats[0] > 0 else 0
    }

def export_progress(user_id=1):
    """Export progress data to a JSON file for a specific user"""
    conn = get_db_connection()
    query = '''
    SELECT t.name as topic, q.id, q.title, q.leetcode_url, q.gfg_url, q.difficulty, 
           COALESCE(p.completed, FALSE) as completed
    FROM questions q
    JOIN topics t ON q.topic_id = t.id
    LEFT JOIN progress p ON q.id = p.question_id AND p.user_id = %s
    ORDER BY t.name, q.id
    '''
    df = pd.read_sql_query(query, conn, params=(user_id,))
    conn.close()
    
    filename = f'progress_export_user_{user_id}.json'
    df.to_json(filename, orient='records', indent=2)
    return filename

def get_topic_stats(topic_id, user_id=1):
    """Get completion statistics for a topic for a specific user"""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
    SELECT COUNT(*) as total,
           SUM(CASE WHEN p.completed = TRUE THEN 1 ELSE 0 END) as completed
    FROM questions q
    LEFT JOIN progress p ON q.id = p.question_id AND p.user_id = %s
    WHERE q.topic_id = %s
    ''', (user_id, topic_id))

    stats = cursor.fetchone()
    conn.close()

    return {'total': stats[0], 'completed': stats[1]}


def update_question_notes(question_id, notes, user_id=1):
    """Update the notes for a question for a specific user"""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
        INSERT INTO progress (question_id, user_id, notes)
        VALUES (%s, %s, %s)
        ON CONFLICT (question_id, user_id) DO UPDATE
        SET notes = EXCLUDED.notes
    ''', (question_id, user_id, notes))

    conn.commit()
    cursor.close()
    conn.close()


def update_question_solution(question_id, solution, user_id=1):
    """Update the solution for a question for a specific user"""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
        INSERT INTO progress (question_id, user_id, solution)
        VALUES (%s, %s, %s)
        ON CONFLICT (question_id, user_id) DO UPDATE
        SET solution = EXCLUDED.solution
    ''', (question_id, user_id, solution))

    conn.commit()
    cursor.close()
    conn.close()


def toggle_bookmark(question_id, user_id=1):
    """Toggle the bookmark status for a question for a specific user"""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT bookmarked FROM progress WHERE question_id = %s AND user_id = %s
    ''', (question_id, user_id))
    result = cursor.fetchone()

    if result is not None:
        new_status = not result[0]  # Toggle the current status
        cursor.execute('''
            UPDATE progress SET bookmarked = %s WHERE question_id = %s AND user_id = %s
        ''', (new_status, question_id, user_id))
    else:
        new_status = True
        cursor.execute('''
            INSERT INTO progress (question_id, user_id, bookmarked)
            VALUES (%s, %s, %s)
        ''', (question_id, user_id, new_status))

    conn.commit()
    cursor.close()
    conn.close()

    return new_status


def get_bookmarked_questions(user_id=1):
    """Get all bookmarked questions for a specific user"""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT q.id, q.title, q.leetcode_url, q.gfg_url, q.difficulty, t.name as topic,
               p.completed, p.notes, p.solution, p.bookmarked
        FROM questions q
        JOIN topics t ON q.topic_id = t.id
        JOIN progress p ON q.id = p.question_id
        WHERE p.user_id = %s AND p.bookmarked = TRUE
        ORDER BY t.name, q.difficulty
    ''', (user_id,))

    questions = [{'id': row[0], 'title': row[1], 'leetcode_url': row[2], 'gfg_url': row[3], 'difficulty': row[4],
                  'topic': row[5], 'completed': row[6], 'notes': row[7], 'solution': row[8], 'bookmarked': row[9]}
                 for row in cursor.fetchall()]
    conn.close()

    return questions


def get_detailed_progress_by_difficulty(user_id=1):
    """Get detailed progress breakdown by difficulty level for a specific user"""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
    SELECT q.difficulty,
           COUNT(*) as total,
           SUM(CASE WHEN p.completed = TRUE THEN 1 ELSE 0 END) as completed
    FROM questions q
    LEFT JOIN progress p ON q.id = p.question_id AND p.user_id = %s
    GROUP BY q.difficulty
    ORDER BY 
        CASE 
            WHEN q.difficulty = 'Easy' THEN 1
            WHEN q.difficulty = 'Medium' THEN 2
            WHEN q.difficulty = 'Hard' THEN 3
            ELSE 4
        END
    ''', (user_id,))

    results = [{'difficulty': row[0], 'total': row[1], 'completed': row[2]} for row in cursor.fetchall()]
    conn.close()

    return results


def get_all_users():
    """Get all user accounts from the database"""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT id, username, email, created_at, last_login
        FROM users
        ORDER BY id
    ''')

    users = [{'id': row[0], 'username': row[1], 'email': row[2], 'created_at': row[3], 'last_login': row[4]}
             for row in cursor.fetchall()]
    conn.close()

    return users


def register_user(username, password, email=None):
    """Register a new user"""
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute('''
            INSERT INTO users (username, password, email, created_at)
            VALUES (%s, %s, %s, %s)
        ''', (username, password, email, datetime.now()))

        conn.commit()
        success = True
        message = "User registered successfully"
    except psycopg2.Error as e:
        conn.rollback()
        success = False
        message = f"Error registering user: {e}"
    finally:
        cursor.close()
        conn.close()

    return success, message
