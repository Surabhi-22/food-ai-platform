import { NextResponse } from "next/server";
import { cookies } from "next/headers";
import axios from "axios";

export async function POST() {
  try {
    const cookieStore = await cookies();
    const authToken = cookieStore.get("auth_token")?.value;

    if (!authToken) {
      return NextResponse.json({ error: "No token to refresh" }, { status: 401 });
    }

    const backendUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

    // Attempt to call backend refresh endpoint if it exists
    const response = await axios.post(
      `${backendUrl}/auth/refresh`,
      {},
      { headers: { Authorization: `Bearer ${authToken}` } }
    );

    const newToken = response.data?.access_token;

    const nextResponse = NextResponse.json({ access_token: newToken }, { status: 200 });
    nextResponse.cookies.set({
      name: "auth_token",
      value: newToken,
      httpOnly: true,
      path: "/",
      sameSite: "lax",
      maxAge: 60 * 60 * 24 * 7,
    });

    return nextResponse;
  } catch {
    // Clear bad cookie and force re-login
    const res = NextResponse.json({ error: "Token refresh failed" }, { status: 401 });
    res.cookies.set({ name: "auth_token", value: "", path: "/", expires: new Date(0) });
    return res;
  }
}
