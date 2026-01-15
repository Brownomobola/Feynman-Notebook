# Feynman Tutor - Setup Guide

This guide will walk you through setting up the Feynman Tutor application from scratch.

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Backend Setup](#backend-setup)
3. [Frontend Setup](#frontend-setup)
4. [Running the Application](#running-the-application)
5. [Troubleshooting](#troubleshooting)

## Prerequisites

Before you begin, ensure you have the following installed:

### Required Software
- **Node.js** (v18.0.0 or higher)
  - Download from [nodejs.org](https://nodejs.org/)
  - Verify installation: `node --version`

- **npm** (comes with Node.js)
  - Verify installation: `npm --version`

- **Python** (v3.10 or higher)
  - Download from [python.org](https://www.python.org/)
  - Verify installation: `python --version` or `python3 --version`

- **pip** (comes with Python)
  - Verify installation: `pip --version` or `pip3 --version`

### API Keys
- **Google Gemini API Key**
  - Sign up at [Google AI Studio](https://makersuite.google.com/app/apikey)
  - Create a new API key
  - Keep it secure - you'll need it for the backend setup

## Backend Setup

### 1. Navigate to Backend Directory
```bash
cd backend
```

### 2. Create Virtual Environment (Recommended)
```bash
# On macOS/Linux
python3 -m venv venv
source venv/bin/activate

# On Windows
python -m venv venv
venv\Scripts\activate
```

### 3. Install Python Dependencies
```bash
pip install django djangorestframework google-generativeai pillow python-dotenv
```

Or if you have a requirements.txt:
```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables
Create a `.env` file in your backend directory:
```bash
touch .env
```

Add the following to `.env`:
```
GEMINI_API_KEY=your-actual-api-key-here
DEBUG=True
SECRET_KEY=your-secret-key-here
```

### 5. Update Settings
In `backend/settings.py`, ensure you have:
```python
import os
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

# CORS settings for development
CORS_ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]
```

### 6. Run Database Migrations
```bash
python manage.py makemigrations
python manage.py migrate
```

### 7. Create Superuser (Optional)
```bash
python manage.py createsuperuser
```

### 8. Test Backend Server
```bash
python manage.py runserver
```

Visit `http://localhost:8000/admin` to verify the server is running.

## Frontend Setup

### 1. Navigate to Frontend Directory
```bash
cd feynman-tutor
```

### 2. Install Dependencies
```bash
npm install
```

This will install all required packages including:
- React & React DOM
- React Router
- Framer Motion
- KaTeX
- Lucide React
- Vite

### 3. Configure Environment (Optional)
Create a `.env` file:
```bash
cp .env.example .env
```

Edit `.env` if you need to customize API endpoints:
```
VITE_API_URL=http://localhost:8000/api
```

### 4. Verify Configuration
Check that `vite.config.js` has the correct proxy settings:
```javascript
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      }
    }
  }
})
```

## Running the Application

### Starting Both Servers

You'll need two terminal windows/tabs:

#### Terminal 1 - Backend
```bash
cd backend
source venv/bin/activate  # On Windows: venv\Scripts\activate
python manage.py runserver
```

Backend will run on `http://localhost:8000`

#### Terminal 2 - Frontend
```bash
cd feynman-tutor
npm run dev
```

Frontend will run on `http://localhost:5173`

### Access the Application
Open your browser and navigate to:
```
http://localhost:5173
```

## Testing the Setup

### 1. Test Homepage
- You should see the Feynman Tutor landing page
- Navigation should work (Home, Analysis, History)

### 2. Test Analysis Page
- Navigate to `/analysis`
- Try uploading an image or typing text
- Submit for analysis (requires valid backend connection)

### 3. Check Browser Console
- Open Developer Tools (F12)
- Check Console tab for any errors
- Network tab should show successful API requests

### 4. Check Backend Logs
- Backend terminal should show incoming requests
- Look for 200 status codes (success)

## Troubleshooting

### Frontend Issues

#### Port Already in Use
```bash
# If port 5173 is in use, Vite will prompt for another port
# Or specify a different port:
npm run dev -- --port 3000
```

#### Module Not Found Errors
```bash
# Clear npm cache and reinstall
rm -rf node_modules package-lock.json
npm install
```

#### CORS Errors
- Ensure backend CORS settings include frontend URL
- Check that backend is running
- Verify proxy configuration in `vite.config.js`

### Backend Issues

#### Gemini API Key Not Found
- Check `.env` file exists and has correct key
- Verify `python-dotenv` is installed
- Restart Django server after updating `.env`

#### Database Errors
```bash
# Reset database (WARNING: loses data)
rm db.sqlite3
python manage.py migrate
```

#### Import Errors
```bash
# Ensure virtual environment is activated
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Reinstall dependencies
pip install -r requirements.txt
```

### Common Issues

#### API Requests Fail
1. Check backend is running (`http://localhost:8000`)
2. Check frontend proxy configuration
3. Look at browser Network tab for error details
4. Check backend terminal for error logs

#### Styles Not Loading
1. Clear browser cache
2. Hard refresh (Ctrl+Shift+R or Cmd+Shift+R)
3. Check that `index.css` is imported in `main.jsx`

#### Images Not Uploading
1. Check file size (max 10MB)
2. Verify file type (JPEG, PNG, GIF, WebP)
3. Check backend media settings
4. Look at Network tab for error response

## Development Tips

### Hot Reload
- Frontend: Vite provides instant hot reload
- Backend: Django auto-reloads on file changes (development server)

### Debugging
```javascript
// Frontend - Add console logs
console.log('Debug info:', data);

# Backend - Add print statements
print(f"Debug info: {data}")
```

### Building for Production

#### Frontend
```bash
npm run build
npm run preview  # Test production build
```

#### Backend
- Set `DEBUG=False` in settings
- Configure proper database (PostgreSQL recommended)
- Set up static file serving
- Configure ALLOWED_HOSTS

## Additional Resources

- [React Documentation](https://react.dev/)
- [Vite Documentation](https://vitejs.dev/)
- [Django Documentation](https://docs.djangoproject.com/)
- [Google Gemini API](https://ai.google.dev/)

## Getting Help

If you encounter issues:
1. Check error messages carefully
2. Search error messages online
3. Review Django and React documentation
4. Check GitHub issues for similar problems

## Next Steps

Once setup is complete:
1. Explore the application features
2. Try analyzing a math problem
3. Test the gym practice mode
4. Review the codebase to understand the architecture

---

Happy coding! 🚀
