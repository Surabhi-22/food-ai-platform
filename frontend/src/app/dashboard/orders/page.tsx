"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { format } from "date-fns";
import {
  CalendarIcon,
  Check,
  Download,
  Loader2,
  Search,
  X,
} from "lucide-react";
import {
  ColumnDef,
  ColumnFiltersState,
  PaginationState,
  SortingState,
  flexRender,
  getCoreRowModel,
  getFilteredRowModel,
  getPaginationRowModel,
  getSortedRowModel,
  useReactTable,
} from "@tanstack/react-table";
import { toast } from "sonner";

import { api } from "@/lib/api";
import { Order } from "@/types/api";
import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Card,
  CardContent,
} from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { Calendar } from "@/components/ui/calendar";
import { PremiumSkeleton } from "@/components/ui/premium-skeleton";
import { EmptyState } from "@/components/ui/empty-state";
import { PageHeader } from "@/components/ui/page-header";
import { Receipt } from "lucide-react";
import type { DateRange } from "react-day-picker";

/* ------------------------------------------------------------------ */
/* Helpers                                                             */
/* ------------------------------------------------------------------ */

const statusConfig: Record<string, { label: string; variant: "warning" | "success" | "destructive" | "default" }> = {
  pending: { label: "Pending", variant: "warning" },
  preparing: { label: "Preparing", variant: "default" },
  ready: { label: "Ready", variant: "default" },
  completed: { label: "Completed", variant: "success" },
  cancelled: { label: "Cancelled", variant: "destructive" },
};

/* ------------------------------------------------------------------ */
/* Component                                                           */
/* ------------------------------------------------------------------ */

export default function OrdersPage() {
  // Data
  const [orders, setOrders] = useState<Order[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  // Filters
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [dateRange, setDateRange] = useState<DateRange | undefined>();

  // TanStack Table state
  const [sorting, setSorting] = useState<SortingState>([]);
  const [columnFilters, setColumnFilters] = useState<ColumnFiltersState>([]);
  const [pagination, setPagination] = useState<PaginationState>({
    pageIndex: 0,
    pageSize: 10,
  });

  // Confirmation dialog
  const [confirmDialog, setConfirmDialog] = useState<{
    open: boolean;
    orderId: string;
    action: "confirm" | "cancel";
  }>({ open: false, orderId: "", action: "confirm" });
  const [actionLoading, setActionLoading] = useState(false);

  /* ── Fetch Orders ─────────────────────────────────────────────── */

  const fetchOrders = useCallback(async () => {
    try {
      const res = await api.get<Order[]>("/orders");
      // Handle both array and paginated response formats
      const data = Array.isArray(res.data) ? res.data : (res.data as unknown as { orders: Order[] }).orders || [];
      setOrders(data);
    } catch (err) {
      console.error("Failed to fetch orders", err);
      toast.error("Failed to load orders");
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchOrders();
  }, [fetchOrders]);

  /* ── Supabase Realtime (WebSocket simulation via polling) ────── */

  useEffect(() => {
    // Poll for new orders every 15 seconds as a Realtime substitute
    const interval = setInterval(async () => {
      try {
        const res = await api.get<Order[]>("/orders?limit=1");
        const latest = Array.isArray(res.data) ? res.data : (res.data as unknown as { orders: Order[] }).orders || [];
        if (latest.length > 0 && orders.length > 0 && latest[0].id !== orders[0]?.id) {
          toast.info(`New order received!`, { description: `₹${latest[0].total_amount}` });
          fetchOrders();
        }
      } catch {
        // Silently ignore polling errors
      }
    }, 15000);
    return () => clearInterval(interval);
  }, [orders, fetchOrders]);

  /* ── Filtered Data ────────────────────────────────────────────── */

  const filteredData = useMemo(() => {
    let result = [...orders];

    // Search by customer_id (proxy for customer name in current schema)
    if (search) {
      const q = search.toLowerCase();
      result = result.filter(
        (o) =>
          o.id.toLowerCase().includes(q) ||
          o.customer_id?.toLowerCase().includes(q) ||
          o.items?.some((item) => item.menu_item_name?.toLowerCase().includes(q))
      );
    }

    // Status filter
    if (statusFilter && statusFilter !== "all") {
      result = result.filter((o) => o.status === statusFilter);
    }

    // Date range
    if (dateRange?.from) {
      result = result.filter((o) => {
        const d = new Date(o.created_at);
        if (dateRange.from && d < dateRange.from) return false;
        if (dateRange.to && d > new Date(dateRange.to.getTime() + 86400000)) return false;
        return true;
      });
    }

    return result;
  }, [orders, search, statusFilter, dateRange]);

  /* ── Actions ──────────────────────────────────────────────────── */

  const handleStatusUpdate = async () => {
    const { orderId, action } = confirmDialog;
    setActionLoading(true);

    // Optimistic update
    const previousOrders = [...orders];
    const newStatus = action === "confirm" ? "completed" : "cancelled";
    setOrders((prev) =>
      prev.map((o) => (o.id === orderId ? { ...o, status: newStatus as Order["status"] } : o))
    );

    try {
      await api.patch(`/orders/${orderId}/status`, { status: newStatus });
      toast.success(`Order ${action === "confirm" ? "confirmed" : "cancelled"} successfully`);
    } catch (err) {
      // Rollback
      setOrders(previousOrders);
      toast.error(`Failed to ${action} order`);
    } finally {
      setActionLoading(false);
      setConfirmDialog({ open: false, orderId: "", action: "confirm" });
    }
  };

  /* ── CSV Export ────────────────────────────────────────────────── */

  const exportCSV = () => {
    const headers = ["Order ID", "Customer ID", "Items", "Total", "Status", "Date"];
    const rows = filteredData.map((o) => [
      o.id,
      o.customer_id || "N/A",
      o.items?.map((i) => i.menu_item_name || i.menu_item_id).join("; ") || "",
      o.total_amount.toString(),
      o.status,
      format(new Date(o.created_at), "yyyy-MM-dd HH:mm"),
    ]);
    const csv = [headers, ...rows].map((r) => r.join(",")).join("\n");
    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `orders_${format(new Date(), "yyyyMMdd")}.csv`;
    a.click();
    URL.revokeObjectURL(url);
    toast.success("Orders exported to CSV");
  };

  /* ── Column Definitions ───────────────────────────────────────── */

  const columns: ColumnDef<Order>[] = useMemo(
    () => [
      {
        accessorKey: "id",
        header: "Order ID",
        cell: ({ row }) => (
          <span className="font-mono text-xs text-muted-foreground">
            {row.original.id.slice(0, 8)}…
          </span>
        ),
      },
      {
        accessorKey: "customer_id",
        header: "Customer",
        cell: ({ row }) => (
          <span className="font-medium">
            {row.original.customer_id?.slice(0, 8) || "Walk-in"}
          </span>
        ),
      },
      {
        id: "items",
        header: "Items",
        cell: ({ row }) => {
          const names = row.original.items?.map((i) => i.menu_item_name || "Item").join(", ");
          return (
            <span className="text-sm text-muted-foreground max-w-[200px] truncate block">
              {names || "—"}
            </span>
          );
        },
      },
      {
        accessorKey: "total_amount",
        header: "Total",
        cell: ({ row }) => (
          <span className="font-semibold">₹{Number(row.original.total_amount).toLocaleString()}</span>
        ),
      },
      {
        accessorKey: "status",
        header: "Status",
        cell: ({ row }) => {
          const cfg = statusConfig[row.original.status] || statusConfig.pending;
          return <Badge variant={cfg.variant}>{cfg.label}</Badge>;
        },
      },
      {
        accessorKey: "created_at",
        header: "Time",
        cell: ({ row }) => (
          <span className="text-sm text-muted-foreground">
            {format(new Date(row.original.created_at), "MMM dd, HH:mm")}
          </span>
        ),
      },
      {
        id: "actions",
        header: "Actions",
        cell: ({ row }) => {
          const order = row.original;
          if (order.status === "completed" || order.status === "cancelled") {
            return <span className="text-xs text-muted-foreground">—</span>;
          }
          return (
            <div className="flex items-center gap-1">
              <Button
                size="sm"
                variant="ghost"
                className="h-8 text-success hover:text-success hover:bg-success/10"
                onClick={() =>
                  setConfirmDialog({ open: true, orderId: order.id, action: "confirm" })
                }
              >
                <Check className="mr-1 h-3 w-3" />
                Confirm
              </Button>
              <Button
                size="sm"
                variant="ghost"
                className="h-8 text-destructive hover:text-destructive hover:bg-destructive/10"
                onClick={() =>
                  setConfirmDialog({ open: true, orderId: order.id, action: "cancel" })
                }
              >
                <X className="mr-1 h-3 w-3" />
                Cancel
              </Button>
            </div>
          );
        },
      },
    ],
    []
  );

  /* ── Table Instance ───────────────────────────────────────────── */

  const table = useReactTable({
    data: filteredData,
    columns,
    state: { sorting, columnFilters, pagination },
    onSortingChange: setSorting,
    onColumnFiltersChange: setColumnFilters,
    onPaginationChange: setPagination,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
  });

  /* ── Render ───────────────────────────────────────────────────── */

  return (
    <div className="space-y-6 pb-8 animate-in fade-in duration-500">
      {/* Header */}
      <PageHeader
        title="Orders"
        description="Manage and track all incoming orders."
        actions={
          <>
            <Button variant="outline" size="sm" onClick={exportCSV}>
              <Download className="mr-2 h-4 w-4" />
              Export CSV
            </Button>
            <Button size="sm" asChild>
              <a href="/dashboard/orders/new">+ New Order</a>
            </Button>
          </>
        }
      />

      {/* Filters */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center">
            {/* Search */}
            <div className="relative flex-1 max-w-sm">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                placeholder="Search orders..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="pl-9"
              />
            </div>

            {/* Status filter */}
            <Select value={statusFilter} onValueChange={setStatusFilter}>
              <SelectTrigger className="w-[160px]">
                <SelectValue placeholder="All statuses" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Statuses</SelectItem>
                <SelectItem value="pending">Pending</SelectItem>
                <SelectItem value="preparing">Preparing</SelectItem>
                <SelectItem value="completed">Completed</SelectItem>
                <SelectItem value="cancelled">Cancelled</SelectItem>
              </SelectContent>
            </Select>

            {/* Date range picker */}
            <Popover>
              <PopoverTrigger asChild>
                <Button
                  variant="outline"
                  className={cn(
                    "w-[240px] justify-start text-left font-normal",
                    !dateRange && "text-muted-foreground"
                  )}
                >
                  <CalendarIcon className="mr-2 h-4 w-4" />
                  {dateRange?.from ? (
                    dateRange.to ? (
                      <>
                        {format(dateRange.from, "LLL dd")} – {format(dateRange.to, "LLL dd")}
                      </>
                    ) : (
                      format(dateRange.from, "LLL dd, yyyy")
                    )
                  ) : (
                    <span>Pick date range</span>
                  )}
                </Button>
              </PopoverTrigger>
              <PopoverContent className="w-auto p-0" align="start">
                <Calendar
                  mode="range"
                  selected={dateRange}
                  onSelect={setDateRange}
                  numberOfMonths={2}
                />
              </PopoverContent>
            </Popover>

            {/* Clear filters */}
            {(search || statusFilter !== "all" || dateRange) && (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => {
                  setSearch("");
                  setStatusFilter("all");
                  setDateRange(undefined);
                }}
              >
                Clear
              </Button>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Data Table */}
      <Card className="overflow-hidden">
        <CardContent className="p-0">
          {isLoading ? (
            <div className="p-6 space-y-4">
              {Array.from({ length: 5 }).map((_, i) => (
                <PremiumSkeleton key={i} className="h-12 w-full" />
              ))}
            </div>
          ) : (
            <>
              <Table>
                <TableHeader>
                  {table.getHeaderGroups().map((hg) => (
                    <TableRow key={hg.id}>
                      {hg.headers.map((header) => (
                        <TableHead key={header.id}>
                          {header.isPlaceholder
                            ? null
                            : flexRender(header.column.columnDef.header, header.getContext())}
                        </TableHead>
                      ))}
                    </TableRow>
                  ))}
                </TableHeader>
                <TableBody>
                  {table.getRowModel().rows.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={columns.length} className="p-0">
                        <EmptyState
                          icon={Receipt}
                          title="No orders found"
                          description={search || statusFilter !== "all" || dateRange ? "No orders match your current filters." : "You haven't received any orders yet."}
                          minHeight="min-h-[300px]"
                          className="border-none shadow-none bg-transparent"
                        />
                      </TableCell>
                    </TableRow>
                  ) : (
                    table.getRowModel().rows.map((row) => (
                      <TableRow 
                        key={row.id}
                        className="hover:bg-primary/5 transition-colors cursor-pointer group"
                      >
                        {row.getVisibleCells().map((cell) => (
                          <TableCell key={cell.id} className="py-4">
                            {flexRender(cell.column.columnDef.cell, cell.getContext())}
                          </TableCell>
                        ))}
                      </TableRow>
                    ))
                  )}
                </TableBody>
              </Table>

              {/* Pagination */}
              <div className="flex items-center justify-between border-t px-4 py-3">
                <p className="text-sm text-muted-foreground">
                  Showing{" "}
                  {table.getState().pagination.pageIndex * table.getState().pagination.pageSize + 1}–
                  {Math.min(
                    (table.getState().pagination.pageIndex + 1) * table.getState().pagination.pageSize,
                    filteredData.length
                  )}{" "}
                  of {filteredData.length} orders
                </p>
                <div className="flex items-center gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => table.previousPage()}
                    disabled={!table.getCanPreviousPage()}
                  >
                    Previous
                  </Button>
                  <span className="text-sm font-medium">
                    Page {table.getState().pagination.pageIndex + 1} of {table.getPageCount()}
                  </span>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => table.nextPage()}
                    disabled={!table.getCanNextPage()}
                  >
                    Next
                  </Button>
                </div>
              </div>
            </>
          )}
        </CardContent>
      </Card>

      {/* Confirmation Dialog */}
      <Dialog
        open={confirmDialog.open}
        onOpenChange={(open) =>
          !open && setConfirmDialog({ open: false, orderId: "", action: "confirm" })
        }
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              {confirmDialog.action === "confirm" ? "Confirm Order" : "Cancel Order"}
            </DialogTitle>
            <DialogDescription>
              {confirmDialog.action === "confirm"
                ? "Mark this order as completed? This will trigger the ML pipeline for demand forecasting."
                : "Are you sure you want to cancel this order? This action cannot be undone."}
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setConfirmDialog({ open: false, orderId: "", action: "confirm" })}
              disabled={actionLoading}
            >
              Go back
            </Button>
            <Button
              variant={confirmDialog.action === "cancel" ? "destructive" : "default"}
              onClick={handleStatusUpdate}
              disabled={actionLoading}
            >
              {actionLoading ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : null}
              {confirmDialog.action === "confirm" ? "Yes, confirm" : "Yes, cancel order"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
