import type { ChatMessage as ChatMessageType } from '../types';
import { ChatMessageRole } from '../types';

interface ChatMessageProps {
  message: ChatMessageType;
  characterName: string;
}

const ChatMessageComponent = ({ message, characterName }: ChatMessageProps) => {
  const isUser = message.role === ChatMessageRole.USER;

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-5`}>
      <div className={`max-w-[82%] ${isUser ? 'items-end' : 'items-start'} flex flex-col`}>
        {/* Sender label */}
        <span className={`font-mono text-[9px] tracking-widest uppercase mb-1.5 ${
          isUser ? 'text-dim text-right' : 'text-gold-dim'
        }`}>
          {isUser ? 'You' : characterName}
        </span>

        {/* Bubble */}
        <div className={[
          'px-4 py-3 border',
          isUser
            ? 'bg-overlay border-border text-ink'
            : 'bg-surface border-gold-dim text-ink',
        ].join(' ')}>
          <p className="font-body text-sm leading-relaxed whitespace-pre-wrap">
            {message.content}
          </p>
        </div>

        {/* Timestamp */}
        <span className="font-mono text-[9px] text-faint mt-1">
          {new Date(message.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
          {!isUser && message.generation_time_ms && (
            <span className="ml-2">{(message.generation_time_ms / 1000).toFixed(1)}s</span>
          )}
        </span>
      </div>
    </div>
  );
};

export default ChatMessageComponent;
