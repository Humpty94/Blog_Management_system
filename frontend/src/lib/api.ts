import {
  BookmarkItem,
  Category,
  CommentItem,
  CurrentUser,
  PaginatedResponse,
  PostDetail,
  PostSummary,
  ReplyItem,
} from "../types";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000/api/v1";

interface RequestOptions extends RequestInit {
  requiresAuth?: boolean;
}

class ApiClient {
  private accessToken: string | null = null;
  private refreshToken: string | null = null;

  constructor() {
    if (typeof window !== "undefined") {
      this.accessToken = localStorage.getItem("access_token");
      this.refreshToken = localStorage.getItem("refresh_token");
    }
  }

  public setTokens(access: string, refresh: string) {
    this.accessToken = access;
    this.refreshToken = refresh;
    if (typeof window !== "undefined") {
      localStorage.setItem("access_token", access);
      localStorage.setItem("refresh_token", refresh);
    }
  }

  public clearTokens() {
    this.accessToken = null;
    this.refreshToken = null;
    if (typeof window !== "undefined") {
      localStorage.removeItem("access_token");
      localStorage.removeItem("refresh_token");
    }
  }

  public getAccessToken(): string | null {
    if (!this.accessToken && typeof window !== "undefined") {
      this.accessToken = localStorage.getItem("access_token");
    }
    return this.accessToken;
  }

  public getRefreshToken(): string | null {
    if (!this.refreshToken && typeof window !== "undefined") {
      this.refreshToken = localStorage.getItem("refresh_token");
    }
    return this.refreshToken;
  }

  private async refreshAccessToken(): Promise<string | null> {
    const refresh = this.getRefreshToken();
    if (!refresh) return null;

    try {
      const res = await fetch(`${API_BASE_URL}/auth/refresh/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh }),
      });

      if (!res.ok) {
        this.clearTokens();
        return null;
      }

      const data = await res.json();
      this.setTokens(data.access, data.refresh);
      return data.access;
    } catch {
      this.clearTokens();
      return null;
    }
  }

  public async request<T>(
    endpoint: string,
    options: RequestOptions = {}
  ): Promise<T> {
    const { headers = {}, ...rest } = options;
    const reqHeaders: Record<string, string> = {
      "Content-Type": "application/json",
      ...(headers as Record<string, string>),
    };

    const token = this.getAccessToken();
    if (token) {
      reqHeaders["Authorization"] = `Bearer ${token}`;
    }

    const url = endpoint.startsWith("http")
      ? endpoint
      : `${API_BASE_URL}${endpoint.startsWith("/") ? "" : "/"}${endpoint}`;

    let response = await fetch(url, {
      ...rest,
      headers: reqHeaders,
    });

    // Handle 401 token expiration and automatic rotation
    if (response.status === 401 && this.getRefreshToken()) {
      const newToken = await this.refreshAccessToken();
      if (newToken) {
        reqHeaders["Authorization"] = `Bearer ${newToken}`;
        response = await fetch(url, {
          ...rest,
          headers: reqHeaders,
        });
      }
    }

    if (response.status === 204) {
      return {} as T;
    }

    const data = await response.json();

    if (!response.ok) {
      const errorMsg =
        data?.error?.message ||
        data?.message ||
        data?.detail ||
        "An unexpected error occurred.";
      const errorObj = new Error(errorMsg) as Error & {
        code?: string;
        details?: unknown;
        status?: number;
      };
      errorObj.code = data?.error?.code || "request_failed";
      errorObj.details = data?.error?.details;
      errorObj.status = response.status;
      throw errorObj;
    }

    return data as T;
  }

  // --- Auth & Users ---
  public register(payload: {
    email: string;
    username: string;
    password: string;
    display_name?: string;
  }) {
    return this.request<{ message: string; user: { username: string; email: string } }>(
      "/auth/register/",
      {
        method: "POST",
        body: JSON.stringify(payload),
      }
    );
  }

  public login(payload: { email: string; password: string }) {
    return this.request<{ access: string; refresh: string }>("/auth/login/", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  }

  public verifyEmail(token: string) {
    return this.request<{ message: string }>("/auth/verify-email/", {
      method: "POST",
      body: JSON.stringify({ token }),
    });
  }

  public resendVerification(email: string) {
    return this.request<{ message: string }>("/auth/resend-verification/", {
      method: "POST",
      body: JSON.stringify({ email }),
    });
  }

  public getCurrentUser() {
    return this.request<CurrentUser>("/users/me/", { requiresAuth: true });
  }

  public updateProfile(payload: { display_name?: string; bio?: string }) {
    return this.request<CurrentUser>("/users/me/", {
      method: "PATCH",
      requiresAuth: true,
      body: JSON.stringify(payload),
    });
  }

  public deactivateAccount(password: string) {
    return this.request<{ message: string }>("/users/me/deactivate/", {
      method: "POST",
      requiresAuth: true,
      body: JSON.stringify({ password }),
    });
  }

  // --- Categories ---
  public getCategories() {
    return this.request<Category[]>("/categories/");
  }

  // --- Posts ---
  public getPublishedPosts(params?: {
    category?: string;
    author?: string;
    search?: string;
    ordering?: string;
    page?: number;
  }) {
    const searchParams = new URLSearchParams();
    if (params?.category) searchParams.set("category", params.category);
    if (params?.author) searchParams.set("author", params.author);
    if (params?.search) searchParams.set("search", params.search);
    if (params?.ordering) searchParams.set("ordering", params.ordering);
    if (params?.page) searchParams.set("page", params.page.toString());

    const qs = searchParams.toString();
    return this.request<PaginatedResponse<PostSummary>>(
      `/posts/${qs ? `?${qs}` : ""}`
    );
  }

  public getPostBySlug(slug: string) {
    return this.request<PostDetail>(`/posts/${slug}/`);
  }

  public createPost(payload: {
    title: string;
    category_slug: string;
    content_markdown: string;
  }) {
    return this.request<PostDetail>("/posts/", {
      method: "POST",
      requiresAuth: true,
      body: JSON.stringify(payload),
    });
  }

  public updatePost(
    slug: string,
    payload: {
      title?: string;
      category_slug?: string;
      content_markdown?: string;
    }
  ) {
    return this.request<PostDetail>(`/posts/${slug}/`, {
      method: "PATCH",
      requiresAuth: true,
      body: JSON.stringify(payload),
    });
  }

  public deletePost(slug: string) {
    return this.request<void>(`/posts/${slug}/`, {
      method: "DELETE",
      requiresAuth: true,
    });
  }

  public publishPost(slug: string) {
    return this.request<PostDetail>(`/posts/${slug}/publish/`, {
      method: "POST",
      requiresAuth: true,
    });
  }

  public unpublishPost(slug: string) {
    return this.request<PostDetail>(`/posts/${slug}/unpublish/`, {
      method: "POST",
      requiresAuth: true,
    });
  }

  public getMyPosts(params?: { status?: "draft" | "published"; page?: number }) {
    const searchParams = new URLSearchParams();
    if (params?.status) searchParams.set("status", params.status);
    if (params?.page) searchParams.set("page", params.page.toString());

    const qs = searchParams.toString();
    return this.request<PaginatedResponse<PostSummary>>(
      `/users/me/posts/${qs ? `?${qs}` : ""}`,
      { requiresAuth: true }
    );
  }

  // --- Comments ---
  public getPostComments(slug: string, page = 1) {
    return this.request<PaginatedResponse<CommentItem>>(
      `/posts/${slug}/comments/?page=${page}`
    );
  }

  public createComment(
    slug: string,
    payload: { body: string; parent_id?: number | null }
  ) {
    return this.request<CommentItem | ReplyItem>(`/posts/${slug}/comments/`, {
      method: "POST",
      requiresAuth: true,
      body: JSON.stringify(payload),
    });
  }

  public deleteComment(commentId: number) {
    return this.request<void>(`/comments/${commentId}/`, {
      method: "DELETE",
      requiresAuth: true,
    });
  }

  // --- Engagement (Likes & Bookmarks) ---
  public likePost(slug: string) {
    return this.request<{ liked: boolean; like_count: number }>(
      `/posts/${slug}/like/`,
      {
        method: "POST",
        requiresAuth: true,
      }
    );
  }

  public unlikePost(slug: string) {
    return this.request<{ liked: boolean; like_count: number }>(
      `/posts/${slug}/like/`,
      {
        method: "DELETE",
        requiresAuth: true,
      }
    );
  }

  public bookmarkPost(slug: string) {
    return this.request<{ bookmarked: boolean }>(`/posts/${slug}/bookmark/`, {
      method: "POST",
      requiresAuth: true,
    });
  }

  public unbookmarkPost(slug: string) {
    return this.request<void>(`/posts/${slug}/bookmark/`, {
      method: "DELETE",
      requiresAuth: true,
    });
  }

  public getMyBookmarks(page = 1) {
    return this.request<PaginatedResponse<BookmarkItem>>(
      `/users/me/bookmarks/?page=${page}`,
      { requiresAuth: true }
    );
  }
}

export const api = new ApiClient();
