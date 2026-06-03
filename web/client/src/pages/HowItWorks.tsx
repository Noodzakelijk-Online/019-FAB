import {
  ArrowRight,
  Link2,
  Brain,
  Send,
  CheckCircle,
  Mail,
  FileText,
  MessageSquare,
  HardDrive,
  RefreshCw,
  Shield,
  Clock,
  Zap,
  ArrowDown,
  Smartphone,
  Globe,
  Building2,
  Landmark,
  Wallet,
} from "lucide-react";
import { useState } from "react";
import { motion } from "framer-motion";
import { Button } from "@/components/ui/button";
import { Link } from "wouter";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import WaitlistModal from "@/components/WaitlistModal";
import { useLanguage } from "@/contexts/LanguageContext";

const fadeUp = {
  hidden: { opacity: 0, y: 30 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.6, ease: [0, 0, 0.58, 1] as const } },
};

const stagger = {
  hidden: {},
  visible: { transition: { staggerChildren: 0.12 } },
};

export default function HowItWorks() {
  const { t } = useLanguage();
  const [waitlistOpen, setWaitlistOpen] = useState(false);

  return (
    <div className="min-h-screen bg-warm-white">
      <Navbar />

      {/* ═══════════════════════════════════════════════════════════════
          HERO
      ═══════════════════════════════════════════════════════════════ */}
      <section className="relative overflow-hidden pt-28 pb-16 lg:pt-36 lg:pb-20">
        <div className="absolute inset-0 z-0">
          <div className="absolute top-20 right-0 w-[500px] h-[500px] bg-sage-light/30 rounded-full blur-3xl" />
          <div className="absolute bottom-0 left-10 w-[400px] h-[400px] bg-sand/40 rounded-full blur-3xl" />
        </div>
        <div className="container relative z-10">
          <motion.div
            className="max-w-3xl mx-auto text-center"
            initial="hidden"
            animate="visible"
            variants={stagger}
          >
            <motion.div variants={fadeUp} className="mb-5">
              <span className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-sage-light text-teal text-sm font-medium tracking-wide">
                <Zap className="w-4 h-4" />
                {t("hiwPage.badge")}
              </span>
            </motion.div>
            <motion.h1
              variants={fadeUp}
              className="font-serif text-4xl sm:text-5xl lg:text-[3.25rem] leading-[1.1] tracking-tight text-charcoal mb-6"
            >
              {t("hiwPage.title1")}{" "}
              <span className="text-teal">{t("hiwPage.titleHighlight")}</span>
            </motion.h1>
            <motion.p
              variants={fadeUp}
              className="text-lg text-charcoal-light max-w-2xl mx-auto font-light leading-relaxed"
            >
              {t("hiwPage.desc")}
            </motion.p>
          </motion.div>
        </div>
      </section>

      {/* ═══════════════════════════════════════════════════════════════
          STEP 1: CONNECT YOUR SOURCES
      ═══════════════════════════════════════════════════════════════ */}
      <section className="py-16 lg:py-24">
        <div className="container">
          <motion.div
            className="flex items-center gap-4 mb-8"
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true, margin: "-80px" }}
            variants={fadeUp}
          >
            <div className="w-14 h-14 rounded-2xl bg-teal flex items-center justify-center text-white font-serif text-2xl shadow-lg">
              1
            </div>
            <div>
              <span className="text-teal font-medium text-sm tracking-widest uppercase font-sans">{t("hiwPage.stepOne")}</span>
              <h2 className="text-3xl lg:text-4xl text-charcoal">{t("hiwPage.step1.title")}</h2>
            </div>
          </motion.div>

          <motion.p
            className="text-lg text-charcoal-light leading-relaxed max-w-3xl mb-12 font-sans"
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true, margin: "-80px" }}
            variants={fadeUp}
          >
            {t("hiwPage.step1.desc")}
          </motion.p>

          {/* Source diagram */}
          <motion.div
            className="grid md:grid-cols-2 lg:grid-cols-3 gap-6"
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true, margin: "-80px" }}
            variants={stagger}
          >
            {[
              { icon: Mail, title: "Gmail", descKey: "hiwPage.step1.gmail", color: "bg-red-50 text-red-500" },
              { icon: MessageSquare, title: "WhatsApp", descKey: "hiwPage.step1.whatsapp", color: "bg-green-50 text-green-600" },
              { icon: HardDrive, title: "Google Drive", descKey: "hiwPage.step1.drive", color: "bg-blue-50 text-blue-500" },
              { icon: Landmark, title: "Bank Accounts", descKey: "hiwPage.step1.bank", color: "bg-amber-50 text-amber-600" },
              { icon: Globe, title: "mijngeldzaken.nl", descKey: "hiwPage.step1.mgz", color: "bg-purple-50 text-purple-500" },
              { icon: Building2, title: "WaveApps", descKey: "hiwPage.step1.wave", color: "bg-cyan-50 text-cyan-600" },
              { icon: Wallet, title: "SVB", descKey: "hiwPage.step1.svb", color: "bg-orange-50 text-orange-500" },
              { icon: Smartphone, title: "Cash", descKey: "hiwPage.step1.cash", color: "bg-teal/10 text-teal" },
            ].map((source, i) => (
              <motion.div
                key={i}
                variants={fadeUp}
                className="bg-white rounded-2xl p-6 border border-sand-dark/10 hover:border-teal/20 hover:shadow-md transition-all group"
              >
                <div className={`w-12 h-12 rounded-xl ${source.color} flex items-center justify-center mb-4`}>
                  <source.icon className="w-6 h-6" />
                </div>
                <h4 className="font-sans font-semibold text-charcoal mb-2">{source.title}</h4>
                <p className="text-sm text-charcoal-light leading-relaxed font-sans">{t(source.descKey)}</p>
              </motion.div>
            ))}
          </motion.div>

          {/* Connection security note */}
          <motion.div
            className="mt-8 flex items-start gap-3 bg-sage-light/30 rounded-xl p-5 max-w-2xl"
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true, margin: "-80px" }}
            variants={fadeUp}
          >
            <Shield className="w-5 h-5 text-sage shrink-0 mt-0.5" />
            <div>
              <p className="text-sm font-sans font-medium text-charcoal mb-1">{t("hiwPage.step1.secure")}</p>
              <p className="text-sm text-charcoal-light font-sans leading-relaxed">
                {t("hiwPage.step1.secureDesc")}
              </p>
            </div>
          </motion.div>
        </div>
      </section>

      {/* Arrow connector */}
      <motion.div
        className="flex justify-center py-4"
        initial={{ opacity: 0, scale: 0.5 }}
        whileInView={{ opacity: 1, scale: 1 }}
        viewport={{ once: true }}
        transition={{ duration: 0.4 }}
      >
        <div className="w-12 h-12 rounded-full bg-sand flex items-center justify-center">
          <ArrowDown className="w-5 h-5 text-charcoal-light" />
        </div>
      </motion.div>

      {/* ═══════════════════════════════════════════════════════════════
          STEP 2: AI EXTRACTS & CATEGORIZES
      ═══════════════════════════════════════════════════════════════ */}
      <section className="py-16 lg:py-24 bg-white">
        <div className="container">
          <motion.div
            className="flex items-center gap-4 mb-8"
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true, margin: "-80px" }}
            variants={fadeUp}
          >
            <div className="w-14 h-14 rounded-2xl bg-sage flex items-center justify-center text-white font-serif text-2xl shadow-lg">
              2
            </div>
            <div>
              <span className="text-sage font-medium text-sm tracking-widest uppercase font-sans">{t("hiwPage.stepTwo")}</span>
              <h2 className="text-3xl lg:text-4xl text-charcoal">{t("hiwPage.step2.title")}</h2>
            </div>
          </motion.div>

          <motion.p
            className="text-lg text-charcoal-light leading-relaxed max-w-3xl mb-12 font-sans"
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true, margin: "-80px" }}
            variants={fadeUp}
          >
            {t("hiwPage.step2.desc")}
          </motion.p>

          {/* AI Processing pipeline */}
          <div className="space-y-6">
            <motion.div
              className="grid lg:grid-cols-4 gap-4"
              initial="hidden"
              whileInView="visible"
              viewport={{ once: true, margin: "-80px" }}
              variants={stagger}
            >
              {[
                { icon: FileText, stepKey: "hiwPage.step2.scan", titleKey: "hiwPage.step2.scanTitle", descKey: "hiwPage.step2.scanDesc" },
                { icon: Brain, stepKey: "hiwPage.step2.classify", titleKey: "hiwPage.step2.classifyTitle", descKey: "hiwPage.step2.classifyDesc" },
                { icon: Link2, stepKey: "hiwPage.step2.map", titleKey: "hiwPage.step2.mapTitle", descKey: "hiwPage.step2.mapDesc" },
                { icon: CheckCircle, stepKey: "hiwPage.step2.score", titleKey: "hiwPage.step2.scoreTitle", descKey: "hiwPage.step2.scoreDesc" },
              ].map((item, i) => (
                <motion.div key={i} variants={fadeUp} className="relative bg-warm-white rounded-2xl p-6 border border-sand-dark/10">
                  <div className="absolute -top-3 left-6 bg-teal text-white text-xs font-sans font-semibold px-3 py-1 rounded-full">
                    {t(item.stepKey)}
                  </div>
                  <item.icon className="w-8 h-8 text-teal mt-2 mb-4" />
                  <h4 className="font-sans font-semibold text-charcoal mb-2">{t(item.titleKey)}</h4>
                  <p className="text-sm text-charcoal-light leading-relaxed font-sans">{t(item.descKey)}</p>
                  {i < 3 && (
                    <div className="hidden lg:block absolute top-1/2 -right-4 z-10">
                      <ArrowRight className="w-5 h-5 text-teal/40" />
                    </div>
                  )}
                </motion.div>
              ))}
            </motion.div>

            {/* What the AI extracts */}
            <motion.div
              className="bg-warm-white rounded-2xl p-8 border border-sand-dark/10"
              initial="hidden"
              whileInView="visible"
              viewport={{ once: true, margin: "-80px" }}
              variants={stagger}
            >
              <motion.h4 variants={fadeUp} className="font-sans font-semibold text-charcoal mb-4">{t("hiwPage.step2.extractTitle")}</motion.h4>
              <motion.div variants={stagger} className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
                {[
                  { labelKey: "hiwPage.step2.vendorName", exKey: "hiwPage.step2.vendorEx" },
                  { labelKey: "hiwPage.step2.amount", exKey: "hiwPage.step2.amountEx" },
                  { labelKey: "hiwPage.step2.date", exKey: "hiwPage.step2.dateEx" },
                  { labelKey: "hiwPage.step2.category", exKey: "hiwPage.step2.categoryEx" },
                  { labelKey: "hiwPage.step2.invoice", exKey: "hiwPage.step2.invoiceEx" },
                  { labelKey: "hiwPage.step2.payment", exKey: "hiwPage.step2.paymentEx" },
                  { labelKey: "hiwPage.step2.taxDeduct", exKey: "hiwPage.step2.taxDeductEx" },
                  { labelKey: "hiwPage.step2.earmarked", exKey: "hiwPage.step2.earmarkedEx" },
                ].map((item, i) => (
                  <motion.div key={i} variants={fadeUp} className="bg-white rounded-xl p-4 border border-sand-dark/10">
                    <p className="text-xs text-teal font-sans font-semibold uppercase tracking-wide mb-1">{t(item.labelKey)}</p>
                    <p className="text-sm text-charcoal-light font-sans">{t(item.exKey)}</p>
                  </motion.div>
                ))}
              </motion.div>
            </motion.div>
          </div>
        </div>
      </section>

      {/* Arrow connector */}
      <motion.div
        className="flex justify-center py-4"
        initial={{ opacity: 0, scale: 0.5 }}
        whileInView={{ opacity: 1, scale: 1 }}
        viewport={{ once: true }}
        transition={{ duration: 0.4 }}
      >
        <div className="w-12 h-12 rounded-full bg-sand flex items-center justify-center">
          <ArrowDown className="w-5 h-5 text-charcoal-light" />
        </div>
      </motion.div>

      {/* ═══════════════════════════════════════════════════════════════
          STEP 3: AUTO-ROUTE, COMPLETE & SYNC
      ═══════════════════════════════════════════════════════════════ */}
      <section className="py-16 lg:py-24">
        <div className="container">
          <motion.div
            className="flex items-center gap-4 mb-8"
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true, margin: "-80px" }}
            variants={fadeUp}
          >
            <div className="w-14 h-14 rounded-2xl bg-teal flex items-center justify-center text-white font-serif text-2xl shadow-lg">
              3
            </div>
            <div>
              <span className="text-teal font-medium text-sm tracking-widest uppercase font-sans">{t("hiwPage.stepThree")}</span>
              <h2 className="text-3xl lg:text-4xl text-charcoal">{t("hiwPage.step3.title")}</h2>
            </div>
          </motion.div>

          <motion.p
            className="text-lg text-charcoal-light leading-relaxed max-w-3xl mb-12 font-sans"
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true, margin: "-80px" }}
            variants={fadeUp}
          >
            {t("hiwPage.step3.desc")}
          </motion.p>

          <motion.div
            className="grid lg:grid-cols-2 gap-8"
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true, margin: "-80px" }}
            variants={stagger}
          >
            {/* Routing diagram */}
            <motion.div variants={fadeUp} className="bg-white rounded-2xl p-8 border border-sand-dark/10">
              <h4 className="font-sans font-semibold text-charcoal mb-6 flex items-center gap-2">
                <Send className="w-5 h-5 text-teal" />
                {t("hiwPage.step3.routing")}
              </h4>
              <div className="space-y-4">
                {[
                  { fromKey: "hiwPage.step3.r1from", toKey: "hiwPage.step3.r1to", color: "bg-purple-100 text-purple-600", toColor: "bg-purple-50" },
                  { fromKey: "hiwPage.step3.r2from", toKey: "hiwPage.step3.r2to", color: "bg-cyan-100 text-cyan-600", toColor: "bg-cyan-50" },
                  { fromKey: "hiwPage.step3.r3from", toKey: "hiwPage.step3.r3to", color: "bg-rose-100 text-rose-600", toColor: "bg-rose-50" },
                  { fromKey: "hiwPage.step3.r4from", toKey: "hiwPage.step3.r4to", color: "bg-orange-100 text-orange-600", toColor: "bg-orange-50" },
                ].map((route, i) => (
                  <div key={i} className="flex items-center gap-3">
                    <div className={`${route.color} text-xs font-sans font-semibold px-3 py-1.5 rounded-lg flex-1 text-center`}>
                      {t(route.fromKey)}
                    </div>
                    <ArrowRight className="w-4 h-4 text-charcoal-light shrink-0" />
                    <div className={`${route.toColor} text-xs font-sans font-medium px-3 py-1.5 rounded-lg flex-1 text-center text-charcoal`}>
                      {t(route.toKey)}
                    </div>
                  </div>
                ))}
              </div>
              <p className="text-xs text-charcoal-light font-sans mt-4 leading-relaxed">
                {t("hiwPage.step3.routingNote")}
              </p>
            </motion.div>

            {/* Autonomous Communication */}
            <motion.div variants={fadeUp} className="bg-white rounded-2xl p-8 border border-sand-dark/10">
              <h4 className="font-sans font-semibold text-charcoal mb-6 flex items-center gap-2">
                <Mail className="w-5 h-5 text-teal" />
                {t("hiwPage.step3.autoComplete")}
              </h4>
              <div className="space-y-5">
                {[
                  { step: "1", titleKey: "hiwPage.step3.ac1", descKey: "hiwPage.step3.ac1Desc" },
                  { step: "2", titleKey: "hiwPage.step3.ac2", descKey: "hiwPage.step3.ac2Desc" },
                  { step: "3", titleKey: "hiwPage.step3.ac3", descKey: "hiwPage.step3.ac3Desc" },
                  { step: "4", titleKey: "hiwPage.step3.ac4", descKey: "hiwPage.step3.ac4Desc" },
                  { step: "5", titleKey: "hiwPage.step3.ac5", descKey: "hiwPage.step3.ac5Desc" },
                  { step: "6", titleKey: "hiwPage.step3.ac6", descKey: "hiwPage.step3.ac6Desc" },
                ].map((item, i) => (
                  <div key={i} className="flex gap-3">
                    <div className="w-7 h-7 rounded-full bg-teal/10 text-teal text-xs font-sans font-bold flex items-center justify-center shrink-0 mt-0.5">
                      {item.step}
                    </div>
                    <div>
                      <p className="text-sm font-sans font-semibold text-charcoal">{t(item.titleKey)}</p>
                      <p className="text-xs text-charcoal-light font-sans leading-relaxed">{t(item.descKey)}</p>
                    </div>
                  </div>
                ))}
              </div>
            </motion.div>
          </motion.div>

          {/* Sync frequency */}
          <motion.div
            className="mt-8 bg-white rounded-2xl p-8 border border-sand-dark/10"
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true, margin: "-80px" }}
            variants={stagger}
          >
            <motion.h4 variants={fadeUp} className="font-sans font-semibold text-charcoal mb-4 flex items-center gap-2">
              <RefreshCw className="w-5 h-5 text-teal" />
              {t("hiwPage.step3.sync")}
            </motion.h4>
            <motion.p variants={fadeUp} className="text-sm text-charcoal-light font-sans leading-relaxed mb-6">
              {t("hiwPage.step3.syncDesc")}
            </motion.p>
            <motion.div variants={stagger} className="grid sm:grid-cols-3 gap-6">
              {[
                { titleKey: "hiwPage.step3.syncPlatform", freqKey: "hiwPage.step3.syncPlatformFreq", descKey: "hiwPage.step3.syncPlatformDesc", icon: RefreshCw, width: "50%" },
                { titleKey: "hiwPage.step3.syncSource", freqKey: "hiwPage.step3.syncSourceFreq", descKey: "hiwPage.step3.syncSourceDesc", icon: FileText, width: "50%" },
                { titleKey: "hiwPage.step3.syncData", freqKey: "hiwPage.step3.syncDataFreq", descKey: "hiwPage.step3.syncDataDesc", icon: Clock, width: "90%" },
              ].map((item, i) => (
                <motion.div key={i} variants={fadeUp} className="bg-warm-white rounded-xl p-5 border border-sand-dark/10">
                  <item.icon className="w-6 h-6 text-teal mb-3" />
                  <p className="font-sans font-semibold text-charcoal text-sm mb-1">{t(item.titleKey)}</p>
                  <p className="text-teal font-sans font-bold text-lg mb-2">{t(item.freqKey)}</p>
                  <p className="text-xs text-charcoal-light font-sans leading-relaxed">{t(item.descKey)}</p>
                  <div className="mt-3 h-1.5 bg-sand rounded-full overflow-hidden">
                    <div className="h-full bg-teal rounded-full" style={{ width: item.width }} />
                  </div>
                  <p className="text-xs text-charcoal-light/60 font-sans mt-1">{t("hiwPage.step3.adjustable")}</p>
                </motion.div>
              ))}
            </motion.div>
          </motion.div>
        </div>
      </section>

      {/* Arrow connector */}
      <motion.div
        className="flex justify-center py-4"
        initial={{ opacity: 0, scale: 0.5 }}
        whileInView={{ opacity: 1, scale: 1 }}
        viewport={{ once: true }}
        transition={{ duration: 0.4 }}
      >
        <div className="w-12 h-12 rounded-full bg-sand flex items-center justify-center">
          <ArrowDown className="w-5 h-5 text-charcoal-light" />
        </div>
      </motion.div>

      {/* ═══════════════════════════════════════════════════════════════
          STEP 4: REVIEW & RELAX
      ═══════════════════════════════════════════════════════════════ */}
      <section className="py-16 lg:py-24 bg-white">
        <div className="container">
          <motion.div
            className="flex items-center gap-4 mb-8"
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true, margin: "-80px" }}
            variants={fadeUp}
          >
            <div className="w-14 h-14 rounded-2xl bg-sage flex items-center justify-center text-white font-serif text-2xl shadow-lg">
              4
            </div>
            <div>
              <span className="text-sage font-medium text-sm tracking-widest uppercase font-sans">{t("hiwPage.stepFour")}</span>
              <h2 className="text-3xl lg:text-4xl text-charcoal">{t("hiwPage.step4.title")}</h2>
            </div>
          </motion.div>

          <motion.p
            className="text-lg text-charcoal-light leading-relaxed max-w-3xl mb-12 font-sans"
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true, margin: "-80px" }}
            variants={fadeUp}
          >
            {t("hiwPage.step4.desc")}
          </motion.p>

          <motion.div
            className="grid lg:grid-cols-3 gap-6"
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true, margin: "-80px" }}
            variants={stagger}
          >
            {/* Review queue */}
            <motion.div variants={fadeUp} className="lg:col-span-2 bg-warm-white rounded-2xl p-8 border border-sand-dark/10">
              <h4 className="font-sans font-semibold text-charcoal mb-6">{t("hiwPage.step4.queue")}</h4>
              <div className="space-y-3">
                {[
                  { vendor: t("hiwPage.step4.unknownVendor"), amount: "\u20AC23.50", uncertain: t("hiwPage.step4.vendorName"), confidence: 45, category: t("hiwPage.step4.healthcare") },
                  { vendor: "Apotheek De Gaper", amount: "\u20AC67.80", uncertain: t("hiwPage.step4.categoryLabel"), confidence: 62, category: t("hiwPage.step4.healthHousehold") },
                  { vendor: "Bol.com", amount: "\u20AC149.00", uncertain: t("hiwPage.step4.categoryLabel"), confidence: 55, category: t("hiwPage.step4.householdSide") },
                ].map((item, i) => (
                  <div key={i} className="bg-white rounded-xl p-4 border border-sand-dark/10 flex items-center justify-between gap-4">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <p className="font-sans font-semibold text-charcoal text-sm">{item.vendor}</p>
                        <span className="text-xs bg-amber-100 text-amber-700 px-2 py-0.5 rounded-full font-sans">
                          {item.uncertain}
                        </span>
                      </div>
                      <p className="text-xs text-charcoal-light font-sans">{item.category}</p>
                    </div>
                    <div className="text-right">
                      <p className="font-sans font-semibold text-charcoal">{item.amount}</p>
                      <div className="flex items-center gap-1 mt-1">
                        <div className="w-16 h-1.5 bg-sand rounded-full overflow-hidden">
                          <div className="h-full bg-amber-400 rounded-full" style={{ width: `${item.confidence}%` }} />
                        </div>
                        <span className="text-xs text-charcoal-light font-sans">{item.confidence}%</span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
              <p className="text-xs text-charcoal-light font-sans mt-4">
                {t("hiwPage.step4.queueNote")}
              </p>
            </motion.div>

            {/* Insights panel */}
            <motion.div variants={fadeUp} className="space-y-6">
              <div className="bg-teal rounded-2xl p-6 text-white">
                <p className="text-white/70 text-xs font-sans font-medium uppercase tracking-wide mb-3">{t("hiwPage.step4.summary")}</p>
                <div className="space-y-4">
                  <div>
                    <p className="text-2xl font-serif">47</p>
                    <p className="text-white/70 text-xs font-sans">{t("hiwPage.step4.autoProcessed")}</p>
                  </div>
                  <div>
                    <p className="text-2xl font-serif">3</p>
                    <p className="text-white/70 text-xs font-sans">{t("hiwPage.step4.needReview")}</p>
                  </div>
                  <div>
                    <p className="text-2xl font-serif">{"\u20AC2,340"}</p>
                    <p className="text-white/70 text-xs font-sans">{t("hiwPage.step4.totalProcessed")}</p>
                  </div>
                  <div>
                    <p className="text-2xl font-serif">{"\u20AC847"}</p>
                    <p className="text-white/70 text-xs font-sans">{t("hiwPage.step4.healthCosts")}</p>
                  </div>
                </div>
              </div>

              <div className="bg-warm-white rounded-2xl p-6 border border-sand-dark/10">
                <p className="text-charcoal font-sans font-semibold text-sm mb-3">{t("hiwPage.step4.timeSaved")}</p>
                <div className="flex items-baseline gap-2">
                  <span className="text-4xl font-serif text-teal">4.5</span>
                  <span className="text-charcoal-light font-sans text-sm">{t("hiwPage.step4.hoursWeek")}</span>
                </div>
                <p className="text-xs text-charcoal-light font-sans mt-2">
                  {t("hiwPage.step4.compared")}
                </p>
              </div>
            </motion.div>
          </motion.div>
        </div>
      </section>

      {/* ═══════════════════════════════════════════════════════════════
          COMPLETE DATA FLOW DIAGRAM
      ═══════════════════════════════════════════════════════════════ */}
      <section className="py-16 lg:py-24 bg-gradient-to-b from-warm-white to-sand/30">
        <div className="container">
          <motion.div
            className="text-center mb-12"
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true, margin: "-80px" }}
            variants={stagger}
          >
            <motion.span variants={fadeUp} className="text-teal font-medium text-sm tracking-widest uppercase font-sans">
              {t("hiwPage.flow.label")}
            </motion.span>
            <motion.h2 variants={fadeUp} className="text-3xl lg:text-4xl text-charcoal mt-3 mb-4">
              {t("hiwPage.flow.title")}
            </motion.h2>
            <motion.p variants={fadeUp} className="text-lg text-charcoal-light max-w-2xl mx-auto font-sans">
              {t("hiwPage.flow.desc")}
            </motion.p>
          </motion.div>

          <motion.div
            className="max-w-4xl mx-auto"
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true, margin: "-80px" }}
            variants={stagger}
          >
            <div className="space-y-4">
              {/* Sources row */}
              <motion.div variants={fadeUp} className="bg-white rounded-2xl p-6 border border-sand-dark/10">
                <p className="text-xs text-teal font-sans font-semibold uppercase tracking-wide mb-4">{t("hiwPage.flow.sources")}</p>
                <div className="flex flex-wrap justify-center gap-3">
                  {["Gmail", "WhatsApp", "Drive", "Banks", "Cash Receipts"].map((s) => (
                    <span key={s} className="bg-teal/10 text-teal text-xs font-sans font-medium px-4 py-2 rounded-full">
                      {s}
                    </span>
                  ))}
                </div>
              </motion.div>

              <motion.div variants={fadeUp} className="flex justify-center">
                <ArrowDown className="w-5 h-5 text-teal/40" />
              </motion.div>

              {/* FAB Processing */}
              <motion.div variants={fadeUp} className="bg-teal rounded-2xl p-6 text-white">
                <p className="text-white/70 text-xs font-sans font-semibold uppercase tracking-wide mb-4">{t("hiwPage.flow.engine")}</p>
                <div className="flex flex-wrap justify-center gap-3">
                  {[
                    t("hiwPage.flow.ocrExtraction"),
                    t("hiwPage.flow.aiClassification"),
                    t("hiwPage.flow.sourceMapping"),
                    t("hiwPage.flow.confidenceScoring"),
                    t("hiwPage.flow.gapDetection"),
                    t("hiwPage.flow.autoEmail"),
                  ].map((s) => (
                    <span key={s} className="bg-white/15 text-white text-xs font-sans font-medium px-4 py-2 rounded-full">
                      {s}
                    </span>
                  ))}
                </div>
              </motion.div>

              <motion.div variants={fadeUp} className="flex justify-center">
                <ArrowDown className="w-5 h-5 text-teal/40" />
              </motion.div>

              {/* End stations */}
              <motion.div variants={fadeUp} className="bg-white rounded-2xl p-6 border border-sand-dark/10">
                <p className="text-xs text-sage font-sans font-semibold uppercase tracking-wide mb-4">{t("hiwPage.flow.endStations")}</p>
                <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-3">
                  {[
                    { name: "mijngeldzaken.nl", typeKey: "hiwPage.flow.household" },
                    { name: "WaveApps Business", typeKey: "hiwPage.flow.sideHustle" },
                    { name: "WaveApps Personal", typeKey: "hiwPage.flow.healthcareType" },
                    { name: "SVB", typeKey: "hiwPage.flow.pgbPayments" },
                  ].map((p) => (
                    <div key={p.name} className="bg-sage-light/30 rounded-xl p-3 text-center">
                      <p className="text-xs font-sans font-semibold text-charcoal">{p.name}</p>
                      <p className="text-xs text-charcoal-light font-sans">{t(p.typeKey)}</p>
                    </div>
                  ))}
                </div>
              </motion.div>

              <motion.div variants={fadeUp} className="flex justify-center">
                <ArrowDown className="w-5 h-5 text-teal/40" />
              </motion.div>

              {/* Unified view */}
              <motion.div variants={fadeUp} className="bg-gradient-to-r from-teal to-sage rounded-2xl p-6 text-white text-center">
                <p className="text-white/80 text-xs font-sans font-semibold uppercase tracking-wide mb-2">{t("hiwPage.flow.result")}</p>
                <p className="text-xl font-serif">{t("hiwPage.flow.resultTitle")}</p>
                <p className="text-white/70 text-sm font-sans mt-1">
                  {t("hiwPage.flow.resultDesc")}
                </p>
              </motion.div>
            </div>
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
            viewport={{ once: true, margin: "-80px" }}
            variants={stagger}
          >
            <motion.h2 variants={fadeUp} className="text-3xl lg:text-5xl text-white mb-6">
              {t("cta.title")}
            </motion.h2>
            <motion.p variants={fadeUp} className="text-xl text-white/80 mb-10 leading-relaxed font-sans">
              {t("cta.desc")}
            </motion.p>
            <motion.div variants={fadeUp} className="flex flex-wrap justify-center gap-4">
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
