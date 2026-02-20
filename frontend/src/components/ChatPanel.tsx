import { useEffect, useRef, useState } from 'react';
import { useChatMutation, useChatHistory } from '../api/queries';
import { useWorkspaceStore } from '../store/workspace';
import { Markdown } from './Markdown';
import type { ConversationMessage, ToolCallLog } from '../api/types';

interface ChatPanelProps {
  templateId: string;
}

const MIN_WIDTH = 300;
const MAX_WIDTH = 620;
const DEFAULT_WIDTH = 360;

export function ChatPanel({ templateId }: ChatPanelProps) {
  const [message, setMessage] = useState('');
  const [panelWidth, setPanelWidth] = useState(DEFAULT_WIDTH);
  const [isResizing, setIsResizing] = useState(false);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const resizeStateRef = useRef<{ startX: number; startWidth: number } | null>(null);

  const {
    chatExpanded,
    toggleChat,
    selectedSectionId,
    selectedSubsectionId,
    selectedSubsectionInfo,
  } = useWorkspaceStore();

  const { data: history, isLoading: historyLoading } = useChatHistory(templateId);
  const chatMutation = useChatMutation(templateId);

  useEffect(() => {
    if (chatExpanded) {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [history?.messages, chatExpanded, chatMutation.isPending]);

  useEffect(() => {
    if (!isResizing) return;

    const handleMouseMove = (event: MouseEvent) => {
      const state = resizeStateRef.current;
      if (!state) return;

      const delta = state.startX - event.clientX;
      const nextWidth = Math.min(MAX_WIDTH, Math.max(MIN_WIDTH, state.startWidth + delta));
      setPanelWidth(nextWidth);
    };

    const handleMouseUp = () => {
      setIsResizing(false);
      resizeStateRef.current = null;
    };

    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('mouseup', handleMouseUp);

    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
    };
  }, [isResizing]);

  const startResize = (event: React.MouseEvent) => {
    event.preventDefault();
    resizeStateRef.current = {
      startX: event.clientX,
      startWidth: panelWidth,
    };
    setIsResizing(true);
  };

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!message.trim() || chatMutation.isPending) return;

    const msg = message.trim();
    setMessage('');

    try {
      await chatMutation.mutateAsync({
        message: msg,
        focus_section_id: selectedSectionId || undefined,
        focus_subsection_id: selectedSubsectionId || undefined,
      });
    } catch (err) {
      console.error('Chat error:', err);
    }
  };

  if (!chatExpanded) {
    return (
      <div className="w-14 rounded-xl border border-zinc-200 bg-gradient-to-b from-sky-50/80 to-zinc-100 shadow-sm flex flex-col items-center justify-between py-4">
        <button
          onClick={toggleChat}
          className="p-2 rounded-lg text-zinc-500 hover:text-zinc-700 hover:bg-zinc-100"
          title="Open assistant"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
          </svg>
        </button>
        <span className="text-[10px] text-zinc-400 tracking-wide uppercase [writing-mode:vertical-rl] rotate-180">
          AI Chat
        </span>
      </div>
    );
  }

  return (
    <div className="relative flex-shrink-0" style={{ width: `${panelWidth}px` }}>
      <div
        onMouseDown={startResize}
        className={`absolute -left-1.5 top-0 h-full w-2.5 cursor-col-resize ${isResizing ? 'bg-sky-300/80' : 'hover:bg-zinc-300/60'}`}
        title="Resize chat panel"
      />

      <div className="h-full rounded-xl border border-zinc-200 bg-gradient-to-b from-white to-zinc-50 shadow-sm flex flex-col overflow-hidden">
        <div className="px-4 py-3 border-b border-zinc-300/80 bg-sky-50/85 flex items-center justify-between">
          <div>
            <h3 className="text-sm font-semibold text-zinc-900">AI Assistant</h3>
          </div>
          <div className="flex items-center gap-1">
            <button
              onClick={() => setPanelWidth(DEFAULT_WIDTH)}
              className="p-1.5 text-zinc-400 hover:text-zinc-600"
              title="Reset width"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582M20 20v-5h-.581M5 9a7 7 0 0111.95-2.45L20 9M4 15l3.05 2.45A7 7 0 0019 15" />
              </svg>
            </button>
            <button
              onClick={toggleChat}
              className="p-1.5 text-zinc-400 hover:text-zinc-600"
              title="Collapse assistant"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 12H4" />
              </svg>
            </button>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-zinc-50/70">
          {historyLoading ? (
            <div className="text-center text-zinc-500 text-sm">Loading history...</div>
          ) : (
            <>
              {history?.messages.map((msg) => (
                <MessageBubble key={msg.id} message={msg} />
              ))}

              {chatMutation.isPending && (
                <div className="flex items-center gap-2 text-zinc-500 text-sm">
                  <div className="animate-spin w-4 h-4 border-2 border-sky-500 border-t-transparent rounded-full" />
                  Thinking...
                </div>
              )}

              {chatMutation.data && !chatMutation.isPending && (
                <ToolCallBadges toolCalls={chatMutation.data.tool_calls} />
              )}

              <div ref={messagesEndRef} />
            </>
          )}
        </div>

        <form onSubmit={handleSubmit} className="p-4 border-t border-zinc-200/90 bg-white/85 space-y-2">
          <div className="flex gap-2">
            <input
              type="text"
              value={message}
              onChange={(event) => setMessage(event.target.value)}
              placeholder="Ask for help with this subsection..."
              className="flex-1 px-3 py-2 text-sm border border-zinc-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-sky-500"
              disabled={chatMutation.isPending}
            />
            <button
              type="submit"
              disabled={chatMutation.isPending || !message.trim()}
              className="px-4 py-2 text-sm bg-sky-600 text-white rounded-lg hover:bg-sky-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Send
            </button>
          </div>

          {selectedSectionId && (
            <div className="flex items-center gap-2 min-h-[20px]">
              <span className="text-xs text-zinc-500">Context:</span>
              {selectedSubsectionId && selectedSubsectionInfo ? (
                <span className="inline-flex items-center gap-1 text-xs bg-sky-100 text-sky-700 px-2 py-0.5 rounded-full">
                  <span className="font-bold">{selectedSubsectionInfo.label}</span>
                  {selectedSubsectionInfo.title && (
                    <span className="text-sky-600 truncate max-w-[180px]">{selectedSubsectionInfo.title}</span>
                  )}
                </span>
              ) : (
                <span className="text-xs text-zinc-500">Section selected</span>
              )}
            </div>
          )}
        </form>
      </div>
    </div>
  );
}

function MessageBubble({ message }: { message: ConversationMessage }) {
  const isUser = message.role === 'user';

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div
        className={`max-w-[90%] rounded-lg px-3 py-2 ${
          isUser
            ? 'bg-sky-600 text-white'
            : 'bg-zinc-100 text-zinc-800'
        }`}
      >
        {isUser ? (
          <p className="text-sm whitespace-pre-wrap">{message.content}</p>
        ) : (
          <Markdown content={message.content} className="text-sm" />
        )}
      </div>
    </div>
  );
}

function ToolCallBadges({ toolCalls }: { toolCalls: ToolCallLog[] }) {
  if (!toolCalls || toolCalls.length === 0) return null;

  return (
    <div className="flex flex-wrap gap-1">
      {toolCalls.map((toolCall, index) => (
        <span
          key={index}
          className={`px-2 py-0.5 text-xs rounded ${
            toolCall.error
              ? 'bg-red-100 text-red-700'
              : 'bg-green-100 text-green-700'
          }`}
          title={toolCall.error || JSON.stringify(toolCall.result, null, 2)}
        >
          {toolCall.tool}
        </span>
      ))}
    </div>
  );
}
