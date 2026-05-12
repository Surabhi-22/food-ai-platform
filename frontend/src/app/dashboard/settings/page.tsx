"use client";

import { useState } from "react";
import { Save, User, Bell, Shield, Palette, Globe, Database } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

/* ------------------------------------------------------------------ */
/* Settings Page                                                        */
/* ------------------------------------------------------------------ */

const SECTIONS = [
  { id: "profile", label: "Profile", icon: User },
  { id: "notifications", label: "Notifications", icon: Bell },
  { id: "security", label: "Security", icon: Shield },
  { id: "appearance", label: "Appearance", icon: Palette },
  { id: "integrations", label: "Integrations", icon: Globe },
  { id: "data", label: "Data & Storage", icon: Database },
];

export default function SettingsPage() {
  const [activeSection, setActiveSection] = useState("profile");
  const [isSaving, setIsSaving] = useState(false);

  // Profile form state
  const [profile, setProfile] = useState({
    businessName: "",
    email: "",
    phone: "",
    address: "",
    currency: "INR",
    timezone: "Asia/Kolkata",
  });

  // Notification state
  const [notifications, setNotifications] = useState({
    emailAlerts: true,
    orderNotifications: true,
    forecastReady: true,
    weeklyReport: false,
    stockAlerts: true,
  });

  const handleSave = async () => {
    setIsSaving(true);
    await new Promise((r) => setTimeout(r, 800));
    setIsSaving(false);
    toast.success("Settings saved successfully");
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-3xl font-bold tracking-tight">Settings</h2>
          <p className="text-muted-foreground">Manage your account and platform preferences.</p>
        </div>
        <Button onClick={handleSave} disabled={isSaving}>
          <Save className="mr-2 h-4 w-4" />
          {isSaving ? "Saving..." : "Save Changes"}
        </Button>
      </div>

      <div className="flex flex-col gap-6 md:flex-row">
        {/* Sidebar nav */}
        <nav className="flex flex-row gap-1 md:flex-col md:w-48 shrink-0">
          {SECTIONS.map((section) => {
            const Icon = section.icon;
            return (
              <button
                key={section.id}
                onClick={() => setActiveSection(section.id)}
                className={`flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium transition-colors w-full text-left ${
                  activeSection === section.id
                    ? "bg-primary text-primary-foreground"
                    : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
                }`}
              >
                <Icon className="h-4 w-4 shrink-0" />
                {section.label}
              </button>
            );
          })}
        </nav>

        {/* Content */}
        <div className="flex-1 space-y-4">
          {/* Profile */}
          {activeSection === "profile" && (
            <Card>
              <CardHeader>
                <CardTitle>Business Profile</CardTitle>
                <CardDescription>Update your business information and contact details.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid gap-4 md:grid-cols-2">
                  <div className="space-y-2">
                    <Label htmlFor="businessName">Business Name</Label>
                    <Input
                      id="businessName"
                      value={profile.businessName}
                      onChange={(e) => setProfile({ ...profile, businessName: e.target.value })}
                      placeholder="Your restaurant name"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="email">Email Address</Label>
                    <Input
                      id="email"
                      type="email"
                      value={profile.email}
                      onChange={(e) => setProfile({ ...profile, email: e.target.value })}
                      placeholder="you@example.com"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="phone">Phone Number</Label>
                    <Input
                      id="phone"
                      value={profile.phone}
                      onChange={(e) => setProfile({ ...profile, phone: e.target.value })}
                      placeholder="+91 98765 43210"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="address">Business Address</Label>
                    <Input
                      id="address"
                      value={profile.address}
                      onChange={(e) => setProfile({ ...profile, address: e.target.value })}
                      placeholder="Street, City, State"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="currency">Currency</Label>
                    <select
                      id="currency"
                      value={profile.currency}
                      onChange={(e) => setProfile({ ...profile, currency: e.target.value })}
                      className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                    >
                      <option value="INR">₹ Indian Rupee (INR)</option>
                      <option value="USD">$ US Dollar (USD)</option>
                      <option value="EUR">€ Euro (EUR)</option>
                    </select>
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="timezone">Timezone</Label>
                    <select
                      id="timezone"
                      value={profile.timezone}
                      onChange={(e) => setProfile({ ...profile, timezone: e.target.value })}
                      className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                    >
                      <option value="Asia/Kolkata">Asia/Kolkata (IST)</option>
                      <option value="UTC">UTC</option>
                      <option value="America/New_York">America/New_York (EST)</option>
                    </select>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Notifications */}
          {activeSection === "notifications" && (
            <Card>
              <CardHeader>
                <CardTitle>Notification Preferences</CardTitle>
                <CardDescription>Choose what alerts and updates you want to receive.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                {[
                  { key: "emailAlerts", label: "Email Alerts", desc: "Receive important alerts via email" },
                  { key: "orderNotifications", label: "New Orders", desc: "Get notified when new orders arrive" },
                  { key: "forecastReady", label: "Forecast Ready", desc: "Notified when ML forecast is generated" },
                  { key: "weeklyReport", label: "Weekly Report", desc: "Receive a weekly analytics summary" },
                  { key: "stockAlerts", label: "Stock Alerts", desc: "Alerts when inventory runs low" },
                ].map(({ key, label, desc }) => (
                  <div key={key} className="flex items-center justify-between rounded-lg border p-4">
                    <div>
                      <p className="font-medium">{label}</p>
                      <p className="text-sm text-muted-foreground">{desc}</p>
                    </div>
                    <button
                      onClick={() =>
                        setNotifications((prev) => ({ ...prev, [key]: !prev[key as keyof typeof prev] }))
                      }
                      className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                        notifications[key as keyof typeof notifications] ? "bg-primary" : "bg-muted"
                      }`}
                    >
                      <span
                        className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                          notifications[key as keyof typeof notifications] ? "translate-x-6" : "translate-x-1"
                        }`}
                      />
                    </button>
                  </div>
                ))}
              </CardContent>
            </Card>
          )}

          {/* Security */}
          {activeSection === "security" && (
            <Card>
              <CardHeader>
                <CardTitle>Security Settings</CardTitle>
                <CardDescription>Manage your password and account security.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="currentPassword">Current Password</Label>
                  <Input id="currentPassword" type="password" placeholder="Enter current password" />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="newPassword">New Password</Label>
                  <Input id="newPassword" type="password" placeholder="Minimum 8 characters" />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="confirmPassword">Confirm New Password</Label>
                  <Input id="confirmPassword" type="password" placeholder="Repeat new password" />
                </div>
                <Button onClick={() => toast.success("Password updated successfully")}>
                  Update Password
                </Button>
              </CardContent>
            </Card>
          )}

          {/* Appearance */}
          {activeSection === "appearance" && (
            <Card>
              <CardHeader>
                <CardTitle>Appearance</CardTitle>
                <CardDescription>Customize the look and feel of your dashboard.</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-3 gap-4">
                  {["Light", "Dark", "System"].map((theme) => (
                    <button
                      key={theme}
                      onClick={() => toast.info(`Theme: ${theme} (coming soon)`)}
                      className="flex flex-col items-center gap-2 rounded-lg border-2 border-muted p-4 hover:border-primary transition-colors"
                    >
                      <div className={`h-10 w-16 rounded-md ${
                        theme === "Light" ? "bg-white border" :
                        theme === "Dark" ? "bg-slate-900" : "bg-gradient-to-r from-white to-slate-900"
                      }`} />
                      <span className="text-sm font-medium">{theme}</span>
                    </button>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}

          {/* Integrations */}
          {activeSection === "integrations" && (
            <Card>
              <CardHeader>
                <CardTitle>API Integrations</CardTitle>
                <CardDescription>Connect external services to enhance platform capabilities.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                {[
                  { name: "OpenAI", desc: "Powers the AI assistant. Required for chat features.", status: "Not configured" },
                  { name: "Pinecone", desc: "Vector database for AI context memory.", status: "Not configured" },
                  { name: "OpenWeatherMap", desc: "Weather-based demand forecasting.", status: "Not configured" },
                ].map((integration) => (
                  <div key={integration.name} className="flex items-center justify-between rounded-lg border p-4">
                    <div>
                      <p className="font-medium">{integration.name}</p>
                      <p className="text-sm text-muted-foreground">{integration.desc}</p>
                    </div>
                    <span className="text-xs text-amber-600 bg-amber-50 px-2 py-1 rounded-full border border-amber-200">
                      {integration.status}
                    </span>
                  </div>
                ))}
                <p className="text-xs text-muted-foreground">
                  To configure API keys, update <code className="bg-muted px-1 rounded">backend/.env</code>
                </p>
              </CardContent>
            </Card>
          )}

          {/* Data */}
          {activeSection === "data" && (
            <Card>
              <CardHeader>
                <CardTitle>Data & Storage</CardTitle>
                <CardDescription>Manage your data, exports, and storage settings.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="rounded-lg border p-4 space-y-3">
                  <p className="font-medium">Database</p>
                  <p className="text-sm text-muted-foreground">Connected to Supabase PostgreSQL</p>
                  <div className="flex gap-2">
                    <Button variant="outline" size="sm" onClick={() => toast.success("Export initiated")}>
                      Export All Data (CSV)
                    </Button>
                  </div>
                </div>
                <div className="rounded-lg border border-red-200 bg-red-50 p-4 space-y-2">
                  <p className="font-medium text-red-700">Danger Zone</p>
                  <p className="text-sm text-red-600">Permanently delete all orders and forecast data. This cannot be undone.</p>
                  <Button
                    variant="destructive"
                    size="sm"
                    onClick={() => toast.error("Feature disabled in this environment")}
                  >
                    Delete All Data
                  </Button>
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
