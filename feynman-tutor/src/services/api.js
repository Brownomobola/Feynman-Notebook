// API Service for backend communication

const API_BASE_URL = '/api';

class APIService {
  constructor() {
    this.baseURL = API_BASE_URL;
  }

  // Helper method for handling fetch requests
  async request(endpoint, options = {}) {
    const url = `${this.baseURL}${endpoint}`;
    const config = {
      headers: {
        'Content-Type': 'application/json',
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

  // Transcribe an image or text
  async transcribe(formData, type = 'analysis') {
    const endpoint = type === 'gym' ? '/gym/transcribe/' : '/transcribe/';
    
    const response = await fetch(`${this.baseURL}${endpoint}`, {
      method: 'POST',
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
    
    if (problemData.problemImage) {
      formData.append('problem_image', problemData.problemImage);
    }
    if (problemData.problemText) {
      formData.append('problem_text', problemData.problemText);
    }
    if (problemData.attemptImage) {
      formData.append('attempt_image', problemData.attemptImage);
    }
    if (problemData.attemptText) {
      formData.append('attempt_text', problemData.attemptText);
    }

    const response = await fetch(`${this.baseURL}/analysis/`, {
      method: 'POST',
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
    return this.request('/analyses/');
  }

  // Get single analysis
  async getAnalysis(id) {
    return this.request(`/analysis/${id}/`);
  }

  // Create gym session
  async createGymSession(analysisId, numQuestions = 5) {
    return this.request('/gym/create/', {
      method: 'POST',
      body: JSON.stringify({
        analysis_id: analysisId,
        num_questions: numQuestions,
      }),
    });
  }

  // Get gym question
  async getGymQuestion(gymSeshId, questionId) {
    return this.request(`/gym/question/?gym_sesh_id=${gymSeshId}&question_id=${questionId}`);
  }

  // Submit gym solution with SSE streaming
  async submitGymSolution(solutionData, onChunk) {
    const formData = new FormData();
    formData.append('gym_sesh_id', solutionData.gymSeshId);
    formData.append('gym_question_id', solutionData.questionId);
    formData.append('question_number', solutionData.questionNumber);
    formData.append('problem', solutionData.problem);
    formData.append('attempt', solutionData.attempt);

    const response = await fetch(`${this.baseURL}/gym/solution/`, {
      method: 'POST',
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
}

export default new APIService();
