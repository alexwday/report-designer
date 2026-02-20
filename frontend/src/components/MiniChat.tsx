import { useState, useRef, useEffect } from 'react';
import { useChatMutation } from '../api/queries';
import { Markdown } from './Markdown';
import type { ToolCallLog } from '../api/types';

interface MiniChatProps {
  templateId: string;
  sectionId: string;
  subsectionId: string;
  onClose: () => void;
  position?: { top: number; left: number };
}

export function MiniChat({
  templateId,
  sectionId,
  subsectionId,
  onClose,
  position,
}: MiniChatProps) {
  const [message, setMessage] = useState('');
  const [messages, setMessages] = useState<Array<{ role: 'user' | 'assistant'; content: string }>>([]);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const chatMutation = useChatMutation(templateId);

  // Auto-focus input on mount
  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Close on Escape
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [onClose]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!message.trim() || chatMutation.isPending) return;

    const userMessage = message.trim();
    setMessage('');
    setMessages((prev) => [...prev, { role: 'user', content: userMessage }]);

    try {
      const response = await chatMutation.mutateAsync({
        message: userMessage,
        focus_section_id: sectionId,
        focus_subsection_id: subsectionId,
      });
      setMessages((prev) => [...prev, { role: 'assistant', content: response.response }]);
    } catch (err) {
      console.error('Chat error:', err);
      setMessages((prev) => [...prev, { role: 'assistant', content: 'Sorry, something went wrong.' }]);
    }
  };

  const suggestedPrompts = [
    'Generate content for this subsection',
    'Summarize key points',
    'Add a data table',
    'Improve the writing',
  ];

  const handleSuggestion = (prompt: string) => {
    setMessage(prompt);
    inputRef.current?.focus();
  };

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 z-40"
        onClick={onClose}
      />

      {/* Chat popup */}
      <div
        className="fixed z-50 w-80 bg-white rounded-lg shadow-2xl border border-zinc-200 flex flex-col max-h-96"
        style={position ? { top: position.top, left: position.left } : { top: '50%', left: '50%', transform: 'translate(-50%, -50%)' }}
      >
        {/* Header */}
        <div className="px-4 py-3 border-b border-zinc-200 flex items-center justify-between bg-zinc-50 rounded-t-lg">
          <div>
            <span className="font-medium text-zinc-800 text-sm">Quick Chat</span>
          </div>
          <button
            onClick={onClose}
            className="p-1 text-zinc-400 hover:text-zinc-600 rounded"
            title="Close (Esc)"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-3 space-y-3 min-h-[100px]">
          {messages.length === 0 ? (
            <div className="space-y-2">
              <p className="text-xs text-zinc-500 text-center">Quick actions:</p>
              <div className="flex flex-wrap gap-1">
                {suggestedPrompts.map((prompt) => (
                  <button
                    key={prompt}
                    onClick={() => handleSuggestion(prompt)}
                    className="px-2 py-1 text-xs bg-zinc-100 text-zinc-700 rounded hover:bg-zinc-200 transition-colors"
                  >
                    {prompt}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            messages.map((msg, idx) => (
              <div
                key={idx}
                className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                <div
                  className={`max-w-[90%] rounded-lg px-3 py-2 text-sm ${
                    msg.role === 'user'
                      ? 'bg-sky-600 text-white'
                      : 'bg-zinc-100 text-zinc-800'
                  }`}
                >
                  {msg.role === 'user' ? (
                    <p className="whitespace-pre-wrap">{msg.content}</p>
                  ) : (
                    <Markdown content={msg.content} className="text-sm" />
                  )}
                </div>
              </div>
            ))
          )}
          {chatMutation.isPending && (
            <div className="flex items-center gap-2 text-zinc-500 text-xs">
              <div className="animate-spin w-3 h-3 border-2 border-sky-500 border-t-transparent rounded-full" />
              Thinking...
            </div>
          )}
          {chatMutation.data && !chatMutation.isPending && chatMutation.data.tool_calls.length > 0 && (
            <ToolCallBadges toolCalls={chatMutation.data.tool_calls} />
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Input */}
        <form onSubmit={handleSubmit} className="p-3 border-t border-zinc-200">
          <div className="flex gap-2">
            <input
              ref={inputRef}
              type="text"
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              placeholder="Ask about this subsection..."
              className="flex-1 px-3 py-1.5 text-sm border border-zinc-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-sky-500"
              disabled={chatMutation.isPending}
            />
            <button
              type="submit"
              disabled={chatMutation.isPending || !message.trim()}
              className="px-3 py-1.5 bg-sky-600 text-white text-sm rounded-lg hover:bg-sky-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
              </svg>
            </button>
          </div>
        </form>
      </div>
    </>
  );
}

function ToolCallBadges({ toolCalls }: { toolCalls: ToolCallLog[] }) {
  if (!toolCalls || toolCalls.length === 0) return null;

  return (
    <div className="flex flex-wrap gap-1">
      {toolCalls.map((tc, i) => (
        <span
          key={i}
          className={`px-1.5 py-0.5 text-xs rounded ${
            tc.error
              ? 'bg-red-100 text-red-700'
              : 'bg-green-100 text-green-700'
          }`}
          title={tc.error || 'Success'}
        >
          {tc.tool}
        </span>
      ))}
    </div>
  );
}
