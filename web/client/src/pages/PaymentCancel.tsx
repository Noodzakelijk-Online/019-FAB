import { motion } from "framer-motion";
import { XCircle, ArrowLeft } from "lucide-react";
import { Button } from "@/components/ui/button";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
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

export default function PaymentCancel() {
  const { t } = useLanguage();

  return (
    <div className="min-h-screen bg-warm-white">
      <Navbar />

      <section className="pt-32 pb-20 lg:pt-40 lg:pb-28">
        <div className="container">
          <motion.div
            className="max-w-2xl mx-auto text-center"
            initial="hidden"
            animate="visible"
            variants={fadeUp}
          >
            <div className="w-20 h-20 rounded-full bg-sand flex items-center justify-center mx-auto mb-6">
              <XCircle className="w-10 h-10 text-charcoal-light" />
            </div>
            <h1 className="text-3xl lg:text-4xl text-charcoal mb-4">
              {t("payment.cancel.title")}
            </h1>
            <p className="text-lg text-charcoal-light leading-relaxed mb-8">
              {t("payment.cancel.desc")}
            </p>
            <div className="flex flex-wrap justify-center gap-4">
              <Link href="/">
                <Button
                  size="lg"
                  className="bg-teal hover:bg-teal-light text-white px-8 py-6 text-base rounded-xl"
                >
                  <ArrowLeft className="mr-2 w-5 h-5" />
                  {t("payment.cancel.cta")}
                </Button>
              </Link>
            </div>
          </motion.div>
        </div>
      </section>

      <Footer />
    </div>
  );
}
