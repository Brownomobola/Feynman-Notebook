# Feynman Tutor - Debug Your Intuition

An intelligent tutoring application that helps engineering students debug their intuition by comparing handwritten work against AI-generated golden solutions.

## 🎯 Core Concept

This isn't just another answer-checking tool. Feynman Tutor performs a sophisticated analysis of your problem-solving approach:

1. **Precision Diagnosis**: Compares your work against a "Golden Solution" to identify exactly where your understanding diverges
2. **Feynman-Style Explanations**: Provides conceptual explanations that build understanding from first principles
3. **Targeted Practice**: Generates practice problems that strengthen weak points in your understanding

## 🚀 Features

### Analysis Mode
- Upload images of handwritten problems and solutions
- AI transcription of mathematical notation to LaTeX
- Real-time streaming analysis with:
  - What you got right (positive reinforcement)
  - Where understanding broke down (precise diagnosis)
  - Conceptual explanations (Feynman-style learning)
- Automatic tagging of mathematical concepts

### Gym Mode
- Practice sessions with AI-generated problems
- Instant feedback on attempts
- Progressive difficulty
- Score tracking and performance metrics
- Full solution walkthroughs

### History
- Review past analyses
- Track learning progress
- Access previous explanations
- Restart practice sessions from any analysis

## 🛠️ Tech Stack

### Frontend
- **React 18** - Modern React with hooks
- **Vite** - Lightning-fast dev server and build tool
- **Framer Motion** - Sophisticated animations and transitions
- **React Router** - Client-side routing
- **KaTeX** - Beautiful mathematical typesetting
- **Lucide React** - Clean, consistent icons

### Backend (Django)
- **Django REST Framework** - API endpoints
- **Google Gemini AI** - Analysis and problem generation
- **Server-Sent Events (SSE)** - Real-time streaming responses
- **PIL** - Image processing and enhancement

## 📦 Installation

### Prerequisites
- Node.js 18+ and npm
- Python 3.10+
- Django 4.2+
- Google Gemini API key

### Frontend Setup

1. Install dependencies:
```bash
npm install
```

2. Start the development server:
```bash
npm run dev
```

The app will be available at `http://localhost:5173`

### Backend Setup

1. Install Python dependencies:
```bash
pip install django djangorestframework google-generativeai pillow
```

2. Set up your Gemini API key in `backend/backend/settings.py`:
```python
GEMINI_API_KEY = 'your-api-key-here'
```

3. Run migrations:
```bash
python manage.py makemigrations
python manage.py migrate
```

4. Start the Django server:
```bash
python manage.py runserver
```

The API will be available at `http://localhost:8000`

## 🎨 Design Philosophy

### Aesthetic Direction
The UI embraces an **Academic Elegance** aesthetic:

- **Typography**: Crimson Pro (serif) for headings, DM Sans for body, JetBrains Mono for code
- **Colors**: Warm paper tones (#FDFBF7) with educational red accent (#C84630)
- **Motion**: Purposeful animations that enhance understanding without distraction
- **Layout**: Generous whitespace with focused content areas

This creates a sophisticated, scholarly feel that respects the serious nature of learning while remaining approachable and modern.

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

## 📁 Project Structure

```
feynman-tutor/
├── src/
│   ├── components/          # Reusable UI components
│   │   ├── Button.jsx
│   │   ├── Card.jsx
│   │   ├── Header.jsx
│   │   ├── ImageUpload.jsx
│   │   ├── MathDisplay.jsx
│   │   └── StreamingText.jsx
│   ├── pages/              # Main application pages
│   │   ├── Home.jsx
│   │   ├── Analysis.jsx
│   │   ├── Gym.jsx
│   │   └── History.jsx
│   ├── services/           # API communication
│   │   └── api.js
│   ├── hooks/              # Custom React hooks
│   │   └── index.js
│   ├── App.jsx             # Main app component
│   ├── main.jsx            # Entry point
│   └── index.css           # Global styles
├── index.html              # HTML template
├── vite.config.js          # Vite configuration
└── package.json            # Dependencies
```

## 🎯 Key Components

### Custom Hooks
- `useImageUpload` - Handle image uploads with preview
- `useSSEStream` - Manage Server-Sent Events streaming
- `useGymSession` - Track gym session state
- `useLocalStorage` - Persist data locally
- `useDebounce` - Debounce user input

### Core Components
- `MathDisplay` - Render LaTeX and mathematical notation
- `StreamingText` - Display SSE-streamed text with cursor
- `ImageUpload` - Drag-and-drop image upload with preview
- `Card` - Animated card container with hover effects
- `Button` - Consistent button styling with loading states

## 🔧 Configuration

### API Endpoints
Configure the backend URL in `src/services/api.js`:
```javascript
const API_BASE_URL = '/api';  // Will proxy to localhost:8000 in dev
```

### Styling
Customize the design system in `src/index.css`:
```css
:root {
  --color-paper: #FDFBF7;
  --color-accent: #C84630;
  /* ... other CSS variables */
}
```

## 🚢 Deployment

### Build for Production
```bash
npm run build
```

This creates an optimized build in the `dist/` directory.

### Preview Production Build
```bash
npm run preview
```

## 🤝 Contributing

This is an educational project designed to showcase:
- Modern React patterns and best practices
- Real-time streaming with SSE
- AI integration for educational purposes
- Sophisticated UI/UX design

## 📄 License

MIT License - feel free to use this project for learning and development.

## 🙏 Acknowledgments

- Built with inspiration from Richard Feynman's teaching philosophy
- Designed for engineering students who want to truly understand concepts
- Powered by Google's Gemini AI for analysis and generation

---

**Debug Your Intuition. Build True Understanding.**
