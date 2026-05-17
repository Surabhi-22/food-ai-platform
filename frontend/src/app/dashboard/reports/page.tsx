"use client";

import React, { useState, useCallback } from "react";
import { toast } from "sonner";
import {
  FileText,
  Download,
  Calendar,
  Filter,
  TrendingUp,
  AlertCircle,
  Clock,
  ArrowRight,
  BarChart3,
  PieChart,
  DollarSign,
  Package,
  ShoppingCart,
  Loader2,
  CheckCircle2,
  X,
} from "lucide-react";
import { PageHeader } from "@/components/ui/page-header";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  CardFooter,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";

/* ─── Report Data ─────────────────────────────────────────────────────────── */

interface ReportData {
  id: string;
  title: string;
  description: string;
  date: string;
  time: string;
  category: string;
  status: "Ready" | "Generating";
  summary: string;
  metrics: { label: string; value: string; change: string; positive: boolean }[];
  tableHeaders: string[];
  tableRows: string[][];
  insights: string[];
}

const reports: ReportData[] = [
  {
    id: "REP-001",
    title: "Monthly Sales Performance",
    description:
      "Detailed breakdown of sales, revenue, and top-performing items for the last 30 days.",
    date: "May 01, 2026",
    time: "2:30 PM",
    category: "Sales",
    status: "Ready",
    summary:
      "Overall sales have increased by 12.4% compared to the previous month, driven primarily by increased weekend orders and the introduction of 3 new menu items. Customer acquisition rate improved by 8.2%.",
    metrics: [
      { label: "Total Revenue", value: "₹4,82,350", change: "+12.4%", positive: true },
      { label: "Total Orders", value: "3,847", change: "+9.1%", positive: true },
      { label: "Avg Order Value", value: "₹125.40", change: "+3.2%", positive: true },
      { label: "Return Customers", value: "68%", change: "+5.7%", positive: true },
    ],
    tableHeaders: ["Item", "Units Sold", "Revenue", "Growth"],
    tableRows: [
      ["Butter Chicken", "842", "₹1,26,300", "+18%"],
      ["Paneer Tikka", "634", "₹63,400", "+12%"],
      ["Biryani (Veg)", "521", "₹78,150", "+22%"],
      ["Dal Makhani", "498", "₹49,800", "+7%"],
      ["Naan (Butter)", "1,203", "₹36,090", "+4%"],
    ],
    insights: [
      "Weekend orders account for 42% of total weekly revenue",
      "Biryani variants showed the highest growth at 22%",
      "Average delivery time decreased by 4 minutes to 28 minutes",
      "Customer satisfaction rating improved to 4.6/5.0",
    ],
  },
  {
    id: "REP-002",
    title: "Inventory Waste Analysis",
    description:
      "Identification of stock wastage patterns and recommendations for order optimization.",
    date: "May 10, 2026",
    time: "2:30 PM",
    category: "Inventory",
    status: "Ready",
    summary:
      "Inventory waste has been reduced by 15.3% following last month's optimization recommendations. The primary areas of waste remain in fresh produce (leafy greens, tomatoes) and dairy products.",
    metrics: [
      { label: "Total Waste", value: "₹18,420", change: "-15.3%", positive: true },
      { label: "Waste Rate", value: "4.2%", change: "-1.8%", positive: true },
      { label: "Items At Risk", value: "12", change: "-5", positive: true },
      { label: "Cost Savings", value: "₹3,340", change: "+22%", positive: true },
    ],
    tableHeaders: ["Ingredient", "Wasted (kg)", "Cost Lost", "Shelf Life Left"],
    tableRows: [
      ["Leafy Greens", "23.4", "₹4,680", "1-2 days"],
      ["Tomatoes", "18.7", "₹2,805", "2-3 days"],
      ["Paneer", "8.2", "₹3,280", "3 days"],
      ["Cream/Milk", "12.1", "₹1,815", "2 days"],
      ["Herbs (Fresh)", "5.6", "₹1,680", "1 day"],
    ],
    insights: [
      "Implementing FIFO rotation reduced dairy waste by 28%",
      "Smaller, more frequent produce orders recommended for weekdays",
      "Herb garden initiative could save ₹1,680/month",
      "Cold storage temperature adjustments extended shelf life by 1 day on average",
    ],
  },
  {
    id: "REP-003",
    title: "AI Forecast Accuracy Report",
    description:
      "Comparison of AI-predicted demand versus actual sales to measure model performance.",
    date: "May 15, 2026",
    time: "2:30 PM",
    category: "AI Metrics",
    status: "Generating",
    summary: "",
    metrics: [],
    tableHeaders: [],
    tableRows: [],
    insights: [],
  },
  {
    id: "REP-004",
    title: "Peak Hour Demand Trends",
    description:
      "Heatmap analysis of order volume throughout the day to optimize staffing.",
    date: "May 12, 2026",
    time: "2:30 PM",
    category: "Operations",
    status: "Ready",
    summary:
      "Peak ordering hours remain consistent between 12:00–14:00 and 19:00–21:00. Saturday evening shows the highest demand spike, with orders 45% above the daily average. Staffing recommendations have been updated accordingly.",
    metrics: [
      { label: "Peak Hour Orders", value: "127/hr", change: "+8%", positive: true },
      { label: "Avg Wait Time", value: "24 min", change: "-12%", positive: true },
      { label: "Staff Utilization", value: "87%", change: "+6%", positive: true },
      { label: "Off-Peak Revenue", value: "₹42,100", change: "+15%", positive: true },
    ],
    tableHeaders: ["Time Slot", "Avg Orders", "Revenue", "Staff Needed"],
    tableRows: [
      ["11:00 – 13:00", "98", "₹12,250", "8"],
      ["13:00 – 15:00", "62", "₹7,750", "5"],
      ["15:00 – 17:00", "34", "₹4,250", "3"],
      ["17:00 – 19:00", "56", "₹7,000", "5"],
      ["19:00 – 21:00", "115", "₹14,375", "9"],
    ],
    insights: [
      "Saturday 19:00–21:00 is the busiest slot with 145 avg orders",
      "Monday–Wednesday off-peak promotions increased revenue by 15%",
      "Adding 2 staff during peak hours reduced wait time by 12%",
      "Pre-order feature adoption at 23%, reducing kitchen congestion",
    ],
  },
];

/* ─── Category Icon Mapping ───────────────────────────────────────────────── */

function getCategoryIcon(category: string) {
  switch (category) {
    case "Sales":
      return <DollarSign className="h-4 w-4" />;
    case "Inventory":
      return <Package className="h-4 w-4" />;
    case "AI Metrics":
      return <BarChart3 className="h-4 w-4" />;
    case "Operations":
      return <ShoppingCart className="h-4 w-4" />;
    default:
      return <FileText className="h-4 w-4" />;
  }
}

/* ─── PDF Generation ──────────────────────────────────────────────────────── */

async function generatePDF(report: ReportData) {
  const { jsPDF } = await import("jspdf");
  const doc = new jsPDF({ orientation: "portrait", unit: "mm", format: "a4" });

  const pageWidth = doc.internal.pageSize.getWidth();
  const margin = 20;
  const contentWidth = pageWidth - margin * 2;
  let y = margin;

  // ── Header band ──
  doc.setFillColor(22, 163, 74); // green-600
  doc.rect(0, 0, pageWidth, 38, "F");
  doc.setTextColor(255, 255, 255);
  doc.setFontSize(22);
  doc.setFont("helvetica", "bold");
  doc.text("FoodAI Platform", margin, 16);
  doc.setFontSize(10);
  doc.setFont("helvetica", "normal");
  doc.text(`Report ID: ${report.id}`, margin, 24);
  doc.text(`Generated: ${report.date} at ${report.time}`, margin, 30);
  doc.text(`Category: ${report.category}`, pageWidth - margin - 40, 24);
  y = 50;

  // ── Title ──
  doc.setTextColor(17, 24, 39);
  doc.setFontSize(18);
  doc.setFont("helvetica", "bold");
  doc.text(report.title, margin, y);
  y += 10;

  // ── Summary ──
  doc.setFontSize(10);
  doc.setFont("helvetica", "normal");
  doc.setTextColor(75, 85, 99);
  const summaryLines = doc.splitTextToSize(report.summary, contentWidth);
  doc.text(summaryLines, margin, y);
  y += summaryLines.length * 5 + 8;

  // ── Metrics ──
  if (report.metrics.length > 0) {
    doc.setFontSize(13);
    doc.setFont("helvetica", "bold");
    doc.setTextColor(17, 24, 39);
    doc.text("Key Metrics", margin, y);
    y += 8;

    const metricBoxWidth = (contentWidth - 6) / 2;
    report.metrics.forEach((metric, idx) => {
      const col = idx % 2;
      const row = Math.floor(idx / 2);
      const bx = margin + col * (metricBoxWidth + 6);
      const by = y + row * 22;

      doc.setFillColor(249, 250, 251);
      doc.roundedRect(bx, by, metricBoxWidth, 18, 2, 2, "F");

      doc.setFontSize(9);
      doc.setFont("helvetica", "normal");
      doc.setTextColor(107, 114, 128);
      doc.text(metric.label, bx + 4, by + 6);

      doc.setFontSize(14);
      doc.setFont("helvetica", "bold");
      doc.setTextColor(17, 24, 39);
      doc.text(metric.value, bx + 4, by + 13);

      doc.setFontSize(9);
      doc.setFont("helvetica", "bold");
      if (metric.positive) {
        doc.setTextColor(22, 163, 74);
      } else {
        doc.setTextColor(220, 38, 38);
      }
      doc.text(metric.change, bx + metricBoxWidth - 16, by + 13);
    });
    y += Math.ceil(report.metrics.length / 2) * 22 + 8;
  }

  // ── Table ──
  if (report.tableHeaders.length > 0) {
    doc.setFontSize(13);
    doc.setFont("helvetica", "bold");
    doc.setTextColor(17, 24, 39);
    doc.text("Detailed Breakdown", margin, y);
    y += 8;

    const colCount = report.tableHeaders.length;
    const colW = contentWidth / colCount;

    // Header row
    doc.setFillColor(22, 163, 74);
    doc.rect(margin, y, contentWidth, 8, "F");
    doc.setFontSize(9);
    doc.setFont("helvetica", "bold");
    doc.setTextColor(255, 255, 255);
    report.tableHeaders.forEach((header, i) => {
      doc.text(header, margin + i * colW + 3, y + 5.5);
    });
    y += 8;

    // Data rows
    report.tableRows.forEach((row, rowIdx) => {
      if (rowIdx % 2 === 0) {
        doc.setFillColor(249, 250, 251);
        doc.rect(margin, y, contentWidth, 7, "F");
      }
      doc.setFontSize(9);
      doc.setFont("helvetica", "normal");
      doc.setTextColor(55, 65, 81);
      row.forEach((cell, i) => {
        doc.text(cell, margin + i * colW + 3, y + 5);
      });
      y += 7;
    });
    y += 8;
  }

  // ── Insights ──
  if (report.insights.length > 0) {
    // Check if we need a new page
    if (y > 240) {
      doc.addPage();
      y = margin;
    }

    doc.setFontSize(13);
    doc.setFont("helvetica", "bold");
    doc.setTextColor(17, 24, 39);
    doc.text("Key Insights", margin, y);
    y += 8;

    doc.setFontSize(10);
    doc.setFont("helvetica", "normal");
    doc.setTextColor(55, 65, 81);
    report.insights.forEach((insight) => {
      doc.setFillColor(22, 163, 74);
      doc.circle(margin + 2, y - 1.2, 1.2, "F");
      const lines = doc.splitTextToSize(insight, contentWidth - 10);
      doc.text(lines, margin + 8, y);
      y += lines.length * 5 + 3;
    });
  }

  // ── Footer ──
  const pageHeight = doc.internal.pageSize.getHeight();
  doc.setFillColor(249, 250, 251);
  doc.rect(0, pageHeight - 14, pageWidth, 14, "F");
  doc.setFontSize(8);
  doc.setFont("helvetica", "normal");
  doc.setTextColor(156, 163, 175);
  doc.text(
    "Generated by FoodAI Platform • Confidential",
    pageWidth / 2,
    pageHeight - 6,
    { align: "center" }
  );

  doc.save(`${report.id}_${report.title.replace(/\s+/g, "_")}.pdf`);
}

/* ─── Report Viewer Dialog ────────────────────────────────────────────────── */

function ReportViewerDialog({
  report,
  open,
  onClose,
}: {
  report: ReportData | null;
  open: boolean;
  onClose: () => void;
}) {
  if (!report) return null;

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-3xl max-h-[85vh] overflow-y-auto">
        <DialogHeader>
          <div className="flex items-center gap-2 mb-1">
            <Badge
              variant={report.category === "AI Metrics" ? "default" : "secondary"}
              className="text-xs"
            >
              {report.category}
            </Badge>
            <span className="text-xs text-muted-foreground">{report.id}</span>
          </div>
          <DialogTitle className="text-xl">{report.title}</DialogTitle>
          <DialogDescription className="flex items-center gap-4 text-xs">
            <span className="flex items-center gap-1">
              <Calendar className="h-3 w-3" /> {report.date}
            </span>
            <span className="flex items-center gap-1">
              <Clock className="h-3 w-3" /> {report.time}
            </span>
          </DialogDescription>
        </DialogHeader>

        {/* Summary */}
        <div className="rounded-lg border bg-slate-50/80 p-4 mt-2">
          <h4 className="text-sm font-semibold text-slate-700 mb-2 flex items-center gap-2">
            <FileText className="h-4 w-4 text-green-600" />
            Executive Summary
          </h4>
          <p className="text-sm text-slate-600 leading-relaxed">{report.summary}</p>
        </div>

        {/* Metrics Grid */}
        {report.metrics.length > 0 && (
          <div>
            <h4 className="text-sm font-semibold text-slate-700 mb-3 flex items-center gap-2">
              <PieChart className="h-4 w-4 text-green-600" />
              Key Metrics
            </h4>
            <div className="grid grid-cols-2 gap-3">
              {report.metrics.map((metric, idx) => (
                <div
                  key={idx}
                  className="rounded-lg border bg-white p-3 flex flex-col gap-1 hover:shadow-sm transition-shadow"
                >
                  <span className="text-xs text-muted-foreground">{metric.label}</span>
                  <div className="flex items-baseline justify-between">
                    <span className="text-lg font-bold text-slate-900">{metric.value}</span>
                    <span
                      className={`text-xs font-semibold px-1.5 py-0.5 rounded ${
                        metric.positive
                          ? "bg-green-50 text-green-700"
                          : "bg-red-50 text-red-700"
                      }`}
                    >
                      {metric.change}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Data Table */}
        {report.tableHeaders.length > 0 && (
          <div>
            <h4 className="text-sm font-semibold text-slate-700 mb-3 flex items-center gap-2">
              <BarChart3 className="h-4 w-4 text-green-600" />
              Detailed Breakdown
            </h4>
            <div className="rounded-lg border overflow-hidden">
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-green-600 text-white">
                    {report.tableHeaders.map((header, idx) => (
                      <th key={idx} className="px-4 py-2.5 text-left font-medium text-xs">
                        {header}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {report.tableRows.map((row, rowIdx) => (
                    <tr
                      key={rowIdx}
                      className={`border-t ${
                        rowIdx % 2 === 0 ? "bg-white" : "bg-slate-50/60"
                      } hover:bg-green-50/40 transition-colors`}
                    >
                      {row.map((cell, cellIdx) => (
                        <td
                          key={cellIdx}
                          className={`px-4 py-2.5 ${
                            cellIdx === 0 ? "font-medium text-slate-900" : "text-slate-600"
                          }`}
                        >
                          {cell}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Insights */}
        {report.insights.length > 0 && (
          <div>
            <h4 className="text-sm font-semibold text-slate-700 mb-3 flex items-center gap-2">
              <TrendingUp className="h-4 w-4 text-green-600" />
              Key Insights
            </h4>
            <ul className="space-y-2">
              {report.insights.map((insight, idx) => (
                <li
                  key={idx}
                  className="flex items-start gap-2 text-sm text-slate-600 bg-white rounded-lg border p-3 hover:border-green-200 transition-colors"
                >
                  <CheckCircle2 className="h-4 w-4 text-green-500 mt-0.5 flex-shrink-0" />
                  {insight}
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Actions */}
        <div className="flex justify-end gap-2 pt-2 border-t mt-2">
          <Button variant="outline" size="sm" onClick={onClose}>
            <X className="mr-2 h-3 w-3" /> Close
          </Button>
          <Button
            size="sm"
            onClick={() => generatePDF(report)}
            className="bg-green-600 hover:bg-green-700"
          >
            <Download className="mr-2 h-3 w-3" /> Download PDF
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}

/* ─── Main Page ───────────────────────────────────────────────────────────── */

export default function ReportsPage() {
  const [viewReport, setViewReport] = useState<ReportData | null>(null);
  const [downloadingId, setDownloadingId] = useState<string | null>(null);

  const handleDownloadPDF = useCallback(async (report: ReportData) => {
    setDownloadingId(report.id);
    try {
      await generatePDF(report);
    } finally {
      // Short delay so user sees the loading state
      setTimeout(() => setDownloadingId(null), 800);
    }
  }, []);

  return (
    <div className="space-y-6 pb-8 animate-in fade-in duration-500">
      <PageHeader
        title="Business Reports"
        description="Access and generate detailed analytical reports for your business performance."
        actions={
          <Button onClick={() => toast.success('Report generation started. It will appear in the list when ready.')}>
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
            <p className="text-xs text-muted-foreground mt-1">
              Generated this month
            </p>
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
            <p className="text-xs text-muted-foreground mt-1">
              Of 1 GB total storage
            </p>
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
            <p className="text-xs text-muted-foreground mt-1">
              Reports currently processing
            </p>
          </CardContent>
        </Card>
      </div>

      <div className="flex items-center justify-between mt-8">
        <h3 className="text-lg font-semibold tracking-tight">
          Available Reports
        </h3>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={() => toast.info('Filter feature coming soon')}>
            <Filter className="mr-2 h-4 w-4" /> Filter
          </Button>
          <Button variant="outline" size="sm" onClick={() => toast.info('Date range filter coming soon')}>
            <Calendar className="mr-2 h-4 w-4" /> Date Range
          </Button>
        </div>
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        {reports.map((report) => (
          <Card
            key={report.id}
            className="group hover:border-primary/50 transition-all duration-300"
          >
            <CardHeader>
              <div className="flex justify-between items-start">
                <Badge
                  variant={
                    report.category === "AI Metrics" ? "default" : "secondary"
                  }
                >
                  {report.category}
                </Badge>
                <Badge
                  variant={
                    report.status === "Ready" ? "outline" : "secondary"
                  }
                  className={
                    report.status === "Ready"
                      ? "bg-green-50 text-green-700 border-green-200"
                      : ""
                  }
                >
                  {report.status}
                </Badge>
              </div>
              <CardTitle className="mt-4 flex items-center justify-between">
                {report.title}
                <span className="text-xs font-normal text-muted-foreground">
                  {report.id}
                </span>
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
                  <Clock className="h-3 w-3" /> {report.time}
                </div>
              </div>
            </CardContent>
            <CardFooter className="border-t bg-slate-50/50 pt-4 flex justify-between">
              <Button
                variant="ghost"
                size="sm"
                className="text-muted-foreground hover:text-primary"
                disabled={report.status !== "Ready"}
                onClick={() => setViewReport(report)}
              >
                {getCategoryIcon(report.category)}
                <span className="ml-2">View Online</span>
                <ArrowRight className="ml-2 h-3 w-3" />
              </Button>
              <Button
                variant="outline"
                size="sm"
                disabled={report.status !== "Ready" || downloadingId === report.id}
                onClick={() => handleDownloadPDF(report)}
              >
                {downloadingId === report.id ? (
                  <Loader2 className="mr-2 h-3 w-3 animate-spin" />
                ) : (
                  <Download className="mr-2 h-3 w-3" />
                )}
                {downloadingId === report.id ? "Generating..." : "Download PDF"}
              </Button>
            </CardFooter>
          </Card>
        ))}
      </div>

      {/* Report Viewer Dialog */}
      <ReportViewerDialog
        report={viewReport}
        open={!!viewReport}
        onClose={() => setViewReport(null)}
      />
    </div>
  );
}
