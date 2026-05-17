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

/* ── Lightweight Markdown → HTML ──────────────────────────────────────── */

function renderMarkdown(text: string): string {
  // Escape HTML first
  let html = text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");

  // Tables: detect lines starting with |
  html = html.replace(
    /((?:^\|.+\|$\n?)+)/gm,
    (tableBlock) => {
      const rows = tableBlock.trim().split("\n").filter(Boolean);
      let table = '<table style="border-collapse:collapse;width:100%;margin:8px 0;font-size:13px;">';
      rows.forEach((row, i) => {
        // Skip separator rows like |---|---|
        if (/^\|[\s-:|]+\|$/.test(row)) return;
        const cells = row.split("|").filter((_, idx, arr) => idx > 0 && idx < arr.length - 1);
        const tag = i === 0 ? "th" : "td";
        const bgStyle = i === 0 ? 'background:#f1f5f9;font-weight:600;' : (i % 2 === 0 ? 'background:#f8fafc;' : '');
        table += "<tr>";
        cells.forEach((cell) => {
          table += `<${tag} style="border:1px solid #e2e8f0;padding:6px 10px;text-align:left;${bgStyle}">${cell.trim()}</${tag}>`;
        });
        table += "</tr>";
      });
      table += "</table>";
      return table;
    }
  );

  // Bold: **text**
  html = html.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");

  // Bullet points: lines starting with • or -
  html = html.replace(/^[•\-]\s+(.+)$/gm, '<div style="display:flex;gap:6px;margin:2px 0;"><span>•</span><span>$1</span></div>');

  // Numbered lists: lines starting with 1. 2. etc
  html = html.replace(/^(\d+)\.\s+(.+)$/gm, '<div style="display:flex;gap:6px;margin:2px 0;"><span style="font-weight:600;">$1.</span><span>$2</span></div>');

  // Headings (inline): lines starting with ## or ###  
  html = html.replace(/^###\s+(.+)$/gm, '<div style="font-size:14px;font-weight:700;margin:10px 0 4px;">$1</div>');
  html = html.replace(/^##\s+(.+)$/gm, '<div style="font-size:15px;font-weight:700;margin:12px 0 4px;">$1</div>');

  // Line breaks
  html = html.replace(/\n/g, "<br/>");

  // Clean up excessive <br/> after block elements
  html = html.replace(/(<\/table>)<br\/>/g, "$1");
  html = html.replace(/(<\/div>)<br\/>/g, "$1");

  return html;
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
                "text-[15px] leading-relaxed break-words prose-sm",
                isUser ? "text-primary-foreground font-medium" : "text-foreground/90 font-medium"
              )}
              dangerouslySetInnerHTML={{ __html: renderMarkdown(message.content) }}
            />

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
