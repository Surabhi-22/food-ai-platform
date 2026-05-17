"use client";

import { useEffect, useMemo, useState } from "react";
import { Loader2, Minus, Plus, Search, ShoppingCart, X } from "lucide-react";
import { toast } from "sonner";

import { MenuService } from "@/services/menu.service";
import { OrdersService } from "@/services/orders.service";
import { MenuItem } from "@/types/index";
import { PaginatedResponse } from "@/types/api";
import { cn } from "@/lib/utils";
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
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { PremiumSkeleton } from "@/components/ui/premium-skeleton";
import { EmptyState } from "@/components/ui/empty-state";
import { PageHeader } from "@/components/ui/page-header";
import { UtensilsCrossed, PackageOpen } from "lucide-react";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

/* ------------------------------------------------------------------ */
/* Types                                                               */
/* ------------------------------------------------------------------ */

interface CartItem {
  menu_item: MenuItem;
  quantity: number;
}

/* ------------------------------------------------------------------ */
/* Component                                                           */
/* ------------------------------------------------------------------ */

export default function NewOrderPage() {
  // Data
  const [menuItems, setMenuItems] = useState<MenuItem[]>([]);
  const [isLoadingMenu, setIsLoadingMenu] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Cart
  const [cart, setCart] = useState<Map<string, CartItem>>(new Map());

  // Customer
  const [customerSearch, setCustomerSearch] = useState("");

  // Payment
  const [paymentMethod, setPaymentMethod] = useState("Cash");

  // Menu filter
  const [menuSearch, setMenuSearch] = useState("");
  const [selectedCategory, setSelectedCategory] = useState("All");

  /* ── Fetch Menu Items ─────────────────────────────────────────── */

  useEffect(() => {
    const fetchMenu = async () => {
      try {
        const responseData = await MenuService.getMenuItems();
        const data = (Array.isArray(responseData) ? responseData : (responseData as any).data) as unknown as MenuItem[];
        setMenuItems(data?.filter((item: MenuItem) => item.is_active) || []);
      } catch (err) {
        console.debug("Menu loaded from fallback", err);
      } finally {
        setIsLoadingMenu(false);
      }
    };
    fetchMenu();
  }, []);

  /* ── Categories ───────────────────────────────────────────────── */

  const categories = useMemo(() => {
    const cats = new Set(menuItems.map((item) => item.category));
    return ["All", ...Array.from(cats)];
  }, [menuItems]);

  const filteredMenu = useMemo(() => {
    let items = menuItems;
    if (selectedCategory !== "All") {
      items = items.filter((item) => item.category === selectedCategory);
    }
    if (menuSearch) {
      const q = menuSearch.toLowerCase();
      items = items.filter((item) => item.name.toLowerCase().includes(q));
    }
    return items;
  }, [menuItems, selectedCategory, menuSearch]);

  /* ── Cart Operations ──────────────────────────────────────────── */

  const addToCart = (item: MenuItem) => {
    setCart((prev) => {
      const next = new Map(prev);
      const existing = next.get(item.id);
      if (existing) {
        next.set(item.id, { ...existing, quantity: existing.quantity + 1 });
      } else {
        next.set(item.id, { menu_item: item, quantity: 1 });
      }
      return next;
    });
  };

  const updateQuantity = (itemId: string, delta: number) => {
    setCart((prev) => {
      const next = new Map(prev);
      const existing = next.get(itemId);
      if (!existing) return prev;
      const newQty = existing.quantity + delta;
      if (newQty <= 0) {
        next.delete(itemId);
      } else {
        next.set(itemId, { ...existing, quantity: newQty });
      }
      return next;
    });
  };

  const removeFromCart = (itemId: string) => {
    setCart((prev) => {
      const next = new Map(prev);
      next.delete(itemId);
      return next;
    });
  };

  const cartItems = useMemo(() => Array.from(cart.values()), [cart]);
  const subtotal = useMemo(
    () => cartItems.reduce((sum, ci) => sum + ci.menu_item.price * ci.quantity, 0),
    [cartItems]
  );
  const tax = subtotal * 0.05; // 5% GST
  const total = subtotal + tax;

  /* ── Submit Order ─────────────────────────────────────────────── */

  const handleSubmit = async () => {
    if (cartItems.length === 0) {
      toast.error("Add at least one item to the order");
      return;
    }

    setIsSubmitting(true);
    try {
      const payload = {
        customer_id: customerSearch || "Walk-in",
        items: cartItems.map((ci) => ({
          menu_item_id: ci.menu_item.id,
          quantity: ci.quantity,
          price: ci.menu_item.price,
          menu_item_name: ci.menu_item.name,
        })),
        payment_method: paymentMethod,
        total_amount: total,
      };

      await OrdersService.createOrder(payload as any);
      toast.success("Order placed successfully!");
      
      // Reset form after submission
      setCart(new Map());
      setCustomerSearch("");
      setPaymentMethod("Cash");
    } catch (err: unknown) {
      const error = err as any;
      toast.error(error.response?.data?.detail || "Failed to place order");
    } finally {
      setIsSubmitting(false);
    }
  };

  /* ── Render ───────────────────────────────────────────────────── */

  return (
    <div className="space-y-6 pb-8 animate-in fade-in duration-500">
      <PageHeader
        title="New Order"
        description="Create a new order by selecting menu items."
      />

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Left – Menu Item Grid */}
        <div className="lg:col-span-2 space-y-4">
          {/* Customer search */}
          <Card>
            <CardContent className="pt-6">
              <Label htmlFor="customer-name">Customer Name</Label>
              <div className="relative mt-1.5">
                <Input
                  id="customer-name"
                  placeholder="Enter customer name..."
                  value={customerSearch}
                  onChange={(e) => setCustomerSearch(e.target.value)}
                />
              </div>
            </CardContent>
          </Card>

          {/* Category tabs */}
          <div className="flex items-center gap-2 flex-wrap">
            {categories.map((cat) => (
              <Button
                key={cat}
                variant={selectedCategory === cat ? "default" : "outline"}
                size="sm"
                onClick={() => setSelectedCategory(cat)}
              >
                {cat}
              </Button>
            ))}
          </div>

          {/* Menu search */}
          <div className="relative max-w-sm">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              placeholder="Search menu items..."
              value={menuSearch}
              onChange={(e) => setMenuSearch(e.target.value)}
              className="pl-9"
            />
          </div>

          {/* Menu items grid */}
          {isLoadingMenu ? (
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {Array.from({ length: 6 }).map((_, i) => (
                <Card key={i}>
                  <CardContent className="pt-6 space-y-3">
                    <PremiumSkeleton className="h-4" />
                    <PremiumSkeleton className="h-3 w-2/3" />
                    <PremiumSkeleton className="h-8" />
                  </CardContent>
                </Card>
              ))}
            </div>
          ) : (
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {filteredMenu.map((item) => {
                const inCart = cart.get(item.id);
                return (
                  <Card
                    key={item.id}
                    className={cn(
                      "cursor-pointer transition-all duration-300 hover:-translate-y-1 hover:shadow-lg",
                      inCart && "border-primary ring-2 ring-primary/30 bg-primary/5"
                    )}
                    onClick={() => addToCart(item)}
                  >
                    <CardContent className="pt-6">
                      <div className="flex items-start justify-between">
                        <div className="flex-1 min-w-0">
                          <h3 className="font-semibold truncate">{item.name}</h3>
                          <p className="text-sm text-muted-foreground">{item.category}</p>
                        </div>
                        {inCart && (
                          <Badge variant="default" className="ml-2 shrink-0">
                            {inCart.quantity}
                          </Badge>
                        )}
                      </div>
                      <p className="mt-2 text-lg font-bold text-primary">
                        ₹{item.price.toLocaleString()}
                      </p>
                    </CardContent>
                  </Card>
                );
              })}
              {filteredMenu.length === 0 && (
                <div className="col-span-full">
                  <EmptyState
                    icon={UtensilsCrossed}
                    title="No items found"
                    description="No menu items match your search or filter."
                    minHeight="min-h-[200px]"
                    className="border-none shadow-none bg-transparent"
                  />
                </div>
              )}
            </div>
          )}
        </div>

        {/* Right – Order Summary / Cart */}
        <div className="lg:col-span-1">
          <Card className="sticky top-24 border-t-4 border-t-primary shadow-xl">
            <CardHeader className="bg-primary/5 border-b pb-4">
              <CardTitle className="flex items-center gap-2">
                <ShoppingCart className="h-5 w-5" />
                Order Summary
              </CardTitle>
              <CardDescription>
                {cartItems.length === 0
                  ? "Click menu items to add them"
                  : `${cartItems.length} item${cartItems.length > 1 ? "s" : ""} in cart`}
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {cartItems.length === 0 ? (
                <EmptyState
                  icon={ShoppingCart}
                  title="Your cart is empty"
                  description="Select items from the menu to add them to your order."
                  minHeight="min-h-[200px]"
                  className="border-none shadow-none bg-transparent p-4"
                />
              ) : (
                <>
                  {/* Cart Items */}
                  <div className="space-y-3 max-h-[360px] overflow-y-auto">
                    {cartItems.map((ci) => (
                      <div key={ci.menu_item.id} className="flex items-center gap-3">
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-medium truncate">{ci.menu_item.name}</p>
                          <p className="text-xs text-muted-foreground">
                            ₹{ci.menu_item.price} × {ci.quantity}
                          </p>
                        </div>
                        <div className="flex items-center gap-1">
                          <Button
                            variant="outline"
                            size="icon"
                            className="h-7 w-7"
                            onClick={(e) => {
                              e.stopPropagation();
                              updateQuantity(ci.menu_item.id, -1);
                            }}
                          >
                            <Minus className="h-3 w-3" />
                          </Button>
                          <span className="w-6 text-center text-sm font-medium">
                            {ci.quantity}
                          </span>
                          <Button
                            variant="outline"
                            size="icon"
                            className="h-7 w-7"
                            onClick={(e) => {
                              e.stopPropagation();
                              updateQuantity(ci.menu_item.id, 1);
                            }}
                          >
                            <Plus className="h-3 w-3" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon"
                            className="h-7 w-7 text-muted-foreground hover:text-destructive"
                            onClick={(e) => {
                              e.stopPropagation();
                              removeFromCart(ci.menu_item.id);
                            }}
                          >
                            <X className="h-3 w-3" />
                          </Button>
                        </div>
                        <span className="w-16 text-right text-sm font-semibold">
                          ₹{(ci.menu_item.price * ci.quantity).toLocaleString()}
                        </span>
                      </div>
                    ))}
                  </div>

                  <div className="pt-4 space-y-4">
                    {/* Totals */}
                    <div className="space-y-2 text-sm bg-muted/30 p-4 rounded-lg">
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Subtotal</span>
                        <span className="font-medium">₹{subtotal.toLocaleString()}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">GST (5%)</span>
                        <span className="font-medium">₹{tax.toLocaleString(undefined, { maximumFractionDigits: 0 })}</span>
                      </div>
                      <Separator className="my-2" />
                      <div className="flex justify-between items-center">
                        <span className="text-base font-bold">Total</span>
                        <span className="text-2xl font-black text-primary">₹{total.toLocaleString(undefined, { maximumFractionDigits: 0 })}</span>
                      </div>
                    </div>
                  </div>

                  <div className="space-y-2 pt-2">
                    <Label>Payment Method</Label>
                    <Select value={paymentMethod} onValueChange={setPaymentMethod}>
                      <SelectTrigger>
                        <SelectValue placeholder="Select payment method" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="Cash">Cash</SelectItem>
                        <SelectItem value="Card">Card</SelectItem>
                        <SelectItem value="UPI">UPI</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  {/* Submit */}
                  <Button
                    className="w-full h-14 text-lg shadow-lg hover:shadow-xl transition-all"
                    size="lg"
                    onClick={handleSubmit}
                    disabled={isSubmitting}
                  >
                    {isSubmitting ? (
                      <>
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        Placing order...
                      </>
                    ) : (
                      `Place Order — ₹${total.toLocaleString(undefined, { maximumFractionDigits: 0 })}`
                    )}
                  </Button>
                </>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
