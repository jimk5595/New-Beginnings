import React, { useState } from "react";
import { sendToEliza } from "../services/elizaService";

interface Message {
  sender: "user" | "eliza";
  text: string;
}

export default function ChatWindow() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSend() {
    if (!input.trim()) return;

    const userMessage: Message = { sender: "user", text: input };
    setMessages(prev => [...prev, userMessage]);
    setInput("");
    setLoading(true);

    const response = await sendToEliza(userMessage.text);
    const elizaMessage: Message = {
      sender: "eliza",
      text: response.message
    };

    setMessages(prev => [...prev, elizaMessage]);
    setLoading(false);
  }

  return (
    <div style={{ 
      width: "100%", 
      maxWidth: "600px", 
      margin: "0 auto", 
      background: "#ffffff",
      borderRadius: "8px",
      padding: "20px",
      boxShadow: "0 0 10px rgba(0,0,0,0.1)"
    }}>
      <div style={{
        height: "400px",
        overflowY: "auto",
        border: "1px solid #ddd",
        padding: "10px",
        marginBottom: "15px",
        background: "#fafafa"
      }}>
        {messages.map((msg, index) => (
          <div 
            key={index}
            style={{
              marginBottom: "10px",
              textAlign: msg.sender === "user" ? "right" : "left"
            }}
          >
            <span 
              style={{
                display: "inline-block",
                padding: "8px 12px",
                borderRadius: "6px",
                background: msg.sender === "user" ? "#007bff" : "#e0e0e0",
                color: msg.sender === "user" ? "#fff" : "#000"
              }}
            >
              {msg.text}
            </span>
          </div>
        ))}
        {loading && (
          <div style={{ fontStyle: "italic", color: "#666" }}>
            Eliza is thinking...
          </div>
        )}
      </div>
      <div style={{ display: "flex", gap: "10px" }}>
        <input
          value={input}
          onChange={e => setInput(e.target.value)}
          placeholder="Type your message..."
          style={{
            flex: 1,
            padding: "10px",
            borderRadius: "6px",
            border: "1px solid #ccc"
          }}
        />
        <button
          onClick={handleSend}
          style={{
            padding: "10px 16px",
            borderRadius: "6px",
            border: "none",
            background: "#007bff",
            color: "#fff",
            cursor: "pointer"
          }}
        >
          Send
        </button>
      </div>
    </div>
  );
}
