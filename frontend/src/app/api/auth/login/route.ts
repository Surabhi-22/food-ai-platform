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

    if (!accessToken) {
      return NextResponse.json(
        { error: "Authentication failed: no token received from backend" },
        { status: 500 }
      );
    }

    // Create response — return token in body so frontend can store it for API calls
    const nextResponse = NextResponse.json(
      { success: true, user: { email }, access_token: accessToken },
      { status: 200 }
    );

    // Set HTTPOnly cookie with JWT
    nextResponse.cookies.set({
      name: "auth_token",
      value: accessToken,
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
