# Feynman Tutor - AI Agent Instructions

## Project Overview
Feynman Tutor is an AI-powered tutoring platform using the Feynman Technique. It analyzes student problem-solving attempts, identifies conceptual gaps, and provides real-world analogies for understanding.

## Architecture

### Stack
- **Backend**: Django 6.0 + ADRF (async DRF) + Google Gemini AI
- **Frontend**: React 18 + Vite + Framer Motion + KaTeX
- **Communication**: Server-Sent Events (SSE) for real-time streaming

### Core Data Flow
1. User uploads problem/attempt (image or text) → `TranscribeAnalysisImageView`
2. Gemini transcribes to LaTeX → Frontend receives transcript
3. Both transcripts submitted to `AnalyzeSolutionView`
4. Streaming SSE response with progressive JSON parsing → `StreamGenerator`
5. Analysis saved to DB, user can start Gym practice session

### Key Files
- [backend/api/services/streaming.py](../backend/api/services/streaming.py) - SSE streaming with progressive JSON field extraction
- [backend/api/schemas.py](../backend/api/schemas.py) - Pydantic schemas define AI response structure
- [backend/api/views/](../backend/api/views/) - Async views using ADRF's `APIView`
- [frontend/src/services/api.js](../frontend/src/services/api.js) - API client with SSE handling
- [frontend/src/hooks/index.js](../frontend/src/hooks/index.js) - `useSSEStream` hook for streaming state

## Development Commands

```bash
# Backend (from backend/)
source .venv/bin/activate
python manage.py runserver          # Dev server
python manage.py migrate            # Apply migrations

# Frontend (from frontend/)
npm run dev                         # Vite dev server (port 5173)

# Tests
```

## Conventions & Patterns

### Backend
- **Async views required**: Use `async def` for all view methods and `await` for ORM calls (`acreate`, `aget`, `asave`)
- **Streaming responses**: Return `StreamingHttpResponse(stream_generator(), content_type='text/event-stream')`
- **AI prompts**: System prompts live in view methods; use XML-style tags (`<role>`, `<reasoning_process>`)
- **Schemas**: Define Pydantic models in `schemas.py` - these control Gemini's JSON output structure

### Frontend
- **SSE handling**: Use `useSSEStream` hook, call `handleChunk(data)` in the `onChunk` callback
- **Math rendering**: All LaTeX uses `$...$` (inline) or `$$...$$` (block), rendered via `<MathDisplay />`
- **Styling**: CSS variables from `index.css` (`--color-ink`, `--color-accent`, etc.)

### SSE Event Format
```javascript
// Partial update (string fields streamed progressively)
{ type: 'partial', field: 'explanation', content: 'chunk text', is_complete: false }

// Array fields (sent complete)
{ type: 'array', field: 'tags', content: ['tag1', 'tag2'] }

// Final complete response
{ type: 'complete', field: 'all', content: { ...fullObject }, is_complete: true }
```

### Models Relationship
```
AnalysisTranscript (images/text)
GymTranscript (images/text)
Analysis (problem, attempt, AI feedback)
  └── GymSesh (practice session)
       └── GymQuestions (individual practice problems)
```

## Environment Variables (backend/.env)
```
GEMINI_API_KEY=...
DJANGO_SECRET=...
DEBUG=True
DB_NAME/DB_USER/DB_PASSWORD/DB_HOST/DB_PORT (for PostgreSQL)
```

## Common Tasks

### Adding a new AI-powered endpoint
1. Define Pydantic schema in `schemas.py` with `Field(description=...)` for each property
2. Create async view in `views/` using `StreamGenerator` for streaming
3. Add URL pattern to `urls.py`
4. Add frontend API method in `api.js` with SSE reader loop

### Modifying AI behavior
- Edit system prompts in view methods - prompts use structured XML tags
- Adjust schema fields to change what Gemini returns
- `StreamGenerator` auto-handles string/array/boolean fields based on schema type
