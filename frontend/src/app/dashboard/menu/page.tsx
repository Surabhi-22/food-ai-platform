"use client";

import { useEffect, useMemo, useState } from "react";
import {
  Edit2,
  Loader2,
  Plus,
  Search,
  Trash2,
} from "lucide-react";
import { z } from "zod";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { toast } from "sonner";

import { MenuItem, PaginatedResponse } from "@/types/api";
import { MenuService } from "@/services/menu.service";
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
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

/* ------------------------------------------------------------------ */
/* Validation Schema                                                   */
/* ------------------------------------------------------------------ */

const menuItemSchema = z.object({
  name: z.string().min(2, "Name is required"),
  category: z.string().min(1, "Category is required"),
  price: z.coerce.number().positive("Price must be positive"),
  cogs_percentage: z.coerce.number().min(0).max(100, "Must be 0–100").optional(),
  description: z.string().optional(),
});

type MenuItemFormValues = z.infer<typeof menuItemSchema>;

const CATEGORIES = [
  "Main Course",
  "Beverages",
  "Desserts",
  "Starters",
  "Snacks",
  "Biryani",
  "Bread",
  "Salads",
  "Combos",
];

/* ------------------------------------------------------------------ */
/* Component                                                           */
/* ------------------------------------------------------------------ */

export default function MenuPage() {
  // Data
  const [menuItems, setMenuItems] = useState<MenuItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  // Filters
  const [search, setSearch] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("All");

  // Dialogs
  const [formDialog, setFormDialog] = useState(false);
  const [deleteDialog, setDeleteDialog] = useState<{ open: boolean; item: MenuItem | null }>({
    open: false,
    item: null,
  });
  const [editingItem, setEditingItem] = useState<MenuItem | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

  // Form
  const {
    register,
    handleSubmit,
    reset,
    setValue,
    formState: { errors },
  } = useForm<MenuItemFormValues>({
    resolver: zodResolver(menuItemSchema),
  });

  /* ── Fetch Menu Items ─────────────────────────────────────────── */

  useEffect(() => {
    const fetchMenu = async () => {
      try {
        const responseData = await MenuService.getMenuItems();
        const data = Array.isArray(responseData) ? responseData : (responseData as PaginatedResponse<MenuItem>).data || [];
        setMenuItems(data);
      } catch (err) {
        console.error("Failed to fetch menu items", err);
        toast.error("Failed to load menu items");
      } finally {
        setIsLoading(false);
      }
    };
    fetchMenu();
  }, []);

  /* ── Categories ───────────────────────────────────────────────── */

  const allCategories = useMemo(() => {
    const set = new Set(menuItems.map((i) => i.category));
    CATEGORIES.forEach((c) => set.add(c));
    return ["All", ...Array.from(set)];
  }, [menuItems]);

  const filteredItems = useMemo(() => {
    let items = menuItems;
    if (categoryFilter !== "All") {
      items = items.filter((i) => i.category === categoryFilter);
    }
    if (search) {
      const q = search.toLowerCase();
      items = items.filter((i) => i.name.toLowerCase().includes(q));
    }
    return items;
  }, [menuItems, categoryFilter, search]);

  /* ── Open Add / Edit ──────────────────────────────────────────── */

  const openAddDialog = () => {
    setEditingItem(null);
    reset({ name: "", category: "", price: 0, cogs_percentage: 30, description: "" });
    setFormDialog(true);
  };

  const openEditDialog = (item: MenuItem) => {
    setEditingItem(item);
    reset({
      name: item.name,
      category: item.category,
      price: item.price,
      cogs_percentage: item.cogs_percentage ?? 30,
      description: item.description || "",
    });
    setFormDialog(true);
  };

  /* ── Submit (Create / Update) ─────────────────────────────────── */

  const onSubmit = async (data: MenuItemFormValues) => {
    setIsSubmitting(true);

    if (editingItem) {
      // Optimistic update
      const previousItems = [...menuItems];
      setMenuItems((prev) =>
        prev.map((item) =>
          item.id === editingItem.id ? { ...item, ...data } : item
        )
      );

      try {
        const updatedItem = await MenuService.updateMenuItem(editingItem.id, data);
        // Replace with the server's response
        setMenuItems((prev) =>
          prev.map((item) => (item.id === editingItem.id ? (updatedItem as MenuItem) : item))
        );
        toast.success(`${data.name} updated`);
        setFormDialog(false);
      } catch (err: unknown) {
        setMenuItems(previousItems);
        const error = err as { response?: { data?: { detail?: string } } };
        toast.error(error.response?.data?.detail || "Failed to update item");
      }
    } else {
      try {
        const newItem = await MenuService.createMenuItem(data);
        setMenuItems((prev) => [newItem as MenuItem, ...prev]);
        toast.success(`${data.name} added to menu`);
        setFormDialog(false);
      } catch (err: unknown) {
        const error = err as { response?: { data?: { detail?: string } } };
        toast.error(error.response?.data?.detail || "Failed to add item");
      }
    }

    setIsSubmitting(false);
  };

  /* ── Delete ───────────────────────────────────────────────────── */

  const handleDelete = async () => {
    if (!deleteDialog.item) return;
    setIsDeleting(true);

    const itemToDelete = deleteDialog.item;
    const previousItems = [...menuItems];

    // Optimistic removal
    setMenuItems((prev) => prev.filter((i) => i.id !== itemToDelete.id));

    try {
      await MenuService.deleteMenuItem(itemToDelete.id);
      toast.success(`${itemToDelete.name} deleted`);
    } catch (err) {
      setMenuItems(previousItems);
      toast.error("Failed to delete item");
    } finally {
      setIsDeleting(false);
      setDeleteDialog({ open: false, item: null });
    }
  };

  /* ── Toggle Active Status ─────────────────────────────────────── */

  const toggleActive = async (item: MenuItem) => {
    const newStatus = !item.is_active;
    const previousItems = [...menuItems];

    // Optimistic update
    setMenuItems((prev) =>
      prev.map((i) => (i.id === item.id ? { ...i, is_active: newStatus } : i))
    );

    try {
      await MenuService.updateMenuItem(item.id, {
        name: item.name,
        category: item.category,
        price: item.price,
        is_active: newStatus,
      } as Partial<MenuItem>);
      toast.success(`${item.name} ${newStatus ? "activated" : "deactivated"}`);
    } catch {
      setMenuItems(previousItems);
      toast.error("Failed to update status");
    }
  };

  /* ── Render ───────────────────────────────────────────────────── */

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-3xl font-bold tracking-tight">Menu</h2>
          <p className="text-muted-foreground">Manage your food items and categories.</p>
        </div>
        <Button onClick={openAddDialog}>
          <Plus className="mr-2 h-4 w-4" />
          Add Item
        </Button>
      </div>

      {/* Filters */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center">
        <div className="relative max-w-sm flex-1">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="Search menu items..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9"
          />
        </div>
      </div>

      {/* Category Tabs */}
      <div className="flex items-center gap-2 flex-wrap">
        {allCategories.map((cat) => (
          <Button
            key={cat}
            variant={categoryFilter === cat ? "default" : "outline"}
            size="sm"
            onClick={() => setCategoryFilter(cat)}
          >
            {cat}
          </Button>
        ))}
      </div>

      {/* Menu Items Grid */}
      {isLoading ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {Array.from({ length: 8 }).map((_, i) => (
            <Card key={i}>
              <CardContent className="pt-6 space-y-3">
                <div className="h-5 w-3/4 bg-muted rounded animate-pulse" />
                <div className="h-4 w-1/2 bg-muted rounded animate-pulse" />
                <div className="h-8 bg-muted rounded animate-pulse" />
              </CardContent>
            </Card>
          ))}
        </div>
      ) : filteredItems.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12">
            <p className="text-muted-foreground">No menu items found.</p>
            <Button variant="outline" className="mt-4" onClick={openAddDialog}>
              <Plus className="mr-2 h-4 w-4" /> Add your first item
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {filteredItems.map((item) => (
            <Card
              key={item.id}
              className={cn(
                "relative group transition-all hover:shadow-md",
                !item.is_active && "opacity-60"
              )}
            >
              <CardHeader className="pb-3">
                <div className="flex items-start justify-between">
                  <div className="flex-1 min-w-0">
                    <CardTitle className="text-base truncate">{item.name}</CardTitle>
                    <CardDescription>{item.category}</CardDescription>
                  </div>
                  <Badge variant={item.is_active ? "success" : "secondary"} className="shrink-0 ml-2">
                    {item.is_active ? "Active" : "Inactive"}
                  </Badge>
                </div>
              </CardHeader>
              <CardContent>
                <div className="flex items-end justify-between">
                  <div>
                    <p className="text-2xl font-bold text-primary">
                      ₹{item.price.toLocaleString()}
                    </p>
                    {item.cogs_percentage != null && (
                      <p className="text-xs text-muted-foreground mt-1">
                        COGS: {item.cogs_percentage}% · Margin: {(100 - item.cogs_percentage).toFixed(0)}%
                      </p>
                    )}
                  </div>
                  <div className="flex items-center gap-1">
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-8 w-8"
                      onClick={() => toggleActive(item)}
                      title={item.is_active ? "Deactivate" : "Activate"}
                    >
                      <div
                        className={cn(
                          "h-4 w-8 rounded-full transition-colors relative",
                          item.is_active ? "bg-success" : "bg-muted"
                        )}
                      >
                        <div
                          className={cn(
                            "absolute top-0.5 h-3 w-3 rounded-full bg-white transition-transform shadow-sm",
                            item.is_active ? "translate-x-4" : "translate-x-0.5"
                          )}
                        />
                      </div>
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-8 w-8"
                      onClick={() => openEditDialog(item)}
                    >
                      <Edit2 className="h-4 w-4" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-8 w-8 text-muted-foreground hover:text-destructive"
                      onClick={() => setDeleteDialog({ open: true, item })}
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Add / Edit Dialog */}
      <Dialog open={formDialog} onOpenChange={setFormDialog}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>{editingItem ? "Edit Menu Item" : "Add New Item"}</DialogTitle>
            <DialogDescription>
              {editingItem
                ? "Update the details of this menu item."
                : "Fill in the details to add a new item to your menu."}
            </DialogDescription>
          </DialogHeader>

          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            {/* Name */}
            <div className="space-y-2">
              <Label htmlFor="name">Name</Label>
              <Input
                id="name"
                placeholder="e.g., Chicken Biryani"
                {...register("name")}
                className={errors.name ? "border-destructive" : ""}
              />
              {errors.name && (
                <p className="text-sm text-destructive">{errors.name.message}</p>
              )}
            </div>

            {/* Category */}
            <div className="space-y-2">
              <Label>Category</Label>
              <Select
                defaultValue={editingItem?.category || ""}
                onValueChange={(val) => setValue("category", val)}
              >
                <SelectTrigger className={errors.category ? "border-destructive" : ""}>
                  <SelectValue placeholder="Select a category" />
                </SelectTrigger>
                <SelectContent>
                  {CATEGORIES.map((cat) => (
                    <SelectItem key={cat} value={cat}>
                      {cat}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              {errors.category && (
                <p className="text-sm text-destructive">{errors.category.message}</p>
              )}
            </div>

            {/* Price and COGS */}
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="price">Price (₹)</Label>
                <Input
                  id="price"
                  type="number"
                  step="0.01"
                  placeholder="150"
                  {...register("price")}
                  className={errors.price ? "border-destructive" : ""}
                />
                {errors.price && (
                  <p className="text-sm text-destructive">{errors.price.message}</p>
                )}
              </div>
              <div className="space-y-2">
                <Label htmlFor="cogs">COGS (%)</Label>
                <Input
                  id="cogs"
                  type="number"
                  step="1"
                  placeholder="30"
                  {...register("cogs_percentage")}
                  className={errors.cogs_percentage ? "border-destructive" : ""}
                />
                {errors.cogs_percentage && (
                  <p className="text-sm text-destructive">{errors.cogs_percentage.message}</p>
                )}
              </div>
            </div>

            <DialogFooter>
              <Button
                type="button"
                variant="outline"
                onClick={() => setFormDialog(false)}
                disabled={isSubmitting}
              >
                Cancel
              </Button>
              <Button type="submit" disabled={isSubmitting}>
                {isSubmitting ? (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                ) : null}
                {editingItem ? "Save changes" : "Add item"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <Dialog
        open={deleteDialog.open}
        onOpenChange={(open) => !open && setDeleteDialog({ open: false, item: null })}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete &quot;{deleteDialog.item?.name}&quot;?</DialogTitle>
            <DialogDescription>
              This action cannot be undone. This will permanently remove the item from your menu.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setDeleteDialog({ open: false, item: null })}
              disabled={isDeleting}
            >
              Cancel
            </Button>
            <Button variant="destructive" onClick={handleDelete} disabled={isDeleting}>
              {isDeleting ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
              Delete
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
