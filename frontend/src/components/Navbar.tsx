"use client";

import React, { useState } from "react";
import Link from "next/link";
import {
  Bookmark,
  CheckCircle,
  FileText,
  LogOut,
  PenSquare,
  Search,
  Sparkles,
  User,
} from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { AuthModal } from "./AuthModal";

interface NavbarProps {
  onSearchClick?: () => void;
}

export function Navbar({ onSearchClick }: NavbarProps) {
  const { user, logout } = useAuth();
  const [authModalOpen, setAuthModalOpen] = useState(false);
  const [userDropdownOpen, setUserDropdownOpen] = useState(false);

  return (
    <>
      <header className="sticky top-0 z-40 w-full border-b border-zinc-200/80 dark:border-zinc-800/80 bg-white/90 dark:bg-zinc-950/90 backdrop-blur-md transition-colors">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between gap-4">
          {/* Left: Brand / Logo */}
          <div className="flex items-center gap-8">
            <Link href="/" className="flex items-center gap-2.5 group">
              <span className="flex items-center justify-center w-8 h-8 rounded-lg bg-zinc-900 dark:bg-white text-white dark:text-zinc-900 font-extrabold text-base tracking-tighter shadow-sm group-hover:scale-105 transition-transform">
                G
              </span>
              <span className="text-xl font-extrabold tracking-tight text-zinc-900 dark:text-white font-serif">
                Ghost<span className="text-zinc-400 font-sans font-medium text-sm ml-1">PRESS</span>
              </span>
            </Link>

            {/* Desktop Navigation */}
            <nav className="hidden md:flex items-center gap-6 text-sm font-medium text-zinc-600 dark:text-zinc-400">
              <Link
                href="/"
                className="hover:text-zinc-900 dark:hover:text-white transition-colors"
              >
                Publication
              </Link>
              <Link
                href="/workspace"
                className="hover:text-zinc-900 dark:hover:text-white transition-colors flex items-center gap-1.5"
              >
                <span>Workspace</span>
                <span className="text-[10px] uppercase font-bold tracking-wider px-1.5 py-0.5 rounded bg-zinc-100 dark:bg-zinc-800 text-zinc-600 dark:text-zinc-400">
                  Studio
                </span>
              </Link>
            </nav>
          </div>

          {/* Right: Actions & User State */}
          <div className="flex items-center gap-3">
            {onSearchClick && (
              <button
                onClick={onSearchClick}
                className="p-2 text-zinc-500 hover:text-zinc-900 dark:hover:text-white rounded-lg hover:bg-zinc-100 dark:hover:bg-zinc-900 transition-colors"
                title="Search articles"
              >
                <Search className="w-4 h-4" />
              </button>
            )}

            {user ? (
              <div className="relative">
                <div className="flex items-center gap-2">
                  <Link
                    href="/workspace?tab=new"
                    className="hidden sm:inline-flex items-center gap-1.5 text-xs font-semibold py-2 px-3 rounded-lg bg-zinc-900 hover:bg-zinc-800 dark:bg-white dark:hover:bg-zinc-100 text-white dark:text-zinc-900 shadow-sm transition-all"
                  >
                    <PenSquare className="w-3.5 h-3.5" />
                    <span>New Post</span>
                  </Link>

                  <button
                    onClick={() => setUserDropdownOpen(!userDropdownOpen)}
                    className="flex items-center gap-2 p-1 pl-2 pr-2.5 rounded-full border border-zinc-200 dark:border-zinc-800 hover:border-zinc-300 dark:hover:border-zinc-700 bg-zinc-50 dark:bg-zinc-900 transition"
                  >
                    <div className="w-7 h-7 rounded-full bg-zinc-900 dark:bg-white text-white dark:text-zinc-900 flex items-center justify-center font-bold text-xs uppercase shadow-inner">
                      {user.username.slice(0, 2)}
                    </div>
                    <span className="text-xs font-semibold text-zinc-800 dark:text-zinc-200 max-w-[100px] truncate">
                      {user.display_name || user.username}
                    </span>
                  </button>
                </div>

                {/* Dropdown Menu */}
                {userDropdownOpen && (
                  <div
                    className="absolute right-0 mt-2 w-56 rounded-xl bg-white dark:bg-zinc-900 shadow-xl border border-zinc-200 dark:border-zinc-800 py-1.5 text-sm z-50 animate-in fade-in slide-in-from-top-1"
                    onClick={() => setUserDropdownOpen(false)}
                  >
                    <div className="px-3.5 py-2 border-b border-zinc-100 dark:border-zinc-800">
                      <p className="font-semibold text-zinc-900 dark:text-white truncate">
                        {user.display_name || user.username}
                      </p>
                      <p className="text-xs text-zinc-500 truncate">{user.email}</p>
                      <div className="mt-1 flex items-center gap-1 text-[11px]">
                        {user.is_email_verified ? (
                          <span className="text-emerald-600 dark:text-emerald-400 flex items-center gap-1 font-medium">
                            <CheckCircle className="w-3 h-3" /> Verified Author
                          </span>
                        ) : (
                          <span className="text-amber-600 dark:text-amber-400 flex items-center gap-1 font-medium">
                            • Email unverified
                          </span>
                        )}
                      </div>
                    </div>

                    <Link
                      href="/workspace"
                      className="flex items-center gap-2.5 px-3.5 py-2 text-zinc-700 dark:text-zinc-300 hover:bg-zinc-50 dark:hover:bg-zinc-800/50"
                    >
                      <FileText className="w-4 h-4 text-zinc-400" />
                      <span>Workspace Studio</span>
                    </Link>

                    <Link
                      href="/workspace?tab=bookmarks"
                      className="flex items-center gap-2.5 px-3.5 py-2 text-zinc-700 dark:text-zinc-300 hover:bg-zinc-50 dark:hover:bg-zinc-800/50"
                    >
                      <Bookmark className="w-4 h-4 text-zinc-400" />
                      <span>My Bookmarks</span>
                    </Link>

                    <Link
                      href="/workspace?tab=settings"
                      className="flex items-center gap-2.5 px-3.5 py-2 text-zinc-700 dark:text-zinc-300 hover:bg-zinc-50 dark:hover:bg-zinc-800/50"
                    >
                      <User className="w-4 h-4 text-zinc-400" />
                      <span>Profile & Settings</span>
                    </Link>

                    <div className="border-t border-zinc-100 dark:border-zinc-800 my-1" />

                    <button
                      onClick={logout}
                      className="w-full flex items-center gap-2.5 px-3.5 py-2 text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-950/20 text-left"
                    >
                      <LogOut className="w-4 h-4" />
                      <span>Sign Out</span>
                    </button>
                  </div>
                )}
              </div>
            ) : (
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setAuthModalOpen(true)}
                  className="text-xs font-semibold px-3 py-2 text-zinc-700 dark:text-zinc-300 hover:text-zinc-900 dark:hover:text-white transition"
                >
                  Sign In
                </button>
                <button
                  onClick={() => setAuthModalOpen(true)}
                  className="inline-flex items-center gap-1 text-xs font-semibold py-2 px-3.5 rounded-lg bg-zinc-900 hover:bg-zinc-800 dark:bg-white dark:hover:bg-zinc-100 text-white dark:text-zinc-900 shadow-sm transition"
                >
                  <Sparkles className="w-3.5 h-3.5" />
                  <span>Get Started</span>
                </button>
              </div>
            )}
          </div>
        </div>
      </header>

      <AuthModal
        isOpen={authModalOpen}
        onClose={() => setAuthModalOpen(false)}
      />
    </>
  );
}
