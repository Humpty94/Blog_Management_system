"use client";

import React, { useEffect, useState, useTransition } from "react";
import Link from "next/link";
import {
  ArrowRight,
  Bookmark,
  Calendar,
  Clock,
  Heart,
  Loader2,
  Search,
  Sparkles,
  TrendingUp,
} from "lucide-react";
import { Navbar } from "../components/Navbar";
import { Footer } from "../components/Footer";
import { useAuth } from "../context/AuthContext";
import { api } from "../lib/api";
import { Category, PaginatedResponse, PostSummary } from "../types";

export default function LandingPage() {
  const { user } = useAuth();
  const [categories, setCategories] = useState<Category[]>([]);
  const [postsData, setPostsData] = useState<PaginatedResponse<PostSummary> | null>(null);
  const [selectedCategory, setSelectedCategory] = useState<string>("");
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [loading, setLoading] = useState<boolean>(true);
  const [bookmarkedMap, setBookmarkedMap] = useState<Record<string, boolean>>({});
  const [, startTransition] = useTransition();

  // Fetch Categories
  useEffect(() => {
    api
      .getCategories()
      .then((cats) => setCategories(cats))
      .catch((err) => console.error("Error fetching categories:", err));
  }, []);

  // Fetch Published Posts
  useEffect(() => {
    setLoading(true);
    const debounceTimer = setTimeout(() => {
      api
        .getPublishedPosts({
          category: selectedCategory || undefined,
          search: searchQuery || undefined,
          page: currentPage,
        })
        .then((res) => {
          setPostsData(res);
        })
        .catch((err) => {
          console.error("Error fetching posts:", err);
          setPostsData(null);
        })
        .finally(() => {
          setLoading(false);
        });
    }, 250);

    return () => clearTimeout(debounceTimer);
  }, [selectedCategory, searchQuery, currentPage]);

  const handleCategorySelect = (slug: string) => {
    startTransition(() => {
      setSelectedCategory(slug === selectedCategory ? "" : slug);
      setCurrentPage(1);
    });
  };

  const handleToggleBookmark = async (e: React.MouseEvent, postSlug: string) => {
    e.preventDefault();
    e.stopPropagation();
    if (!user) {
      alert("Please sign in to save bookmarks to your private reading list.");
      return;
    }

    const isCurrentlyBookmarked = !!bookmarkedMap[postSlug];
    // Optimistic toggle
    setBookmarkedMap((prev) => ({ ...prev, [postSlug]: !isCurrentlyBookmarked }));

    try {
      if (isCurrentlyBookmarked) {
        await api.unbookmarkPost(postSlug);
      } else {
        await api.bookmarkPost(postSlug);
      }
    } catch (err) {
      console.error("Failed to toggle bookmark:", err);
      // Revert on error
      setBookmarkedMap((prev) => ({ ...prev, [postSlug]: isCurrentlyBookmarked }));
    }
  };

  const featuredPost = postsData?.results?.[0];
  const regularPosts = postsData?.results?.slice(1) || [];

  return (
    <div className="min-h-screen flex flex-col bg-zinc-50 dark:bg-zinc-950 text-zinc-900 dark:text-zinc-100 transition-colors">
      <Navbar />

      <main className="flex-1">
        {/* =================================================================== */}
        {/* GHOST EDITORIAL HERO */}
        {/* =================================================================== */}
        <section className="relative overflow-hidden border-b border-zinc-200 dark:border-zinc-850 bg-white dark:bg-zinc-900/50 py-16 sm:py-24">
          <div className="max-w-6xl mx-auto px-4 sm:px-6 relative z-10 text-center sm:text-left">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-zinc-200 dark:border-zinc-800 bg-zinc-50 dark:bg-zinc-850 text-xs font-semibold text-zinc-700 dark:text-zinc-300 mb-6">
              <Sparkles className="w-3.5 h-3.5 text-zinc-500" />
              <span>Independent Engineering Publication</span>
            </div>

            <h1 className="text-4xl sm:text-6xl font-extrabold tracking-tight font-serif text-zinc-950 dark:text-white max-w-3xl leading-[1.12]">
              Stories, ideas & modern software architecture.
            </h1>

            <p className="mt-5 text-base sm:text-lg text-zinc-600 dark:text-zinc-400 max-w-2xl leading-relaxed">
              Carefully crafted essays, deep-dives into modular monoliths, and technical insights from verified authors. Read freely or jump into your workspace to write.
            </p>

            <div className="mt-8 flex flex-wrap items-center justify-center sm:justify-start gap-3">
              <Link
                href="/workspace"
                className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg bg-zinc-900 hover:bg-zinc-800 dark:bg-white dark:hover:bg-zinc-100 text-white dark:text-zinc-900 text-sm font-semibold shadow-md transition"
              >
                <span>Enter Workspace</span>
                <ArrowRight className="w-4 h-4" />
              </Link>
              <a
                href="#feed"
                className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg border border-zinc-200 dark:border-zinc-800 hover:bg-zinc-100 dark:hover:bg-zinc-850 text-zinc-800 dark:text-zinc-200 text-sm font-semibold transition"
              >
                Browse Articles
              </a>
            </div>
          </div>
        </section>

        {/* =================================================================== */}
        {/* DISCOVERY BAR (CATEGORIES & LIVE SEARCH) */}
        {/* =================================================================== */}
        <section id="feed" className="sticky top-16 z-30 border-b border-zinc-200 dark:border-zinc-800 bg-white/95 dark:bg-zinc-950/95 backdrop-blur-md py-3.5">
          <div className="max-w-6xl mx-auto px-4 sm:px-6 flex flex-col md:flex-row items-center justify-between gap-4">
            {/* Category Pills */}
            <div className="flex items-center gap-2 overflow-x-auto w-full md:w-auto scrollbar-none pb-1 md:pb-0">
              <button
                onClick={() => handleCategorySelect("")}
                className={`px-3 py-1.5 rounded-full text-xs font-semibold whitespace-nowrap transition-all ${
                  selectedCategory === ""
                    ? "bg-zinc-900 text-white dark:bg-white dark:text-zinc-900 shadow-sm"
                    : "bg-zinc-100 dark:bg-zinc-850 text-zinc-600 dark:text-zinc-400 hover:bg-zinc-200 dark:hover:bg-zinc-800"
                }`}
              >
                All Topics
              </button>

              {categories.map((cat) => (
                <button
                  key={cat.id}
                  onClick={() => handleCategorySelect(cat.slug)}
                  className={`px-3 py-1.5 rounded-full text-xs font-semibold whitespace-nowrap transition-all ${
                    selectedCategory === cat.slug
                      ? "bg-zinc-900 text-white dark:bg-white dark:text-zinc-900 shadow-sm"
                      : "bg-zinc-100 dark:bg-zinc-850 text-zinc-600 dark:text-zinc-400 hover:bg-zinc-200 dark:hover:bg-zinc-800"
                  }`}
                >
                  {cat.name}
                </button>
              ))}
            </div>

            {/* Debounced Search Input */}
            <div className="relative w-full md:w-72 shrink-0">
              <Search className="absolute left-3 top-2.5 w-4 h-4 text-zinc-400" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => {
                  setSearchQuery(e.target.value);
                  setCurrentPage(1);
                }}
                placeholder="Search articles & essays..."
                className="w-full pl-9 pr-3 py-1.5 text-xs rounded-full border border-zinc-200 dark:border-zinc-800 bg-zinc-50 dark:bg-zinc-900 text-zinc-900 dark:text-white placeholder-zinc-400 focus:outline-none focus:ring-2 focus:ring-zinc-900 dark:focus:ring-white transition"
              />
            </div>
          </div>
        </section>

        {/* =================================================================== */}
        {/* PUBLICATION FEED */}
        {/* =================================================================== */}
        <section className="max-w-6xl mx-auto px-4 sm:px-6 py-12">
          {loading && !postsData ? (
            <div className="py-24 flex flex-col items-center justify-center text-zinc-400 space-y-3">
              <Loader2 className="w-8 h-8 animate-spin text-zinc-900 dark:text-white" />
              <p className="text-sm">Fetching publication stories...</p>
            </div>
          ) : !postsData || postsData.results.length === 0 ? (
            <div className="py-24 text-center border border-dashed border-zinc-200 dark:border-zinc-800 rounded-2xl p-8">
              <TrendingUp className="w-10 h-10 mx-auto text-zinc-400 mb-3" />
              <h3 className="text-lg font-bold text-zinc-900 dark:text-white">
                No articles found
              </h3>
              <p className="text-sm text-zinc-500 mt-1 max-w-sm mx-auto">
                No stories match your current filters. Try searching for a different keyword or category.
              </p>
              <button
                onClick={() => {
                  setSelectedCategory("");
                  setSearchQuery("");
                }}
                className="mt-4 text-xs font-semibold text-zinc-900 dark:text-white underline"
              >
                Clear all filters
              </button>
            </div>
          ) : (
            <div className="space-y-12">
              {/* FEATURED STORY CARD */}
              {featuredPost && currentPage === 1 && !searchQuery && !selectedCategory && (
                <article className="group relative rounded-2xl border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900/60 p-6 sm:p-10 shadow-sm hover:shadow-md transition-all">
                  <div className="flex flex-col md:flex-row gap-6 md:gap-10 justify-between items-start">
                    <div className="space-y-4 max-w-2xl">
                      <div className="flex items-center gap-3 text-xs text-zinc-500">
                        <span className="font-semibold uppercase tracking-wider px-2.5 py-0.5 rounded bg-zinc-100 dark:bg-zinc-800 text-zinc-700 dark:text-zinc-300">
                          {featuredPost.category.name}
                        </span>
                        <span>•</span>
                        <span className="flex items-center gap-1">
                          <Calendar className="w-3.5 h-3.5" />
                          {new Date(featuredPost.published_at || featuredPost.created_at).toLocaleDateString("en-US", {
                            month: "short",
                            day: "numeric",
                            year: "numeric",
                          })}
                        </span>
                        <span>•</span>
                        <span className="flex items-center gap-1">
                          <Clock className="w-3.5 h-3.5" />
                          4 min read
                        </span>
                      </div>

                      <h2 className="text-2xl sm:text-4xl font-extrabold tracking-tight font-serif text-zinc-900 dark:text-white group-hover:text-zinc-600 dark:group-hover:text-zinc-300 transition-colors">
                        <Link href={`/posts/${featuredPost.slug}`}>
                          {featuredPost.title}
                        </Link>
                      </h2>

                      <p className="text-zinc-600 dark:text-zinc-400 text-sm sm:text-base leading-relaxed line-clamp-3">
                        {featuredPost.excerpt}
                      </p>

                      <div className="pt-2 flex items-center justify-between">
                        <div className="flex items-center gap-2.5">
                          <div className="w-8 h-8 rounded-full bg-zinc-900 dark:bg-white text-white dark:text-zinc-900 flex items-center justify-center font-bold text-xs uppercase shadow-sm">
                            {featuredPost.author.username.slice(0, 2)}
                          </div>
                          <div>
                            <p className="text-xs font-bold text-zinc-900 dark:text-white">
                              {featuredPost.author.display_name || featuredPost.author.username}
                            </p>
                            <p className="text-[11px] text-zinc-400">Author</p>
                          </div>
                        </div>

                        <div className="flex items-center gap-4 text-xs text-zinc-500">
                          <span className="flex items-center gap-1.5">
                            <Heart className="w-4 h-4 text-red-500 fill-red-500" />
                            <span>{featuredPost.like_count}</span>
                          </span>

                          <button
                            onClick={(e) => handleToggleBookmark(e, featuredPost.slug)}
                            className="p-1.5 hover:text-zinc-900 dark:hover:text-white rounded transition"
                            title="Save to bookmarks"
                          >
                            <Bookmark
                              className={`w-4 h-4 ${
                                bookmarkedMap[featuredPost.slug]
                                  ? "text-zinc-900 dark:text-white fill-current"
                                  : ""
                              }`}
                            />
                          </button>
                        </div>
                      </div>
                    </div>

                    <div className="hidden lg:flex w-64 h-48 rounded-xl bg-zinc-100 dark:bg-zinc-800 items-center justify-center text-zinc-400 font-serif italic text-sm border border-zinc-200/50 dark:border-zinc-700/50">
                      Ghost Editorial
                    </div>
                  </div>
                </article>
              )}

              {/* POSTS GRID */}
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {(currentPage === 1 && !searchQuery && !selectedCategory
                  ? regularPosts
                  : postsData.results
                ).map((post) => (
                  <article
                    key={post.id}
                    className="group flex flex-col justify-between rounded-xl border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900/60 p-6 hover:shadow-md hover:border-zinc-300 dark:hover:border-zinc-700 transition-all"
                  >
                    <div className="space-y-3">
                      <div className="flex items-center justify-between text-xs text-zinc-500">
                        <span className="font-semibold uppercase tracking-wider text-[11px] px-2 py-0.5 rounded bg-zinc-100 dark:bg-zinc-800 text-zinc-700 dark:text-zinc-300">
                          {post.category.name}
                        </span>
                        <span>
                          {new Date(post.published_at || post.created_at).toLocaleDateString("en-US", {
                            month: "short",
                            day: "numeric",
                          })}
                        </span>
                      </div>

                      <h3 className="text-xl font-bold font-serif text-zinc-900 dark:text-white group-hover:text-zinc-600 dark:group-hover:text-zinc-300 transition-colors line-clamp-2">
                        <Link href={`/posts/${post.slug}`}>{post.title}</Link>
                      </h3>

                      <p className="text-sm text-zinc-600 dark:text-zinc-400 line-clamp-3 leading-relaxed">
                        {post.excerpt}
                      </p>
                    </div>

                    <div className="mt-6 pt-4 border-t border-zinc-100 dark:border-zinc-800/80 flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <div className="w-6 h-6 rounded-full bg-zinc-800 dark:bg-zinc-200 text-white dark:text-zinc-900 flex items-center justify-center font-bold text-[10px] uppercase">
                          {post.author.username.slice(0, 2)}
                        </div>
                        <span className="text-xs font-medium text-zinc-700 dark:text-zinc-300 truncate max-w-[110px]">
                          {post.author.display_name || post.author.username}
                        </span>
                      </div>

                      <div className="flex items-center gap-3 text-xs text-zinc-500">
                        <span className="flex items-center gap-1">
                          <Heart className="w-3.5 h-3.5 text-zinc-400 group-hover:text-red-500 transition-colors" />
                          <span>{post.like_count}</span>
                        </span>

                        <button
                          onClick={(e) => handleToggleBookmark(e, post.slug)}
                          className="hover:text-zinc-900 dark:hover:text-white transition"
                          title="Bookmark post"
                        >
                          <Bookmark
                            className={`w-3.5 h-3.5 ${
                              bookmarkedMap[post.slug]
                                ? "text-zinc-900 dark:text-white fill-current"
                                : ""
                            }`}
                          />
                        </button>
                      </div>
                    </div>
                  </article>
                ))}
              </div>

              {/* PAGINATION CONTROLS */}
              {postsData.pagination.total_pages > 1 && (
                <div className="pt-8 flex items-center justify-between border-t border-zinc-200 dark:border-zinc-800">
                  <button
                    disabled={!postsData.pagination.previous}
                    onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                    className="px-4 py-2 text-xs font-semibold rounded-lg border border-zinc-200 dark:border-zinc-800 hover:bg-zinc-100 dark:hover:bg-zinc-800 disabled:opacity-40 disabled:cursor-not-allowed transition"
                  >
                    Previous
                  </button>

                  <span className="text-xs text-zinc-500">
                    Page {postsData.pagination.page} of {postsData.pagination.total_pages}
                  </span>

                  <button
                    disabled={!postsData.pagination.next}
                    onClick={() => setCurrentPage((p) => p + 1)}
                    className="px-4 py-2 text-xs font-semibold rounded-lg border border-zinc-200 dark:border-zinc-800 hover:bg-zinc-100 dark:hover:bg-zinc-800 disabled:opacity-40 disabled:cursor-not-allowed transition"
                  >
                    Next
                  </button>
                </div>
              )}
            </div>
          )}
        </section>
      </main>

      <Footer />
    </div>
  );
}
