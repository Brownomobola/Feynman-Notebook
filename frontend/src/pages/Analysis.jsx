import { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { Upload, FileText, CheckCircle, ArrowRight, Dumbbell, Send, MessageCircle, User, Bot } from 'lucide-react';
import Button from '../components/Button';
import Card from '../components/Card';
import ImageUpload from '../components/ImageUpload';
import StreamingText from '../components/StreamingText';
import MathDisplay from '../components/MathDisplay';
import { useImageUpload, useSSEStream } from '../hooks';
import apiService from '../services/api';

const Analysis = () => {
  const navigate = useNavigate();
  
  // Problem state
  const problemImage = useImageUpload();
  const [problemText, setProblemText] = useState('');
  
  // Attempt state
  const attemptImage = useImageUpload();
  const [attemptText, setAttemptText] = useState('');
  
  // Analysis state
  const [currentStep, setCurrentStep] = useState('input'); // input, analyzing, results
  const [analysisId, setAnalysisId] = useState(null);
  const [gymSeshId, setGymSeshId] = useState(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const { streamData, isStreaming, isComplete, error, handleChunk, startStream, reset } = useSSEStream();

  // Chat state
  const [chatMessages, setChatMessages] = useState([]);
  const [chatInput, setChatInput] = useState('');
  const [isChatStreaming, setIsChatStreaming] = useState(false);
  const [streamingMessage, setStreamingMessage] = useState('');
  const chatContainerRef = useRef(null);
  const chatInputRef = useRef(null);

  // Auto-scroll chat to bottom
  useEffect(() => {
    if (chatContainerRef.current) {
      chatContainerRef.current.scrollTop = chatContainerRef.current.scrollHeight;
    }
  }, [chatMessages, streamingMessage]);

  // Load chat history when analysis is complete
  useEffect(() => {
    if (analysisId && isComplete) {
      loadChatHistory();
    }
  }, [analysisId, isComplete]);

  const loadChatHistory = async () => {
    try {
      const response = await apiService.getChatHistory(analysisId);
      setChatMessages(response.messages || []);
    } catch (err) {
      console.error('Failed to load chat history:', err);
    }
  };

  const handleSendMessage = async () => {
    if (!chatInput.trim() || isChatStreaming || !analysisId) return;

    const userMessage = chatInput.trim();
    setChatInput('');
    setIsChatStreaming(true);
    setStreamingMessage('');

    // Optimistically add user message to UI
    setChatMessages(prev => [...prev, {
      id: Date.now(),
      role: 'user',
      content: userMessage,
      created_at: new Date().toISOString()
    }]);

    try {
      await apiService.sendChatMessage(analysisId, userMessage, (data) => {
        if (data.type === 'text') {
          setStreamingMessage(prev => prev + data.content);
        } else if (data.type === 'complete') {
          // Add the complete AI message
          setChatMessages(prev => [...prev, {
            id: Date.now() + 1,
            role: 'model',
            content: data.content,
            created_at: new Date().toISOString()
          }]);
          setStreamingMessage('');
          setIsChatStreaming(false);
        } else if (data.type === 'error') {
          console.error('Chat error:', data.content);
          setIsChatStreaming(false);
          setStreamingMessage('');
        }
      });
    } catch (err) {
      console.error('Chat failed:', err);
      setIsChatStreaming(false);
      setStreamingMessage('');
    }
  };

  const handleChatKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const canSubmit = (problemImage.image || problemText) && (attemptImage.image || attemptText) && !isSubmitting && !isStreaming;

  const handleSubmit = async () => {
    if (!canSubmit || isSubmitting) return;

    setIsSubmitting(true);
    setCurrentStep('analyzing');
    startStream();

    try {
      // Create the promises (requests) but do not await them individually yet
      const problemTranscriptionPromise = apiService.transcribe(
        { dataImage: problemImage.image, 
          dataText: problemText,
          isQuestion: true},
        'analysis'
      );

      const attemptTranscriptionPromise = apiService.transcribe(
        { dataImage: attemptImage.image, 
          dataText: attemptText,
          isQuestion: false},
        'analysis'
      );

      // Await both transcriptions together
      const [problemTranscription, attemptTranscription] = await Promise.all([
        problemTranscriptionPromise,
        attemptTranscriptionPromise
      ]);

      // Only proceed to create analysis after transcription is done
      await apiService.createAnalysis(
        {
          transcribedProblemText: problemTranscription,
          transcribedAttemptText: attemptTranscription,
        },
        (data) => {
          handleChunk(data);
          // Check for analysis_saved event
          if (data.type === 'analysis_saved') {
            setAnalysisId(data.analysis_id);
            setGymSeshId(data.gym_sesh_id);
            setCurrentStep('results');
          }
        }
      );
    } catch (err) {
      console.error('Analysis failed:', err);
      setIsSubmitting(false);
      setCurrentStep('input');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleStartGym = () => {
    if (analysisId && gymSeshId) {
      navigate(`/gym/${gymSeshId}/${1}`);
    }
  };

  const handleNewAnalysis = () => {
    setCurrentStep('input');
    problemImage.clearImage();
    setProblemText('');
    attemptImage.clearImage();
    setAttemptText('');
    setAnalysisId(null);
    reset();
    // Reset chat state
    setChatMessages([]);
    setChatInput('');
    setStreamingMessage('');
  };

  return (
    <div className="min-h-screen py-12">
      <div className="container mx-auto px-6">
        <AnimatePresence mode="wait">
          {/* Input Step */}
          {currentStep === 'input' && (
            <motion.div
              key="input"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              transition={{ duration: 0.5 }}
            >
              <div className="max-w-4xl mx-auto">
                <div className="text-center mb-12">
                  <h1 
                    className="text-4xl md:text-5xl font-bold mb-4"
                    style={{ 
                      fontFamily: 'var(--font-serif)',
                      color: 'var(--color-ink)'
                    }}
                  >
                    Submit Your Work
                  </h1>
                  <p 
                    className="text-xl"
                    style={{ color: 'var(--color-ink-light)' }}
                  >
                    Upload images or type out the problem and your attempt
                  </p>
                </div>

                {/* Problem Section */}
                <Card className="mb-8">
                  <div className="flex items-center gap-3 mb-6">
                    <div 
                      className="p-2 rounded-lg"
                      style={{ backgroundColor: 'var(--color-highlight)' }}
                    >
                      <FileText size={24} style={{ color: 'var(--color-accent)' }} />
                    </div>
                    <h2 
                      className="text-2xl font-semibold"
                      style={{ 
                        fontFamily: 'var(--font-serif)',
                        color: 'var(--color-ink)'
                      }}
                    >
                      1. The Problem
                    </h2>
                  </div>

                  <ImageUpload
                    label="Upload Problem Image"
                    onImageChange={problemImage.handleImageChange}
                    preview={problemImage.preview}
                    onClear={problemImage.clearImage}
                    className="mb-6"
                  />

                  <div>
                    <label 
                      className="block text-sm font-medium mb-2"
                      style={{ color: 'var(--color-ink)' }}
                    >
                      Or Type Problem Text (Optional)
                    </label>
                    <textarea
                      value={problemText}
                      onChange={(e) => setProblemText(e.target.value)}
                      placeholder="Type or paste the problem statement here..."
                      className="w-full"
                      rows={4}
                    />
                  </div>
                </Card>

                {/* Attempt Section */}
                <Card className="mb-8">
                  <div className="flex items-center gap-3 mb-6">
                    <div 
                      className="p-2 rounded-lg"
                      style={{ backgroundColor: 'var(--color-highlight)' }}
                    >
                      <Upload size={24} style={{ color: 'var(--color-accent)' }} />
                    </div>
                    <h2 
                      className="text-2xl font-semibold"
                      style={{ 
                        fontFamily: 'var(--font-serif)',
                        color: 'var(--color-ink)'
                      }}
                    >
                      2. Your Attempt
                    </h2>
                  </div>

                  <ImageUpload
                    label="Upload Your Work"
                    onImageChange={attemptImage.handleImageChange}
                    preview={attemptImage.preview}
                    onClear={attemptImage.clearImage}
                    className="mb-6"
                  />

                  <div>
                    <label 
                      className="block text-sm font-medium mb-2"
                      style={{ color: 'var(--color-ink)' }}
                    >
                      Or Type Your Work (Optional)
                    </label>
                    <textarea
                      value={attemptText}
                      onChange={(e) => setAttemptText(e.target.value)}
                      placeholder="Type your solution here..."
                      className="w-full"
                      rows={4}
                    />
                  </div>
                </Card>

                {/* Submit Button */}
                <div className="text-center">
                  <Button
                    variant="primary"
                    size="lg"
                    onClick={handleSubmit}
                    disabled={!canSubmit}
                    loading={isSubmitting || isStreaming}
                    icon={!isSubmitting && !isStreaming ? <ArrowRight size={20} /> : null}
                  >
                    Analyze My Work
                  </Button>
                  {!canSubmit && (
                    <p 
                      className="mt-3 text-sm"
                      style={{ color: 'var(--color-ink-light)' }}
                    >
                      Please provide both a problem and your attempt (image or text)
                    </p>
                  )}
                </div>
              </div>
            </motion.div>
          )}

          {/* Analyzing Step */}
          {currentStep === 'analyzing' && (
            <motion.div
              key="analyzing"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="max-w-4xl mx-auto"
            >
              <Card>
                <div className="text-center mb-8">
                  <div className="inline-flex items-center justify-center p-4 rounded-2xl mb-4"
                    style={{ backgroundColor: 'var(--color-highlight)' }}
                  >
                    <motion.div
                      animate={{ rotate: 360 }}
                      transition={{ repeat: Infinity, duration: 2, ease: "linear" }}
                    >
                      <CheckCircle size={40} style={{ color: 'var(--color-accent)' }} />
                    </motion.div>
                  </div>
                  <h2 
                    className="text-3xl font-bold mb-2"
                    style={{ 
                      fontFamily: 'var(--font-serif)',
                      color: 'var(--color-ink)'
                    }}
                  >
                    Analyzing Your Work...
                  </h2>
                  <p style={{ color: 'var(--color-ink-light)' }}>
                    Our AI is comparing your solution against the golden solution
                  </p>
                </div>

                {error && (
                  <div 
                    className="p-4 rounded-lg mb-6"
                    style={{ backgroundColor: 'var(--color-error-bg)' }}
                  >
                    <p style={{ color: 'var(--color-incorrect)' }}>
                      Error: {error}
                    </p>
                  </div>
                )}

                <div className="space-y-6">
                  {streamData.title && (
                    <StreamingText
                      title="Analysis Title"
                      content={streamData.title}
                      isComplete={isComplete}
                    />
                  )}

                  {streamData.tags && streamData.tags.length > 0 && (
                    <div>
                      <h3 className="text-lg font-semibold mb-2">Concepts</h3>
                      <div className="flex flex-wrap gap-2">
                        {streamData.tags.map((tag, i) => (
                          <span
                            key={i}
                            className="px-3 py-1 rounded-full text-sm"
                            style={{ 
                              backgroundColor: 'var(--color-highlight)',
                              color: 'var(--color-accent)'
                            }}
                          >
                            {tag}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  {streamData.praise && (
                    <StreamingText
                      title="✨ What You Got Right"
                      content={streamData.praise}
                      isComplete={isComplete}
                    />
                  )}

                  {streamData.diagnosis && (
                    <StreamingText
                      title="🔍 Where Understanding Broke Down"
                      content={streamData.diagnosis}
                      isComplete={isComplete}
                    />
                  )}

                  {streamData.explanation && (
                    <StreamingText
                      title="💡 Building Intuition"
                      content={streamData.explanation}
                      isComplete={isComplete}
                    />
                  )}
                </div>
              </Card>
            </motion.div>
          )}

          {/* Results Step */}
          {currentStep === 'results' && isComplete && (
            <motion.div
              key="results"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="max-w-4xl mx-auto"
            >
              <Card>
                <div className="text-center mb-8">
                  <div 
                    className="inline-flex items-center justify-center p-4 rounded-2xl mb-4"
                    style={{ backgroundColor: 'var(--color-success-bg)' }}
                  >
                    <CheckCircle size={40} style={{ color: 'var(--color-correct)' }} />
                  </div>
                  <h2 
                    className="text-3xl font-bold mb-2"
                    style={{ 
                      fontFamily: 'var(--font-serif)',
                      color: 'var(--color-ink)'
                    }}
                  >
                    Analysis Complete!
                  </h2>
                </div>

                <div className="space-y-6 mb-8">
                  {streamData.title && (
                    <div>
                      <h3 
                        className="text-2xl font-bold"
                        style={{ 
                          fontFamily: 'var(--font-serif)',
                          color: 'var(--color-ink)'
                        }}
                      >
                        {streamData.title}
                      </h3>
                    </div>
                  )}

                  {streamData.tags && streamData.tags.length > 0 && (
                    <div>
                      <h4 className="text-sm font-semibold mb-2" style={{ color: 'var(--color-ink-light)' }}>
                        CONCEPTS COVERED
                      </h4>
                      <div className="flex flex-wrap gap-2">
                        {streamData.tags.map((tag, i) => (
                          <span
                            key={i}
                            className="px-3 py-1 rounded-full text-sm font-medium"
                            style={{ 
                              backgroundColor: 'var(--color-highlight)',
                              color: 'var(--color-accent)'
                            }}
                          >
                            {tag}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  <div className="decorative-line" />

                  {streamData.praise && (
                    <div>
                      <h3 
                        className="text-xl font-semibold mb-3 flex items-center gap-2"
                        style={{ color: 'var(--color-correct)' }}
                      >
                        ✨ What You Got Right
                      </h3>
                      <div 
                        className="p-4 rounded-lg"
                        style={{ backgroundColor: 'var(--color-success-bg)' }}
                      >
                        <StreamingText content={streamData.praise} isComplete={true} />
                      </div>
                    </div>
                  )}

                  {streamData.diagnosis && (
                    <div>
                      <h3 
                        className="text-xl font-semibold mb-3 flex items-center gap-2"
                        style={{ color: 'var(--color-accent)' }}
                      >
                        🔍 Where Understanding Broke Down
                      </h3>
                      <div 
                        className="p-4 rounded-lg"
                        style={{ backgroundColor: 'var(--color-error-bg)' }}
                      >
                        <StreamingText content={streamData.diagnosis} isComplete={true} />
                      </div>
                    </div>
                  )}

                  {streamData.explanation && (
                    <div>
                      <h3 
                        className="text-xl font-semibold mb-3 flex items-center gap-2"
                        style={{ color: 'var(--color-ink)' }}
                      >
                        💡 Building Intuition
                      </h3>
                      <div 
                        className="p-4 rounded-lg"
                        style={{ 
                          backgroundColor: 'var(--color-highlight)',
                          borderLeft: '4px solid var(--color-accent)'
                        }}
                      >
                        <StreamingText content={streamData.explanation} isComplete={true} />
                      </div>
                    </div>
                  )}
                </div>

                <div className="flex gap-4 justify-center">
                  <Button
                    variant="primary"
                    size="lg"
                    onClick={handleStartGym}
                    icon={<Dumbbell size={20} />}
                  >
                    Practice in Gym
                  </Button>
                  <Button
                    variant="secondary"
                    size="lg"
                    onClick={handleNewAnalysis}
                  >
                    New Analysis
                  </Button>
                </div>
              </Card>

              {/* Chat Section */}
              <Card className="mt-8">
                <div className="flex items-center gap-3 mb-6">
                  <div 
                    className="p-2 rounded-lg"
                    style={{ backgroundColor: 'var(--color-highlight)' }}
                  >
                    <MessageCircle size={24} style={{ color: 'var(--color-accent)' }} />
                  </div>
                  <h2 
                    className="text-2xl font-semibold"
                    style={{ 
                      fontFamily: 'var(--font-serif)',
                      color: 'var(--color-ink)'
                    }}
                  >
                    Chat with Feynman Tutor
                  </h2>
                </div>

                <p 
                  className="text-sm mb-4"
                  style={{ color: 'var(--color-ink-light)' }}
                >
                  Ask questions about the problem, your mistakes, or the concepts involved
                </p>

                {/* Chat Messages Container */}
                <div 
                  ref={chatContainerRef}
                  className="rounded-lg p-4 mb-4 overflow-y-auto"
                  style={{ 
                    backgroundColor: 'var(--color-paper)',
                    border: '1px solid var(--color-border)',
                    minHeight: '200px',
                    maxHeight: '400px'
                  }}
                >
                  {chatMessages.length === 0 && !streamingMessage && (
                    <div 
                      className="text-center py-8"
                      style={{ color: 'var(--color-ink-light)' }}
                    >
                      <MessageCircle size={40} className="mx-auto mb-3 opacity-50" />
                      <p>No messages yet. Start a conversation!</p>
                    </div>
                  )}

                  {chatMessages.map((message, index) => (
                    <div
                      key={message.id || index}
                      className={`flex gap-3 mb-4 ${message.role === 'user' ? 'flex-row-reverse' : ''}`}
                    >
                      {/* Avatar */}
                      <div 
                        className="flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center"
                        style={{ 
                          backgroundColor: message.role === 'user' 
                            ? 'var(--color-accent)' 
                            : 'var(--color-highlight)'
                        }}
                      >
                        {message.role === 'user' ? (
                          <User size={16} style={{ color: 'white' }} />
                        ) : (
                          <Bot size={16} style={{ color: 'var(--color-accent)' }} />
                        )}
                      </div>

                      {/* Message Bubble */}
                      <div 
                        className={`max-w-[80%] p-3 rounded-lg ${
                          message.role === 'user' ? 'rounded-tr-sm' : 'rounded-tl-sm'
                        }`}
                        style={{ 
                          backgroundColor: message.role === 'user' 
                            ? 'var(--color-accent)' 
                            : 'var(--color-highlight)',
                          color: message.role === 'user' 
                            ? 'white' 
                            : 'var(--color-ink)'
                        }}
                      >
                        {message.role === 'user' ? (
                          <p className="whitespace-pre-wrap">{message.content}</p>
                        ) : (
                          <MathDisplay content={message.content} />
                        )}
                      </div>
                    </div>
                  ))}

                  {/* Streaming Message */}
                  {streamingMessage && (
                    <div className="flex gap-3 mb-4">
                      <div 
                        className="flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center"
                        style={{ backgroundColor: 'var(--color-highlight)' }}
                      >
                        <Bot size={16} style={{ color: 'var(--color-accent)' }} />
                      </div>
                      <div 
                        className="max-w-[80%] p-3 rounded-lg rounded-tl-sm"
                        style={{ 
                          backgroundColor: 'var(--color-highlight)',
                          color: 'var(--color-ink)'
                        }}
                      >
                        <MathDisplay content={streamingMessage} />
                        <span 
                          className="inline-block w-2 h-4 ml-1 animate-pulse"
                          style={{ backgroundColor: 'var(--color-accent)' }}
                        />
                      </div>
                    </div>
                  )}
                </div>

                {/* Chat Input */}
                <div className="flex gap-3">
                  <textarea
                    ref={chatInputRef}
                    value={chatInput}
                    onChange={(e) => setChatInput(e.target.value)}
                    onKeyPress={handleChatKeyPress}
                    placeholder="Ask a question about this problem..."
                    className="flex-1 resize-none"
                    rows={2}
                    disabled={isChatStreaming}
                    style={{
                      opacity: isChatStreaming ? 0.6 : 1
                    }}
                  />
                  <Button
                    variant="primary"
                    onClick={handleSendMessage}
                    disabled={!chatInput.trim() || isChatStreaming}
                    loading={isChatStreaming}
                    icon={!isChatStreaming ? <Send size={18} /> : null}
                    style={{ alignSelf: 'flex-end' }}
                  >
                    Send
                  </Button>
                </div>
              </Card>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
};

export default Analysis;
