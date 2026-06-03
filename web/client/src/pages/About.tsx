/**
 * FAB About Us Page — "Nordic Clarity" Design
 * Scandinavian Minimalism meets Healthcare Trust
 * Palette: Deep Teal, Warm Sand, Soft Sage, Charcoal on Warm White
 * Typography: DM Serif Display (display) + DM Sans (body)
 */

import { useState } from "react";
import { motion } from "framer-motion";
import {
  ArrowRight,
  Brain,
  Eye,
  Globe,
  Heart,
  Lightbulb,
  RefreshCw,
  Shield,
  Sparkles,
  Target,
  TrendingUp,
  Users,
  Zap,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import WaitlistModal from "@/components/WaitlistModal";
import { Link } from "wouter";
import { useLanguage } from "@/contexts/LanguageContext";

const fadeUp = {
  hidden: { opacity: 0, y: 30 },
  visible: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.7, ease: [0.25, 0.1, 0.25, 1] as const },
  },
};

const fadeIn = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { duration: 0.8, ease: [0.25, 0.1, 0.25, 1] as const },
  },
};

const stagger = {
  visible: { transition: { staggerChildren: 0.12 } },
};

const staggerSlow = {
  visible: { transition: { staggerChildren: 0.2 } },
};

export default function About() {
  const { t } = useLanguage();
  const [waitlistOpen, setWaitlistOpen] = useState(false);

  const missionPillars = [
    {
      icon: Zap,
      titleKey: "about.mission.pillar1.title",
      descKey: "about.mission.pillar1.desc",
    },
    {
      icon: RefreshCw,
      titleKey: "about.mission.pillar2.title",
      descKey: "about.mission.pillar2.desc",
    },
    {
      icon: Eye,
      titleKey: "about.mission.pillar3.title",
      descKey: "about.mission.pillar3.desc",
    },
  ];

  const differentiators = [
    {
      icon: Brain,
      titleKey: "about.different.item1.title",
      descKey: "about.different.item1.desc",
    },
    {
      icon: Shield,
      titleKey: "about.different.item2.title",
      descKey: "about.different.item2.desc",
    },
    {
      icon: Globe,
      titleKey: "about.different.item3.title",
      descKey: "about.different.item3.desc",
    },
    {
      icon: Users,
      titleKey: "about.different.item4.title",
      descKey: "about.different.item4.desc",
    },
  ];

  const values = [
    { number: "01", titleKey: "about.values.v1.title", descKey: "about.values.v1.desc" },
    { number: "02", titleKey: "about.values.v2.title", descKey: "about.values.v2.desc" },
    { number: "03", titleKey: "about.values.v3.title", descKey: "about.values.v3.desc" },
    { number: "04", titleKey: "about.values.v4.title", descKey: "about.values.v4.desc" },
  ];

  const impactStats = [
    { stat: "1M+", labelKey: "about.impact.stat1", detailKey: "about.impact.stat1Detail" },
    { stat: "€3.6B", labelKey: "about.impact.stat2", detailKey: "about.impact.stat2Detail" },
    { stat: "30%", labelKey: "about.impact.stat3", detailKey: "about.impact.stat3Detail" },
  ];

  return (
    <div className="min-h-screen bg-warm-white">
      <Navbar />

      {/* ═══════════════════════════════════════════════════════════════
          HERO — Our Story
      ═══════════════════════════════════════════════════════════════ */}
      <section className="relative overflow-hidden pt-28 pb-20 lg:pt-36 lg:pb-28">
        {/* Background image overlay */}
        <div className="absolute inset-0 z-0">
          <img
            src="https://d2xsxph8kpxj0f.cloudfront.net/90835377/YwJSkbpfC6SiQf3mXpKwi7/about-hero-7Q3MWdpKRnCREwzRjwCH4G.webp"
            alt=""
            className="w-full h-full object-cover opacity-15"
          />
          <div className="absolute inset-0 bg-gradient-to-b from-warm-white via-warm-white/80 to-warm-white" />
        </div>

        <div className="container relative z-10">
          <motion.div
            initial="hidden"
            animate="visible"
            variants={stagger}
            className="max-w-3xl"
          >
            <motion.div variants={fadeUp} className="mb-5">
              <span className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-sage-light text-teal text-sm font-medium tracking-wide">
                <Heart className="w-4 h-4" />
                {t("about.badge")}
              </span>
            </motion.div>
            <motion.h1
              variants={fadeUp}
              className="font-serif text-4xl sm:text-5xl lg:text-[3.5rem] leading-[1.1] tracking-tight text-charcoal mb-6"
            >
              {t("about.title1")}{" "}
              <span className="text-teal">{t("about.titleHighlight")}</span>,{" "}
              {t("about.title2")}
            </motion.h1>
            <motion.p
              variants={fadeUp}
              className="text-lg lg:text-xl text-charcoal-light max-w-2xl font-light leading-relaxed"
            >
              {t("about.hero.desc")}
            </motion.p>
          </motion.div>
        </div>
      </section>

      {/* ═══════════════════════════════════════════════════════════════
          THE PROBLEM WE LIVED
      ═══════════════════════════════════════════════════════════════ */}
      <section className="py-20 lg:py-28 bg-sand/30">
        <div className="container">
          <div className="grid lg:grid-cols-2 gap-12 lg:gap-20 items-center">
            <motion.div
              initial="hidden"
              whileInView="visible"
              viewport={{ once: true, margin: "-80px" }}
              variants={stagger}
            >
              <motion.h2
                variants={fadeUp}
                className="font-serif text-3xl sm:text-4xl text-charcoal mb-6 leading-tight"
              >
                {t("about.problem.title1")}{" "}
                <span className="text-teal">{t("about.problem.titleHighlight")}</span>
              </motion.h2>
              <motion.p
                variants={fadeUp}
                className="text-charcoal-light leading-relaxed mb-5"
              >
                {t("about.problem.p1")}
              </motion.p>
              <motion.p
                variants={fadeUp}
                className="text-charcoal-light leading-relaxed mb-5"
              >
                {t("about.problem.p2")}
              </motion.p>
              <motion.p
                variants={fadeUp}
                className="text-charcoal-light leading-relaxed"
              >
                {t("about.problem.p3pre")}{" "}
                <strong className="text-charcoal">
                  "{t("about.problem.p3quote")}"
                </strong>{" "}
                {t("about.problem.p3post")}
              </motion.p>
            </motion.div>

            <motion.div
              initial="hidden"
              whileInView="visible"
              viewport={{ once: true, margin: "-80px" }}
              variants={fadeIn}
              className="relative"
            >
              <img
                src="https://d2xsxph8kpxj0f.cloudfront.net/90835377/YwJSkbpfC6SiQf3mXpKwi7/about-timeline-6ty4ndGrvugZTRHmSMMZiE.webp"
                alt="From financial chaos to clarity"
                className="w-full rounded-2xl shadow-lg"
              />
              <div className="absolute -bottom-4 -left-4 w-24 h-24 bg-sage-light rounded-2xl -z-10" />
              <div className="absolute -top-4 -right-4 w-16 h-16 bg-sand rounded-xl -z-10" />
            </motion.div>
          </div>
        </div>
      </section>

      {/* ═══════════════════════════════════════════════════════════════
          OUR MISSION
      ═══════════════════════════════════════════════════════════════ */}
      <section className="py-20 lg:py-28">
        <div className="container">
          <motion.div
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true, margin: "-80px" }}
            variants={stagger}
            className="max-w-3xl mx-auto text-center mb-16"
          >
            <motion.div variants={fadeUp} className="mb-5">
              <span className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-sage-light text-teal text-sm font-medium tracking-wide">
                <Target className="w-4 h-4" />
                {t("about.mission.label")}
              </span>
            </motion.div>
            <motion.h2
              variants={fadeUp}
              className="font-serif text-3xl sm:text-4xl text-charcoal mb-6 leading-tight"
            >
              {t("about.mission.subtitle")}{" "}
              <span className="text-teal">{t("about.mission.subtitleHighlight")}</span>
            </motion.h2>
            <motion.p
              variants={fadeUp}
              className="text-charcoal-light text-lg leading-relaxed"
            >
              {t("about.mission.desc")}
            </motion.p>
          </motion.div>

          {/* Mission pillars */}
          <motion.div
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true, margin: "-80px" }}
            variants={staggerSlow}
            className="grid md:grid-cols-3 gap-8"
          >
            {missionPillars.map((pillar, i) => (
              <motion.div
                key={i}
                variants={fadeUp}
                className="group bg-white rounded-2xl p-8 border border-sand-dark/10 hover:border-teal/20 transition-all duration-300 hover:shadow-lg"
              >
                <div className="w-14 h-14 rounded-xl bg-sage-light flex items-center justify-center mb-6 group-hover:bg-teal/10 transition-colors duration-300">
                  <pillar.icon className="w-7 h-7 text-teal" />
                </div>
                <h3 className="font-serif text-xl text-charcoal mb-3">
                  {t(pillar.titleKey)}
                </h3>
                <p className="text-charcoal-light text-sm leading-relaxed">
                  {t(pillar.descKey)}
                </p>
              </motion.div>
            ))}
          </motion.div>
        </div>
      </section>

      {/* ═══════════════════════════════════════════════════════════════
          WHAT MAKES FAB DIFFERENT
      ═══════════════════════════════════════════════════════════════ */}
      <section className="py-20 lg:py-28 bg-charcoal text-white">
        <div className="container">
          <motion.div
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true, margin: "-80px" }}
            variants={stagger}
            className="max-w-3xl mx-auto text-center mb-16"
          >
            <motion.div variants={fadeUp} className="mb-5">
              <span className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-white/10 text-sage text-sm font-medium tracking-wide">
                <Sparkles className="w-4 h-4" />
                {t("about.different.label")}
              </span>
            </motion.div>
            <motion.h2
              variants={fadeUp}
              className="font-serif text-3xl sm:text-4xl text-white mb-6 leading-tight"
            >
              {t("about.different.subtitle")}{" "}
              <span className="text-sage">{t("about.different.subtitleHighlight")}</span>
            </motion.h2>
            <motion.p
              variants={fadeUp}
              className="text-white/70 text-lg leading-relaxed"
            >
              {t("about.different.desc")}
            </motion.p>
          </motion.div>

          <motion.div
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true, margin: "-80px" }}
            variants={staggerSlow}
            className="grid md:grid-cols-2 gap-6 max-w-4xl mx-auto"
          >
            {differentiators.map((item, i) => (
              <motion.div
                key={i}
                variants={fadeUp}
                className="bg-white/5 backdrop-blur-sm rounded-2xl p-8 border border-white/10 hover:border-sage/30 transition-all duration-300"
              >
                <div className="w-12 h-12 rounded-xl bg-teal/20 flex items-center justify-center mb-5">
                  <item.icon className="w-6 h-6 text-sage" />
                </div>
                <h3 className="font-serif text-xl text-white mb-3">
                  {t(item.titleKey)}
                </h3>
                <p className="text-white/60 text-sm leading-relaxed">
                  {t(item.descKey)}
                </p>
              </motion.div>
            ))}
          </motion.div>
        </div>
      </section>

      {/* ═══════════════════════════════════════════════════════════════
          OUR VALUES
      ═══════════════════════════════════════════════════════════════ */}
      <section className="py-20 lg:py-28">
        <div className="container">
          <motion.div
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true, margin: "-80px" }}
            variants={stagger}
            className="max-w-3xl mx-auto text-center mb-16"
          >
            <motion.div variants={fadeUp} className="mb-5">
              <span className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-sage-light text-teal text-sm font-medium tracking-wide">
                <Lightbulb className="w-4 h-4" />
                {t("about.values.label")}
              </span>
            </motion.div>
            <motion.h2
              variants={fadeUp}
              className="font-serif text-3xl sm:text-4xl text-charcoal mb-6 leading-tight"
            >
              {t("about.values.subtitle")}{" "}
              <span className="text-teal">{t("about.values.subtitleHighlight")}</span>{" "}
              {t("about.values.subtitleEnd")}
            </motion.h2>
          </motion.div>

          <motion.div
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true, margin: "-80px" }}
            variants={staggerSlow}
            className="grid sm:grid-cols-2 lg:grid-cols-4 gap-6"
          >
            {values.map((value, i) => (
              <motion.div
                key={i}
                variants={fadeUp}
                className="relative bg-white rounded-2xl p-7 border border-sand-dark/10 hover:border-teal/20 transition-all duration-300 hover:shadow-md"
              >
                <span className="font-serif text-5xl text-sage-light/60 absolute top-4 right-5 select-none">
                  {value.number}
                </span>
                <div className="relative z-10">
                  <h3 className="font-serif text-lg text-charcoal mb-3 mt-6">
                    {t(value.titleKey)}
                  </h3>
                  <p className="text-charcoal-light text-sm leading-relaxed">
                    {t(value.descKey)}
                  </p>
                </div>
              </motion.div>
            ))}
          </motion.div>
        </div>
      </section>

      {/* ═══════════════════════════════════════════════════════════════
          THE BIGGER PICTURE — Social Impact
      ═══════════════════════════════════════════════════════════════ */}
      <section className="py-20 lg:py-28 bg-sand/30">
        <div className="container">
          <div className="grid lg:grid-cols-2 gap-12 lg:gap-20 items-center">
            <motion.div
              initial="hidden"
              whileInView="visible"
              viewport={{ once: true, margin: "-80px" }}
              variants={stagger}
            >
              <motion.div variants={fadeUp} className="mb-5">
                <span className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-sage-light text-teal text-sm font-medium tracking-wide">
                  <TrendingUp className="w-4 h-4" />
                  {t("about.impact.biggerPicture")}
                </span>
              </motion.div>
              <motion.h2
                variants={fadeUp}
                className="font-serif text-3xl sm:text-4xl text-charcoal mb-6 leading-tight"
              >
                {t("about.impact.title1")}{" "}
                <span className="text-teal">{t("about.impact.titleHighlight")}</span>{" "}
                {t("about.impact.titleEnd")}
              </motion.h2>
              <motion.p
                variants={fadeUp}
                className="text-charcoal-light leading-relaxed mb-5"
              >
                {t("about.impact.p1")}
              </motion.p>
              <motion.p
                variants={fadeUp}
                className="text-charcoal-light leading-relaxed mb-5"
              >
                {t("about.impact.p2")}
              </motion.p>
              <motion.p
                variants={fadeUp}
                className="text-charcoal-light leading-relaxed"
              >
                {t("about.impact.p3")}
              </motion.p>
            </motion.div>

            <motion.div
              initial="hidden"
              whileInView="visible"
              viewport={{ once: true, margin: "-80px" }}
              variants={staggerSlow}
              className="space-y-6"
            >
              {impactStats.map((item, i) => (
                <motion.div
                  key={i}
                  variants={fadeUp}
                  className="bg-white rounded-2xl p-6 border border-sand-dark/10 flex gap-6 items-start"
                >
                  <div className="shrink-0">
                    <span className="font-serif text-3xl text-teal">
                      {item.stat}
                    </span>
                  </div>
                  <div>
                    <h4 className="font-sans font-semibold text-charcoal text-sm mb-1">
                      {t(item.labelKey)}
                    </h4>
                    <p className="text-charcoal-light text-sm leading-relaxed">
                      {t(item.detailKey)}
                    </p>
                  </div>
                </motion.div>
              ))}
            </motion.div>
          </div>
        </div>
      </section>

      {/* ═══════════════════════════════════════════════════════════════
          OUR VISION
      ═══════════════════════════════════════════════════════════════ */}
      <section className="py-20 lg:py-28">
        <div className="container">
          <motion.div
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true, margin: "-80px" }}
            variants={stagger}
            className="max-w-3xl mx-auto text-center"
          >
            <motion.div variants={fadeUp} className="mb-5">
              <span className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-sage-light text-teal text-sm font-medium tracking-wide">
                <Globe className="w-4 h-4" />
                {t("about.vision.label")}
              </span>
            </motion.div>
            <motion.h2
              variants={fadeUp}
              className="font-serif text-3xl sm:text-4xl text-charcoal mb-6 leading-tight"
            >
              {t("about.vision.title1")}{" "}
              <span className="text-teal">{t("about.vision.titleHighlight")}</span>{" "}
              {t("about.vision.titleEnd")}
            </motion.h2>
            <motion.p
              variants={fadeUp}
              className="text-charcoal-light text-lg leading-relaxed mb-5"
            >
              {t("about.vision.p1")}
            </motion.p>
            <motion.p
              variants={fadeUp}
              className="text-charcoal-light text-lg leading-relaxed mb-8"
            >
              {t("about.vision.p2")}
            </motion.p>
            <motion.div variants={fadeUp} className="flex flex-col sm:flex-row gap-4 justify-center">
              <Button
                size="lg"
                className="rounded-xl bg-teal hover:bg-teal-light text-white px-8 h-12 text-base"
                onClick={() => setWaitlistOpen(true)}
              >
                {t("about.cta.primary")}
                <ArrowRight className="w-4 h-4 ml-2" />
              </Button>
              <Link href="/contact">
                <Button
                  variant="outline"
                  size="lg"
                  className="rounded-xl border-teal/20 text-teal hover:bg-teal/5 px-8 h-12 text-base"
                >
                  {t("about.cta.secondary")}
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
