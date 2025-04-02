import streamlit as st

def get_difficulty_color(difficulty):
    """Return the color for a given difficulty level"""
    if difficulty == "Easy":
        return "green"
    elif difficulty == "Medium":
        return "orange"
    elif difficulty == "Hard":
        return "red"
    return "blue"  # Default color

def create_topic_card(topic_name, total_questions, progress=0):
    """Create a card for a topic with its progress"""
    progress_pct = 0 if total_questions == 0 else int((progress / total_questions) * 100)
    
    with st.container():
        col1, col2 = st.columns([3, 1])
        
        with col1:
            st.markdown(f"### {topic_name}")
            st.markdown(f"Total Questions: {total_questions}")
            
            if progress == 0:
                st.markdown("**_Not yet started_**")
            else:
                st.markdown(f"**_Progress: {progress}/{total_questions}_**")
                
        with col2:
            st.progress(progress_pct / 100)
            st.markdown(f"**{progress_pct}%**")
        
        st.markdown("---")

def format_question_item(question, on_change_callback):
    """Format a single question item with checkbox and difficulty label"""
    # Using function references passed from app.py instead of importing
    question_id = question['id']
    
    # Initialize session state for this question if not already initialized
    if f"notes_{question_id}" not in st.session_state:
        st.session_state[f"notes_{question_id}"] = question.get('notes', '')
    
    if f"solution_{question_id}" not in st.session_state:
        st.session_state[f"solution_{question_id}"] = question.get('solution', '')
    
    # Create two columns for the question header
    header_col1, header_col2 = st.columns([4, 1])
    
    with header_col1:
        completed = st.checkbox(
            question['title'], 
            value=bool(question['completed']),
            key=f"question_{question_id}",
            on_change=on_change_callback,
            args=(question_id,)
        )
        
        # Create a row for links
        link_cols = st.columns(4)
        
        # LeetCode link (if available)
        with link_cols[0]:
            if 'leetcode_url' in question and question['leetcode_url']:
                st.markdown(f"[LeetCode]({question['leetcode_url']})")
        
        # GFG link (if available)
        with link_cols[1]:
            if 'gfg_url' in question and question['gfg_url']:
                st.markdown(f"[GeeksForGeeks]({question['gfg_url']})")
        
        # Google search link
        with link_cols[2]:
            google_search_url = f"https://www.google.com/search?q={question['title'].replace(' ', '+')}"
            st.markdown(f"[Search Google]({google_search_url})")
            
        # Bookmark button
        with link_cols[3]:
            is_bookmarked = question.get('bookmarked', False)
            bookmark_icon = "🔖" if is_bookmarked else "📌"
            if st.button(f"{bookmark_icon} Bookmark", key=f"bookmark_{question_id}"):
                question['bookmark_fn'](question_id)
                st.rerun()
    
    with header_col2:
        difficulty_color = get_difficulty_color(question['difficulty'])
        st.markdown(
            f"<span style='background-color:{difficulty_color}; color:white; padding:4px 8px; border-radius:3px;'>{question['difficulty']}</span>", 
            unsafe_allow_html=True
        )
    
    # Create a container for expandable sections
    with st.expander("Notes & Solution"):
        tabs = st.tabs(["Notes", "Solution"])
        
        # Notes tab
        with tabs[0]:
            notes = st.text_area(
                "Your notes for this question",
                value=st.session_state[f"notes_{question_id}"],
                key=f"notes_input_{question_id}",
                height=150
            )
            
            if st.button("Save Notes", key=f"save_notes_{question_id}"):
                question['save_notes_fn'](question_id, notes)
                st.session_state[f"notes_{question_id}"] = notes
        
        # Solution tab
        with tabs[1]:
            solution = st.text_area(
                "Your solution for this question",
                value=st.session_state[f"solution_{question_id}"],
                key=f"solution_input_{question_id}",
                height=200
            )
            
            if st.button("Save Solution", key=f"save_solution_{question_id}"):
                question['save_solution_fn'](question_id, solution)
                st.session_state[f"solution_{question_id}"] = solution
    
    st.markdown("---")

def show_topic_progress(topic_stats):
    """Display progress statistics for a topic"""
    total = topic_stats['total']
    completed = topic_stats['completed']
    
    if total > 0:
        progress_pct = int((completed / total) * 100)
        st.progress(progress_pct / 100)
        st.markdown(f"### Progress: {completed}/{total} ({progress_pct}%)")
    else:
        st.progress(0)
        st.markdown("### No questions available")
