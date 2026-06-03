/*
 * FAB Contact Page — "Nordic Clarity" Design
 * Scandinavian Minimalism meets Healthcare Trust
 * Palette: Deep Teal, Warm Sand, Soft Sage, Charcoal on Warm White
 * Typography: DM Serif Display (display) + DM Sans (body)
 */

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  ArrowRight,
  CheckCircle2,
  Clock,
  Mail,
  MapPin,
  MessageSquare,
  Phone,
  Send,
  User,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import { toast } from "sonner";
import { Link } from "wouter";
import { useLanguage } from "@/contexts/LanguageContext";
import { trpc } from "@/lib/trpc";

const fadeUp = {
  hidden: { opacity: 0, y: 30 },
  visible: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.7, ease: [0.25, 0.1, 0.25, 1] as const },
  },
};

const stagger = {
  visible: { transition: { staggerChildren: 0.12 } },
};

type FormData = {
  firstName: string;
  lastName: string;
  email: string;
  subject: string;
  message: string;
};

type FormErrors = Partial<Record<keyof FormData, string>>;

const subjectOptionKeys = [
  { value: "", labelKey: "contact.topic.select" },
  { value: "general", labelKey: "contact.topic.general" },
  { value: "demo", labelKey: "contact.topic.demo" },
  { value: "pricing", labelKey: "contact.topic.pricing" },
  { value: "partnership", labelKey: "contact.topic.partnership" },
  { value: "support", labelKey: "contact.topic.support" },
  { value: "accessibility", labelKey: "contact.topic.accessibility" },
  { value: "media", labelKey: "contact.topic.media" },
];

export default function Contact() {
  const { t } = useLanguage();
  const [formData, setFormData] = useState<FormData>({
    firstName: "",
    lastName: "",
    email: "",
    subject: "",
    message: "",
  });
  const [errors, setErrors] = useState<FormErrors>({});
  const [submitted, setSubmitted] = useState(false);
  const [sending, setSending] = useState(false);

  function validate(): boolean {
    const newErrors: FormErrors = {};
    const trimFirst = formData.firstName.trim();
    const trimLast = formData.lastName.trim();
    const trimEmail = formData.email.trim().toLowerCase();
    const trimMsg = formData.message.trim();

    if (!trimFirst) newErrors.firstName = t("contact.error.firstName");
    else if (trimFirst.length > 100) newErrors.firstName = "Max 100 characters";

    if (!trimLast) newErrors.lastName = t("contact.error.lastName");
    else if (trimLast.length > 100) newErrors.lastName = "Max 100 characters";

    if (!trimEmail) {
      newErrors.email = t("contact.error.email");
    } else if (!/^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$/.test(trimEmail)) {
      newErrors.email = t("contact.error.emailInvalid");
    }

    if (!formData.subject) newErrors.subject = t("contact.error.subject");

    if (!trimMsg) {
      newErrors.message = t("contact.error.message");
    } else if (trimMsg.length < 10) {
      newErrors.message = t("contact.error.messageLength");
    } else if (trimMsg.length > 5000) {
      newErrors.message = "Max 5000 characters";
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  }

  function handleChange(
    e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>
  ) {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
    // Clear error on change
    if (errors[name as keyof FormData]) {
      setErrors((prev) => ({ ...prev, [name]: undefined }));
    }
  }

  const submitMutation = trpc.contact.submit.useMutation({
    onSuccess: () => {
      setSending(false);
      setSubmitted(true);
      toast.success(t("contact.success.toast"));
    },
    onError: (error) => {
      setSending(false);
      toast.error(error.message || "Something went wrong. Please try again.");
    },
  });

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!validate()) return;

    setSending(true);
    submitMutation.mutate({
      firstName: formData.firstName.trim(),
      lastName: formData.lastName.trim(),
      email: formData.email.trim(),
      subject: formData.subject,
      message: formData.message.trim(),
    });
  }

  function handleReset() {
    setFormData({ firstName: "", lastName: "", email: "", subject: "", message: "" });
    setErrors({});
    setSubmitted(false);
  }

  const inputBase =
    "w-full px-4 py-3.5 rounded-xl border bg-white text-charcoal placeholder:text-charcoal-light/50 font-sans text-[15px] transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-teal/30 focus:border-teal";
  const inputError = "border-red-400 focus:ring-red-300/30 focus:border-red-400";
  const inputNormal = "border-sand-dark/30 hover:border-sand-dark/50";

  return (
    <div className="min-h-screen bg-warm-white">
      <Navbar />

      {/* ═══════════════════════════════════════════════════════════════
          HERO HEADER
      ═══════════════════════════════════════════════════════════════ */}
      <section className="relative pt-28 pb-12 lg:pt-36 lg:pb-16 overflow-hidden">
        {/* Background organic shapes */}
        <div className="absolute top-0 left-0 w-full h-full -z-10 opacity-20">
          <svg viewBox="0 0 1200 400" className="w-full h-full" preserveAspectRatio="none">
            <ellipse cx="200" cy="350" rx="400" ry="250" fill="oklch(0.88 0.04 145)" />
            <ellipse cx="1000" cy="50" rx="300" ry="200" fill="oklch(0.93 0.03 80)" />
          </svg>
        </div>

        <div className="container">
          <motion.div
            className="max-w-2xl"
            initial="hidden"
            animate="visible"
            variants={stagger}
          >
            <motion.span
              variants={fadeUp}
              className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-sage-light text-teal text-sm font-medium tracking-wide mb-4"
            >
              <MessageSquare className="w-4 h-4" />
              {t("contact.badge")}
            </motion.span>
            <motion.h1
              variants={fadeUp}
              className="text-4xl sm:text-5xl lg:text-[3.25rem] leading-[1.1] tracking-tight text-charcoal mb-5"
            >
              {t("contact.title1")} <span className="text-teal">{t("contact.titleHighlight")}</span>
            </motion.h1>
            <motion.p
              variants={fadeUp}
              className="text-lg text-charcoal-light leading-relaxed max-w-xl"
            >
              {t("contact.desc")}
            </motion.p>
          </motion.div>
        </div>
      </section>

      {/* ═══════════════════════════════════════════════════════════════
          CONTACT FORM + INFO CARDS
      ═══════════════════════════════════════════════════════════════ */}
      <section className="pb-20 lg:pb-28">
        <div className="container">
          <div className="grid lg:grid-cols-12 gap-10 lg:gap-14">
            {/* LEFT — Contact Form */}
            <motion.div
              className="lg:col-span-7"
              initial="hidden"
              animate="visible"
              variants={stagger}
            >
              <motion.div
                variants={fadeUp}
                className="bg-white rounded-2xl shadow-sm border border-sand-dark/15 p-8 lg:p-10"
              >
                <AnimatePresence mode="wait">
                  {submitted ? (
                    /* ── Success State ── */
                    <motion.div
                      key="success"
                      initial={{ opacity: 0, scale: 0.95 }}
                      animate={{ opacity: 1, scale: 1 }}
                      exit={{ opacity: 0, scale: 0.95 }}
                      className="text-center py-12"
                    >
                      <div className="w-20 h-20 rounded-full bg-sage-light flex items-center justify-center mx-auto mb-6">
                        <CheckCircle2 className="w-10 h-10 text-teal" />
                      </div>
                      <h3 className="text-2xl text-charcoal mb-3">
                        {t("contact.success.title")}
                      </h3>
                      <p className="text-charcoal-light leading-relaxed max-w-md mx-auto mb-8">
                        {t("contact.success.desc")} <span className="font-medium text-charcoal">{formData.email}</span>
                      </p>
                      <div className="flex flex-wrap justify-center gap-4">
                        <Button
                          onClick={handleReset}
                          className="bg-teal hover:bg-teal-light text-white px-6 py-5 rounded-xl"
                        >
                          {t("contact.success.another")}
                        </Button>
                        <Button
                          variant="outline"
                          onClick={() => (window.location.href = "/")}
                          className="border-teal/20 text-teal hover:bg-teal/5 px-6 py-5 rounded-xl"
                        >
                          {t("contact.success.backHome")}
                        </Button>
                      </div>
                    </motion.div>
                  ) : (
                    /* ── Form ── */
                    <motion.form
                      key="form"
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      exit={{ opacity: 0 }}
                      onSubmit={handleSubmit}
                      noValidate
                    >
                      <div className="mb-8">
                        <h2 className="text-2xl text-charcoal mb-2 font-sans font-semibold">
                          {t("contact.form.send")}
                        </h2>
                        <p className="text-charcoal-light text-[15px]">
                          {t("contact.desc")}
                        </p>
                      </div>

                      <div className="space-y-5">
                        {/* Name row */}
                        <div className="grid sm:grid-cols-2 gap-5">
                          <div>
                            <label
                              htmlFor="firstName"
                              className="block text-sm font-medium text-charcoal mb-1.5"
                            >
                              {t("contact.form.firstName")} <span className="text-red-400">*</span>
                            </label>
                            <div className="relative">
                              <User className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-charcoal-light/50" />
                              <input
                                id="firstName"
                                name="firstName"
                                type="text"
                                placeholder={t("contact.form.firstNamePlaceholder")}
                                value={formData.firstName}
                                onChange={handleChange}
                                className={`${inputBase} pl-10 ${errors.firstName ? inputError : inputNormal}`}
                              />
                            </div>
                            {errors.firstName && (
                              <p className="mt-1.5 text-xs text-red-500">{errors.firstName}</p>
                            )}
                          </div>
                          <div>
                            <label
                              htmlFor="lastName"
                              className="block text-sm font-medium text-charcoal mb-1.5"
                            >
                              {t("contact.form.lastName")} <span className="text-red-400">*</span>
                            </label>
                            <div className="relative">
                              <User className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-charcoal-light/50" />
                              <input
                                id="lastName"
                                name="lastName"
                                type="text"
                                placeholder={t("contact.form.lastNamePlaceholder")}
                                value={formData.lastName}
                                onChange={handleChange}
                                className={`${inputBase} pl-10 ${errors.lastName ? inputError : inputNormal}`}
                              />
                            </div>
                            {errors.lastName && (
                              <p className="mt-1.5 text-xs text-red-500">{errors.lastName}</p>
                            )}
                          </div>
                        </div>

                        {/* Email */}
                        <div>
                          <label
                            htmlFor="email"
                            className="block text-sm font-medium text-charcoal mb-1.5"
                          >
                            {t("contact.form.email")} <span className="text-red-400">*</span>
                          </label>
                          <div className="relative">
                            <Mail className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-charcoal-light/50" />
                            <input
                              id="email"
                              name="email"
                              type="email"
                              placeholder={t("contact.form.emailPlaceholder")}
                              value={formData.email}
                              onChange={handleChange}
                              className={`${inputBase} pl-10 ${errors.email ? inputError : inputNormal}`}
                            />
                          </div>
                          {errors.email && (
                            <p className="mt-1.5 text-xs text-red-500">{errors.email}</p>
                          )}
                        </div>

                        {/* Subject */}
                        <div>
                          <label
                            htmlFor="subject"
                            className="block text-sm font-medium text-charcoal mb-1.5"
                          >
                            {t("contact.form.topic")} <span className="text-red-400">*</span>
                          </label>
                          <div className="relative">
                            <MessageSquare className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-charcoal-light/50" />
                            <select
                              id="subject"
                              name="subject"
                              value={formData.subject}
                              onChange={handleChange}
                              className={`${inputBase} pl-10 appearance-none ${errors.subject ? inputError : inputNormal}`}
                            >
                              {subjectOptionKeys.map((opt) => (
                                <option key={opt.value} value={opt.value}>
                                  {t(opt.labelKey)}
                                </option>
                              ))}
                            </select>
                            {/* Custom chevron */}
                            <svg
                              className="absolute right-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-charcoal-light/50 pointer-events-none"
                              fill="none"
                              viewBox="0 0 24 24"
                              stroke="currentColor"
                              strokeWidth={2}
                            >
                              <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
                            </svg>
                          </div>
                          {errors.subject && (
                            <p className="mt-1.5 text-xs text-red-500">{errors.subject}</p>
                          )}
                        </div>

                        {/* Message */}
                        <div>
                          <label
                            htmlFor="message"
                            className="block text-sm font-medium text-charcoal mb-1.5"
                          >
                            {t("contact.form.message")} <span className="text-red-400">*</span>
                          </label>
                          <textarea
                            id="message"
                            name="message"
                            rows={5}
                            placeholder={t("contact.form.messagePlaceholderLong")}
                            value={formData.message}
                            onChange={handleChange}
                            className={`${inputBase} resize-none ${errors.message ? inputError : inputNormal}`}
                          />
                          {errors.message && (
                            <p className="mt-1.5 text-xs text-red-500">{errors.message}</p>
                          )}
                          <p className="mt-1.5 text-xs text-charcoal-light/60 text-right">
                            {formData.message.length} / 2000
                          </p>
                        </div>
                      </div>

                      {/* Submit */}
                      <div className="mt-8">
                        <Button
                          type="submit"
                          disabled={sending}
                          className="w-full sm:w-auto bg-teal hover:bg-teal-light text-white px-10 py-6 text-base rounded-xl shadow-lg shadow-teal/20 transition-all duration-300 hover:shadow-xl hover:shadow-teal/30 disabled:opacity-60"
                        >
                          {sending ? (
                            <>
                              <svg
                                className="animate-spin -ml-1 mr-2 h-5 w-5 text-white"
                                xmlns="http://www.w3.org/2000/svg"
                                fill="none"
                                viewBox="0 0 24 24"
                              >
                                <circle
                                  className="opacity-25"
                                  cx="12"
                                  cy="12"
                                  r="10"
                                  stroke="currentColor"
                                  strokeWidth="4"
                                />
                                <path
                                  className="opacity-75"
                                  fill="currentColor"
                                  d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
                                />
                              </svg>
                              {t("contact.form.sending")}
                            </>
                          ) : (
                            <>
                              {t("contact.form.send")}
                              <Send className="ml-2 w-5 h-5" />
                            </>
                          )}
                        </Button>
                      </div>
                    </motion.form>
                  )}
                </AnimatePresence>
              </motion.div>
            </motion.div>

            {/* RIGHT — Contact Info Cards */}
            <motion.div
              className="lg:col-span-5"
              initial="hidden"
              animate="visible"
              variants={stagger}
            >
              <div className="space-y-6 lg:sticky lg:top-28">
                {/* Email card */}
                <motion.div
                  variants={fadeUp}
                  className="bg-white rounded-2xl p-6 shadow-sm border border-sand-dark/15 hover:shadow-md transition-shadow duration-300"
                >
                  <div className="flex items-start gap-4">
                    <div className="w-12 h-12 rounded-xl bg-sage-light flex items-center justify-center shrink-0">
                      <Mail className="w-5 h-5 text-teal" />
                    </div>
                    <div>
                      <h3 className="text-lg text-charcoal font-sans font-semibold mb-1">
                        {t("contact.info.email")}
                      </h3>
                      <p className="text-sm text-charcoal-light mb-2">
                        {t("contact.info.email")}
                      </p>
                      <a
                        href="mailto:hello@fab-finance.nl"
                        className="text-teal hover:text-teal-light text-sm font-medium transition-colors"
                      >
                        hello@fab-finance.nl
                      </a>
                    </div>
                  </div>
                </motion.div>

                {/* Response time card */}
                <motion.div
                  variants={fadeUp}
                  className="bg-white rounded-2xl p-6 shadow-sm border border-sand-dark/15 hover:shadow-md transition-shadow duration-300"
                >
                  <div className="flex items-start gap-4">
                    <div className="w-12 h-12 rounded-xl bg-sand flex items-center justify-center shrink-0">
                      <Clock className="w-5 h-5 text-teal" />
                    </div>
                    <div>
                      <h3 className="text-lg text-charcoal font-sans font-semibold mb-1">
                        {t("contact.info.response")}
                      </h3>
                      <p className="text-sm text-charcoal-light">
                        {t("contact.info.responseVal")}
                      </p>
                    </div>
                  </div>
                </motion.div>

                {/* Location card */}
                <motion.div
                  variants={fadeUp}
                  className="bg-white rounded-2xl p-6 shadow-sm border border-sand-dark/15 hover:shadow-md transition-shadow duration-300"
                >
                  <div className="flex items-start gap-4">
                    <div className="w-12 h-12 rounded-xl bg-sage-light flex items-center justify-center shrink-0">
                      <MapPin className="w-5 h-5 text-teal" />
                    </div>
                    <div>
                      <h3 className="text-lg text-charcoal font-sans font-semibold mb-1">
                        {t("contact.info.location")}
                      </h3>
                      <p className="text-sm text-charcoal-light">
                        {t("contact.info.locationVal")}
                      </p>
                    </div>
                  </div>
                </motion.div>

                {/* Phone card */}
                <motion.div
                  variants={fadeUp}
                  className="bg-white rounded-2xl p-6 shadow-sm border border-sand-dark/15 hover:shadow-md transition-shadow duration-300"
                >
                  <div className="flex items-start gap-4">
                    <div className="w-12 h-12 rounded-xl bg-sand flex items-center justify-center shrink-0">
                      <Phone className="w-5 h-5 text-teal" />
                    </div>
                    <div>
                      <h3 className="text-lg text-charcoal font-sans font-semibold mb-1">
                        {t("contact.info.phone")}
                      </h3>
                      <p className="text-sm text-charcoal-light mb-2">
                        {t("contact.info.phoneVal")}
                      </p>
                      <button
                        className="text-teal hover:text-teal-light text-sm font-medium transition-colors inline-flex items-center gap-1"
                        onClick={() => toast(t("contact.toast.schedule"))}
                      >
                        {t("contact.info.phoneVal")}
                        <ArrowRight className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>
                </motion.div>

                {/* FAQ nudge */}
                <motion.div
                  variants={fadeUp}
                  className="bg-teal/5 rounded-2xl p-6 border border-teal/10"
                >
                  <h3 className="text-lg text-charcoal font-sans font-semibold mb-2">
                    {t("contact.info.faq")}
                  </h3>
                  <p className="text-sm text-charcoal-light mb-3">
                    {t("contact.info.faqDesc")}
                  </p>
                  <Link
                    href="/faq"
                    className="text-teal hover:text-teal-light text-sm font-medium transition-colors inline-flex items-center gap-1"
                  >
                    {t("contact.info.faqLink")}
                    <ArrowRight className="w-3.5 h-3.5" />
                  </Link>
                </motion.div>
              </div>
            </motion.div>
          </div>
        </div>
      </section>

      <Footer />
    </div>
  );
}
