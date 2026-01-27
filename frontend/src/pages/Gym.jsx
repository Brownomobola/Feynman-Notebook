import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { Dumbbell, Trophy, ArrowRight, CheckCircle, XCircle, Loader2 } from 'lucide-react';
import Button from '../components/Button';
import Card from '../components/Card';
import StreamingText from '../components/StreamingText';
import MathDisplay from '../components/MathDisplay';
import { useSSEStream, useGymSession } from '../hooks';
import apiService from '../services/api';

const Gym = () => {
  const { analysisId, gymSeshId } = useParams();
  const navigate = useNavigate();
  
  const [loading, setLoading] = useState(true);
  const [attemptText, setAttemptText] = useState('');
  const [sessionComplete, setSessionComplete] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  
  const { streamData, isStreaming, isComplete, handleChunk, startStream, reset } = useSSEStream();
  const { gymSession, currentQuestion, questionHistory, initializeSession, moveToNextQuestion, updateScore } = useGymSession();

  useEffect(() => {
    initializeGymSession();
  }, [analysisId]);

  const initializeGymSession = async () => {
    try {
      setLoading(true);
      const session = await apiService.getGymSession(analysisId, gymSeshId, 1);
      const firstQuestion = {
        id: session.first_question_id,
        question: session.first_question,
        question_number: 1
      };
      initializeSession(
        {
          id: gymSeshId,
          score: 0,
          num_questions: 0,
          status: 'active'
        },
        firstQuestion
      );
    } catch (err) {
      console.error('Failed to initialize gym session:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmitAttempt = async () => {
    if (!attemptText.trim() || !currentQuestion || !gymSession || isSubmitting) return;

    setIsSubmitting(true);
    startStream();

    try {
      await apiService.submitGymSolution(
        {
          gymSeshId: gymSession.id,
          questionId: currentQuestion.id,
          questionNumber: currentQuestion.question_number,
          problem: currentQuestion.question,
          attempt: attemptText,
        },
        (data) => {
          handleChunk(data);
          
          // Handle gym evaluation saved event
          if (data.type === 'gym_evaluation_saved') {
            updateScore(streamData.is_correct);
            
            if (data.is_complete) {
              // Move to next question
              moveToNextQuestion({
                id: data.next_question_id,
                question: streamData.next_question,
                question_number: data.question_number,
                feedback: streamData.feedback,
                solution: streamData.solution,
                is_correct: streamData.is_correct
              });
              
              setAttemptText('');
              reset();
            }
          }
        }
      );
    } catch (err) {
      console.error('Failed to submit solution:', err);
      setIsSubmitting(false);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleCompleteSession = async () => {
    if (!gymSession) return;
    
    try {
      await apiService.completeGymSession(gymSession.id);
      setSessionComplete(true);
    } catch (err) {
      console.error('Failed to complete session:', err);
    }
  };

  const getScorePercentage = () => {
    if (!gymSession || gymSession.num_questions === 0) return 0;
    return Math.round((gymSession.score / gymSession.num_questions) * 100);
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <Loader2 
            size={48} 
            className="animate-spin mx-auto mb-4"
            style={{ color: 'var(--color-accent)' }}
          />
          <p style={{ color: 'var(--color-ink-light)' }}>
            Preparing your practice session...
          </p>
        </div>
      </div>
    );
  }

  if (sessionComplete) {
    return (
      <div className="min-h-screen py-12">
        <div className="container mx-auto px-6">
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className="max-w-2xl mx-auto"
          >
            <Card>
              <div className="text-center">
                <div 
                  className="inline-flex items-center justify-center p-4 rounded-2xl mb-6"
                  style={{ backgroundColor: 'var(--color-success-bg)' }}
                >
                  <Trophy size={48} style={{ color: 'var(--color-correct)' }} />
                </div>

                <h1 
                  className="text-4xl font-bold mb-4"
                  style={{ 
                    fontFamily: 'var(--font-serif)',
                    color: 'var(--color-ink)'
                  }}
                >
                  Session Complete!
                </h1>

                <div className="mb-8">
                  <div 
                    className="text-6xl font-bold mb-2"
                    style={{ color: 'var(--color-accent)' }}
                  >
                    {getScorePercentage()}%
                  </div>
                  <p style={{ color: 'var(--color-ink-light)' }}>
                    You got {gymSession?.score} out of {gymSession?.num_questions} correct
                  </p>
                </div>

                <div className="flex gap-4 justify-center">
                  <Button
                    variant="primary"
                    onClick={() => navigate('/analysis')}
                    icon={<ArrowRight size={20} />}
                  >
                    New Analysis
                  </Button>
                  <Button
                    variant="secondary"
                    onClick={() => navigate('/history')}
                  >
                    View History
                  </Button>
                </div>
              </div>
            </Card>
          </motion.div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen py-12">
      <div className="container mx-auto px-6">
        <div className="max-w-4xl mx-auto">
          {/* Header with Progress */}
          <div className="mb-8">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-3">
                <div 
                  className="p-2 rounded-lg"
                  style={{ backgroundColor: 'var(--color-highlight)' }}
                >
                  <Dumbbell size={24} style={{ color: 'var(--color-accent)' }} />
                </div>
                <div>
                  <h1 
                    className="text-3xl font-bold"
                    style={{ 
                      fontFamily: 'var(--font-serif)',
                      color: 'var(--color-ink)'
                    }}
                  >
                    Practice Gym
                  </h1>
                  <p style={{ color: 'var(--color-ink-light)' }}>
                    Question {currentQuestion?.question_number || 1}
                  </p>
                </div>
              </div>

              <div className="text-right">
                <div 
                  className="text-3xl font-bold"
                  style={{ color: 'var(--color-accent)' }}
                >
                  {gymSession?.score || 0}/{gymSession?.num_questions || 0}
                </div>
                <p className="text-sm" style={{ color: 'var(--color-ink-light)' }}>
                  Score
                </p>
              </div>
            </div>

            {/* Progress Bar */}
            <div 
              className="h-2 rounded-full overflow-hidden"
              style={{ backgroundColor: 'var(--color-muted)' }}
            >
              <motion.div
                initial={{ width: 0 }}
                animate={{ width: `${getScorePercentage()}%` }}
                transition={{ duration: 0.5 }}
                className="h-full rounded-full"
                style={{ backgroundColor: 'var(--color-correct)' }}
              />
            </div>
          </div>

          <AnimatePresence mode="wait">
            {/* Question Display */}
            {!isStreaming && !isComplete && currentQuestion && (
              <motion.div
                key={`question-${currentQuestion.question_number}`}
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -20 }}
              >
                <Card className="mb-6">
                  <h2 
                    className="text-xl font-semibold mb-4"
                    style={{ 
                      fontFamily: 'var(--font-serif)',
                      color: 'var(--color-ink)'
                    }}
                  >
                    Problem
                  </h2>
                  <MathDisplay content={currentQuestion.question} />
                </Card>

                <Card>
                  <h2 
                    className="text-xl font-semibold mb-4"
                    style={{ 
                      fontFamily: 'var(--font-serif)',
                      color: 'var(--color-ink)'
                    }}
                  >
                    Your Solution
                  </h2>
                  <textarea
                    value={attemptText}
                    onChange={(e) => setAttemptText(e.target.value)}
                    placeholder="Type your solution here... Use LaTeX for math (e.g., $x^2 + 1$)"
                    className="w-full mb-4"
                    rows={8}
                  />
                  
                  <div className="flex gap-4">
                    <Button
                      variant="primary"
                      onClick={handleSubmitAttempt}
                      disabled={!attemptText.trim()}
                      icon={<CheckCircle size={20} />}
                    >
                      Submit Answer
                    </Button>
                    <Button
                      variant="secondary"
                      onClick={handleCompleteSession}
                    >
                      End Session
                    </Button>
                  </div>
                </Card>
              </motion.div>
            )}

            {/* Feedback Display */}
            {(isStreaming || isComplete) && (
              <motion.div
                key="feedback"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
              >
                <Card>
                  <div className="mb-6">
                    {streamData.is_correct !== undefined && (
                      <div className="flex items-center gap-3 mb-4">
                        {streamData.is_correct ? (
                          <>
                            <CheckCircle size={32} style={{ color: 'var(--color-correct)' }} />
                            <h3 
                              className="text-2xl font-bold"
                              style={{ color: 'var(--color-correct)' }}
                            >
                              Correct!
                            </h3>
                          </>
                        ) : (
                          <>
                            <XCircle size={32} style={{ color: 'var(--color-incorrect)' }} />
                            <h3 
                              className="text-2xl font-bold"
                              style={{ color: 'var(--color-incorrect)' }}
                            >
                              Not Quite
                            </h3>
                          </>
                        )}
                      </div>
                    )}
                  </div>

                  {streamData.feedback && (
                    <div className="mb-6">
                      <h4 
                        className="text-lg font-semibold mb-3"
                        style={{ color: 'var(--color-ink)' }}
                      >
                        Feedback
                      </h4>
                      <StreamingText 
                        content={streamData.feedback} 
                        isComplete={isComplete}
                      />
                    </div>
                  )}

                  {streamData.solution && (
                    <div 
                      className="p-4 rounded-lg"
                      style={{ 
                        backgroundColor: 'var(--color-highlight)',
                        borderLeft: '4px solid var(--color-accent)'
                      }}
                    >
                      <h4 
                        className="text-lg font-semibold mb-3"
                        style={{ color: 'var(--color-ink)' }}
                      >
                        Solution
                      </h4>
                      <StreamingText 
                        content={streamData.solution} 
                        isComplete={isComplete}
                      />
                    </div>
                  )}

                  {isComplete && (
                    <div className="mt-6 text-center">
                      <Button
                        variant="primary"
                        onClick={() => {
                          reset();
                          setAttemptText('');
                        }}
                        icon={<ArrowRight size={20} />}
                      >
                        Next Question
                      </Button>
                    </div>
                  )}
                </Card>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </div>
  );
};

export default Gym;
