"use client";

import { useState } from "react";
import axios from "axios";

export default function ChatPage() {
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);

  const sendMessage = async () => {
    if (!input.trim()) return;

    const userMessage = { role: "user", content: input };
    const newMessages = [...messages, userMessage];
    setMessages(newMessages);
    setInput("");
    setLoading(true);

    try {
      const response = await axios.post("http://localhost:3001/chat", {
        messages: newMessages,
      });

      const reply = response.data.reply;
      setMessages([...newMessages, reply]);
    } catch (error) {
      console.error("Error sending message:", error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-white to-blue-50 p-4">
      <div className="max-w-3xl mx-auto">
        <h1 className="text-3xl font-bold text-center text-blue-800 mb-6">AI Study Companion</h1>

        <div className="space-y-6">
          {messages.map((msg, index) => (
            <div
              key={index}
              className={`p-4 rounded-xl shadow-md ${
                msg.role === "user" ? "bg-white text-right" : "bg-blue-100 text-left"
              }`}
            >
              {msg.role === "assistant" ? (
                <div className="space-y-3">
                  {msg.content.split(/(?=\n\*\*\u{1F4A1}|\*\*\u{2696}|\*\*\u{1F680})/u).map((section, idx) => (
                    <div key={idx} className="bg-white p-3 rounded-lg">
                      <p className="whitespace-pre-wrap text-gray-800">{section.trim()}</p>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-blue-800 font-semibold">{msg.content}</p>
              )}
            </div>
          ))}
        </div>

        <div className="mt-6 flex items-center gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && sendMessage()}
            placeholder="Ask a question..."
            className="flex-1 p-3 border border-blue-300 rounded-xl shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
          />
          <button
            onClick={sendMessage}
            disabled={loading}
            className="px-4 py-2 bg-blue-600 text-white rounded-xl hover:bg-blue-700 transition"
          >
            {loading ? "..." : "Send"}
          </button>
        </div>
      </div>
    </div>
  );
}
