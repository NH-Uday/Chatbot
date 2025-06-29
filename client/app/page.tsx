'use client'

import { useState } from 'react'

export default function Home() {
  const [input, setInput] = useState('')
  const [messages, setMessages] = useState<any[]>([])
  const [loading, setLoading] = useState(false)

  const sendMessage = async () => {
    if (!input.trim()) return

    const newMessages = [...messages, { role: 'user', content: input }]
    setMessages(newMessages)
    setInput('')
    setLoading(true)

    try {
      const res = await fetch('http://localhost:3001/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ messages: newMessages }),
      })

      const data = await res.json()

      if (data?.reply?.content) {
        setMessages([...newMessages, { role: 'assistant', content: data.reply.content }])
      } else {
        setMessages([
          ...newMessages,
          {
            role: 'assistant',
            content: '⚠️ An error occurred while generating a response. Please try again later.',
          },
        ])
      }
    } catch (error) {
      setMessages([
        ...newMessages,
        {
          role: 'assistant',
          content: '⚠️ Network error. Please check your connection or try again later.',
        },
      ])
    }

    setLoading(false)
  }

  return (
    <main className="flex flex-col h-screen bg-gray-900 text-white">
      <div className="flex-1 overflow-y-auto p-6 space-y-4">
        {messages.map((msg, i) => (
          <div
            key={i}
            className={`max-w-xl px-4 py-2 rounded-lg text-sm whitespace-pre-wrap ${
              msg.role === 'user'
                ? 'bg-blue-600 self-end ml-auto'
                : 'bg-gray-700 self-start mr-auto'
            }`}
          >
            {msg.content}
          </div>
        ))}
        {loading && <p className="text-gray-400 text-sm">ChatGPT is thinking...</p>}
      </div>

      <div className="p-4 border-t border-gray-700 bg-gray-800 flex">
        <input
          className="flex-1 px-4 py-2 bg-gray-700 text-white rounded-l focus:outline-none"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask a question..."
          onKeyDown={(e) => e.key === 'Enter' && sendMessage()}
        />
        <button
          onClick={sendMessage}
          className="bg-blue-600 px-4 rounded-r hover:bg-blue-700"
          disabled={!input.trim() || loading}
        >
          Send
        </button>
      </div>
    </main>
  )
}
