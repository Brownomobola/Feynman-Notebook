// API Service for backend communication
// Prefer env-based base URL; fallback to Vite dev proxy '/api'
const API_BASE_URL = import.meta.env?.VITE_API_BASE_URL || '/api';

// Get CSRF token from cookie
function getCSRFToken() {
  const name = 'csrftoken';
  let cookieValue = null;
  if (document.cookie && document.cookie !== '') {
    const cookies = document.cookie.split(';');
    for (let i = 0; i < cookies.length; i++) {
      const cookie = cookies[i].trim();
      if (cookie.substring(0, name.length + 1) === (name + '=')) {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
        break;
      }
    }
  }
  return cookieValue;
}

class APIService {
  constructor() {
    this.baseURL = API_BASE_URL;
  }

  // Helper method for handling fetch requests
  async request(endpoint, options = {}) {
    const url = `${this.baseURL}${endpoint}`;
    const csrfToken = getCSRFToken();
    
    const config = {
      credentials: 'include', // Include cookies for session auth
      headers: {
        'Content-Type': 'application/json',
        ...(csrfToken && { 'X-CSRFToken': csrfToken }),
        ...options.headers,
      },
      ...options,
    };

    try {
      const response = await fetch(url, config);
      
      if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        throw new Error(error.error || `HTTP error! status: ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error('API request failed:', error);
      throw error;
    }
  }

  // ============ Auth Methods ============
  
  // Get CSRF token (call on app init)
  async getCSRFToken() {
    return this.request('/auth/csrf/');
  }

  // Get current user info
  async getMe() {
    return this.request('/auth/me/');
  }

  // Register new user
  async register(username, email, password, passwordConfirm) {
    return this.request('/auth/register/', {
      method: 'POST',
      body: JSON.stringify({
        username,
        email,
        password,
        password_confirm: passwordConfirm
      }),
    });
  }

  // Login
  async login(username, password) {
    return this.request('/auth/login/', {
      method: 'POST',
      body: JSON.stringify({ username, password }),
    });
  }

  // Logout
  async logout() {
    return this.request('/auth/logout/', {
      method: 'POST',
    });
  }

  // ============ Existing Methods ============

  // Transcribe an image or text
  async transcribe(Data, type = 'analysis') {
    const endpoint = type === 'gym' ? '/gym/transcribe/' : '/analysis/transcribe/';
    const formData = new FormData();

    if (Data.dataImage) {
      formData.append('data_image', Data.dataImage);
    }
    if (Data.dataText) {
      formData.append('data_text', Data.dataText);
    }
    // Add is_question if type is 'analysis' and there is a question
    if (type === 'analysis') {
      if (Data.isQuestion) {
        formData.append('is_question', 'True');
      };
    }

    const response = await fetch(`${this.baseURL}${endpoint}`, {
      method: 'POST',
      credentials: 'include',
      body: formData,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.error || 'Transcription failed');
    }

    return await response.text();
  }

  // Create analysis with SSE streaming
  async createAnalysis(problemData, onChunk) {
    const formData = new FormData();

    if (problemData.transcribedProblemText) {
      formData.append('problem', problemData.transcribedProblemText);
    }
    if (problemData.transcribedAttemptText) {
      formData.append('attempt', problemData.transcribedAttemptText);
    }

    const response = await fetch(`${this.baseURL}/analysis/`, {
      method: 'POST',
      credentials: 'include',
      body: formData,
    });

    if (!response.ok) {
      throw new Error('Analysis request failed');
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const data = JSON.parse(line.slice(6));
            onChunk(data);
          } catch (e) {
            console.error('Failed to parse SSE data:', e);
          }
        }
      }
    }
  }

  // Get all analyses
  async getAnalyses() {
    return this.request('/analysis/');
  }

  // Get single analysis
  async getAnalysis(id) {
    return this.request(`/analysis/${id}/`);
  }

  // Create gym session
  //async createGymSession(analysisId, numQuestions = 5) {
  //  return this.request('/gym/create/', {
  //    method: 'POST',
  //    body: JSON.stringify({
  //      analysis_id: analysisId,
  //      num_questions: numQuestions,
  //    }),
  //  });
  //} 

  // Get gym question
  //async getGymQuestion(gymSeshId, questionId) {
  //  return this.request(`/gym/?gym_sesh_id=${gymSeshId}&gym_question_id=${questionId}`);
  //}
  
  // Get gym question, can also be used to start a new session
  async getGymSession(analysisId, gymSeshId, questionCount) {
    return this.request(`/gym/?analysis_id=${analysisId}&gym_sesh_id=${gymSeshId}&question_num=${questionCount}`);
  }
  // Submit gym solution with SSE streaming
  async submitGymSolution(solutionData, onChunk) {
    const formData = new FormData();
    formData.append('gym_sesh_id', solutionData.gymSeshId);
    formData.append('gym_question_id', solutionData.questionId);
    formData.append('question_number', solutionData.questionNumber);
    formData.append('problem', solutionData.problem);
    formData.append('attempt', solutionData.attempt);

    const response = await fetch(`${this.baseURL}/gym/`, {
      method: 'POST',
      credentials: 'include',
      body: formData,
    });

    if (!response.ok) {
      throw new Error('Solution submission failed');
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const data = JSON.parse(line.slice(6));
            onChunk(data);
          } catch (e) {
            console.error('Failed to parse SSE data:', e);
          }
        }
      }
    }
  }

  // Complete gym session
  async completeGymSession(gymSeshId) {
    return this.request('/gym/complete/', {
      method: 'POST',
      body: JSON.stringify({ gym_sesh_id: gymSeshId }),
    });
  }

  // Get chat history for an analysis
  async getChatHistory(analysisId) {
    return this.request(`/chat/?analysis_id=${analysisId}`);
  }

  // Send chat message with SSE streaming
  async sendChatMessage(analysisId, message, onChunk) {
    const response = await fetch(`${this.baseURL}/chat/`, {
      method: 'POST',
      credentials: 'include',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        analysis_id: analysisId,
        message: message,
      }),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.error || 'Chat request failed');
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const data = JSON.parse(line.slice(6));
            onChunk(data);
          } catch (e) {
            console.error('Failed to parse SSE data:', e);
          }
        }
      }
    }
  }
}

export default new APIService();
