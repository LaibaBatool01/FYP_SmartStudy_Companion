import streamlit as st
import pymongo
import re
import hashlib
import os
import secrets
import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv
from FRONTEND import main as frontend_main
from FRONTEND import create_progress_visualization
import json

# Load environment variables from .env file
load_dotenv()

# Set page configuration
st.set_page_config(
    page_title="Authentication System",
    page_icon="🔐",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# MongoDB connection
def get_database_connection():
    # Get MongoDB connection string from environment variable or use a default for local development
    mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
    client = pymongo.MongoClient(mongo_uri)
    db = client["auth_app_db"]
    return db

# Initialize database connection
db = get_database_connection()
users_collection = db["users"]
reset_tokens_collection = db["reset_tokens"]

# Create indexes for username and email (if they don't exist)
users_collection.create_index([("username", pymongo.ASCENDING)], unique=True)
users_collection.create_index([("email", pymongo.ASCENDING)], unique=True)
reset_tokens_collection.create_index([("token", pymongo.ASCENDING)], unique=True)
reset_tokens_collection.create_index([("email", pymongo.ASCENDING)])
reset_tokens_collection.create_index([("expires_at", pymongo.ASCENDING)], expireAfterSeconds=0)

# Password hashing function
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# Validate email format
def is_valid_email(email):
    pattern = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
    return re.match(pattern, email) is not None

# Generate reset token
def generate_reset_token():
    return secrets.token_urlsafe(32)

# Send reset email
def send_reset_email(email, token):
    smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_username = os.getenv("SMTP_USERNAME")
    smtp_password = os.getenv("SMTP_PASSWORD")
    
    if not all([smtp_username, smtp_password]):
        st.error("Email configuration is missing. Please set SMTP_USERNAME and SMTP_PASSWORD in .env file")
        return False
    
    # Create message
    msg = MIMEMultipart()
    msg['From'] = smtp_username
    msg['To'] = email
    msg['Subject'] = "Password Reset Request"
    
    # Create reset link with a special format that we can parse
    reset_link = f"http://localhost:8501/?token={token}"
    
    # Email body
    body = f"""
    Hello,
    
    You have requested to reset your password. Click the link below to reset your password:
    
    {reset_link}
    
    This link will expire in 1 hour.
    
    If you did not request this password reset, please ignore this email.
    
    Best regards,
    Your App Team
    """
    
    msg.attach(MIMEText(body, 'plain'))
    
    try:
        # Create SMTP session
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(smtp_username, smtp_password)
        
        # Send email
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        st.error(f"Failed to send email: {str(e)}")
        return False

# Initialize session state variables
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'username' not in st.session_state:
    st.session_state.username = ""
if 'page' not in st.session_state:
    st.session_state.page = "login"  # Default page
if 'reset_token' not in st.session_state:
    st.session_state.reset_token = None

# Function to switch pages
def switch_page(page):
    st.session_state.page = page
    # Clear any existing form data when switching pages
    if 'form_data' in st.session_state:
        st.session_state.form_data = {}

# Logout function
def logout():
    st.session_state.logged_in = False
    st.session_state.username = ""
    switch_page("login")

# Custom CSS
st.markdown("""
<style>
    .main {
        padding: 2rem;
    }
    .auth-container {
        background-color: #f8f9fa;
        padding: 2rem;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        margin-bottom: 1rem;
    }
    .auth-header {
        text-align: center;
        margin-bottom: 2rem;
    }
    .auth-footer {
        text-align: center;
        margin-top: 1rem;
        font-size: 0.9rem;
    }
    .stButton button {
        width: 100%;
        background: linear-gradient(45deg, #2196F3, #1976D2) !important;
        color: white !important;
        border: none !important;
        border-radius: 12px !important;
        padding: 1rem 1.5rem !important;
        font-weight: 600 !important;
        font-size: 1rem !important;
        box-shadow: 0 4px 15px rgba(33, 150, 243, 0.3) !important;
        transition: all 0.3s ease !important;
        margin: 0.5rem 0 !important;
        height: 3.5rem !important;
    }
    
    .stButton button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 6px 20px rgba(33, 150, 243, 0.4) !important;
        background: linear-gradient(45deg, #1976D2, #1565C0) !important;
    }
    
    /* Special styling for logout button */
    .stButton button[data-testid*="logout"] {
        background: linear-gradient(45deg, #f44336, #d32f2f) !important;
        box-shadow: 0 4px 15px rgba(244, 67, 54, 0.3) !important;
    }
    
    .stButton button[data-testid*="logout"]:hover {
        background: linear-gradient(45deg, #d32f2f, #c62828) !important;
        box-shadow: 0 6px 20px rgba(244, 67, 54, 0.4) !important;
    }
</style>
""", unsafe_allow_html=True)

# Main app logic
def main():
    # Check for reset token in URL parameters
    if 'token' in st.query_params:
        token = st.query_params['token']
        # Verify token
        token_data = reset_tokens_collection.find_one({
            "token": token,
            "expires_at": {"$gt": datetime.datetime.utcnow()}
        })
        if token_data:
            st.session_state.reset_token = token
            st.session_state.page = "reset_password"
            # Clear the URL parameters
            st.query_params.clear()

    if st.session_state.logged_in:
        # Initialize necessary session state variables for frontend
        if 'current_page' not in st.session_state:
            st.session_state.current_page = None
        if 'chat_history' not in st.session_state:
            st.session_state.chat_history = []
        if 'learned_topics' not in st.session_state:
            st.session_state.learned_topics = []
            
        # Check if user just signed up (show frontend) or logged in (show dashboard)
        if st.session_state.get('just_signed_up', False):
            # Reset the flag and show frontend for topic selection
            st.session_state.just_signed_up = False
            # Set current_page to cpp_prerequisites to stay on topic selection
            st.session_state.current_page = "cpp_prerequisites"
            frontend_main()
        elif st.session_state.get('current_page') in ["hierarchy_tree", "chatbot", "cpp_prerequisites"]:
            # User is navigating within frontend pages
            frontend_main()
        else:
            # Show dashboard for returning users or when current_page is cleared
            display_dashboard()
    else:
        if st.session_state.page == "login":
            display_login()
        elif st.session_state.page == "signup":
            display_signup()
        elif st.session_state.page == "forgot_password":
            display_forgot_password()
        elif st.session_state.page == "reset_password":
            display_reset_password()

# Dashboard page (after login)
def display_dashboard():
    # Enhanced CSS for dashboard
    st.markdown("""
    <style>
        /* Dashboard specific styling */
        .dashboard-container {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 2rem;
            border-radius: 15px;
            margin-bottom: 2rem;
            color: white;
        }
        
        .welcome-header {
            text-align: center;
            font-size: 2.5rem;
            font-weight: 700;
            margin-bottom: 1rem;
            color: white;
        }
        
        .progress-card {
            background: white;
            padding: 1.5rem;
            border-radius: 12px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
            margin: 1rem 0;
        }
        
        .topic-pill {
            display: inline-block;
            background: linear-gradient(45deg, #4CAF50, #45a049);
            color: white;
            padding: 0.5rem 1rem;
            border-radius: 20px;
            margin: 0.25rem;
            font-size: 0.9rem;
            font-weight: 500;
            box-shadow: 0 2px 5px rgba(0,0,0,0.2);
        }
        
        .next-topic-pill {
            display: inline-block;
            background: linear-gradient(45deg, #2196F3, #1976D2);
            color: white;
            padding: 0.5rem 1rem;
            border-radius: 20px;
            margin: 0.25rem;
            font-size: 0.9rem;
            font-weight: 500;
            box-shadow: 0 2px 5px rgba(0,0,0,0.2);
        }
        
        .action-button {
            background: linear-gradient(45deg, #2196F3, #1976D2) !important;
            color: white !important;
            border: none !important;
            border-radius: 12px !important;
            padding: 1rem 1.5rem !important;
            font-weight: 600 !important;
            font-size: 1rem !important;
            box-shadow: 0 4px 15px rgba(33, 150, 243, 0.3) !important;
            transition: all 0.3s ease !important;
            width: 100% !important;
            margin: 0.5rem 0 !important;
        }
        
        .action-button:hover {
            transform: translateY(-2px) !important;
            box-shadow: 0 6px 20px rgba(33, 150, 243, 0.4) !important;
        }
        
        .logout-button {
            background: linear-gradient(45deg, #f44336, #d32f2f) !important;
            color: white !important;
            border: none !important;
            border-radius: 12px !important;
            padding: 1rem 1.5rem !important;
            font-weight: 600 !important;
            font-size: 1rem !important;
            box-shadow: 0 4px 15px rgba(244, 67, 54, 0.3) !important;
            transition: all 0.3s ease !important;
            width: 100% !important;
            margin: 1rem 0 !important;
        }
        
        .logout-button:hover {
            transform: translateY(-2px) !important;
            box-shadow: 0 6px 20px rgba(244, 67, 54, 0.4) !important;
        }
        
        .section-header {
            color: #2c3e50;
            font-size: 1.5rem;
            font-weight: 600;
            margin: 1.5rem 0 1rem 0;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }
        
        .progress-text {
            font-size: 1.1rem;
            color: #34495e;
            margin: 0.5rem 0;
        }
        
        .congratulations {
            background: linear-gradient(45deg, #4CAF50, #45a049);
            color: white;
            padding: 1rem;
            border-radius: 12px;
            text-align: center;
            font-weight: 600;
            margin: 1rem 0;
        }
        
                 .no-topics {
             background: linear-gradient(45deg, #FF9800, #F57C00);
             color: white;
             padding: 1rem;
             border-radius: 12px;
             text-align: center;
             font-weight: 500;
             margin: 1rem 0;
         }
         
         /* Navigation container styling */
         .nav-container {
             background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
             padding: 1rem;
             border-radius: 15px;
             margin-bottom: 2rem;
             box-shadow: 0 4px 15px rgba(0,0,0,0.1);
         }
    </style>
    """, unsafe_allow_html=True)
    
    # Top navigation bar with buttons (like other pages)
    st.markdown('<div class="nav-container">', unsafe_allow_html=True)
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        if st.button("🏠 Dashboard", use_container_width=True, disabled=True):
            pass  # Already on dashboard
    with col2:
        if st.button("📚 Learning Path", use_container_width=True):
            st.session_state.current_page = "cpp_prerequisites"
            st.rerun()
    with col3:
        if st.button("🌳 Tree Visualization", use_container_width=True):
            st.session_state.current_page = "hierarchy_tree"
            st.rerun()
    with col4:
        if st.button("🤖 Chatbot", use_container_width=True):
            st.session_state.current_page = "chatbot"
            st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Welcome header with gradient background
    st.markdown(f"""
    <div class="dashboard-container">
        <div class="welcome-header">
            Welcome, {st.session_state.username}! 👋
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Add the interactive progress visualization
    create_progress_visualization()
    
    # Load prerequisites for additional dashboard content
    try:
        with open('cpp-prerequisites-json.json', 'r') as f:
            cpp_prerequisites = json.load(f)
        all_topics = list(cpp_prerequisites.keys())
    except FileNotFoundError:
        st.error("Prerequisites file not found. Please ensure cpp-prerequisites-json.json exists.")
        all_topics = []
    
    # Get user's learned topics
    learned_topics = st.session_state.get('learned_topics', [])
    
    # Show learned topics in a compact format
    if learned_topics:
        st.markdown('<div class="section-header">✅ Recently Mastered Topics:</div>', unsafe_allow_html=True)
        st.markdown('<div class="progress-card">', unsafe_allow_html=True)
        # Show only the last 10 topics to keep it compact
        recent_topics = learned_topics[-10:] if len(learned_topics) > 10 else learned_topics
        for topic in recent_topics:
            st.markdown(f'<span class="topic-pill">✓ {topic}</span>', unsafe_allow_html=True)
        if len(learned_topics) > 10:
            st.markdown(f'<p style="margin-top: 1rem; color: #666;">And {len(learned_topics) - 10} more topics completed!</p>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="no-topics">No topics completed yet. Start your learning journey!</div>', unsafe_allow_html=True)

# Login page
def display_login():
    st.markdown("""
    <div class="auth-header">
        <h1>🔐 Login</h1>
        <p>Enter your credentials to access your account</p>
    </div>
    """, unsafe_allow_html=True)
    
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submit = st.form_submit_button("Login")
        
        if submit:
            if not username or not password:
                st.error("Please fill in all fields")
            else:
                # Check if user exists
                hashed_password = hash_password(password)
                user = users_collection.find_one({"username": username})
                
                if user and user["password"] == hashed_password:
                    st.session_state.logged_in = True
                    st.session_state.username = username
                    # Load user's progress from database
                    st.session_state.learned_topics = user.get("learned_topics", [])
                    st.session_state.last_quiz_topic = user.get("last_quiz_topic", None)
                    # Don't set just_signed_up flag for login
                    st.success("Login successful!")
                    st.rerun()
                else:
                    st.error("Invalid username or password")
    
    st.markdown("""
    <div class="auth-footer">
        Don't have an account?
    </div>
    """, unsafe_allow_html=True)
    
    st.button("Sign Up", on_click=lambda: switch_page("signup"))
    
    st.markdown("""
    <div class="auth-footer">
        Forgot your password?
    </div>
    """, unsafe_allow_html=True)
    
    st.button("Reset Password", on_click=lambda: switch_page("forgot_password"))

# Sign-up page
def display_signup():
    st.markdown("""
    <div class="auth-header">
        <h1>📝 Sign Up</h1>
        <p>Create a new account</p>
    </div>
    """, unsafe_allow_html=True)
    
    with st.form("signup_form"):
        username = st.text_input("Username")
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        confirm_password = st.text_input("Confirm Password", type="password")
        submit = st.form_submit_button("Sign Up")
        
        if submit:
            # Validate inputs
            if not username or not email or not password or not confirm_password:
                st.error("Please fill in all fields")
            elif password != confirm_password:
                st.error("Passwords do not match")
            elif not is_valid_email(email):
                st.error("Invalid email format")
            else:
                # Check if username or email already exists
                existing_user = users_collection.find_one({"$or": [{"username": username}, {"email": email}]})
                
                if existing_user:
                    if existing_user.get("username") == username:
                        st.error("Username already exists")
                    else:
                        st.error("Email already registered")
                else:
                    # Create new user
                    hashed_password = hash_password(password)
                    new_user = {
                        "username": username,
                        "email": email,
                        "password": hashed_password,
                        "learned_topics": [],
                        "last_quiz_topic": None
                    }
                    
                    try:
                        users_collection.insert_one(new_user)
                        st.success("Account created successfully!")
                        
                        # Store user info in session state
                        st.session_state.logged_in = True
                        st.session_state.username = username
                        # Initialize empty progress for new user
                        st.session_state.learned_topics = []
                        st.session_state.last_quiz_topic = None
                        # Set flag to show frontend (topic selection) after signup
                        st.session_state.just_signed_up = True
                        
                        st.rerun()
                    except pymongo.errors.PyMongoError as e:
                        st.error(f"Database error: {str(e)}")
    
    st.markdown("""
    <div class="auth-footer">
        Already have an account?
    </div>
    """, unsafe_allow_html=True)
    
    st.button("Login", on_click=lambda: switch_page("login"))

# Forgot password page
def display_forgot_password():
    st.markdown("""
    <div class="auth-header">
        <h1>🔑 Reset Password</h1>
        <p>Enter your email to reset your password</p>
    </div>
    """, unsafe_allow_html=True)
    
    with st.form("reset_password_form"):
        email = st.text_input("Email")
        submit = st.form_submit_button("Send Reset Link")
        
        if submit:
            if not email:
                st.error("Please enter your email")
            elif not is_valid_email(email):
                st.error("Invalid email format")
            else:
                # Check if email exists
                user = users_collection.find_one({"email": email})
                
                if user:
                    # Generate reset token
                    token = generate_reset_token()
                    expires_at = datetime.datetime.utcnow() + datetime.timedelta(hours=1)
                    
                    # Store token in database
                    reset_tokens_collection.insert_one({
                        "email": email,
                        "token": token,
                        "expires_at": expires_at
                    })
                    
                    # Send reset email
                    if send_reset_email(email, token):
                        st.success("Password reset link has been sent to your email!")
                    else:
                        st.error("Failed to send reset email. Please try again later.")
                else:
                    # For security reasons, don't reveal if the email exists or not
                    st.success("If your email is registered, you will receive a password reset link.")
    
    st.markdown("""
    <div class="auth-footer">
        Remember your password?
    </div>
    """, unsafe_allow_html=True)
    
    st.button("Back to Login", on_click=lambda: switch_page("login"))

# Reset password page
def display_reset_password():
    st.markdown("""
    <div class="auth-header">
        <h1>🔑 Set New Password</h1>
        <p>Enter your new password</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Get token from session state
    token = st.session_state.reset_token
    
    if not token:
        st.error("Invalid or missing reset token")
        st.button("Back to Login", on_click=lambda: switch_page("login"))
        return
    
    # Verify token
    token_data = reset_tokens_collection.find_one({
        "token": token,
        "expires_at": {"$gt": datetime.datetime.utcnow()}
    })
    
    if not token_data:
        st.error("Invalid or expired reset token")
        st.button("Back to Login", on_click=lambda: switch_page("login"))
        return
    
    with st.form("new_password_form"):
        new_password = st.text_input("New Password", type="password")
        confirm_password = st.text_input("Confirm Password", type="password")
        submit = st.form_submit_button("Reset Password")
        
        if submit:
            if not new_password or not confirm_password:
                st.error("Please fill in all fields")
            elif new_password != confirm_password:
                st.error("Passwords do not match")
            else:
                # Update password
                hashed_password = hash_password(new_password)
                users_collection.update_one(
                    {"email": token_data["email"]},
                    {"$set": {"password": hashed_password}}
                )
                # Delete used token
                reset_tokens_collection.delete_one({"token": token})
                # Clear reset token from session state
                st.session_state.reset_token = None
                st.session_state.password_reset_success = True

    # After the form
    if st.session_state.get("password_reset_success"):
        st.success("Password has been reset successfully!")
        st.button("Go to Login", on_click=lambda: switch_page("login"))
        st.session_state.password_reset_success = False

if __name__ == "__main__":
    main()
