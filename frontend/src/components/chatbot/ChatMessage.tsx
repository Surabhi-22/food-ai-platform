"use client";

import { format } from "date-fns";
import { Bot, User } from "lucide-react";

import { cn } from "@/lib/utils";
import TypingIndicator from "./TypingIndicator";
import SourceChips, { type SourceReference } from "./SourceChips";

export interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: string;
  sources?: SourceReference[];
  isStreaming?: boolean;
}

interface ChatMessageProps {
  message: Message;
}

export default function ChatMessage({ message }: ChatMessageProps) {
  const isUser = message.role === "user";
  const isStreaming = message.isStreaming && message.content === "";

  return (
    <div
      className={cn(
        "flex gap-3 w-full",
        isUser ? "justify-end" : "justify-start"
      )}
    >
      {/* Avatar for assistant */}
      {!isUser && (
        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-500 via-purple-500 to-pink-500 shadow-md ring-1 ring-white/20">
          <Bot className="h-5 w-5 text-white" />
        </div>
      )}

      {/* Message bubble */}
      <div
        className={cn(
          "max-w-[85%] md:max-w-[75%] rounded-2xl px-5 py-4 shadow-sm transition-all",
          isUser
            ? "bg-gradient-to-br from-primary to-indigo-600 text-primary-foreground rounded-br-sm shadow-primary/20"
            : "glass-card text-foreground rounded-bl-sm border-primary/10 shadow-lg"
        )}
      >
        {/* Typing indicator */}
        {isStreaming ? (
          <TypingIndicator />
        ) : (
          <>
            {/* Message text with markdown-like rendering */}
            <div
              className={cn(
                "text-[15px] leading-relaxed whitespace-pre-wrap break-words",
                isUser ? "text-primary-foreground font-medium" : "text-foreground/90 font-medium"
              )}
            >
              {message.content}
            </div>

            {/* Sources (assistant only) */}
            {!isUser && message.sources && message.sources.length > 0 && (
              <SourceChips sources={message.sources} />
            )}
          </>
        )}

        {/* Timestamp */}
        <p
          className={cn(
            "mt-2 text-[10px] font-bold uppercase tracking-wider",
            isUser ? "text-primary-foreground/70 text-right" : "text-muted-foreground"
          )}
        >
          {format(new Date(message.timestamp), "h:mm a")}
        </p>
      </div>

      {/* Avatar for user */}
      {isUser && (
        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-primary/10 shadow-sm border border-primary/20">
          <User className="h-5 w-5 text-primary" />
        </div>
      )}
    </div>
  );
}
