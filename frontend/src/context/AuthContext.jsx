import React, { createContext, useContext, useState, useEffect } from 'react';
import { authAPI, userAPI } from '../lib/api';

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(() => {
    const saved = localStorage.getItem('socialpilot_user');
    return saved ? JSON.parse(saved) : null;
  });
  const [token, setToken] = useState(() => localStorage.getItem('socialpilot_access_token'));
  const [isLoading, setIsLoading] = useState(true);

  // Theme Management — default to 'dark' to match SocialPilot brand identity
  const [theme, setTheme] = useState(() => localStorage.getItem('socialpilot_theme') || 'dark');

  useEffect(() => {
    const root = document.documentElement;
    const applyTheme = (t) => {
      if (t === 'dark') {
        root.classList.add('dark');
      } else if (t === 'light') {
        root.classList.remove('dark');
      } else {
        // System preference
        if (window.matchMedia('(prefers-color-scheme: dark)').matches) {
          root.classList.add('dark');
        } else {
          root.classList.remove('dark');
        }
      }
    };

    applyTheme(theme);
    localStorage.setItem('socialpilot_theme', theme);

    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
    const handleChange = () => {
      if (theme === 'system') applyTheme('system');
    };
    mediaQuery.addEventListener('change', handleChange);
    return () => mediaQuery.removeEventListener('change', handleChange);
  }, [theme]);

  // Initial Auth Check
  useEffect(() => {
    const initAuth = async () => {
      const storedToken = localStorage.getItem('socialpilot_access_token');
      if (storedToken) {
        try {
          const res = await authAPI.getMe();
          setUser(res.data);
          localStorage.setItem('socialpilot_user', JSON.stringify(res.data));
        } catch (err) {
          console.warn('Failed to restore session:', err);
          localStorage.removeItem('socialpilot_access_token');
          localStorage.removeItem('socialpilot_refresh_token');
          localStorage.removeItem('socialpilot_user');
          setUser(null);
          setToken(null);
        }
      }
      setIsLoading(false);
    };

    initAuth();
  }, []);

  const login = async (email, password) => {
    const res = await authAPI.login(email, password);
    const { access_token, refresh_token, user: userData } = res.data;

    localStorage.setItem('socialpilot_access_token', access_token);
    if (refresh_token) {
      localStorage.setItem('socialpilot_refresh_token', refresh_token);
    }
    if (userData) {
      localStorage.setItem('socialpilot_user', JSON.stringify(userData));
      setUser(userData);
    }
    setToken(access_token);
    return res.data;
  };

  const register = async (email, password, full_name) => {
    const res = await authAPI.register(email, password, full_name);
    // After registration, automatically log in
    return login(email, password);
  };

  const googleLogin = async (credential) => {
    const res = await authAPI.googleAuth(credential);
    const { access_token, refresh_token, user: userData } = res.data;

    localStorage.setItem('socialpilot_access_token', access_token);
    if (refresh_token) {
      localStorage.setItem('socialpilot_refresh_token', refresh_token);
    }
    if (userData) {
      localStorage.setItem('socialpilot_user', JSON.stringify(userData));
      setUser(userData);
    }
    setToken(access_token);
    return res.data;
  };

  const logout = () => {
    localStorage.removeItem('socialpilot_access_token');
    localStorage.removeItem('socialpilot_refresh_token');
    localStorage.removeItem('socialpilot_user');
    setUser(null);
    setToken(null);
    window.location.href = '/login';
  };

  const updateProfile = async (data) => {
    const res = await userAPI.updateProfile(data);
    setUser(res.data);
    localStorage.setItem('socialpilot_user', JSON.stringify(res.data));
    return res.data;
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        isAuthenticated: !!user && !!token,
        isLoading,
        login,
        register,
        googleLogin,
        logout,
        updateProfile,
        theme,
        setTheme,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
