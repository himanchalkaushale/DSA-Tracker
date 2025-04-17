import streamlit as st
import pandas as pd
import plotly.express as px
import json
import os
import sqlite3
from database import get_questions_dataframe
from database import get_overall_progress
from database import (
    initialize_database, 
    load_initial_data, 
    get_topics, 
    get_questions_by_topic,
    get_topic_stats, 
    update_question_progress,
    get_questions_dataframe,
    export_progress,
    add_question,
    add_questions_batch,
    verify_admin,
    change_admin_password,
    delete_question,
    get_detailed_progress_by_difficulty,
    get_progress_by_week,
    # User authentication and tracking functions
    register_user,
    verify_user,
    get_user_info,
    get_user_progress,
    # New functions for notes, solutions, and bookmarks
    update_question_notes,
    update_question_solution,
    toggle_bookmark,
    get_bookmarked_questions,
    # Admin management functions
    get_all_users,
    add_admin
)
from utils import (
    get_difficulty_color, 
    create_topic_card, 
    format_question_item,
    show_topic_progress
)

# Page configuration
st.set_page_config(
    page_title="DSA Cracker",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Initialize the database if it doesn't exist
initialize_database()
load_initial_data()

# Set up session state for tracking the current page and other state
if 'current_page' not in st.session_state:
    st.session_state.current_page = 'home'
if 'current_topic_id' not in st.session_state:
    st.session_state.current_topic_id = None
if 'search_query' not in st.session_state:
    st.session_state.search_query = ""
if 'difficulty_filter' not in st.session_state:
    st.session_state.difficulty_filter = "All"
if 'batch_questions' not in st.session_state:
    st.session_state.batch_questions = "[]"
if 'admin_logged_in' not in st.session_state:
    st.session_state.admin_logged_in = False
if 'show_admin_login' not in st.session_state:
    st.session_state.show_admin_login = False
if 'confirm_delete' not in st.session_state:
    st.session_state.confirm_delete = False
# User authentication session state
if 'user_logged_in' not in st.session_state:
    st.session_state.user_logged_in = False
if 'user_id' not in st.session_state:
    st.session_state.user_id = 1  # Default user ID for backward compatibility
if 'show_user_login' not in st.session_state:
    st.session_state.show_user_login = False
if 'show_register' not in st.session_state:
    st.session_state.show_register = False
if 'login_error' not in st.session_state:
    st.session_state.login_error = None
if 'register_error' not in st.session_state:
    st.session_state.register_error = None
# New session state variables for notes, solutions, and bookmarks
if 'show_notes' not in st.session_state:
    st.session_state.show_notes = {}
if 'show_solution' not in st.session_state:
    st.session_state.show_solution = {}

# Add a small CSS to improve UI elements
st.markdown("""
<style>
.stButton>button {
    border-radius: 6px !important;
    font-weight: 600 !important;
    transition: all 0.3s ease;
}
</style>
""", unsafe_allow_html=True)

def navigate_to_topic(topic_id):
    """Navigate to a specific topic page"""
    st.session_state.current_page = 'topic'
    st.session_state.current_topic_id = topic_id
    st.rerun()

def navigate_to_home():
    """Navigate back to the home page"""
    st.session_state.current_page = 'home'
    st.rerun()

def navigate_to_dashboard():
    """Navigate to the progress dashboard"""
    st.session_state.current_page = 'dashboard'
    st.rerun()

def navigate_to_manage():
    """Navigate to the manage questions page"""
    st.session_state.current_page = 'manage'
    st.rerun()

def update_progress(question_id):
    """Update the progress of a question in the database"""
    checkbox_key = f"question_{question_id}"
    completed = st.session_state[checkbox_key]
    # Use the current user's ID when updating progress
    user_id = st.session_state.user_id
    update_question_progress(question_id, completed, user_id)
    
def save_notes(question_id, notes):
    """Save notes for a question"""
    user_id = st.session_state.user_id
    update_question_notes(question_id, notes, user_id)
    st.success("Notes saved successfully!")
    
def save_solution(question_id, solution):
    """Save solution for a question"""
    user_id = st.session_state.user_id
    update_question_solution(question_id, solution, user_id)
    st.success("Solution saved successfully!")
    
def bookmark_question(question_id):
    """Toggle bookmark status for a question"""
    user_id = st.session_state.user_id
    is_bookmarked = toggle_bookmark(question_id, user_id)
    if is_bookmarked:
        st.success("Question bookmarked!")
    else:
        st.info("Bookmark removed.")
    return is_bookmarked
    
def navigate_to_bookmarks():
    """Navigate to the bookmarks page"""
    st.session_state.current_page = 'bookmarks'
    st.rerun()

# User authentication functions
def toggle_user_login():
    """Toggle the display of the user login form"""
    st.session_state.show_user_login = not st.session_state.show_user_login
    st.session_state.show_register = False

def toggle_register():
    """Toggle the display of the user registration form"""
    st.session_state.show_register = not st.session_state.show_register
    st.session_state.show_user_login = False

def user_login(username, password):
    """Attempt to log in a user with the provided credentials"""
    success, user_id, message = verify_user(username, password)
    if success:
        st.session_state.user_logged_in = True
        st.session_state.user_id = user_id
        st.session_state.show_user_login = False
        st.session_state.login_error = None
        st.success("Login successful! Welcome back, " + username)
        st.rerun()
    else:
        st.session_state.login_error = message

def user_logout():
    """Log out the current user"""
    st.session_state.user_logged_in = False
    st.session_state.user_id = 1  # Reset to default user
    st.rerun()

def user_register(username, password, email=None):
    """Register a new user with the provided information"""
    success, message = register_user(username, password, email)
    if success:
        st.session_state.show_register = False
        st.session_state.register_error = None
        st.success(message + " You can now log in.")
        # Automatically show login form after successful registration
        st.session_state.show_user_login = True
        st.rerun()
    else:
        st.session_state.register_error = message

def navigate_to_profile():
    """Navigate to the user profile page"""
    st.session_state.current_page = 'profile'
    st.rerun()

# Toggle admin login
def toggle_admin_login():
    st.session_state.show_admin_login = not st.session_state.show_admin_login

# Admin login function
def admin_login(username, password):
    if verify_admin(username, password):
        st.session_state.admin_logged_in = True
        st.session_state.show_admin_login = False
        st.success("Admin login successful!")
        st.rerun()
    else:
        st.error("Invalid username or password")

# Admin logout function
def admin_logout():
    st.session_state.admin_logged_in = False
    st.rerun()
    
# Theme function has been removed

# Sidebar navigation
with st.sidebar:
    st.title("DSA Cracker")
    st.markdown("Navigate between topics to practice Data Structures and Algorithms challenges.")
    
    # User authentication section
    user_auth_container = st.container()
    with user_auth_container:
        if st.session_state.user_logged_in:
            user_info = get_user_info(st.session_state.user_id)
            if user_info:
                st.markdown(f"### Welcome, {user_info['username']}! 👋")
                
                # Show user profile/dashboard button
                if st.button("My Profile", use_container_width=True):
                    navigate_to_profile()
                    
                # User logout button
                if st.button("Log Out", type="secondary", use_container_width=True):
                    user_logout()
        else:
            # User login/register buttons
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Log In", key="login_btn", use_container_width=True):
                    toggle_user_login()
                    st.session_state.show_register = False
            with col2:
                if st.button("Register", key="register_btn", use_container_width=True):
                    toggle_register()
                    st.session_state.show_user_login = False
            
            # User login form
            if st.session_state.show_user_login:
                with st.form("user_login_form"):
                    st.subheader("User Login")
                    user_username = st.text_input("Username")
                    user_password = st.text_input("Password", type="password")
                    
                    # Show login error if any
                    if st.session_state.login_error:
                        st.error(st.session_state.login_error)
                    
                    login_cols = st.columns([1, 1])
                    with login_cols[0]:
                        if st.form_submit_button("Cancel"):
                            st.session_state.show_user_login = False
                            st.rerun()
                    with login_cols[1]:
                        if st.form_submit_button("Login"):
                            if user_username and user_password:
                                user_login(user_username, user_password)
                            else:
                                st.warning("Username and password are required")
            
            # User registration form
            if st.session_state.show_register:
                with st.form("user_register_form"):
                    st.subheader("Register New Account")
                    new_username = st.text_input("Username")
                    new_password = st.text_input("Password", type="password")
                    confirm_password = st.text_input("Confirm Password", type="password")
                    email = st.text_input("Email (optional)")
                    
                    # Show registration error if any
                    if st.session_state.register_error:
                        st.error(st.session_state.register_error)
                    
                    reg_cols = st.columns([1, 1])
                    with reg_cols[0]:
                        if st.form_submit_button("Cancel"):
                            st.session_state.show_register = False
                            st.rerun()
                    with reg_cols[1]:
                        if st.form_submit_button("Register"):
                            if not new_username or not new_password:
                                st.warning("Username and password are required")
                            elif new_password != confirm_password:
                                st.error("Passwords do not match")
                            else:
                                user_register(new_username, new_password, email if email else None)
    
    st.markdown("---")
    
    # Navigation buttons
    if st.button("Home", use_container_width=True):
        navigate_to_home()
    
    if st.button("Progress Dashboard", use_container_width=True):
        navigate_to_dashboard()
        
    if st.session_state.user_logged_in:
        if st.button("My Bookmarks", use_container_width=True):
            navigate_to_bookmarks()
    
    # Admin section - only show if admin is logged in or show login form
    if st.session_state.admin_logged_in:
        if st.button("Manage Questions", use_container_width=True):
            navigate_to_manage()
        
        # Add admin logout button
        if st.button("Admin Logout", type="secondary", use_container_width=True):
            admin_logout()
    else:
        # Show Admin Login button
        if st.button("Admin Login", type="secondary", use_container_width=True):
            toggle_admin_login()
        
        # Show login form if button was clicked
        if st.session_state.show_admin_login:
            with st.form("admin_login_form"):
                st.subheader("Admin Login")
                admin_username = st.text_input("Username")
                admin_password = st.text_input("Password", type="password")
                
                login_submit = st.form_submit_button("Login", use_container_width=True)
                
                if login_submit:
                    admin_login(admin_username, admin_password)
    
    st.markdown("---")
    st.subheader("Topics")
    
    topics = get_topics()
    for topic in topics:
        if st.button(topic['name'], key=f"sidebar_topic_{topic['id']}", use_container_width=True):
            navigate_to_topic(topic['id'])

# Main content area
if st.session_state.current_page == 'bookmarks':
    st.title("My Bookmarked Questions")
    
    if not st.session_state.user_logged_in:
        st.warning("Please log in to view your bookmarked questions.")
        if st.button("Go to Home"):
            navigate_to_home()
    else:
        # Get bookmarked questions for the current user
        bookmarked_questions = get_bookmarked_questions(st.session_state.user_id)
        
        if not bookmarked_questions:
            st.info("You haven't bookmarked any questions yet.")
            st.markdown("Bookmark questions by clicking the bookmark button on any question you want to save for later.")
            
            if st.button("Go to Home"):
                navigate_to_home()
        else:
            st.success(f"You have {len(bookmarked_questions)} bookmarked questions.")
            
            # Group questions by topic
            questions_by_topic = {}
            for question in bookmarked_questions:
                topic = question['topic']
                if topic not in questions_by_topic:
                    questions_by_topic[topic] = []
                questions_by_topic[topic].append(question)
            
            # Create tabs for each topic
            topic_tabs = st.tabs(list(questions_by_topic.keys()))
            
            for i, (topic, questions) in enumerate(questions_by_topic.items()):
                with topic_tabs[i]:
                    st.markdown(f"### {topic} ({len(questions)} questions)")
                    
                    # Display questions for this topic
                    for question in questions:
                        # Pass all required functions to format_question_item
                        question['save_notes_fn'] = save_notes
                        question['save_solution_fn'] = save_solution
                        question['bookmark_fn'] = bookmark_question
                        format_question_item(question, update_progress)
            
            # Option to clear all bookmarks
            with st.expander("Clear Bookmarks"):
                st.warning("This will remove all your bookmarks. This action cannot be undone.")
                if st.button("Clear All Bookmarks"):
                    # TODO: Implement a function to clear all bookmarks
                    st.error("This feature is not yet implemented.")

elif st.session_state.current_page == 'profile':
    st.title("User Profile")
    
    if not st.session_state.user_logged_in:
        st.warning("Please log in to view your profile.")
        if st.button("Go to Home"):
            navigate_to_home()
    else:
        user_info = get_user_info(st.session_state.user_id)
        if not user_info:
            st.error("User information not found!")
        else:
            # User info section
            st.header(f"👤 {user_info['username']}'s Profile")
            
            # Create two columns for user info
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("### Account Information")
                st.markdown(f"**Username:** {user_info['username']}")
                st.markdown(f"**Email:** {user_info['email'] or 'Not provided'}")
                st.markdown(f"**Account Created:** {user_info['created_at']}")
                st.markdown(f"**Last Login:** {user_info['last_login'] or 'Not available'}")
            
            # Get user progress statistics
            user_progress = get_user_progress(st.session_state.user_id)
            
            with col2:
                st.markdown("### Progress Summary")
                
                total = user_progress['total']
                completed = user_progress['completed']
                
                if total > 0:
                    progress_pct = int((completed / total) * 100)
                    st.progress(progress_pct / 100)
                    st.markdown(f"**Overall Completion:** {completed}/{total} questions ({progress_pct}%)")
                else:
                    st.info("No progress data available.")
            
            # Progress by difficulty
            st.header("Progress by Difficulty")
            diff_cols = st.columns(3)
            
            for i, diff_data in enumerate(user_progress.get('by_difficulty', [])):
                with diff_cols[i % 3]:
                    diff = diff_data['difficulty']
                    diff_total = diff_data['total']
                    diff_completed = diff_data['completed']
                    
                    if diff_total > 0:
                        diff_pct = int((diff_completed / diff_total) * 100)
                        color = "#48BB78" if diff == "Easy" else "#ECC94B" if diff == "Medium" else "#F56565"
                        
                        st.markdown(f"### {diff}")
                        st.progress(diff_pct / 100)
                        st.markdown(f"**{diff_completed}/{diff_total}** ({diff_pct}%)")
            
            # Progress by topic
            st.header("Progress by Topic")
            
            # Calculate completion percentages
            topic_data = user_progress.get('by_topic', [])
            if topic_data:
                for topic in topic_data:
                    if topic['total'] > 0:
                        topic['percentage'] = int((topic['completed'] / topic['total']) * 100)
                    else:
                        topic['percentage'] = 0
                
                # Create a DataFrame for the progress chart
                df_topics = pd.DataFrame(topic_data)
                
                # Create a bar chart for topic progress
                fig = px.bar(
                    df_topics,
                    x='topic',
                    y='percentage',
                    title="Topic Completion Percentage",
                    labels={'percentage': 'Completion %', 'topic': 'Topic'},
                    color='percentage',
                    color_continuous_scale=px.colors.sequential.Viridis,
                )
                fig.update_layout(xaxis_tickangle=-45)
                st.plotly_chart(fig, use_container_width=True)
                
                # Display topic progress as a table
                for topic in topic_data:
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.markdown(f"**{topic['topic']}**")
                        st.progress(topic['percentage'] / 100)
                    with col2:
                        st.markdown(f"**{topic['completed']}/{topic['total']}** ({topic['percentage']}%)")
            else:
                st.info("No topic progress data available.")

elif st.session_state.current_page == 'home':
    st.title("DSA Cracker")
    st.markdown("### Your Gateway to crack DSA 🔥")
    st.markdown("#### Start Solving")
    
    topics_data = get_overall_progress(st.session_state.user_id)
    
    # Create a grid layout for the topics
    col1, col2 = st.columns(2)
    
    for i, topic_data in enumerate(topics_data):
        with col1 if i % 2 == 0 else col2:
            with st.container():
                st.markdown(f"### {topic_data['topic']}")
                st.markdown(f"Total Questions: {topic_data['total']}")
                
                if topic_data['completed'] == 0:
                    st.markdown("**_Not yet started_**")
                else:
                    progress_pct = int((topic_data['completed'] / topic_data['total']) * 100)
                    st.progress(progress_pct / 100)
                    st.markdown(f"**_Progress: {topic_data['completed']}/{topic_data['total']} ({progress_pct}%)_**")
                
                if st.button("Start Now", key=f"home_topic_{i}", use_container_width=True):
                    # Find the topic_id for this topic name
                    for t in topics:
                        if t['name'] == topic_data['topic']:
                            navigate_to_topic(t['id'])
                            break
                
                st.markdown("---")

elif st.session_state.current_page == 'topic':
    # Get the current topic details
    current_topic_id = st.session_state.current_topic_id
    current_topic = None
    
    for topic in topics:
        if topic['id'] == current_topic_id:
            current_topic = topic
            break
    
    if not current_topic:
        st.error("Topic not found!")
        if st.button("Go back to Home"):
            navigate_to_home()
    else:
        st.title(f"{current_topic['name']} Questions")
        
        # Search and filter controls
        col1, col2, col3 = st.columns([3, 2, 1])
        
        with col1:
            search_query = st.text_input(
                "Search by question title",
                value=st.session_state.search_query
            )
            st.session_state.search_query = search_query
        
        with col2:
            difficulty_filter = st.selectbox(
                "Filter by difficulty",
                ["All", "Easy", "Medium", "Hard"],
                index=["All", "Easy", "Medium", "Hard"].index(st.session_state.difficulty_filter)
            )
            st.session_state.difficulty_filter = difficulty_filter
        
        with col3:
            if st.button("Reset Filters", use_container_width=True):
                st.session_state.search_query = ""
                st.session_state.difficulty_filter = "All"
                st.rerun()
        
        # Get topic statistics and show progress
        topic_stats = get_topic_stats(current_topic_id, st.session_state.user_id)
        show_topic_progress(topic_stats)
        
        # Get questions for this topic with filters applied
        questions = get_questions_by_topic(
            current_topic_id, 
            search_query=search_query if search_query else None,
            difficulty=difficulty_filter if difficulty_filter != "All" else None,
            user_id=st.session_state.user_id
        )
        
        # Display questions
        if not questions:
            st.info("No questions found with the current filters.")
        else:
            for question in questions:
                # Pass all required functions to format_question_item
                question['save_notes_fn'] = save_notes
                question['save_solution_fn'] = save_solution
                question['bookmark_fn'] = bookmark_question
                format_question_item(question, update_progress)

elif st.session_state.current_page == 'dashboard':
    st.title("Progress Dashboard")
    
    # Get overall progress data for the current user
    progress_data = get_overall_progress(st.session_state.user_id)
    
    # Calculate total progress
    total_questions = sum(item['total'] for item in progress_data)
    total_completed = sum(item['completed'] for item in progress_data)
    
    if total_questions > 0:
        overall_percent = int((total_completed / total_questions) * 100)
        
        # Display overall progress
        st.markdown(f"## Overall Progress: {overall_percent}%")
        st.progress(overall_percent / 100)
        st.markdown(f"### {total_completed} out of {total_questions} questions completed")
        
        # Create a DataFrame for visualization
        df = pd.DataFrame(progress_data)
        
        # Add percentage column
        df['percentage'] = df.apply(
            lambda row: 0 if row['total'] == 0 else (row['completed'] / row['total']) * 100, 
            axis=1
        )
        
        # Create charts
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Progress by Topic")
            fig = px.bar(
                df,
                x='topic',
                y='percentage',
                title="Completion Percentage by Topic",
                labels={'percentage': 'Completion %', 'topic': 'Topic'},
                color='percentage',
                color_continuous_scale=px.colors.sequential.Viridis,
            )
            fig.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.subheader("Questions by Topic")
            fig = px.bar(
                df,
                x='topic',
                y=['completed', 'total'],
                title="Completed vs Total Questions by Topic",
                labels={'value': 'Number of Questions', 'topic': 'Topic', 'variable': 'Status'},
                barmode='overlay',
                opacity=0.7,
            )
            fig.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig, use_container_width=True)
        
        # Add detailed progress by difficulty
        st.subheader("Progress by Difficulty")
        diff_data = get_detailed_progress_by_difficulty(st.session_state.user_id)
        
        # Convert to dataframe for display
        df_diff = pd.DataFrame(diff_data)
        
        # Add percentage column
        df_diff['percentage'] = df_diff.apply(
            lambda row: 0 if row['total'] == 0 else (row['completed'] / row['total']) * 100, 
            axis=1
        )
        
        # Create a three-column layout for difficulty stats
        col1, col2, col3 = st.columns(3)
        
        # Display statistics by difficulty
        for i, diff in enumerate(['Easy', 'Medium', 'Hard']):
            diff_row = df_diff[df_diff['difficulty'] == diff]
            if not diff_row.empty:
                col = col1 if i == 0 else col2 if i == 1 else col3
                with col:
                    diff_total = int(diff_row['total'].values[0])
                    diff_completed = int(diff_row['completed'].values[0])
                    diff_pct = 0 if diff_total == 0 else int((diff_completed / diff_total) * 100)
                    
                    st.metric(
                        label=f"{diff} Questions", 
                        value=f"{diff_completed}/{diff_total}",
                        delta=f"{diff_pct}%"
                    )
                    st.progress(diff_pct / 100)
        
        # Add weekly progress chart
        st.subheader("Weekly Progress")
        weekly_data = get_progress_by_week(st.session_state.user_id)
        df_weekly = pd.DataFrame(weekly_data)
        
        # Create tabs for different visualizations
        weekly_tab1, weekly_tab2 = st.tabs(["Total Progress", "Progress by Difficulty"])
        
        with weekly_tab1:
            # Total progress line chart
            fig = px.line(
                df_weekly,
                x='week',
                y='questions_completed',
                title="Questions Completed per Week",
                labels={'questions_completed': 'Questions Completed', 'week': 'Week'},
                markers=True,
                line_shape='spline',
                color_discrete_sequence=['#4299E1']
            )
            fig.update_traces(mode='lines+markers', line=dict(width=3), marker=dict(size=8))
            fig.update_layout(
                hovermode="x unified",
                hoverlabel=dict(bgcolor="white", font_size=12)
            )
            st.plotly_chart(fig, use_container_width=True)
            
        with weekly_tab2:
            # Stacked area chart by difficulty
            fig = px.area(
                df_weekly,
                x='week',
                y=['easy', 'medium', 'hard'],
                title="Questions Completed by Difficulty",
                labels={
                    'value': 'Questions Completed', 
                    'week': 'Week', 
                    'variable': 'Difficulty'
                },
                color_discrete_map={
                    'easy': '#48BB78',    # Green for easy
                    'medium': '#ECC94B',  # Yellow for medium
                    'hard': '#F56565'     # Red for hard
                }
            )
            fig.update_layout(
                hovermode="x unified",
                hoverlabel=dict(bgcolor="white", font_size=12),
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="right",
                    x=1
                )
            )
            # Update names in the legend
            newnames = {'easy': 'Easy', 'medium': 'Medium', 'hard': 'Hard'}
            fig.for_each_trace(lambda t: t.update(name = newnames[t.name]))
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Display the weekly data in a table
            st.markdown("### Weekly Breakdown")
            df_display = df_weekly.copy()
            df_display = df_display.rename(columns={
                'week': 'Week', 
                'questions_completed': 'Total', 
                'easy': 'Easy', 
                'medium': 'Medium', 
                'hard': 'Hard'
            })
            st.dataframe(
                df_display[['Week', 'Total', 'Easy', 'Medium', 'Hard']],
                use_container_width=True
            )
        
        # Export progress button
        if st.button("Export Progress Data"):
            export_file = export_progress(st.session_state.user_id)
            st.success(f"Progress data exported to {export_file}")
            
            # Create a download button for the exported file
            with open(export_file, 'r') as f:
                export_data = f.read()
            st.download_button(
                label="Download Progress Data",
                data=export_data,
                file_name="dsa_progress.json",
                mime="application/json"
            )
        
        # Detailed progress table
        st.subheader("Detailed Progress")
        df_detailed = get_questions_dataframe(st.session_state.user_id)
        
        # Format the completed column
        df_detailed['status'] = df_detailed['completed'].apply(
            lambda x: "✅ Completed" if x else "❌ Pending"
        )
        
        # Display as a table
        st.dataframe(
            df_detailed[['topic', 'title', 'difficulty', 'status']],
            use_container_width=True,
            column_config={
                "topic": "Topic",
                "title": "Question",
                "difficulty": "Difficulty",
                "status": "Status"
            }
        )
    else:
        st.info("No questions found in the database.")

elif st.session_state.current_page == 'manage':
    st.title("Manage Questions")
    
    # Check if user is authenticated as admin
    if not st.session_state.admin_logged_in:
        st.warning("This page is restricted to administrators only. Please log in as an admin using the sidebar.")
        if st.button("Back to Home"):
            navigate_to_home()
    else:
        # Get list of topics for select boxes
        topics = get_topics()
        topic_names = [topic['name'] for topic in topics]
        topic_ids = [topic['id'] for topic in topics]
        
        # Create tabs for different ways to manage questions
        tab1, tab2, tab3, tab4 = st.tabs(["Add Single Question", "Batch Add Questions", "Delete Questions", "Admin Settings"])
        
        with tab1:
            st.header("Add Single Question")
            
            # Form for adding a single question
            with st.form("add_question_form"):
                title = st.text_input("Question Title", placeholder="e.g., Find the maximum subarray sum")
                
                col1, col2 = st.columns(2)
                with col1:
                    leetcode_url = st.text_input("LeetCode URL (optional)", placeholder="https://leetcode.com/problems/...")
                with col2:
                    gfg_url = st.text_input("GeeksForGeeks URL (optional)", placeholder="https://practice.geeksforgeeks.org/problems/...")
                
                col1, col2 = st.columns(2)
                with col1:
                    topic_index = st.selectbox("Topic", range(len(topic_names)), format_func=lambda i: topic_names[i])
                    topic_id = topic_ids[topic_index]
                
                with col2:
                    difficulty = st.selectbox("Difficulty", ["Easy", "Medium", "Hard"])
                
                submitted = st.form_submit_button("Add Question", use_container_width=True)
                
                if submitted:
                    if not title:
                        st.error("Question title is required!")
                    else:
                        try:
                            # Add the question to the database
                            question_id = add_question(title, leetcode_url, gfg_url, difficulty, topic_id)
                            st.success(f"Question '{title}' added successfully with ID {question_id}!")
                        except Exception as e:
                            st.error(f"Error adding question: {str(e)}")
        
        with tab2:
            st.header("Batch Add Questions")
            
            # Select a topic for all questions in this batch
            topic_index = st.selectbox(
                "Select Topic for All Questions",
                range(len(topic_names)),
                format_func=lambda i: topic_names[i],
                key="batch_topic_select"
            )
            selected_topic_id = topic_ids[topic_index]
            
            # JSON input area for batch questions
            st.markdown("""
            ### Batch Questions Format
            
            Enter a JSON array of questions in the following format:
            ```json
            [
              {
                "title": "Question Title 1",
                "leetcode_url": "https://leetcode.com/problems/example1",
                "gfg_url": "https://practice.geeksforgeeks.org/problems/example1",
                "difficulty": "Easy"
              },
              {
                "title": "Question Title 2",
                "difficulty": "Medium",
                "gfg_url": "https://practice.geeksforgeeks.org/problems/example2"
              },
              {
                "title": "Question Title 3 (No URLs)",
                "difficulty": "Hard"
              }
            ]
            ```
            Note: Both `leetcode_url` and `gfg_url` are optional for each question.
            """)
            
            json_input = st.text_area(
                "Enter Questions JSON",
                value=st.session_state.batch_questions,
                height=300
            )
            st.session_state.batch_questions = json_input
            
            if st.button("Add Batch Questions", use_container_width=True):
                if not json_input.strip():
                    st.error("Please enter question data in JSON format!")
                else:
                    try:
                        # Parse JSON input
                        questions_data = json.loads(json_input)
                        
                        if not isinstance(questions_data, list):
                            st.error("JSON input must be an array of questions!")
                        elif len(questions_data) == 0:
                            st.warning("No questions found in JSON input!")
                        else:
                            # Validate each question
                            valid = True
                            for i, q in enumerate(questions_data):
                                if not isinstance(q, dict):
                                    st.error(f"Question {i+1} is not a valid object!")
                                    valid = False
                                    break
                                if 'title' not in q or 'difficulty' not in q:
                                    st.error(f"Question {i+1} is missing required fields (title, difficulty)!")
                                    valid = False
                                    break
                                if q['difficulty'] not in ["Easy", "Medium", "Hard"]:
                                    st.error(f"Question {i+1} has invalid difficulty! Must be 'Easy', 'Medium', or 'Hard'.")
                                    valid = False
                                    break
                            
                            if valid:
                                # Add questions to database
                                count = add_questions_batch(questions_data, selected_topic_id)
                                st.success(f"Successfully added {count} questions to '{topic_names[topic_index]}'!")
                                # Clear the text area
                                st.session_state.batch_questions = "[]"
                                st.rerun()
                    
                    except json.JSONDecodeError:
                        st.error("Invalid JSON format! Please check your input.")
                    except Exception as e:
                        st.error(f"Error adding questions: {str(e)}")
                        
        with tab3:
            st.header("Delete Questions")
            st.warning("⚠️ Warning: Deleting questions will permanently remove them from the database. This action cannot be undone.")
            
            # Get all questions for display and selection
            # For admin, show all questions regardless of user
            df_questions = get_questions_dataframe()
            
            if df_questions.empty:
                st.info("No questions available in the database.")
            else:
                # Add a selection column to the dataframe
                df_questions['Select'] = False
                
                # Create a filter for topics
                topic_filter = st.selectbox(
                    "Filter by Topic",
                    ["All Topics"] + sorted(df_questions['topic'].unique().tolist()),
                    key="delete_topic_filter"
                )
                
                # Apply the filter
                if topic_filter != "All Topics":
                    filtered_df = df_questions[df_questions['topic'] == topic_filter]
                else:
                    filtered_df = df_questions
                
                # Display the questions with a selection box
                selected_df = st.data_editor(
                    filtered_df[['id', 'topic', 'title', 'difficulty', 'Select']],
                    column_config={
                        "id": st.column_config.NumberColumn("ID"),
                        "topic": "Topic",
                        "title": "Question",
                        "difficulty": "Difficulty",
                        "Select": st.column_config.CheckboxColumn("Select to Delete")
                    },
                    disabled=['id', 'topic', 'title', 'difficulty'],
                    use_container_width=True,
                    key="question_selection"
                )
                
                # Get the IDs of selected questions
                selected_ids = selected_df[selected_df['Select']]['id'].tolist()
                
                # Display the delete button with confirmation
                col1, col2 = st.columns([3, 1])
                with col2:
                    if len(selected_ids) > 0:
                        if st.button("Delete Selected", type="primary", use_container_width=True):
                            st.session_state.confirm_delete = True
                
                # Show confirmation dialog
                if st.session_state.get('confirm_delete', False):
                    st.warning(f"Are you sure you want to delete {len(selected_ids)} selected questions? This action cannot be undone.")
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        if st.button("Cancel", use_container_width=True):
                            st.session_state.confirm_delete = False
                            st.rerun()
                    
                    with col2:
                        if st.button("Confirm Delete", type="primary", use_container_width=True):
                            success_count = 0
                            error_count = 0
                            
                            # Attempt to delete each selected question
                            for q_id in selected_ids:
                                if delete_question(q_id):
                                    success_count += 1
                                else:
                                    error_count += 1
                            
                            # Display the results
                            if success_count > 0:
                                st.success(f"Successfully deleted {success_count} questions.")
                            
                            if error_count > 0:
                                st.error(f"Failed to delete {error_count} questions.")
                            
                            # Reset the confirmation state
                            st.session_state.confirm_delete = False
                            st.rerun()
                            
        with tab4:
            st.header("Admin Settings")
            
            # Create subtabs for different admin settings
            admin_tab1, admin_tab2 = st.tabs(["View User Accounts", "Admin Credentials"])
            
            with admin_tab1:
                st.subheader("User Accounts")
                
                # Get all user accounts
                users = get_all_users()
                
                if not users:
                    st.info("No user accounts found in the database.")
                else:
                    # Convert to DataFrame for display
                    users_df = pd.DataFrame(users)
                    
                    # Format the data for display
                    st.dataframe(
                        users_df,
                        column_config={
                            "id": "User ID",
                            "username": "Username",
                            "email": "Email",
                            "created_at": "Registered On",
                            "last_login": "Last Login"
                        },
                        use_container_width=True
                    )
                    
                    st.info(f"Total registered users: {len(users)}")
            
            with admin_tab2:
                st.subheader("Admin Credentials")
                
                # Form to change admin password
                with st.form("change_admin_password_form"):
                    st.write("Change Admin Password")
                    current_username = st.text_input("Admin Username")
                    current_password = st.text_input("Current Password", type="password")
                    new_password = st.text_input("New Password", type="password")
                    confirm_password = st.text_input("Confirm New Password", type="password")
                    
                    if st.form_submit_button("Change Password", use_container_width=True):
                        if not current_username or not current_password or not new_password:
                            st.error("All fields are required!")
                        elif new_password != confirm_password:
                            st.error("New passwords do not match!")
                        else:
                            # Attempt to change the password
                            if change_admin_password(current_username, current_password, new_password):
                                st.success(f"Password changed successfully for admin '{current_username}'!")
                            else:
                                st.error("Failed to change password. Check your current username and password.")
                
                # Form to add new admin
                with st.form("add_admin_form"):
                    st.write("Add New Admin")
                    new_admin_username = st.text_input("New Admin Username")
                    new_admin_password = st.text_input("Password", type="password", key="new_admin_pass")
                    confirm_admin_password = st.text_input("Confirm Password", type="password", key="confirm_admin_pass")
                    update_if_exists = st.checkbox("Update password if admin already exists")
                    
                    if st.form_submit_button("Add Admin", use_container_width=True):
                        if not new_admin_username or not new_admin_password:
                            st.error("Username and password are required!")
                        elif new_admin_password != confirm_admin_password:
                            st.error("Passwords do not match!")
                        else:
                            # Attempt to add the new admin
                            success, message = add_admin(new_admin_username, new_admin_password, update_if_exists)
                            if success:
                                st.success(message)
                            else:
                                st.error(message)
