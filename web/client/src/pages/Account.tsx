import { useState } from "react";
import { motion } from "framer-motion";
import {
  CreditCard,
  FileText,
  ExternalLink,
  Download,
  Shield,
  CheckCircle,
  XCircle,
  Clock,
  User,
  Mail,
  Calendar,
  Loader2,
  ArrowRight,
  LogOut,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import { useLanguage } from "@/contexts/LanguageContext";
import { useAuth } from "@/_core/hooks/useAuth";
import { trpc } from "@/lib/trpc";
import { getLoginUrl } from "@/const";
import { toast } from "sonner";

const fadeUp = {
  hidden: { opacity: 0, y: 30 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.7, ease: [0.25, 0.1, 0.25, 1] as const } },
};

const stagger = {
  visible: { transition: { staggerChildren: 0.12 } },
};

function StatusBadge({ status }: { status: string }) {
  const { t } = useLanguage();
  const statusConfig: Record<string, { color: string; icon: typeof CheckCircle; label: string }> = {
    active: { color: "bg-green-100 text-green-700", icon: CheckCircle, label: t("account.statusActive") },
    trialing: { color: "bg-blue-100 text-blue-700", icon: Clock, label: t("account.statusTrialing") },
    past_due: { color: "bg-amber-100 text-amber-700", icon: Clock, label: t("account.statusPastDue") },
    canceled: { color: "bg-red-100 text-red-700", icon: XCircle, label: t("account.statusCanceled") },
    none: { color: "bg-sand text-charcoal-light", icon: Shield, label: t("account.statusFree") },
  };

  const config = statusConfig[status] || statusConfig.none;
  const Icon = config.icon;

  return (
    <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium ${config.color}`}>
      <Icon className="w-3.5 h-3.5" />
      {config.label}
    </span>
  );
}

export default function Account() {
  const { t, lang } = useLanguage();
  const { user, loading: authLoading, isAuthenticated, logout } = useAuth();
  const [portalLoading, setPortalLoading] = useState(false);

  const { data: subData, isLoading: subLoading } = trpc.stripe.subscriptionStatus.useQuery(
    undefined,
    { enabled: isAuthenticated }
  );

  const { data: invoiceData, isLoading: invoicesLoading } = trpc.stripe.invoices.useQuery(
    undefined,
    { enabled: isAuthenticated }
  );

  const portalMutation = trpc.stripe.createPortalSession.useMutation({
    onSuccess: (data) => {
      window.open(data.url, "_blank");
      toast.success(t("account.portalRedirect"));
    },
    onError: (error) => {
      toast.error(error.message);
    },
  });

  const checkoutMutation = trpc.stripe.createCheckout.useMutation({
    onSuccess: (data) => {
      window.open(data.url, "_blank");
      toast.success(t("account.checkoutRedirect"));
    },
    onError: (error) => {
      toast.error(error.message);
    },
  });

  const handleManageBilling = () => {
    setPortalLoading(true);
    portalMutation.mutate(
      { origin: window.location.origin },
      { onSettled: () => setPortalLoading(false) }
    );
  };

  const handleUpgrade = () => {
    checkoutMutation.mutate({
      origin: window.location.origin,
      productKey: "payAsYouGo",
    });
  };

  const handleLogout = async () => {
    await logout();
    window.location.href = "/";
  };

  const formatDate = (date: Date | string) => {
    const d = new Date(date);
    return d.toLocaleDateString(lang === "nl" ? "nl-NL" : "en-US", {
      year: "numeric",
      month: "long",
      day: "numeric",
    });
  };

  const formatCurrency = (amount: number, currency: string) => {
    return new Intl.NumberFormat(lang === "nl" ? "nl-NL" : "en-US", {
      style: "currency",
      currency: currency.toUpperCase(),
    }).format(amount / 100);
  };

  // Not authenticated - show login prompt
  if (!authLoading && !isAuthenticated) {
    return (
      <div className="min-h-screen bg-warm-white">
        <Navbar />
        <section className="pt-32 pb-20">
          <div className="container max-w-lg text-center">
            <motion.div
              initial="hidden"
              animate="visible"
              variants={stagger}
            >
              <motion.div variants={fadeUp} className="w-16 h-16 rounded-2xl bg-sand flex items-center justify-center mx-auto mb-6">
                <User className="w-8 h-8 text-teal" />
              </motion.div>
              <motion.h1 variants={fadeUp} className="text-3xl text-charcoal mb-4">
                {t("account.loginRequired")}
              </motion.h1>
              <motion.p variants={fadeUp} className="text-charcoal-light mb-8">
                {t("account.loginRequiredDesc")}
              </motion.p>
              <motion.div variants={fadeUp}>
                <a href={getLoginUrl()}>
                  <Button className="bg-teal hover:bg-teal-light text-white px-8 py-5 rounded-xl">
                    {t("nav.signIn")}
                    <ArrowRight className="ml-2 w-4 h-4" />
                  </Button>
                </a>
              </motion.div>
            </motion.div>
          </div>
        </section>
        <Footer />
      </div>
    );
  }

  // Loading state
  if (authLoading) {
    return (
      <div className="min-h-screen bg-warm-white">
        <Navbar />
        <section className="pt-32 pb-20">
          <div className="container flex justify-center">
            <Loader2 className="w-8 h-8 animate-spin text-teal" />
          </div>
        </section>
        <Footer />
      </div>
    );
  }

  const hasSubscription = subData?.hasSubscription ?? false;
  const billingReady = subData?.billingReady ?? hasSubscription;
  const subscriptionStatus = subData?.status ?? "none";
  const invoices = invoiceData?.invoices ?? [];

  return (
    <div className="min-h-screen bg-warm-white">
      <Navbar />

      {/* Header */}
      <section className="pt-28 pb-12 lg:pt-32 lg:pb-16">
        <div className="container max-w-4xl">
          <motion.div
            initial="hidden"
            animate="visible"
            variants={stagger}
          >
            <motion.span
              variants={fadeUp}
              className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-sage-light text-teal text-sm font-medium tracking-wide mb-4"
            >
              <User className="w-4 h-4" />
              {t("account.title")}
            </motion.span>
            <motion.h1
              variants={fadeUp}
              className="text-3xl lg:text-4xl text-charcoal mb-2"
            >
              {t("account.welcome")}, {user?.name || t("account.user")}
            </motion.h1>
            <motion.p variants={fadeUp} className="text-charcoal-light text-lg">
              {t("account.subtitle")}
            </motion.p>
          </motion.div>
        </div>
      </section>

      {/* Main Content */}
      <section className="pb-20">
        <div className="container max-w-4xl">
          <div className="grid gap-6">

            {/* Profile Card */}
            <motion.div
              initial="hidden"
              whileInView="visible"
              viewport={{ once: true }}
              variants={fadeUp}
              className="bg-white rounded-2xl p-6 lg:p-8 shadow-sm border border-sand-dark/20"
            >
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-xl text-charcoal font-sans font-semibold flex items-center gap-2">
                  <User className="w-5 h-5 text-teal" />
                  {t("account.profile")}
                </h2>
                <Button
                  variant="outline"
                  size="sm"
                  className="rounded-lg border-red-200 text-red-600 hover:bg-red-50"
                  onClick={handleLogout}
                >
                  <LogOut className="w-4 h-4 mr-1.5" />
                  {t("account.logout")}
                </Button>
              </div>
              <div className="grid sm:grid-cols-2 gap-4">
                <div className="flex items-center gap-3 p-4 rounded-xl bg-sand/40">
                  <User className="w-5 h-5 text-teal shrink-0" />
                  <div>
                    <div className="text-xs text-charcoal-light">{t("account.name")}</div>
                    <div className="text-sm text-charcoal font-medium">{user?.name || "—"}</div>
                  </div>
                </div>
                <div className="flex items-center gap-3 p-4 rounded-xl bg-sand/40">
                  <Mail className="w-5 h-5 text-teal shrink-0" />
                  <div>
                    <div className="text-xs text-charcoal-light">{t("account.email")}</div>
                    <div className="text-sm text-charcoal font-medium">{user?.email || "—"}</div>
                  </div>
                </div>
                <div className="flex items-center gap-3 p-4 rounded-xl bg-sand/40">
                  <Calendar className="w-5 h-5 text-teal shrink-0" />
                  <div>
                    <div className="text-xs text-charcoal-light">{t("account.memberSince")}</div>
                    <div className="text-sm text-charcoal font-medium">
                      {user?.createdAt ? formatDate(user.createdAt) : "—"}
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-3 p-4 rounded-xl bg-sand/40">
                  <Shield className="w-5 h-5 text-teal shrink-0" />
                  <div>
                    <div className="text-xs text-charcoal-light">{t("account.plan")}</div>
                    <div className="text-sm text-charcoal font-medium">
                      {billingReady ? "Usage billing" : t("account.freePlan")}
                    </div>
                  </div>
                </div>
              </div>
            </motion.div>

            {/* Subscription Card */}
            <motion.div
              initial="hidden"
              whileInView="visible"
              viewport={{ once: true }}
              variants={fadeUp}
              className="bg-white rounded-2xl p-6 lg:p-8 shadow-sm border border-sand-dark/20"
            >
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-xl text-charcoal font-sans font-semibold flex items-center gap-2">
                  <CreditCard className="w-5 h-5 text-teal" />
                  {t("account.subscription")}
                </h2>
                {subLoading ? (
                  <Loader2 className="w-5 h-5 animate-spin text-charcoal-light" />
                ) : (
                  <StatusBadge status={subscriptionStatus} />
                )}
              </div>

              {subLoading ? (
                <div className="flex justify-center py-8">
                  <Loader2 className="w-6 h-6 animate-spin text-teal" />
                </div>
              ) : billingReady ? (
                <div className="space-y-4">
                  <div className="grid sm:grid-cols-2 gap-4">
                    <div className="p-4 rounded-xl bg-sand/40">
                      <div className="text-xs text-charcoal-light mb-1">Billing model</div>
                      <div className="text-sm text-charcoal font-medium">Resource cost x 2.5</div>
                    </div>
                    <div className="p-4 rounded-xl bg-sand/40">
                      <div className="text-xs text-charcoal-light mb-1">Fixed monthly fee</div>
                      <div className="text-sm text-charcoal font-medium">None</div>
                    </div>
                  </div>
                  <p className="text-sm text-charcoal-light">Your saved payment method is used only for verified resource-usage invoices. A successful setup does not create a recurring subscription.</p>
                  <Button
                    className="bg-teal hover:bg-teal-light text-white rounded-xl"
                    onClick={handleManageBilling}
                    disabled={portalLoading}
                  >
                    {portalLoading ? (
                      <Loader2 className="w-4 h-4 animate-spin mr-2" />
                    ) : (
                      <ExternalLink className="w-4 h-4 mr-2" />
                    )}
                    {t("account.manageBilling")}
                  </Button>
                </div>
              ) : (
                <div className="text-center py-6">
                  <div className="w-14 h-14 rounded-2xl bg-sand flex items-center justify-center mx-auto mb-4">
                    <Shield className="w-7 h-7 text-charcoal-light" />
                  </div>
                  <h3 className="text-lg text-charcoal font-sans font-semibold mb-2">
                    {t("account.freePlanTitle")}
                  </h3>
                  <p className="text-charcoal-light text-sm mb-6 max-w-md mx-auto">
                    {t("account.freePlanDesc")}
                  </p>
                  <Button
                    className="bg-teal hover:bg-teal-light text-white rounded-xl px-8"
                    onClick={handleUpgrade}
                    disabled={checkoutMutation.isPending}
                  >
                    {checkoutMutation.isPending ? (
                      <Loader2 className="w-4 h-4 animate-spin mr-2" />
                    ) : (
                      <ArrowRight className="w-4 h-4 mr-2" />
                    )}
                    {t("account.upgradeCta")}
                  </Button>
                </div>
              )}
            </motion.div>

            {/* Invoices Card */}
            <motion.div
              initial="hidden"
              whileInView="visible"
              viewport={{ once: true }}
              variants={fadeUp}
              className="bg-white rounded-2xl p-6 lg:p-8 shadow-sm border border-sand-dark/20"
            >
              <h2 className="text-xl text-charcoal font-sans font-semibold flex items-center gap-2 mb-6">
                <FileText className="w-5 h-5 text-teal" />
                {t("account.invoices")}
              </h2>

              {invoicesLoading ? (
                <div className="flex justify-center py-8">
                  <Loader2 className="w-6 h-6 animate-spin text-teal" />
                </div>
              ) : invoices.length === 0 ? (
                <div className="text-center py-8">
                  <div className="w-14 h-14 rounded-2xl bg-sand flex items-center justify-center mx-auto mb-4">
                    <FileText className="w-7 h-7 text-charcoal-light" />
                  </div>
                  <p className="text-charcoal-light text-sm">
                    {t("account.noInvoices")}
                  </p>
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-sand">
                        <th className="text-left py-3 px-2 text-charcoal-light font-medium text-xs uppercase tracking-wider">
                          {t("account.invoiceDate")}
                        </th>
                        <th className="text-left py-3 px-2 text-charcoal-light font-medium text-xs uppercase tracking-wider">
                          {t("account.invoiceAmount")}
                        </th>
                        <th className="text-left py-3 px-2 text-charcoal-light font-medium text-xs uppercase tracking-wider">
                          {t("account.invoiceStatus")}
                        </th>
                        <th className="text-right py-3 px-2 text-charcoal-light font-medium text-xs uppercase tracking-wider">
                          {t("account.invoiceActions")}
                        </th>
                      </tr>
                    </thead>
                    <tbody>
                      {invoices.map((invoice) => (
                        <tr key={invoice.id} className="border-b border-sand/50 hover:bg-sand/20 transition-colors">
                          <td className="py-3 px-2 text-charcoal">
                            {formatDate(invoice.created)}
                          </td>
                          <td className="py-3 px-2 text-charcoal font-medium">
                            {formatCurrency(invoice.amountPaid, invoice.currency)}
                          </td>
                          <td className="py-3 px-2">
                            <span
                              className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${
                                invoice.status === "paid"
                                  ? "bg-green-100 text-green-700"
                                  : invoice.status === "open"
                                  ? "bg-amber-100 text-amber-700"
                                  : "bg-sand text-charcoal-light"
                              }`}
                            >
                              {invoice.status === "paid" && <CheckCircle className="w-3 h-3" />}
                              {invoice.status === "open" && <Clock className="w-3 h-3" />}
                              {invoice.status || "—"}
                            </span>
                          </td>
                          <td className="py-3 px-2 text-right">
                            <div className="flex items-center justify-end gap-2">
                              {invoice.hostedInvoiceUrl && (
                                <a
                                  href={invoice.hostedInvoiceUrl}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="text-teal hover:text-teal-light transition-colors"
                                  title={t("account.viewInvoice")}
                                >
                                  <ExternalLink className="w-4 h-4" />
                                </a>
                              )}
                              {invoice.invoicePdf && (
                                <a
                                  href={invoice.invoicePdf}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="text-teal hover:text-teal-light transition-colors"
                                  title={t("account.downloadPdf")}
                                >
                                  <Download className="w-4 h-4" />
                                </a>
                              )}
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </motion.div>

          </div>
        </div>
      </section>

      <Footer />
    </div>
  );
}
