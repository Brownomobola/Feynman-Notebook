import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { Upload, FileText, CheckCircle, ArrowRight, Dumbbell } from 'lucide-react';
import Button from '../components/Button';
import Card from '../components/Card';
import ImageUpload from '../components/ImageUpload';
import StreamingText from '../components/StreamingText';
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
  const { streamData, isStreaming, isComplete, error, handleChunk, startStream, reset } = useSSEStream();

  const canSubmit = (problemImage.image || problemText) && (attemptImage.image || attemptText);

  const handleSubmit = async () => {
    if (!canSubmit) return;

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
            setCurrentStep('results');
          }
        }
      );
    } catch (err) {
      console.error('Analysis failed:', err);
    }
  };

  const handleStartGym = () => {
    if (analysisId) {
      navigate(`/gym/${analysisId}`);
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
                    icon={<ArrowRight size={20} />}
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
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
};

export default Analysis;
