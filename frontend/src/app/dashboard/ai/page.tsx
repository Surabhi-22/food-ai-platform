"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { format } from "date-fns";
import {
  Bot,
  MessageSquarePlus,
  Send,
  Sparkles,
  Trash2,
} from "lucide-react";
import { toast } from "sonner";

import { ChatService } from "@/services/chat.service";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import ChatMessage, { type Message } from "@/components/chatbot/ChatMessage";
import type { SourceReference } from "@/components/chatbot/SourceChips";

/* ------------------------------------------------------------------ */
/* Constants                                                           */
/* ------------------------------------------------------------------ */

const SUGGESTED_PROMPTS = [
  "What should I prepare for tomorrow?",
  "Which items are overstocked this week?",
  "What was my best revenue day last month?",
  "How much did I earn on biryani last week?",
  "What is my predicted profit for next 3 days?",
  "Which items should I remove from the menu?",
];

interface ChatSessionSummary {
  id: string;
  preview: string;
  created_at: string;
  message_count: number;
}

/* ------------------------------------------------------------------ */
/* Component                                                           */
/* ------------------------------------------------------------------ */

export default function AIChatPage() {
  // Messages state
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputValue, setInputValue] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);

  // Chat sessions
  const [sessions, setSessions] = useState<ChatSessionSummary[]>([]);
  const [isLoadingSessions, setIsLoadingSessions] = useState(true);

  // Refs
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const abortRef = useRef<AbortController | null>(null);

  /* ── Auto-scroll ──────────────────────────────────────────────── */

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

  /* ── Load Sessions ────────────────────────────────────────────── */

  const loadSessions = useCallback(async () => {
    setIsLoadingSessions(true);
    try {
      const res = await api.get("/chat/sessions");
      const data = res.data?.sessions || [];
      setSessions(
        data.map((s: any) => ({
          id: s.id,
          preview: s.preview || "New conversation",
          created_at: s.created_at || s.updated_at,
          message_count: s.message_count || 0,
        }))
      );
    } catch {
      // Silently fail — sessions panel is optional
    } finally {
      setIsLoadingSessions(false);
    }
  }, []);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    loadSessions();
  }, [loadSessions]);

  /* ── Load Specific Session ────────────────────────────────────── */

  const loadSession = async (id: string) => {
    try {
      const res = await api.get(`/chat/history?session_id=${id}`);
      const data = res.data;

      const loadedMessages: Message[] = (data.messages || []).map((m: any, i: number) => ({
        id: `${id}-${i}`,
        role: m.role,
        content: m.content,
        timestamp: m.timestamp || new Date().toISOString(),
        sources: m.sources || [],
      }));

      setMessages(loadedMessages);
      setSessionId(id);
    } catch (err: unknown) {
      toast.error("Failed to load chat session");
    }
  };

  /* ── New Chat ─────────────────────────────────────────────────── */

  const startNewChat = () => {
    setMessages([]);
    setSessionId(null);
    setInputValue("");
    inputRef.current?.focus();
  };

  const sendMessage = async (content?: string) => {
    const text = (content || inputValue).trim();
    if (!text || isStreaming) return;

    setInputValue("");

    // Add user message
    const userMsg: Message = {
      id: `user-${crypto.randomUUID()}`,
      role: "user",
      content: text,
      timestamp: new Date().toISOString(),
    };

    // Add placeholder assistant message (loading/typing state)
    const assistantMsgId = `assistant-${crypto.randomUUID()}`;
    const assistantMsg: Message = {
      id: assistantMsgId,
      role: "assistant",
      content: "",
      timestamp: new Date().toISOString(),
      isStreaming: true,
      sources: [],
    };

    setMessages((prev) => [...prev, userMsg, assistantMsg]);
    setIsStreaming(true);

    try {
      // Send question to backend
      const reply = await ChatService.sendMessage(text);
      
      setMessages((prev) =>
        prev.map((m) =>
          m.id === assistantMsgId
            ? {
                ...m,
                content: reply.response || reply.answer || reply.reply || reply.content || "I'm sorry, I couldn't understand that.",
                isStreaming: false,
                sources: reply.sources || [],
              }
            : m
        )
      );
      
      // Update session if it's the first message
      if (!sessionId) {
        setSessionId(`session-${crypto.randomUUID()}`);
        loadSessions();
      }
    } catch (err: unknown) {
      setMessages((prev) =>
        prev.map((m) =>
          m.id === assistantMsgId
            ? {
                ...m,
                content: "I'm sorry, I couldn't process your request right now. Please check your backend connection and try again.",
                isStreaming: false,
              }
            : m
        )
      );
      toast.error("Failed to connect to AI assistant");
    } finally {
      setIsStreaming(false);
    }
  };

  /* ── Clear History ────────────────────────────────────────────── */

  const clearHistory = async () => {
    try {
      if (sessionId) {
        await api.delete(`/chat/history?session_id=${sessionId}`);
      }
      startNewChat();
      loadSessions();
      toast.success("Chat history cleared");
    } catch {
      toast.error("Failed to clear history");
    }
  };

  /* ── Keyboard shortcuts ───────────────────────────────────────── */

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  /* ── Render ───────────────────────────────────────────────────── */

  return (
    <div className="flex h-[calc(100vh-8rem)] gap-0 rounded-xl border bg-white shadow-sm overflow-hidden">
      {/* ── Left Sidebar ─────────────────────────────────────────── */}
      <div className="hidden md:flex md:w-[30%] flex-col border-r bg-slate-50/50">
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b">
          <div className="flex items-center gap-2">
            <Sparkles className="h-4 w-4 text-indigo-500" />
            <span className="text-sm font-semibold">AI Assistant</span>
          </div>
          <Button variant="ghost" size="icon" className="h-8 w-8" onClick={startNewChat}>
            <MessageSquarePlus className="h-4 w-4" />
          </Button>
        </div>

        {/* Suggested Prompts */}
        <div className="px-4 py-3 border-b">
          <p className="text-xs font-medium text-muted-foreground mb-2">Suggested prompts</p>
          <div className="flex flex-col gap-1.5">
            {SUGGESTED_PROMPTS.map((prompt) => (
              <button
                key={prompt}
                onClick={() => sendMessage(prompt)}
                disabled={isStreaming}
                className="text-left text-xs px-3 py-2 rounded-lg bg-white border border-slate-200 text-slate-600 hover:border-indigo-300 hover:bg-indigo-50 hover:text-indigo-700 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {prompt}
              </button>
            ))}
          </div>
        </div>

        {/* Chat Sessions */}
        <div className="flex-1 overflow-y-auto px-4 py-3">
          <p className="text-xs font-medium text-muted-foreground mb-2">History</p>
          {isLoadingSessions ? (
            <div className="space-y-2">
              {[...Array(3)].map((_, i) => <Skeleton key={i} className="h-12 w-full" />)}
            </div>
          ) : sessions.length === 0 ? (
            <p className="text-xs text-muted-foreground py-4 text-center">No chat history yet</p>
          ) : (
            <div className="space-y-1">
              {sessions.map((session) => (
                <button
                  key={session.id}
                  onClick={() => loadSession(session.id)}
                  className={cn(
                    "w-full text-left rounded-lg px-3 py-2.5 text-xs transition-colors hover:bg-white hover:shadow-sm",
                    sessionId === session.id
                      ? "bg-white shadow-sm border border-indigo-200"
                      : "border border-transparent"
                  )}
                >
                  <p className="font-medium text-slate-700 truncate">
                    {session.preview}
                  </p>
                  <p className="text-[10px] text-slate-400 mt-0.5">
                    {format(new Date(session.created_at), "MMM dd, h:mm a")} · {session.message_count} messages
                  </p>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Clear button */}
        {sessionId && (
          <div className="px-4 py-3 border-t">
            <Button
              variant="ghost"
              size="sm"
              className="w-full text-muted-foreground hover:text-destructive"
              onClick={clearHistory}
            >
              <Trash2 className="mr-2 h-3 w-3" />
              Clear this chat
            </Button>
          </div>
        )}
      </div>

      {/* ── Right Panel (Chat Area) ──────────────────────────────── */}
      <div className="flex flex-1 flex-col">
        {/* Messages Area */}
        <div className="flex-1 overflow-y-auto px-4 lg:px-6 py-4 space-y-4">
          {messages.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full text-center gap-4">
              <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-indigo-500 to-purple-600 shadow-lg">
                <Bot className="h-8 w-8 text-white" />
              </div>
              <div>
                <h3 className="text-lg font-semibold text-slate-800">FoodAI Assistant</h3>
                <p className="text-sm text-muted-foreground mt-1 max-w-sm">
                  Ask me anything about your business — sales trends, demand forecasts, menu performance, and inventory insights. I use your real data to answer.
                </p>
              </div>
              {/* Mobile suggested prompts */}
              <div className="md:hidden grid grid-cols-1 gap-2 w-full max-w-sm mt-4">
                {SUGGESTED_PROMPTS.slice(0, 4).map((prompt) => (
                  <button
                    key={prompt}
                    onClick={() => sendMessage(prompt)}
                    className="text-xs px-3 py-2 rounded-lg bg-slate-50 border text-slate-600 hover:border-indigo-300 hover:bg-indigo-50 transition-all text-left"
                  >
                    {prompt}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            messages.map((msg) => <ChatMessage key={msg.id} message={msg} />)
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Input Bar */}
        <div className="border-t bg-white px-4 lg:px-6 py-3">
          <div className="flex items-end gap-2">
            <div className="relative flex-1">
              <textarea
                ref={inputRef}
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Ask about your business data..."
                disabled={isStreaming}
                rows={1}
                className={cn(
                  "w-full resize-none rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 pr-12 text-sm",
                  "placeholder:text-muted-foreground",
                  "focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-400",
                  "disabled:opacity-50 disabled:cursor-not-allowed",
                  "transition-all"
                )}
                style={{ minHeight: "44px", maxHeight: "120px" }}
                onInput={(e) => {
                  const target = e.target as HTMLTextAreaElement;
                  target.style.height = "auto";
                  target.style.height = `${Math.min(target.scrollHeight, 120)}px`;
                }}
              />
            </div>
            <Button
              onClick={() => sendMessage()}
              disabled={!inputValue.trim() || isStreaming}
              size="icon"
              className="h-11 w-11 rounded-xl bg-indigo-600 hover:bg-indigo-700 shrink-0"
            >
              <Send className="h-4 w-4" />
            </Button>
          </div>
          <p className="text-[10px] text-muted-foreground mt-1.5 text-center">
            Press Enter to send · Shift+Enter for new line · Powered by GPT-4o + RAG
          </p>
        </div>
      </div>
    </div>
  );
}
