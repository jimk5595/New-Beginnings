import React, { useState, useEffect, useRef } from 'react';

interface Attachment {
  name: string;
  mimeType: string;
  data: string;
  isText: boolean;
}

interface Message {
  sender: 'user' | 'eliza' | 'system' | string;
  text: string;
  timestamp: string;
  attachments?: Attachment[];
}

const TEXT_MIMES = new Set([
  'application/json', 'application/xml', 'application/javascript',
  'application/x-python', 'application/x-sh', 'application/x-yaml',
  'application/toml', 'application/csv',
]);

function isTextMime(mime: string): boolean {
  return mime.startsWith('text/') || TEXT_MIMES.has(mime);
}

async function readFileAsAttachment(file: File): Promise<Attachment> {
  const mime = file.type || 'application/octet-stream';
  return new Promise((resolve) => {
    if (isTextMime(mime)) {
      const reader = new FileReader();
      reader.onloadend = () => resolve({ name: file.name, mimeType: mime, data: reader.result as string, isText: true });
      reader.readAsText(file);
    } else {
      const reader = new FileReader();
      reader.onloadend = () => {
        const result = reader.result as string;
        const b64 = result.includes(',') ? result.split(',')[1] : result;
        resolve({ name: file.name, mimeType: mime, data: b64, isText: false });
      };
      reader.readAsDataURL(file);
    }
  });
}

const SESSION_ID = `session_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;

export const SharedChat: React.FC = () => {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([
    { sender: 'eliza', text: 'Hello! I am Eliza, your System Orchestrator. How can I help you build today?', timestamp: new Date().toLocaleTimeString() }
  ]);
  const [input, setInput] = useState('');
  const [stagedFiles, setStagedFiles] = useState<File[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      setStagedFiles(prev => [...prev, ...Array.from(e.target.files!)]);
    }
    e.target.value = '';
  };

  const removeStagedFile = (i: number) => {
    setStagedFiles(prev => prev.filter((_, idx) => idx !== i));
  };

  const handleSend = async () => {
    if (!input.trim() && stagedFiles.length === 0) return;

    const filesToSend = [...stagedFiles];
    setStagedFiles([]);
    const currentInput = input;
    setInput('');
    setIsLoading(true);

    const attachments = await Promise.all(filesToSend.map(readFileAsAttachment));

    const userMsg: Message = {
      sender: 'user',
      text: currentInput || '(attachment only)',
      timestamp: new Date().toLocaleTimeString(),
      attachments,
    };
    setMessages(prev => [...prev, userMsg]);

    try {
      const response = await fetch('http://127.0.0.1:8000/api/eliza/task', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ task_text: currentInput, attachments, session_id: SESSION_ID }),
      });
      const data = await response.json();

      const responseText = (data.response && typeof data.response === 'object')
        ? (data.response.text || JSON.stringify(data.response))
        : (data.response || data.message || 'No response received.');

      const elizaMsg: Message = {
        sender: data.assigned_to || 'eliza',
        text: responseText,
        timestamp: new Date().toLocaleTimeString(),
      };
      setMessages(prev => [...prev, elizaMsg]);
    } catch {
      setMessages(prev => [...prev, { sender: 'system', text: 'Communication error.', timestamp: new Date().toLocaleTimeString() }]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) handleSend();
  };

  return (
    <div style={{ position: 'fixed', bottom: '20px', right: '20px', zIndex: 9999, fontFamily: 'sans-serif' }}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        style={{
          width: '60px', height: '60px', borderRadius: '50%',
          backgroundColor: '#007bff', color: 'white', border: 'none',
          boxShadow: '0 4px 12px rgba(0,0,0,0.15)', cursor: 'pointer',
          fontSize: '24px', display: 'flex', alignItems: 'center',
          justifyContent: 'center', transition: 'transform 0.2s',
        }}
      >
        {isOpen ? '✕' : '💬'}
      </button>

      {isOpen && (
        <div style={{
          position: 'absolute', bottom: '80px', right: '0',
          width: '370px', height: '540px', backgroundColor: 'white',
          borderRadius: '12px', boxShadow: '0 8px 24px rgba(0,0,0,0.2)',
          display: 'flex', flexDirection: 'column', overflow: 'hidden',
          border: '1px solid #eee',
        }}>
          <div style={{ padding: '15px', backgroundColor: '#007bff', color: 'white', fontWeight: 'bold', fontSize: '14px' }}>
            System Orchestrator
          </div>

          <div ref={scrollRef} style={{ flex: 1, padding: '15px', overflowY: 'auto', backgroundColor: '#f9f9f9', display: 'flex', flexDirection: 'column', gap: '12px' }}>
            {messages.map((msg, i) => (
              <div key={i} style={{ display: 'flex', flexDirection: 'column', alignItems: msg.sender === 'user' ? 'flex-end' : 'flex-start' }}>
                <div style={{ fontSize: '10px', color: '#888', marginBottom: '3px' }}>{msg.sender.toUpperCase()} — {msg.timestamp}</div>
                <div style={{
                  display: 'inline-block', padding: '10px 14px', borderRadius: '12px',
                  backgroundColor: msg.sender === 'user' ? '#007bff' : msg.sender === 'system' ? 'transparent' : '#fff',
                  color: msg.sender === 'user' ? 'white' : msg.sender === 'system' ? '#aaa' : '#333',
                  boxShadow: msg.sender === 'system' ? 'none' : '0 1px 2px rgba(0,0,0,0.05)',
                  maxWidth: '85%', wordWrap: 'break-word', whiteSpace: 'pre-wrap',
                  border: (msg.sender !== 'user' && msg.sender !== 'system') ? '1px solid #eee' : 'none',
                  fontStyle: msg.sender === 'system' ? 'italic' : 'normal',
                  fontSize: msg.sender === 'system' ? '11px' : '13px',
                }}>
                  {msg.text}
                </div>
                {msg.attachments && msg.attachments.length > 0 && (
                  <div style={{ marginTop: '6px', display: 'flex', flexWrap: 'wrap', gap: '5px' }}>
                    {msg.attachments.map((att, idx) => (
                      att.mimeType.startsWith('image/') && !att.isText ? (
                        <img key={idx} src={`data:${att.mimeType};base64,${att.data}`} style={{ maxWidth: '180px', maxHeight: '130px', borderRadius: '6px', border: '1px solid #ddd' }} alt={att.name} />
                      ) : att.mimeType.startsWith('video/') && !att.isText ? (
                        <video key={idx} src={`data:${att.mimeType};base64,${att.data}`} controls style={{ maxWidth: '200px', borderRadius: '6px' }} />
                      ) : (
                        <span key={idx} style={{ background: '#f0f0f0', border: '1px solid #ddd', borderRadius: '4px', padding: '2px 8px', fontSize: '11px', color: '#666' }}>📄 {att.name}</span>
                      )
                    ))}
                  </div>
                )}
              </div>
            ))}
            {isLoading && <div style={{ fontSize: '12px', color: '#aaa', fontStyle: 'italic' }}>Thinking…</div>}
          </div>

          {stagedFiles.length > 0 && (
            <div style={{ padding: '6px 14px', borderTop: '1px solid #eee', display: 'flex', flexWrap: 'wrap', gap: '5px', backgroundColor: '#fafafa' }}>
              {stagedFiles.map((f, i) => (
                <span key={i} style={{ background: '#e8f0fe', border: '1px solid #c5d3f5', borderRadius: '4px', padding: '2px 8px', fontSize: '11px', color: '#3d5afe', display: 'flex', alignItems: 'center', gap: '4px' }}>
                  📄 {f.name}
                  <span style={{ cursor: 'pointer', color: '#999', marginLeft: '2px' }} onClick={() => removeStagedFile(i)}>✕</span>
                </span>
              ))}
            </div>
          )}

          <div style={{ padding: '10px 12px', borderTop: '1px solid #eee', display: 'flex', gap: '8px', alignItems: 'center' }}>
            <input type="file" multiple onChange={handleFileChange} ref={fileInputRef} style={{ display: 'none' }} />
            <button onClick={() => fileInputRef.current?.click()} style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: '20px', padding: '2px' }} title="Attach files">📎</button>
            <input
              type="text" value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Type a message..."
              style={{ flex: 1, padding: '8px 12px', borderRadius: '20px', border: '1px solid #ddd', outline: 'none', fontSize: '13px' }}
            />
            <button onClick={handleSend} style={{ padding: '8px 15px', borderRadius: '20px', border: 'none', backgroundColor: '#007bff', color: 'white', cursor: 'pointer', fontSize: '13px' }}>
              Send
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default SharedChat;
