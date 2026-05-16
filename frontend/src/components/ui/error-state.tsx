import React from "react";
import { AlertTriangle, RefreshCcw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface ErrorStateProps {
  title?: string;
  description?: string;
  onRetry?: () => void;
  className?: string;
  minHeight?: string;
}

export function ErrorState({
  title = "Something went wrong",
  description = "We couldn't load this data. Please try again.",
  onRetry,
  className,
  minHeight = "min-h-[300px]",
}: ErrorStateProps) {
  return (
    <div
      className={cn(
        "glass-card flex flex-col items-center justify-center p-8 text-center border-destructive/20 bg-destructive/5 animate-in fade-in duration-500",
        minHeight,
        className
      )}
    >
      <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-destructive/10 text-destructive mb-4 ring-1 ring-destructive/20">
        <AlertTriangle className="h-8 w-8" strokeWidth={2} />
      </div>
      <h3 className="text-lg font-bold tracking-tight text-destructive mb-2">
        {title}
      </h3>
      <p className="text-sm font-medium text-destructive/80 max-w-xs mb-6">
        {description}
      </p>
      {onRetry && (
        <Button
          variant="outline"
          onClick={onRetry}
          className="border-destructive/30 text-destructive hover:bg-destructive/10 hover:text-destructive transition-colors"
        >
          <RefreshCcw className="mr-2 h-4 w-4" />
          Try Again
        </Button>
      )}
    </div>
  );
}
