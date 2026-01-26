import { Link, useLocation, useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Brain, BookOpen, Dumbbell, History, LogIn, LogOut, User } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';

const Header = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const { user, isAuthenticated, isLoading, logout } = useAuth();

  const navItems = [
    { path: '/', label: 'Home', icon: Brain },
    { path: '/analysis', label: 'Analysis', icon: BookOpen },
    { path: '/history', label: 'History', icon: History },
  ];

  const isActive = (path) => location.pathname === path;

  const handleLogout = async () => {
    await logout();
    navigate('/');
  };

  return (
    <header 
      className="sticky top-0 z-50 backdrop-blur-md border-b"
      style={{ 
        backgroundColor: 'rgba(253, 251, 247, 0.9)',
        borderColor: 'var(--color-border)'
      }}
    >
      <nav className="container mx-auto px-6 py-4">
        <div className="flex items-center justify-between">
          {/* Logo */}
          <Link to="/" className="flex items-center gap-3 group">
            <motion.div
              whileHover={{ rotate: 180 }}
              transition={{ duration: 0.3 }}
              className="p-2 rounded-lg"
              style={{ backgroundColor: 'var(--color-accent)' }}
            >
              <Brain size={24} color="white" />
            </motion.div>
            <div>
              <h1 
                className="text-2xl font-bold tracking-tight"
                style={{ 
                  fontFamily: 'var(--font-serif)',
                  color: 'var(--color-ink)'
                }}
              >
                Feynman Tutor
              </h1>
              <p 
                className="text-xs"
                style={{ color: 'var(--color-ink-light)' }}
              >
                Debug Your Intuition
              </p>
            </div>
          </Link>

          {/* Navigation */}
          <div className="flex items-center gap-1">
            {navItems.map((item) => {
              const Icon = item.icon;
              const active = isActive(item.path);

              return (
                <Link
                  key={item.path}
                  to={item.path}
                  className="relative px-4 py-2 rounded-lg transition-colors flex items-center gap-2"
                  style={{
                    color: active ? 'var(--color-accent)' : 'var(--color-ink)',
                    fontWeight: active ? 500 : 400
                  }}
                >
                  <Icon size={18} />
                  <span>{item.label}</span>
                  
                  {active && (
                    <motion.div
                      layoutId="activeTab"
                      className="absolute inset-0 rounded-lg"
                      style={{ backgroundColor: 'var(--color-highlight)' }}
                      transition={{ type: "spring", bounce: 0.2, duration: 0.6 }}
                    />
                  )}
                  
                  <span className="relative z-10 flex items-center gap-2">
                    <Icon size={18} />
                    {item.label}
                  </span>
                </Link>
              );
            })}

            {/* Auth Section */}
            <div className="ml-4 pl-4 border-l flex items-center gap-2" style={{ borderColor: 'var(--color-border)' }}>
              {isLoading ? (
                <span className="text-sm" style={{ color: 'var(--color-ink-light)' }}>...</span>
              ) : isAuthenticated ? (
                <>
                  <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg" style={{ backgroundColor: 'var(--color-highlight)' }}>
                    <User size={16} style={{ color: 'var(--color-accent)' }} />
                    <span className="text-sm font-medium" style={{ color: 'var(--color-ink)' }}>
                      {user?.username}
                    </span>
                  </div>
                  <button
                    onClick={handleLogout}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg transition-colors hover:opacity-80"
                    style={{ 
                      color: 'var(--color-ink-light)'
                    }}
                  >
                    <LogOut size={16} />
                    <span className="text-sm">Logout</span>
                  </button>
                </>
              ) : (
                <>
                  <Link
                    to="/login"
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg transition-colors"
                    style={{ 
                      color: 'var(--color-ink)',
                      backgroundColor: isActive('/login') ? 'var(--color-highlight)' : 'transparent'
                    }}
                  >
                    <LogIn size={16} />
                    <span className="text-sm">Login</span>
                  </Link>
                  <Link
                    to="/register"
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg transition-colors"
                    style={{ 
                      color: 'white',
                      backgroundColor: 'var(--color-accent)'
                    }}
                  >
                    <span className="text-sm">Sign Up</span>
                  </Link>
                </>
              )}
            </div>
          </div>
        </div>
      </nav>
    </header>
  );
};

export default Header;
