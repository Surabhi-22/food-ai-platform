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
        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-indigo-500 to-purple-600 shadow-sm">
          <Bot className="h-4 w-4 text-white" />
        </div>
      )}

      {/* Message bubble */}
      <div
        className={cn(
          "max-w-[75%] rounded-2xl px-4 py-3 shadow-sm",
          isUser
            ? "bg-gradient-to-r from-indigo-600 to-indigo-500 text-white rounded-br-md"
            : "bg-white border border-slate-100 text-slate-800 rounded-bl-md"
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
                "text-sm leading-relaxed whitespace-pre-wrap break-words",
                isUser ? "text-white" : "text-slate-700"
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
            "mt-1.5 text-[10px]",
            isUser ? "text-indigo-200 text-right" : "text-slate-400"
          )}
        >
          {format(new Date(message.timestamp), "h:mm a")}
        </p>
      </div>

      {/* Avatar for user */}
      {isUser && (
        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-indigo-100 shadow-sm">
          <User className="h-4 w-4 text-indigo-600" />
        </div>
      )}
    </div>
  );
}
