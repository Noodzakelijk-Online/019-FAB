import { useState, useMemo } from "react";
import { useAuth } from "@/_core/hooks/useAuth";
import { trpc } from "@/lib/trpc";
import AdminLayout from "@/components/AdminLayout";
import { Button } from "@/components/ui/button";
import {
  Plus,
  Edit,
  Trash2,
  Eye,
  EyeOff,
  Search,
  FileText,
  ExternalLink,
} from "lucide-react";
import { toast } from "sonner";

function slugify(text: string): string {
  return text
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/(^-|-$)/g, "");
}

export default function AdminBlog() {
  const { user, loading: authLoading } = useAuth();
  const [searchQuery, setSearchQuery] = useState("");
  const [showEditor, setShowEditor] = useState(false);
  const [editingPost, setEditingPost] = useState<any>(null);

  // Form state
  const [title, setTitle] = useState("");
  const [titleNl, setTitleNl] = useState("");
  const [slug, setSlug] = useState("");
  const [excerpt, setExcerpt] = useState("");
  const [excerptNl, setExcerptNl] = useState("");
  const [content, setContent] = useState("");
  const [contentNl, setContentNl] = useState("");
  const [category, setCategory] = useState("update");
  const [coverImage, setCoverImage] = useState("");
  const [published, setPublished] = useState(false);
  const [readTime, setReadTime] = useState(3);

  const { data: posts, isLoading, refetch } = trpc.blog.list.useQuery();
  const createMutation = trpc.blog.create.useMutation({
    onSuccess: () => {
      toast.success("Post created successfully");
      resetForm();
      refetch();
    },
    onError: (err) => toast.error(err.message),
  });
  const updateMutation = trpc.blog.update.useMutation({
    onSuccess: () => {
      toast.success("Post updated successfully");
      resetForm();
      refetch();
    },
    onError: (err) => toast.error(err.message),
  });
  const deleteMutation = trpc.blog.delete.useMutation({
    onSuccess: () => {
      toast.success("Post deleted");
      refetch();
    },
    onError: (err) => toast.error(err.message),
  });

  const filteredPosts = useMemo(() => {
    if (!posts) return [];
    if (!searchQuery) return posts;
    const q = searchQuery.toLowerCase();
    return posts.filter(
      (p) =>
        p.title.toLowerCase().includes(q) ||
        (p.titleNl && p.titleNl.toLowerCase().includes(q)) ||
        p.slug.includes(q)
    );
  }, [posts, searchQuery]);

  function resetForm() {
    setShowEditor(false);
    setEditingPost(null);
    setTitle("");
    setTitleNl("");
    setSlug("");
    setExcerpt("");
    setExcerptNl("");
    setContent("");
    setContentNl("");
    setCategory("update");
    setCoverImage("");
    setPublished(false);
    setReadTime(3);
  }

  function openEditor(post?: any) {
    if (post) {
      setEditingPost(post);
      setTitle(post.title);
      setTitleNl(post.titleNl || "");
      setSlug(post.slug);
      setExcerpt(post.excerpt);
      setExcerptNl(post.excerptNl || "");
      setContent(post.content);
      setContentNl(post.contentNl || "");
      setCategory(post.category);
      setCoverImage(post.coverImage || "");
      setPublished(post.published);
      setReadTime(post.readTimeMinutes || 3);
    } else {
      resetForm();
    }
    setShowEditor(true);
  }

  function handleSave() {
    if (!title || !slug || !excerpt || !content) {
      toast.error("Please fill in all required fields (Title, Slug, Excerpt, Content)");
      return;
    }

    if (editingPost) {
      updateMutation.mutate({
        id: editingPost.id,
        title,
        titleNl: titleNl || undefined,
        slug,
        excerpt,
        excerptNl: excerptNl || undefined,
        content,
        contentNl: contentNl || undefined,
        category,
        coverImage: coverImage || undefined,
        published,
        readTimeMinutes: readTime,
      });
    } else {
      createMutation.mutate({
        title,
        titleNl: titleNl || undefined,
        slug,
        excerpt,
        excerptNl: excerptNl || undefined,
        content,
        contentNl: contentNl || undefined,
        category,
        coverImage: coverImage || undefined,
        published,
        readTimeMinutes: readTime,
      });
    }
  }

  function handleDelete(id: number) {
    if (confirm("Are you sure you want to delete this post?")) {
      deleteMutation.mutate({ id });
    }
  }

  function handleTogglePublish(post: any) {
    updateMutation.mutate({
      id: post.id,
      published: !post.published,
    });
  }

  const formatDate = (date: Date | string | null) => {
    if (!date) return "—";
    return new Date(date).toLocaleDateString("en-US", {
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  };

  if (authLoading || isLoading) {
    return (
      <AdminLayout>
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin w-8 h-8 border-2 border-teal border-t-transparent rounded-full" />
        </div>
      </AdminLayout>
    );
  }

  if (!user || user.role !== "admin") {
    return (
      <AdminLayout>
        <div className="text-center py-16">
          <h2 className="text-xl text-charcoal mb-2">Access Denied</h2>
          <p className="text-charcoal-light">You need admin privileges to access this page.</p>
        </div>
      </AdminLayout>
    );
  }

  if (showEditor) {
    return (
      <AdminLayout>
        <div className="max-w-4xl">
          <div className="flex items-center justify-between mb-8">
            <h1 className="text-2xl font-semibold text-charcoal">
              {editingPost ? "Edit Post" : "New Post"}
            </h1>
            <div className="flex gap-3">
              <Button variant="outline" onClick={resetForm} className="rounded-xl">
                Cancel
              </Button>
              <Button
                onClick={handleSave}
                className="bg-teal hover:bg-teal-light text-white rounded-xl"
                disabled={createMutation.isPending || updateMutation.isPending}
              >
                {createMutation.isPending || updateMutation.isPending ? "Saving..." : "Save Post"}
              </Button>
            </div>
          </div>

          <div className="space-y-6">
            {/* Title EN */}
            <div>
              <label className="block text-sm font-medium text-charcoal mb-1.5">
                Title (English) *
              </label>
              <input
                type="text"
                value={title}
                onChange={(e) => {
                  setTitle(e.target.value);
                  if (!editingPost) setSlug(slugify(e.target.value));
                }}
                className="w-full px-4 py-3 rounded-xl border border-sand-dark/30 bg-white text-charcoal focus:outline-none focus:ring-2 focus:ring-teal/30"
                placeholder="Enter post title..."
              />
            </div>

            {/* Title NL */}
            <div>
              <label className="block text-sm font-medium text-charcoal mb-1.5">
                Title (Dutch)
              </label>
              <input
                type="text"
                value={titleNl}
                onChange={(e) => setTitleNl(e.target.value)}
                className="w-full px-4 py-3 rounded-xl border border-sand-dark/30 bg-white text-charcoal focus:outline-none focus:ring-2 focus:ring-teal/30"
                placeholder="Voer posttitel in..."
              />
            </div>

            {/* Slug */}
            <div>
              <label className="block text-sm font-medium text-charcoal mb-1.5">
                Slug *
              </label>
              <input
                type="text"
                value={slug}
                onChange={(e) => setSlug(slugify(e.target.value))}
                className="w-full px-4 py-3 rounded-xl border border-sand-dark/30 bg-white text-charcoal focus:outline-none focus:ring-2 focus:ring-teal/30"
                placeholder="post-url-slug"
              />
            </div>

            {/* Row: Category, Read Time, Published */}
            <div className="grid grid-cols-3 gap-4">
              <div>
                <label className="block text-sm font-medium text-charcoal mb-1.5">Category</label>
                <select
                  value={category}
                  onChange={(e) => setCategory(e.target.value)}
                  className="w-full px-4 py-3 rounded-xl border border-sand-dark/30 bg-white text-charcoal focus:outline-none focus:ring-2 focus:ring-teal/30"
                >
                  <option value="update">Update</option>
                  <option value="milestone">Milestone</option>
                  <option value="feature">Feature</option>
                  <option value="announcement">Announcement</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-charcoal mb-1.5">Read Time (min)</label>
                <input
                  type="number"
                  value={readTime}
                  onChange={(e) => setReadTime(parseInt(e.target.value) || 3)}
                  min={1}
                  max={60}
                  className="w-full px-4 py-3 rounded-xl border border-sand-dark/30 bg-white text-charcoal focus:outline-none focus:ring-2 focus:ring-teal/30"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-charcoal mb-1.5">Status</label>
                <button
                  onClick={() => setPublished(!published)}
                  className={`w-full px-4 py-3 rounded-xl border text-left font-medium transition-colors ${
                    published
                      ? "bg-teal/10 border-teal/30 text-teal"
                      : "bg-sand/40 border-sand-dark/30 text-charcoal-light"
                  }`}
                >
                  {published ? "Published" : "Draft"}
                </button>
              </div>
            </div>

            {/* Cover Image URL */}
            <div>
              <label className="block text-sm font-medium text-charcoal mb-1.5">
                Cover Image URL
              </label>
              <input
                type="text"
                value={coverImage}
                onChange={(e) => setCoverImage(e.target.value)}
                className="w-full px-4 py-3 rounded-xl border border-sand-dark/30 bg-white text-charcoal focus:outline-none focus:ring-2 focus:ring-teal/30"
                placeholder="https://..."
              />
            </div>

            {/* Excerpt EN */}
            <div>
              <label className="block text-sm font-medium text-charcoal mb-1.5">
                Excerpt (English) *
              </label>
              <textarea
                value={excerpt}
                onChange={(e) => setExcerpt(e.target.value)}
                rows={3}
                className="w-full px-4 py-3 rounded-xl border border-sand-dark/30 bg-white text-charcoal focus:outline-none focus:ring-2 focus:ring-teal/30 resize-y"
                placeholder="Brief summary of the post..."
              />
            </div>

            {/* Excerpt NL */}
            <div>
              <label className="block text-sm font-medium text-charcoal mb-1.5">
                Excerpt (Dutch)
              </label>
              <textarea
                value={excerptNl}
                onChange={(e) => setExcerptNl(e.target.value)}
                rows={3}
                className="w-full px-4 py-3 rounded-xl border border-sand-dark/30 bg-white text-charcoal focus:outline-none focus:ring-2 focus:ring-teal/30 resize-y"
                placeholder="Korte samenvatting van het bericht..."
              />
            </div>

            {/* Content EN */}
            <div>
              <label className="block text-sm font-medium text-charcoal mb-1.5">
                Content (English) * — Markdown supported
              </label>
              <textarea
                value={content}
                onChange={(e) => setContent(e.target.value)}
                rows={12}
                className="w-full px-4 py-3 rounded-xl border border-sand-dark/30 bg-white text-charcoal font-mono text-sm focus:outline-none focus:ring-2 focus:ring-teal/30 resize-y"
                placeholder="Write your post content in Markdown..."
              />
            </div>

            {/* Content NL */}
            <div>
              <label className="block text-sm font-medium text-charcoal mb-1.5">
                Content (Dutch) — Markdown supported
              </label>
              <textarea
                value={contentNl}
                onChange={(e) => setContentNl(e.target.value)}
                rows={12}
                className="w-full px-4 py-3 rounded-xl border border-sand-dark/30 bg-white text-charcoal font-mono text-sm focus:outline-none focus:ring-2 focus:ring-teal/30 resize-y"
                placeholder="Schrijf je berichtinhoud in Markdown..."
              />
            </div>
          </div>
        </div>
      </AdminLayout>
    );
  }

  return (
    <AdminLayout>
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-semibold text-charcoal">Blog Posts</h1>
          <p className="text-charcoal-light text-sm mt-1">
            {posts?.length || 0} total posts
          </p>
        </div>
        <Button
          onClick={() => openEditor()}
          className="bg-teal hover:bg-teal-light text-white rounded-xl"
        >
          <Plus className="w-4 h-4 mr-2" />
          New Post
        </Button>
      </div>

      {/* Search */}
      <div className="relative mb-6">
        <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-charcoal-light" />
        <input
          type="text"
          placeholder="Search posts..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="w-full pl-12 pr-4 py-3 rounded-xl border border-sand-dark/30 bg-white text-charcoal placeholder:text-charcoal-light/60 focus:outline-none focus:ring-2 focus:ring-teal/30"
        />
      </div>

      {/* Posts Table */}
      {filteredPosts.length === 0 ? (
        <div className="text-center py-16 bg-white rounded-2xl border border-sand-dark/20">
          <FileText className="w-12 h-12 text-sand-dark/40 mx-auto mb-4" />
          <h3 className="text-lg text-charcoal mb-2 font-semibold">No posts yet</h3>
          <p className="text-charcoal-light text-sm mb-6">
            Create your first blog post to share updates with your audience.
          </p>
          <Button
            onClick={() => openEditor()}
            className="bg-teal hover:bg-teal-light text-white rounded-xl"
          >
            <Plus className="w-4 h-4 mr-2" />
            Create Post
          </Button>
        </div>
      ) : (
        <div className="bg-white rounded-2xl border border-sand-dark/20 overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="border-b border-sand">
                <th className="text-left px-6 py-4 text-sm font-medium text-charcoal-light">Title</th>
                <th className="text-left px-4 py-4 text-sm font-medium text-charcoal-light">Category</th>
                <th className="text-left px-4 py-4 text-sm font-medium text-charcoal-light">Status</th>
                <th className="text-left px-4 py-4 text-sm font-medium text-charcoal-light">Date</th>
                <th className="text-right px-6 py-4 text-sm font-medium text-charcoal-light">Actions</th>
              </tr>
            </thead>
            <tbody>
              {filteredPosts.map((post) => (
                <tr key={post.id} className="border-b border-sand/60 hover:bg-sand/20 transition-colors">
                  <td className="px-6 py-4">
                    <div className="font-medium text-charcoal text-sm">{post.title}</div>
                    <div className="text-xs text-charcoal-light mt-0.5">/{post.slug}</div>
                  </td>
                  <td className="px-4 py-4">
                    <span className={`px-2.5 py-1 rounded-full text-xs font-medium ${
                      post.category === "update" ? "bg-teal/10 text-teal" :
                      post.category === "milestone" ? "bg-sage-light text-sage" :
                      post.category === "feature" ? "bg-sand text-charcoal" :
                      "bg-teal text-white"
                    }`}>
                      {post.category}
                    </span>
                  </td>
                  <td className="px-4 py-4">
                    <span className={`inline-flex items-center gap-1.5 text-xs font-medium ${
                      post.published ? "text-teal" : "text-charcoal-light"
                    }`}>
                      {post.published ? <Eye className="w-3 h-3" /> : <EyeOff className="w-3 h-3" />}
                      {post.published ? "Published" : "Draft"}
                    </span>
                  </td>
                  <td className="px-4 py-4 text-sm text-charcoal-light">
                    {formatDate(post.publishedAt || post.createdAt)}
                  </td>
                  <td className="px-6 py-4">
                    <div className="flex items-center justify-end gap-2">
                      {post.published && (
                        <a
                          href={`/blog/${post.slug}`}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="p-2 rounded-lg hover:bg-sand/60 text-charcoal-light hover:text-teal transition-colors"
                          title="View post"
                        >
                          <ExternalLink className="w-4 h-4" />
                        </a>
                      )}
                      <button
                        onClick={() => handleTogglePublish(post)}
                        className="p-2 rounded-lg hover:bg-sand/60 text-charcoal-light hover:text-teal transition-colors"
                        title={post.published ? "Unpublish" : "Publish"}
                      >
                        {post.published ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                      </button>
                      <button
                        onClick={() => openEditor(post)}
                        className="p-2 rounded-lg hover:bg-sand/60 text-charcoal-light hover:text-teal transition-colors"
                        title="Edit"
                      >
                        <Edit className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => handleDelete(post.id)}
                        className="p-2 rounded-lg hover:bg-red-50 text-charcoal-light hover:text-red-500 transition-colors"
                        title="Delete"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </AdminLayout>
  );
}
