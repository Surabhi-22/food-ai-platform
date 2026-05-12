"use client";

import { useState } from "react";
import { ChevronDown, ChevronUp, FileText } from "lucide-react";
import { cn } from "@/lib/utils";

export interface SourceReference {
  content: string;
  metadata?: {
    date?: string;
    item_name?: string;
    data_type?: string;
  };
  score?: number;
}

interface SourceChipsProps {
  sources: SourceReference[];
}

export default function SourceChips({ sources }: SourceChipsProps) {
  const [isOpen, setIsOpen] = useState(false);

  if (!sources || sources.length === 0) return null;

  return (
    <div className="mt-3 border-t border-slate-100 pt-2">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors"
      >
        <FileText className="h-3 w-3" />
        <span>{sources.length} source{sources.length > 1 ? "s" : ""} used</span>
        {isOpen ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
      </button>

      {isOpen && (
        <div className="mt-2 space-y-1.5 animate-in slide-in-from-top-1 duration-200">
          {sources.map((source, i) => (
            <div
              key={i}
              className="rounded-md border border-slate-100 bg-slate-50 px-3 py-2 text-xs text-muted-foreground"
            >
              <div className="flex items-center gap-2 mb-1">
                {source.metadata?.data_type && (
                  <span
                    className={cn(
                      "inline-flex items-center rounded-full px-1.5 py-0.5 text-[10px] font-medium",
                      source.metadata.data_type === "order"
                        ? "bg-blue-100 text-blue-700"
                        : source.metadata.data_type === "forecast"
                        ? "bg-purple-100 text-purple-700"
                        : "bg-green-100 text-green-700"
                    )}
                  >
                    {source.metadata.data_type}
                  </span>
                )}
                {source.metadata?.date && (
                  <span className="text-[10px] text-slate-400">{source.metadata.date}</span>
                )}
                {source.score != null && (
                  <span className="text-[10px] text-slate-400 ml-auto">
                    {(source.score * 100).toFixed(0)}% match
                  </span>
                )}
              </div>
              <p className="line-clamp-2">{source.content}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
