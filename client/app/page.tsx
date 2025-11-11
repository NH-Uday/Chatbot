'use client';

import { useState, useEffect, KeyboardEvent } from 'react';
import axios from 'axios';

declare global {
  interface Window {
    MathJax?: {
      typeset: () => void;
    };
  }
}

type Message = {
  role: 'user' | 'assistant';
  content: string;
};

const API_BASE =
  process.env.NEXT_PUBLIC_BACKEND_ORIGIN || 'http://localhost:8000';

export default function ChatPage() {
  const [input, setInput] = useState<string>('');
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState<boolean>(false);

  // Re-render MathJax equations when messages change (client-side only)
  useEffect(() => {
    if (typeof window !== 'undefined' && window.MathJax?.typeset) {
      window.MathJax.typeset();
    }
  }, [messages]);

  const sendMessage = async () => {
    if (!input.trim() || loading) return;

    const text = input.trim();
    const userMessage: Message = { role: 'user', content: text };

    // Optimistically append user message
    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setLoading(true);

    try {
      const response = await axios.post(`${API_BASE}/chat`, {
        question: text,
      });

      const answer =
        (response.data && (response.data.answer || response.data.response)) ||
        'I did not receive a response from the backend.';

      const reply: Message = {
        role: 'assistant',
        content: answer,
      };

      setMessages((prev) => [...prev, reply]);
    } catch (error) {
      console.error('Error sending message:', error);

      const errorReply: Message = {
        role: 'assistant',
        content:
          '⚠️ I could not reach the backend. Please check that the API is running and accessible.',
      };

      setMessages((prev) => [...prev, errorReply]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      sendMessage();
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-white to-blue-50 p-4">
      <div className="max-w-3xl mx-auto">
        <h1 className="text-3xl font-bold text-center text-blue-800 mb-6">
          Chatbot companion for Lab
        </h1>

        {/* Messages */}
        <div className="space-y-6">
          {messages.map((msg, index) => (
            <div
              key={index}
              className={`p-4 rounded-xl shadow-md ${
                msg.role === 'user'
                  ? 'bg-white text-right'
                  : 'bg-blue-100 text-left'
              }`}
            >
              {msg.role === 'assistant' ? (
                <div className="space-y-3">
                  {msg.content
                    .split(/\n(?=🧠|⚖️|🚀)/)
                    .map((section, idx) => (
                      <div key={idx} className="bg-white p-3 rounded-lg">
                        <p
                          className="text-sm whitespace-pre-wrap"
                          dangerouslySetInnerHTML={{
                            __html: section.trim(),
                          }}
                        />
                      </div>
                    ))}
                </div>
              ) : (
                <p className="text-blue-800 font-semibold">
                  {msg.content}
                </p>
              )}
            </div>
          ))}
        </div>

        {/* Input */}
        <div className="mt-6 flex items-center gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask a question..."
            className="flex-1 p-3 border border-blue-300 rounded-xl shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
          />
          <button
            onClick={sendMessage}
            disabled={loading}
            className="px-4 py-2 bg-blue-600 text-white rounded-xl hover:bg-blue-700 transition disabled:opacity-60"
          >
            {loading ? '...' : 'Send'}
          </button>
        </div>
      </div>
    </div>
  );
}
