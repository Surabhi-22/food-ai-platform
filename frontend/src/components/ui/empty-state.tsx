import React from "react";
import { LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";

interface EmptyStateProps {
  icon: LucideIcon;
  title: string;
  description: string;
  action?: React.ReactNode;
  className?: string;
  minHeight?: string;
}

export function EmptyState({
  icon: Icon,
  title,
  description,
  action,
  className,
  minHeight = "min-h-[400px]",
}: EmptyStateProps) {
  return (
    <div
      className={cn(
        "glass-card flex flex-col items-center justify-center p-8 text-center animate-in fade-in zoom-in-95 duration-500",
        minHeight,
        className
      )}
    >
      <div className="flex h-20 w-20 items-center justify-center rounded-3xl bg-gradient-to-br from-primary/20 via-primary/10 to-transparent shadow-inner ring-1 ring-primary/20 mb-6">
        <Icon className="h-10 w-10 text-primary" strokeWidth={1.5} />
      </div>
      <h3 className="text-xl font-bold tracking-tight text-foreground mb-2">
        {title}
      </h3>
      <p className="text-sm font-medium text-muted-foreground max-w-sm mb-6">
        {description}
      </p>
      {action && <div>{action}</div>}
    </div>
  );
}
