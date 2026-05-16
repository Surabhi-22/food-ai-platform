"use client";

import React from "react";
import { 
  FileText, 
  Download, 
  Calendar, 
  Filter, 
  TrendingUp, 
  AlertCircle,
  Clock,
  ArrowRight
} from "lucide-react";
import { PageHeader } from "@/components/ui/page-header";
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

export default function ReportsPage() {
  const reports = [
    {
      id: "REP-001",
      title: "Monthly Sales Performance",
      description: "Detailed breakdown of sales, revenue, and top-performing items for the last 30 days.",
      date: "May 01, 2026",
      category: "Sales",
      status: "Ready",
    },
    {
      id: "REP-002",
      title: "Inventory Waste Analysis",
      description: "Identification of stock wastage patterns and recommendations for order optimization.",
      date: "May 10, 2026",
      category: "Inventory",
      status: "Ready",
    },
    {
      id: "REP-003",
      title: "AI Forecast Accuracy Report",
      description: "Comparison of AI-predicted demand versus actual sales to measure model performance.",
      date: "May 15, 2026",
      category: "AI Metrics",
      status: "Generating",
    },
    {
      id: "REP-004",
      title: "Peak Hour Demand Trends",
      description: "Heatmap analysis of order volume throughout the day to optimize staffing.",
      date: "May 12, 2026",
      category: "Operations",
      status: "Ready",
    }
  ];

  return (
    <div className="space-y-6 pb-8 animate-in fade-in duration-500">
      <PageHeader
        title="Business Reports"
        description="Access and generate detailed analytical reports for your business performance."
        actions={
          <Button>
            <FileText className="mr-2 h-4 w-4" />
            Generate New Report
          </Button>
        }
      />

      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
        {/* Quick Stats */}
        <Card className="flex flex-col justify-between">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-2">
              <Clock className="h-4 w-4" /> Recent Reports
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">12</div>
            <p className="text-xs text-muted-foreground mt-1">Generated this month</p>
          </CardContent>
        </Card>

        <Card className="flex flex-col justify-between">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-2">
              <TrendingUp className="h-4 w-4" /> Storage Used
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">156 MB</div>
            <p className="text-xs text-muted-foreground mt-1">Of 1 GB total storage</p>
          </CardContent>
        </Card>

        <Card className="flex flex-col justify-between">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-2">
              <AlertCircle className="h-4 w-4" /> Pending
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">2</div>
            <p className="text-xs text-muted-foreground mt-1">Reports currently processing</p>
          </CardContent>
        </Card>
      </div>

      <div className="flex items-center justify-between mt-8">
        <h3 className="text-lg font-semibold tracking-tight">Available Reports</h3>
        <div className="flex gap-2">
          <Button variant="outline" size="sm">
            <Filter className="mr-2 h-4 w-4" /> Filter
          </Button>
          <Button variant="outline" size="sm">
            <Calendar className="mr-2 h-4 w-4" /> Date Range
          </Button>
        </div>
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        {reports.map((report) => (
          <Card key={report.id} className="group hover:border-primary/50 transition-all duration-300">
            <CardHeader>
              <div className="flex justify-between items-start">
                <Badge variant={report.category === "AI Metrics" ? "default" : "secondary"}>
                  {report.category}
                </Badge>
                <Badge variant={report.status === "Ready" ? "outline" : "secondary"} className={report.status === "Ready" ? "bg-green-50 text-green-700 border-green-200" : ""}>
                  {report.status}
                </Badge>
              </div>
              <CardTitle className="mt-4 flex items-center justify-between">
                {report.title}
                <span className="text-xs font-normal text-muted-foreground">{report.id}</span>
              </CardTitle>
              <CardDescription className="line-clamp-2">
                {report.description}
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex items-center gap-4 text-xs text-muted-foreground">
                <div className="flex items-center gap-1">
                  <Calendar className="h-3 w-3" /> {report.date}
                </div>
                <div className="flex items-center gap-1">
                  <Clock className="h-3 w-3" /> 2:30 PM
                </div>
              </div>
            </CardContent>
            <CardFooter className="border-t bg-slate-50/50 pt-4 flex justify-between">
              <Button variant="ghost" size="sm" className="text-muted-foreground hover:text-primary">
                View Online <ArrowRight className="ml-2 h-3 w-3" />
              </Button>
              <Button variant="outline" size="sm" disabled={report.status !== "Ready"}>
                <Download className="mr-2 h-3 w-3" /> Download PDF
              </Button>
            </CardFooter>
          </Card>
        ))}
      </div>
    </div>
  );
}
