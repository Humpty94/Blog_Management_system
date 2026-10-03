"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import {
  ArrowLeft,
  Bookmark,
  Calendar,
  Clock,
  CornerDownRight,
  Heart,
  Loader2,
  MessageSquare,
  Share2,
  Trash2,
} from "lucide-react";
import { Navbar } from "../../../components/Navbar";
import { Footer } from "../../../components/Footer";
import { useAuth } from "../../../context/AuthContext";
import { api } from "../../../lib/api";
import { CommentItem, PostDetail } from "../../../types";

export default function PostReaderPage() {
  const params = useParams();
  const slug = params?.slug as string;
  const { user } = useAuth();

  const [post, setPost] = useState<PostDetail | null>(null);
  const [comments, setComments] = useState<CommentItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Engagement state
  const [liked, setLiked] = useState(false);
  const [likeCount, setLikeCount] = useState(0);
  const [bookmarked, setBookmarked] = useState(false);
  const [selfLikeWarning, setSelfLikeWarning] = useState(false);

  // Comment input state
  const [newCommentBody, setNewCommentBody] = useState("");
  const [replyingToId, setReplyingToId] = useState<number | null>(null);
  const [replyBody, setReplyBody] = useState("");
  const [submittingComment, setSubmittingComment] = useState(false);

  useEffect(() => {
    if (!slug) return;
    setLoading(true);

    Promise.all([api.getPostBySlug(slug), api.getPostComments(slug)])
      .then(([postData, commentsData]) => {
        setPost(postData);
        setLikeCount(postData.like_count);
        setComments(commentsData.results);
      })
      .catch((err) => {
        console.error("Failed to load post:", err);
        setError("Article not found or private draft.");
      })
      .finally(() => {
        setLoading(false);
      });
  }, [slug]);

  const handleLike = async () => {
    if (!user) {
      alert("Please sign in to like this article.");
      return;
    }

    if (user.username === post?.author.username) {
      setSelfLikeWarning(true);
      setTimeout(() => setSelfLikeWarning(false), 3000);
      return;
    }

    const nextLiked = !liked;
    setLiked(nextLiked);
    setLikeCount((c) => (nextLiked ? c + 1 : Math.max(0, c - 1)));

    try {
      if (nextLiked) {
        const res = await api.likePost(slug);
        setLikeCount(res.like_count);
      } else {
        const res = await api.unlikePost(slug);
        setLikeCount(res.like_count);
      }
    } catch (err) {
      console.error("Like toggle error:", err);
      // Revert on error
      setLiked(!nextLiked);
      setLikeCount((c) => (!nextLiked ? c + 1 : Math.max(0, c - 1)));
    }
  };

  const handleBookmark = async () => {
    if (!user) {
      alert("Please sign in to save articles to your private bookmarks.");
      return;
    }

    const nextBookmarked = !bookmarked;
    setBookmarked(nextBookmarked);

    try {
      if (nextBookmarked) {
        await api.bookmarkPost(slug);
      } else {
        await api.unbookmarkPost(slug);
      }
    } catch (err) {
      console.error("Bookmark toggle error:", err);
      setBookmarked(!nextBookmarked);
    }
  };

  const handleCreateRootComment = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newCommentBody.trim() || !user) return;
    setSubmittingComment(true);

    try {
      await api.createComment(slug, { body: newCommentBody.trim() });
      setNewCommentBody("");
      // Reload comments
      const updated = await api.getPostComments(slug);
      setComments(updated.results);
    } catch (err: unknown) {
      const e = err as { message?: string };
      alert(e.message || "Failed to post comment.");
    } finally {
      setSubmittingComment(false);
    }
  };

  const handleCreateReply = async (parentId: number) => {
    if (!replyBody.trim() || !user) return;
    setSubmittingComment(true);

    try {
      await api.createComment(slug, {
        body: replyBody.trim(),
        parent_id: parentId,
      });
      setReplyBody("");
      setReplyingToId(null);
      // Reload comments
      const updated = await api.getPostComments(slug);
      setComments(updated.results);
    } catch (err: unknown) {
      const e = err as { message?: string };
      alert(e.message || "Failed to post reply.");
    } finally {
      setSubmittingComment(false);
    }
  };

  const handleDeleteComment = async (commentId: number) => {
    if (!confirm("Are you sure you want to delete this comment?")) return;

    try {
      await api.deleteComment(commentId);
      const updated = await api.getPostComments(slug);
      setComments(updated.results);
    } catch (err) {
      console.error("Failed to delete comment:", err);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex flex-col bg-zinc-50 dark:bg-zinc-950">
        <Navbar />
        <div className="flex-1 flex items-center justify-center py-24 text-zinc-400">
          <Loader2 className="w-8 h-8 animate-spin" />
        </div>
        <Footer />
      </div>
    );
  }

  if (error || !post) {
    return (
      <div className="min-h-screen flex flex-col bg-zinc-50 dark:bg-zinc-950">
        <Navbar />
        <div className="flex-1 flex flex-col items-center justify-center py-24 text-center px-4">
          <h2 className="text-2xl font-bold font-serif text-zinc-900 dark:text-white">
            Article Not Found
          </h2>
          <p className="text-sm text-zinc-500 mt-2 max-w-sm">
            {error || "This article may be private, unpublished, or has been removed."}
          </p>
          <Link
            href="/"
            className="mt-6 inline-flex items-center gap-2 text-xs font-semibold px-4 py-2 rounded-lg bg-zinc-900 dark:bg-white text-white dark:text-zinc-900"
          >
            <ArrowLeft className="w-4 h-4" />
            <span>Back to Publication</span>
          </Link>
        </div>
        <Footer />
      </div>
    );
  }

  const isAuthor = user?.username === post.author.username;

  return (
    <div className="min-h-screen flex flex-col bg-white dark:bg-zinc-950 text-zinc-900 dark:text-zinc-100 transition-colors">
      <Navbar />

      <main className="flex-1 max-w-3xl mx-auto w-full px-4 sm:px-6 py-12">
        {/* Back Link */}
        <div className="mb-8">
          <Link
            href="/"
            className="inline-flex items-center gap-1.5 text-xs font-semibold text-zinc-500 hover:text-zinc-900 dark:hover:text-white transition"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            <span>All Articles</span>
          </Link>
        </div>

        {/* Article Header */}
        <header className="space-y-6 pb-8 border-b border-zinc-100 dark:border-zinc-800">
          <div className="flex items-center gap-2.5 text-xs text-zinc-500">
            <span className="font-semibold uppercase tracking-wider px-2.5 py-0.5 rounded bg-zinc-100 dark:bg-zinc-850 text-zinc-700 dark:text-zinc-300">
              {post.category.name}
            </span>
            <span>•</span>
            <span className="flex items-center gap-1">
              <Calendar className="w-3.5 h-3.5" />
              {new Date(post.published_at || post.created_at).toLocaleDateString("en-US", {
                month: "long",
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

          <h1 className="text-3xl sm:text-5xl font-extrabold tracking-tight font-serif text-zinc-950 dark:text-white leading-[1.15]">
            {post.title}
          </h1>

          {/* Author Byline */}
          <div className="pt-2 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-full bg-zinc-900 dark:bg-white text-white dark:text-zinc-900 flex items-center justify-center font-bold text-sm uppercase shadow-sm">
                {post.author.username.slice(0, 2)}
              </div>
              <div>
                <p className="text-sm font-bold text-zinc-900 dark:text-white">
                  {post.author.display_name || post.author.username}
                </p>
                <p className="text-xs text-zinc-500">{post.author.bio || "Staff Author"}</p>
              </div>
            </div>

            {isAuthor && (
              <Link
                href={`/workspace?edit=${post.slug}`}
                className="text-xs font-semibold px-3 py-1.5 rounded-lg border border-zinc-200 dark:border-zinc-800 hover:bg-zinc-100 dark:hover:bg-zinc-850 transition"
              >
                Edit in Studio
              </Link>
            )}
          </div>
        </header>

        {/* Article Body */}
        <article className="py-10 prose prose-zinc dark:prose-invert max-w-none prose-headings:font-serif prose-headings:tracking-tight prose-a:text-zinc-900 dark:prose-a:text-white prose-pre:bg-zinc-900 prose-pre:border prose-pre:border-zinc-800 leading-relaxed text-zinc-800 dark:text-zinc-200">
          <div
            dangerouslySetInnerHTML={{ __html: post.content_html }}
            className="space-y-4"
          />
        </article>

        {/* Engagement Floating / Action Bar */}
        <section className="py-8 my-8 border-y border-zinc-100 dark:border-zinc-800 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="relative">
              <button
                onClick={handleLike}
                className={`flex items-center gap-2 px-3.5 py-2 rounded-full border text-xs font-semibold transition ${
                  liked
                    ? "border-red-200 bg-red-50 text-red-600 dark:border-red-900/50 dark:bg-red-950/30 dark:text-red-400"
                    : "border-zinc-200 dark:border-zinc-800 hover:bg-zinc-100 dark:hover:bg-zinc-850 text-zinc-700 dark:text-zinc-300"
                }`}
              >
                <Heart
                  className={`w-4 h-4 ${liked ? "fill-current text-red-500" : "text-zinc-500"}`}
                />
                <span>{likeCount} likes</span>
              </button>

              {selfLikeWarning && (
                <div className="absolute left-0 bottom-full mb-2 w-56 rounded-lg bg-zinc-900 text-white text-[11px] p-2 shadow-lg animate-in fade-in z-20">
                  Authors cannot like their own posts (enforced by backend domain rules).
                </div>
              )}
            </div>

            <button
              onClick={handleBookmark}
              className={`p-2 rounded-full border text-xs transition ${
                bookmarked
                  ? "border-zinc-900 dark:border-white bg-zinc-900 dark:bg-white text-white dark:text-zinc-900"
                  : "border-zinc-200 dark:border-zinc-800 hover:bg-zinc-100 dark:hover:bg-zinc-850 text-zinc-600 dark:text-zinc-400"
              }`}
              title="Bookmark this post"
            >
              <Bookmark className="w-4 h-4" />
            </button>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => {
                if (navigator.share) {
                  navigator.share({ title: post.title, url: window.location.href });
                } else {
                  navigator.clipboard.writeText(window.location.href);
                  alert("Article link copied to clipboard!");
                }
              }}
              className="p-2 rounded-full border border-zinc-200 dark:border-zinc-800 hover:bg-zinc-100 dark:hover:bg-zinc-850 text-zinc-600 dark:text-zinc-400 transition"
              title="Share article"
            >
              <Share2 className="w-4 h-4" />
            </button>
          </div>
        </section>

        {/* =================================================================== */}
        {/* DISCUSSION & COMMENT ENGINE */}
        {/* =================================================================== */}
        <section className="pt-6 space-y-8">
          <div className="flex items-center justify-between">
            <h3 className="text-xl font-bold font-serif text-zinc-900 dark:text-white flex items-center gap-2">
              <MessageSquare className="w-5 h-5" />
              <span>Discussion</span>
              <span className="text-sm font-sans font-normal text-zinc-400">
                ({comments.length})
              </span>
            </h3>
          </div>

          {/* New Comment Box */}
          {user ? (
            <form onSubmit={handleCreateRootComment} className="space-y-3">
              <textarea
                rows={3}
                required
                value={newCommentBody}
                onChange={(e) => setNewCommentBody(e.target.value)}
                placeholder="Share your thoughts on this architecture..."
                className="w-full p-3.5 text-sm rounded-xl border border-zinc-200 dark:border-zinc-800 bg-zinc-50 dark:bg-zinc-900 text-zinc-900 dark:text-white placeholder-zinc-400 focus:outline-none focus:ring-2 focus:ring-zinc-900 dark:focus:ring-white transition"
              />
              <div className="flex justify-end">
                <button
                  type="submit"
                  disabled={submittingComment || !newCommentBody.trim()}
                  className="px-4 py-2 rounded-lg bg-zinc-900 hover:bg-zinc-800 dark:bg-white dark:hover:bg-zinc-100 text-white dark:text-zinc-900 font-semibold text-xs transition disabled:opacity-50"
                >
                  {submittingComment ? "Posting..." : "Post Comment"}
                </button>
              </div>
            </form>
          ) : (
            <div className="p-4 rounded-xl border border-zinc-200 dark:border-zinc-800 bg-zinc-50 dark:bg-zinc-900/50 text-center text-xs text-zinc-500">
              Please sign in to participate in the discussion.
            </div>
          )}

          {/* Comments List */}
          <div className="space-y-6">
            {comments.map((comment) => (
              <div
                key={comment.id}
                className="p-5 rounded-xl border border-zinc-200/80 dark:border-zinc-800 bg-zinc-50/50 dark:bg-zinc-900/40 space-y-3"
              >
                {/* Root Comment Header */}
                <div className="flex items-center justify-between text-xs">
                  <div className="flex items-center gap-2">
                    <div className="w-6 h-6 rounded-full bg-zinc-800 dark:bg-zinc-200 text-white dark:text-zinc-900 flex items-center justify-center font-bold text-[10px] uppercase">
                      {comment.author ? comment.author.username.slice(0, 2) : "?"}
                    </div>
                    <span className="font-semibold text-zinc-900 dark:text-white">
                      {comment.is_deleted
                        ? "Deleted user"
                        : comment.author?.display_name || comment.author?.username}
                    </span>
                    <span className="text-zinc-400">•</span>
                    <span className="text-zinc-400">
                      {new Date(comment.created_at).toLocaleDateString()}
                    </span>
                  </div>

                  {!comment.is_deleted && user?.username === comment.author?.username && (
                    <button
                      onClick={() => handleDeleteComment(comment.id)}
                      className="text-zinc-400 hover:text-red-500 transition"
                      title="Delete comment"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  )}
                </div>

                {/* Root Comment Body */}
                <p
                  className={`text-sm leading-relaxed ${
                    comment.is_deleted
                      ? "italic text-zinc-400 dark:text-zinc-500"
                      : "text-zinc-800 dark:text-zinc-200"
                  }`}
                >
                  {comment.body}
                </p>

                {/* Reply Button (Only on root comments) */}
                {user && !comment.is_deleted && (
                  <div className="pt-1">
                    <button
                      onClick={() =>
                        setReplyingToId(replyingToId === comment.id ? null : comment.id)
                      }
                      className="text-xs font-semibold text-zinc-500 hover:text-zinc-900 dark:hover:text-white transition flex items-center gap-1"
                    >
                      <CornerDownRight className="w-3 h-3" />
                      <span>{replyingToId === comment.id ? "Cancel" : "Reply"}</span>
                    </button>
                  </div>
                )}

                {/* Reply Form */}
                {replyingToId === comment.id && (
                  <div className="mt-3 pl-4 border-l-2 border-zinc-300 dark:border-zinc-700 space-y-2">
                    <textarea
                      rows={2}
                      value={replyBody}
                      onChange={(e) => setReplyBody(e.target.value)}
                      placeholder="Write your reply..."
                      className="w-full p-2.5 text-xs rounded-lg border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 text-zinc-900 dark:text-white focus:outline-none focus:ring-1 focus:ring-zinc-900 dark:focus:ring-white"
                    />
                    <div className="flex justify-end gap-2">
                      <button
                        onClick={() => {
                          setReplyingToId(null);
                          setReplyBody("");
                        }}
                        className="px-3 py-1 text-xs text-zinc-500 hover:text-zinc-800"
                      >
                        Cancel
                      </button>
                      <button
                        onClick={() => handleCreateReply(comment.id)}
                        disabled={submittingComment || !replyBody.trim()}
                        className="px-3 py-1 rounded bg-zinc-900 dark:bg-white text-white dark:text-zinc-900 text-xs font-semibold"
                      >
                        Send Reply
                      </button>
                    </div>
                  </div>
                )}

                {/* Nested Replies Stream (1 Level Only) */}
                {comment.replies && comment.replies.length > 0 && (
                  <div className="mt-4 pl-4 border-l-2 border-zinc-200 dark:border-zinc-800 space-y-3">
                    {comment.replies.map((reply) => (
                      <div
                        key={reply.id}
                        className="p-3 rounded-lg bg-white dark:bg-zinc-900 border border-zinc-100 dark:border-zinc-800/60 space-y-1.5"
                      >
                        <div className="flex items-center justify-between text-xs">
                          <div className="flex items-center gap-2">
                            <span className="font-semibold text-zinc-900 dark:text-white">
                              {reply.author?.display_name || reply.author?.username}
                            </span>
                            <span className="text-zinc-400">•</span>
                            <span className="text-zinc-400">
                              {new Date(reply.created_at).toLocaleDateString()}
                            </span>
                          </div>

                          {user?.username === reply.author?.username && (
                            <button
                              onClick={() => handleDeleteComment(reply.id)}
                              className="text-zinc-400 hover:text-red-500 transition"
                              title="Delete reply"
                            >
                              <Trash2 className="w-3.5 h-3.5" />
                            </button>
                          )}
                        </div>

                        <p className="text-xs text-zinc-700 dark:text-zinc-300 leading-relaxed">
                          {reply.body}
                        </p>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        </section>
      </main>

      <Footer />
    </div>
  );
}
