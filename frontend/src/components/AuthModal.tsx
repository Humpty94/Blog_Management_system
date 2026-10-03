"use client";

import React, { useState } from "react";
import { CheckCircle2, KeyRound, Loader2, Mail, User, X } from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { api } from "../lib/api";

interface AuthModalProps {
  isOpen: boolean;
  onClose: () => void;
  defaultMode?: "login" | "register" | "verify";
}

export function AuthModal({
  isOpen,
  onClose,
  defaultMode = "login",
}: AuthModalProps) {
  const { login, register, refreshUser } = useAuth();
  const [mode, setMode] = useState<"login" | "register" | "verify">(defaultMode);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  // Form states
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [username, setUsername] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [verifyToken, setVerifyToken] = useState("");

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccess(null);
    setLoading(true);

    try {
      if (mode === "login") {
        await login({ email, password });
        onClose();
      } else if (mode === "register") {
        const res = await register({
          email,
          username,
          password,
          display_name: displayName,
        });
        setSuccess(
          res.message ||
            "Registration successful! Please check your email or enter your verification token."
        );
        setMode("verify");
      } else if (mode === "verify") {
        const res = await api.verifyEmail(verifyToken.trim());
        setSuccess(res.message || "Email verified successfully! You can now log in.");
        await refreshUser();
        setTimeout(() => {
          setMode("login");
          setSuccess(null);
        }, 1500);
      }
    } catch (err: unknown) {
      const e = err as { message?: string };
      setError(e.message || "An unexpected error occurred. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
      <div className="relative w-full max-w-md rounded-2xl bg-white dark:bg-zinc-900 p-8 shadow-2xl border border-zinc-200 dark:border-zinc-800">
        <button
          onClick={onClose}
          className="absolute right-5 top-5 p-1 rounded-full text-zinc-400 hover:text-zinc-700 dark:hover:text-zinc-200 transition-colors"
        >
          <X className="w-5 h-5" />
        </button>

        {/* Modal Header */}
        <div className="text-center mb-6">
          <div className="inline-flex items-center justify-center w-12 h-12 rounded-xl bg-zinc-900 dark:bg-white text-white dark:text-zinc-900 font-bold text-xl mb-3 shadow-md">
            G
          </div>
          <h2 className="text-2xl font-bold tracking-tight text-zinc-900 dark:text-white">
            {mode === "login" && "Welcome back"}
            {mode === "register" && "Join the publication"}
            {mode === "verify" && "Verify your email"}
          </h2>
          <p className="text-sm text-zinc-500 dark:text-zinc-400 mt-1">
            {mode === "login" && "Enter your credentials to access your account."}
            {mode === "register" && "Create an author account to publish and engage."}
            {mode === "verify" && "Enter the single-use token sent to your email."}
          </p>
        </div>

        {error && (
          <div className="mb-4 rounded-lg bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-900/50 p-3 text-sm text-red-600 dark:text-red-400">
            {error}
          </div>
        )}

        {success && (
          <div className="mb-4 flex items-center gap-2 rounded-lg bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-200 dark:border-emerald-900/50 p-3 text-sm text-emerald-700 dark:text-emerald-400">
            <CheckCircle2 className="w-4 h-4 shrink-0" />
            <span>{success}</span>
          </div>
        )}

        {/* Form Body */}
        <form onSubmit={handleSubmit} className="space-y-4">
          {mode === "register" && (
            <>
              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-zinc-500 mb-1.5">
                  Username
                </label>
                <div className="relative">
                  <User className="absolute left-3 top-3 w-4 h-4 text-zinc-400" />
                  <input
                    type="text"
                    required
                    value={username}
                    onChange={(e) => setUsername(e.target.value.toLowerCase())}
                    placeholder="alex_dev"
                    className="w-full pl-9 pr-3 py-2 text-sm rounded-lg border border-zinc-200 dark:border-zinc-800 bg-zinc-50 dark:bg-zinc-800/50 text-zinc-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-zinc-900 dark:focus:ring-white transition"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-zinc-500 mb-1.5">
                  Display Name
                </label>
                <input
                  type="text"
                  value={displayName}
                  onChange={(e) => setDisplayName(e.target.value)}
                  placeholder="Alex Rivers"
                  className="w-full px-3 py-2 text-sm rounded-lg border border-zinc-200 dark:border-zinc-800 bg-zinc-50 dark:bg-zinc-800/50 text-zinc-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-zinc-900 dark:focus:ring-white transition"
                />
              </div>
            </>
          )}

          {(mode === "login" || mode === "register") && (
            <>
              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-zinc-500 mb-1.5">
                  Email Address
                </label>
                <div className="relative">
                  <Mail className="absolute left-3 top-3 w-4 h-4 text-zinc-400" />
                  <input
                    type="email"
                    required
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="alex@example.com"
                    className="w-full pl-9 pr-3 py-2 text-sm rounded-lg border border-zinc-200 dark:border-zinc-800 bg-zinc-50 dark:bg-zinc-800/50 text-zinc-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-zinc-900 dark:focus:ring-white transition"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-zinc-500 mb-1.5">
                  Password
                </label>
                <div className="relative">
                  <KeyRound className="absolute left-3 top-3 w-4 h-4 text-zinc-400" />
                  <input
                    type="password"
                    required
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="••••••••••••"
                    className="w-full pl-9 pr-3 py-2 text-sm rounded-lg border border-zinc-200 dark:border-zinc-800 bg-zinc-50 dark:bg-zinc-800/50 text-zinc-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-zinc-900 dark:focus:ring-white transition"
                  />
                </div>
              </div>
            </>
          )}

          {mode === "verify" && (
            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-zinc-500 mb-1.5">
                Verification Token
              </label>
              <textarea
                required
                rows={3}
                value={verifyToken}
                onChange={(e) => setVerifyToken(e.target.value)}
                placeholder="Paste the token sent to your email..."
                className="w-full px-3 py-2 text-sm rounded-lg border border-zinc-200 dark:border-zinc-800 bg-zinc-50 dark:bg-zinc-800/50 text-zinc-900 dark:text-white font-mono focus:outline-none focus:ring-2 focus:ring-zinc-900 dark:focus:ring-white transition"
              />
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full flex items-center justify-center gap-2 py-2.5 px-4 rounded-lg bg-zinc-900 hover:bg-zinc-800 dark:bg-white dark:hover:bg-zinc-100 text-white dark:text-zinc-900 font-semibold text-sm transition-all shadow-md active:scale-[0.98] disabled:opacity-50"
          >
            {loading && <Loader2 className="w-4 h-4 animate-spin" />}
            {mode === "login" && "Sign In"}
            {mode === "register" && "Create Account"}
            {mode === "verify" && "Verify Email"}
          </button>
        </form>

        {/* Mode Switchers */}
        <div className="mt-6 text-center text-xs text-zinc-500 space-y-2">
          {mode === "login" && (
            <div>
              Don&apos;t have an account?{" "}
              <button
                type="button"
                onClick={() => {
                  setError(null);
                  setMode("register");
                }}
                className="font-semibold text-zinc-900 dark:text-white hover:underline"
              >
                Sign up
              </button>
              {" · "}
              <button
                type="button"
                onClick={() => {
                  setError(null);
                  setMode("verify");
                }}
                className="hover:underline"
              >
                Verify token
              </button>
            </div>
          )}

          {mode === "register" && (
            <div>
              Already have an account?{" "}
              <button
                type="button"
                onClick={() => {
                  setError(null);
                  setMode("login");
                }}
                className="font-semibold text-zinc-900 dark:text-white hover:underline"
              >
                Sign in
              </button>
            </div>
          )}

          {mode === "verify" && (
            <div>
              Back to{" "}
              <button
                type="button"
                onClick={() => {
                  setError(null);
                  setMode("login");
                }}
                className="font-semibold text-zinc-900 dark:text-white hover:underline"
              >
                Sign in
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
