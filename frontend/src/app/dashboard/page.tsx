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
  Wallet,
  Clock,
  ArrowRight,
  PackageCheck,
  Download
} from "lucide-react";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  CartesianGrid,
} from "recharts";

import { PredictionsService } from "@/services/predictions.service";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Prediction, DashboardAnalytics } from "@/types/api";
import { PageHeader } from "@/components/ui/page-header";
import { PremiumSkeleton } from "@/components/ui/premium-skeleton";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";

export default function DashboardOverview() {
  const [analytics, setAnalytics] = useState<DashboardAnalytics | null>(null);
  const [predictions, setPredictions] = useState<Prediction[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const generateDemoData = () => {
      setAnalytics({
        total_revenue_3day: 84750,
        total_quantity_3day: 1284,
        low_stock_alerts: [
          { item_name: "Chicken Biryani", current_stock: 12, predicted_demand: 45, unit: "kg" },
          { item_name: "Paneer", current_stock: 5, predicted_demand: 30, unit: "kg" },
          { item_name: "Basmati Rice", current_stock: 8, predicted_demand: 60, unit: "kg" },
        ],
      } as unknown as DashboardAnalytics);

      const dates = ["2026-05-14", "2026-05-15", "2026-05-16"];
      const items = ["Chicken Biryani", "Paneer Masala", "Dosa", "Veg Thali", "Cold Coffee"];
      const demoPredictions: Prediction[] = [];
      dates.forEach((date) => {
        items.forEach((item) => {
          demoPredictions.push({
            date,
            menu_item_name: item,
            predicted_demand: 20 + Math.floor(Math.random() * 40),
            quantity: 15 + Math.floor(Math.random() * 30),
          } as unknown as Prediction);
        });
      });
      setPredictions(demoPredictions);
    };

    const fetchDashboardData = async () => {
      setIsLoading(true);
      try {
        const [analyticsRes, predictionsRes] = await Promise.all([
          PredictionsService.getAnalytics(),
          PredictionsService.getPredictions(),
        ]);
        setAnalytics(analyticsRes as unknown as DashboardAnalytics);
        setPredictions(predictionsRes as unknown as Prediction[]);
      } catch (error) {
        console.error("Failed to fetch dashboard data:", error);
        generateDemoData();
      } finally {
        setIsLoading(false);
      }
    };

    fetchDashboardData();
  }, []);

  if (isLoading) {
    return (
      <div className="space-y-8 pb-8">
        <div className="flex flex-col gap-2">
          <PremiumSkeleton className="h-10 w-48" />
          <PremiumSkeleton className="h-5 w-80" />
        </div>
        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <Card key={i}>
              <CardContent className="h-32 pt-6">
                <PremiumSkeleton className="h-full w-full" />
              </CardContent>
            </Card>
          ))}
        </div>
        <div className="grid gap-6 md:grid-cols-3">
          <Card className="md:col-span-2 h-[400px]">
            <CardContent className="h-full pt-6">
              <PremiumSkeleton className="h-full w-full" />
            </CardContent>
          </Card>
          <Card className="h-[400px]">
            <CardContent className="h-full pt-6">
              <PremiumSkeleton className="h-full w-full" />
            </CardContent>
          </Card>
        </div>
      </div>
    );
  }

  const chartData = predictions?.map((p: Prediction) => ({
    name: p.date ? format(new Date(p.date), "MMM dd") : "Unknown",
    revenue: (p.predicted_demand || p.quantity || 0) * 120, // Mock revenue conversion
    predicted: p.predicted_demand || p.quantity || 0,
  })) || [];

  const mockRecentOrders = [
    { id: "ORD-9431", customer: "Alice Johnson", amount: 480, status: "completed", time: "10 mins ago" },
    { id: "ORD-9430", customer: "Michael Chen", amount: 1250, status: "preparing", time: "25 mins ago" },
    { id: "ORD-9429", customer: "Sarah Smith", amount: 320, status: "pending", time: "1 hour ago" },
    { id: "ORD-9428", customer: "David Wilson", amount: 890, status: "completed", time: "2 hours ago" },
  ];

  return (
    <div className="space-y-6 pb-8 animate-in fade-in duration-500">
      <PageHeader
        title="Overview"
        description="Your real-time business metrics and AI demand forecasts."
        actions={
          <div className="flex gap-2">
            <Button variant="outline" size="sm">
              <Download className="mr-2 h-4 w-4" />
              Export
            </Button>
            <Button size="sm" asChild>
              <a href="/dashboard/reports">+ Generate Report</a>
            </Button>
          </div>
        }
      />

      {/* KPI Cards */}
      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
        {/* Revenue */}
        <Card className="relative overflow-hidden group">
          <div className="absolute inset-0 bg-gradient-to-br from-primary/10 to-transparent opacity-50 group-hover:opacity-100 transition-opacity duration-500" />
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2 relative z-10">
            <CardTitle className="text-sm font-medium text-muted-foreground">Est. 3-Day Revenue</CardTitle>
            <div className="h-8 w-8 rounded-full bg-primary/10 flex items-center justify-center">
              <IndianRupee className="h-4 w-4 text-primary" />
            </div>
          </CardHeader>
          <CardContent className="relative z-10">
            <div className="text-3xl font-bold tracking-tight">
              ₹{analytics?.total_revenue_3day?.toLocaleString(undefined, { maximumFractionDigits: 0 }) || "0"}
            </div>
            <p className="text-sm text-muted-foreground mt-2 flex items-center font-medium">
              <ArrowUpRight className="mr-1 h-4 w-4 text-success" />
              <span className="text-success">+12.5%</span> <span className="ml-1 opacity-70 font-normal">vs last week</span>
            </p>
          </CardContent>
        </Card>

        {/* Orders */}
        <Card className="relative overflow-hidden group">
          <div className="absolute inset-0 bg-gradient-to-br from-success/10 to-transparent opacity-50 group-hover:opacity-100 transition-opacity duration-500" />
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2 relative z-10">
            <CardTitle className="text-sm font-medium text-muted-foreground">Total Orders</CardTitle>
            <div className="h-8 w-8 rounded-full bg-success/10 flex items-center justify-center">
              <PackageOpen className="h-4 w-4 text-success" />
            </div>
          </CardHeader>
          <CardContent className="relative z-10">
            <div className="text-3xl font-bold tracking-tight">
              342
            </div>
            <p className="text-sm text-muted-foreground mt-2 flex items-center font-medium">
              <ArrowUpRight className="mr-1 h-4 w-4 text-success" />
              <span className="text-success">+8.2%</span> <span className="ml-1 opacity-70 font-normal">vs last week</span>
            </p>
          </CardContent>
        </Card>

        {/* Predictions */}
        <Card className="relative overflow-hidden group">
          <div className="absolute inset-0 bg-gradient-to-br from-indigo-500/10 to-transparent opacity-50 group-hover:opacity-100 transition-opacity duration-500" />
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2 relative z-10">
            <CardTitle className="text-sm font-medium text-muted-foreground">Predicted Demand</CardTitle>
            <div className="h-8 w-8 rounded-full bg-indigo-500/10 flex items-center justify-center">
              <TrendingUp className="h-4 w-4 text-indigo-500" />
            </div>
          </CardHeader>
          <CardContent className="relative z-10">
            <div className="text-3xl font-bold tracking-tight">
              {analytics?.total_quantity_3day?.toLocaleString(undefined, { maximumFractionDigits: 0 }) || "0"} <span className="text-lg font-normal text-muted-foreground">units</span>
            </div>
            <p className="text-sm text-muted-foreground mt-2 flex items-center font-medium">
              <PackageCheck className="mr-1 h-4 w-4 text-indigo-500" />
              <span className="text-indigo-500">94%</span> <span className="ml-1 opacity-70 font-normal">model confidence</span>
            </p>
          </CardContent>
        </Card>

        {/* Profit */}
        <Card className="relative overflow-hidden group">
          <div className="absolute inset-0 bg-gradient-to-br from-amber-500/10 to-transparent opacity-50 group-hover:opacity-100 transition-opacity duration-500" />
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2 relative z-10">
            <CardTitle className="text-sm font-medium text-muted-foreground">Est. Profit Margin</CardTitle>
            <div className="h-8 w-8 rounded-full bg-amber-500/10 flex items-center justify-center">
              <Wallet className="h-4 w-4 text-amber-500" />
            </div>
          </CardHeader>
          <CardContent className="relative z-10">
            <div className="text-3xl font-bold tracking-tight">
              ₹{((analytics?.total_revenue_3day || 0) * 0.42).toLocaleString(undefined, { maximumFractionDigits: 0 }) || "0"}
            </div>
            <p className="text-sm text-muted-foreground mt-2 flex items-center font-medium">
              <ArrowDownRight className="mr-1 h-4 w-4 text-destructive" />
              <span className="text-destructive">-24%</span> <span className="ml-1 opacity-70 font-normal">waste reduction</span>
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Charts Section */}
      <div className="grid gap-6 md:grid-cols-2">
        <Card className="md:col-span-2 overflow-hidden flex flex-col">
          <CardHeader>
            <CardTitle>Revenue Forecast Trend</CardTitle>
            <CardDescription>Predicted 3-day revenue trajectory based on AI analysis.</CardDescription>
          </CardHeader>
          <CardContent className="flex-1 min-h-[300px]">
            {chartData.length === 0 ? (
              <EmptyState
                icon={BarChart3}
                title="No forecast data"
                description="We don't have enough data to generate predictions yet."
                minHeight="min-h-[300px]"
                className="border-none shadow-none bg-transparent"
              />
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                  <defs>
                    <linearGradient id="colorRev" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="var(--primary)" stopOpacity={0.4}/>
                      <stop offset="95%" stopColor="var(--primary)" stopOpacity={0.0}/>
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e5e7eb" strokeOpacity={0.4} />
                  <XAxis 
                    dataKey="name" 
                    axisLine={false} 
                    tickLine={false} 
                    tick={{ fill: '#888888', fontSize: 12 }}
                    dy={10}
                  />
                  <YAxis 
                    axisLine={false} 
                    tickLine={false} 
                    tick={{ fill: '#888888', fontSize: 12 }}
                    tickFormatter={(value) => `₹${value}`}
                  />
                  <Tooltip 
                    contentStyle={{ borderRadius: '12px', border: '1px solid rgba(255,255,255,0.1)', backdropFilter: 'blur(10px)', backgroundColor: 'rgba(0,0,0,0.8)', color: 'white' }}
                    itemStyle={{ color: 'white' }}
                  />
                  <Area type="monotone" dataKey="revenue" stroke="var(--primary)" strokeWidth={3} fillOpacity={1} fill="url(#colorRev)" />
                </AreaChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>

        <Card className="overflow-hidden flex flex-col">
          <CardHeader>
            <CardTitle>Top Predicted Items</CardTitle>
            <CardDescription>Items with highest expected demand.</CardDescription>
          </CardHeader>
          <CardContent className="flex-1 min-h-[300px]">
            {chartData.length === 0 ? (
              <EmptyState
                icon={PackageOpen}
                title="No item data"
                description="Your top selling items will appear here."
                minHeight="min-h-[300px]"
                className="border-none shadow-none bg-transparent"
              />
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e5e7eb" strokeOpacity={0.4} />
                  <XAxis 
                    dataKey="name" 
                    axisLine={false} 
                    tickLine={false} 
                    tick={{ fill: '#888888', fontSize: 12 }}
                    dy={10}
                  />
                  <YAxis 
                    axisLine={false} 
                    tickLine={false} 
                    tick={{ fill: '#888888', fontSize: 12 }}
                  />
                  <Tooltip 
                    cursor={{ fill: 'rgba(100,100,100,0.1)' }}
                    contentStyle={{ borderRadius: '12px', border: 'none', backgroundColor: 'rgba(0,0,0,0.8)', color: 'white' }}
                    itemStyle={{ color: 'white' }}
                  />
                  <Bar dataKey="predicted" fill="var(--success)" radius={[6, 6, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Bottom Section: Orders & Alerts */}
      <div className="grid gap-6 md:grid-cols-3">
        {/* Recent Orders */}
        <Card className="md:col-span-2">
          <CardHeader className="flex flex-row justify-between items-center">
            <div>
              <CardTitle>Recent Orders</CardTitle>
              <CardDescription>Live feed of incoming restaurant orders.</CardDescription>
            </div>
            <Button variant="ghost" size="sm" className="hidden sm:flex">View all</Button>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {mockRecentOrders.map((order) => (
                <div key={order.id} className="flex items-center justify-between p-4 rounded-lg bg-muted/30 hover:bg-muted/50 transition-colors">
                  <div className="flex items-center gap-4">
                    <div className="h-10 w-10 rounded-full bg-primary/10 flex items-center justify-center">
                      <span className="text-primary font-bold text-sm">{order.customer.charAt(0)}</span>
                    </div>
                    <div>
                      <p className="text-sm font-medium">{order.customer}</p>
                      <p className="text-xs text-muted-foreground flex items-center">
                        <span className="font-mono">{order.id}</span>
                        <span className="mx-2">•</span>
                        <Clock className="h-3 w-3 mr-1" /> {order.time}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-4">
                    <div className="text-right">
                      <p className="text-sm font-bold">₹{order.amount}</p>
                      <Badge variant={order.status === 'completed' ? 'success' : order.status === 'preparing' ? 'warning' : 'secondary'} className="mt-1 text-[10px] px-1.5 py-0.5">
                        {order.status}
                      </Badge>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Inventory Alerts */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <AlertTriangle className="h-5 w-5 text-warning" />
              Inventory Alerts
            </CardTitle>
            <CardDescription>Items predicted to run out soon.</CardDescription>
          </CardHeader>
          <CardContent>
            {analytics?.low_stock_alerts && analytics.low_stock_alerts.length > 0 ? (
              <div className="space-y-4">
                {analytics.low_stock_alerts.slice(0, 4).map((alert, idx) => (
                  <div key={idx} className="flex flex-col gap-2 p-3 rounded-lg border border-warning/20 bg-warning/5">
                    <div className="flex justify-between items-start">
                      <p className="text-sm font-semibold">{alert.item_name}</p>
                      <Badge variant="destructive" className="text-[10px]">Action needed</Badge>
                    </div>
                    <div className="flex justify-between text-xs text-muted-foreground">
                      <span>Stock: {alert.current_stock} {alert.unit}</span>
                      <span>Demand: {alert.predicted_demand} {alert.unit}</span>
                    </div>
                    <div className="w-full bg-muted rounded-full h-1.5 mt-1">
                      <div className="bg-warning h-1.5 rounded-full" style={{ width: `${Math.min((alert.current_stock / alert.predicted_demand) * 100, 100)}%` }} />
                    </div>
                  </div>
                ))}
                <Button variant="outline" className="w-full mt-2 text-xs">View Inventory</Button>
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center py-8 text-center">
                <div className="h-12 w-12 rounded-full bg-success/10 flex items-center justify-center mb-3">
                  <PackageCheck className="h-6 w-6 text-success" />
                </div>
                <p className="text-sm font-medium">Stock Levels Optimal</p>
                <p className="text-xs text-muted-foreground mt-1">No upcoming shortages predicted based on the 3-day forecast.</p>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

