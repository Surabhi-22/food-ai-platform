import { NextResponse } from "next/server";

export async function POST() {
  const response = NextResponse.json({ success: true }, { status: 200 });

  // Clear the auth cookie
  response.cookies.set({
    name: "auth_token",
    value: "",
    httpOnly: true,
    path: "/",
    expires: new Date(0),
  });

  return response;
}
