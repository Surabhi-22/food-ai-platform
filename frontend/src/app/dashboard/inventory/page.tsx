"use client";

import { useCallback, useEffect, useState } from "react";
import {
  AlertTriangle,
  Check,
  Loader2,
  Package,
  Save,
  TrendingDown,
  TrendingUp,
  Carrot,
  Wheat,
  Fish,
  Beef,
  Coffee,
  Milk,
  Apple,
} from "lucide-react";
import { toast } from "sonner";

import { InventoryService } from "@/services/inventory.service";
import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { PremiumSkeleton } from "@/components/ui/premium-skeleton";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import { PageHeader } from "@/components/ui/page-header";
import { InventoryItem as ApiInventoryItem, PaginatedResponse } from "@/types/api";

/* ------------------------------------------------------------------ */
/* Types                                                               */
/* ------------------------------------------------------------------ */

interface DashboardInventoryItem {
  id: string;
  name: string;
  category: string;
  unit: string;
  currentStock: number;
  predictedDemand: number;
  surplusDeficit: number;
  reorderQty: number;
  status: "surplus" | "deficit" | "adequate";
  clusterLabel: string;
}

/* ------------------------------------------------------------------ */
/* Component                                                           */
/* ------------------------------------------------------------------ */

const getCategoryIcon = (category: string) => {
  const cat = category.toLowerCase();
  if (cat.includes("dairy") || cat.includes("milk")) return <Milk className="h-6 w-6" />;
  if (cat.includes("meat") || cat.includes("chicken")) return <Beef className="h-6 w-6" />;
  if (cat.includes("veg") || cat.includes("produce")) return <Carrot className="h-6 w-6" />;
  if (cat.includes("fruit")) return <Apple className="h-6 w-6" />;
  if (cat.includes("grain") || cat.includes("flour")) return <Wheat className="h-6 w-6" />;
  if (cat.includes("seafood") || cat.includes("fish")) return <Fish className="h-6 w-6" />;
  if (cat.includes("beverage")) return <Coffee className="h-6 w-6" />;
  return <Package className="h-6 w-6" />;
};

export default function InventoryPage() {
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [items, setItems] = useState<DashboardInventoryItem[]>([]);
  const [stockInputs, setStockInputs] = useState<Record<string, number>>({});
  const [deficitCount, setDeficitCount] = useState(0);

  /* ── Fetch & Build Inventory ──────────────────────────────────── */

  const fetchInventory = useCallback(async () => {
    setIsLoading(true);
    try {
      const res = await InventoryService.getInventory() as { items?: any[]; total_items_analyzed?: number };
      // /analytics/inventory returns { items: [...], analysis_date, total_items_analyzed }
      const data: any[] = res?.items || [];

      const invItems: DashboardInventoryItem[] = data.map((item: any) => {
        const predicted = Number(item.predicted_demand ?? 0);
        const actual = Number(item.actual_sales ?? 0);
        const diff = actual - predicted;

        return {
          id: item.menu_item_id || Math.random().toString(),
          name: item.item_name || "Unknown Item",
          category: item.category || "Uncategorised",
          unit: "units",
          currentStock: actual,
          predictedDemand: predicted,
          surplusDeficit: diff,
          reorderQty: diff < 0 ? Math.abs(diff) + Math.round(predicted * 0.15) : 0,
          status: diff < 0 ? "deficit" : diff < predicted * 0.2 ? "adequate" : "surplus",
          clusterLabel: diff < 0 ? "HIGH_DEMAND" : "MEDIUM_DEMAND",
        };
      });

      setItems(invItems);
      setDeficitCount(invItems.filter((i) => i.status === "deficit").length);

      const inputs: Record<string, number> = {};
      invItems.forEach((item) => {
        inputs[item.id] = item.currentStock;
      });
      setStockInputs(inputs);
    } catch {
      console.debug("Failed to load inventory data — backend unreachable");
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    fetchInventory();
  }, [fetchInventory]);

  /* ── Stock input handler ──────────────────────────────────────── */

  const updateStockInput = (itemId: string, value: number) => {
    setStockInputs((prev) => ({ ...prev, [itemId]: value }));

    // Recalculate status for this item
    setItems((prev) =>
      prev.map((item) => {
        if (item.id !== itemId) return item;
        const diff = value - item.predictedDemand;
        return {
          ...item,
          currentStock: value,
          surplusDeficit: diff,
          reorderQty: diff < 0 ? Math.abs(diff) + Math.round(item.predictedDemand * 0.15) : 0,
          status: diff < 0 ? "deficit" : diff < item.predictedDemand * 0.2 ? "adequate" : "surplus",
        };
      })
    );
  };

  /* ── Bulk Save ────────────────────────────────────────────────── */

  const handleBulkSave = async () => {
    setIsSaving(true);
    try {
      // Create bulk updates
      const updates = items.map((item) => {
        if (stockInputs[item.id] !== item.currentStock) {
          return InventoryService.updateStock(item.id, stockInputs[item.id]);
        }
        return null;
      }).filter(Boolean);

      if (updates.length > 0) {
        await Promise.all(updates);
      }
      toast.success("Stock levels updated successfully");
      
      // Refresh inventory from server
      await fetchInventory();
    } catch {
      toast.error("Failed to update stock levels");
    } finally {
      setIsSaving(false);
    }
  };

  /* ── Summary stats ────────────────────────────────────────────── */

  const surplusCount = items.filter((i) => i.status === "surplus").length;
  const adequateCount = items.filter((i) => i.status === "adequate").length;
  const totalReorderQty = items.reduce((s, i) => s + i.reorderQty, 0);

  /* ── Render ───────────────────────────────────────────────────── */

  if (isLoading) {
    return (
      <div className="space-y-6">
        <PremiumSkeleton className="h-10 w-48" />
        <PremiumSkeleton className="h-24" />
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {[...Array(6)].map((_, i) => <PremiumSkeleton key={i} className="h-48" />)}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6 pb-8 animate-in fade-in duration-500">
      {/* Sticky Header */}
      <div className="sticky top-0 z-10 p-4 rounded-xl shadow-sm mb-6 border border-primary/10 backdrop-blur-xl bg-background/80">
        <PageHeader
          title="Inventory"
          description="Compare current stock with ML-predicted demand."
          actions={
            <Button onClick={handleBulkSave} disabled={isSaving} className="shadow-lg hover:-translate-y-0.5 transition-transform">
              {isSaving ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Save className="mr-2 h-4 w-4" />}
              Save Changes
            </Button>
          }
        />
      </div>

      {/* Deficit Alert */}
      {deficitCount > 0 && (
        <Alert variant="warning">
          <AlertTriangle className="h-4 w-4" />
          <AlertTitle>Stock Deficit Detected</AlertTitle>
          <AlertDescription>
            {deficitCount} item{deficitCount > 1 ? "s" : ""} have predicted demand exceeding current stock.
            Total reorder quantity needed: <strong>{totalReorderQty} units</strong>.
          </AlertDescription>
        </Alert>
      )}

      {/* Summary Cards */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card className="hover:-translate-y-1 transition-transform">
          <CardContent className="pt-6">
            <div className="flex items-center gap-3">
              <div className="rounded-lg bg-red-100 p-2 shadow-sm">
                <TrendingDown className="h-5 w-5 text-red-600" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground font-medium">Deficit Items</p>
                <p className="text-2xl font-black text-red-600">{deficitCount}</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card className="hover:-translate-y-1 transition-transform">
          <CardContent className="pt-6">
            <div className="flex items-center gap-3">
              <div className="rounded-lg bg-amber-100 p-2 shadow-sm">
                <Package className="h-5 w-5 text-amber-600" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground font-medium">Adequate</p>
                <p className="text-2xl font-black text-amber-600">{adequateCount}</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card className="hover:-translate-y-1 transition-transform">
          <CardContent className="pt-6">
            <div className="flex items-center gap-3">
              <div className="rounded-lg bg-emerald-100 p-2 shadow-sm">
                <TrendingUp className="h-5 w-5 text-emerald-600" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground font-medium">Surplus</p>
                <p className="text-2xl font-black text-emerald-600">{surplusCount}</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card className="hover:-translate-y-1 transition-transform">
          <CardContent className="pt-6">
            <div className="flex items-center gap-3">
              <div className="rounded-lg bg-indigo-100 p-2 shadow-sm">
                <Check className="h-5 w-5 text-indigo-600" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground font-medium">Total Items</p>
                <p className="text-2xl font-black">{items.length}</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Inventory Cards Grid */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {items
          .sort((a, b) => {
            const order = { deficit: 0, adequate: 1, surplus: 2 };
            return order[a.status] - order[b.status];
          })
          .map((item) => {
            const isDeficit = item.status === "deficit";
            const isSurplus = item.status === "surplus";

            return (
              <Card
                key={item.id}
                className={cn(
                  "transition-all duration-300 hover:shadow-xl hover:-translate-y-1 overflow-hidden relative",
                  isDeficit && "border-red-500/30 bg-red-500/5",
                  isSurplus && "border-emerald-500/20"
                )}
              >
                {/* Visual Indicator Line at top */}
                <div className={cn(
                  "absolute top-0 left-0 right-0 h-1",
                  isDeficit ? "bg-red-500" : isSurplus ? "bg-emerald-500" : "bg-primary/20"
                )} />
                
                <CardHeader className="pb-3 pt-5">
                  <div className="flex items-start justify-between">
                    <div className="flex items-center gap-3">
                      <div className={cn(
                        "p-2 rounded-lg shrink-0 shadow-sm",
                        isDeficit ? "bg-red-100 text-red-600" : isSurplus ? "bg-emerald-100 text-emerald-600" : "bg-primary/10 text-primary"
                      )}>
                        {getCategoryIcon(item.category)}
                      </div>
                      <div>
                        <CardTitle className="text-base truncate" title={item.name}>{item.name}</CardTitle>
                        <CardDescription className="text-xs font-bold uppercase tracking-wider mt-0.5">{item.category}</CardDescription>
                      </div>
                    </div>
                    <Badge
                      variant={isDeficit ? "destructive" : isSurplus ? "success" : "secondary"}
                      className={cn("shrink-0 shadow-sm", isDeficit ? "animate-pulse" : "")}
                    >
                      {isDeficit ? "DEFICIT" : isSurplus ? "SURPLUS" : "OK"}
                    </Badge>
                  </div>
                </CardHeader>
                <CardContent className="space-y-5">
                  {/* Stock vs Demand Progress Bar */}
                  <div className="space-y-2">
                    <div className="flex justify-between text-xs font-medium">
                      <span className="text-muted-foreground">Stock Level</span>
                      <span className={cn(isDeficit ? "text-red-500 font-bold" : "text-foreground font-bold")}>
                        {Math.round((item.currentStock / Math.max(item.predictedDemand, 1)) * 100)}% of Demand
                      </span>
                    </div>
                    <div className="h-2 w-full bg-muted/50 overflow-hidden rounded-full shadow-inner">
                      <div 
                        className={cn(
                          "h-full transition-all duration-1000 ease-out",
                          isDeficit ? "bg-red-500" : isSurplus ? "bg-emerald-500" : "bg-primary"
                        )}
                        style={{ width: `${Math.min((item.currentStock / Math.max(item.predictedDemand, 1)) * 100, 100)}%` }}
                      />
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-4 text-sm bg-background/50 p-3 rounded-lg border border-primary/5">
                    <div>
                      <p className="text-muted-foreground text-[10px] uppercase font-bold tracking-wider">Demand</p>
                      <p className="font-black text-lg">{item.predictedDemand} <span className="text-xs font-normal text-muted-foreground">{item.unit}</span></p>
                    </div>
                    <div>
                      <p className="text-muted-foreground text-[10px] uppercase font-bold tracking-wider">Variance</p>
                      <p className={cn("font-black text-lg", item.surplusDeficit >= 0 ? "text-emerald-500" : "text-red-500")}>
                        {item.surplusDeficit >= 0 ? "+" : ""}{item.surplusDeficit} <span className="text-xs font-normal opacity-70">{item.unit}</span>
                      </p>
                    </div>
                  </div>

                  {/* Current Stock Input */}
                  <div className="pt-2">
                    <Label htmlFor={`stock-${item.id}`} className="text-xs font-bold text-muted-foreground uppercase tracking-wider">
                      Update Stock
                    </Label>
                    <div className="relative mt-1.5">
                      <Input
                        id={`stock-${item.id}`}
                        type="number"
                        min={0}
                        value={stockInputs[item.id] ?? item.currentStock}
                        onChange={(e) => updateStockInput(item.id, Number(e.target.value))}
                        className={cn(
                          "font-mono text-lg pr-14 h-10 shadow-sm transition-colors",
                          isDeficit && "border-red-300 focus-visible:ring-red-400 bg-red-50/30"
                        )}
                      />
                      <div className="absolute right-3 top-1/2 -translate-y-1/2 text-xs font-medium text-muted-foreground pointer-events-none uppercase">
                        {item.unit}
                      </div>
                    </div>
                  </div>

                  {/* Reorder Suggestion */}
                  {isDeficit && item.reorderQty > 0 && (
                    <div className="rounded-lg bg-red-500/10 border border-red-500/20 px-4 py-3 text-sm flex items-start gap-3 mt-4">
                      <AlertTriangle className="h-5 w-5 text-red-500 shrink-0 mt-0.5" />
                      <div>
                        <p className="font-bold text-red-700 dark:text-red-400">
                          Reorder {item.reorderQty} {item.unit}
                        </p>
                        <p className="text-red-600/80 dark:text-red-400/80 text-xs mt-1 font-medium">
                          Includes 15% safety buffer.
                        </p>
                      </div>
                    </div>
                  )}

                  {isSurplus && (
                    <div className="rounded-lg bg-emerald-500/10 border border-emerald-500/20 px-4 py-3 text-sm flex items-start gap-3 mt-4">
                      <Check className="h-5 w-5 text-emerald-500 shrink-0 mt-0.5" />
                      <div>
                        <p className="font-bold text-emerald-700 dark:text-emerald-400">
                          Stock Optimal
                        </p>
                        <p className="text-emerald-600/80 dark:text-emerald-400/80 text-xs mt-1 font-medium">
                          {item.surplusDeficit} {item.unit} over demand.
                        </p>
                      </div>
                    </div>
                  )}
                </CardContent>
              </Card>
            );
          })}
      </div>
    </div>
  );
}
