import React, { useState, useEffect, useRef } from 'react';
import { useAuth } from '../../context/AuthContext';
import { AlertCircle, Loader2 } from 'lucide-react';

export const GoogleSignInButton = ({ onSuccess, text = "Continue with Google" }) => {
  const { googleLogin } = useAuth();
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const googleBtnContainerRef = useRef(null);

  const googleClientId = import.meta.env.VITE_GOOGLE_CLIENT_ID || '';
  const cleanClientId = (googleClientId || '')
    .replace(/^\uFEFF/, '')
    .trim();

  const handleGoogleCredentialResponse = async (response) => {
    if (!response || !response.credential) {
      setError('Google returned invalid credential token.');
      return;
    }
    setIsLoading(true);
    setError('');
    try {
      await googleLogin(response.credential);
      if (onSuccess) onSuccess();
    } catch (err) {
      console.error('[Google Auth Error]:', err);
      const msg = err.response?.data?.detail || 'Google Authentication failed. Please try again.';
      setError(msg);
    } finally {
      setIsLoading(false);
    }
  };

  // Store latest handler in ref so GSI callback always calls current function
  const handleResponseRef = useRef(handleGoogleCredentialResponse);
  useEffect(() => {
    handleResponseRef.current = handleGoogleCredentialResponse;
  });

  const hasInitializedRef = useRef(false);

  useEffect(() => {
    if (!cleanClientId) {
      setError('VITE_GOOGLE_CLIENT_ID is not configured.');
      console.warn('[Google Auth]: VITE_GOOGLE_CLIENT_ID is not configured.');
      return;
    }

    if (import.meta.env.DEV && window.location.origin !== 'http://localhost:5173') {
      console.warn(`[Google Auth Origin Warning]: Expected http://localhost:5173 but detected ${window.location.origin}`);
    }

    console.log('[Google OAuth Diagnostic]', {
      origin: window.location.origin,
      clientConfigured: 'YES',
      clientSuffix: cleanClientId ? cleanClientId.slice(-6) : 'NONE',
      environment: import.meta.env.MODE || 'development',
    });

    const callbackWrapper = (res) => {
      if (handleResponseRef.current) {
        handleResponseRef.current(res);
      }
    };

    const initGsi = () => {
      if (window.google?.accounts?.id) {
        try {
          if (!hasInitializedRef.current) {
            window.google.accounts.id.initialize({
              client_id: cleanClientId,
              callback: callbackWrapper,
              auto_select: false,
              cancel_on_tap_outside: true,
              ux_mode: 'popup',
            });
            hasInitializedRef.current = true;
          }

          if (googleBtnContainerRef.current) {
            googleBtnContainerRef.current.innerHTML = '';
            window.google.accounts.id.renderButton(googleBtnContainerRef.current, {
              type: 'standard',
              theme: 'outline',
              size: 'large',
              width: 360,
              text: 'continue_with',
              shape: 'pill',
              logo_alignment: 'left',
            });
          }
        } catch (e) {
          console.error('[Google GIS Init Error]:', e);
          setError('Failed to initialize Google Sign-In.');
        }
      }
    };

    if (!window.google?.accounts?.id) {
      // Check if script element already exists
      let script = document.querySelector('script[src="https://accounts.google.com/gsi/client"]');
      if (!script) {
        script = document.createElement('script');
        script.src = 'https://accounts.google.com/gsi/client';
        script.async = true;
        script.defer = true;
        script.onerror = () => {
          console.error('[Google Auth]: Failed to load Google Identity Services SDK script.');
          setError('Google Sign-In SDK failed to load. Please check your internet connection or disable ad-blockers.');
        };
        script.onload = initGsi;
        document.body.appendChild(script);
      } else {
        script.addEventListener('load', initGsi);
        if (window.google?.accounts?.id) {
          initGsi();
        }
      }
    } else {
      initGsi();
    }
  }, [cleanClientId]);

  return (
    <div className="w-full space-y-2">
      {error && (
        <div className="flex items-start gap-2 rounded-xl p-3 text-xs font-medium"
          style={{ background: 'rgba(239, 68, 68, 0.1)', border: '1px solid rgba(239, 68, 68, 0.25)', color: '#EF4444' }}
          role="alert"
        >
          <AlertCircle className="h-4 w-4 flex-shrink-0 mt-0.5" aria-hidden="true" />
          <span>{error}</span>
        </div>
      )}

      {isLoading && (
        <div className="flex items-center justify-center gap-2 rounded-xl p-3 text-xs font-medium"
          style={{ background: 'rgba(34, 197, 94, 0.1)', border: '1px solid rgba(34, 197, 94, 0.25)', color: 'var(--sp-primary)' }}
        >
          <Loader2 className="h-4 w-4 animate-spin flex-shrink-0" />
          <span>Authenticating with Google...</span>
        </div>
      )}

      {/* Render Google's official GIS button container */}
      <div 
        ref={googleBtnContainerRef} 
        className="w-full flex justify-center min-h-[44px]"
        style={{ colorScheme: 'none' }}
      />
    </div>
  );
};

