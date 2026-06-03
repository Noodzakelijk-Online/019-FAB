/*
 * FAB Website — "Nordic Clarity" Design
 * Scandinavian Minimalism meets Healthcare Trust
 * Palette: Deep Teal, Warm Sand, Soft Sage, Charcoal on Warm White
 * Typography: DM Serif Display (display) + DM Sans (body)
 */

import { useState } from "react";
import { motion } from "framer-motion";
import {
  ArrowRight,
  Brain,
  Building2,
  Clock,
  FileText,
  Globe,
  Heart,
  Landmark,
  Link2,
  Loader2,
  Lock,
  Mail,
  MessageSquare,
  RefreshCw,
  Shield,
  Smartphone,
  Sparkles,
  TrendingUp,
  Wallet,
  Zap,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import WaitlistModal from "@/components/WaitlistModal";
import { Link } from "wouter";
import { useLanguage } from "@/contexts/LanguageContext";
import { useAuth } from "@/_core/hooks/useAuth";
import { getLoginUrl } from "@/const";
import { trpc } from "@/lib/trpc";
import { toast } from "sonner";

const fadeUp = {
  hidden: { opacity: 0, y: 30 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.7, ease: [0.25, 0.1, 0.25, 1] as const } },
};

const stagger = {
  visible: { transition: { staggerChildren: 0.12 } },
};

export default function Home() {
  const { t } = useLanguage();
  const [waitlistOpen, setWaitlistOpen] = useState(false);
  const { user, isAuthenticated } = useAuth();
  const [checkoutLoading, setCheckoutLoading] = useState(false);

  const createCheckout = trpc.stripe.createCheckout.useMutation({
    onSuccess: (data) => {
      if (data.url) {
        window.location.href = data.url;
      }
    },
    onError: (error) => {
      setCheckoutLoading(false);
      toast.error(error.message || "Failed to create checkout session");
    },
  });

  const handleSubscribe = () => {
    if (!isAuthenticated) {
      // Redirect to login first, then come back
      window.location.href = getLoginUrl();
      return;
    }
    setCheckoutLoading(true);
    createCheckout.mutate({
      origin: window.location.origin,
      productKey: "payAsYouGo",
    });
  };

  return (
    <div className="min-h-screen bg-warm-white">
      <Navbar />

      {/* ═══════════════════════════════════════════════════════════════
          HERO SECTION — Asymmetric split layout
      ═══════════════════════════════════════════════════════════════ */}
      <section className="relative overflow-hidden pt-24 pb-16 lg:pt-32 lg:pb-24">
        <div className="container">
          <div className="grid lg:grid-cols-12 gap-8 lg:gap-12 items-center">
            {/* Left: Text */}
            <motion.div
              className="lg:col-span-7"
              initial="hidden"
              animate="visible"
              variants={stagger}
            >
              <motion.div variants={fadeUp} className="mb-4">
                <span className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-sage-light text-teal text-sm font-medium tracking-wide">
                  <Sparkles className="w-4 h-4" />
                  {t("hero.badge")}
                </span>
              </motion.div>
              <motion.h1
                variants={fadeUp}
                className="text-4xl sm:text-5xl lg:text-[3.5rem] xl:text-[4rem] leading-[1.1] tracking-tight text-charcoal mb-6"
              >
                {t("hero.title1")}{" "}
                <span className="text-teal">{t("hero.titleHighlight")}</span>{" "}
                {t("hero.title2")}
              </motion.h1>
              <motion.p
                variants={fadeUp}
                className="text-lg lg:text-xl text-charcoal-light max-w-xl mb-8 font-light leading-relaxed"
              >
                {t("hero.desc")}
              </motion.p>
              <motion.div variants={fadeUp} className="flex flex-wrap gap-4">
                <Button
                  size="lg"
                  className="bg-teal hover:bg-teal-light text-white px-8 py-6 text-base rounded-xl shadow-lg shadow-teal/20 transition-all duration-300 hover:shadow-xl hover:shadow-teal/30"
                  onClick={() => setWaitlistOpen(true)}
                >
                  {t("hero.cta1")}
                  <ArrowRight className="ml-2 w-5 h-5" />
                </Button>
                <Link href="/how-it-works">
                  <Button
                    variant="outline"
                    size="lg"
                    className="px-8 py-6 text-base rounded-xl border-2 border-teal/20 text-teal hover:bg-teal/5 transition-all duration-300"
                  >
                    {t("hero.cta2")}
                  </Button>
                </Link>
              </motion.div>
              <motion.div
                variants={fadeUp}
                className="mt-8 flex items-center gap-6 text-sm text-charcoal-light"
              >
                <span className="flex items-center gap-2">
                  <Clock className="w-4 h-4 text-sage" />
                  {t("hero.stat1")}
                </span>
                <span className="flex items-center gap-2">
                  <Shield className="w-4 h-4 text-sage" />
                  {t("hero.stat2")}
                </span>
                <span className="flex items-center gap-2">
                  <Smartphone className="w-4 h-4 text-sage" />
                  {t("hero.stat3")}
                </span>
              </motion.div>
            </motion.div>

            {/* Right: Hero Image */}
            <motion.div
              className="lg:col-span-5"
              initial={{ opacity: 0, x: 40 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.8, delay: 0.3 }}
            >
              <div className="relative">
                <div className="absolute -inset-4 bg-gradient-to-br from-sage-light/60 to-sand/60 rounded-3xl blur-2xl" />
                <img
                  src="https://d2xsxph8kpxj0f.cloudfront.net/90835377/YwJSkbpfC6SiQf3mXpKwi7/hero-main-LKzCci3qvPiXoyqxRayT8m.webp"
                  alt="FAB Financial Orchestration"
                  className="relative rounded-2xl shadow-2xl w-full"
                />
              </div>
            </motion.div>
          </div>
        </div>

        {/* Background organic shape */}
        <div className="absolute top-0 right-0 w-1/2 h-full -z-10 opacity-30">
          <svg viewBox="0 0 600 800" className="w-full h-full">
            <path
              d="M300,0 C450,100 600,200 550,400 C500,600 400,700 300,800 L600,800 L600,0 Z"
              fill="oklch(0.93 0.03 80)"
            />
          </svg>
        </div>
      </section>

      {/* ═══════════════════════════════════════════════════════════════
          PROBLEM SECTION — The Challenge
      ═══════════════════════════════════════════════════════════════ */}
      <section className="py-20 lg:py-28 bg-sand/40">
        <div className="container">
          <motion.div
            className="max-w-3xl mx-auto text-center mb-16"
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true, margin: "-100px" }}
            variants={stagger}
          >
            <motion.span
              variants={fadeUp}
              className="text-sage font-medium text-sm tracking-widest uppercase"
            >
              {t("problem.label")}
            </motion.span>
            <motion.h2
              variants={fadeUp}
              className="text-3xl lg:text-4xl text-charcoal mt-3 mb-6"
            >
              {t("problem.title")}
            </motion.h2>
            <motion.p
              variants={fadeUp}
              className="text-lg text-charcoal-light leading-relaxed"
            >
              {t("problem.desc")}
            </motion.p>
          </motion.div>

          <motion.div
            className="grid md:grid-cols-3 gap-6 lg:gap-8"
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true, margin: "-100px" }}
            variants={stagger}
          >
            {[
              {
                icon: FileText,
                titleKey: "problem.card1.title",
                descKey: "problem.card1.desc",
                statKey: "problem.card1.stat",
                statLabelKey: "problem.card1.statLabel",
              },
              {
                icon: Clock,
                titleKey: "problem.card2.title",
                descKey: "problem.card2.desc",
                statKey: "problem.card2.stat",
                statLabelKey: "problem.card2.statLabel",
              },
              {
                icon: Heart,
                titleKey: "problem.card3.title",
                descKey: "problem.card3.desc",
                statKey: "problem.card3.stat",
                statLabelKey: "problem.card3.statLabel",
              },
            ].map((item, i) => (
              <motion.div
                key={i}
                variants={fadeUp}
                className="bg-white rounded-2xl p-8 shadow-sm border border-sand-dark/20 hover:shadow-md transition-shadow duration-300"
              >
                <div className="w-12 h-12 rounded-xl bg-sand flex items-center justify-center mb-5">
                  <item.icon className="w-6 h-6 text-teal" />
                </div>
                <h3 className="text-xl text-charcoal mb-3 font-sans font-semibold">
                  {t(item.titleKey)}
                </h3>
                <p className="text-charcoal-light leading-relaxed mb-5">
                  {t(item.descKey)}
                </p>
                <div className="pt-4 border-t border-sand">
                  <span className="text-3xl font-serif text-teal">
                    {t(item.statKey)}
                  </span>
                  <span className="text-sm text-charcoal-light ml-2">
                    {t(item.statLabelKey)}
                  </span>
                </div>
              </motion.div>
            ))}
          </motion.div>
        </div>
      </section>

      {/* ═══════════════════════════════════════════════════════════════
          HOW IT WORKS — Step-by-step
      ═══════════════════════════════════════════════════════════════ */}
      <section className="py-20 lg:py-28" id="how-it-works">
        <div className="container">
          <motion.div
            className="max-w-3xl mb-16"
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true, margin: "-100px" }}
            variants={stagger}
          >
            <motion.span
              variants={fadeUp}
              className="text-sage font-medium text-sm tracking-widest uppercase"
            >
              {t("hiw.label")}
            </motion.span>
            <motion.h2
              variants={fadeUp}
              className="text-3xl lg:text-4xl text-charcoal mt-3 mb-6"
            >
              {t("hiw.title")}
            </motion.h2>
            <motion.p
              variants={fadeUp}
              className="text-lg text-charcoal-light leading-relaxed"
            >
              {t("hiw.desc")}
            </motion.p>
          </motion.div>

          <motion.div
            className="grid lg:grid-cols-4 gap-8"
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true, margin: "-100px" }}
            variants={stagger}
          >
            {[
              {
                step: "01",
                titleKey: "hiw.step1.title",
                descKey: "hiw.step1.desc",
                icon: Globe,
                color: "bg-teal",
              },
              {
                step: "02",
                titleKey: "hiw.step2.title",
                descKey: "hiw.step2.desc",
                icon: Brain,
                color: "bg-sage",
              },
              {
                step: "03",
                titleKey: "hiw.step3.title",
                descKey: "hiw.step3.desc",
                icon: RefreshCw,
                color: "bg-teal-light",
              },
              {
                step: "04",
                titleKey: "hiw.step4.title",
                descKey: "hiw.step4.desc",
                icon: Sparkles,
                color: "bg-sage",
              },
            ].map((item, i) => (
              <motion.div key={i} variants={fadeUp} className="relative group">
                <div className="mb-6">
                  <span className="text-6xl font-serif text-sand-dark/40 group-hover:text-teal/30 transition-colors duration-500">
                    {item.step}
                  </span>
                </div>
                <div
                  className={`w-12 h-12 rounded-xl ${item.color} flex items-center justify-center mb-4`}
                >
                  <item.icon className="w-6 h-6 text-white" />
                </div>
                <h3 className="text-xl text-charcoal mb-3 font-sans font-semibold">
                  {t(item.titleKey)}
                </h3>
                <p className="text-charcoal-light leading-relaxed">
                  {t(item.descKey)}
                </p>
                {i < 3 && (
                  <div className="hidden lg:block absolute top-8 right-0 translate-x-1/2">
                    <ArrowRight className="w-5 h-5 text-sand-dark/40" />
                  </div>
                )}
              </motion.div>
            ))}
          </motion.div>

          {/* Link to detailed How It Works page */}
          <motion.div
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true }}
            variants={fadeUp}
            className="mt-12 text-center"
          >
            <Link href="/how-it-works">
              <Button
                variant="outline"
                className="rounded-xl border-teal/20 text-teal hover:bg-teal/5 px-8 py-5"
              >
                {t("hero.cta2")}
                <ArrowRight className="ml-2 w-4 h-4" />
              </Button>
            </Link>
          </motion.div>
        </div>
      </section>

      {/* ═══════════════════════════════════════════════════════════════
          INTEGRATIONS — Connected Platforms
      ═══════════════════════════════════════════════════════════════ */}
      <section className="py-20 lg:py-28 bg-white" id="integrations">
        <div className="container">
          <motion.div
            className="max-w-3xl mx-auto text-center mb-16"
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true, margin: "-100px" }}
            variants={stagger}
          >
            <motion.span
              variants={fadeUp}
              className="text-sage font-medium text-sm tracking-widest uppercase"
            >
              {t("integrations.label")}
            </motion.span>
            <motion.h2
              variants={fadeUp}
              className="text-3xl lg:text-4xl text-charcoal mt-3 mb-6"
            >
              {t("integrations.title")}
            </motion.h2>
            <motion.p
              variants={fadeUp}
              className="text-lg text-charcoal-light leading-relaxed"
            >
              {t("integrations.desc")}
            </motion.p>
          </motion.div>

          {/* Orchestration Diagram */}
          <motion.div
            className="mb-16"
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true, margin: "-100px" }}
            variants={fadeUp}
          >
            <div className="relative max-w-4xl mx-auto">
              <div className="absolute -inset-4 bg-gradient-to-br from-teal/5 to-sage-light/20 rounded-3xl blur-xl" />
              <img
                src="https://d2xsxph8kpxj0f.cloudfront.net/90835377/YwJSkbpfC6SiQf3mXpKwi7/integration-orchestration-hero-NvugbGx6rssPtHPRGuHTDT.webp"
                alt="FAB Orchestration — connecting all your financial platforms"
                className="relative rounded-2xl shadow-lg w-full"
              />
            </div>
          </motion.div>

          {/* Platform Cards */}
          <motion.div
            className="grid sm:grid-cols-2 lg:grid-cols-3 gap-6"
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true, margin: "-100px" }}
            variants={stagger}
          >
            {[
              {
                icon: Globe,
                name: "MijnGeldzaken.nl",
                titleKey: "integrations.mgz.title",
                descKey: "integrations.mgz.desc",
                color: "bg-purple-50 text-purple-600",
                borderColor: "hover:border-purple-200",
                tag: "integrations.mgz.tag",
              },
              {
                icon: Building2,
                name: "Wave Apps",
                titleKey: "integrations.wave.title",
                descKey: "integrations.wave.desc",
                color: "bg-cyan-50 text-cyan-600",
                borderColor: "hover:border-cyan-200",
                tag: "integrations.wave.tag",
              },
              {
                icon: Landmark,
                name: "Dutch Banks",
                titleKey: "integrations.banks.title",
                descKey: "integrations.banks.desc",
                color: "bg-amber-50 text-amber-600",
                borderColor: "hover:border-amber-200",
                tag: "integrations.banks.tag",
              },
              {
                icon: Wallet,
                name: "SVB",
                titleKey: "integrations.svb.title",
                descKey: "integrations.svb.desc",
                color: "bg-orange-50 text-orange-600",
                borderColor: "hover:border-orange-200",
                tag: "integrations.svb.tag",
              },
              {
                icon: Mail,
                name: "Gmail & Drive",
                titleKey: "integrations.google.title",
                descKey: "integrations.google.desc",
                color: "bg-red-50 text-red-500",
                borderColor: "hover:border-red-200",
                tag: "integrations.google.tag",
              },
              {
                icon: Link2,
                name: "More Coming",
                titleKey: "integrations.more.title",
                descKey: "integrations.more.desc",
                color: "bg-teal/10 text-teal",
                borderColor: "hover:border-teal/30",
                tag: "integrations.more.tag",
              },
            ].map((platform, i) => (
              <motion.div
                key={i}
                variants={fadeUp}
                className={`bg-white rounded-2xl p-7 border border-sand-dark/10 ${platform.borderColor} hover:shadow-lg transition-all duration-300 group`}
              >
                <div className="flex items-start justify-between mb-4">
                  <div className={`w-12 h-12 rounded-xl ${platform.color} flex items-center justify-center`}>
                    <platform.icon className="w-6 h-6" />
                  </div>
                  <span className="text-xs font-medium text-charcoal-light bg-sand/60 px-3 py-1 rounded-full">
                    {t(platform.tag)}
                  </span>
                </div>
                <h4 className="font-sans font-semibold text-charcoal text-lg mb-2">
                  {t(platform.titleKey)}
                </h4>
                <p className="text-sm text-charcoal-light leading-relaxed">
                  {t(platform.descKey)}
                </p>
              </motion.div>
            ))}
          </motion.div>

          {/* Key differentiator callout */}
          <motion.div
            className="mt-12 bg-gradient-to-r from-teal/5 to-sage-light/30 rounded-2xl p-8 lg:p-10 max-w-4xl mx-auto"
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true }}
            variants={fadeUp}
          >
            <div className="flex flex-col lg:flex-row items-start lg:items-center gap-6">
              <div className="w-14 h-14 rounded-2xl bg-teal flex items-center justify-center shrink-0">
                <RefreshCw className="w-7 h-7 text-white" />
              </div>
              <div>
                <h4 className="font-sans font-semibold text-charcoal text-lg mb-2">
                  {t("integrations.callout.title")}
                </h4>
                <p className="text-charcoal-light leading-relaxed">
                  {t("integrations.callout.desc")}
                </p>
              </div>
            </div>
          </motion.div>

          {/* Learn more link */}
          <motion.div
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true }}
            variants={fadeUp}
            className="mt-10 text-center"
          >
            <Link href="/how-it-works">
              <Button
                variant="outline"
                className="rounded-xl border-teal/20 text-teal hover:bg-teal/5 px-8 py-5"
              >
                {t("integrations.cta")}
                <ArrowRight className="ml-2 w-4 h-4" />
              </Button>
            </Link>
          </motion.div>
        </div>
      </section>

      {/* ═══════════════════════════════════════════════════════════════
          FEATURES — Alternating image/text blocks
      ═══════════════════════════════════════════════════════════════ */}
      <section className="py-20 lg:py-28 bg-sand/30" id="features">
        <div className="container">
          <motion.div
            className="max-w-3xl mx-auto text-center mb-20"
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true, margin: "-100px" }}
            variants={stagger}
          >
            <motion.span
              variants={fadeUp}
              className="text-sage font-medium text-sm tracking-widest uppercase"
            >
              {t("features.orch.label")}
            </motion.span>
            <motion.h2
              variants={fadeUp}
              className="text-3xl lg:text-4xl text-charcoal mt-3"
            >
              {t("features.orch.title")}
            </motion.h2>
          </motion.div>

          {/* Feature 1: Orchestration */}
          <motion.div
            className="grid lg:grid-cols-2 gap-12 lg:gap-16 items-center mb-24"
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true, margin: "-100px" }}
            variants={stagger}
          >
            <motion.div variants={fadeUp}>
              <div className="relative">
                <div className="absolute -inset-3 bg-teal/5 rounded-3xl" />
                <img
                  src="https://d2xsxph8kpxj0f.cloudfront.net/90835377/YwJSkbpfC6SiQf3mXpKwi7/feature-orchestration-E4csoetGoK6Em8j6ySY8w8.webp"
                  alt="Financial Orchestration"
                  className="relative rounded-2xl shadow-lg w-full"
                />
              </div>
            </motion.div>
            <motion.div variants={stagger}>
              <motion.span
                variants={fadeUp}
                className="text-sage font-medium text-sm tracking-widest uppercase"
              >
                {t("features.orch.label")}
              </motion.span>
              <motion.h3
                variants={fadeUp}
                className="text-2xl lg:text-3xl text-charcoal mt-3 mb-5"
              >
                {t("features.orch.title")}
              </motion.h3>
              <motion.p
                variants={fadeUp}
                className="text-charcoal-light leading-relaxed mb-6"
              >
                {t("features.orch.desc")}
              </motion.p>
              <motion.ul variants={stagger} className="space-y-3">
                {[
                  t("features.orch.item1"),
                  t("features.orch.item2"),
                  t("features.orch.item3"),
                  t("features.orch.item4"),
                ].map((item, i) => (
                  <motion.li
                    key={i}
                    variants={fadeUp}
                    className="flex items-start gap-3 text-charcoal-light"
                  >
                    <div className="w-5 h-5 rounded-full bg-sage-light flex items-center justify-center mt-0.5 shrink-0">
                      <div className="w-2 h-2 rounded-full bg-sage" />
                    </div>
                    {item}
                  </motion.li>
                ))}
              </motion.ul>
            </motion.div>
          </motion.div>

          {/* Feature 2: AI Processing (reversed) */}
          <motion.div
            className="grid lg:grid-cols-2 gap-12 lg:gap-16 items-center mb-24"
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true, margin: "-100px" }}
            variants={stagger}
          >
            <motion.div variants={stagger} className="order-2 lg:order-1">
              <motion.span
                variants={fadeUp}
                className="text-sage font-medium text-sm tracking-widest uppercase"
              >
                {t("features.ai.label")}
              </motion.span>
              <motion.h3
                variants={fadeUp}
                className="text-2xl lg:text-3xl text-charcoal mt-3 mb-5"
              >
                {t("features.ai.title")}
              </motion.h3>
              <motion.p
                variants={fadeUp}
                className="text-charcoal-light leading-relaxed mb-6"
              >
                {t("features.ai.desc")}
              </motion.p>
              <motion.ul variants={stagger} className="space-y-3">
                {[
                  t("features.ai.item1"),
                  t("features.ai.item2"),
                  t("features.ai.item3"),
                  t("features.ai.item4"),
                ].map((item, i) => (
                  <motion.li
                    key={i}
                    variants={fadeUp}
                    className="flex items-start gap-3 text-charcoal-light"
                  >
                    <div className="w-5 h-5 rounded-full bg-sage-light flex items-center justify-center mt-0.5 shrink-0">
                      <div className="w-2 h-2 rounded-full bg-teal" />
                    </div>
                    {item}
                  </motion.li>
                ))}
              </motion.ul>
            </motion.div>
            <motion.div variants={fadeUp} className="order-1 lg:order-2">
              <div className="relative">
                <div className="absolute -inset-3 bg-sage/5 rounded-3xl" />
                <img
                  src="https://d2xsxph8kpxj0f.cloudfront.net/90835377/YwJSkbpfC6SiQf3mXpKwi7/feature-ai-cFrymZgDZ4oLX3pUUkYX3b.webp"
                  alt="AI-Powered Processing"
                  className="relative rounded-2xl shadow-lg w-full"
                />
              </div>
            </motion.div>
          </motion.div>

          {/* Feature 3: Clarity */}
          <motion.div
            className="grid lg:grid-cols-2 gap-12 lg:gap-16 items-center"
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true, margin: "-100px" }}
            variants={stagger}
          >
            <motion.div variants={fadeUp}>
              <div className="relative">
                <div className="absolute -inset-3 bg-sand/60 rounded-3xl" />
                <img
                  src="https://d2xsxph8kpxj0f.cloudfront.net/90835377/YwJSkbpfC6SiQf3mXpKwi7/feature-clarity-kx9p3Xwu4yrN8jVDvQkrZ2.webp"
                  alt="Financial Clarity Dashboard"
                  className="relative rounded-2xl shadow-lg w-full"
                />
              </div>
            </motion.div>
            <motion.div variants={stagger}>
              <motion.span
                variants={fadeUp}
                className="text-sage font-medium text-sm tracking-widest uppercase"
              >
                {t("features.dash.label")}
              </motion.span>
              <motion.h3
                variants={fadeUp}
                className="text-2xl lg:text-3xl text-charcoal mt-3 mb-5"
              >
                {t("features.dash.title")}
              </motion.h3>
              <motion.p
                variants={fadeUp}
                className="text-charcoal-light leading-relaxed mb-6"
              >
                {t("features.dash.desc")}
              </motion.p>
              <motion.ul variants={stagger} className="space-y-3">
                {[
                  t("features.dash.item1"),
                  t("features.dash.item2"),
                  t("features.dash.item3"),
                  t("features.dash.item4"),
                ].map((item, i) => (
                  <motion.li
                    key={i}
                    variants={fadeUp}
                    className="flex items-start gap-3 text-charcoal-light"
                  >
                    <div className="w-5 h-5 rounded-full bg-sage-light flex items-center justify-center mt-0.5 shrink-0">
                      <div className="w-2 h-2 rounded-full bg-sage" />
                    </div>
                    {item}
                  </motion.li>
                ))}
              </motion.ul>
            </motion.div>
          </motion.div>
        </div>
      </section>

      {/* ═══════════════════════════════════════════════════════════════
          STATS SECTION — Key numbers
      ═══════════════════════════════════════════════════════════════ */}
      <section className="py-20 lg:py-24 bg-teal text-white">
        <div className="container">
          <motion.div
            className="grid sm:grid-cols-2 lg:grid-cols-4 gap-8 lg:gap-12"
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true, margin: "-100px" }}
            variants={stagger}
          >
            {[
              { value: "1M+", labelKey: "stats.users", subKey: "stats.usersSub" },
              { value: "€3.6B", labelKey: "stats.budget", subKey: "stats.budgetSub" },
              { value: "<10", labelKey: "stats.minutes", subKey: "stats.minutesSub" },
              { value: "80%", labelKey: "stats.saved", subKey: "stats.savedSub" },
            ].map((stat, i) => (
              <motion.div key={i} variants={fadeUp} className="text-center lg:text-left">
                <div className="text-4xl lg:text-5xl font-serif mb-2">
                  {stat.value}
                </div>
                <div className="text-white/90 font-medium mb-1">
                  {t(stat.labelKey)}
                </div>
                <div className="text-white/60 text-sm">{t(stat.subKey)}</div>
              </motion.div>
            ))}
          </motion.div>
        </div>
      </section>

      {/* ═══════════════════════════════════════════════════════════════
          TESTIMONIALS — Social Proof
      ═══════════════════════════════════════════════════════════════ */}
      <section className="py-20 lg:py-28 bg-sand/30">
        <div className="container">
          <motion.div
            className="max-w-3xl mx-auto text-center mb-16"
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true, margin: "-100px" }}
            variants={stagger}
          >
            <motion.span
              variants={fadeUp}
              className="text-sage font-medium text-sm tracking-widest uppercase"
            >
              {t("testimonials.label")}
            </motion.span>
            <motion.h2
              variants={fadeUp}
              className="text-3xl lg:text-4xl text-charcoal mt-3 mb-6"
            >
              {t("testimonials.title")}
            </motion.h2>
            <motion.p
              variants={fadeUp}
              className="text-lg text-charcoal-light leading-relaxed"
            >
              {t("testimonials.desc")}
            </motion.p>
          </motion.div>

          <motion.div
            className="grid md:grid-cols-2 gap-6 lg:gap-8 mb-16"
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true, margin: "-100px" }}
            variants={stagger}
          >
            {[
              { quoteKey: "testimonials.t1.quote", nameKey: "testimonials.t1.name", roleKey: "testimonials.t1.role", initials: "SM" },
              { quoteKey: "testimonials.t2.quote", nameKey: "testimonials.t2.name", roleKey: "testimonials.t2.role", initials: "TK" },
              { quoteKey: "testimonials.t3.quote", nameKey: "testimonials.t3.name", roleKey: "testimonials.t3.role", initials: "LD" },
              { quoteKey: "testimonials.t4.quote", nameKey: "testimonials.t4.name", roleKey: "testimonials.t4.role", initials: "MB" },
            ].map((item, i) => (
              <motion.div
                key={i}
                variants={fadeUp}
                className="bg-white rounded-2xl p-8 shadow-sm border border-sand-dark/20 hover:shadow-md transition-shadow duration-300 flex flex-col"
              >
                <div className="flex-1">
                  <svg className="w-8 h-8 text-sage/40 mb-4" fill="currentColor" viewBox="0 0 24 24">
                    <path d="M14.017 21v-7.391c0-5.704 3.731-9.57 8.983-10.609l.995 2.151c-2.432.917-3.995 3.638-3.995 5.849h4v10h-9.983zm-14.017 0v-7.391c0-5.704 3.731-9.57 8.983-10.609l.995 2.151c-2.432.917-3.995 3.638-3.995 5.849h4v10h-9.983z" />
                  </svg>
                  <p className="text-charcoal-light leading-relaxed italic">
                    "{t(item.quoteKey)}"
                  </p>
                </div>
                <div className="flex items-center gap-3 mt-6 pt-6 border-t border-sand">
                  <div className="w-10 h-10 rounded-full bg-teal/10 flex items-center justify-center">
                    <span className="text-sm font-semibold text-teal">{item.initials}</span>
                  </div>
                  <div>
                    <div className="font-semibold text-charcoal text-sm">{t(item.nameKey)}</div>
                    <div className="text-xs text-charcoal-light">{t(item.roleKey)}</div>
                  </div>
                </div>
              </motion.div>
            ))}
          </motion.div>

          {/* Trust Badges */}
          <motion.div
            className="flex flex-wrap justify-center gap-4 lg:gap-6"
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true }}
            variants={stagger}
          >
            {[
              { icon: Shield, labelKey: "testimonials.trustBadge1" },
              { icon: Lock, labelKey: "testimonials.trustBadge2" },
              { icon: Globe, labelKey: "testimonials.trustBadge3" },
              { icon: Heart, labelKey: "testimonials.trustBadge4" },
            ].map((badge, i) => (
              <motion.div
                key={i}
                variants={fadeUp}
                className="flex items-center gap-2 px-5 py-2.5 rounded-full bg-white border border-sand-dark/20 shadow-sm"
              >
                <badge.icon className="w-4 h-4 text-teal" />
                <span className="text-sm font-medium text-charcoal">{t(badge.labelKey)}</span>
              </motion.div>
            ))}
          </motion.div>
        </div>
      </section>

      {/* ═══════════════════════════════════════════════════════════════
          SECURITY & PRIVACY
      ═══════════════════════════════════════════════════════════════ */}
      <section className="py-20 lg:py-28" id="security">
        <div className="container">
          <motion.div
            className="grid lg:grid-cols-2 gap-12 lg:gap-16 items-center"
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true, margin: "-100px" }}
            variants={stagger}
          >
            <motion.div variants={stagger}>
              <motion.span
                variants={fadeUp}
                className="text-sage font-medium text-sm tracking-widest uppercase"
              >
                {t("security.label")}
              </motion.span>
              <motion.h2
                variants={fadeUp}
                className="text-3xl lg:text-4xl text-charcoal mt-3 mb-6"
              >
                {t("security.title")}
              </motion.h2>
              <motion.p
                variants={fadeUp}
                className="text-lg text-charcoal-light leading-relaxed mb-8"
              >
                {t("security.desc")}
              </motion.p>
              <motion.div variants={stagger} className="grid sm:grid-cols-2 gap-4">
                {[
                  { icon: Lock, titleKey: "security.e2e", descKey: "security.e2eDesc" },
                  { icon: Shield, titleKey: "security.gdpr", descKey: "security.gdprDesc" },
                  { icon: Smartphone, titleKey: "security.bio", descKey: "security.bioDesc" },
                  { icon: FileText, titleKey: "security.export", descKey: "security.exportDesc" },
                ].map((item, i) => (
                  <motion.div
                    key={i}
                    variants={fadeUp}
                    className="flex items-start gap-3 p-4 rounded-xl bg-sand/40"
                  >
                    <item.icon className="w-5 h-5 text-teal mt-0.5 shrink-0" />
                    <div>
                      <div className="font-medium text-charcoal text-sm">
                        {t(item.titleKey)}
                      </div>
                      <div className="text-xs text-charcoal-light mt-0.5">
                        {t(item.descKey)}
                      </div>
                    </div>
                  </motion.div>
                ))}
              </motion.div>
            </motion.div>
            <motion.div variants={fadeUp}>
              <div className="bg-gradient-to-br from-teal/5 to-sage-light/40 rounded-3xl p-10 lg:p-14">
                <div className="space-y-6">
                  {[
                    { icon: Lock, textKey: "security.local" },
                    { icon: Shield, textKey: "security.2fa" },
                    { icon: Mail, textKey: "security.emailApproval" },
                    { icon: Globe, textKey: "security.offline" },
                    { icon: FileText, textKey: "security.gdprExport" },
                    { icon: Heart, textKey: "security.trusted" },
                  ].map((item, i) => (
                    <div key={i} className="flex items-center gap-4">
                      <div className="w-10 h-10 rounded-xl bg-white shadow-sm flex items-center justify-center shrink-0">
                        <item.icon className="w-5 h-5 text-teal" />
                      </div>
                      <span className="text-charcoal">{t(item.textKey)}</span>
                    </div>
                  ))}
                </div>
              </div>
            </motion.div>
          </motion.div>
        </div>
      </section>

      {/* ═══════════════════════════════════════════════════════════════
          PRICING
      ═══════════════════════════════════════════════════════════════ */}
      <section className="py-20 lg:py-28 bg-sand/30" id="pricing">
        <div className="container">
          <motion.div
            className="max-w-3xl mx-auto text-center mb-16"
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true, margin: "-100px" }}
            variants={stagger}
          >
            <motion.span
              variants={fadeUp}
              className="text-sage font-medium text-sm tracking-widest uppercase"
            >
              {t("pricing.label")}
            </motion.span>
            <motion.h2
              variants={fadeUp}
              className="text-3xl lg:text-4xl text-charcoal mt-3 mb-6"
            >
              {t("pricing.title")}
            </motion.h2>
            <motion.p
              variants={fadeUp}
              className="text-lg text-charcoal-light leading-relaxed"
            >
              {t("pricing.desc")}
            </motion.p>
          </motion.div>

          <motion.div
            className="max-w-4xl mx-auto grid md:grid-cols-2 gap-8"
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true, margin: "-100px" }}
            variants={stagger}
          >
            {/* Free Tier */}
            <motion.div
              variants={fadeUp}
              className="bg-white rounded-2xl p-8 lg:p-10 shadow-sm border border-sand-dark/20"
            >
              <div className="text-sage font-medium text-sm tracking-widest uppercase mb-2">
                {t("pricing.free.label")}
              </div>
              <div className="flex items-baseline gap-1 mb-2">
                <span className="text-4xl font-serif text-charcoal">{t("pricing.free.price")}</span>
                <span className="text-charcoal-light">{t("pricing.free.period")}</span>
              </div>
              <p className="text-charcoal-light text-sm mb-8">
                {t("pricing.free.desc")}
              </p>
              <ul className="space-y-3 mb-8">
                {[
                  t("pricing.free.item1"),
                  t("pricing.free.item2"),
                  t("pricing.free.item3"),
                  t("pricing.free.item4"),
                  t("pricing.free.item5"),
                ].map((item, i) => (
                  <li key={i} className="flex items-center gap-3 text-sm text-charcoal-light">
                    <div className="w-4 h-4 rounded-full bg-sage-light flex items-center justify-center shrink-0">
                      <div className="w-1.5 h-1.5 rounded-full bg-sage" />
                    </div>
                    {item}
                  </li>
                ))}
              </ul>
              <Button
                variant="outline"
                className="w-full py-5 rounded-xl border-2 border-teal/20 text-teal hover:bg-teal/5"
                onClick={() => setWaitlistOpen(true)}
              >
                {t("pricing.free.cta")}
              </Button>
            </motion.div>

            {/* Pay As You Go */}
            <motion.div
              variants={fadeUp}
              className="bg-teal rounded-2xl p-8 lg:p-10 shadow-lg text-white relative overflow-hidden"
            >
              <div className="absolute top-0 right-0 w-32 h-32 bg-white/5 rounded-full -translate-y-1/2 translate-x-1/2" />
              <div className="relative">
                <div className="text-white/80 font-medium text-sm tracking-widest uppercase mb-2">
                  {t("pricing.payg.label")}
                </div>
                <div className="flex items-baseline gap-1 mb-2">
                  <span className="text-4xl font-serif">{t("pricing.payg.formula")}</span>
                </div>
                <p className="text-white/70 text-sm mb-8">
                  {t("pricing.payg.desc")}
                </p>
                <ul className="space-y-3 mb-8">
                  {[
                    t("pricing.payg.item1"),
                    t("pricing.payg.item2"),
                    t("pricing.payg.item3"),
                    t("pricing.payg.item4"),
                    t("pricing.payg.item5"),
                    t("pricing.payg.item6"),
                    t("pricing.payg.item7"),
                  ].map((item, i) => (
                    <li key={i} className="flex items-center gap-3 text-sm text-white/90">
                      <div className="w-4 h-4 rounded-full bg-white/20 flex items-center justify-center shrink-0">
                        <div className="w-1.5 h-1.5 rounded-full bg-white" />
                      </div>
                      {item}
                    </li>
                  ))}
                </ul>
                <Button
                  className="w-full py-5 rounded-xl bg-white text-teal hover:bg-white/90 font-semibold"
                  onClick={handleSubscribe}
                  disabled={checkoutLoading}
                >
                  {checkoutLoading ? (
                    <Loader2 className="w-4 h-4 animate-spin mr-2" />
                  ) : null}
                  {t("pricing.payg.cta")}
                  {!checkoutLoading && <ArrowRight className="ml-2 w-4 h-4" />}
                </Button>
              </div>
            </motion.div>
          </motion.div>
        </div>
      </section>

      {/* ═══════════════════════════════════════════════════════════════
          SOCIAL IMPACT
      ═══════════════════════════════════════════════════════════════ */}
      <section className="py-20 lg:py-28 relative overflow-hidden" id="impact">
        <div className="container relative z-10">
          <motion.div
            className="grid lg:grid-cols-2 gap-12 lg:gap-16 items-center"
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true, margin: "-100px" }}
            variants={stagger}
          >
            <motion.div variants={stagger}>
              <motion.span
                variants={fadeUp}
                className="text-sage font-medium text-sm tracking-widest uppercase"
              >
                {t("impact.label")}
              </motion.span>
              <motion.h2
                variants={fadeUp}
                className="text-3xl lg:text-4xl text-charcoal mt-3 mb-6"
              >
                {t("impact.title")}
              </motion.h2>
              <motion.p
                variants={fadeUp}
                className="text-lg text-charcoal-light leading-relaxed mb-8"
              >
                {t("impact.desc")}
              </motion.p>
              <motion.div variants={stagger} className="grid sm:grid-cols-2 gap-6">
                {[
                  { icon: Heart, titleKey: "impact.card1.title", descKey: "impact.card1.desc" },
                  { icon: TrendingUp, titleKey: "impact.card2.title", descKey: "impact.card2.desc" },
                  { icon: MessageSquare, titleKey: "impact.card3.title", descKey: "impact.card3.desc" },
                  { icon: Zap, titleKey: "impact.card4.title", descKey: "impact.card4.desc" },
                ].map((item, i) => (
                  <motion.div key={i} variants={fadeUp}>
                    <item.icon className="w-6 h-6 text-teal mb-3" />
                    <h4 className="font-sans font-semibold text-charcoal mb-1">
                      {t(item.titleKey)}
                    </h4>
                    <p className="text-sm text-charcoal-light leading-relaxed">
                      {t(item.descKey)}
                    </p>
                  </motion.div>
                ))}
              </motion.div>
            </motion.div>
            <motion.div variants={fadeUp}>
              <div className="relative">
                <div className="absolute -inset-4 bg-gradient-to-br from-sage-light/40 to-sand/40 rounded-3xl blur-xl" />
                <img
                  src="https://d2xsxph8kpxj0f.cloudfront.net/90835377/YwJSkbpfC6SiQf3mXpKwi7/hero-social-impact-bE9Nec35Jz367zvEZ2YppA.webp"
                  alt="Social Impact"
                  className="relative rounded-2xl shadow-xl w-full"
                />
              </div>
            </motion.div>
          </motion.div>
        </div>
      </section>

      {/* ═══════════════════════════════════════════════════════════════
          CTA SECTION
      ═══════════════════════════════════════════════════════════════ */}
      <section className="py-20 lg:py-28 bg-teal relative overflow-hidden">
        <div className="absolute inset-0 opacity-10">
          <svg className="w-full h-full" viewBox="0 0 1200 400">
            <circle cx="200" cy="200" r="300" fill="white" />
            <circle cx="1000" cy="100" r="200" fill="white" />
          </svg>
        </div>
        <div className="container relative z-10">
          <motion.div
            className="max-w-3xl mx-auto text-center"
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true, margin: "-100px" }}
            variants={stagger}
          >
            <motion.h2
              variants={fadeUp}
              className="text-3xl lg:text-5xl text-white mb-6"
            >
              {t("cta.title")}
            </motion.h2>
            <motion.p
              variants={fadeUp}
              className="text-xl text-white/80 mb-10 leading-relaxed"
            >
              {t("cta.desc")}
            </motion.p>
            <motion.div
              variants={fadeUp}
              className="flex flex-wrap justify-center gap-4"
            >
              <Button
                size="lg"
                className="bg-white text-teal hover:bg-white/90 px-10 py-6 text-base rounded-xl font-semibold shadow-lg"
                onClick={() => setWaitlistOpen(true)}
              >
                {t("cta.primary")}
                <ArrowRight className="ml-2 w-5 h-5" />
              </Button>
              <Link href="/contact">
                <Button
                  variant="outline"
                  size="lg"
                  className="border-2 border-white/30 text-white hover:bg-white/10 px-10 py-6 text-base rounded-xl"
                >
                  {t("cta.secondary")}
                </Button>
              </Link>
            </motion.div>
          </motion.div>
        </div>
      </section>

      <Footer />
      <WaitlistModal isOpen={waitlistOpen} onClose={() => setWaitlistOpen(false)} />
    </div>
  );
}
