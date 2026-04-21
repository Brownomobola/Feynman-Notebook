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
      <style>{GYM_STYLES}</style>
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

// ─── Styles ───────────────────────────────────────────────────────────────────
const GYM_STYLES = `
  @import url('https://fonts.googleapis.com/css2?family=DM+Mono:ital,wght@0,300;0,400;0,500;1,400&family=Syne:wght@400;600;700;800&display=swap');

  :root {
    --gym-bg: #0d0d0f;
    --gym-surface: #141418;
    --gym-surface-2: #1c1c22;
    --gym-surface-3: #242430;
    --gym-border: rgba(255,255,255,0.07);
    --gym-border-hover: rgba(255,255,255,0.14);
    --gym-ink: #f0f0f5;
    --gym-ink-dim: rgba(240,240,245,0.5);
    --gym-ink-faint: rgba(240,240,245,0.25);
    --gym-accent: #a78bfa;
    --gym-accent-glow: rgba(167,139,250,0.18);
    --gym-correct: #34d399;
    --gym-correct-bg: rgba(52,211,153,0.1);
    --gym-incorrect: #f87171;
    --gym-incorrect-bg: rgba(248,113,113,0.1);
    --gym-skipped: #94a3b8;
    --gym-skipped-bg: rgba(148,163,184,0.1);
    --gym-gold: #fbbf24;
    --gym-font-display: 'Syne', sans-serif;
    --gym-font-mono: 'DM Mono', monospace;
    --gym-radius: 14px;
    --gym-radius-sm: 8px;
  }

  .gym-root {
    min-height: 100vh;
    background: var(--gym-bg);
    font-family: var(--gym-font-display);
    color: var(--gym-ink);
    padding: 0;
  }

  /* ── Loader ── */
  .gym-loading-wrap {
    min-height: 100vh;
    display: flex;
    align-items: center;
    justify-content: center;
  }
  .gym-loader {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 32px;
  }
  .gym-loader__ring {
    position: relative;
    width: 80px;
    height: 80px;
  }
  .gym-loader__bar {
    position: absolute;
    top: 0; left: 50%;
    width: 3px;
    height: 22px;
    border-radius: 99px;
    background: var(--gym-accent);
    transform-origin: center 40px;
    transform: translateX(-50%) rotate(calc(var(--i) * 30deg));
    opacity: 0.15;
    animation: gym-spin-bar 1s linear infinite;
    animation-delay: calc(var(--i) * (1s / 12));
  }
  @keyframes gym-spin-bar {
    0%   { opacity: 0.15; }
    50%  { opacity: 1; }
    100% { opacity: 0.15; }
  }
  .gym-loader__label {
    font-family: var(--gym-font-mono);
    font-size: 13px;
    color: var(--gym-ink-dim);
    letter-spacing: 0.05em;
  }

  /* ── Error ── */
  .gym-error {
    position: fixed;
    top: 20px; left: 50%;
    transform: translateX(-50%);
    background: var(--gym-incorrect-bg);
    border: 1px solid var(--gym-incorrect);
    color: var(--gym-incorrect);
    padding: 10px 20px;
    border-radius: var(--gym-radius-sm);
    font-size: 14px;
    z-index: 100;
  }

  /* ── Lobby ── */
  .lobby {
    min-height: 100vh;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 40px 20px;
  }
  .lobby__card {
    background: var(--gym-surface);
    border: 1px solid var(--gym-border);
    border-radius: 24px;
    padding: 48px 40px;
    width: 100%;
    max-width: 520px;
    text-align: center;
  }
  .lobby__icon {
    font-size: 48px;
    margin-bottom: 16px;
  }
  .lobby__title {
    font-size: 36px;
    font-weight: 800;
    color: var(--gym-ink);
    margin: 0 0 8px;
    letter-spacing: -0.03em;
  }
  .lobby__sub {
    color: var(--gym-ink-dim);
    font-size: 15px;
    margin: 0 0 36px;
    font-family: var(--gym-font-mono);
  }
  .lobby__type-row {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 12px;
    margin-bottom: 28px;
  }
  .lobby__type-btn {
    background: var(--gym-surface-2);
    border: 1.5px solid var(--gym-border);
    border-radius: var(--gym-radius);
    padding: 20px 16px;
    cursor: pointer;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 6px;
    transition: border-color 0.2s, background 0.2s, box-shadow 0.2s;
  }
  .lobby__type-btn:hover {
    border-color: var(--gym-border-hover);
    background: var(--gym-surface-3);
  }
  .lobby__type-btn.--active {
    border-color: var(--gym-accent);
    background: var(--gym-accent-glow);
    box-shadow: 0 0 0 3px var(--gym-accent-glow);
  }
  .lobby__type-icon { font-size: 24px; }
  .lobby__type-name {
    font-size: 14px;
    font-weight: 700;
    color: var(--gym-ink);
  }
  .lobby__type-hint {
    font-size: 11px;
    color: var(--gym-ink-faint);
    font-family: var(--gym-font-mono);
  }
  .lobby__count-section {
    overflow: hidden;
    margin-bottom: 28px;
  }
  .lobby__count-label {
    font-size: 13px;
    color: var(--gym-ink-dim);
    font-family: var(--gym-font-mono);
    margin: 0 0 14px;
    letter-spacing: 0.04em;
  }
  .lobby__count-grid {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    justify-content: center;
  }
  .lobby__count-btn {
    width: 44px; height: 44px;
    border-radius: var(--gym-radius-sm);
    border: 1.5px solid var(--gym-border);
    background: var(--gym-surface-2);
    color: var(--gym-ink-dim);
    font-size: 14px;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.15s;
    font-family: var(--gym-font-mono);
  }
  .lobby__count-btn:hover {
    border-color: var(--gym-border-hover);
    color: var(--gym-ink);
  }
  .lobby__count-btn.--active {
    border-color: var(--gym-accent);
    background: var(--gym-accent-glow);
    color: var(--gym-accent);
  }
  .lobby__start-btn {
    width: 100%;
    padding: 16px;
    border-radius: var(--gym-radius);
    border: none;
    background: var(--gym-accent);
    color: #0d0d0f;
    font-size: 16px;
    font-weight: 800;
    font-family: var(--gym-font-display);
    cursor: pointer;
    letter-spacing: -0.01em;
    transition: opacity 0.2s, transform 0.1s;
  }
  .lobby__start-btn:hover { opacity: 0.9; transform: translateY(-1px); }
  .lobby__start-btn:active { transform: translateY(0); }

  /* ── Progress Bar ── */
  .progress-bar {
    flex: 1;
    max-width: 480px;
  }
  .progress-bar__meta {
    display: flex;
    justify-content: space-between;
    margin-bottom: 6px;
  }
  .progress-bar__pos {
    font-size: 13px;
    font-weight: 700;
    color: var(--gym-ink);
    font-family: var(--gym-font-mono);
  }
  .progress-bar__of { color: var(--gym-ink-faint); }
  .progress-bar__score {
    font-size: 12px;
    color: var(--gym-ink-dim);
    font-family: var(--gym-font-mono);
  }
  .progress-bar__track {
    height: 4px;
    background: var(--gym-surface-3);
    border-radius: 99px;
    overflow: hidden;
  }
  .progress-bar__fill {
    height: 100%;
    background: var(--gym-correct);
    border-radius: 99px;
  }

  /* ── Question Navigator ── */
  .q-nav {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    padding: 16px 24px;
    border-bottom: 1px solid var(--gym-border);
  }
  .q-nav__dot {
    width: 32px; height: 32px;
    border-radius: var(--gym-radius-sm);
    border: 1.5px solid var(--gym-border);
    background: var(--gym-surface-2);
    color: var(--gym-ink-faint);
    font-size: 12px;
    font-weight: 600;
    font-family: var(--gym-font-mono);
    cursor: pointer;
    transition: all 0.15s;
  }
  .q-nav__dot:hover { border-color: var(--gym-border-hover); color: var(--gym-ink); }
  .q-nav__dot.--current {
    border-color: var(--gym-accent);
    color: var(--gym-accent);
    background: var(--gym-accent-glow);
  }
  .q-nav__dot.--correct {
    border-color: var(--gym-correct);
    color: var(--gym-correct);
    background: var(--gym-correct-bg);
  }
  .q-nav__dot.--incorrect {
    border-color: var(--gym-incorrect);
    color: var(--gym-incorrect);
    background: var(--gym-incorrect-bg);
  }
  .q-nav__dot.--skipped {
    border-color: var(--gym-skipped);
    color: var(--gym-skipped);
    background: var(--gym-skipped-bg);
  }

  /* ── Session Shell ── */
  .gym-session {
    min-height: 100vh;
    display: flex;
    flex-direction: column;
    background: var(--gym-bg);
  }
  .gym-session__header {
    display: flex;
    align-items: center;
    gap: 24px;
    padding: 18px 24px;
    border-bottom: 1px solid var(--gym-border);
    background: var(--gym-surface);
    position: sticky;
    top: 0;
    z-index: 10;
  }
  .gym-session__brand {
    font-size: 15px;
    font-weight: 800;
    white-space: nowrap;
    letter-spacing: -0.02em;
  }
  .gym-session__body {
    flex: 1;
    padding: 32px 24px;
    max-width: 760px;
    width: 100%;
    margin: 0 auto;
  }
  .gym-session__footer {
    padding: 16px 24px;
    border-top: 1px solid var(--gym-border);
    display: flex;
    justify-content: flex-end;
    background: var(--gym-surface);
    position: sticky;
    bottom: 0;
  }
  .gym-session__next-btn {
    padding: 12px 28px;
    border-radius: var(--gym-radius);
    border: none;
    background: var(--gym-accent);
    color: #0d0d0f;
    font-size: 14px;
    font-weight: 800;
    font-family: var(--gym-font-display);
    cursor: pointer;
    transition: opacity 0.2s, transform 0.1s;
    letter-spacing: -0.01em;
  }
  .gym-session__next-btn:hover:not(:disabled) { opacity: 0.9; transform: translateY(-1px); }
  .gym-session__next-btn:disabled { opacity: 0.35; cursor: not-allowed; }

  /* ── MCQ ── */
  .mcq { display: flex; flex-direction: column; gap: 24px; }
  .mcq__question {
    background: var(--gym-surface);
    border: 1px solid var(--gym-border);
    border-radius: var(--gym-radius);
    padding: 24px;
  }
  .mcq__q-label {
    display: block;
    font-size: 10px;
    font-family: var(--gym-font-mono);
    color: var(--gym-accent);
    letter-spacing: 0.12em;
    text-transform: uppercase;
    margin-bottom: 10px;
  }
  .mcq__q-text {
    font-size: 17px;
    line-height: 1.65;
    color: var(--gym-ink);
    margin: 0;
    font-weight: 400;
  }
  .mcq__options { display: flex; flex-direction: column; gap: 10px; }
  .mcq__option {
    display: flex;
    align-items: center;
    gap: 14px;
    padding: 16px 18px;
    background: var(--gym-surface);
    border: 1.5px solid var(--gym-border);
    border-radius: var(--gym-radius);
    cursor: pointer;
    transition: border-color 0.15s, background 0.15s;
    text-align: left;
    width: 100%;
  }
  .mcq__option:hover { border-color: var(--gym-border-hover); background: var(--gym-surface-2); }
  .mcq__option.--selected { border-color: var(--gym-accent); background: var(--gym-accent-glow); }
  .mcq__option.--correct { border-color: var(--gym-correct); background: var(--gym-correct-bg); }
  .mcq__option.--incorrect { border-color: var(--gym-incorrect); background: var(--gym-incorrect-bg); }
  .mcq__opt-letter {
    width: 28px; height: 28px;
    border-radius: 6px;
    background: var(--gym-surface-3);
    display: flex; align-items: center; justify-content: center;
    font-size: 12px;
    font-weight: 700;
    font-family: var(--gym-font-mono);
    color: var(--gym-ink-dim);
    flex-shrink: 0;
  }
  .mcq__opt-text { flex: 1; font-size: 15px; color: var(--gym-ink); line-height: 1.5; }
  .mcq__opt-badge {
    font-size: 11px;
    font-family: var(--gym-font-mono);
    padding: 3px 8px;
    border-radius: 99px;
    font-weight: 600;
    flex-shrink: 0;
  }
  .mcq__opt-badge.--correct { background: var(--gym-correct-bg); color: var(--gym-correct); }
  .mcq__opt-badge.--incorrect { background: var(--gym-incorrect-bg); color: var(--gym-incorrect); }
  .mcq__feedback {
    display: flex;
    gap: 12px;
    padding: 16px 18px;
    background: var(--gym-surface-2);
    border: 1px solid var(--gym-border);
    border-radius: var(--gym-radius);
    border-left: 3px solid var(--gym-accent);
  }
  .mcq__feedback-icon { font-size: 18px; flex-shrink: 0; }
  .mcq__feedback p { margin: 0; font-size: 14px; color: var(--gym-ink-dim); line-height: 1.6; }

  /* ── Open-Ended ── */
  .oe { display: flex; flex-direction: column; gap: 20px; }
  .oe__question {
    background: var(--gym-surface);
    border: 1px solid var(--gym-border);
    border-radius: var(--gym-radius);
    padding: 24px;
  }
  .oe__q-label {
    display: block;
    font-size: 10px;
    font-family: var(--gym-font-mono);
    color: var(--gym-accent);
    letter-spacing: 0.12em;
    text-transform: uppercase;
    margin-bottom: 10px;
  }
  .oe__q-text { font-size: 17px; line-height: 1.65; color: var(--gym-ink); margin: 0; }
  .oe__answer-area {
    background: var(--gym-surface);
    border: 1px solid var(--gym-border);
    border-radius: var(--gym-radius);
    overflow: hidden;
  }
  .oe__textarea {
    width: 100%;
    background: transparent;
    border: none;
    outline: none;
    color: var(--gym-ink);
    font-size: 15px;
    font-family: var(--gym-font-mono);
    line-height: 1.7;
    padding: 20px;
    resize: none;
    box-sizing: border-box;
  }
  .oe__textarea::placeholder { color: var(--gym-ink-faint); }
  .oe__textarea:disabled { opacity: 0.5; }
  .oe__toolbar {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 10px 14px;
    border-top: 1px solid var(--gym-border);
    background: var(--gym-surface-2);
    flex-wrap: wrap;
  }
  .oe__img-btn {
    padding: 8px 14px;
    border-radius: var(--gym-radius-sm);
    border: 1px solid var(--gym-border);
    background: transparent;
    color: var(--gym-ink-dim);
    font-size: 13px;
    cursor: pointer;
    font-family: var(--gym-font-display);
    transition: all 0.15s;
  }
  .oe__img-btn:hover { border-color: var(--gym-border-hover); color: var(--gym-ink); }
  .oe__preview-wrap { position: relative; display: inline-block; }
  .oe__preview { height: 40px; width: auto; border-radius: 6px; border: 1px solid var(--gym-border); }
  .oe__preview-remove {
    position: absolute;
    top: -6px; right: -6px;
    width: 18px; height: 18px;
    border-radius: 50%;
    background: var(--gym-incorrect);
    border: none;
    color: white;
    font-size: 10px;
    cursor: pointer;
    display: flex; align-items: center; justify-content: center;
    line-height: 1;
  }
  .oe__submit-btn {
    margin-left: auto;
    padding: 9px 20px;
    border-radius: var(--gym-radius-sm);
    border: none;
    background: var(--gym-accent);
    color: #0d0d0f;
    font-size: 13px;
    font-weight: 700;
    font-family: var(--gym-font-display);
    cursor: pointer;
    transition: opacity 0.2s;
  }
  .oe__submit-btn:disabled { opacity: 0.35; cursor: not-allowed; }

  /* Feedback — Claude chat style */
  .oe__feedback-wrap {
    background: var(--gym-surface);
    border: 1px solid var(--gym-border);
    border-radius: var(--gym-radius);
    padding: 20px;
    display: flex;
    flex-direction: column;
    gap: 14px;
  }
  .oe__feedback-header {
    display: flex;
    align-items: center;
    gap: 10px;
  }
  .oe__feedback-avatar {
    width: 28px; height: 28px;
    border-radius: 50%;
    background: var(--gym-accent-glow);
    border: 1px solid var(--gym-accent);
    display: flex; align-items: center; justify-content: center;
    font-size: 13px;
    flex-shrink: 0;
    color: var(--gym-accent);
  }
  .oe__feedback-title {
    font-size: 13px;
    font-weight: 700;
    color: var(--gym-ink);
  }
  .oe__feedback-typing {
    width: 6px; height: 6px;
    border-radius: 50%;
    background: var(--gym-accent);
    animation: gym-blink 0.9s ease-in-out infinite;
  }
  @keyframes gym-blink {
    0%, 100% { opacity: 0.2; } 50% { opacity: 1; }
  }
  .oe__result-badge {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    font-size: 13px;
    font-weight: 700;
    font-family: var(--gym-font-mono);
    padding: 5px 12px;
    border-radius: 99px;
    width: fit-content;
  }
  .oe__result-badge.--correct { background: var(--gym-correct-bg); color: var(--gym-correct); }
  .oe__result-badge.--incorrect { background: var(--gym-incorrect-bg); color: var(--gym-incorrect); }
  .oe__result-score { opacity: 0.75; }
  .oe__feedback-bubble {
    background: var(--gym-surface-2);
    border-radius: var(--gym-radius-sm);
    padding: 16px;
  }
  .oe__feedback-text {
    margin: 0;
    font-size: 14px;
    line-height: 1.75;
    color: var(--gym-ink-dim);
    white-space: pre-wrap;
  }
  .oe__cursor {
    display: inline-block;
    width: 2px; height: 14px;
    background: var(--gym-accent);
    vertical-align: text-bottom;
    margin-left: 2px;
    animation: gym-blink 0.7s step-end infinite;
  }
  .oe__your-answer {
    border-top: 1px solid var(--gym-border);
    padding-top: 12px;
  }
  .oe__your-answer-label {
    display: block;
    font-size: 10px;
    font-family: var(--gym-font-mono);
    color: var(--gym-ink-faint);
    letter-spacing: 0.1em;
    text-transform: uppercase;
    margin-bottom: 6px;
  }
  .oe__your-answer p {
    margin: 0;
    font-size: 13px;
    color: var(--gym-ink-dim);
    font-family: var(--gym-font-mono);
    line-height: 1.6;
  }

  /* ── Summary ── */
  .summary {
    min-height: 100vh;
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: 60px 24px 80px;
    max-width: 680px;
    margin: 0 auto;
    width: 100%;
  }
  .summary__hero { text-align: center; margin-bottom: 48px; }
  .summary__medal {
    font-size: 64px;
    display: block;
    margin-bottom: 12px;
    filter: drop-shadow(0 0 24px rgba(251,191,36,0.35));
  }
  .summary__grade-label {
    font-size: 28px;
    font-weight: 800;
    color: var(--gym-ink);
    margin: 0 0 8px;
    letter-spacing: -0.03em;
  }
  .summary__pct {
    font-size: 72px;
    font-weight: 800;
    color: var(--gym-accent);
    letter-spacing: -0.04em;
    line-height: 1;
    margin-bottom: 10px;
  }
  .summary__tally {
    font-size: 14px;
    color: var(--gym-ink-dim);
    font-family: var(--gym-font-mono);
    margin: 0;
  }
  .summary__list {
    width: 100%;
    display: flex;
    flex-direction: column;
    gap: 8px;
    margin-bottom: 40px;
  }
  .summary__item {
    display: flex;
    align-items: flex-start;
    gap: 14px;
    padding: 14px 16px;
    background: var(--gym-surface);
    border: 1px solid var(--gym-border);
    border-radius: var(--gym-radius);
  }
  .summary__item--correct { border-left: 3px solid var(--gym-correct); }
  .summary__item--incorrect { border-left: 3px solid var(--gym-incorrect); }
  .summary__item--skipped,
  .summary__item--unanswered { border-left: 3px solid var(--gym-skipped); }
  .summary__item-num {
    font-size: 11px;
    font-family: var(--gym-font-mono);
    color: var(--gym-ink-faint);
    white-space: nowrap;
    padding-top: 2px;
    min-width: 24px;
  }
  .summary__item-text {
    flex: 1;
    font-size: 14px;
    color: var(--gym-ink-dim);
    line-height: 1.5;
  }
  .summary__item-right {
    display: flex;
    align-items: center;
    gap: 8px;
    flex-shrink: 0;
  }
  .summary__badge {
    font-size: 12px;
    font-weight: 700;
    font-family: var(--gym-font-mono);
    padding: 3px 10px;
    border-radius: 99px;
  }
  .summary__badge.--correct { background: var(--gym-correct-bg); color: var(--gym-correct); }
  .summary__badge.--incorrect { background: var(--gym-incorrect-bg); color: var(--gym-incorrect); }
  .summary__badge.--skipped { background: var(--gym-skipped-bg); color: var(--gym-skipped); }
  .summary__raw-score {
    font-size: 12px;
    font-family: var(--gym-font-mono);
    color: var(--gym-ink-faint);
  }
  .summary__retry-btn {
    padding: 16px 40px;
    border-radius: var(--gym-radius);
    border: 1.5px solid var(--gym-accent);
    background: transparent;
    color: var(--gym-accent);
    font-size: 16px;
    font-weight: 800;
    font-family: var(--gym-font-display);
    cursor: pointer;
    letter-spacing: -0.01em;
    transition: background 0.2s, color 0.2s;
  }
  .summary__retry-btn:hover {
    background: var(--gym-accent);
    color: #0d0d0f;
  }

  /* ── Responsive ── */
  @media (max-width: 540px) {
    .lobby__card { padding: 32px 20px; }
    .lobby__type-row { grid-template-columns: 1fr; }
    .gym-session__header { gap: 12px; padding: 14px 16px; }
    .gym-session__body { padding: 20px 16px; }
    .summary { padding: 40px 16px 60px; }
    .summary__pct { font-size: 56px; }
  }
`;

export default Gym;