export interface UserProfile {
  username: string;
  display_name: string;
  bio: string;
}

export interface CurrentUser {
  id: number;
  email: string;
  username: string;
  display_name: string;
  bio: string;
  is_email_verified: boolean;
  email_verified_at: string | null;
  created_at: string;
}

export interface Category {
  id: number;
  name: string;
  slug: string;
  description?: string;
  created_at?: string;
}

export interface PostAuthor {
  username: string;
  display_name: string;
  bio: string;
}

export interface PostSummary {
  id: number;
  slug: string;
  title: string;
  excerpt: string;
  category: {
    id: number;
    name: string;
    slug: string;
  };
  author: PostAuthor;
  published_at: string | null;
  like_count: number;
  created_at: string;
  updated_at: string;
  status?: "draft" | "published";
}

export interface PostDetail extends PostSummary {
  content_markdown: string;
  content_html: string;
  status: "draft" | "published";
  is_author?: boolean;
}

export interface CommentAuthor {
  username: string;
  display_name: string;
  bio: string;
}

export interface ReplyItem {
  id: number;
  author: CommentAuthor | null;
  body: string;
  created_at: string;
  updated_at: string;
}

export interface CommentItem {
  id: number;
  author: CommentAuthor | null;
  body: string;
  is_deleted: boolean;
  deleted_at: string | null;
  created_at: string;
  updated_at: string;
  replies: ReplyItem[];
}

export interface BookmarkItem {
  id: number;
  post: PostSummary;
  created_at: string;
}

export interface PaginatedResponse<T> {
  results: T[];
  pagination: {
    count: number;
    page: number;
    page_size: number;
    total_pages: number;
    next: string | null;
    previous: string | null;
  };
}

export interface ApiError {
  code: string;
  message: string;
  details?: Record<string, unknown>;
}
