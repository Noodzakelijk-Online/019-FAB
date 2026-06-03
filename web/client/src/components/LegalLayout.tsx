import { motion } from "framer-motion";
import { ArrowLeft } from "lucide-react";
import { Link } from "wouter";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import { useLanguage } from "@/contexts/LanguageContext";

const fadeUp = {
  hidden: { opacity: 0, y: 30 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.7, ease: [0.25, 0.1, 0.25, 1] as const } },
};

interface LegalLayoutProps {
  title: string;
  lastUpdated: string;
  children: React.ReactNode;
}

export default function LegalLayout({ title, lastUpdated, children }: LegalLayoutProps) {
  const { t } = useLanguage();

  return (
    <div className="min-h-screen bg-warm-white">
      <Navbar />

      <section className="pt-28 pb-8 lg:pt-32">
        <div className="container max-w-3xl">
          <Link href="/" className="inline-flex items-center gap-2 text-sm text-teal hover:text-teal-light transition-colors mb-6">
            <ArrowLeft className="w-4 h-4" />
            {t("legal.backHome")}
          </Link>
          <motion.h1
            initial="hidden"
            animate="visible"
            variants={fadeUp}
            className="text-3xl lg:text-4xl text-charcoal mb-3"
          >
            {title}
          </motion.h1>
          <motion.p
            initial="hidden"
            animate="visible"
            variants={fadeUp}
            className="text-sm text-charcoal-light"
          >
            {t("legal.lastUpdated")}: {lastUpdated}
          </motion.p>
        </div>
      </section>

      <section className="pb-20">
        <div className="container max-w-3xl">
          <motion.div
            initial="hidden"
            animate="visible"
            variants={fadeUp}
            className="prose prose-charcoal max-w-none
              [&_h2]:text-2xl [&_h2]:text-charcoal [&_h2]:mt-10 [&_h2]:mb-4 [&_h2]:font-sans [&_h2]:font-semibold
              [&_h3]:text-lg [&_h3]:text-charcoal [&_h3]:mt-6 [&_h3]:mb-3 [&_h3]:font-sans [&_h3]:font-semibold
              [&_p]:text-charcoal-light [&_p]:leading-relaxed [&_p]:mb-4
              [&_ul]:text-charcoal-light [&_ul]:mb-4 [&_ul]:space-y-2
              [&_li]:leading-relaxed
              [&_a]:text-teal [&_a]:underline [&_a]:underline-offset-2 hover:[&_a]:text-teal-light
              [&_strong]:text-charcoal [&_strong]:font-semibold
            "
          >
            {children}
          </motion.div>
        </div>
      </section>

      <Footer />
    </div>
  );
}
