import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import App from './app/App';
import { AuthProvider } from './auth/AuthContext';
import './styles/global.css';
import './styles/v2.css';
import './styles/social.css';
import './styles/feed.css';
import './styles/chat.css';
import './styles/v7.css';

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <AuthProvider><App /></AuthProvider>
  </StrictMode>
);
