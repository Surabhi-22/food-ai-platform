"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { format } from "date-fns";
import {
  Area,
  AreaChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import {
  Download,
  Loader2,
  RefreshCw,
  TrendingUp,
} from "lucide-react";
import { toast } from "sonner";

import { api } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Skeleton } from "@/components/ui/skeleton";
import type { ForecastListResponse, ForecastItem, ForecastDateGroup } from "@/types/api";

/* ------------------------------------------------------------------ */
/* Types                                                               */
/* ------------------------------------------------------------------ */

interface ChartDataPoint {
  date: string;
  predicted: number;
  lower: number;
  upper: number;
  range: [number, number];
}

/* ------------------------------------------------------------------ */
/* Cluster badge styling                                               */
/* ------------------------------------------------------------------ */

const clusterConfig: Record<string, { label: string; variant: "default" | "success" | "warning" | "destructive" }> = {
  HIGH_DEMAND: { label: "HIGH", variant: "destructive" },
  MEDIUM_DEMAND: { label: "MED", variant: "warning" },
  LOW_DEMAND: { label: "LOW", variant: "success" },
};

/* ------------------------------------------------------------------ */
/* Component                                                           */
/* ------------------------------------------------------------------ */

export default function ForecastsPage() {
  const [isLoading, setIsLoading] = useState(true);
  const [isRetraining, setIsRetraining] = useState(false);
  const [forecastData, setForecastData] = useState<ForecastListResponse | null>(null);
  const [isExporting, setIsExporting] = useState(false);
  const forecastRef = useRef<HTMLDivElement>(null);

  /* ── Fetch Forecasts ──────────────────────────────────────────── */

  const generateDemoData = useCallback(() => {
    const items = [
      { name: "Chicken Biryani", category: "Biryani", cluster: "HIGH_DEMAND" },
      { name: "Paneer Butter Masala", category: "Main Course", cluster: "HIGH_DEMAND" },
      { name: "Masala Dosa", category: "Main Course", cluster: "MEDIUM_DEMAND" },
      { name: "Veg Thali", category: "Combos", cluster: "HIGH_DEMAND" },
      { name: "Cold Coffee", category: "Beverages", cluster: "MEDIUM_DEMAND" },
      { name: "Gulab Jamun", category: "Desserts", cluster: "LOW_DEMAND" },
      { name: "Butter Naan", category: "Bread", cluster: "MEDIUM_DEMAND" },
      { name: "Manchurian", category: "Starters", cluster: "MEDIUM_DEMAND" },
    ];

    const dates = ["2026-05-12", "2026-05-13", "2026-05-14"];
    const groups: ForecastDateGroup[] = dates.map((date) => ({
      forecast_date: date,
      items: items.map((item) => {
        const base = item.cluster === "HIGH_DEMAND" ? 40 : item.cluster === "MEDIUM_DEMAND" ? 25 : 12;
        const qty = base + Math.floor(Math.random() * 15);
        const price = 80 + Math.floor(Math.random() * 200);
        const revenue = qty * price;
        return {
          menu_item_id: crypto.randomUUID(),
          menu_item_name: item.name,
          category: item.category,
          forecast_date: date,
          predicted_quantity: qty,
          predicted_revenue: revenue,
          predicted_profit: Math.round(revenue * 0.65),
          confidence_lower: Math.round(qty * 0.82),
          confidence_upper: Math.round(qty * 1.18),
          cluster_label: item.cluster,
          inventory_required: Math.round(qty * 1.15),
          model_version: "ensemble_v1",
        };
      }),
      total_predicted_quantity: 0,
      total_predicted_revenue: 0,
    }));

    // Recalculate totals
    groups.forEach((g) => {
      g.total_predicted_quantity = g.items.reduce((s, i) => s + i.predicted_quantity, 0);
      g.total_predicted_revenue = g.items.reduce((s, i) => s + i.predicted_revenue, 0);
    });

    setForecastData({
      vendor_id: "demo",
      forecast_groups: groups,
      total_items: groups.reduce((s, g) => s + g.items.length, 0),
      date_range_start: dates[0],
      date_range_end: dates[dates.length - 1],
      cached: false,
    });
  }, []);

  const fetchForecasts = useCallback(async () => {
    setIsLoading(true);
    try {
      const res = await api.get<ForecastListResponse>("/forecasts?days=3");
      setForecastData(res.data);
    } catch {
      // Generate demo data
      generateDemoData();
    } finally {
      setIsLoading(false);
    }
  }, [generateDemoData]);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    fetchForecasts();
  }, [fetchForecasts]);

  /* ── Retrain ──────────────────────────────────────────────────── */

  const handleRetrain = async () => {
    setIsRetraining(true);
    try {
      await api.post("/ml/retrain");
      toast.success("ML pipeline retraining started. Results will appear in a few minutes.");
    } catch {
      toast.error("Failed to trigger retraining");
    } finally {
      setIsRetraining(false);
    }
  };

  /* ── PDF Export ────────────────────────────────────────────────── */

  const exportPDF = async () => {
    if (!forecastRef.current) return;
    setIsExporting(true);

    try {
      const html2canvas = (await import("html2canvas")).default;
      const { jsPDF } = await import("jspdf");

      const canvas = await html2canvas(forecastRef.current, {
        scale: 2,
        backgroundColor: "#ffffff",
        logging: false,
      });

      const imgData = canvas.toDataURL("image/png");
      const pdf = new jsPDF("p", "mm", "a4");
      const pdfWidth = pdf.internal.pageSize.getWidth();
      const pdfHeight = (canvas.height * pdfWidth) / canvas.width;

      pdf.setFontSize(18);
      pdf.text("Demand Forecast Report", 14, 20);
      pdf.setFontSize(10);
      pdf.setTextColor(100);
      pdf.text(`Generated: ${format(new Date(), "PPpp")}`, 14, 28);

      pdf.addImage(imgData, "PNG", 0, 35, pdfWidth, Math.min(pdfHeight, 240));
      pdf.save(`forecast_${format(new Date(), "yyyyMMdd")}.pdf`);
      toast.success("Forecast PDF downloaded");
    } catch (err) {
      console.error("PDF export error:", err);
      toast.error("Failed to export PDF");
    } finally {
      setIsExporting(false);
    }
  };

  /* ── Build chart data ─────────────────────────────────────────── */

  const chartData: ChartDataPoint[] = [];
  const allItems: (ForecastItem & { dayLabel: string })[] = [];

  if (forecastData) {
    forecastData.forecast_groups.forEach((group) => {
      const dateLabel = format(new Date(group.forecast_date + "T00:00:00"), "EEE, MMM dd");
      chartData.push({
        date: dateLabel,
        predicted: group.total_predicted_quantity,
        lower: group.items.reduce((s, i) => s + i.confidence_lower, 0),
        upper: group.items.reduce((s, i) => s + i.confidence_upper, 0),
        range: [
          group.items.reduce((s, i) => s + i.confidence_lower, 0),
          group.items.reduce((s, i) => s + i.confidence_upper, 0),
        ],
      });

      group.items.forEach((item) => {
        allItems.push({ ...item, dayLabel: dateLabel });
      });
    });
  }

  // Deduplicate items across days for the table
  const uniqueItems = new Map<string, ForecastItem & { day1: number; day2: number; day3: number; totalRevenue: number; totalInventory: number }>();
  if (forecastData) {
    forecastData.forecast_groups.forEach((group, dayIndex) => {
      group.items.forEach((item) => {
        const existing = uniqueItems.get(item.menu_item_name);
        if (existing) {
          if (dayIndex === 0) existing.day1 = item.predicted_quantity;
          if (dayIndex === 1) existing.day2 = item.predicted_quantity;
          if (dayIndex === 2) existing.day3 = item.predicted_quantity;
          existing.totalRevenue += item.predicted_revenue;
          existing.totalInventory += item.inventory_required;
        } else {
          uniqueItems.set(item.menu_item_name, {
            ...item,
            day1: dayIndex === 0 ? item.predicted_quantity : 0,
            day2: dayIndex === 1 ? item.predicted_quantity : 0,
            day3: dayIndex === 2 ? item.predicted_quantity : 0,
            totalRevenue: item.predicted_revenue,
            totalInventory: item.inventory_required,
          });
        }
      });
    });
  }
  const tableItems = Array.from(uniqueItems.values()).sort((a, b) => b.totalRevenue - a.totalRevenue);

  /* ── Render ───────────────────────────────────────────────────── */

  if (isLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-10 w-48" />
        <Skeleton className="h-[350px]" />
        <Skeleton className="h-[400px]" />
      </div>
    );
  }

  return (
    <div className="space-y-6" ref={forecastRef}>
      {/* Header */}
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-3xl font-bold tracking-tight">Demand Forecasts</h2>
          <p className="text-muted-foreground">
            ML-powered 3-day demand predictions with confidence intervals.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={handleRetrain} disabled={isRetraining}>
            {isRetraining ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <RefreshCw className="mr-2 h-4 w-4" />}
            Retrain Model
          </Button>
          <Button variant="outline" size="sm" onClick={exportPDF} disabled={isExporting}>
            {isExporting ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Download className="mr-2 h-4 w-4" />}
            Export PDF
          </Button>
        </div>
      </div>

      {/* Summary Cards */}
      {forecastData && (
        <div className="grid gap-4 md:grid-cols-3">
          {forecastData.forecast_groups.map((group) => (
            <Card key={group.forecast_date}>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">
                  {format(new Date(group.forecast_date + "T00:00:00"), "EEEE, MMM dd")}
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  ₹{Math.round(group.total_predicted_revenue).toLocaleString()}
                </div>
                <p className="text-sm text-muted-foreground mt-1">
                  {Math.round(group.total_predicted_quantity)} predicted units
                </p>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Area Chart with Confidence Interval */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <TrendingUp className="h-5 w-5 text-primary" />
            3-Day Demand Forecast
          </CardTitle>
          <CardDescription>
            Predicted total units with confidence interval shading (±1.96σ).
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="h-[350px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={chartData} margin={{ top: 10, right: 30, bottom: 20, left: 20 }}>
                <defs>
                  <linearGradient id="colorPredicted" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#4F46E5" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#4F46E5" stopOpacity={0.05} />
                  </linearGradient>
                  <linearGradient id="colorConfidence" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#10B981" stopOpacity={0.15} />
                    <stop offset="95%" stopColor="#10B981" stopOpacity={0.02} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e5e7eb" />
                <XAxis
                  dataKey="date"
                  axisLine={false}
                  tickLine={false}
                  tick={{ fill: "#6b7280", fontSize: 12 }}
                  dy={10}
                />
                <YAxis
                  axisLine={false}
                  tickLine={false}
                  tick={{ fill: "#6b7280", fontSize: 12 }}
                  label={{ value: "Units", angle: -90, position: "insideLeft", style: { fill: "#6b7280", fontSize: 12 } }}
                />
                <Tooltip
                  contentStyle={{ borderRadius: "8px", border: "none", boxShadow: "0 4px 6px -1px rgb(0 0 0 / 0.1)" }}
                  formatter={(value: number | [number, number], name: string) => {
                    if (name === "Confidence Range" && Array.isArray(value)) {
                      return [`${value[0]} – ${value[1]}`, name];
                    }
                    return [Math.round(value as number), name];
                  }}
                />
                <Legend verticalAlign="top" height={36} />
                <Area
                  dataKey="range"
                  name="Confidence Range"
                  stroke="none"
                  fill="url(#colorConfidence)"
                  fillOpacity={1}
                />
                <Area
                  dataKey="predicted"
                  name="Predicted Demand"
                  stroke="#4F46E5"
                  strokeWidth={3}
                  fill="url(#colorPredicted)"
                  dot={{ r: 5, fill: "#4F46E5", stroke: "#fff", strokeWidth: 2 }}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </CardContent>
      </Card>

      {/* Forecast Table */}
      <Card>
        <CardHeader>
          <CardTitle>Item-Level Forecast Details</CardTitle>
          <CardDescription>Predicted demand, revenue, cluster label, and required inventory per item.</CardDescription>
        </CardHeader>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Item</TableHead>
                <TableHead>Category</TableHead>
                <TableHead>Cluster</TableHead>
                <TableHead className="text-right">Day 1</TableHead>
                <TableHead className="text-right">Day 2</TableHead>
                <TableHead className="text-right">Day 3</TableHead>
                <TableHead className="text-right">Revenue</TableHead>
                <TableHead className="text-right">Inventory</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {tableItems.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={8} className="text-center py-8 text-muted-foreground">
                    No forecast data available. Trigger a model retrain to generate predictions.
                  </TableCell>
                </TableRow>
              ) : (
                tableItems.map((item) => {
                  const cfg = clusterConfig[item.cluster_label] || clusterConfig.MEDIUM_DEMAND;
                  return (
                    <TableRow key={item.menu_item_name}>
                      <TableCell className="font-medium">{item.menu_item_name}</TableCell>
                      <TableCell className="text-muted-foreground">{item.category}</TableCell>
                      <TableCell>
                        <Badge variant={cfg.variant} className="text-xs">
                          {cfg.label}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-right font-mono">{Math.round(item.day1)}</TableCell>
                      <TableCell className="text-right font-mono">{Math.round(item.day2)}</TableCell>
                      <TableCell className="text-right font-mono">{Math.round(item.day3)}</TableCell>
                      <TableCell className="text-right font-semibold">
                        ₹{Math.round(item.totalRevenue).toLocaleString()}
                      </TableCell>
                      <TableCell className="text-right font-mono">
                        {Math.round(item.totalInventory)} units
                      </TableCell>
                    </TableRow>
                  );
                })
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}
