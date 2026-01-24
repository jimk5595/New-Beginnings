import React from "react";
import ChatWindow from "./components/ChatWindow";

export default function App() {
  return (
    <div style={{ padding: "20px" }}>
      <h1 style={{ textAlign: "center" }}>Eliza Chat</h1>
      <ChatWindow />
    </div>
  );
}
