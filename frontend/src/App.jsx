import React, { useState, useEffect, useRef } from 'react';
import './App.css';
import { 
  Send, 
  PlusCircle, 
  Bot, 
  User, 
  Cpu, 
  Clock, 
  Key, 
  Layers, 
  AlertTriangle,
  RotateCw,
  Sparkles,
  Zap
} from 'lucide-react';

const API_BASE_URL = (import.meta.env.VITE_API_URL || import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000').replace(/\/+$/, '');

function generateSessionId() {
  return 's-' + Math.random().toString(36).substring(2, 10);
}

export default function App() {
  const [sessionId, setSessionId] = useState('');
  const [messages, setMessages] = useState([]);
  const [inputMessage, setInputMessage] = useState('');
  const [systemPrompt, setSystemPrompt] = useState('You are Lyftr AI, a helpful, intelligent and reliable assistant.');
  const [isLoading, setIsLoading] = useState(false);
  const [simulateFailureHeader, setSimulateFailureHeader] = useState('');
  const [healthStatus, setHealthStatus] = useState(null);

  const messagesEndRef = useRef(null);

  // Initialize a new session on load per requirements
  useEffect(() => {
    startNewSession();
    checkHealth();
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const startNewSession = () => {
    const newId = generateSessionId();
    setSessionId(newId);
    setMessages([]);
    setInputMessage('');
  };

  const checkHealth = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/health`);
      if (res.ok) {
        const data = await res.json();
        setHealthStatus(data);
      }
    } catch (e) {
      console.error('Health check failed:', e);
    }
  };

  const handleSendMessage = async (e) => {
    if (e) e.preventDefault();
    const trimmed = inputMessage.trim();
    if (!trimmed || isLoading) return;

    // Add user message to UI immediately
    const userMsg = {
      role: 'user',
      content: trimmed
    };
    setMessages((prev) => [...prev, userMsg]);
    setInputMessage('');
    setIsLoading(true);

    try {
      const headers = {
        'Content-Type': 'application/json'
      };

      if (simulateFailureHeader.trim()) {
        headers['X-Simulate-Failure'] = simulateFailureHeader.trim();
      }

      const res = await fetch(`${API_BASE_URL}/chat`, {
        method: 'POST',
        headers: headers,
        body: JSON.stringify({
          session_id: sessionId,
          message: trimmed,
          system_prompt: systemPrompt.trim() ? systemPrompt.trim() : undefined
        })
      });

      const data = await res.json();

      if (!res.ok) {
        // Display readable error message
        const errMsg = typeof data.detail === 'string' 
          ? data.detail 
          : JSON.stringify(data.detail || 'An error occurred');
        
        setMessages((prev) => [
          ...prev,
          {
            role: 'error',
            content: `Error (${res.status}): ${errMsg}`
          }
        ]);
      } else {
        // Successful assistant response
        setMessages((prev) => [
          ...prev,
          {
            role: 'assistant',
            content: data.reply,
            metadata: data.metadata
          }
        ]);
      }
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          role: 'error',
          content: `Network or Connection Error: ${err.message}`
        }
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  return (
    <div className="app-layout">
      {/* Sidebar */}
      <aside className="sidebar">
        <div className="brand-section">
          <div className="brand-icon">
            <Zap size={22} color="#ffffff" />
          </div>
          <div>
            <div className="brand-title">Lyftr AI</div>
            <div className="brand-subtitle">Gemini Flash Gateway</div>
          </div>
        </div>

        <button className="new-chat-btn" onClick={startNewSession}>
          <PlusCircle size={18} />
          New Chat
        </button>

        <div className="sidebar-section">
          <span className="section-label">Session ID</span>
          <div className="session-info">
            <span>Active Session:</span>
            <span className="session-id-text">{sessionId}</span>
          </div>
        </div>

        <div className="sidebar-section">
          <span className="section-label">System Prompt</span>
          <textarea
            data-testid="system-prompt-input"
            className="system-prompt-textarea"
            value={systemPrompt}
            onChange={(e) => setSystemPrompt(e.target.value)}
            placeholder="Set system instructions..."
          />
        </div>

        <div className="sidebar-section">
          <span className="section-label">X-Simulate-Failure Hook</span>
          <div className="hook-controls">
            <input
              type="text"
              className="hook-input"
              value={simulateFailureHeader}
              onChange={(e) => setSimulateFailureHeader(e.target.value)}
              placeholder="e.g. key_1=429"
            />
            <div className="hook-presets">
              <button 
                type="button" 
                className="preset-chip" 
                onClick={() => setSimulateFailureHeader('key_1=429')}
              >
                key_1=429
              </button>
              <button 
                type="button" 
                className="preset-chip" 
                onClick={() => setSimulateFailureHeader('key_1=500')}
              >
                key_1=500
              </button>
              <button 
                type="button" 
                className="preset-chip" 
                onClick={() => setSimulateFailureHeader('*=429')}
              >
                *=429
              </button>
              <button 
                type="button" 
                className="preset-chip" 
                onClick={() => setSimulateFailureHeader('')}
              >
                Clear
              </button>
            </div>
          </div>
        </div>

        <div style={{ marginTop: 'auto' }} className="sidebar-section">
          <div className="session-info">
            <span style={{ fontWeight: 600 }}>System Health</span>
            {healthStatus ? (
              <>
                <span style={{ color: '#3fb950' }}>● Status: {healthStatus.status}</span>
                <span>Keys configured: {healthStatus.keys_configured}</span>
                <span>Cache: {healthStatus.cache_enabled ? 'Enabled' : 'Disabled'}</span>
              </>
            ) : (
              <span style={{ color: '#f85149' }}>● Connecting...</span>
            )}
          </div>
        </div>
      </aside>

      {/* Main Chat Area */}
      <main className="chat-container">
        <header className="chat-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <span style={{ fontWeight: 600, fontSize: '1rem' }}>Lyftr AI Multi-Turn Chat</span>
            <span style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>Session: {sessionId}</span>
          </div>
          <div className="status-badge">
            <div className="status-dot"></div>
            <span>LiteLLM Connected</span>
          </div>
        </header>

        {/* Messages List */}
        <div className="messages-list">
          {messages.length === 0 ? (
            <div className="empty-chat">
              <Bot className="empty-icon" />
              <div>
                <h3 style={{ marginBottom: '0.5rem', color: '#fff' }}>Welcome to Lyftr AI</h3>
                <p style={{ maxWidth: '450px', fontSize: '0.9rem', lineHeight: '1.5' }}>
                  A high-resilience AI chatbot powered by Gemini Flash, LiteLLM gateway failover, and exact response caching.
                </p>
              </div>
            </div>
          ) : (
            messages.map((msg, index) => {
              if (msg.role === 'user') {
                return (
                  <div key={index} className="message-row user">
                    <div className="user-message-bubble">
                      {msg.content}
                    </div>
                  </div>
                );
              } else if (msg.role === 'assistant') {
                const meta = msg.metadata || {};
                const isCache = meta.resolution_source === 'LLM_CACHE';
                return (
                  <div key={index} className="message-row assistant">
                    <div data-testid="assistant-message" className="assistant-message-container">
                      <div className="assistant-text">{msg.content}</div>

                      {/* Required Metadata Elements */}
                      <div className="metadata-card">
                        <span 
                          data-testid="meta-source" 
                          className={`meta-source-badge ${isCache ? 'cache' : 'live'}`}
                        >
                          {meta.resolution_source}
                        </span>

                        <span className="meta-pill">
                          <Cpu size={13} />
                          <span data-testid="meta-model">{meta.model}</span>
                        </span>

                        <span className="meta-pill">
                          <Clock size={13} />
                          <span data-testid="meta-latency">{meta.latency_ms} ms</span>
                        </span>

                        <span className="meta-pill">
                          <Layers size={13} />
                          <span>Input: <strong data-testid="meta-input-tokens">{meta.input_tokens}</strong></span>
                        </span>

                        <span className="meta-pill">
                          <Layers size={13} />
                          <span>Output: <strong data-testid="meta-output-tokens">{meta.output_tokens}</strong></span>
                        </span>

                        {meta.key_id && (
                          <span className="meta-pill">
                            <Key size={13} />
                            <span>Key: {meta.key_id}</span>
                          </span>
                        )}

                        {meta.fallback_attempts !== undefined && meta.fallback_attempts > 0 && (
                          <span className="meta-pill" style={{ color: '#d29922', borderColor: '#d29922' }}>
                            <RotateCw size={13} />
                            <span>Fallback: {meta.fallback_attempts}</span>
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                );
              } else if (msg.role === 'error') {
                return (
                  <div key={index} className="message-row assistant">
                    <div className="error-message">
                      <AlertTriangle size={18} />
                      <span>{msg.content}</span>
                    </div>
                  </div>
                );
              }
              return null;
            })
          )}

          {isLoading && (
            <div className="message-row assistant">
              <div className="loading-indicator">
                <Sparkles size={16} className="animate-pulse" />
                <span>Lyftr AI is generating response...</span>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Input Box Area */}
        <div className="input-section">
          <form onSubmit={handleSendMessage} className="input-box-wrapper">
            <textarea
              data-testid="chat-input"
              className="chat-textarea"
              rows={1}
              value={inputMessage}
              onChange={(e) => setInputMessage(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask Lyftr AI anything... (Enter to send, Shift+Enter for new line)"
            />
            <button
              data-testid="send-button"
              type="submit"
              disabled={!inputMessage.trim() || isLoading}
              className="send-action-btn"
            >
              <Send size={18} />
            </button>
          </form>
        </div>
      </main>
    </div>
  );
}
