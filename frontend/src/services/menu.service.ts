import { api } from "@/lib/api";
import { MenuItem, PaginatedResponse } from "@/types/api";

/* ─── Local Storage Fallback ───────────────────────────────────────────────
   When the backend is unavailable (e.g. Vercel-only deployment), CRUD
   operations fall through to localStorage so the menu page still works.
   ─────────────────────────────────────────────────────────────────────── */

const STORAGE_KEY = "food_ai_menu_items";

function getLocalItems(): MenuItem[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

function saveLocalItems(items: MenuItem[]) {
  if (typeof window === "undefined") return;
  localStorage.setItem(STORAGE_KEY, JSON.stringify(items));
}

/* ─── Default seed data (shown on first visit) ────────────────────────── */

const SEED_ITEMS: MenuItem[] = [
  { id: "seed-1", name: "Butter Chicken", description: "Creamy tomato-based chicken curry", price: 320, category: "Main Course", is_available: true },
  { id: "seed-2", name: "Paneer Tikka", description: "Char-grilled cottage cheese with spices", price: 220, category: "Starters", is_available: true },
  { id: "seed-3", name: "Veg Biryani", description: "Aromatic rice with seasonal vegetables", price: 180, category: "Main Course", is_available: true },
  { id: "seed-4", name: "Masala Chai", description: "Spiced Indian tea", price: 40, category: "Beverages", is_available: true },
  { id: "seed-5", name: "Gulab Jamun", description: "Deep-fried milk dumplings in sugar syrup", price: 80, category: "Desserts", is_available: true },
  { id: "seed-6", name: "Dal Makhani", description: "Slow-cooked black lentils in butter", price: 190, category: "Main Course", is_available: true },
  { id: "seed-7", name: "Samosa", description: "Crispy pastry with spiced potato filling", price: 30, category: "Snacks", is_available: true },
  { id: "seed-8", name: "Chicken Biryani", description: "Hyderabadi style dum biryani", price: 280, category: "Main Course", is_available: true },
];

function ensureSeeded(): MenuItem[] {
  let items = getLocalItems();
  if (items.length === 0) {
    items = SEED_ITEMS;
    saveLocalItems(items);
  }
  return items;
}

/* ─── Service ──────────────────────────────────────────────────────────── */

export const MenuService = {
  getMenuItems: async (params?: Record<string, unknown>): Promise<PaginatedResponse<MenuItem> | MenuItem[]> => {
    try {
      const response = await api.get("/menu", { params });
      return response.data;
    } catch {
      // Fallback: return local items
      return ensureSeeded();
    }
  },

  getMenuItem: async (id: string): Promise<MenuItem> => {
    try {
      const response = await api.get(`/menu/${id}`);
      return response.data;
    } catch {
      const items = ensureSeeded();
      const found = items.find((i) => i.id === id);
      if (!found) throw new Error("Item not found");
      return found;
    }
  },

  createMenuItem: async (data: Partial<MenuItem>): Promise<MenuItem> => {
    try {
      const response = await api.post("/menu", data);
      const created = response.data;
      // Also save locally so it persists if backend goes down
      const items = getLocalItems();
      items.unshift(created);
      saveLocalItems(items);
      return created;
    } catch {
      // Fallback: create locally
      const newItem: MenuItem = {
        id: `local-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
        name: data.name || "Untitled",
        description: data.description || "",
        price: data.price || 0,
        category: data.category || "Main Course",
        is_available: true,
        created_at: new Date().toISOString(),
      };
      const items = ensureSeeded();
      items.unshift(newItem);
      saveLocalItems(items);
      return newItem;
    }
  },

  updateMenuItem: async (id: string, data: Partial<MenuItem>): Promise<MenuItem> => {
    try {
      const response = await api.put(`/menu/${id}`, data);
      const updated = response.data;
      // Sync locally
      const items = getLocalItems().map((i) => (i.id === id ? { ...i, ...updated } : i));
      saveLocalItems(items);
      return updated;
    } catch {
      // Fallback: update locally
      const items = ensureSeeded();
      const idx = items.findIndex((i) => i.id === id);
      if (idx === -1) throw new Error("Item not found");
      const updated = { ...items[idx], ...data, updated_at: new Date().toISOString() };
      items[idx] = updated as MenuItem;
      saveLocalItems(items);
      return updated as MenuItem;
    }
  },

  deleteMenuItem: async (id: string): Promise<void> => {
    try {
      await api.delete(`/menu/${id}`);
    } catch {
      // Fallback: delete locally — still works
    }
    // Always remove from local store
    const items = getLocalItems().filter((i) => i.id !== id);
    saveLocalItems(items);
  },
};
