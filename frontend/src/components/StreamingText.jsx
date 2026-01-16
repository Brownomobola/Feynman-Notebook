import { motion } from 'framer-motion';
import MathDisplay from './MathDisplay';

const StreamingText = ({ 
  content, 
  title,
  isComplete = false,
  className = '' 
}) => {
  if (!content && !title) return null;

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className={`mb-6 ${className}`}
    >
      {title && (
        <h3 
          className="text-xl font-semibold mb-3"
          style={{ 
            fontFamily: 'var(--font-serif)',
            color: 'var(--color-ink)'
          }}
        >
          {title}
        </h3>
      )}
      
      <div className="relative">
        <MathDisplay content={content} />
        
        {!isComplete && content && (
          <motion.span
            animate={{ opacity: [1, 0.3, 1] }}
            transition={{ repeat: Infinity, duration: 1.5 }}
            className="inline-block w-2 h-5 ml-1 bg-accent"
            style={{ backgroundColor: 'var(--color-accent)' }}
          />
        )}
      </div>
    </motion.div>
  );
};

export default StreamingText;
