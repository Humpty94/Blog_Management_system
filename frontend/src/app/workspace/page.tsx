"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import {
  AlertCircle,
  ArrowLeft,
  Bookmark,
  CheckCircle2,
  Eye,
  FileEdit,
  FileText,
  LayoutDashboard,
  Loader2,
  Lock,
  Plus,
  Send,
  Settings,
} from "lucide-react";
import { Navbar } from "../../components/Navbar";
import { useAuth } from "../../context/AuthContext";
import { api } from "../../lib/api";
import { BookmarkItem, Category, PostSummary } from "../../types";

function WorkspaceContent() {
  const { user, refreshUser } = useAuth();
  const searchParams = useSearchParams();
  const initialTab = searchParams.get("tab") || "dashboard";
  const editSlugParam = searchParams.get("edit");

  const [activeTab, setActiveTab] = useState<string>(
    editSlugParam ? "editor" : initialTab
  );

  // Data states
  const [categories, setCategories] = useState<Category[]>([]);
  const [myPosts, setMyPosts] = useState<PostSummary[]>([]);
  const [bookmarks, setBookmarks] = useState<BookmarkItem[]>([]);
  const [loadingPosts, setLoadingPosts] = useState<boolean>(true);

  // Editor states
  const [editingPostSlug, setEditingPostSlug] = useState<string | null>(
    editSlugParam || null
  );
  const [editorTitle, setEditorTitle] = useState("");
  const [editorCategory, setEditorCategory] = useState("");
  const [editorMarkdown, setEditorMarkdown] = useState("");
  const [editorStatus, setEditorStatus] = useState<"draft" | "published">("draft");
  const [savingPost, setSavingPost] = useState(false);
  const [editorMessage, setEditorMessage] = useState<string | null>(null);

  // Settings states
  const [settingsDisplayName, setSettingsDisplayName] = useState(
    user?.display_name || ""
  );
  const [settingsBio, setSettingsBio] = useState(user?.bio || "");
  const [deactivatePassword, setDeactivatePassword] = useState("");
  const [showDeactivateModal, setShowDeactivateModal] = useState(false);

  // Fetch initial workspace data
  useEffect(() => {
    if (!user) return;

    api.getCategories().then((cats) => {
      setCategories(cats);
      setEditorCategory((prev) => prev || (cats.length > 0 ? cats[0].slug : ""));
    });

    loadWorkspacePosts();
    loadBookmarks();
  }, [user]);

  // Load existing post if editing
  useEffect(() => {
    if (editingPostSlug) {
      api.getPostBySlug(editingPostSlug).then((p) => {
        setEditorTitle(p.title);
        setEditorCategory(p.category.slug);
        setEditorMarkdown(p.content_markdown || "");
        setEditorStatus(p.status);
        setActiveTab("editor");
      });
    }
  }, [editingPostSlug]);

  const loadWorkspacePosts = async () => {
    setLoadingPosts(true);
    try {
      const res = await api.getMyPosts({ page: 1 });
      setMyPosts(res.results);
    } catch (err) {
      console.error("Error loading user posts:", err);
    } finally {
      setLoadingPosts(false);
    }
  };

  const loadBookmarks = async () => {
    try {
      const res = await api.getMyBookmarks(1);
      setBookmarks(res.results);
    } catch (err) {
      console.error("Error loading bookmarks:", err);
    }
  };

  const handleSaveDraft = async () => {
    if (!editorTitle.trim()) {
      alert("Please provide an article title.");
      return;
    }
    setSavingPost(true);
    setEditorMessage(null);

    try {
      if (editingPostSlug) {
        await api.updatePost(editingPostSlug, {
          title: editorTitle,
          category_slug: editorCategory,
          content_markdown: editorMarkdown,
        });
        setEditorMessage("Draft updated successfully.");
      } else {
        const created = await api.createPost({
          title: editorTitle,
          category_slug: editorCategory,
          content_markdown: editorMarkdown,
        });
        setEditingPostSlug(created.slug);
        setEditorMessage("Draft created successfully.");
      }
      await loadWorkspacePosts();
    } catch (err: unknown) {
      const e = err as { message?: string };
      alert(e.message || "Failed to save draft.");
    } finally {
      setSavingPost(false);
    }
  };

  const handlePublishToggle = async () => {
    if (!user) return;

    if (!user.is_email_verified && editorStatus === "draft") {
      alert(
        "Email verification required: According to publication security rules, you must verify your email before publishing."
      );
      return;
    }

    setSavingPost(true);
    setEditorMessage(null);

    try {
      // If new, save first
      let currentSlug = editingPostSlug;
      if (!currentSlug) {
        const created = await api.createPost({
          title: editorTitle,
          category_slug: editorCategory,
          content_markdown: editorMarkdown,
        });
        currentSlug = created.slug;
        setEditingPostSlug(created.slug);
      } else {
        await api.updatePost(currentSlug, {
          title: editorTitle,
          category_slug: editorCategory,
          content_markdown: editorMarkdown,
        });
      }

      if (editorStatus === "draft") {
        await api.publishPost(currentSlug);
        setEditorStatus("published");
        setEditorMessage("Article published live to the publication feed!");
      } else {
        await api.unpublishPost(currentSlug);
        setEditorStatus("draft");
        setEditorMessage("Article reverted back to private draft.");
      }
      await loadWorkspacePosts();
    } catch (err: unknown) {
      const e = err as { message?: string };
      alert(e.message || "Failed to transition post state.");
    } finally {
      setSavingPost(false);
    }
  };

  const handleDeletePost = async (slug: string) => {
    if (!confirm("Are you sure you want to permanently delete this post?")) return;
    try {
      await api.deletePost(slug);
      if (editingPostSlug === slug) {
        resetEditor();
      }
      await loadWorkspacePosts();
    } catch (err) {
      console.error("Failed to delete post:", err);
    }
  };

  const resetEditor = () => {
    setEditingPostSlug(null);
    setEditorTitle("");
    setEditorMarkdown("");
    setEditorStatus("draft");
    setEditorMessage(null);
    if (categories.length > 0) {
      setEditorCategory(categories[0].slug);
    }
  };

  const handleUpdateProfile = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await api.updateProfile({
        display_name: settingsDisplayName,
        bio: settingsBio,
      });
      await refreshUser();
      alert("Profile updated successfully!");
    } catch (err) {
      console.error("Profile update error:", err);
      alert("Failed to update profile.");
    }
  };

  const handleDeactivateAccount = async () => {
    if (!deactivatePassword) {
      alert("Please enter your password to confirm deactivation.");
      return;
    }

    try {
      await api.deactivateAccount(deactivatePassword);
      alert("Account successfully deactivated and anonymized.");
      window.location.href = "/";
    } catch (err: unknown) {
      const e = err as { message?: string };
      alert(e.message || "Failed to deactivate account.");
    }
  };

  if (!user) {
    return (
      <div className="min-h-screen flex flex-col bg-zinc-50 dark:bg-zinc-950">
        <Navbar />
        <div className="flex-1 flex flex-col items-center justify-center p-6 text-center">
          <Lock className="w-10 h-10 text-zinc-400 mb-3" />
          <h2 className="text-xl font-bold font-serif text-zinc-900 dark:text-white">
            Authentication Required
          </h2>
          <p className="text-sm text-zinc-500 mt-1 max-w-sm">
            Sign in to access the Ghost Admin workspace, manage your publications, and draft articles.
          </p>
        </div>
      </div>
    );
  }

  // Dashboard calculations
  const totalPosts = myPosts.length;
  const publishedCount = myPosts.filter((p) => p.status === "published").length;
  const draftCount = myPosts.filter((p) => p.status === "draft").length;
  const totalLikes = myPosts.reduce((acc, p) => acc + (p.like_count || 0), 0);
  const wordCount = editorMarkdown.trim().split(/\s+/).filter(Boolean).length;

  return (
    <div className="min-h-screen flex flex-col bg-zinc-100 dark:bg-zinc-950 text-zinc-900 dark:text-zinc-100 transition-colors">
      <Navbar />

      <div className="flex-1 max-w-7xl mx-auto w-full px-4 sm:px-6 py-8 flex flex-col md:flex-row gap-8">
        {/* =================================================================== */}
        {/* GHOST ADMIN SIDEBAR */}
        {/* =================================================================== */}
        <aside className="w-full md:w-60 shrink-0 space-y-6">
          <div className="rounded-xl border border-zinc-200 dark:border-zinc-850 bg-white dark:bg-zinc-900 p-4 shadow-sm">
            <div className="flex items-center gap-3 pb-4 border-b border-zinc-100 dark:border-zinc-800">
              <div className="w-9 h-9 rounded-lg bg-zinc-900 dark:bg-white text-white dark:text-zinc-900 flex items-center justify-center font-bold text-sm">
                G
              </div>
              <div className="truncate">
                <p className="text-sm font-bold text-zinc-900 dark:text-white truncate font-serif">
                  Ghost Studio
                </p>
                <p className="text-xs text-zinc-400">Creator Workspace</p>
              </div>
            </div>

            <nav className="mt-4 space-y-1">
              <button
                onClick={() => setActiveTab("dashboard")}
                className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-xs font-semibold text-left transition ${
                  activeTab === "dashboard"
                    ? "bg-zinc-900 text-white dark:bg-white dark:text-zinc-900"
                    : "text-zinc-600 dark:text-zinc-400 hover:bg-zinc-100 dark:hover:bg-zinc-800"
                }`}
              >
                <LayoutDashboard className="w-4 h-4" />
                <span>Dashboard</span>
              </button>

              <button
                onClick={() => setActiveTab("posts")}
                className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-xs font-semibold text-left transition ${
                  activeTab === "posts"
                    ? "bg-zinc-900 text-white dark:bg-white dark:text-zinc-900"
                    : "text-zinc-600 dark:text-zinc-400 hover:bg-zinc-100 dark:hover:bg-zinc-800"
                }`}
              >
                <FileText className="w-4 h-4" />
                <span>Posts</span>
                <span className="ml-auto text-[10px] font-bold px-1.5 py-0.5 rounded bg-zinc-200 dark:bg-zinc-700 text-zinc-700 dark:text-zinc-200">
                  {totalPosts}
                </span>
              </button>

              <button
                onClick={() => {
                  resetEditor();
                  setActiveTab("editor");
                }}
                className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-xs font-semibold text-left transition ${
                  activeTab === "editor"
                    ? "bg-zinc-900 text-white dark:bg-white dark:text-zinc-900"
                    : "text-zinc-600 dark:text-zinc-400 hover:bg-zinc-100 dark:hover:bg-zinc-800"
                }`}
              >
                <FileEdit className="w-4 h-4" />
                <span>Studio Editor</span>
              </button>

              <button
                onClick={() => setActiveTab("bookmarks")}
                className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-xs font-semibold text-left transition ${
                  activeTab === "bookmarks"
                    ? "bg-zinc-900 text-white dark:bg-white dark:text-zinc-900"
                    : "text-zinc-600 dark:text-zinc-400 hover:bg-zinc-100 dark:hover:bg-zinc-800"
                }`}
              >
                <Bookmark className="w-4 h-4" />
                <span>My Bookmarks</span>
                <span className="ml-auto text-[10px] font-bold px-1.5 py-0.5 rounded bg-zinc-200 dark:bg-zinc-700 text-zinc-700 dark:text-zinc-200">
                  {bookmarks.length}
                </span>
              </button>

              <button
                onClick={() => setActiveTab("settings")}
                className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-xs font-semibold text-left transition ${
                  activeTab === "settings"
                    ? "bg-zinc-900 text-white dark:bg-white dark:text-zinc-900"
                    : "text-zinc-600 dark:text-zinc-400 hover:bg-zinc-100 dark:hover:bg-zinc-800"
                }`}
              >
                <Settings className="w-4 h-4" />
                <span>Settings</span>
              </button>
            </nav>

            {/* Email verification status box */}
            <div className="mt-6 pt-4 border-t border-zinc-100 dark:border-zinc-800 text-xs">
              <div className="flex items-center gap-2 text-zinc-500">
                {user.is_email_verified ? (
                  <span className="flex items-center gap-1.5 text-emerald-600 dark:text-emerald-400 font-semibold">
                    <CheckCircle2 className="w-3.5 h-3.5" />
                    <span>Verified Author</span>
                  </span>
                ) : (
                  <span className="flex items-center gap-1.5 text-amber-600 dark:text-amber-400 font-semibold">
                    <AlertCircle className="w-3.5 h-3.5" />
                    <span>Email Unverified</span>
                  </span>
                )}
              </div>
            </div>
          </div>
        </aside>

        {/* =================================================================== */}
        {/* MAIN WORKSPACE CONTENT */}
        {/* =================================================================== */}
        <main className="flex-1 min-w-0">
          {/* TAB 1: DASHBOARD */}
          {activeTab === "dashboard" && (
            <div className="space-y-8 animate-in fade-in">
              <div>
                <h2 className="text-2xl font-bold font-serif text-zinc-950 dark:text-white">
                  Dashboard
                </h2>
                <p className="text-xs text-zinc-500 mt-1">
                  Publication analytics, status of private drafts and published articles.
                </p>
              </div>

              {/* Metric Cards */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                <div className="rounded-xl border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 p-5 shadow-sm">
                  <p className="text-xs text-zinc-500 uppercase tracking-wider font-semibold">
                    Total Posts
                  </p>
                  <p className="text-3xl font-extrabold text-zinc-900 dark:text-white mt-2">
                    {totalPosts}
                  </p>
                </div>

                <div className="rounded-xl border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 p-5 shadow-sm">
                  <p className="text-xs text-emerald-600 dark:text-emerald-400 uppercase tracking-wider font-semibold">
                    Published
                  </p>
                  <p className="text-3xl font-extrabold text-zinc-900 dark:text-white mt-2">
                    {publishedCount}
                  </p>
                </div>

                <div className="rounded-xl border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 p-5 shadow-sm">
                  <p className="text-xs text-amber-600 dark:text-amber-400 uppercase tracking-wider font-semibold">
                    Drafts
                  </p>
                  <p className="text-3xl font-extrabold text-zinc-900 dark:text-white mt-2">
                    {draftCount}
                  </p>
                </div>

                <div className="rounded-xl border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 p-5 shadow-sm">
                  <p className="text-xs text-red-500 uppercase tracking-wider font-semibold">
                    Total Likes
                  </p>
                  <p className="text-3xl font-extrabold text-zinc-900 dark:text-white mt-2">
                    {totalLikes}
                  </p>
                </div>
              </div>

              {/* Quick Actions & Recent Drafts */}
              <div className="rounded-xl border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 p-6 shadow-sm space-y-4">
                <div className="flex items-center justify-between">
                  <h3 className="text-base font-bold font-serif text-zinc-900 dark:text-white">
                    Recent Drafts
                  </h3>
                  <button
                    onClick={() => {
                      resetEditor();
                      setActiveTab("editor");
                    }}
                    className="inline-flex items-center gap-1.5 text-xs font-semibold px-3 py-1.5 rounded-lg bg-zinc-900 dark:bg-white text-white dark:text-zinc-900"
                  >
                    <Plus className="w-3.5 h-3.5" />
                    <span>New Article</span>
                  </button>
                </div>

                {myPosts.filter((p) => p.status === "draft").length === 0 ? (
                  <p className="text-xs text-zinc-400 py-4 text-center">
                    No active drafts. Click &quot;New Article&quot; to start writing.
                  </p>
                ) : (
                  <div className="divide-y divide-zinc-100 dark:divide-zinc-800">
                    {myPosts
                      .filter((p) => p.status === "draft")
                      .slice(0, 5)
                      .map((draft) => (
                        <div
                          key={draft.id}
                          className="py-3 flex items-center justify-between gap-4"
                        >
                          <div>
                            <p className="text-sm font-semibold text-zinc-900 dark:text-white">
                              {draft.title}
                            </p>
                            <p className="text-xs text-zinc-400 mt-0.5">
                              {draft.category.name} • Created{" "}
                              {new Date(draft.created_at).toLocaleDateString()}
                            </p>
                          </div>
                          <button
                            onClick={() => {
                              setEditingPostSlug(draft.slug);
                            }}
                            className="text-xs font-semibold text-zinc-700 dark:text-zinc-300 hover:underline"
                          >
                            Continue editing
                          </button>
                        </div>
                      ))}
                  </div>
                )}
              </div>
            </div>
          )}

          {/* TAB 2: POSTS MANAGER */}
          {activeTab === "posts" && (
            <div className="space-y-6 animate-in fade-in">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-2xl font-bold font-serif text-zinc-950 dark:text-white">
                    Posts Manager
                  </h2>
                  <p className="text-xs text-zinc-500 mt-1">
                    Manage all your drafted and published publication stories.
                  </p>
                </div>

                <button
                  onClick={() => {
                    resetEditor();
                    setActiveTab("editor");
                  }}
                  className="inline-flex items-center gap-1.5 text-xs font-semibold px-3.5 py-2 rounded-lg bg-zinc-900 dark:bg-white text-white dark:text-zinc-900 shadow-sm"
                >
                  <Plus className="w-3.5 h-3.5" />
                  <span>New Post</span>
                </button>
              </div>

              {loadingPosts ? (
                <div className="py-20 flex justify-center text-zinc-400">
                  <Loader2 className="w-6 h-6 animate-spin" />
                </div>
              ) : myPosts.length === 0 ? (
                <div className="py-16 text-center border border-dashed border-zinc-200 dark:border-zinc-800 rounded-xl">
                  <FileText className="w-8 h-8 text-zinc-400 mx-auto mb-2" />
                  <p className="text-sm font-semibold">No posts created yet.</p>
                </div>
              ) : (
                <div className="rounded-xl border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 overflow-hidden shadow-sm">
                  <table className="w-full text-left text-xs">
                    <thead className="bg-zinc-50 dark:bg-zinc-800/60 border-b border-zinc-200 dark:border-zinc-800 text-zinc-500 font-semibold uppercase tracking-wider">
                      <tr>
                        <th className="p-4">Title</th>
                        <th className="p-4">Category</th>
                        <th className="p-4">Status</th>
                        <th className="p-4">Likes</th>
                        <th className="p-4 text-right">Actions</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-zinc-100 dark:divide-zinc-800">
                      {myPosts.map((post) => (
                        <tr
                          key={post.id}
                          className="hover:bg-zinc-50 dark:hover:bg-zinc-850/50 transition"
                        >
                          <td className="p-4 font-semibold text-zinc-900 dark:text-white max-w-xs truncate">
                            {post.title}
                          </td>
                          <td className="p-4 text-zinc-500">{post.category.name}</td>
                          <td className="p-4">
                            {post.status === "published" ? (
                              <span className="px-2 py-0.5 rounded text-[11px] font-semibold bg-emerald-50 dark:bg-emerald-950/40 text-emerald-600 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-800">
                                Published
                              </span>
                            ) : (
                              <span className="px-2 py-0.5 rounded text-[11px] font-semibold bg-amber-50 dark:bg-amber-950/40 text-amber-600 dark:text-amber-400 border border-amber-200 dark:border-amber-800">
                                Draft
                              </span>
                            )}
                          </td>
                          <td className="p-4 text-zinc-500">{post.like_count}</td>
                          <td className="p-4 text-right space-x-2">
                            <button
                              onClick={() => setEditingPostSlug(post.slug)}
                              className="text-xs font-semibold text-zinc-700 dark:text-zinc-300 hover:underline"
                            >
                              Edit
                            </button>
                            <button
                              onClick={() => handleDeletePost(post.slug)}
                              className="text-xs font-semibold text-red-600 dark:text-red-400 hover:underline"
                            >
                              Delete
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}

          {/* TAB 3: GHOST DISTRACTION-FREE SPLIT-PANE EDITOR */}
          {activeTab === "editor" && (
            <div className="space-y-6 animate-in fade-in">
              {/* Top Editor Bar */}
              <div className="flex flex-wrap items-center justify-between gap-4 p-4 rounded-xl border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 shadow-sm">
                <div className="flex items-center gap-3">
                  <button
                    onClick={() => setActiveTab("posts")}
                    className="p-1.5 rounded-lg border border-zinc-200 dark:border-zinc-800 text-zinc-500 hover:text-zinc-900 dark:hover:text-white"
                  >
                    <ArrowLeft className="w-4 h-4" />
                  </button>
                  <span className="text-xs font-bold uppercase tracking-wider text-zinc-400">
                    {editorStatus === "published" ? "Published Post" : "Draft Editor"}
                  </span>
                </div>

                <div className="flex items-center gap-3">
                  {/* Category Picker */}
                  <select
                    value={editorCategory}
                    onChange={(e) => setEditorCategory(e.target.value)}
                    className="text-xs py-1.5 px-3 rounded-lg border border-zinc-200 dark:border-zinc-800 bg-zinc-50 dark:bg-zinc-850 text-zinc-900 dark:text-white focus:outline-none"
                  >
                    {categories.map((c) => (
                      <option key={c.id} value={c.slug}>
                        {c.name}
                      </option>
                    ))}
                  </select>

                  <button
                    onClick={handleSaveDraft}
                    disabled={savingPost}
                    className="text-xs font-semibold py-1.5 px-3.5 rounded-lg border border-zinc-200 dark:border-zinc-800 hover:bg-zinc-100 dark:hover:bg-zinc-800 transition"
                  >
                    Save Draft
                  </button>

                  <button
                    onClick={handlePublishToggle}
                    disabled={savingPost}
                    className={`inline-flex items-center gap-1.5 text-xs font-semibold py-1.5 px-3.5 rounded-lg transition shadow-sm ${
                      editorStatus === "published"
                        ? "bg-amber-600 hover:bg-amber-700 text-white"
                        : "bg-emerald-600 hover:bg-emerald-700 text-white"
                    }`}
                  >
                    {savingPost ? (
                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    ) : (
                      <Send className="w-3.5 h-3.5" />
                    )}
                    <span>{editorStatus === "published" ? "Unpublish" : "Publish"}</span>
                  </button>
                </div>
              </div>

              {editorMessage && (
                <div className="p-3 rounded-lg bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-200 dark:border-emerald-800 text-xs text-emerald-700 dark:text-emerald-400 flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4" />
                  <span>{editorMessage}</span>
                </div>
              )}

              {/* Title Input */}
              <input
                type="text"
                value={editorTitle}
                onChange={(e) => setEditorTitle(e.target.value)}
                placeholder="Post title..."
                className="w-full p-4 text-2xl sm:text-4xl font-extrabold font-serif tracking-tight rounded-xl border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 text-zinc-950 dark:text-white focus:outline-none shadow-sm"
              />

              {/* Split-Pane: Markdown Editor & Live Preview */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                {/* Left: Monospace Raw Markdown */}
                <div className="rounded-xl border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 p-4 shadow-sm flex flex-col">
                  <div className="flex items-center justify-between pb-2 mb-2 border-b border-zinc-100 dark:border-zinc-800 text-xs text-zinc-400 font-semibold uppercase">
                    <span>Markdown Source</span>
                    <span>{wordCount} words</span>
                  </div>
                  <textarea
                    rows={20}
                    value={editorMarkdown}
                    onChange={(e) => setEditorMarkdown(e.target.value)}
                    placeholder="Write your story in Markdown (e.g. # Heading, **bold**, `code`)..."
                    className="w-full flex-1 p-2 text-sm font-mono leading-relaxed bg-transparent text-zinc-800 dark:text-zinc-200 focus:outline-none resize-none"
                  />
                </div>

                {/* Right: Live Preview */}
                <div className="rounded-xl border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 p-6 shadow-sm flex flex-col overflow-y-auto max-h-[550px]">
                  <div className="flex items-center justify-between pb-2 mb-4 border-b border-zinc-100 dark:border-zinc-800 text-xs text-zinc-400 font-semibold uppercase">
                    <span>Live Preview</span>
                    <span className="flex items-center gap-1">
                      <Eye className="w-3.5 h-3.5" />
                      <span>Reading Mode</span>
                    </span>
                  </div>

                  <div className="prose prose-zinc dark:prose-invert max-w-none text-sm leading-relaxed">
                    {editorTitle && (
                      <h1 className="font-serif font-extrabold">{editorTitle}</h1>
                    )}
                    {editorMarkdown ? (
                      <div className="whitespace-pre-wrap font-sans">
                        {editorMarkdown}
                      </div>
                    ) : (
                      <p className="italic text-zinc-400">
                        Live formatted preview will appear here as you write...
                      </p>
                    )}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* TAB 4: BOOKMARKS */}
          {activeTab === "bookmarks" && (
            <div className="space-y-6 animate-in fade-in">
              <div>
                <h2 className="text-2xl font-bold font-serif text-zinc-950 dark:text-white">
                  My Bookmarks
                </h2>
                <p className="text-xs text-zinc-500 mt-1">
                  Your private reading list. Strictly isolated and confidential to your account.
                </p>
              </div>

              {bookmarks.length === 0 ? (
                <div className="py-16 text-center border border-dashed border-zinc-200 dark:border-zinc-800 rounded-xl">
                  <Bookmark className="w-8 h-8 text-zinc-400 mx-auto mb-2" />
                  <p className="text-sm font-semibold">No saved bookmarks yet.</p>
                </div>
              ) : (
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  {bookmarks.map((b) => (
                    <article
                      key={b.id}
                      className="p-5 rounded-xl border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 shadow-sm space-y-2"
                    >
                      <span className="text-[11px] font-semibold uppercase px-2 py-0.5 rounded bg-zinc-100 dark:bg-zinc-800 text-zinc-600 dark:text-zinc-400">
                        {b.post.category.name}
                      </span>
                      <h4 className="text-base font-bold font-serif hover:underline">
                        <Link href={`/posts/${b.post.slug}`}>{b.post.title}</Link>
                      </h4>
                      <p className="text-xs text-zinc-500 line-clamp-2">
                        {b.post.excerpt}
                      </p>
                    </article>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* TAB 5: SETTINGS & ACCOUNT DEACTIVATION */}
          {activeTab === "settings" && (
            <div className="space-y-8 animate-in fade-in max-w-xl">
              <div>
                <h2 className="text-2xl font-bold font-serif text-zinc-950 dark:text-white">
                  Profile & Settings
                </h2>
                <p className="text-xs text-zinc-500 mt-1">
                  Manage your author profile, display name, and account security.
                </p>
              </div>

              <form onSubmit={handleUpdateProfile} className="space-y-4">
                <div>
                  <label className="block text-xs font-semibold uppercase text-zinc-500 mb-1">
                    Display Name
                  </label>
                  <input
                    type="text"
                    value={settingsDisplayName}
                    onChange={(e) => setSettingsDisplayName(e.target.value)}
                    className="w-full px-3 py-2 text-sm rounded-lg border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold uppercase text-zinc-500 mb-1">
                    Author Bio
                  </label>
                  <textarea
                    rows={3}
                    value={settingsBio}
                    onChange={(e) => setSettingsBio(e.target.value)}
                    className="w-full px-3 py-2 text-sm rounded-lg border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900"
                  />
                </div>

                <button
                  type="submit"
                  className="px-4 py-2 rounded-lg bg-zinc-900 dark:bg-white text-white dark:text-zinc-900 text-xs font-semibold shadow-sm"
                >
                  Save Profile
                </button>
              </form>

              {/* Danger Zone: Account Deactivation */}
              <div className="pt-8 border-t border-red-200 dark:border-red-900/50 space-y-3">
                <h3 className="text-sm font-bold text-red-600 dark:text-red-400">
                  Danger Zone: Deactivate Account
                </h3>
                <p className="text-xs text-zinc-500 leading-relaxed">
                  Deactivating your account will irreversibly anonymize your username and email, permanently purge all your private drafts and bookmarks, while preserving your published articles and likes under an anonymized author.
                </p>

                <button
                  onClick={() => setShowDeactivateModal(true)}
                  className="px-4 py-2 rounded-lg border border-red-300 dark:border-red-800 text-red-600 dark:text-red-400 text-xs font-semibold hover:bg-red-50 dark:hover:bg-red-950/20 transition"
                >
                  Deactivate Account...
                </button>
              </div>
            </div>
          )}
        </main>
      </div>

      {/* Deactivation Modal */}
      {showDeactivateModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
          <div className="w-full max-w-md rounded-2xl bg-white dark:bg-zinc-900 p-6 border border-red-200 dark:border-red-900 shadow-2xl space-y-4">
            <h3 className="text-lg font-bold text-red-600 dark:text-red-400 font-serif">
              Confirm Permanent Deactivation
            </h3>
            <p className="text-xs text-zinc-600 dark:text-zinc-400">
              Please enter your password to confirm. This action cannot be reversed.
            </p>
            <input
              type="password"
              placeholder="Your password..."
              value={deactivatePassword}
              onChange={(e) => setDeactivatePassword(e.target.value)}
              className="w-full px-3 py-2 text-sm rounded-lg border border-zinc-200 dark:border-zinc-800 bg-zinc-50 dark:bg-zinc-800"
            />
            <div className="flex justify-end gap-2 pt-2">
              <button
                onClick={() => setShowDeactivateModal(false)}
                className="px-3 py-1.5 text-xs text-zinc-500"
              >
                Cancel
              </button>
              <button
                onClick={handleDeactivateAccount}
                className="px-4 py-1.5 rounded-lg bg-red-600 text-white text-xs font-semibold"
              >
                Confirm Deactivation
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default function WorkspacePage() {
  return (
    <React.Suspense
      fallback={
        <div className="min-h-screen flex items-center justify-center bg-zinc-50 dark:bg-zinc-950">
          <Loader2 className="w-8 h-8 animate-spin text-zinc-400" />
        </div>
      }
    >
      <WorkspaceContent />
    </React.Suspense>
  );
}
