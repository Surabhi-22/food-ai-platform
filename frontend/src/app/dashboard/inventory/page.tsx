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
} from "lucide-react";
import { toast } from "sonner";

import { InventoryService } from "@/services/inventory.service";
import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
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
      toast.error("Failed to load inventory data");
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
        <Skeleton className="h-10 w-48" />
        <Skeleton className="h-24" />
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {[...Array(6)].map((_, i) => <Skeleton key={i} className="h-48" />)}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-3xl font-bold tracking-tight">Inventory</h2>
          <p className="text-muted-foreground">
            Compare current stock with ML-predicted demand. Update levels to optimize.
          </p>
        </div>
        <Button onClick={handleBulkSave} disabled={isSaving}>
          {isSaving ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Save className="mr-2 h-4 w-4" />}
          Save All Changes
        </Button>
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
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-3">
              <div className="rounded-lg bg-red-100 p-2">
                <TrendingDown className="h-5 w-5 text-red-600" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Deficit Items</p>
                <p className="text-2xl font-bold text-red-600">{deficitCount}</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-3">
              <div className="rounded-lg bg-amber-100 p-2">
                <Package className="h-5 w-5 text-amber-600" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Adequate</p>
                <p className="text-2xl font-bold text-amber-600">{adequateCount}</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-3">
              <div className="rounded-lg bg-emerald-100 p-2">
                <TrendingUp className="h-5 w-5 text-emerald-600" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Surplus</p>
                <p className="text-2xl font-bold text-emerald-600">{surplusCount}</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-3">
              <div className="rounded-lg bg-indigo-100 p-2">
                <Check className="h-5 w-5 text-indigo-600" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Total Items</p>
                <p className="text-2xl font-bold">{items.length}</p>
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
                  "transition-all",
                  isDeficit && "border-red-300 bg-red-50/50",
                  isSurplus && "border-emerald-200"
                )}
              >
                <CardHeader className="pb-3">
                  <div className="flex items-start justify-between">
                    <div>
                      <CardTitle className="text-base">{item.name}</CardTitle>
                      <CardDescription>{item.category}</CardDescription>
                    </div>
                    <Badge
                      variant={isDeficit ? "destructive" : isSurplus ? "success" : "warning"}
                    >
                      {isDeficit ? "DEFICIT" : isSurplus ? "SURPLUS" : "OK"}
                    </Badge>
                  </div>
                </CardHeader>
                <CardContent className="space-y-4">
                  {/* Current Stock Input */}
                  <div className="space-y-1.5 flex items-center gap-2">
                    <div className="flex-1">
                      <Label htmlFor={`stock-${item.id}`} className="text-xs text-muted-foreground">
                        Current Stock
                      </Label>
                      <div className="relative">
                        <Input
                          id={`stock-${item.id}`}
                          type="number"
                          min={0}
                          value={stockInputs[item.id] ?? item.currentStock}
                          onChange={(e) => updateStockInput(item.id, Number(e.target.value))}
                          className={cn("font-mono pr-12", isDeficit && "border-red-300 focus-visible:ring-red-400")}
                        />
                        <div className="absolute right-3 top-1/2 -translate-y-1/2 text-sm text-muted-foreground pointer-events-none">
                          {item.unit}
                        </div>
                      </div>
                    </div>
                  </div>

                  <Separator />

                  {/* Metrics */}
                  <div className="grid grid-cols-2 gap-3 text-sm">
                    <div>
                      <p className="text-muted-foreground text-xs">Predicted Demand</p>
                      <p className="font-semibold">{item.predictedDemand} {item.unit}</p>
                    </div>
                    <div>
                      <p className="text-muted-foreground text-xs">Surplus / Deficit</p>
                      <p className={cn("font-semibold", item.surplusDeficit >= 0 ? "text-emerald-600" : "text-red-600")}>
                        {item.surplusDeficit >= 0 ? "+" : ""}{item.surplusDeficit} {item.unit}
                      </p>
                    </div>
                  </div>

                  {/* Reorder Suggestion */}
                  {isDeficit && item.reorderQty > 0 && (
                    <div className="rounded-md bg-red-100 px-3 py-2 text-sm">
                      <p className="font-medium text-red-800">
                        ⚠️ Reorder <strong>{item.reorderQty} {item.unit}</strong>
                      </p>
                      <p className="text-red-700 text-xs mt-0.5">
                        Includes 15% safety buffer above predicted demand.
                      </p>
                    </div>
                  )}

                  {isSurplus && (
                    <div className="rounded-md bg-emerald-50 px-3 py-2 text-sm">
                      <p className="text-emerald-700">
                        ✓ {item.surplusDeficit} {item.unit} above predicted demand. Consider reducing prep.
                      </p>
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
