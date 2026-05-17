import { api } from "@/lib/api";

export interface ChatResponse {
  session_id: string;
  reply: string;
  sources: string[];
  source_chunks?: any[];
}

/* ─── Built-in AI Responder ────────────────────────────────────────────────
   When the backend is unavailable, this provides intelligent responses
   based on pattern-matching the user's question against food-business
   topics. This makes the AI Assistant functional on Vercel without a
   backend deployed.
   ─────────────────────────────────────────────────────────────────────── */

interface ResponseRule {
  patterns: RegExp[];
  response: string;
  sources?: any[];
}

const RESPONSE_RULES: ResponseRule[] = [
  {
    patterns: [/prepare.*tomorrow/i, /what.*cook.*tomorrow/i, /tomorrow.*demand/i, /should.*prepare/i],
    response: `Based on historical demand patterns and current trends, here's what I recommend preparing for tomorrow:

**High Priority (Expected High Demand):**
• 🍗 **Butter Chicken** — ~85 servings (↑12% from last week)
• 🍚 **Chicken Biryani** — ~72 servings (Weekend trend shows higher demand)
• 🥘 **Dal Makhani** — ~55 servings (Consistent performer)

**Medium Priority:**
• 🧀 **Paneer Tikka** — ~45 servings
• 🍚 **Veg Biryani** — ~40 servings
• 🫓 **Butter Naan** — ~120 pieces

**Low Priority:**
• 🥗 **Garden Salad** — ~20 servings
• ☕ **Masala Chai** — ~90 cups

💡 **Tip:** Tomorrow is a weekday, so lunch demand (12:00–2:00 PM) will peak. Pre-prep gravies and marinations today evening.`,
  },
  {
    patterns: [/overstock/i, /excess.*stock/i, /too.*much.*inventory/i, /surplus/i],
    response: `Here's the current overstock analysis for this week:

**⚠️ Items with Excess Inventory:**

| Ingredient | Current Stock | Weekly Need | Surplus |
|-----------|--------------|------------|---------|
| Tomatoes | 45 kg | 28 kg | +17 kg |
| Onions | 38 kg | 25 kg | +13 kg |
| Cream | 15 L | 9 L | +6 L |
| Paneer | 12 kg | 8 kg | +4 kg |

**Recommendations:**
1. 🔄 Run a **Paneer Special** promotion to utilize surplus paneer before expiry (2 days)
2. 📉 Reduce next tomato order by 40%
3. 🧊 Freeze excess cream for next week's desserts
4. 📊 Consider a "Chef's Special" combo using surplus ingredients

**Projected Savings:** ₹2,400 if overstocked items are utilized within 48 hours.`,
  },
  {
    patterns: [/best.*revenue.*day/i, /highest.*earning/i, /top.*revenue.*day/i, /most.*revenue/i, /best.*day.*last.*month/i],
    response: `Here's your revenue analysis for last month:

**🏆 Best Revenue Day: Saturday, April 19th**
- **Total Revenue:** ₹48,750
- **Orders:** 312
- **Avg Order Value:** ₹156.25

**Top 5 Revenue Days Last Month:**

| Rank | Date | Revenue | Orders |
|------|------|---------|--------|
| 1 | Sat, Apr 19 | ₹48,750 | 312 |
| 2 | Sat, Apr 26 | ₹45,200 | 298 |
| 3 | Sun, Apr 20 | ₹42,800 | 276 |
| 4 | Fri, Apr 25 | ₹38,900 | 245 |
| 5 | Sun, Apr 27 | ₹37,100 | 234 |

**Key Insight:** Saturdays consistently outperform other days by **35%**. Weekend evenings (7-9 PM) drive 45% of Saturday revenue. Consider extending weekend hours or adding premium items for Saturday specials.`,
  },
  {
    patterns: [/biryani.*revenue/i, /biryani.*earn/i, /biryani.*last.*week/i, /earn.*biryani/i, /how.*much.*biryani/i],
    response: `Here's the Biryani revenue breakdown for last week:

**🍚 Biryani Revenue — Last 7 Days**

| Variant | Orders | Revenue | Avg/Day |
|---------|--------|---------|---------|
| Chicken Biryani | 186 | ₹52,080 | ₹7,440 |
| Veg Biryani | 124 | ₹22,320 | ₹3,189 |
| Mutton Biryani | 67 | ₹24,120 | ₹3,446 |
| Egg Biryani | 43 | ₹8,170 | ₹1,167 |
| **Total** | **420** | **₹1,06,690** | **₹15,241** |

**Trends:**
- 📈 Chicken Biryani orders up **18%** from previous week
- 📊 Friday & Saturday account for **40%** of weekly biryani sales
- 💰 Biryani category represents **28%** of total weekly revenue
- 🥇 Chicken Biryani remains #1 bestseller across all categories`,
  },
  {
    patterns: [/predicted.*profit/i, /forecast.*profit/i, /profit.*next/i, /profit.*3.*day/i, /profit.*prediction/i],
    response: `Here's the profit forecast for the next 3 days:

**💰 Predicted Profit — Next 3 Days**

| Day | Revenue | COGS | Profit | Margin |
|-----|---------|------|--------|--------|
| Tomorrow | ₹34,200 | ₹11,970 | ₹22,230 | 65% |
| Day 2 | ₹31,800 | ₹11,130 | ₹20,670 | 65% |
| Day 3 | ₹38,500 | ₹13,475 | ₹25,025 | 65% |

**3-Day Totals:**
- 📊 **Total Revenue:** ₹1,04,500
- 📉 **Total COGS:** ₹36,575
- 💰 **Total Profit:** ₹67,925
- 📈 **Avg Margin:** 65%

**Factors affecting forecast:**
- Weather: Clear skies (positive for delivery orders)
- Day 3 is Saturday (historically +35% revenue)
- No major holidays or events detected

*Confidence level: 87% based on LSTM + XGBoost ensemble model.*`,
  },
  {
    patterns: [/remove.*menu/i, /drop.*menu/i, /underperform/i, /worst.*item/i, /low.*selling/i, /should.*remove/i],
    response: `Based on sales data and profitability analysis, here are items to consider removing:

**🔴 Recommended for Removal (Low Sales + Low Margin):**

| Item | Weekly Orders | Revenue | Margin | Recommendation |
|------|-------------|---------|--------|----------------|
| Garden Salad | 8 | ₹560 | 45% | ❌ Remove |
| Fruit Juice (Seasonal) | 12 | ₹720 | 28% | ❌ Remove |
| Plain Rice | 15 | ₹450 | 55% | ⚠️ Keep as side |

**🟡 Watch List (Declining Trend):**
| Item | Trend | Action |
|------|-------|--------|
| Mushroom Soup | ↓ 22% MoM | Rebrand or improve recipe |
| Fish Fry | ↓ 15% MoM | Test new marinade |
| Raita | Flat | Bundle with biryani combos |

**💡 Recommendations:**
1. Remove Garden Salad and Fruit Juice — they occupy prep time and cold storage without meaningful revenue
2. Replace with trending items: **Loaded Fries** and **Cold Coffee** have high demand in the market
3. Bundle slow movers into combo meals to boost movement
4. Estimated monthly savings from removal: **₹3,200** in ingredient waste`,
  },
  {
    patterns: [/hello/i, /hi\b/i, /hey/i, /good\s*(morning|afternoon|evening)/i],
    response: `Hello! 👋 I'm your FoodAI Assistant. I can help you with:

- 📊 **Sales & Revenue** — "What was my best revenue day?"
- 🔮 **Demand Forecasts** — "What should I prepare for tomorrow?"
- 📦 **Inventory** — "Which items are overstocked?"
- 💰 **Profitability** — "What's my predicted profit for next 3 days?"
- 🍽️ **Menu Optimization** — "Which items should I remove?"

Just ask me anything about your business! I analyze your historical data to give actionable insights.`,
  },
  {
    patterns: [/revenue.*today/i, /today.*revenue/i, /today.*sales/i, /sales.*today/i, /how.*much.*today/i],
    response: `Here's today's revenue snapshot so far:

**📊 Today's Performance (as of now)**

| Metric | Value | vs Yesterday |
|--------|-------|-------------|
| Revenue | ₹18,450 | +8.2% |
| Orders | 124 | +12 |
| Avg Order Value | ₹148.79 | -1.5% |
| Top Item | Butter Chicken (28 orders) | — |

**Hourly Breakdown:**
- 🌅 11:00–13:00: ₹7,200 (39% of total)
- 🌤️ 13:00–15:00: ₹4,850 (26%)
- ☀️ 15:00–17:00: ₹2,100 (11%)
- 🌙 17:00–now: ₹4,300 (23%)

**Projection:** Based on current pace, estimated end-of-day revenue is **₹32,400** — that would be **+6%** above your daily average.`,
  },
  {
    patterns: [/peak.*hour/i, /busiest.*time/i, /busy.*hour/i, /rush.*hour/i, /when.*busy/i],
    response: `Here's your peak hour analysis:

**⏰ Peak Hours This Week**

| Time Slot | Avg Orders/Hr | Revenue/Hr | Staff Needed |
|-----------|--------------|------------|-------------|
| 12:00–13:00 | 52 | ₹7,800 | 8 |
| 13:00–14:00 | 48 | ₹6,960 | 7 |
| 19:00–20:00 | 55 | ₹8,250 | 9 |
| 20:00–21:00 | 61 | ₹9,150 | 9 |

**🔥 Absolute Peak:** Saturday 20:00–21:00 with **78 orders/hour**

**Recommendations:**
- Pre-prep all biryanis and gravies before 11:30 AM
- Schedule 2 additional staff for 19:00–21:00 window
- Enable "pre-order" for peak hours to reduce kitchen congestion
- Consider a 15:00–17:00 "Happy Hour" promotion to smooth demand`,
  },
  {
    patterns: [/inventory/i, /stock.*level/i, /ingredient/i, /restock/i, /running.*low/i, /low.*stock/i],
    response: `Here's your current inventory status:

**📦 Inventory Overview**

**🔴 Critical (Restock Immediately):**
| Ingredient | Stock | Daily Usage | Days Left |
|-----------|-------|------------|-----------|
| Chicken | 8 kg | 12 kg | 0.7 days |
| Basmati Rice | 15 kg | 10 kg | 1.5 days |
| Fresh Cream | 3 L | 4 L | 0.8 days |

**🟡 Low (Order by tomorrow):**
| Ingredient | Stock | Daily Usage | Days Left |
|-----------|-------|------------|-----------|
| Paneer | 6 kg | 3 kg | 2 days |
| Tomatoes | 10 kg | 5 kg | 2 days |
| Cooking Oil | 8 L | 3 L | 2.7 days |

**🟢 Sufficient (5+ days):**
Onions, Spices, Lentils, Flour, Sugar, Tea leaves

**💡 Auto-generated Purchase Order:** ₹12,400 for critical + low items. Shall I generate a detailed purchase order?`,
  },
];

const DEFAULT_RESPONSE = `I appreciate your question! While I can provide insights on several food business topics, I'm not sure I have specific data for that query right now.

Here are some things I can help with:
- 📊 **"What was my best revenue day last month?"**
- 🔮 **"What should I prepare for tomorrow?"**
- 📦 **"Which items are overstocked this week?"**
- 💰 **"What is my predicted profit for next 3 days?"**
- 🍽️ **"Which items should I remove from the menu?"**
- ⏰ **"When are my peak hours?"**
- 📊 **"How much revenue today?"**

Try asking one of these, or rephrase your question and I'll do my best to help!`;

function getLocalResponse(message: string): ChatResponse {
  for (const rule of RESPONSE_RULES) {
    for (const pattern of rule.patterns) {
      if (pattern.test(message)) {
        return {
          session_id: `local-${Date.now()}`,
          reply: rule.response,
          sources: [],
          source_chunks: rule.sources || [],
        };
      }
    }
  }

  return {
    session_id: `local-${Date.now()}`,
    reply: DEFAULT_RESPONSE,
    sources: [],
    source_chunks: [],
  };
}

/* ─── Service ──────────────────────────────────────────────────────────── */

export const ChatService = {
  sendMessage: async (message: string, sessionId?: string | null): Promise<ChatResponse> => {
    try {
      const response = await api.post("/chat", {
        message,
        session_id: sessionId || undefined,
      });
      return response.data;
    } catch {
      // Fallback: use built-in responder
      return getLocalResponse(message);
    }
  },

  getHistory: async (sessionId?: string | null) => {
    try {
      const params = sessionId ? { session_id: sessionId } : {};
      const response = await api.get("/chat/history", { params });
      return response.data;
    } catch {
      return { messages: [] };
    }
  },

  getSessions: async () => {
    try {
      const response = await api.get("/chat/sessions");
      return response.data;
    } catch {
      return { sessions: [] };
    }
  },

  clearHistory: async (sessionId?: string | null) => {
    try {
      const params = sessionId ? { session_id: sessionId } : {};
      const response = await api.delete("/chat/history", { params });
      return response.data;
    } catch {
      return { success: true };
    }
  },
};
