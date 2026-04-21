import { useState, useEffect, useRef, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import apiService from '../services/api';

// ─── Constants ────────────────────────────────────────────────────────────────
const QUESTION_TYPES = { MCQ: 'MCQ', OPEN_ENDED: 'Open-Ended' };
const MAX_QUESTIONS = { MCQ: 10, 'Open-Ended': 5 };
const PHASES = {
  LOBBY: 'lobby',
  LOADING: 'loading',
  SESSION: 'session',
  SUMMARY: 'summary',
};

// ─── Loading Animation ────────────────────────────────────────────────────────
const GymLoader = ({ type }) => {
  const bars = Array.from({ length: 12 });
  return (
    <div className="gym-loader">
      <div className="gym-loader__ring">
        {bars.map((_, i) => (
          <span
            key={i}
            className="gym-loader__bar"
            style={{ '--i': i, animationDelay: `${(i / bars.length) * 1}s` }}
          />
        ))}
      </div>
      <p className="gym-loader__label">
        {type === QUESTION_TYPES.MCQ
          ? 'Generating your MCQ set…'
          : 'Crafting open-ended questions…'}
      </p>
    </div>
  );
};

// ─── Lobby ────────────────────────────────────────────────────────────────────
const Lobby = ({ onStart }) => {
  const [type, setType] = useState(null);
  const [count, setCount] = useState(null);

  const handleTypeSelect = (t) => {
    setType(t);
    setCount(null);
  };

  const max = type ? MAX_QUESTIONS[type] : 10;
  const counts = type ? Array.from({ length: max }, (_, i) => i + 1) : [];

  return (
    <div className="lobby">
      <motion.div
        className="lobby__card"
        initial={{ opacity: 0, y: 32 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
      >
        <div className="lobby__icon">🏋️</div>
        <h1 className="lobby__title">Practice Gym</h1>
        <p className="lobby__sub">Choose your workout style</p>

        <div className="lobby__type-row">
          {Object.values(QUESTION_TYPES).map((t) => (
            <button
              key={t}
              className={`lobby__type-btn${type === t ? ' --active' : ''}`}
              onClick={() => handleTypeSelect(t)}
            >
              <span className="lobby__type-icon">
                {t === QUESTION_TYPES.MCQ ? '⚡' : '✍️'}
              </span>
              <span className="lobby__type-name">{t === QUESTION_TYPES.MCQ ? 'Multiple Choice' : 'Open-Ended'}</span>
              <span className="lobby__type-hint">
                {t === QUESTION_TYPES.MCQ ? 'Up to 10 questions' : 'Up to 5 questions'}
              </span>
            </button>
          ))}
        </div>

        <AnimatePresence>
          {type && (
            <motion.div
              className="lobby__count-section"
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              transition={{ duration: 0.3 }}
            >
              <p className="lobby__count-label">How many questions?</p>
              <div className="lobby__count-grid">
                {counts.map((n) => (
                  <button
                    key={n}
                    className={`lobby__count-btn${count === n ? ' --active' : ''}`}
                    onClick={() => setCount(n)}
                  >
                    {n}
                  </button>
                ))}
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        <AnimatePresence>
          {type && count && (
            <motion.button
              className="lobby__start-btn"
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              onClick={() => onStart(type, count)}
            >
              Start Session →
            </motion.button>
          )}
        </AnimatePresence>
      </motion.div>
    </div>
  );
};

// ─── Progress Bar ─────────────────────────────────────────────────────────────
const ProgressBar = ({ current, total, score }) => {
  const pct = total > 0 ? Math.round((score / total) * 100) : 0;
  return (
    <div className="progress-bar">
      <div className="progress-bar__meta">
        <span className="progress-bar__pos">
          Q{current} <span className="progress-bar__of">/ {total}</span>
        </span>
        <span className="progress-bar__score">{score} correct</span>
      </div>
      <div className="progress-bar__track">
        <motion.div
          className="progress-bar__fill"
          initial={{ width: 0 }}
          animate={{ width: `${pct}%` }}
          transition={{ duration: 0.4, ease: 'easeOut' }}
        />
      </div>
    </div>
  );
};

// ─── Question Navigator ───────────────────────────────────────────────────────
const QuestionNav = ({ questions, currentIndex, onJump }) => (
  <div className="q-nav">
    {questions.map((q, i) => {
      let cls = 'q-nav__dot';
      if (i === currentIndex) cls += ' --current';
      else if (q.status === 'correct') cls += ' --correct';
      else if (q.status === 'incorrect') cls += ' --incorrect';
      else if (q.status === 'skipped') cls += ' --skipped';
      return (
        <button key={i} className={cls} onClick={() => onJump(i)} title={`Question ${i + 1}`}>
          {i + 1}
        </button>
      );
    })}
  </div>
);

// ─── MCQ Question Card ────────────────────────────────────────────────────────
const MCQCard = ({ question, onAnswer, isEvaluating }) => {
  const [selected, setSelected] = useState(question.userAnswer ?? null);
  const evaluated = question.status && question.status !== 'unanswered';

  const handleSelect = async (opt) => {
    if (evaluated || isEvaluating) return;
    setSelected(opt);
    await onAnswer(opt);
  };

  const getOptionClass = (opt) => {
    let cls = 'mcq__option';
    if (!evaluated) {
      if (selected === opt) cls += ' --selected';
      return cls;
    }
    if (opt === question.correctAnswer) cls += ' --correct';
    else if (opt === selected && opt !== question.correctAnswer) cls += ' --incorrect';
    return cls;
  };

  return (
    <div className="mcq">
      <div className="mcq__question">
        <span className="mcq__q-label">Question</span>
        <p className="mcq__q-text">{question.question_text}</p>
      </div>
      <div className="mcq__options">
        {question.options.map((opt, i) => (
          <motion.button
            key={i}
            className={getOptionClass(opt)}
            onClick={() => handleSelect(opt)}
            whileHover={!evaluated ? { x: 4 } : {}}
            transition={{ duration: 0.15 }}
          >
            <span className="mcq__opt-letter">
              {String.fromCharCode(65 + i)}
            </span>
            <span className="mcq__opt-text">{opt}</span>
            {evaluated && opt === question.correctAnswer && (
              <span className="mcq__opt-badge --correct">✓ Correct</span>
            )}
            {evaluated && opt === selected && opt !== question.correctAnswer && (
              <span className="mcq__opt-badge --incorrect">✗ Wrong</span>
            )}
          </motion.button>
        ))}
      </div>
      {evaluated && question.feedback && (
        <motion.div
          className="mcq__feedback"
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
        >
          <span className="mcq__feedback-icon">
            {question.status === 'correct' ? '💡' : '📖'}
          </span>
          <p>{question.feedback}</p>
        </motion.div>
      )}
    </div>
  );
};

// ─── Open-Ended Question Card ─────────────────────────────────────────────────
const OpenEndedCard = ({ question, onSubmit, isStreaming, streamedFeedback, streamComplete }) => {
  const [text, setText] = useState(question.userAnswer ?? '');
  const [imageFile, setImageFile] = useState(null);
  const [imagePreview, setImagePreview] = useState(null);
  const fileRef = useRef();
  const evaluated = question.status && question.status !== 'unanswered';

  const handleImage = (e) => {
    const file = e.target.files[0];
    if (!file) return;
    setImageFile(file);
    setImagePreview(URL.createObjectURL(file));
  };

  const handleSubmit = () => {
    if (!text.trim() && !imageFile) return;
    onSubmit(text, imageFile);
  };

  return (
    <div className="oe">
      <div className="oe__question">
        <span className="oe__q-label">Question</span>
        <p className="oe__q-text">{question.question_text}</p>
      </div>

      {!evaluated && (
        <div className="oe__answer-area">
          <textarea
            className="oe__textarea"
            placeholder="Type your answer here… LaTeX supported: $x^2 + 1$"
            value={text}
            onChange={(e) => setText(e.target.value)}
            rows={6}
            disabled={isStreaming}
          />
          <div className="oe__toolbar">
            <button
              className="oe__img-btn"
              onClick={() => fileRef.current.click()}
              disabled={isStreaming}
            >
              📎 Attach Image
            </button>
            <input
              ref={fileRef}
              type="file"
              accept="image/*"
              style={{ display: 'none' }}
              onChange={handleImage}
            />
            {imagePreview && (
              <div className="oe__preview-wrap">
                <img src={imagePreview} className="oe__preview" alt="solution" />
                <button
                  className="oe__preview-remove"
                  onClick={() => { setImageFile(null); setImagePreview(null); }}
                >
                  ✕
                </button>
              </div>
            )}
            <button
              className="oe__submit-btn"
              onClick={handleSubmit}
              disabled={(!text.trim() && !imageFile) || isStreaming}
            >
              {isStreaming ? 'Evaluating…' : 'Submit Answer'}
            </button>
          </div>
        </div>
      )}

      {/* Streamed feedback — Claude chat style */}
      {(isStreaming || (evaluated && question.feedback)) && (
        <div className="oe__feedback-wrap">
          <div className="oe__feedback-header">
            <span className="oe__feedback-avatar">✦</span>
            <span className="oe__feedback-title">Feynman Tutor</span>
            {isStreaming && <span className="oe__feedback-typing" />}
          </div>

          {(question.status === 'correct' || question.status === 'incorrect') && streamComplete && (
            <div className={`oe__result-badge ${question.status === 'correct' ? '--correct' : '--incorrect'}`}>
              {question.status === 'correct' ? '✓ Correct' : '✗ Incorrect'}
              {question.score !== undefined && (
                <span className="oe__result-score"> · {Math.round(question.score)}/100</span>
              )}
            </div>
          )}

          <div className="oe__feedback-bubble">
            <p className="oe__feedback-text">
              {streamedFeedback || question.feedback}
              {isStreaming && <span className="oe__cursor" />}
            </p>
          </div>

          {evaluated && question.userAnswer && (
            <div className="oe__your-answer">
              <span className="oe__your-answer-label">Your answer</span>
              <p>{question.userAnswer}</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

// ─── Summary Screen ───────────────────────────────────────────────────────────
const Summary = ({ questions, type, onRetry }) => {
  const answered = questions.filter((q) => q.status !== 'unanswered');
  const correct = questions.filter((q) => q.status === 'correct');
  const skipped = questions.filter((q) => q.status === 'unanswered' || q.status === 'skipped');
  const pct = answered.length > 0 ? Math.round((correct.length / questions.length) * 100) : 0;

  const grade =
    pct >= 80 ? { label: 'Excellent', emoji: '🏆', cls: '--gold' }
    : pct >= 60 ? { label: 'Good Work', emoji: '💪', cls: '--silver' }
    : pct >= 40 ? { label: 'Keep Going', emoji: '📚', cls: '--bronze' }
    : { label: 'Need More Practice', emoji: '🔁', cls: '--red' };

  return (
    <motion.div
      className="summary"
      initial={{ opacity: 0, y: 24 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
    >
      <div className="summary__hero">
        <div className={`summary__medal ${grade.cls}`}>{grade.emoji}</div>
        <h2 className="summary__grade-label">{grade.label}</h2>
        <div className="summary__pct">{pct}%</div>
        <p className="summary__tally">
          {correct.length} correct · {answered.length - correct.length} incorrect · {skipped.length} skipped
        </p>
      </div>

      <div className="summary__list">
        {questions.map((q, i) => (
          <motion.div
            key={i}
            className={`summary__item summary__item--${q.status ?? 'unanswered'}`}
            initial={{ opacity: 0, x: -12 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: i * 0.04 }}
          >
            <span className="summary__item-num">Q{i + 1}</span>
            <span className="summary__item-text">{q.question_text}</span>
            <div className="summary__item-right">
              {q.status === 'correct' && <span className="summary__badge --correct">✓</span>}
              {q.status === 'incorrect' && <span className="summary__badge --incorrect">✗</span>}
              {(q.status === 'unanswered' || q.status === 'skipped') && (
                <span className="summary__badge --skipped">—</span>
              )}
              {type === QUESTION_TYPES.OPEN_ENDED && q.score !== undefined && q.status !== 'unanswered' && (
                <span className="summary__raw-score">{Math.round(q.score)}/100</span>
              )}
            </div>
          </motion.div>
        ))}
      </div>

      <button className="summary__retry-btn" onClick={onRetry}>
        Have Another Go →
      </button>
    </motion.div>
  );
};

// ─── Main Gym Component ───────────────────────────────────────────────────────
const Gym = () => {
  const { analysisId } = useParams();
  const navigate = useNavigate();

  const [phase, setPhase] = useState(PHASES.LOBBY);
  const [sessionType, setSessionType] = useState(null);
  const [gymSeshId, setGymSeshId] = useState(null);
  const [questions, setQuestions] = useState([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [score, setScore] = useState(0);
  const [isEvaluating, setIsEvaluating] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamedFeedback, setStreamedFeedback] = useState('');
  const [streamComplete, setStreamComplete] = useState(false);
  const [error, setError] = useState(null);

  const currentQ = questions[currentIndex] ?? null;

  // ── Start session ──
  const handleStart = async (type, count) => {
    setSessionType(type);
    setPhase(PHASES.LOADING);
    setError(null);

    try {
      if (type === QUESTION_TYPES.MCQ) {
        const data = await apiService.generateGymQuestions(analysisId, type, count);
        const seshId = data.gym_sesh_id;
        setGymSeshId(seshId);
        navigate(`/gym/${analysisId}/${seshId}`, { replace: true });
        setQuestions(
          data.questions.map((q) => ({
            ...q,
            status: 'unanswered',
            userAnswer: null,
            feedback: null,
            correctAnswer: null,
            score: null,
          }))
        );
        setPhase(PHASES.SESSION);
      } else {
        // Open-Ended: SSE stream
        const accumulated = [];
        let seshId = null;

        await apiService.generateGymQuestions(analysisId, type, count, (event) => {
          if (event.type === 'questions_saved') {
            seshId = event.gym_sesh_id;
          }
          if (event.type === 'array' && event.field === 'questions') {
            event.content.forEach((q, i) => {
              accumulated[i] = q;
            });
          }
          if (event.type === 'complete' && event.content?.questions) {
            event.content.questions.forEach((q, i) => {
              accumulated[i] = q;
            });
          }
        });

        if (!seshId || accumulated.length === 0) {
          throw new Error('Failed to receive questions from server.');
        }

        setGymSeshId(seshId);
        navigate(`/gym/${analysisId}/${seshId}`, { replace: true });
        setQuestions(
          accumulated.map((q) => ({
            ...q,
            status: 'unanswered',
            userAnswer: null,
            feedback: null,
            score: null,
          }))
        );
        setPhase(PHASES.SESSION);
      }
    } catch (err) {
      console.error('Failed to generate questions:', err);
      setError(err.message || 'Something went wrong. Please try again.');
      setPhase(PHASES.LOBBY);
    }
  };

  // ── MCQ answer ──
  const handleMCQAnswer = async (selectedOption) => {
    if (!gymSeshId || !currentQ) return;
    setIsEvaluating(true);
    try {
      const result = await apiService.evaluateGymAnswer(
        gymSeshId,
        currentQ.id,
        selectedOption,
        QUESTION_TYPES.MCQ
      );

      const isCorrect = result.is_correct;
      setQuestions((prev) =>
        prev.map((q, i) =>
          i === currentIndex
            ? {
                ...q,
                status: isCorrect ? 'correct' : 'incorrect',
                userAnswer: selectedOption,
                correctAnswer: isCorrect ? selectedOption : result.correct_answer ?? q.correctAnswer,
                feedback: result.feedback,
                score: result.score,
              }
            : q
        )
      );
      if (isCorrect) setScore((s) => s + 1);
    } catch (err) {
      console.error('MCQ evaluation failed:', err);
    } finally {
      setIsEvaluating(false);
    }
  };

  // ── Open-Ended answer ──
  const handleOpenEndedSubmit = async (text) => {
    if (!gymSeshId || !currentQ) return;
    setIsStreaming(true);
    setStreamedFeedback('');
    setStreamComplete(false);

    let finalIsCorrect = false;
    let finalScore = 0;
    let accFeedback = '';

    try {
      await apiService.evaluateGymAnswer(
        gymSeshId,
        currentQ.id,
        text,
        QUESTION_TYPES.OPEN_ENDED,
        (event) => {
          if (event.type === 'partial' && event.field === 'feedback') {
            accFeedback += event.content;
            setStreamedFeedback((f) => f + event.content);
          }
          if (event.type === 'boolean' && event.field === 'is_correct') {
            finalIsCorrect = event.content;
          }
          if (event.type === 'evaluated') {
            finalIsCorrect = event.is_correct;
            finalScore = event.score ?? 0;
          }
          if (event.type === 'complete' && event.content) {
            if (event.content.is_correct !== undefined) finalIsCorrect = event.content.is_correct;
            if (event.content.score !== undefined) finalScore = event.content.score;
            if (event.content.feedback) {
              accFeedback = event.content.feedback;
              setStreamedFeedback(event.content.feedback);
            }
          }
        }
      );
    } catch (err) {
      console.error('Open-ended evaluation failed:', err);
    } finally {
      setQuestions((prev) =>
        prev.map((q, i) =>
          i === currentIndex
            ? {
                ...q,
                status: finalIsCorrect || finalScore >= 50 ? 'correct' : 'incorrect',
                userAnswer: text,
                feedback: accFeedback,
                score: finalScore,
              }
            : q
        )
      );
      if (finalIsCorrect || finalScore >= 50) setScore((s) => s + 1);
      setIsStreaming(false);
      setStreamComplete(true);
    }
  };

  // ── Navigation ──
  const handleNext = () => {
    if (isStreaming) return;
    if (currentIndex < questions.length - 1) {
      // Mark current as skipped if unanswered
      if (currentQ?.status === 'unanswered') {
        setQuestions((prev) =>
          prev.map((q, i) => (i === currentIndex ? { ...q, status: 'skipped' } : q))
        );
      }
      setCurrentIndex((i) => i + 1);
      setStreamedFeedback('');
      setStreamComplete(false);
    } else {
      // Last question — go to summary
      if (currentQ?.status === 'unanswered') {
        setQuestions((prev) =>
          prev.map((q, i) => (i === currentIndex ? { ...q, status: 'skipped' } : q))
        );
      }
      setPhase(PHASES.SUMMARY);
    }
  };

  const handleJump = (idx) => {
    if (isStreaming) return;
    if (currentQ?.status === 'unanswered') {
      setQuestions((prev) =>
        prev.map((q, i) => (i === currentIndex ? { ...q, status: 'skipped' } : q))
      );
    }
    setCurrentIndex(idx);
    setStreamedFeedback('');
    setStreamComplete(false);
  };

  const handleRetry = () => {
    setPhase(PHASES.LOBBY);
    setQuestions([]);
    setCurrentIndex(0);
    setScore(0);
    setGymSeshId(null);
    setStreamedFeedback('');
    setStreamComplete(false);
    setSessionType(null);
  };

  const isLastQuestion = currentIndex === questions.length - 1;

  // ── Render ──
  return (
    <>
      <div className="gym-root">
        <AnimatePresence mode="wait">
          {phase === PHASES.LOBBY && (
            <motion.div key="lobby" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
              {error && <div className="gym-error">{error}</div>}
              <Lobby onStart={handleStart} />
            </motion.div>
          )}

          {phase === PHASES.LOADING && (
            <motion.div key="loading" className="gym-loading-wrap" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
              <GymLoader type={sessionType} />
            </motion.div>
          )}

          {phase === PHASES.SESSION && currentQ && (
            <motion.div
              key="session"
              className="gym-session"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
            >
              <div className="gym-session__header">
                <span className="gym-session__brand">🏋️ Gym</span>
                <ProgressBar
                  current={currentIndex + 1}
                  total={questions.length}
                  score={score}
                />
              </div>

              <QuestionNav
                questions={questions}
                currentIndex={currentIndex}
                onJump={handleJump}
              />

              <AnimatePresence mode="wait">
                <motion.div
                  key={`q-${currentIndex}`}
                  className="gym-session__body"
                  initial={{ opacity: 0, x: 20 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: -20 }}
                  transition={{ duration: 0.25 }}
                >
                  {sessionType === QUESTION_TYPES.MCQ ? (
                    <MCQCard
                      question={currentQ}
                      onAnswer={handleMCQAnswer}
                      isEvaluating={isEvaluating}
                    />
                  ) : (
                    <OpenEndedCard
                      key={currentIndex}
                      question={currentQ}
                      onSubmit={handleOpenEndedSubmit}
                      isStreaming={isStreaming}
                      streamedFeedback={streamedFeedback}
                      streamComplete={streamComplete}
                    />
                  )}
                </motion.div>
              </AnimatePresence>

              <div className="gym-session__footer">
                <button
                  className="gym-session__next-btn"
                  onClick={handleNext}
                  disabled={isStreaming}
                >
                  {isLastQuestion ? 'Finish Session →' : 'Next →'}
                </button>
              </div>
            </motion.div>
          )}

          {phase === PHASES.SUMMARY && (
            <motion.div key="summary" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
              <Summary
                questions={questions}
                type={sessionType}
                onRetry={handleRetry}
              />
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </>
  );
};

export default Gym;