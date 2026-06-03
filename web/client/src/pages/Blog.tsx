import { useState } from "react";
import { motion } from "framer-motion";
import { Calendar, Clock, ArrowRight, Search, BookOpen } from "lucide-react";
import { Button } from "@/components/ui/button";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import { Link } from "wouter";
import { useLanguage } from "@/contexts/LanguageContext";
import { trpc } from "@/lib/trpc";

const fadeUp = {
  hidden: { opacity: 0, y: 30 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.7, ease: [0.25, 0.1, 0.25, 1] as const } },
};

const stagger = {
  visible: { transition: { staggerChildren: 0.12 } },
};

const categoryColors: Record<string, string> = {
  update: "bg-teal/10 text-teal",
  milestone: "bg-sage-light text-sage",
  feature: "bg-sand text-charcoal",
  announcement: "bg-teal text-white",
  technology: "bg-teal-light/10 text-teal-light",
  guide: "bg-sage/10 text-sage",
};

export default function Blog() {
  const { t, lang: language } = useLanguage();
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);

  const { data: posts, isLoading } = trpc.blog.published.useQuery({});

  const categories = [
    { key: null, label: t("blog.allPosts") },
    { key: "update", label: t("blog.catUpdate") },
    { key: "milestone", label: t("blog.catMilestone") },
    { key: "feature", label: t("blog.catFeature") },
    { key: "announcement", label: t("blog.catAnnouncement") },
    { key: "technology", label: t("blog.catTechnology") },
    { key: "guide", label: t("blog.catGuide") },
  ];

  const filteredPosts = (posts ?? []).filter((post) => {
    const title = language === "nl" && post.titleNl ? post.titleNl : post.title;
    const excerpt = language === "nl" && post.excerptNl ? post.excerptNl : post.excerpt;
    const matchesSearch = !searchQuery || 
      title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      excerpt.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesCategory = !selectedCategory || post.category === selectedCategory;
    return matchesSearch && matchesCategory;
  });

  const formatDate = (date: Date | string | null) => {
    if (!date) return "";
    const d = new Date(date);
    return d.toLocaleDateString(language === "nl" ? "nl-NL" : "en-US", {
      year: "numeric",
      month: "long",
      day: "numeric",
    });
  };

  return (
    <div className="min-h-screen bg-warm-white">
      <Navbar />

      {/* Hero */}
      <section className="relative overflow-hidden pt-24 pb-12 lg:pt-32 lg:pb-16">
        <div className="container">
          <motion.div
            className="max-w-3xl mx-auto text-center"
            initial="hidden"
            animate="visible"
            variants={stagger}
          >
            <motion.div variants={fadeUp} className="mb-4">
              <span className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-sage-light text-teal text-sm font-medium tracking-wide">
                <BookOpen className="w-4 h-4" />
                {t("blog.badge")}
              </span>
            </motion.div>
            <motion.h1
              variants={fadeUp}
              className="text-4xl sm:text-5xl lg:text-[3.5rem] leading-[1.1] tracking-tight text-charcoal mb-6"
            >
              {t("blog.title")}
            </motion.h1>
            <motion.p
              variants={fadeUp}
              className="text-lg lg:text-xl text-charcoal-light max-w-xl mx-auto leading-relaxed"
            >
              {t("blog.desc")}
            </motion.p>
          </motion.div>
        </div>
      </section>

      {/* Search & Filters */}
      <section className="pb-8">
        <div className="container">
          <motion.div
            className="max-w-4xl mx-auto"
            initial="hidden"
            animate="visible"
            variants={stagger}
          >
            {/* Search */}
            <motion.div variants={fadeUp} className="relative mb-6">
              <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-charcoal-light" />
              <input
                type="text"
                placeholder={t("blog.searchPlaceholder")}
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-12 pr-4 py-3.5 rounded-xl border border-sand-dark/30 bg-white text-charcoal placeholder:text-charcoal-light/60 focus:outline-none focus:ring-2 focus:ring-teal/30 focus:border-teal/50 transition-all"
              />
            </motion.div>

            {/* Category Filters */}
            <motion.div variants={fadeUp} className="flex flex-wrap gap-2">
              {categories.map((cat) => (
                <button
                  key={cat.key ?? "all"}
                  onClick={() => setSelectedCategory(cat.key)}
                  className={`px-4 py-2 rounded-full text-sm font-medium transition-all duration-200 ${
                    selectedCategory === cat.key
                      ? "bg-teal text-white shadow-sm"
                      : "bg-sand/60 text-charcoal-light hover:bg-sand hover:text-charcoal"
                  }`}
                >
                  {cat.label}
                </button>
              ))}
            </motion.div>
          </motion.div>
        </div>
      </section>

      {/* Blog Posts Grid */}
      <section className="pb-20 lg:pb-28">
        <div className="container">
          {isLoading ? (
            <div className="max-w-4xl mx-auto grid md:grid-cols-2 gap-6">
              {[1, 2, 3, 4].map((i) => (
                <div key={i} className="bg-white rounded-2xl p-6 shadow-sm border border-sand-dark/20 animate-pulse">
                  <div className="h-40 bg-sand/60 rounded-xl mb-4" />
                  <div className="h-4 bg-sand/60 rounded w-1/4 mb-3" />
                  <div className="h-6 bg-sand/60 rounded w-3/4 mb-3" />
                  <div className="h-4 bg-sand/60 rounded w-full mb-2" />
                  <div className="h-4 bg-sand/60 rounded w-2/3" />
                </div>
              ))}
            </div>
          ) : filteredPosts.length === 0 ? (
            <motion.div
              className="max-w-md mx-auto text-center py-16"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
            >
              <BookOpen className="w-12 h-12 text-sand-dark/40 mx-auto mb-4" />
              <h3 className="text-xl text-charcoal mb-2 font-semibold">
                {t("blog.noPosts")}
              </h3>
              <p className="text-charcoal-light">
                {t("blog.noPostsDesc")}
              </p>
            </motion.div>
          ) : (
            <motion.div
              className="max-w-4xl mx-auto grid md:grid-cols-2 gap-6"
              initial="hidden"
              whileInView="visible"
              viewport={{ once: true }}
              variants={stagger}
            >
              {filteredPosts.map((post) => {
                const title = language === "nl" && post.titleNl ? post.titleNl : post.title;
                const excerpt = language === "nl" && post.excerptNl ? post.excerptNl : post.excerpt;

                return (
                  <motion.div key={post.id} variants={fadeUp}>
                    <Link href={`/blog/${post.slug}`}>
                      <div className="bg-white rounded-2xl overflow-hidden shadow-sm border border-sand-dark/20 hover:shadow-md transition-all duration-300 cursor-pointer group h-full flex flex-col">
                        {post.coverImage && (
                          <div className="h-48 overflow-hidden">
                            <img
                              src={post.coverImage}
                              alt={title}
                              className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
                            />
                          </div>
                        )}
                        <div className="p-6 flex flex-col flex-1">
                          <div className="flex items-center gap-3 mb-3">
                            <span className={`px-3 py-1 rounded-full text-xs font-medium ${categoryColors[post.category] || "bg-sand text-charcoal"}`}>
                              {t(`blog.cat${post.category.charAt(0).toUpperCase() + post.category.slice(1)}`)}
                            </span>
                            <span className="flex items-center gap-1 text-xs text-charcoal-light">
                              <Clock className="w-3 h-3" />
                              {post.readTimeMinutes} min
                            </span>
                          </div>
                          <h3 className="text-lg font-semibold text-charcoal mb-2 group-hover:text-teal transition-colors line-clamp-2">
                            {title}
                          </h3>
                          <p className="text-sm text-charcoal-light leading-relaxed flex-1 line-clamp-3">
                            {excerpt}
                          </p>
                          <div className="flex items-center justify-between mt-4 pt-4 border-t border-sand">
                            <span className="flex items-center gap-1.5 text-xs text-charcoal-light">
                              <Calendar className="w-3 h-3" />
                              {formatDate(post.publishedAt)}
                            </span>
                            <span className="flex items-center gap-1 text-sm font-medium text-teal group-hover:gap-2 transition-all">
                              {t("blog.readMore")}
                              <ArrowRight className="w-4 h-4" />
                            </span>
                          </div>
                        </div>
                      </div>
                    </Link>
                  </motion.div>
                );
              })}
            </motion.div>
          )}
        </div>
      </section>

      <Footer />
    </div>
  );
}
