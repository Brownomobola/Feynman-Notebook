import { BlockMath, InlineMath } from 'react-katex';
import 'katex/dist/katex.min.css';

const MathDisplay = ({ content, inline = false, className = '' }) => {
  if (!content) return null;

  // Check if content contains LaTeX delimiters
  const hasLatex = /\$\$[\s\S]+?\$\$|\$[^\$]+?\$/.test(content);

  if (!hasLatex) {
    return <div className={className}>{content}</div>;
  }

  // Split content by LaTeX delimiters
  const parts = [];
  let lastIndex = 0;
  
  // Match both display math ($$...$$) and inline math ($...$)
  const regex = /(\$\$[\s\S]+?\$\$|\$[^\$]+?\$)/g;
  let match;

  while ((match = regex.exec(content)) !== null) {
    // Add text before the math
    if (match.index > lastIndex) {
      parts.push({
        type: 'text',
        content: content.slice(lastIndex, match.index)
      });
    }

    // Add the math
    const mathContent = match[1];
    if (mathContent.startsWith('$$')) {
      parts.push({
        type: 'display',
        content: mathContent.slice(2, -2).trim()
      });
    } else {
      parts.push({
        type: 'inline',
        content: mathContent.slice(1, -1).trim()
      });
    }

    lastIndex = match.index + match[1].length;
  }

  // Add remaining text
  if (lastIndex < content.length) {
    parts.push({
      type: 'text',
      content: content.slice(lastIndex)
    });
  }

  return (
    <div className={className}>
      {parts.map((part, index) => {
        if (part.type === 'text') {
          return <span key={index}>{part.content}</span>;
        } else if (part.type === 'display') {
          return (
            <div key={index} className="math-display my-4">
              <BlockMath math={part.content} />
            </div>
          );
        } else {
          return (
            <span key={index} className="inline-block mx-1">
              <InlineMath math={part.content} />
            </span>
          );
        }
      })}
    </div>
  );
};

export default MathDisplay;
