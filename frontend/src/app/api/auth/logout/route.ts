import { NextResponse } from "next/server";

export async function POST() {
  const response = NextResponse.json({ success: true }, { status: 200 });

  // Clear all auth cookies
  response.cookies.set({ name: "access_token", value: "", httpOnly: true, path: "/", expires: new Date(0) });
  response.cookies.set({ name: "refresh_token", value: "", httpOnly: true, path: "/", expires: new Date(0) });
  // Clear old cookie name for backwards compatibility
  response.cookies.set({ name: "auth_token", value: "", httpOnly: true, path: "/", expires: new Date(0) });

  return response;
}
