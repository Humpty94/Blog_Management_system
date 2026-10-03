import React from "react";
import Link from "next/link";
import { GitBranch, Layers, ShieldCheck, Terminal } from "lucide-react";

export function Footer() {
  return (
    <footer className="w-full border-t border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-950 py-12 transition-colors">
      <div className="max-w-6xl mx-auto px-4 sm:px-6">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8 pb-10 border-b border-zinc-100 dark:border-zinc-850">
          {/* Brand Info */}
          <div className="md:col-span-2 space-y-3">
            <div className="flex items-center gap-2">
              <span className="flex items-center justify-center w-7 h-7 rounded-lg bg-zinc-900 dark:bg-white text-white dark:text-zinc-900 font-extrabold text-sm">
                G
              </span>
              <span className="text-lg font-extrabold tracking-tight font-serif text-zinc-900 dark:text-white">
                Ghost<span className="text-zinc-400 font-sans font-medium text-xs ml-1">PRESS</span>
              </span>
            </div>
            <p className="text-sm text-zinc-500 dark:text-zinc-400 max-w-sm leading-relaxed">
              Independent publication platform powered by a verified Django 5.1 & PostgreSQL 16 modular monolith backend, crafted with Ghost-grade editorial precision.
            </p>
          </div>

          {/* Architecture Links */}
          <div className="space-y-3">
            <h4 className="text-xs font-semibold uppercase tracking-wider text-zinc-400">
              Architecture
            </h4>
            <ul className="space-y-2 text-sm text-zinc-600 dark:text-zinc-400">
              <li className="flex items-center gap-2">
                <Layers className="w-3.5 h-3.5 text-zinc-400" />
                <span>Modular Monolith</span>
              </li>
              <li className="flex items-center gap-2">
                <ShieldCheck className="w-3.5 h-3.5 text-zinc-400" />
                <span>PostgreSQL 16 Checks</span>
              </li>
              <li className="flex items-center gap-2">
                <Terminal className="w-3.5 h-3.5 text-zinc-400" />
                <span>Single-Reply Engine</span>
              </li>
            </ul>
          </div>

          {/* Quick Links */}
          <div className="space-y-3">
            <h4 className="text-xs font-semibold uppercase tracking-wider text-zinc-400">
              Platform
            </h4>
            <ul className="space-y-2 text-sm text-zinc-600 dark:text-zinc-400">
              <li>
                <Link href="/" className="hover:text-zinc-900 dark:hover:text-white transition">
                  Publication Feed
                </Link>
              </li>
              <li>
                <Link href="/workspace" className="hover:text-zinc-900 dark:hover:text-white transition">
                  Ghost Admin Studio
                </Link>
              </li>
              <li>
                <a
                  href="https://github.com/Humpty94/Blog_Management_system"
                  target="_blank"
                  rel="noreferrer"
                  className="flex items-center gap-1.5 hover:text-zinc-900 dark:hover:text-white transition"
                >
                  <GitBranch className="w-3.5 h-3.5" />
                  <span>GitHub Repository</span>
                </a>
              </li>
            </ul>
          </div>
        </div>

        {/* Bottom Bar */}
        <div className="pt-8 flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-zinc-400">
          <p>© {new Date().getFullYear()} GhostPRESS. Powered by Django REST Framework & Next.js.</p>
          <div className="flex items-center gap-4">
            <span className="flex items-center gap-1 text-emerald-600 dark:text-emerald-400">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
              API v1 Active
            </span>
          </div>
        </div>
      </div>
    </footer>
  );
}
