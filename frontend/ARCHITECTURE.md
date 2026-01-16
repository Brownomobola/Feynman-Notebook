# Feynman Tutor - Architecture Documentation

## System Overview

Feynman Tutor is a full-stack intelligent tutoring application that combines React frontend with Django backend, integrated with Google's Gemini AI for analysis and problem generation.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                        Frontend (React)                      │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────────┐   │
│  │    Pages    │  │  Components  │  │   Services/API   │   │
│  │  - Home     │  │  - Button    │  │  - API Service   │   │
│  │  - Analysis │  │  - Card      │  │  - SSE Handler   │   │
│  │  - Gym      │  │  - Upload    │  │                  │   │
│  │  - History  │  │  - Math      │  │                  │   │
│  └─────────────┘  └──────────────┘  └──────────────────┘   │
│                            │                                 │
└────────────────────────────┼─────────────────────────────────┘
                             │ HTTP/SSE
                             │
┌────────────────────────────┼─────────────────────────────────┐
│                    Backend (Django)                          │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────────┐   │
│  │    Views    │  │    Models    │  │   AI Services    │   │
│  │  - Analyze  │  │  - Analysis  │  │  - Transcriber   │   │
│  │  - Gym      │  │  - GymSesh   │  │  - StreamGen     │   │
│  │  - History  │  │  - Questions │  │                  │   │
│  └─────────────┘  └──────────────┘  └──────────────────┘   │
│                            │                                 │
└────────────────────────────┼─────────────────────────────────┘
                             │
                    ┌────────┴────────┐
                    │  Gemini AI API  │
                    │  - Analysis     │
                    │  - Generation   │
                    └─────────────────┘
```

## Component Architecture

### Frontend Components

#### 1. Pages (Route Components)
- **Home.jsx**: Landing page with feature showcase
- **Analysis.jsx**: Problem submission and analysis display
- **Gym.jsx**: Practice session interface
- **History.jsx**: Past analyses browser

#### 2. UI Components
- **Button.jsx**: Reusable button with variants and loading states
- **Card.jsx**: Animated container with hover effects
- **Header.jsx**: Navigation with active tab indication
- **ImageUpload.jsx**: Drag-and-drop image upload
- **MathDisplay.jsx**: LaTeX rendering with KaTeX
- **StreamingText.jsx**: Real-time SSE text display

#### 3. Services
- **api.js**: Centralized API communication layer
  - Handles all backend requests
  - Manages SSE streaming
  - Error handling and retries

#### 4. Custom Hooks
- **useImageUpload**: Image file handling
- **useSSEStream**: Server-Sent Events management
- **useGymSession**: Gym session state management
- **useLocalStorage**: Persistent storage
- **useDebounce**: Input debouncing

### Backend Architecture

#### 1. Models
```python
AnalysisTranscript
├── image_obj: ImageField
├── text_obj: TextField
├── is_question: BooleanField
└── transcript: TextField

Analysis
├── problem: TextField
├── attempt: TextField
├── title: CharField
├── tags: JSONField
├── praise: TextField
├── diagnosis: TextField
└── explanation: TextField

GymSesh
├── analysis: ForeignKey(Analysis)
├── status: CharField (PENDING/ACTIVE/COMPLETED)
├── num_questions: IntegerField
├── score: IntegerField
└── timestamps

GymQuestions
├── gym_sesh: ForeignKey(GymSesh)
├── status: CharField
├── question: TextField
├── attempt: TextField
├── is_correct: BooleanField
├── feedback: TextField
└── solution: TextField
```

#### 2. Services
- **ImageTranscriber**: 
  - Handles image preprocessing
  - Transcribes handwritten math to LaTeX
  - Uses Gemini 2.5 Flash model

- **AnalysisStreamGenerator**:
  - Manages SSE streaming
  - Progressive JSON parsing
  - Handles string, array, and boolean fields

#### 3. Views/Endpoints

##### Analysis Endpoints
```
POST /api/transcribe/
- Transcribes problem or attempt images
- Returns: Transcribed text

POST /api/analysis/
- Creates new analysis (SSE streaming)
- Returns: Streamed analysis data
- Final event: { type: 'analysis_saved', analysis_id: ... }

GET /api/analyses/
- Lists all analyses
- Returns: { analyses: [...] }

GET /api/analysis/<id>/
- Gets single analysis
- Returns: Analysis object
```

##### Gym Endpoints
```
POST /api/gym/transcribe/
- Transcribes gym attempt images
- Returns: Transcribed text

POST /api/gym/create/
- Creates new gym session
- Returns: { gym_sesh_id, first_question_id, first_question }

GET /api/gym/question/
- Gets current question
- Returns: Question object

POST /api/gym/solution/
- Submits solution (SSE streaming)
- Returns: Streamed evaluation + next question
- Final event: { type: 'gym_evaluation_saved', ... }

POST /api/gym/complete/
- Completes gym session
- Returns: Final score and statistics
```

## Data Flow Patterns

### 1. Analysis Flow
```
User Input → Frontend
    ↓
Form Data → API Service
    ↓
Django View → ImageTranscriber (if images)
    ↓
Transcribed Text → Gemini AI
    ↓
SSE Stream ← AnalysisStreamGenerator
    ↓
Frontend Updates ← useSSEStream hook
    ↓
Save to DB → Analysis model
    ↓
Final Event → Update UI
```

### 2. Gym Flow
```
Create Session → POST /gym/create/
    ↓
Display Question → GET /gym/question/
    ↓
User Attempts → Submit Form
    ↓
Evaluate → POST /gym/solution/ (SSE)
    ↓
Stream Feedback → Frontend Display
    ↓
Generate Next → Save + New Question
    ↓
Repeat until → Complete Session
```

## State Management

### Frontend State
- **Local Component State**: useState for UI state
- **URL State**: React Router for navigation
- **Session Storage**: For temporary gym session data
- **SSE Stream State**: Custom useSSEStream hook

### Backend State
- **Database**: SQLite (dev) / PostgreSQL (prod)
- **Session**: Django session middleware
- **Cache**: Optional Redis for performance

## API Communication

### Request Types
1. **Standard REST**: GET/POST with JSON
2. **Multipart Form**: For file uploads
3. **Server-Sent Events**: For streaming responses

### SSE Message Format
```javascript
{
  type: 'partial' | 'array' | 'boolean' | 'complete' | 'error',
  field: 'field_name',
  content: 'field_value' | [...] | true/false
}
```

## Security Considerations

### Frontend
- Input validation before submission
- File type and size validation
- XSS prevention (React auto-escapes)
- HTTPS in production

### Backend
- CORS configuration
- API key protection (environment variables)
- File upload validation
- Rate limiting on expensive operations
- SQL injection protection (Django ORM)

## Performance Optimizations

### Frontend
- Code splitting with React.lazy
- Image optimization
- Debounced inputs
- Memoized components
- Progressive loading

### Backend
- Database indexing
- Async views with Django async
- Image preprocessing caching
- Streaming responses (SSE)
- Query optimization

## Deployment Architecture

### Development
```
Frontend: Vite Dev Server (localhost:5173)
Backend: Django Dev Server (localhost:8000)
Database: SQLite
```

### Production (Recommended)
```
Frontend: 
- Build: npm run build
- Serve: Nginx/Vercel/Netlify

Backend:
- Server: Gunicorn + Nginx
- Database: PostgreSQL
- Static: S3/CloudFront
- Cache: Redis

AI Service:
- Gemini API (Google Cloud)
```

## Monitoring and Logging

### Frontend
- Console errors in development
- Error boundaries for runtime errors
- Analytics (optional): Google Analytics, Plausible

### Backend
- Django logging framework
- API request/response logging
- Error tracking: Sentry (recommended)
- Performance monitoring: New Relic/DataDog

## Testing Strategy

### Frontend Tests (Recommended)
- Unit: Jest + React Testing Library
- Integration: Cypress/Playwright
- E2E: Full user flows

### Backend Tests
- Unit: Django TestCase
- Integration: DRF APITestCase
- Mock external APIs (Gemini)

## Future Enhancements

### Technical
- WebSocket for real-time collaboration
- GraphQL API for flexible queries
- Service worker for offline capability
- Progressive Web App (PWA)

### Features
- User authentication
- Collaborative problem solving
- Progress tracking dashboard
- Spaced repetition algorithm
- Mobile app (React Native)

## Technology Decisions

### Why React?
- Component reusability
- Strong ecosystem
- Excellent developer experience
- Virtual DOM performance

### Why Django?
- Rapid development
- Built-in admin
- Strong ORM
- Security features
- Python AI ecosystem

### Why Gemini AI?
- Advanced multimodal capabilities
- Image understanding
- Structured output support
- Streaming responses
- Cost-effective

### Why SSE over WebSocket?
- Simpler implementation
- Unidirectional (sufficient for our use)
- Better with HTTP/2
- Easier to deploy

## Development Workflow

1. Backend changes → Test with Django shell/Postman
2. Frontend changes → Hot reload in browser
3. API changes → Update both sides
4. New features → Branch → PR → Review → Merge
5. Deploy → Test staging → Production

---

This architecture provides a solid foundation for an intelligent tutoring system that can scale with user needs while maintaining code quality and performance.
