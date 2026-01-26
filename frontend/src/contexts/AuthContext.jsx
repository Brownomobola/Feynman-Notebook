import { createContext, useContext, useState, useEffect, useCallback } from 'react';
import apiService from '../services/api';

const AuthContext = createContext(null);

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [sessionKey, setSessionKey] = useState(null);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  // Check auth status on mount
  useEffect(() => {
    checkAuthStatus();
  }, []);

  const checkAuthStatus = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await apiService.getMe();
      if (response.authenticated) {
        setUser(response.user);
        setIsAuthenticated(true);
        setSessionKey(null);
      } else {
        setUser(null);
        setIsAuthenticated(false);
        setSessionKey(response.session_key);
      }
    } catch (err) {
      console.error('Auth check failed:', err);
      setError(err.message);
      setUser(null);
      setIsAuthenticated(false);
    } finally {
      setIsLoading(false);
    }
  };

  const login = useCallback(async (username, password) => {
    setError(null);
    try {
      const response = await apiService.login(username, password);
      setUser(response.user);
      setIsAuthenticated(true);
      setSessionKey(null);
      return { success: true };
    } catch (err) {
      setError(err.message);
      return { success: false, error: err.message };
    }
  }, []);

  const register = useCallback(async (username, email, password, passwordConfirm) => {
    setError(null);
    try {
      const response = await apiService.register(username, email, password, passwordConfirm);
      setUser(response.user);
      setIsAuthenticated(true);
      setSessionKey(null);
      return { success: true };
    } catch (err) {
      setError(err.message);
      return { success: false, error: err.message };
    }
  }, []);

  const logout = useCallback(async () => {
    try {
      await apiService.logout();
    } catch (err) {
      console.error('Logout failed:', err);
    } finally {
      setUser(null);
      setIsAuthenticated(false);
      // Refresh to get new session key
      await checkAuthStatus();
    }
  }, []);

  const clearError = useCallback(() => {
    setError(null);
  }, []);

  const value = {
    user,
    sessionKey,
    isAuthenticated,
    isLoading,
    error,
    login,
    register,
    logout,
    checkAuthStatus,
    clearError
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};

export default AuthContext;
