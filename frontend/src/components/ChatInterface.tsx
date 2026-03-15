import React, { useState, useEffect, useRef } from 'react';
import type { Character, ChatSession, ChatMessage as ChatMessageType } from '../types';
import {
  sendChatMessage,
  getChatMessages,
  closeChatSession,
  regenerateChatResponse,
  exportChatSession,
} from '../services/api';
import ChatMessageComponent from './ChatMessage';
import { X, Download, RotateCcw, Send } from 'lucide-react';

interface ChatInterfaceProps {
  character: Character;
  session: ChatSession;
  onClose: () => void;
  onSessionUpdate: (session: ChatSession) => void;
}

const ChatInterface = ({ character, session, onClose, onSessionUpdate }: ChatInterfaceProps) => {
  const [messages, setMessages] = useState<ChatMessageType[]>([]);
  const [inputText, setInputText] = useState('');
  const [isSending, setIsSending] = useState(false);
  const [isLoadingHistory, setIsLoadingHistory] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    const loadMessages = async () => {
      setIsLoadingHistory(true);
      const response = await getChatMessages(session.id, 50, 0);
      if (response.data) setMessages(response.data.messages);
      setIsLoadingHistory(false);
    };
    loadMessages();
  }, [session.id]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isSending]);

  useEffect(() => { inputRef.current?.focus(); }, []);

  const handleSend = async () => {
    const text = inputText.trim();
    if (!text || isSending || !session.is_active) return;

    setInputText('');
    setIsSending(true);
    setError(null);

    const response = await sendChatMessage(session.id, text);
    if (response.data) {
      setMessages((prev) => [...prev, response.data!.user_message, response.data!.character_response]);
    } else {
      setError(response.error?.message || 'Failed to send message');
      setInputText(text);
    }
    setIsSending(false);
    inputRef.current?.focus();
  };

  const handleRegenerate = async () => {
    if (isSending || messages.length === 0) return;
    setIsSending(true);
    setError(null);
    const response = await regenerateChatResponse(session.id);
    if (response.data) {
      setMessages((prev) => {
        const next = [...prev];
        if (next.length > 0 && next[next.length - 1].role === 'character') {
          next[next.length - 1] = response.data!;
        } else {
          next.push(response.data!);
        }
        return next;
      });
    } else {
      setError(response.error?.message || 'Failed to regenerate');
    }
    setIsSending(false);
  };

  const handleCloseSession = async () => {
    const response = await closeChatSession(session.id);
    if (response.data) onSessionUpdate(response.data);
    onClose();
  };

  const handleExport = async () => {
    const response = await exportChatSession(session.id);
    if (response.data) {
      const blob = new Blob([response.data], { type: 'text/markdown' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `chat-${character.name.replace(/\s+/g, '-').toLowerCase()}-${session.character_year_context}.md`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } else {
      setError(response.error?.message || 'Failed to export');
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend(); }
  };

  const lastIsCharacter = messages.length > 0 && messages[messages.length - 1].role === 'character';

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70" onClick={onClose}>
      <div
        className="bg-parchment border border-border w-full max-w-2xl mx-4 flex flex-col corner-brackets"
        style={{ height: '80vh' }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* ── Header ── */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-border shrink-0">
          <div>
            <p className="rubric-label mb-1">§ Correspondence</p>
            <h2 className="font-display text-xl text-gold leading-tight">{character.name}</h2>
            <p className="font-mono text-[10px] text-dim mt-0.5">
              {session.profile_id
                ? `Profile: ${session.character_year_context}`
                : `Speaking from year ${session.character_year_context}`}
            </p>
          </div>

          <div className="flex items-center gap-1">
            {!session.is_active && (
              <span className="font-mono text-[9px] tracking-widest uppercase text-faint border border-border px-2 py-1 mr-2">
                Closed
              </span>
            )}
            <HeaderBtn onClick={handleExport} title="Export as markdown" icon={<Download size={13} />} />
            {session.is_active && (
              <HeaderBtn onClick={handleCloseSession} title="End session" icon={<X size={13} />} danger />
            )}
            <HeaderBtn onClick={onClose} title="Dismiss" icon={<X size={14} />} />
          </div>
        </div>

        {/* ── Messages ── */}
        <div className="flex-1 overflow-y-auto px-5 py-5">
          {isLoadingHistory ? (
            <div className="flex items-center justify-center h-full">
              <p className="font-mono text-xs text-faint tracking-widest uppercase animate-pulse">
                Loading correspondence…
              </p>
            </div>
          ) : messages.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full text-center">
              <p className="font-display text-lg text-dim mb-1">
                Initiate correspondence with {character.name}
              </p>
              <p className="font-caption text-sm text-faint italic">
                They will respond as if living in {session.character_year_context}
              </p>
            </div>
          ) : (
            messages.map((msg) => (
              <ChatMessageComponent key={msg.id} message={msg} characterName={character.name} />
            ))
          )}

          {/* Typing indicator */}
          {isSending && (
            <div className="flex justify-start mb-4">
              <div className="bg-surface border border-gold-dim px-4 py-3">
                <p className="font-mono text-[9px] tracking-widest uppercase text-gold-dim mb-2">{character.name}</p>
                <div className="flex gap-1.5">
                  {[0, 150, 300].map((delay) => (
                    <span
                      key={delay}
                      className="w-1.5 h-1.5 bg-gold-dim rounded-none animate-bounce"
                      style={{ animationDelay: `${delay}ms` }}
                    />
                  ))}
                </div>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* ── Error ── */}
        {error && (
          <div className="px-5 pb-2 shrink-0">
            <div className="border border-rubric-dim px-3 py-2">
              <p className="font-mono text-[10px] text-rubric">{error}</p>
            </div>
          </div>
        )}

        {/* ── Input area ── */}
        <div className="px-5 py-4 border-t border-border shrink-0">
          <div className="flex items-end gap-2">
            {lastIsCharacter && session.is_active && (
              <button
                onClick={handleRegenerate}
                disabled={isSending}
                className="text-dim hover:text-gold-dim transition-colors disabled:opacity-40 cursor-pointer pb-2"
                title="Regenerate last response"
              >
                <RotateCcw size={13} />
              </button>
            )}

            <textarea
              ref={inputRef}
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={!session.is_active || isSending}
              placeholder={session.is_active ? `Message ${character.name}…` : 'Session closed'}
              className={[
                'flex-1 bg-vellum border border-border text-ink font-body text-sm',
                'px-3 py-2 resize-none',
                'placeholder:text-faint placeholder:font-mono placeholder:text-[10px] placeholder:tracking-widest',
                'focus:outline-none focus:border-gold-dim',
                'disabled:opacity-40 disabled:cursor-not-allowed',
                'transition-colors duration-150',
              ].join(' ')}
              rows={1}
              style={{ minHeight: '42px', maxHeight: '120px' }}
              onInput={(e) => {
                const t = e.target as HTMLTextAreaElement;
                t.style.height = '42px';
                t.style.height = Math.min(t.scrollHeight, 120) + 'px';
              }}
            />

            <button
              onClick={handleSend}
              disabled={!inputText.trim() || isSending || !session.is_active}
              className="text-gold-dim hover:text-gold transition-colors disabled:opacity-30 disabled:cursor-not-allowed cursor-pointer pb-2"
              title="Send"
            >
              <Send size={15} />
            </button>
          </div>
          <p className="font-mono text-[9px] text-faint tracking-widest mt-2">
            Enter to send · Shift+Enter for new line
          </p>
        </div>
      </div>
    </div>
  );
};

function HeaderBtn({
  onClick, title, icon, danger,
}: {
  onClick: () => void;
  title: string;
  icon: React.ReactNode;
  danger?: boolean;
}) {
  return (
    <button
      onClick={onClick}
      title={title}
      className={`p-2 transition-colors cursor-pointer ${
        danger ? 'text-dim hover:text-rubric' : 'text-dim hover:text-ink'
      }`}
    >
      {icon}
    </button>
  );
}

export default ChatInterface;
