# DSA Cracker

A comprehensive Data Structures and Algorithms practice platform inspired by 450dsa.com, built with Streamlit and Python.

![DSA Cracker Screenshot](generated-icon.png)

## Features

- **Topic-wise DSA Questions**: Organized by categories like Arrays, Linked Lists, Trees, etc.
- **Progress Tracking**: Keep track of your progress as you solve questions
- **User Authentication**: Create your own account to track your personal progress
- **Built-in Note Taking**: Add personal notes for each problem to remember key concepts
- **Solution Storage**: Save your solutions directly in the app
- **Bookmarking**: Save your favorite questions for later review
- **Difficulty Filters**: Filter questions by difficulty (Easy, Medium, Hard)
- **Search Functionality**: Search for specific questions by keywords
- **Progress Dashboard**: Visualize your progress with interactive charts
- **Admin Panel**: Add, edit, or delete questions (admin access required)
- **LeetCode Integration**: Direct links to solve problems on LeetCode
- **GeeksForGeeks Integration**: Alternative platform links when available

## Installation

### Prerequisites
- Python 3.8 or higher

### Setup Instructions

1. Clone this repository:
   ```bash
   git clone https://github.com/yourusername/dsa-cracker.git
   cd dsa-cracker
   ```

2. Install the required packages:
   ```bash
   pip install streamlit pandas plotly
   ```

3. Run the application:
   ```bash
   streamlit run app.py
   ```

4. Open your browser and navigate to:
   ```
   http://localhost:8501
   ```

## Usage

### User Guide

1. **Home Page**: Browse different DSA topics and see your progress for each
2. **Topic Page**: View questions for a specific topic, mark them as completed, add notes, solutions, and bookmark them
3. **Progress Dashboard**: Visualize your completion statistics, filter by difficulty, and track weekly progress
4. **Profile Page**: View your account information and overall stats
5. **Bookmarks Page**: Access all your bookmarked questions in one place

### Admin Access

Default admin credentials:
- Username: `admin`
- Password: `admin123`

Admin features:
- Add new questions individually
- Batch upload multiple questions at once
- Delete questions
- Manage the database

## Project Structure

- `app.py`: Main Streamlit application with UI components
- `database.py`: Database operations and SQL functions
- `utils.py`: Utility functions for UI formatting
- `questions.json`: Initial seed data for DSA questions
- `dsa_tracker.db`: SQLite database storing questions, user data, and progress

## Customization

You can easily customize the application by:

1. Adding your own questions to the database through the admin panel
2. Modifying the topic categories in the database
3. Adding more difficulty levels or features

## Deployment

This application can be deployed on platforms that support Streamlit applications such as:
- Streamlit Cloud
- Heroku
- Railway
- AWS, GCP, or Azure

The application uses SQLite as the database backend, making it fully portable and easy to deploy.

## Contributing

Contributions are welcome! Feel free to submit a Pull Request.

## License

This project is open source and available under the [MIT License](LICENSE).

## Acknowledgements

- Inspired by [450dsa.com](https://450dsa.com)
- Built with [Streamlit](https://streamlit.io)
- Data visualization powered by [Plotly](https://plotly.com/python/)