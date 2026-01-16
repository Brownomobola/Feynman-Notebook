import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { History as HistoryIcon, Calendar, Tag, ArrowRight, Loader2, Dumbbell } from 'lucide-react';
import Card from '../components/Card';
import Button from '../components/Button';
import apiService from '../services/api';

const History = () => {
  const [analyses, setAnalyses] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    loadAnalyses();
  }, []);

  const loadAnalyses = async () => {
    try {
      setLoading(true);
      const data = await apiService.getAnalyses();
      setAnalyses(data.analyses || []);
    } catch (err) {
      setError('Failed to load analysis history');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (dateString) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
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
            Loading your analysis history...
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen py-12">
      <div className="container mx-auto px-6">
        <div className="max-w-5xl mx-auto">
          {/* Header */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="mb-12"
          >
            <div className="flex items-center gap-4 mb-4">
              <div 
                className="p-3 rounded-xl"
                style={{ backgroundColor: 'var(--color-highlight)' }}
              >
                <HistoryIcon size={32} style={{ color: 'var(--color-accent)' }} />
              </div>
              <div>
                <h1 
                  className="text-4xl md:text-5xl font-bold"
                  style={{ 
                    fontFamily: 'var(--font-serif)',
                    color: 'var(--color-ink)'
                  }}
                >
                  Analysis History
                </h1>
                <p 
                  className="text-lg"
                  style={{ color: 'var(--color-ink-light)' }}
                >
                  Review your past work and insights
                </p>
              </div>
            </div>
          </motion.div>

          {/* Error State */}
          {error && (
            <Card>
              <div className="text-center py-8">
                <p style={{ color: 'var(--color-incorrect)' }}>
                  {error}
                </p>
                <Button
                  variant="secondary"
                  onClick={loadAnalyses}
                  className="mt-4"
                >
                  Try Again
                </Button>
              </div>
            </Card>
          )}

          {/* Empty State */}
          {!error && analyses.length === 0 && (
            <Card>
              <div className="text-center py-12">
                <div 
                  className="inline-flex items-center justify-center p-4 rounded-2xl mb-4"
                  style={{ backgroundColor: 'var(--color-muted)' }}
                >
                  <HistoryIcon size={48} style={{ color: 'var(--color-ink-light)' }} />
                </div>
                <h3 
                  className="text-2xl font-bold mb-2"
                  style={{ 
                    fontFamily: 'var(--font-serif)',
                    color: 'var(--color-ink)'
                  }}
                >
                  No Analyses Yet
                </h3>
                <p 
                  className="mb-6"
                  style={{ color: 'var(--color-ink-light)' }}
                >
                  Start your first analysis to begin tracking your learning journey
                </p>
                <Link to="/analysis">
                  <Button 
                    variant="primary"
                    icon={<ArrowRight size={20} />}
                  >
                    Create Analysis
                  </Button>
                </Link>
              </div>
            </Card>
          )}

          {/* Analysis List */}
          {analyses.length > 0 && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="space-y-6"
            >
              {analyses.map((analysis, index) => (
                <motion.div
                  key={analysis.id}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: index * 0.1 }}
                >
                  <Card hover={true}>
                    <div className="flex flex-col md:flex-row md:items-start md:justify-between gap-6">
                      {/* Content */}
                      <div className="flex-1">
                        <div className="flex items-start gap-3 mb-3">
                          <div 
                            className="mt-1 p-2 rounded-lg flex-shrink-0"
                            style={{ backgroundColor: 'var(--color-highlight)' }}
                          >
                            <HistoryIcon size={20} style={{ color: 'var(--color-accent)' }} />
                          </div>
                          <div className="flex-1">
                            <h3 
                              className="text-2xl font-semibold mb-2"
                              style={{ 
                                fontFamily: 'var(--font-serif)',
                                color: 'var(--color-ink)'
                              }}
                            >
                              {analysis.title || 'Untitled Analysis'}
                            </h3>
                            
                            <div className="flex items-center gap-4 text-sm mb-3">
                              <div 
                                className="flex items-center gap-1"
                                style={{ color: 'var(--color-ink-light)' }}
                              >
                                <Calendar size={16} />
                                {formatDate(analysis.created_at)}
                              </div>
                            </div>

                            {analysis.tags && analysis.tags.length > 0 && (
                              <div className="flex flex-wrap gap-2 mb-4">
                                {analysis.tags.map((tag, i) => (
                                  <span
                                    key={i}
                                    className="inline-flex items-center gap-1 px-2 py-1 rounded text-xs font-medium"
                                    style={{ 
                                      backgroundColor: 'var(--color-highlight)',
                                      color: 'var(--color-accent)'
                                    }}
                                  >
                                    <Tag size={12} />
                                    {tag}
                                  </span>
                                ))}
                              </div>
                            )}

                            {analysis.diagnosis && (
                              <p 
                                className="text-sm line-clamp-2"
                                style={{ color: 'var(--color-ink-light)' }}
                              >
                                {analysis.diagnosis.substring(0, 150)}
                                {analysis.diagnosis.length > 150 ? '...' : ''}
                              </p>
                            )}
                          </div>
                        </div>
                      </div>

                      {/* Actions */}
                      <div className="flex md:flex-col gap-2">
                        <Link 
                          to={`/analysis/${analysis.id}`}
                          className="flex-1 md:flex-initial"
                        >
                          <Button
                            variant="secondary"
                            size="sm"
                            icon={<ArrowRight size={16} />}
                          >
                            View
                          </Button>
                        </Link>
                        <Link 
                          to={`/gym/${analysis.id}`}
                          className="flex-1 md:flex-initial"
                        >
                          <Button
                            variant="ghost"
                            size="sm"
                            icon={<Dumbbell size={16} />}
                          >
                            Practice
                          </Button>
                        </Link>
                      </div>
                    </div>
                  </Card>
                </motion.div>
              ))}
            </motion.div>
          )}

          {/* New Analysis CTA */}
          {analyses.length > 0 && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.5 }}
              className="mt-12 text-center"
            >
              <Link to="/analysis">
                <Button 
                  variant="primary"
                  size="lg"
                  icon={<ArrowRight size={20} />}
                >
                  Create New Analysis
                </Button>
              </Link>
            </motion.div>
          )}
        </div>
      </div>
    </div>
  );
};

export default History;
