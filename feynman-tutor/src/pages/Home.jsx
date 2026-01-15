import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { ArrowRight, Target, Lightbulb, TrendingUp, Brain } from 'lucide-react';
import Button from '../components/Button';
import Card from '../components/Card';

const Home = () => {
  const features = [
    {
      icon: Target,
      title: 'Precision Diagnosis',
      description: 'AI compares your work against golden solutions to identify exactly where your intuition diverges from correct reasoning.',
    },
    {
      icon: Lightbulb,
      title: 'Feynman Explanations',
      description: 'Get clear, conceptual explanations that build understanding from first principles rather than memorization.',
    },
    {
      icon: TrendingUp,
      title: 'Gym Practice',
      description: 'Reinforce learning with targeted practice problems that strengthen the weak points in your understanding.',
    },
  ];

  const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        staggerChildren: 0.1,
        delayChildren: 0.2
      }
    }
  };

  const itemVariants = {
    hidden: { opacity: 0, y: 20 },
    visible: { 
      opacity: 1, 
      y: 0,
      transition: { duration: 0.5, ease: [0.4, 0, 0.2, 1] }
    }
  };

  return (
    <div className="min-h-screen">
      {/* Hero Section */}
      <section 
        className="relative overflow-hidden"
        style={{ 
          background: 'linear-gradient(135deg, var(--color-paper) 0%, var(--color-highlight) 100%)'
        }}
      >
        <div className="container mx-auto px-6 py-20 relative z-10">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, ease: [0.4, 0, 0.2, 1] }}
            className="max-w-4xl mx-auto text-center"
          >
            <motion.div
              initial={{ scale: 0 }}
              animate={{ scale: 1 }}
              transition={{ delay: 0.2, type: "spring", stiffness: 200 }}
              className="inline-flex items-center justify-center p-4 rounded-2xl mb-6"
              style={{ backgroundColor: 'var(--color-accent)' }}
            >
              <Brain size={48} color="white" />
            </motion.div>

            <h1 
              className="text-5xl md:text-7xl font-bold mb-6"
              style={{ 
                fontFamily: 'var(--font-serif)',
                color: 'var(--color-ink)',
                lineHeight: 1.1
              }}
            >
              Debug Your{' '}
              <span style={{ color: 'var(--color-accent)' }}>Intuition</span>
            </h1>

            <p 
              className="text-xl md:text-2xl mb-8 leading-relaxed"
              style={{ color: 'var(--color-ink-light)' }}
            >
              Move beyond answer-getting. Compare your handwritten work against 
              AI-generated golden solutions to identify exactly where your 
              understanding breaks down.
            </p>

            <div className="flex flex-wrap gap-4 justify-center">
              <Link to="/analysis">
                <Button 
                  variant="primary" 
                  size="lg"
                  icon={<ArrowRight size={20} />}
                >
                  Start Analysis
                </Button>
              </Link>
              <Link to="/history">
                <Button variant="ghost" size="lg">
                  View History
                </Button>
              </Link>
            </div>
          </motion.div>
        </div>

        {/* Decorative Elements */}
        <div 
          className="absolute top-0 right-0 w-96 h-96 rounded-full blur-3xl opacity-20"
          style={{ backgroundColor: 'var(--color-accent)' }}
        />
        <div 
          className="absolute bottom-0 left-0 w-96 h-96 rounded-full blur-3xl opacity-10"
          style={{ backgroundColor: 'var(--color-accent)' }}
        />
      </section>

      {/* Features Section */}
      <section className="py-20">
        <div className="container mx-auto px-6">
          <motion.div
            variants={containerVariants}
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true, margin: "-100px" }}
          >
            <motion.h2 
              variants={itemVariants}
              className="text-4xl md:text-5xl font-bold text-center mb-4"
              style={{ 
                fontFamily: 'var(--font-serif)',
                color: 'var(--color-ink)'
              }}
            >
              How It Works
            </motion.h2>

            <motion.p 
              variants={itemVariants}
              className="text-center text-xl mb-12 max-w-2xl mx-auto"
              style={{ color: 'var(--color-ink-light)' }}
            >
              Three powerful tools to transform how you learn engineering concepts
            </motion.p>

            <div className="grid md:grid-cols-3 gap-8 max-w-6xl mx-auto">
              {features.map((feature, index) => {
                const Icon = feature.icon;
                return (
                  <motion.div
                    key={index}
                    variants={itemVariants}
                  >
                    <Card hover={true} delay={index * 0.1}>
                      <div 
                        className="w-14 h-14 rounded-lg flex items-center justify-center mb-4"
                        style={{ backgroundColor: 'var(--color-highlight)' }}
                      >
                        <Icon size={28} style={{ color: 'var(--color-accent)' }} />
                      </div>
                      
                      <h3 
                        className="text-2xl font-semibold mb-3"
                        style={{ 
                          fontFamily: 'var(--font-serif)',
                          color: 'var(--color-ink)'
                        }}
                      >
                        {feature.title}
                      </h3>
                      
                      <p style={{ color: 'var(--color-ink-light)' }}>
                        {feature.description}
                      </p>
                    </Card>
                  </motion.div>
                );
              })}
            </div>
          </motion.div>
        </div>
      </section>

      {/* CTA Section */}
      <section 
        className="py-20"
        style={{ backgroundColor: 'var(--color-muted)' }}
      >
        <div className="container mx-auto px-6">
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            whileInView={{ opacity: 1, scale: 1 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6 }}
            className="max-w-3xl mx-auto text-center"
          >
            <h2 
              className="text-4xl md:text-5xl font-bold mb-6"
              style={{ 
                fontFamily: 'var(--font-serif)',
                color: 'var(--color-ink)'
              }}
            >
              Ready to Level Up Your Learning?
            </h2>
            
            <p 
              className="text-xl mb-8"
              style={{ color: 'var(--color-ink-light)' }}
            >
              Upload your handwritten work and get instant AI-powered feedback 
              that helps you understand not just what went wrong, but why.
            </p>

            <Link to="/analysis">
              <Button 
                variant="primary" 
                size="lg"
                icon={<ArrowRight size={20} />}
              >
                Begin Your First Analysis
              </Button>
            </Link>
          </motion.div>
        </div>
      </section>
    </div>
  );
};

export default Home;
