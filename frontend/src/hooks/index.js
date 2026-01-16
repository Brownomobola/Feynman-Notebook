import { useState, useEffect, useCallback } from 'react';

// Hook for image upload with preview
export const useImageUpload = () => {
  const [image, setImage] = useState(null);
  const [preview, setPreview] = useState(null);

  const handleImageChange = useCallback((file) => {
    if (file && file.type.startsWith('image/')) {
      setImage(file);
      const reader = new FileReader();
      reader.onloadend = () => {
        setPreview(reader.result);
      };
      reader.readAsDataURL(file);
    }
  }, []);

  const clearImage = useCallback(() => {
    setImage(null);
    setPreview(null);
  }, []);

  return { image, preview, handleImageChange, clearImage };
};

// Hook for SSE streaming state
export const useSSEStream = () => {
  const [streamData, setStreamData] = useState({});
  const [isStreaming, setIsStreaming] = useState(false);
  const [isComplete, setIsComplete] = useState(false);
  const [error, setError] = useState(null);

  const handleChunk = useCallback((data) => {
    if (data.type === 'error') {
      setError(data.content);
      setIsStreaming(false);
      return;
    }

    if (data.type === 'complete') {
      setIsComplete(true);
      setIsStreaming(false);
      if (data.content) {
        setStreamData(prev => ({ ...prev, ...data.content }));
      }
      return;
    }

    if (data.type === 'partial') {
      setStreamData(prev => ({
        ...prev,
        [data.field]: (prev[data.field] || '') + data.content
      }));
    } else if (data.type === 'array' || data.type === 'boolean') {
      setStreamData(prev => ({
        ...prev,
        [data.field]: data.content
      }));
    }
  }, []);

  const startStream = useCallback(() => {
    setStreamData({});
    setIsStreaming(true);
    setIsComplete(false);
    setError(null);
  }, []);

  const reset = useCallback(() => {
    setStreamData({});
    setIsStreaming(false);
    setIsComplete(false);
    setError(null);
  }, []);

  return {
    streamData,
    isStreaming,
    isComplete,
    error,
    handleChunk,
    startStream,
    reset
  };
};

// Hook for gym session state
export const useGymSession = () => {
  const [gymSession, setGymSession] = useState(null);
  const [currentQuestion, setCurrentQuestion] = useState(null);
  const [questionHistory, setQuestionHistory] = useState([]);

  const initializeSession = useCallback((session, question) => {
    setGymSession(session);
    setCurrentQuestion(question);
    setQuestionHistory([]);
  }, []);

  const addToHistory = useCallback((question) => {
    setQuestionHistory(prev => [...prev, question]);
  }, []);

  const moveToNextQuestion = useCallback((nextQuestion) => {
    if (currentQuestion) {
      addToHistory(currentQuestion);
    }
    setCurrentQuestion(nextQuestion);
  }, [currentQuestion, addToHistory]);

  const updateScore = useCallback((isCorrect) => {
    setGymSession(prev => {
      if (!prev) return null;
      return {
        ...prev,
        score: prev.score + (isCorrect ? 1 : 0),
        num_questions: prev.num_questions + 1
      };
    });
  }, []);

  const reset = useCallback(() => {
    setGymSession(null);
    setCurrentQuestion(null);
    setQuestionHistory([]);
  }, []);

  return {
    gymSession,
    currentQuestion,
    questionHistory,
    initializeSession,
    moveToNextQuestion,
    updateScore,
    reset
  };
};

// Hook for local storage persistence
export const useLocalStorage = (key, initialValue) => {
  const [storedValue, setStoredValue] = useState(() => {
    try {
      const item = window.localStorage.getItem(key);
      return item ? JSON.parse(item) : initialValue;
    } catch (error) {
      console.error(error);
      return initialValue;
    }
  });

  const setValue = useCallback((value) => {
    try {
      const valueToStore = value instanceof Function ? value(storedValue) : value;
      setStoredValue(valueToStore);
      window.localStorage.setItem(key, JSON.stringify(valueToStore));
    } catch (error) {
      console.error(error);
    }
  }, [key, storedValue]);

  return [storedValue, setValue];
};

// Hook for debouncing input
export const useDebounce = (value, delay = 500) => {
  const [debouncedValue, setDebouncedValue] = useState(value);

  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);

    return () => {
      clearTimeout(handler);
    };
  }, [value, delay]);

  return debouncedValue;
};
