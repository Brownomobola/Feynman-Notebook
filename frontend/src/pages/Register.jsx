import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { UserPlus, User, Mail, Lock, ArrowRight } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import Button from '../components/Button';
import Card from '../components/Card';

const Register = () => {
  const navigate = useNavigate();
  const { register } = useAuth();
  
  const [formData, setFormData] = useState({
    username: '',
    email: '',
    password: '',
    passwordConfirm: ''
  });
  const [error, setError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
    setError('');
  };

  const validateForm = () => {
    if (!formData.username || !formData.email || !formData.password || !formData.passwordConfirm) {
      setError('Please fill in all fields');
      return false;
    }
    
    if (formData.password.length < 8) {
      setError('Password must be at least 8 characters');
      return false;
    }
    
    if (formData.password !== formData.passwordConfirm) {
      setError('Passwords do not match');
      return false;
    }
    
    // Basic email validation
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(formData.email)) {
      setError('Please enter a valid email address');
      return false;
    }
    
    return true;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!validateForm()) return;

    setIsSubmitting(true);
    setError('');

    const result = await register(
      formData.username,
      formData.email,
      formData.password,
      formData.passwordConfirm
    );
    
    if (result.success) {
      navigate('/', { replace: true });
    } else {
      setError(result.error || 'Registration failed');
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
              <UserPlus size={32} style={{ color: 'var(--color-accent)' }} />
            </div>
            <h1 
              className="text-3xl font-bold mb-2"
              style={{ 
                fontFamily: 'var(--font-serif)',
                color: 'var(--color-ink)'
              }}
            >
              Create Account
            </h1>
            <p style={{ color: 'var(--color-ink-light)' }}>
              Join us to track your learning progress
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

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label 
                className="block text-sm font-medium mb-2"
                style={{ color: 'var(--color-ink)' }}
              >
                Username
              </label>
              <div className="relative">
                <User 
                  size={18} 
                  className="absolute left-3 top-1/2 -translate-y-1/2"
                  style={{ color: 'var(--color-ink-light)' }}
                />
                <input
                  type="text"
                  name="username"
                  value={formData.username}
                  onChange={handleChange}
                  placeholder="Choose a username"
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
                Email
              </label>
              <div className="relative">
                <Mail 
                  size={18} 
                  className="absolute left-3 top-1/2 -translate-y-1/2"
                  style={{ color: 'var(--color-ink-light)' }}
                />
                <input
                  type="email"
                  name="email"
                  value={formData.email}
                  onChange={handleChange}
                  placeholder="Enter your email"
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
                  placeholder="Create a password (min 8 characters)"
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
                Confirm Password
              </label>
              <div className="relative">
                <Lock 
                  size={18} 
                  className="absolute left-3 top-1/2 -translate-y-1/2"
                  style={{ color: 'var(--color-ink-light)' }}
                />
                <input
                  type="password"
                  name="passwordConfirm"
                  value={formData.passwordConfirm}
                  onChange={handleChange}
                  placeholder="Confirm your password"
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
              Create Account
            </Button>
          </form>

          <div className="mt-6 text-center">
            <p style={{ color: 'var(--color-ink-light)' }}>
              Already have an account?{' '}
              <Link 
                to="/login"
                className="font-medium hover:underline"
                style={{ color: 'var(--color-accent)' }}
              >
                Sign in
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

export default Register;
