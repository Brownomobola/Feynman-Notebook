# Feynman Tutor

**Feynman Tutor** is an AI-powered educational platform designed to help students master complex engineering and mathematics concepts using the **Feynman Technique**. Instead of just providing answers, it identifies gaps in your intuition, explains concepts using real-world analogies, and encourages deep understanding.

## 🎯 Core Concept

This isn't just another answer-checking tool. Feynman Tutor performs a sophisticated analysis of your problem-solving approach:

1. **Precision Diagnosis**: Compares your work against a "Golden Solution" to identify exactly where your understanding diverges
2. **Feynman-Style Explanations**: Provides conceptual explanations that build understanding from first principles
3. **Targeted Practice**: Generates practice problems that strengthen weak points in your understanding

## 🚀 Features

- **Multi-modal Input:** Upload images of your handwritten math problems and attempts, or type them out.
- **AI Transcription:** Automatically converts handwritten math into LaTeX/Markdown using Google Gemini.
- **Deep Analysis:**
    - Compares your attempt against a "Golden Solution".
    - Identifies the exact step where your logic diverged.
    - Provides constructive feedback, praise, and diagnosis.
    - Uses the **Feynman Prompts** to generate analogies for better intuition.
- **Real-time Streaming:** Experience feedback as it's generated via Server-Sent Events (SSE).
- **The Gym:** 
    - Practice sessions with AI-generated problems
    - Instant feedback on attempts
    - Progressive difficulty
    - Score tracking and performance metrics
    - Full solution walkthroughs
- **History:**
- Review past analyses
- Track learning progress
- Access previous explanations
- Restart practice sessions from any analysis

## 🛠️ Tech Stack

### Backend
- **Framework:** [Django 6.0](https://www.djangoproject.com/)
- **API:** [Django REST Framework](https://www.django-rest-framework.org/) with [ADRF](https://github.com/em1208/adrf) for async support.
- **AI Integration:** [Google GenAI (Gemini)](https://ai.google.dev/)
- **Database:** PostgreSQL / SQLite (default for dev)
- **Server:** Daphne (ASGI) for async capabilities.

### Frontend
- **Framework:** [React 18](https://react.dev/)
- **Build Tool:** [Vite](https://vitejs.dev/)
- **Styling & UI:** CSS Modules / Tailwind (implied), [Framer Motion](https://www.framer.com/motion/) for animations, [Lucide React](https://lucide.dev/) for icons.
- **Math Rendering:** [KaTeX](https://katex.org/)

## 📦 Installation & Setup

### Prerequisites
- Python 3.10+
- Node.js 18+ and npm
- A Google Gemini API Key

### 1. Clone the Repository
```bash
git clone https://github.com/Brownomobola/Feynman-Notebook.git
cd Feynman-Notebook
```

### 2. Backend Setup
Navigate to the backend directory and set up the Python environment.

```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # On Windows use: .venv\Scripts\activate
pip install -r ../requirements.txt
```

**Environment Variables:**
Create a `.env` file in the `backend/` directory (or where `settings.py` expects it) and add your API key:
```env
GEMINI_API_KEY=your_gemini_api_key_here
```
Add your Postgres database config
```env
DB_NAME=db_name
DB_USER=db_user
DB_PASSWORD=secure_password123!
DB_HOST=localhost
DB_PORT=5432
```
Add your Django secret key and the debug mode as well
```env
DJANGO_SECRET=your_django_secret

DEBUG=True 
```

**Run Migrations:**
```bash
python manage.py migrate
```

**Start the Server:**
```bash
python manage.py runserver
```

### 3. Frontend Setup
Open a new terminal, navigate to the frontend directory, and install dependencies.

```bash
cd frontend
npm install
```

**Start Development Server:**
```bash
npm run dev
```

Visit `http://localhost:5173` (or the port shown in your terminal) to use the application.

## 🔄 Data Flow

### Analysis Workflow
```
User Input (Problem + Attempt)
  ↓
Image Transcription (if images provided)
  ↓
AI Analysis (Gemini 2.0 Flash)
  ↓
SSE Streaming Response
  ↓
Progressive UI Updates
  ↓
Save to Database
  ↓
Display Results + Gym Option
```

### Gym Workflow
```
Create Gym Session
  ↓
Generate First Question (Gemini)
  ↓
User Submits Attempt
  ↓
AI Evaluation (SSE Stream)
  ↓
Update Score + Generate Next Question
  ↓
Repeat until session complete
  ↓
Display Final Score
```

## 🤝 Contributing

Contributions are welcome! Please perform the following steps:
1. Fork the project.
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`).
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`).
4. Push to the Branch (`git push origin feature/AmazingFeature`).
5. Open a Pull Request.

## 📄 License

Distributed under the MIT License. See `LICENSE` for more information.

## 🙏 Acknowledgments

- Built with inspiration from Richard Feynman's teaching philosophy
- Designed by an engineering student for engineering students who want to truly understand concepts
- Powered by Google's Gemini AI for analysis and generation

