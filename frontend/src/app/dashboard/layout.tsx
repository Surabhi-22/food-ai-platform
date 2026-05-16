"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  BarChart3,
  Bell,
  Box,
  LayoutDashboard,
  LogOut,
  Menu,
  MessageSquare,
  PieChart,
  Settings,
  ShoppingCart,
  UtensilsCrossed,
  User,
  Utensils,
} from "lucide-react";

import { cn } from "@/lib/utils";

const navigation = [
  { name: "Overview", href: "/dashboard", icon: LayoutDashboard, exact: true },
  { name: "Orders", href: "/dashboard/orders", icon: ShoppingCart, exact: false },
  { name: "Menu", href: "/dashboard/menu", icon: Utensils, exact: false },
  { name: "Forecasts", href: "/dashboard/forecasts", icon: BarChart3, exact: false },
  { name: "Analytics", href: "/dashboard/analytics", icon: PieChart, exact: false },
  { name: "Inventory", href: "/dashboard/inventory", icon: Box, exact: false },
  { name: "AI Assistant", href: "/dashboard/ai", icon: MessageSquare, exact: false },
  { name: "Settings", href: "/dashboard/settings", icon: Settings, exact: false },
];

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  const [sidebarOpen, setSidebarOpen] = useState(false);

  // In dev mode, don't set a fake token — the backend's deps.py dev bypass
  // returns the first vendor automatically when no token is present.
  useEffect(() => {
    if (typeof window !== "undefined") {
      // Clear any stale fake bypass token so the backend receives no token
      // and its dev bypass (ENVIRONMENT=development) can auto-select a vendor.
      const token = localStorage.getItem("access_token");
      if (!token || token === "__dev_bypass__") {
        localStorage.removeItem("access_token");
      }
    }
  }, []);

  const handleLogout = () => {
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    // Stay on dashboard — no redirect to login
    window.location.reload();
  };

  return (
    <div className="flex min-h-screen bg-slate-50">
      {/* Mobile sidebar backdrop */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-20 bg-black/50 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={cn(
          "fixed inset-y-0 left-0 z-30 w-64 transform bg-white border-r transition-transform duration-200 ease-in-out lg:static lg:translate-x-0",
          sidebarOpen ? "translate-x-0" : "-translate-x-full"
        )}
      >
        <div className="flex h-16 shrink-0 items-center px-6 border-b">
          <div className="flex items-center gap-2 text-primary">
            <UtensilsCrossed className="h-6 w-6" />
            <span className="text-lg font-bold">FoodAI Platform</span>
          </div>
        </div>

        <nav className="flex flex-1 flex-col px-4 py-4 space-y-1">
          {navigation.map((item) => {
            const isActive = item.exact
              ? pathname === item.href
              : pathname.startsWith(item.href);
            return (
              <Link
                key={item.name}
                href={item.href}
                className={cn(
                  "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                  isActive
                    ? "bg-primary text-primary-foreground"
                    : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
                )}
              >
                <item.icon className="h-5 w-5 shrink-0" />
                {item.name}
              </Link>
            );
          })}
        </nav>

        <div className="border-t p-4">
          <button
            onClick={handleLogout}
            className="flex w-full items-center gap-3 rounded-md px-3 py-2 text-sm font-medium text-muted-foreground transition-colors hover:bg-accent hover:text-accent-foreground"
          >
            <LogOut className="h-5 w-5 shrink-0" />
            Sign out
          </button>
        </div>
      </aside>

      {/* Main content */}
      <div className="flex flex-1 flex-col overflow-hidden">
        {/* Top Navbar */}
        <header className="flex h-16 shrink-0 items-center justify-between border-b bg-white px-4 lg:px-8">
          <div className="flex items-center gap-4">
            <button
              className="lg:hidden text-muted-foreground hover:text-foreground"
              onClick={() => setSidebarOpen(true)}
            >
              <Menu className="h-6 w-6" />
            </button>
            <h1 className="text-lg font-semibold lg:hidden">FoodAI</h1>
          </div>

          <div className="flex items-center gap-4">
            <button className="text-muted-foreground hover:text-foreground relative">
              <Bell className="h-5 w-5" />
              <span className="absolute -right-1 -top-1 flex h-4 w-4 items-center justify-center rounded-full bg-destructive text-[10px] font-medium text-destructive-foreground">
                3
              </span>
            </button>
            <div className="h-8 w-8 rounded-full bg-primary/10 flex items-center justify-center">
              <User className="h-4 w-4 text-primary" />
            </div>
          </div>
        </header>

        {/* Main scrollable area */}
        <main className="flex-1 overflow-y-auto p-4 lg:p-8">
          {children}
        </main>
      </div>
    </div>
  );
}
