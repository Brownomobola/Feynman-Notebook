import { useState } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { motion } from 'framer-motion';
import { LogIn, Mail, Lock, ArrowRight } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import Button from '../components/Button';
import Card from '../components/Card';

const Login = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { login, isLoading } = useAuth();
  
  const [formData, setFormData] = useState({
    username: '',
    password: ''
  });
  const [error, setError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Get redirect path from location state, default to home
  const from = location.state?.from?.pathname || '/';

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
    setError('');
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!formData.username || !formData.password) {
      setError('Please fill in all fields');
      return;
    }

    setIsSubmitting(true);
    setError('');

    const result = await login(formData.username, formData.password);
    
    if (result.success) {
      navigate(from, { replace: true });
    } else {
      setError(result.error || 'Login failed');
    }
    
    setIsSubmitting(false);
  };

  return (
    <div className="min-h-screen py-12 flex items-center justify-center">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="w-full max-w-md px-6"
      >
        <Card>
          <div className="text-center mb-8">
            <div 
              className="inline-flex items-center justify-center p-4 rounded-2xl mb-4"
              style={{ backgroundColor: 'var(--color-highlight)' }}
            >
              <LogIn size={32} style={{ color: 'var(--color-accent)' }} />
            </div>
            <h1 
              className="text-3xl font-bold mb-2"
              style={{ 
                fontFamily: 'var(--font-serif)',
                color: 'var(--color-ink)'
              }}
            >
              Welcome Back
            </h1>
            <p style={{ color: 'var(--color-ink-light)' }}>
              Sign in to continue learning
            </p>
          </div>

          {error && (
            <div 
              className="p-3 rounded-lg mb-6 text-center"
              style={{ 
                backgroundColor: 'var(--color-error-bg)',
                color: 'var(--color-incorrect)'
              }}
            >
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-5">
            <div>
              <label 
                className="block text-sm font-medium mb-2"
                style={{ color: 'var(--color-ink)' }}
              >
                Username or Email
              </label>
              <div className="relative">
                <Mail 
                  size={18} 
                  className="absolute left-3 top-1/2 -translate-y-1/2"
                  style={{ color: 'var(--color-ink-light)' }}
                />
                <input
                  type="text"
                  name="username"
                  value={formData.username}
                  onChange={handleChange}
                  placeholder="Enter your username or email"
                  className="w-full pl-10"
                  disabled={isSubmitting}
                />
              </div>
            </div>

            <div>
              <label 
                className="block text-sm font-medium mb-2"
                style={{ color: 'var(--color-ink)' }}
              >
                Password
              </label>
              <div className="relative">
                <Lock 
                  size={18} 
                  className="absolute left-3 top-1/2 -translate-y-1/2"
                  style={{ color: 'var(--color-ink-light)' }}
                />
                <input
                  type="password"
                  name="password"
                  value={formData.password}
                  onChange={handleChange}
                  placeholder="Enter your password"
                  className="w-full pl-10"
                  disabled={isSubmitting}
                />
              </div>
            </div>

            <Button
              type="submit"
              variant="primary"
              size="lg"
              className="w-full"
              loading={isSubmitting}
              disabled={isSubmitting}
              icon={!isSubmitting ? <ArrowRight size={18} /> : null}
            >
              Sign In
            </Button>
          </form>

          <div className="mt-6 text-center">
            <p style={{ color: 'var(--color-ink-light)' }}>
              Don't have an account?{' '}
              <Link 
                to="/register"
                className="font-medium hover:underline"
                style={{ color: 'var(--color-accent)' }}
              >
                Sign up
              </Link>
            </p>
          </div>

          <div className="mt-4 text-center">
            <Link 
              to="/"
              className="text-sm hover:underline"
              style={{ color: 'var(--color-ink-light)' }}
            >
              Continue as guest
            </Link>
          </div>
        </Card>
      </motion.div>
    </div>
  );
};

export default Login;
