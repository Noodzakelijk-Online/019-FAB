import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { X, CheckCircle, Sparkles, AlertCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useLanguage } from "@/contexts/LanguageContext";
import { trpc } from "@/lib/trpc";

interface WaitlistModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function WaitlistModal({ isOpen, onClose }: WaitlistModalProps) {
  const { t } = useLanguage();
  const [email, setEmail] = useState("");
  const [firstName, setFirstName] = useState("");
  const [situation, setSituation] = useState("");
  const [submitted, setSubmitted] = useState(false);
  const [alreadyRegistered, setAlreadyRegistered] = useState(false);
  const [errorMsg, setErrorMsg] = useState("");

  const joinMutation = trpc.waitlist.join.useMutation({
    onSuccess: (data) => {
      if (data.message === "already_registered") {
        setAlreadyRegistered(true);
      }
      setSubmitted(true);
    },
    onError: (error) => {
      setErrorMsg(error.message || "Something went wrong. Please try again.");
    },
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg("");
    setAlreadyRegistered(false);

    const trimmedEmail = email.trim().toLowerCase();
    const trimmedName = firstName.trim();

    // Client-side validation
    if (!trimmedEmail) {
      setErrorMsg(t("contact.error.email"));
      return;
    }
    if (!/^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$/.test(trimmedEmail)) {
      setErrorMsg(t("contact.error.emailInvalid"));
      return;
    }
    if (trimmedName.length > 100) {
      setErrorMsg("Name is too long (max 100 characters)");
      return;
    }

    joinMutation.mutate({
      email: trimmedEmail,
      firstName: trimmedName || undefined,
    });
  };

  const handleClose = () => {
    onClose();
    setTimeout(() => {
      setSubmitted(false);
      setAlreadyRegistered(false);
      setErrorMsg("");
      setEmail("");
      setFirstName("");
      setSituation("");
    }, 300);
  };

  const situations = [
    { value: "pgb", label: t("waitlist.situationPGB") },
    { value: "wajong", label: t("waitlist.situationWajong") },
    { value: "wia", label: t("waitlist.situationWIA") },
    { value: "caregiver", label: t("waitlist.situationCaregiver") },
    { value: "other", label: t("waitlist.situationOther") },
  ];

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          className="fixed inset-0 z-50 flex items-center justify-center p-4"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.2 }}
        >
          {/* Backdrop */}
          <motion.div
            className="absolute inset-0 bg-charcoal/60 backdrop-blur-sm"
            onClick={handleClose}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
          />

          {/* Modal */}
          <motion.div
            className="relative bg-white rounded-2xl shadow-2xl w-full max-w-md overflow-hidden"
            initial={{ opacity: 0, scale: 0.95, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 20 }}
            transition={{ duration: 0.3, ease: "easeOut" }}
          >
            {/* Close button */}
            <button
              onClick={handleClose}
              className="absolute top-4 right-4 z-10 w-8 h-8 rounded-full bg-charcoal/5 flex items-center justify-center hover:bg-charcoal/10 transition-colors"
            >
              <X className="w-4 h-4 text-charcoal" />
            </button>

            {/* Header */}
            <div className="bg-gradient-to-br from-teal to-teal-light p-8 pb-6">
              <div className="flex items-center gap-2 mb-3">
                <Sparkles className="w-4 h-4 text-white/80" />
                <span className="text-white/80 text-xs font-medium tracking-widest uppercase">
                  {t("waitlist.badge")}
                </span>
              </div>
              <h2 className="text-2xl text-white mb-2">{t("waitlist.title")}</h2>
              <p className="text-white/70 text-sm leading-relaxed">
                {t("waitlist.desc")}
              </p>
            </div>

            {/* Content */}
            <div className="p-8">
              <AnimatePresence mode="wait">
                {!submitted ? (
                  <motion.form
                    key="form"
                    onSubmit={handleSubmit}
                    className="space-y-4"
                    initial={{ opacity: 1 }}
                    exit={{ opacity: 0, x: -20 }}
                  >
                    <div>
                      <label className="block text-sm font-sans font-medium text-charcoal mb-1.5">
                        {t("waitlist.name")}
                      </label>
                      <input
                        type="text"
                        value={firstName}
                        onChange={(e) => setFirstName(e.target.value)}
                        maxLength={100}
                        placeholder={t("waitlist.namePlaceholder")}
                        className="w-full px-4 py-2.5 rounded-xl border border-sand-dark/30 bg-warm-white text-charcoal placeholder:text-charcoal-light/50 focus:outline-none focus:ring-2 focus:ring-teal/30 focus:border-teal transition-all text-sm font-sans"
                      />
                    </div>

                    <div>
                      <label className="block text-sm font-sans font-medium text-charcoal mb-1.5">
                        {t("waitlist.email")} <span className="text-red-500">*</span>
                      </label>
                      <input
                        type="email"
                        required
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        maxLength={254}
                        placeholder={t("waitlist.emailPlaceholder")}
                        className="w-full px-4 py-2.5 rounded-xl border border-sand-dark/30 bg-warm-white text-charcoal placeholder:text-charcoal-light/50 focus:outline-none focus:ring-2 focus:ring-teal/30 focus:border-teal transition-all text-sm font-sans"
                      />
                    </div>

                    <div>
                      <label className="block text-sm font-sans font-medium text-charcoal mb-1.5">
                        {t("waitlist.situation")}
                      </label>
                      <select
                        value={situation}
                        onChange={(e) => setSituation(e.target.value)}
                        className="w-full px-4 py-2.5 rounded-xl border border-sand-dark/30 bg-warm-white text-charcoal focus:outline-none focus:ring-2 focus:ring-teal/30 focus:border-teal transition-all text-sm font-sans appearance-none"
                      >
                        <option value="">{t("waitlist.situationPlaceholder")}</option>
                        {situations.map((s) => (
                          <option key={s.value} value={s.value}>
                            {s.label}
                          </option>
                        ))}
                      </select>
                    </div>

                    {errorMsg && (
                      <div className="flex items-center gap-2 p-3 rounded-xl bg-red-50 text-red-600 text-sm">
                        <AlertCircle className="w-4 h-4 shrink-0" />
                        {errorMsg}
                      </div>
                    )}

                    <Button
                      type="submit"
                      disabled={joinMutation.isPending}
                      className="w-full py-5 rounded-xl bg-teal hover:bg-teal-light text-white font-semibold font-sans mt-2"
                    >
                      {joinMutation.isPending ? t("waitlist.submitting") : t("waitlist.submit")}
                    </Button>

                    <p className="text-xs text-charcoal-light text-center font-sans">
                      {t("waitlist.privacy")}
                    </p>
                  </motion.form>
                ) : (
                  <motion.div
                    key="success"
                    className="text-center py-4"
                    initial={{ opacity: 0, x: 20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ duration: 0.3 }}
                  >
                    <div className="w-16 h-16 rounded-full bg-sage-light flex items-center justify-center mx-auto mb-4">
                      <CheckCircle className="w-8 h-8 text-sage" />
                    </div>
                    <h3 className="text-xl text-charcoal mb-2">
                      {alreadyRegistered
                        ? t("waitlist.success.alreadyTitle")
                        : t("waitlist.success.title")}
                    </h3>
                    <p className="text-charcoal-light text-sm mb-6 font-sans leading-relaxed">
                      {alreadyRegistered
                        ? t("waitlist.success.alreadyDesc")
                        : t("waitlist.success.desc")}
                    </p>
                    <Button
                      onClick={handleClose}
                      variant="outline"
                      className="rounded-xl border-sand-dark/30 text-charcoal font-sans"
                    >
                      {t("waitlist.success.close")}
                    </Button>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
