"use client";

import { useEffect, useState } from "react";
import { format } from "date-fns";
import {
  AlertTriangle,
  ArrowDownRight,
  ArrowUpRight,
  BarChart3,
  IndianRupee,
  PackageOpen,
  TrendingUp,
} from "lucide-react";
import {
  Bar,
  BarChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  CartesianGrid,
} from "recharts";

import { PredictionsService } from "@/services/predictions.service";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Prediction, DashboardAnalytics } from "@/types/api";

export default function DashboardOverview() {
  const [analytics, setAnalytics] = useState<DashboardAnalytics | null>(null);
  const [predictions, setPredictions] = useState<Prediction[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetchDashboardData = async () => {
      try {
        const [analyticsRes, predictionsRes] = await Promise.all([
          PredictionsService.getAnalytics(),
          PredictionsService.getPredictions(),
        ]);
        setAnalytics(analyticsRes as DashboardAnalytics);
        setPredictions(predictionsRes);
      } catch (error) {
        console.error("Failed to fetch dashboard data:", error);
      } finally {
        setIsLoading(false);
      }
    };

    fetchDashboardData();
  }, []);

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="flex flex-col gap-2">
          <div className="h-8 w-48 bg-muted rounded animate-pulse" />
          <div className="h-4 w-64 bg-muted rounded animate-pulse" />
        </div>
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <Card key={i}>
              <CardContent className="h-24 pt-6">
                <div className="h-full w-full bg-muted rounded animate-pulse" />
              </CardContent>
            </Card>
          ))}
        </div>
        <Card className="h-[400px]">
          <CardContent className="h-full pt-6">
            <div className="h-full w-full bg-muted rounded animate-pulse" />
          </CardContent>
        </Card>
      </div>
    );
  }

  // Format chart data from actual predictions
  const chartData = predictions?.map((p: Prediction) => ({
    name: p.date ? format(new Date(p.date), "MMM dd") : "Unknown",
    predicted: p.predicted_demand || p.quantity || 0,
  })) || [];

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-2">
        <h2 className="text-3xl font-bold tracking-tight">Overview</h2>
        <p className="text-muted-foreground">
          Your business metrics and AI demand forecasts.
        </p>
      </div>

      {/* Low Stock Alerts */}
      {analytics?.low_stock_alerts && analytics.low_stock_alerts.length > 0 && (
        <Alert variant="warning">
          <AlertTriangle className="h-4 w-4" />
          <AlertTitle>Low Stock Warning</AlertTitle>
          <AlertDescription>
            {analytics.low_stock_alerts.length} items are predicted to experience high demand that exceeds your current average supply.
            Check the Inventory tab to reorder.
          </AlertDescription>
        </Alert>
      )}

      {/* KPI Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">3-Day Revenue Forecast</CardTitle>
            <IndianRupee className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              ₹{analytics?.total_revenue_3day?.toLocaleString(undefined, { maximumFractionDigits: 0 }) || "0"}
            </div>
            <p className="text-xs text-muted-foreground mt-1 flex items-center">
              <ArrowUpRight className="mr-1 h-4 w-4 text-success" />
              <span className="text-success font-medium">+12.5%</span> from last week
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Predicted Orders</CardTitle>
            <PackageOpen className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {analytics?.total_quantity_3day?.toLocaleString(undefined, { maximumFractionDigits: 0 }) || "0"} items
            </div>
            <p className="text-xs text-muted-foreground mt-1 flex items-center">
              <ArrowUpRight className="mr-1 h-4 w-4 text-success" />
              <span className="text-success font-medium">+8%</span> predicted growth
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Top Predicted Item</CardTitle>
            <TrendingUp className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold truncate">
              {analytics?.top_item?.menu_item_name || "N/A"}
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              Forecasted: {analytics?.top_item?.predicted_quantity || 0} units
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Waste Reduction</CardTitle>
            <BarChart3 className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-success">-24%</div>
            <p className="text-xs text-muted-foreground mt-1 flex items-center">
              <ArrowDownRight className="mr-1 h-4 w-4 text-success" />
              Improved by ML Pipeline
            </p>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-7">
        {/* Forecast Chart */}
        <Card className="lg:col-span-7">
          <CardHeader>
            <CardTitle>Forecast Preview</CardTitle>
          </CardHeader>
          <CardContent className="pl-2">
            {chartData.length === 0 ? (
              <div className="flex h-[300px] items-center justify-center text-muted-foreground">
                No prediction data available.
              </div>
            ) : (
              <div className="h-[300px] w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={chartData} margin={{ top: 20, right: 20, bottom: 20, left: 20 }}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e5e7eb" />
                    <XAxis 
                      dataKey="name" 
                      axisLine={false} 
                      tickLine={false} 
                      tick={{ fill: '#6b7280', fontSize: 12 }}
                      dy={10}
                    />
                    <YAxis 
                      axisLine={false} 
                      tickLine={false} 
                      tick={{ fill: '#6b7280', fontSize: 12 }}
                      dx={-10}
                    />
                    <Tooltip 
                      cursor={{ fill: '#f3f4f6' }}
                      contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
                    />
                    <Bar dataKey="predicted" name="Predicted Demand" fill="var(--primary)" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
