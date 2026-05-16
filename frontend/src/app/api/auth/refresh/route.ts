import { NextResponse } from "next/server";
import { cookies } from "next/headers";
import axios from "axios";

export async function POST() {
  try {
    const cookieStore = await cookies();
    const refreshToken = cookieStore.get("refresh_token")?.value;

    if (!refreshToken) {
      return NextResponse.json({ error: "No refresh token available" }, { status: 401 });
    }

    const backendUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

    // Backend expects { refresh_token: "..." } in the request body
    const response = await axios.post(`${backendUrl}/auth/refresh`, {
      refresh_token: refreshToken,
    });

    const newAccessToken = response.data?.access_token;
    const newRefreshToken = response.data?.refresh_token;

    if (!newAccessToken) {
      return NextResponse.json({ error: "Token refresh failed: no token returned" }, { status: 401 });
    }

    const nextResponse = NextResponse.json(
      { access_token: newAccessToken },
      { status: 200 }
    );

    // Rotate access token cookie
    nextResponse.cookies.set({
      name: "access_token",
      value: newAccessToken,
      httpOnly: true,
      path: "/",
      sameSite: "lax",
      maxAge: 60 * 60, // 1 hour
    });

    // Rotate refresh token cookie if backend returned a new one
    if (newRefreshToken) {
      nextResponse.cookies.set({
        name: "refresh_token",
        value: newRefreshToken,
        httpOnly: true,
        path: "/",
        sameSite: "lax",
        maxAge: 60 * 60 * 24 * 7, // 7 days
      });
    }

    return nextResponse;
  } catch {
    // Clear bad cookies and force re-login
    const res = NextResponse.json({ error: "Token refresh failed" }, { status: 401 });
    res.cookies.set({ name: "access_token", value: "", path: "/", expires: new Date(0) });
    res.cookies.set({ name: "refresh_token", value: "", path: "/", expires: new Date(0) });
    return res;
  }
}
