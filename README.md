# 🚀 Programming Learning Path Builder with Authentication

A comprehensive web application built with Streamlit that provides an interactive learning platform for programming concepts with user authentication, progress tracking, and personalized dashboards.

## 📋 Table of Contents

- [Quick Start](#-quick-start)
- [Features](#-features)
- [Screenshots](#-screenshots)
- [Installation](#-installation)
- [Configuration](#-configuration)
- [Usage](#-usage)
- [File Structure](#-file-structure)
- [API Endpoints](#-api-endpoints)
- [Database Schema](#-database-schema)
- [Contributing](#-contributing)
- [License](#-license)

## ⚡ Quick Start

**Want to get started quickly? Follow these essential steps:**

1. **Set up accounts** (15 minutes):
   - [Hugging Face](https://huggingface.co) → Request CodeLlama access
   - [Neo4j Aura](https://console-preview.neo4j.io/projects/123eeeda-2ed0-44b9-b336-5ba4247068a4/instances) → Create free database instance
   - [LLM-Knowledge Graph Builder](https://llm-graph-builder.neo4jlabs.com/) → Upload programming books
   - [Ngrok](https://ngrok.com) → Get auth token

2. **Deploy AI models** (20 minutes):
   - Open `quiz_model.ipynb` in Google Colab
   - Update credentials and run all cells
   - Copy the ngrok URL
   - Repeat for `chatbot_for_c++_only.ipynb`

3. **Run main app** (5 minutes):
   ```bash
   # Install the main application (AI models run in Colab)
   pip install -r requirements-minimal.txt
   
   # Update .env file with your credentials and ngrok URLs
   streamlit run login_signup.py
   ```

4. **Test the system**:
   - Sign up → Select topics → Take quiz → Explore visualizations

**⚠️ Important**: Ngrok URLs expire every 8 hours on free tier. Restart Colab notebooks when needed.

## ✨ Features

### 🔐 Authentication System
- **User Registration & Login**: Secure user authentication with password hashing
- **Password Reset**: Email-based password reset functionality with secure tokens
- **Session Management**: Persistent user sessions with automatic logout
- **Email Validation**: Built-in email format validation and duplicate prevention

### 📊 Personalized Dashboard
- **Progress Visualization**: Interactive charts showing learning progress by category
- **Topic Tracking**: Visual representation of completed vs remaining topics
- **Recent Activity**: Timeline of recent quiz completions and achievements
- **Learning Path Suggestions**: Smart recommendations for next topics to learn

### 🎯 Interactive Learning Path
- **Topic Selection**: Checkbox interface for selecting learned topics
- **Prerequisite Management**: Automatic prerequisite handling when selecting topics
- **Progress Saving**: Real-time progress saving to MongoDB database
- **Category Organization**: Topics organized by Foundation, Intermediate, and Advanced levels

### 📝 Adaptive Quiz System
- **Dynamic Quiz Generation**: AI-powered quiz generation based on learned topics
- **Multiple Difficulty Levels**: Hard, Medium, and Easy questions for each topic
- **Question Bank Integration**: Fallback to curated question bank when AI fails
- **Progress Validation**: Quiz results determine learning path progression

### 🌳 Interactive Visualizations
- **Hierarchy Tree**: Visual representation of topic prerequisites and relationships
- **Knowledge Graph**: Interactive network visualization of topic connections
- **Progress Charts**: Pie charts and bar graphs showing completion statistics
- **Topic Highlighting**: Visual feedback for quiz performance and topic mastery

### 🤖 AI Chatbot Assistant
- **Programming Help**: AI-powered assistance for programming questions
- **Context-Aware**: Integration with learning progress for personalized responses
- **Chat History**: Persistent conversation history within sessions
- **Topic Integration**: Direct links from visualizations to relevant chatbot queries

## 🖼️ Screenshots

### Authentication Pages
- Clean, modern login and signup forms
- Password reset with email verification
- Responsive design with gradient backgrounds

### Dashboard
- Personalized welcome with progress overview
- Interactive progress visualizations
- Quick navigation to all features
- Recent achievements display

### Learning Path
- Organized topic selection interface
- Real-time progress tracking
- Adaptive quiz system
- Visual feedback for completed topics

### Visualizations
- Interactive hierarchy tree
- Clickable topic nodes
- Progress-based color coding
- Responsive network layouts

## 🚀 Installation

### Prerequisites
- Python 3.8 or higher
- MongoDB (local or cloud instance)
- Email account for SMTP (Gmail recommended)
- **Hugging Face Account** with access to CodeLlama models
- **Neo4j Database** (cloud or local instance)
- **Ngrok Account** for API tunneling
- **Google Colab** or GPU-enabled environment (recommended for model hosting)

### Step 1: Set Up Required Accounts & Services

#### 🤗 Hugging Face Setup
1. Create account at [huggingface.co](https://huggingface.co)
2. Request access to CodeLlama models:
   - Visit [meta-llama/CodeLlama-7b-Instruct-hf](https://huggingface.co/meta-llama/CodeLlama-7b-Instruct-hf)
   - Click "Request access" and wait for approval
3. Generate access token:
   - Go to Settings → Access Tokens
   - Create new token with "Read" permissions
   - Save your token: `hf_xxxxxxxxxxxxxxxxxxxxxxxxxxxxx`

#### 🗄️ Neo4j Database Setup

**Step 1: Create Neo4j Aura Account & Instance**
1. Go to [Neo4j Aura Console](https://console-preview.neo4j.io/projects/123eeeda-2ed0-44b9-b336-5ba4247068a4/instances)
2. Create a free account if you don't have one
3. Click "Create Instance" and select "AuraDB Free"
4. Choose a name for your instance (e.g., "cpp-learning-db")
5. **Important**: Copy and save your credentials when the instance is created:
   - URI: `neo4j+s://xxxxxxxx.databases.neo4j.io`
   - Username: `neo4j`
   - Password: (generated password - save this!)
6. Wait for the instance to be ready (status: "Running")

**Step 2: Populate Database with Programming Books**
1. Open the [LLM-Knowledge Graph Builder](https://llm-graph-builder.neo4jlabs.com/)
2. Click "Connect to Neo4j" and enter your Aura credentials:
   - **URI**: Your Neo4j URI from Step 1
   - **Username**: `neo4j`
   - **Password**: Your generated password from Step 1
3. Click "Test Connection" to verify
4. Upload all programming books from your project folder:
   - `PF and DS.pdf` (Programming Fundamentals)
   - `Starting Out With C++ 8th Edition - Gaddis.pdf`
   - A11 other C++ or programming books in folder or you have
5. Configure the import settings:
   - **Chunk Size**: 1000-2000 characters
   - **Overlap**: 200 characters
   - **Processing Mode**: "Entities and Relationships"
6. Click "Process Files" and wait for completion
7. Verify the data was imported by checking the "Graph" tab

**Step 3: Verify Database Setup**
1. In the LLM-Knowledge Graph Builder, go to the "Graph" tab
2. You should see nodes representing:
   - **Chunk**: Text chunks from your books
   - **Message**: Processed knowledge for quiz generation
   - **Entity**: Programming concepts and topics
3. Run a test query to confirm data is available:
   ```cypher
   MATCH (c:Chunk) RETURN count(c) as chunk_count
   ```

#### 🌐 Ngrok Setup
1. Create account at [ngrok.com](https://ngrok.com)
2. Get your auth token from the dashboard
3. Install ngrok: `pip install pyngrok`

### Step 2: Deploy AI Models (Google Colab Recommended)

#### 🤖 Deploy Quiz Generation Model
1. Open `quiz_model.ipynb` in Google Colab
2. Update credentials in the notebook:
   ```python
   HF_TOKEN = "your_huggingface_token"
   URI = "your_neo4j_uri"
   USER = "neo4j"
   PASSWORD = "your_neo4j_password"
   ```
3. Update ngrok auth token:
   ```python
   !ngrok authtoken YOUR_NGROK_TOKEN
   ```
4. Run all cells - this will:
   - Install dependencies
   - Load CodeLlama model
   - Start Flask API server
   - Create public ngrok URL
5. **Copy the ngrok URL** (e.g., `https://xxxxx.ngrok-free.app`)

#### 💬 Deploy Chatbot Model
1. Open `chatbot_for_c++_only.ipynb` in Google Colab
2. Update credentials (same as above)
3. Run all cells to deploy chatbot API
4. **Copy the ngrok URL** for chatbot

### Step 3: Clone and Set Up Main Application
```bash
git clone <repository-url>
cd programming-learning-platform
```

### Step 4: Create Virtual Environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### Step 5: Install Dependencies

**🎯 Recommended: Use the minimal installation since AI models run in Google Colab**

#### 🚀 **Main Application (Recommended)**
For the Streamlit application (AI models run separately in Colab):
```bash
pip install -r requirements-minimal.txt
```
**Includes**: Streamlit app, auth, visualizations, database connections (~15 packages)
**Note**: This is all you need! AI models run in Google Colab notebooks.

#### 👨‍💻 **Development Installation**
For contributors and developers:
```bash
pip install -r requirements-dev.txt
```
**Includes**: Main app + testing, linting, documentation tools

#### ⚠️ **Full Local Installation (Not Recommended)**
Only if you want to run AI models locally (requires powerful GPU):
```bash
pip install -r requirements.txt
```
**Includes**: All features including heavy AI dependencies (~100+ packages, ~15GB)
**Warning**: Requires CUDA-compatible GPU and significant resources

#### ☁️ **Google Colab (AI Models)**
AI models run in Colab - no local installation needed!
```bash
# Already included in the notebook cells:
!pip install pyngrok neo4j Flask Flask-CORS
!pip install --upgrade transformers accelerate bitsandbytes
```

### Step 6: Set Up Environment Variables
Create a `.env` file in the root directory:
```env
# MongoDB Configuration
MONGO_URI=mongodb://localhost:27017/

# Email Configuration (for password reset)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password

# AI Model APIs (from Colab deployments)
QUIZ_API_URL=https://your-quiz-ngrok-url.ngrok-free.app
CHATBOT_API_URL=https://your-chatbot-ngrok-url.ngrok-free.app

# Neo4j Configuration (for local testing)
NEO4J_URI=neo4j+s://your-instance.databases.neo4j.io
NEO4J_USER=neo4j
NEO4J_PASSWORD=your-neo4j-password

# Hugging Face Token (if running models locally)
HF_TOKEN=your_huggingface_token
```

### Step 7: Prepare Data Files
Ensure these files are in the root directory:
- `cpp-prerequisites-json.json` - Topic prerequisites data
- `questionbank.json` - Curated quiz questions
- Additional supporting files as needed

### Step 8: Update API URLs in Code
Update the ngrok URLs in your code:

In `FRONTEND.py`, update the quiz API URL:
```python
# Line ~XXX in show_topic_selection()
quiz_ngrok_url = "https://your-quiz-ngrok-url.ngrok-free.app"
```

In `chatbot_api.py`, update the chatbot API URL:
```python
# Update the API endpoint
CHATBOT_API_URL = "https://your-chatbot-ngrok-url.ngrok-free.app"
```

### Step 9: Run the Application
```bash
streamlit run login_signup.py
```

The application will be available at `http://localhost:8501`

## 📊 Data Preparation

### Neo4j Knowledge Base Setup
Your Neo4j database should contain C++ programming knowledge in this structure:

```cypher
// For Quiz Generation - Message nodes
CREATE (m:Message {content: "Your C++ knowledge text here"})

// For Chatbot - Chunk nodes  
CREATE (c:Chunk {text: "Your C++ knowledge text here"})
```

### Sample Data Loading Script
```python
from neo4j import GraphDatabase

def load_cpp_knowledge(uri, user, password):
    driver = GraphDatabase.driver(uri, auth=(user, password))
    
    # Sample C++ knowledge
    cpp_topics = [
        "Variables in C++ are containers for storing data values...",
        "Loops in C++ allow you to execute code repeatedly...",
        "Functions in C++ are blocks of code that perform specific tasks..."
    ]
    
    with driver.session() as session:
        for topic in cpp_topics:
            # For quiz generation
            session.run("CREATE (m:Message {content: $content})", content=topic)
            # For chatbot
            session.run("CREATE (c:Chunk {text: $text})", text=topic)
    
    driver.close()
```

## 📦 Requirements Files Guide

### Available Requirements Files

| File | Purpose | Package Count | Use Case |
|------|---------|---------------|----------|
| `requirements.txt` | Full installation | ~100+ | Production, complete features |
| `requirements-minimal.txt` | Basic app only | ~15 | Quick demo, testing |
| `requirements-dev.txt` | Development | ~150+ | Contributors, developers |
| `requirements-colab.txt` | Colab notebooks | ~10 | AI model deployment |

### Installation Scenarios

#### 🎯 **Scenario 1: Standard Setup (Recommended)**
```bash
# Install main application (AI models run in Google Colab)
pip install -r requirements-minimal.txt

# What you get:
# ✅ Complete Streamlit application
# ✅ User authentication system
# ✅ Learning path interface
# ✅ Progress visualizations
# ✅ Topic hierarchy tree
# ✅ Basic quiz (from question bank)
# ✅ AI-powered quiz generation (via Colab API)
# ✅ AI chatbot functionality (via Colab API)
```

#### 🚀 **Scenario 2: Local AI Models (Advanced)**
```bash
# Install everything locally (requires powerful GPU)
pip install -r requirements.txt

# What you get:
# ✅ Everything from Scenario 1
# ✅ Local AI model execution
# ⚠️ Requires: CUDA GPU, 15GB+ storage, 16GB+ RAM
# ⚠️ Complex setup and maintenance
```

#### 👨‍💻 **Scenario 3: Development Environment**
```bash
# Full development setup
pip install -r requirements-dev.txt

# Additional tools included:
# ✅ Code formatting (black, isort)
# ✅ Linting (flake8, pylint)
# ✅ Testing (pytest, coverage)
# ✅ Type checking (mypy)
# ✅ Documentation tools
# ✅ Pre-commit hooks
```

#### ☁️ **Scenario 4: Google Colab AI Models**
```bash
# In Colab notebook cell
!pip install pyngrok neo4j Flask Flask-CORS
!pip install --upgrade transformers accelerate bitsandbytes

# Or use requirements file:
!pip install -r requirements-colab.txt

# Pre-installed in Colab:
# ✅ PyTorch, NumPy, Pandas
# ✅ Matplotlib, Requests
# ✅ Basic ML libraries
```

### Platform-Specific Installation

#### 🪟 **Windows Users**
```bash
# Install Visual C++ Build Tools first
# Then install requirements
pip install -r requirements.txt

# For GPU support:
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
```

#### 🍎 **macOS (Apple Silicon)**
```bash
# Install requirements
pip install -r requirements.txt

# PyTorch for Apple Silicon:
pip install torch torchvision torchaudio
```

#### 🐧 **Linux**
```bash
# Install requirements
pip install -r requirements.txt

# For CUDA support:
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
```

### Upgrading Dependencies
```bash
# Upgrade all packages to latest versions
pip install -r requirements.txt --upgrade

# Upgrade specific package
pip install streamlit --upgrade

# Check for outdated packages
pip list --outdated
```

### Choosing the Right Requirements File

#### 🤔 **Which file should I use?**

**Use `requirements-minimal.txt` if:** (Recommended)
- ✅ You want the complete application with AI features
- ✅ You're using Google Colab for AI models (recommended)
- ✅ You want fast installation and minimal storage
- ✅ You're on any machine (no GPU required)
- ✅ You want easy setup and maintenance

**Use `requirements.txt` if:** (Advanced)
- ✅ You want to run AI models locally
- ✅ You have a powerful CUDA-compatible GPU
- ✅ You have 15GB+ free storage space
- ✅ You prefer not to use Google Colab
- ✅ You need offline AI model execution

**Use `requirements-dev.txt` if:**
- ✅ You're contributing to the project
- ✅ You want to run tests
- ✅ You need code formatting tools
- ✅ You're developing new features

**Use `requirements-colab.txt` if:**
- ✅ You're running notebooks in Google Colab
- ✅ You're deploying AI models only
- ✅ You don't need the main Streamlit app

#### 💾 **Storage Requirements**

| Requirements File | Download Size | Disk Space | Installation Time | Use Case |
|------------------|---------------|------------|-------------------|----------|
| `requirements-minimal.txt` | ~50MB | ~200MB | 2-3 minutes | **Recommended** - Complete app |
| `requirements.txt` | ~5GB | ~15GB | 15-30 minutes | Advanced - Local AI models |
| `requirements-dev.txt` | ~6GB | ~18GB | 20-40 minutes | Development |
| `requirements-colab.txt` | N/A | N/A | N/A | Auto-installed in Colab |

#### ⚡ **Migration Between Requirements**

```bash
# Recommended: Start with minimal (includes all features via Colab)
pip install -r requirements-minimal.txt
# Deploy AI models in Google Colab notebooks
# Update ngrok URLs in your .env file

# Advanced: Upgrade to local AI models (if you have powerful GPU)
pip install -r requirements.txt  # Adds heavy AI dependencies

# Downgrade from full to minimal
pip freeze > current-packages.txt
pip uninstall -r current-packages.txt -y
pip install -r requirements-minimal.txt
```

## ⚙️ Configuration

### MongoDB Setup
1. Install MongoDB locally or use MongoDB Atlas
2. Create a database named `auth_app_db`
3. Collections will be created automatically:
   - `users` - User accounts and progress
   - `reset_tokens` - Password reset tokens

### Email Configuration
1. Enable 2-factor authentication on your Gmail account
2. Generate an app-specific password
3. Use the app password in the `SMTP_PASSWORD` environment variable

### Quiz API Setup (Optional)
1. Set up the quiz generation API (separate service)
2. Update the `QUIZ_API_URL` in environment variables
3. Ensure the API accepts POST requests with topic parameters

## 📖 Usage

### For New Users

1. **Sign Up**: Create a new account with username, email, and password
2. **Topic Selection**: Select programming topics you've already learned
3. **Take Quiz**: Complete quizzes on your most recent topic
4. **Explore Visualizations**: View your progress in interactive charts
5. **Use Chatbot**: Ask questions about programming concepts

### For Returning Users

1. **Login**: Access your account with username/password
2. **Dashboard**: View your personalized learning dashboard
3. **Continue Learning**: Pick up where you left off
4. **Track Progress**: Monitor your advancement through topics
5. **Get Recommendations**: Follow suggested learning paths

### Navigation

- **🏠 Dashboard**: Overview of your learning progress
- **📚 Learning Path**: Topic selection and quiz interface
- **🌳 Tree Visualization**: Interactive topic relationship viewer
- **🤖 Chatbot**: AI assistant for programming questions

## 📁 File Structure

```
├── login_signup.py          # Main authentication and dashboard logic
├── FRONTEND.py              # Learning path and quiz interface
├── hierarchy_frontend.py    # Tree visualization component
├── chatbot_api.py          # Chatbot integration
├── quiz_generation.py      # Quiz API communication
├── KG_Frontend.py          # Knowledge graph visualization
├── requirements.txt        # Python dependencies
├── .env                    # Environment variables (create this)
├── cpp-prerequisites-json.json  # Topic prerequisites data
├── questionbank.json       # Curated quiz questions
└── lib/                    # Frontend assets (CSS, JS)
    ├── tom-select/         # Multi-select component
    └── vis-9.1.2/         # Network visualization library
```

## 🔌 API Endpoints

### Quiz Generation API
```
POST /generate-quiz
Content-Type: application/json

{
    "topic": "Arrays and Vectors",
    "difficulty": "mixed"
}
```

### Chatbot API
```
POST /chat
Content-Type: application/json

{
    "question": "How do pointers work in C++?",
    "context": "learning_programming"
}
```

## 🗄️ Database Schema

### Users Collection
```javascript
{
  "_id": ObjectId,
  "username": String,
  "email": String,
  "password": String (hashed),
  "learned_topics": [String],
  "last_quiz_topic": String
}
```

### Reset Tokens Collection
```javascript
{
  "_id": ObjectId,
  "email": String,
  "token": String,
  "expires_at": Date
}
```

## 🧠 System Architecture

### 🏗️ **How the System Works**

```
┌─────────────────┐    API Calls    ┌─────────────────┐
│   Streamlit     │ ──────────────► │  Google Colab   │
│   Application   │                 │   AI Models     │
│  (Your Local)   │ ◄────────────── │  (Cloud-hosted) │
└─────────────────┘    Responses    └─────────────────┘
        │                                    │
        │                                    │
        ▼                                    ▼
┌─────────────────┐                 ┌─────────────────┐
│    MongoDB      │                 │     Neo4j       │
│ (User Progress) │                 │ (AI Knowledge)  │
└─────────────────┘                 └─────────────────┘
```

### 🎯 **Why This Architecture?**

**✅ Benefits:**
- **No GPU Required**: Run on any laptop/computer
- **Fast Setup**: 2-3 minute installation vs 30+ minutes
- **Low Storage**: 200MB vs 15GB+ for local AI models
- **Free GPU**: Google Colab provides free GPU access
- **Easy Maintenance**: No complex AI model management
- **Always Updated**: Latest model versions in Colab

**📱 Components:**

### 1. **Streamlit Application** (Local - `requirements-minimal.txt`)
- **User Interface**: Authentication, dashboards, visualizations
- **Database**: MongoDB for user accounts and progress
- **Quiz Fallback**: Local question bank when AI unavailable
- **API Client**: Communicates with Colab-hosted AI models

### 2. **AI Models** (Google Colab - Auto-installed)

#### Quiz Generation Model (`quiz_model.ipynb`)
- **Model**: CodeLlama-7b-Instruct-hf (Meta)
- **Purpose**: Generates 3-difficulty level quizzes (Easy, Medium, Hard)
- **Data Source**: Neo4j database with Message nodes
- **API Endpoint**: `/quiz?topic=<topic_name>`
- **Response Format**: JSON with generated quiz text
- **Deployment**: Google Colab + ngrok tunnel

#### Chatbot Model (`chatbot_for_c++_only.ipynb`)
- **Model**: CodeLlama-7b-Instruct-hf (Meta)
- **Purpose**: Answers C++ programming questions only
- **Data Source**: Neo4j database with Chunk nodes
- **API Endpoint**: `/chat` (POST with JSON)
- **Safety Features**: Topic filtering, non-C++ query rejection
- **Deployment**: Google Colab + ngrok tunnel

### 🚀 **Model Features**
- **GPU Acceleration**: Automatic CUDA detection and usage
- **Memory Optimization**: Float16 precision for efficient inference
- **Context Management**: Truncation and token limits for stable generation
- **Knowledge Integration**: Real-time Neo4j database queries
- **Fallback Mechanisms**: General knowledge when specific data unavailable

## 🛠️ Dependencies

### Core Dependencies
- `streamlit>=1.29.0` - Web application framework
- `pymongo>=4.6.1` - MongoDB integration
- `python-dotenv>=1.0.0` - Environment variable management
- `plotly` - Interactive visualizations
- `pandas` - Data manipulation
- `networkx` - Graph operations

### AI Model Dependencies (for Colab notebooks)
- `torch` - PyTorch framework
- `transformers` - Hugging Face transformers
- `neo4j` - Neo4j database driver
- `flask` - API server framework
- `pyngrok` - Ngrok tunnel management

### Visualization & UI
- `pyvis` - Network visualizations
- `plotly` - Charts and graphs
- Custom CSS/JS libraries in `lib/` directory

### Security & Email
- `hashlib` - Password hashing (built-in)
- `smtplib` - Email sending (built-in)
- `secrets` - Token generation (built-in)

## 🔧 Troubleshooting

### Common Issues

1. **MongoDB Connection Error**
   - Ensure MongoDB is running
   - Check the `MONGO_URI` in your `.env` file
   - Verify network connectivity

2. **Email Not Sending**
   - Verify SMTP credentials in `.env`
   - Check if 2FA is enabled and app password is used
   - Ensure firewall allows SMTP connections

3. **Quiz Generation Fails**
   - Check if quiz API is running and accessible
   - Verify the `QUIZ_API_URL` in environment variables
   - Fallback to question bank should work automatically

4. **Visualization Not Loading**
   - Ensure all files in `lib/` directory are present
   - Check browser console for JavaScript errors
   - Verify data files (`cpp-prerequisites-json.json`) exist

5. **AI Model Issues**
   - **CodeLlama Access Denied**: Ensure you have requested and received access to CodeLlama models on Hugging Face
   - **Ngrok URL Expired**: Ngrok free tier URLs expire after 8 hours - restart Colab notebooks to get new URLs
   - **Out of Memory**: Use Google Colab Pro for better GPU memory, or reduce batch sizes
   - **Model Loading Slow**: First-time model download can take 10-15 minutes
   - **Neo4j Connection Failed**: Check your database is running and credentials are correct

6. **API Connection Issues**
   - **Quiz Generation Fails**: Verify ngrok URL is updated in `FRONTEND.py`
   - **Chatbot Not Responding**: Check ngrok URL in `chatbot_api.py`
   - **CORS Errors**: Add ngrok-skip-browser-warning header if needed
   - **API Timeout**: Increase timeout values for model inference

7. **Dependency & Installation Issues**
   - **Package Conflicts**: Use virtual environment: `python -m venv venv`
   - **Large Download**: Full requirements.txt downloads ~5GB+ of packages
   - **Memory Issues**: Use `requirements-minimal.txt` for basic functionality
   - **Build Failures**: Install Visual C++ Build Tools (Windows) or Xcode (macOS)
   - **CUDA Issues**: Ensure CUDA-compatible PyTorch version for GPU support
   - **Version Conflicts**: Use `pip install --upgrade --force-reinstall package_name`

### Performance Tips

- Use MongoDB Atlas for better performance in production
- Implement caching for frequently accessed data
- Optimize quiz generation by caching common topics
- Use CDN for static assets in production
- **Keep Colab notebooks active** to prevent model unloading
- **Use Google Colab Pro** for faster GPUs and longer runtimes
- **Cache model responses** for common topics to reduce API calls



## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Streamlit team for the amazing framework
- MongoDB for reliable data storage
- Plotly for interactive visualizations
- The open-source community for various libraries used

---

**Built with ❤️ using Streamlit, MongoDB, and modern web technologies** 
