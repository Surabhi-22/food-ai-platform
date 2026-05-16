"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { z } from "zod";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { toast } from "sonner";
import { UtensilsCrossed, Loader2 } from "lucide-react";
import axios from "axios";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { AuthService } from "@/services/auth.service";

const registerSchema = z
  .object({
    business_name: z.string().min(2, "Business name is required"),
    email: z.string().email("Please enter a valid email address"),
    password: z.string().min(8, "Password must be at least 8 characters"),
    confirmPassword: z.string(),
  })
  .refine((data) => data.password === data.confirmPassword, {
    message: "Passwords do not match",
    path: ["confirmPassword"],
  });

type RegisterFormValues = z.infer<typeof registerSchema>;

export default function RegisterPage() {
  const router = useRouter();
  const [isLoading, setIsLoading] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<RegisterFormValues>({
    resolver: zodResolver(registerSchema),
  });

  const onSubmit = async (data: RegisterFormValues) => {
    setIsLoading(true);
    try {
      await AuthService.register({
        business_name: data.business_name,
        email: data.email,
        password: data.password,
      });

      toast.success("Account created successfully");
      router.push("/dashboard");
    } catch (error: any) {
      toast.error(error.response?.data?.detail || "Registration failed");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-primary/10 via-background to-background px-4 py-12 sm:px-6 lg:px-8 overflow-hidden relative">
      {/* Decorative blurred blobs */}
      <div className="pointer-events-none absolute inset-0 flex items-center justify-center opacity-30">
        <div className="absolute h-[50vh] w-[50vw] rounded-full bg-primary/20 blur-[120px]"></div>
      </div>

      <div className="relative w-full max-w-md space-y-8 animate-in fade-in zoom-in-95 duration-700">
        <div className="flex flex-col items-center justify-center text-center">
          <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-primary to-indigo-600 shadow-xl ring-4 ring-primary/10 mb-2">
            <UtensilsCrossed className="h-8 w-8 text-primary-foreground" />
          </div>
          <h2 className="mt-6 text-3xl font-black tracking-tight bg-gradient-to-r from-primary to-indigo-600 bg-clip-text text-transparent">
            Create an account
          </h2>
          <p className="mt-2 text-sm font-medium text-muted-foreground">
            Start optimizing your food business today
          </p>
        </div>

        <Card className="glass-card shadow-2xl border-primary/10 backdrop-blur-xl bg-background/80 relative overflow-hidden">
          <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-transparent via-primary/30 to-transparent"></div>
          <CardHeader className="pb-4">
            <CardDescription className="text-center font-medium">Enter your details to create your vendor account.</CardDescription>
          </CardHeader>
          <form onSubmit={handleSubmit(onSubmit)}>
            <CardContent className="space-y-4">
              <div className="space-y-2 group">
                <Label htmlFor="business_name" className="text-xs font-bold uppercase tracking-wider text-muted-foreground group-focus-within:text-primary transition-colors">Business Name</Label>
                <Input
                  id="business_name"
                  placeholder="Acme Foods"
                  {...register("business_name")}
                  className={cn(
                    "h-12 bg-background/50 border-primary/10 focus-visible:ring-primary/30 focus-visible:border-primary transition-all",
                    errors.business_name && "border-destructive focus-visible:ring-destructive/30"
                  )}
                />
                {errors.business_name && (
                  <p className="text-xs font-semibold text-destructive animate-in fade-in slide-in-from-top-1">{errors.business_name.message}</p>
                )}
              </div>
              <div className="space-y-2 group">
                <Label htmlFor="email" className="text-xs font-bold uppercase tracking-wider text-muted-foreground group-focus-within:text-primary transition-colors">Email address</Label>
                <Input
                  id="email"
                  type="email"
                  placeholder="name@example.com"
                  {...register("email")}
                  className={cn(
                    "h-12 bg-background/50 border-primary/10 focus-visible:ring-primary/30 focus-visible:border-primary transition-all",
                    errors.email && "border-destructive focus-visible:ring-destructive/30"
                  )}
                />
                {errors.email && (
                  <p className="text-xs font-semibold text-destructive animate-in fade-in slide-in-from-top-1">{errors.email.message}</p>
                )}
              </div>
              <div className="space-y-2 group">
                <Label htmlFor="password" className="text-xs font-bold uppercase tracking-wider text-muted-foreground group-focus-within:text-primary transition-colors">Password</Label>
                <Input
                  id="password"
                  type="password"
                  placeholder="••••••••"
                  {...register("password")}
                  className={cn(
                    "h-12 bg-background/50 border-primary/10 focus-visible:ring-primary/30 focus-visible:border-primary transition-all",
                    errors.password && "border-destructive focus-visible:ring-destructive/30"
                  )}
                />
                {errors.password && (
                  <p className="text-xs font-semibold text-destructive animate-in fade-in slide-in-from-top-1">{errors.password.message}</p>
                )}
              </div>
              <div className="space-y-2 group">
                <Label htmlFor="confirmPassword" className="text-xs font-bold uppercase tracking-wider text-muted-foreground group-focus-within:text-primary transition-colors">Confirm Password</Label>
                <Input
                  id="confirmPassword"
                  type="password"
                  placeholder="••••••••"
                  {...register("confirmPassword")}
                  className={cn(
                    "h-12 bg-background/50 border-primary/10 focus-visible:ring-primary/30 focus-visible:border-primary transition-all",
                    errors.confirmPassword && "border-destructive focus-visible:ring-destructive/30"
                  )}
                />
                {errors.confirmPassword && (
                  <p className="text-xs font-semibold text-destructive animate-in fade-in slide-in-from-top-1">{errors.confirmPassword.message}</p>
                )}
              </div>
            </CardContent>
            <CardFooter className="flex flex-col space-y-4 pt-4">
              <Button type="submit" className="w-full h-12 text-base font-bold shadow-lg shadow-primary/25 hover:-translate-y-0.5 transition-all duration-300" disabled={isLoading}>
                {isLoading ? (
                  <>
                    <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                    Creating account...
                  </>
                ) : (
                  "Create account"
                )}
              </Button>
              <p className="text-center text-sm text-muted-foreground font-medium">
                Already have an account?{" "}
                <a href="/login" className="font-bold text-primary hover:text-indigo-600 hover:underline transition-colors">
                  Sign in
                </a>
              </p>
            </CardFooter>
          </form>
        </Card>
      </div>
    </div>
  );
}
