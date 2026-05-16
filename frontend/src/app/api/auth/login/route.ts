import { NextResponse } from "next/server";
import axios from "axios";

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const { email, password } = body;

    const backendUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

    const response = await axios.post(`${backendUrl}/auth/login`, {
      email,
      password,
    });

    const data = response.data;

    // FastAPI returns: { tokens: { access_token, refresh_token }, vendor: {...} }
    const accessToken = data?.tokens?.access_token;
    const refreshToken = data?.tokens?.refresh_token;

    if (!accessToken || !refreshToken) {
      return NextResponse.json(
        { error: "Authentication failed: tokens not received from backend" },
        { status: 500 }
      );
    }

    // Create response — return tokens in body so frontend can store them
    const nextResponse = NextResponse.json(
      { success: true, user: { email }, access_token: accessToken, refresh_token: refreshToken },
      { status: 200 }
    );

    // Set HTTPOnly cookies with JWTs
    nextResponse.cookies.set({
      name: "access_token",
      value: accessToken,
      httpOnly: true,
      path: "/",
      sameSite: "lax",
      maxAge: 60 * 60, // 1 hour
    });

    nextResponse.cookies.set({
      name: "refresh_token",
      value: refreshToken,
      httpOnly: true,
      path: "/",
      sameSite: "lax",
      maxAge: 60 * 60 * 24 * 7, // 7 days
    });

    return nextResponse;
  } catch (error: any) {
    console.error("Login API Error:", error.response?.data || error.message);
    return NextResponse.json(
      { error: error.response?.data?.detail || "Authentication failed" },
      { status: error.response?.status || 401 }
    );
  }
}
