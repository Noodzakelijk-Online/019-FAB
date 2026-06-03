/**
 * FAB FAQ Page — "Nordic Clarity" Design
 * Scandinavian Minimalism meets Healthcare Trust
 * Palette: Deep Teal, Warm Sand, Soft Sage, Charcoal on Warm White
 * Typography: DM Serif Display (display) + DM Sans (body)
 */

import { useState, useMemo } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  ArrowRight,
  ChevronDown,
  CreditCard,
  HelpCircle,
  Layers,
  Mail,
  MessageSquare,
  Monitor,
  Search,
  Shield,
  Sparkles,
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

const stagger = {
  visible: { transition: { staggerChildren: 0.1 } },
};

/* ─── Bilingual FAQ Data ─── */

type BiText = { en: string; nl: string };

type FAQItem = {
  question: BiText;
  answer: BiText;
};

type FAQCategory = {
  id: string;
  labelKey: string;
  descKey: string;
  icon: React.ElementType;
  items: FAQItem[];
};

const faqCategories: FAQCategory[] = [
  {
    id: "general",
    labelKey: "faq.cat.general",
    descKey: "faq.cat.general.desc",
    icon: HelpCircle,
    items: [
      {
        question: { en: "What is FAB?", nl: "Wat is FAB?" },
        answer: {
          en: "FAB (Fully Automated Bookkeeping) is a financial orchestration platform that brings structure and clarity to your finances. It connects all your existing financial tools — mijngeldzaken.nl, WaveApps, SVB, and your bank accounts — into one unified, synchronized system. FAB automatically extracts financial data from scattered sources like WhatsApp, Gmail, and Google Drive, categorizes it, and routes it to the correct platform. It is specifically designed for individuals in the Netherlands managing disability and chronic illness-related finances.",
          nl: "FAB (Fully Automated Bookkeeping) is een financieel orkestratieplatform dat structuur en helderheid brengt in je financiën. Het verbindt al je bestaande financiële tools — mijngeldzaken.nl, WaveApps, SVB en je bankrekeningen — in één uniform, gesynchroniseerd systeem. FAB extraheert automatisch financiële gegevens uit verspreide bronnen zoals WhatsApp, Gmail en Google Drive, categoriseert ze en routeert ze naar het juiste platform. Het is specifiek ontworpen voor mensen in Nederland die financiën beheren gerelateerd aan een beperking of chronische ziekte.",
        },
      },
      {
        question: { en: "Who is FAB designed for?", nl: "Voor wie is FAB ontworpen?" },
        answer: {
          en: "FAB is designed for individuals in the Netherlands who manage complex financial situations due to disability or chronic illness. This includes PGB (Persoonsgebonden Budget) holders, Wajong recipients, WIA benefit recipients, and anyone managing earmarked healthcare funds alongside household finances and side-hustle income. Caregivers managing finances on behalf of a loved one can also benefit from FAB.",
          nl: "FAB is ontworpen voor mensen in Nederland die complexe financiële situaties beheren vanwege een beperking of chronische ziekte. Dit omvat PGB-houders, Wajong-ontvangers, WIA-ontvangers en iedereen die geoormerkte zorgfondsen beheert naast huishoudelijke financiën en bijverdiensten. Mantelzorgers die financiën beheren namens een dierbare kunnen ook profiteren van FAB.",
        },
      },
      {
        question: { en: "Does FAB replace my existing financial tools?", nl: "Vervangt FAB mijn bestaande financiële tools?" },
        answer: {
          en: "No. FAB does not replace tools like mijngeldzaken.nl, WaveApps, or the SVB portal. Instead, it acts as an intelligent orchestration layer that sits above these platforms. It connects them, synchronizes data between them, and provides you with a single unified view of your complete financial picture.",
          nl: "Nee. FAB vervangt tools zoals mijngeldzaken.nl, WaveApps of het SVB-portaal niet. In plaats daarvan fungeert het als een intelligente orkestratielaag die boven deze platforms zit. Het verbindt ze, synchroniseert gegevens ertussen en biedt je één uniform overzicht van je volledige financiële beeld.",
        },
      },
      {
        question: { en: "How much time does FAB require from me each week?", nl: "Hoeveel tijd kost FAB me per week?" },
        answer: {
          en: "Less than 10 minutes per week. FAB's AI handles the heavy lifting — scanning, categorizing, routing, and even requesting missing information from vendors. You only review transactions where the AI is uncertain.",
          nl: "Minder dan 10 minuten per week. FAB's AI doet het zware werk — scannen, categoriseren, routeren en zelfs ontbrekende informatie opvragen bij leveranciers. Je beoordeelt alleen transacties waar de AI onzeker over is.",
        },
      },
      {
        question: { en: "Is FAB available on mobile devices?", nl: "Is FAB beschikbaar op mobiele apparaten?" },
        answer: {
          en: "Yes. FAB is available on both desktop and mobile with full feature parity. The mobile app provides the same complete functionality as the desktop version.",
          nl: "Ja. FAB is beschikbaar op zowel desktop als mobiel met volledige functionaliteit. De mobiele app biedt dezelfde complete functionaliteit als de desktopversie.",
        },
      },
      {
        question: { en: "Can FAB work offline?", nl: "Kan FAB offline werken?" },
        answer: {
          en: "Yes. FAB is built with an offline-first architecture. Core features like document scanning, OCR processing, and transaction categorization work without an internet connection. Actions requiring connectivity are queued and executed when you reconnect.",
          nl: "Ja. FAB is gebouwd met een offline-first architectuur. Kernfuncties zoals documentscannen, OCR-verwerking en transactiecategorisatie werken zonder internetverbinding. Acties die connectiviteit vereisen worden in de wachtrij geplaatst en uitgevoerd wanneer je weer verbinding maakt.",
        },
      },
    ],
  },
  {
    id: "privacy",
    labelKey: "faq.cat.privacy",
    descKey: "faq.cat.privacy.desc",
    icon: Shield,
    items: [
      {
        question: { en: "Where is my data stored?", nl: "Waar worden mijn gegevens opgeslagen?" },
        answer: {
          en: "Your data is stored locally on your own device. FAB is a locally-installed, privacy-first application, which means your financial records, personal information, and documents never leave your computer or phone unless you explicitly choose to sync.",
          nl: "Je gegevens worden lokaal op je eigen apparaat opgeslagen. FAB is een lokaal geïnstalleerde, privacy-first applicatie, wat betekent dat je financiële gegevens, persoonlijke informatie en documenten nooit je computer of telefoon verlaten tenzij je expliciet kiest voor synchronisatie.",
        },
      },
      {
        question: { en: "Is my data encrypted?", nl: "Zijn mijn gegevens versleuteld?" },
        answer: {
          en: "Yes. FAB uses end-to-end encryption for all data, both at rest (stored on your device) and in transit (when syncing with platforms). We use industry-standard AES-256 encryption protocols.",
          nl: "Ja. FAB gebruikt end-to-end encryptie voor alle gegevens, zowel in rust (opgeslagen op je apparaat) als tijdens transport (bij synchronisatie met platforms). We gebruiken industriestandaard AES-256 encryptieprotocollen.",
        },
      },
      {
        question: { en: "Does FAB comply with GDPR?", nl: "Voldoet FAB aan de AVG?" },
        answer: {
          en: "Absolutely. FAB is fully GDPR-compliant. You have complete control over your data, including the right to access, export, and permanently delete all your information at any time.",
          nl: "Absoluut. FAB is volledig AVG-conform. Je hebt volledige controle over je gegevens, inclusief het recht om al je informatie op elk moment in te zien, te exporteren en permanent te verwijderen.",
        },
      },
      {
        question: { en: "What authentication methods does FAB support?", nl: "Welke authenticatiemethoden ondersteunt FAB?" },
        answer: {
          en: "FAB supports biometric login (fingerprint and face recognition), two-factor authentication (2FA), and traditional password-based login. We strongly recommend enabling both biometric login and 2FA for maximum security.",
          nl: "FAB ondersteunt biometrische login (vingerafdruk en gezichtsherkenning), tweefactorauthenticatie (2FA) en traditionele wachtwoordgebaseerde login. We raden sterk aan om zowel biometrische login als 2FA in te schakelen voor maximale beveiliging.",
        },
      },
      {
        question: { en: "Can someone else access my FAB account?", nl: "Kan iemand anders toegang krijgen tot mijn FAB-account?" },
        answer: {
          en: "Only if you explicitly grant them access. FAB includes a trusted person feature that allows you to give a family member or caregiver read-only access to your dashboard. You can revoke this access at any time.",
          nl: "Alleen als je hen expliciet toegang verleent. FAB bevat een vertrouwenspersoon-functie waarmee je een familielid of mantelzorger alleen-lezen toegang kunt geven tot je dashboard. Je kunt deze toegang op elk moment intrekken.",
        },
      },
      {
        question: { en: "Which Dutch regulations does FAB comply with?", nl: "Aan welke Nederlandse regelgeving voldoet FAB?" },
        answer: {
          en: "FAB complies with AFM financial services regulations, AP data protection regulations (Dutch GDPR), SVB-specific PGB administration rules, and Dutch tax regulations for deductible healthcare expenses.",
          nl: "FAB voldoet aan AFM-regelgeving voor financiële diensten, AP-regelgeving voor gegevensbescherming (Nederlandse AVG), SVB-specifieke PGB-administratieregels en Nederlandse belastingregels voor aftrekbare zorgkosten.",
        },
      },
      {
        question: { en: "Does FAB use my data for anything other than my financial management?", nl: "Gebruikt FAB mijn gegevens voor iets anders dan mijn financieel beheer?" },
        answer: {
          en: "FAB may use anonymized, aggregated data — with no personally identifiable information — to publish reports on the true cost of disability. You can opt out at any time. Your individual data is never sold or used for advertising.",
          nl: "FAB kan geanonimiseerde, geaggregeerde gegevens — zonder persoonlijk identificeerbare informatie — gebruiken om rapporten te publiceren over de werkelijke kosten van een beperking. Je kunt je op elk moment afmelden. Je individuele gegevens worden nooit verkocht of gebruikt voor reclame.",
        },
      },
    ],
  },
  {
    id: "pgb",
    labelKey: "faq.cat.pgb",
    descKey: "faq.cat.pgb.desc",
    icon: Layers,
    items: [
      {
        question: { en: "What is PGB and how does FAB help manage it?", nl: "Wat is PGB en hoe helpt FAB bij het beheer ervan?" },
        answer: {
          en: "PGB (Persoonsgebonden Budget) is a personal healthcare budget provided by the Dutch government. FAB automates the entire PGB management process — tracking funds, ensuring correct categorization, and maintaining SVB documentation.",
          nl: "PGB (Persoonsgebonden Budget) is een persoonlijk zorgbudget van de Nederlandse overheid. FAB automatiseert het volledige PGB-beheerproces — fondsen bijhouden, correcte categorisatie waarborgen en SVB-documentatie onderhouden.",
        },
      },
      {
        question: { en: "Does FAB integrate directly with the SVB?", nl: "Integreert FAB direct met de SVB?" },
        answer: {
          en: "Yes. FAB integrates with the SVB PGB portal to synchronize your budget data, payment records, and care worker contracts. This allows complete tracking of every euro in your PGB.",
          nl: "Ja. FAB integreert met het SVB PGB-portaal om je budgetgegevens, betalingsoverzichten en zorgverlenercontracten te synchroniseren. Dit maakt volledige tracking van elke euro in je PGB mogelijk.",
        },
      },
      {
        question: { en: "How does FAB handle earmarked healthcare funds?", nl: "Hoe gaat FAB om met geoormerkte zorgfondsen?" },
        answer: {
          en: "FAB includes a sophisticated source mapping system for earmarked funds. You define which income sources connect to which platforms and categories, and FAB automatically enforces these mappings to prevent mixing earmarked and general funds.",
          nl: "FAB bevat een geavanceerd bronmappingsysteem voor geoormerkte fondsen. Je definieert welke inkomstenbronnen verbonden zijn met welke platforms en categorieën, en FAB handhaaft deze mappings automatisch om vermenging van geoormerkte en algemene fondsen te voorkomen.",
        },
      },
      {
        question: { en: "Can FAB help with WLZ and WMO care arrangements?", nl: "Kan FAB helpen met WLZ- en WMO-zorgregelingen?" },
        answer: {
          en: "Yes. FAB supports the full spectrum of Dutch long-term care arrangements, including WLZ (Wet langdurige zorg) and WMO (Wet maatschappelijke ondersteuning), tracking the specific rules for each funding stream.",
          nl: "Ja. FAB ondersteunt het volledige spectrum van Nederlandse langdurige zorgregelingen, inclusief WLZ (Wet langdurige zorg) en WMO (Wet maatschappelijke ondersteuning), en volgt de specifieke regels voor elke financieringsstroom.",
        },
      },
      {
        question: { en: "Does FAB support Wajong and WIA benefits?", nl: "Ondersteunt FAB Wajong- en WIA-uitkeringen?" },
        answer: {
          en: "Yes. FAB tracks and manages Wajong benefits (for young people with long-term illness or disability) and WIA benefits (work disability insurance). Each benefit type is tracked separately with its own rules.",
          nl: "Ja. FAB volgt en beheert Wajong-uitkeringen (voor jongeren met langdurige ziekte of beperking) en WIA-uitkeringen (arbeidsongeschiktheidsverzekering). Elk uitkeringstype wordt apart gevolgd met eigen regels.",
        },
      },
      {
        question: { en: "Can FAB generate reports for SVB accountability?", nl: "Kan FAB rapporten genereren voor SVB-verantwoording?" },
        answer: {
          en: "Yes. FAB generates comprehensive annual summary reports suitable for SVB accountability and tax filing, with detailed breakdowns of all PGB-related income and expenditures in universally accepted export formats.",
          nl: "Ja. FAB genereert uitgebreide jaarlijkse samenvattingsrapporten geschikt voor SVB-verantwoording en belastingaangifte, met gedetailleerde overzichten van alle PGB-gerelateerde inkomsten en uitgaven in universeel geaccepteerde exportformaten.",
        },
      },
    ],
  },
  {
    id: "pricing",
    labelKey: "faq.cat.pricing",
    descKey: "faq.cat.pricing.desc",
    icon: CreditCard,
    items: [
      {
        question: { en: "How does FAB's pricing work?", nl: "Hoe werkt de prijsstelling van FAB?" },
        answer: {
          en: "FAB uses a transparent, resource-usage based pricing model. Your cost equals the resources you use, multiplied by 2.5. You only pay for what you actually use — no fixed monthly fees or hidden charges.",
          nl: "FAB gebruikt een transparant, op gebruik gebaseerd prijsmodel. Je kosten zijn gelijk aan de resources die je gebruikt, vermenigvuldigd met 2,5. Je betaalt alleen voor wat je daadwerkelijk gebruikt — geen vaste maandelijkse kosten of verborgen kosten.",
        },
      },
      {
        question: { en: "Is there a free tier?", nl: "Is er een gratis versie?" },
        answer: {
          en: "Yes. FAB offers a generous free tier that allows you to process up to 3 transactions per week at no cost. This lets you experience FAB's core value without any financial commitment.",
          nl: "Ja. FAB biedt een ruime gratis versie waarmee je tot 3 transacties per week kunt verwerken zonder kosten. Zo kun je de kernwaarde van FAB ervaren zonder financiële verplichting.",
        },
      },
      {
        question: { en: "Can I set a spending cap?", nl: "Kan ik een bestedingslimiet instellen?" },
        answer: {
          en: "Yes. FAB includes a configurable spending cap. You set your own monthly limit, and when reached, FAB stops processing new transactions until the next billing period.",
          nl: "Ja. FAB bevat een instelbare bestedingslimiet. Je stelt je eigen maandelijkse limiet in, en wanneer deze bereikt is, stopt FAB met het verwerken van nieuwe transacties tot de volgende factureringsperiode.",
        },
      },
      {
        question: { en: "Can I see my current usage in real time?", nl: "Kan ik mijn huidige gebruik in real-time zien?" },
        answer: {
          en: "Yes. FAB includes a real-time cost dashboard showing your current resource usage, associated cost, and proximity to your spending cap.",
          nl: "Ja. FAB bevat een real-time kostendashboard dat je huidige resourcegebruik, bijbehorende kosten en nabijheid tot je bestedingslimiet toont.",
        },
      },
      {
        question: { en: "How am I billed?", nl: "Hoe word ik gefactureerd?" },
        answer: {
          en: "FAB generates a monthly invoice based on your resource usage with a detailed breakdown. Payment is processed via iDEAL, the standard Dutch payment method.",
          nl: "FAB genereert een maandelijkse factuur op basis van je resourcegebruik met een gedetailleerd overzicht. Betaling wordt verwerkt via iDEAL, de standaard Nederlandse betaalmethode.",
        },
      },
      {
        question: { en: "What happens if I stop using FAB?", nl: "Wat gebeurt er als ik stop met FAB?" },
        answer: {
          en: "You simply stop incurring charges — no cancellation fees or lock-in periods. Your data remains on your local device and you can export everything at any time.",
          nl: "Je stopt simpelweg met kosten maken — geen annuleringskosten of lock-in periodes. Je gegevens blijven op je lokale apparaat en je kunt alles op elk moment exporteren.",
        },
      },
    ],
  },
  {
    id: "autonomous",
    labelKey: "faq.cat.autonomous",
    descKey: "faq.cat.autonomous.desc",
    icon: Sparkles,
    items: [
      {
        question: { en: "What does 'autonomous data completion' mean?", nl: "Wat betekent 'autonome gegevensaanvulling'?" },
        answer: {
          en: "Autonomous data completion is FAB's ability to identify missing information in your financial records and proactively fix it by crafting professional email requests to the relevant party. Once the response arrives, FAB parses it and updates the entry automatically.",
          nl: "Autonome gegevensaanvulling is FAB's vermogen om ontbrekende informatie in je financiële administratie te identificeren en proactief op te lossen door professionele e-mailverzoeken op te stellen naar de relevante partij. Wanneer het antwoord binnenkomt, parseert FAB het en werkt de vermelding automatisch bij.",
        },
      },
      {
        question: { en: "Does FAB send emails without my permission?", nl: "Verstuurt FAB e-mails zonder mijn toestemming?" },
        answer: {
          en: "No. FAB always requires your approval before sending any email on your behalf. Drafts are placed in your review queue for you to approve, edit, or reject.",
          nl: "Nee. FAB vereist altijd je goedkeuring voordat het een e-mail namens jou verstuurt. Concepten worden in je beoordelingswachtrij geplaatst zodat je ze kunt goedkeuren, bewerken of afwijzen.",
        },
      },
      {
        question: { en: "What happens if a vendor does not respond?", nl: "Wat gebeurt er als een leverancier niet reageert?" },
        answer: {
          en: "FAB includes a configurable follow-up system with a waiting period and maximum attempts. Once the limit is reached, FAB flags the entry for your manual review.",
          nl: "FAB bevat een configureerbaar opvolgsysteem met een wachttijd en maximaal aantal pogingen. Wanneer de limiet bereikt is, markeert FAB de vermelding voor je handmatige beoordeling.",
        },
      },
      {
        question: { en: "How does FAB decide what to flag for my review?", nl: "Hoe bepaalt FAB wat gemarkeerd wordt voor mijn beoordeling?" },
        answer: {
          en: "FAB uses a confidence scoring system powered by AI. If any parameter falls below the confidence threshold, the transaction is flagged. Over time, FAB learns from your corrections and becomes increasingly accurate.",
          nl: "FAB gebruikt een op AI gebaseerd vertrouwensscoresysteem. Als een parameter onder de vertrouwensdrempel valt, wordt de transactie gemarkeerd. Na verloop van tijd leert FAB van je correcties en wordt het steeds nauwkeuriger.",
        },
      },
      {
        question: { en: "Does FAB automatically delete documents from my inbox?", nl: "Verwijdert FAB automatisch documenten uit mijn inbox?" },
        answer: {
          en: "No. FAB never automatically deletes documents from your WhatsApp, Gmail, or Google Drive. After processing, FAB stores a copy locally and routes the data — the original remains in its source location.",
          nl: "Nee. FAB verwijdert nooit automatisch documenten uit je WhatsApp, Gmail of Google Drive. Na verwerking slaat FAB een kopie lokaal op en routeert de gegevens — het origineel blijft op de bronlocatie.",
        },
      },
      {
        question: { en: "How often does FAB scan for new data?", nl: "Hoe vaak scant FAB naar nieuwe gegevens?" },
        answer: {
          en: "FAB provides user-configurable frequency sliders. Platform synchronization and source scanning run hourly by default. Response checking runs every 5 minutes by default. All frequencies are adjustable.",
          nl: "FAB biedt door de gebruiker instelbare frequentieschuifregelaars. Platformsynchronisatie en bronscannen draaien standaard elk uur. Antwoordcontrole draait standaard elke 5 minuten. Alle frequenties zijn aanpasbaar.",
        },
      },
    ],
  },
  {
    id: "technical",
    labelKey: "faq.cat.technical",
    descKey: "faq.cat.technical.desc",
    icon: Monitor,
    items: [
      {
        question: { en: "How do I set up FAB?", nl: "Hoe stel ik FAB in?" },
        answer: {
          en: "FAB includes an onboarding wizard that guides you through connecting accounts, setting sync frequencies, and configuring your spending cap. Setup typically takes 15-20 minutes.",
          nl: "FAB bevat een onboarding-wizard die je begeleidt bij het verbinden van accounts, het instellen van synchronisatiefrequenties en het configureren van je bestedingslimiet. De installatie duurt doorgaans 15-20 minuten.",
        },
      },
      {
        question: { en: "Does FAB support multiple bank accounts?", nl: "Ondersteunt FAB meerdere bankrekeningen?" },
        answer: {
          en: "Yes. FAB supports connecting multiple bank accounts, essential for managing earmarked healthcare funds that may flow through different accounts. Each account is tracked separately.",
          nl: "Ja. FAB ondersteunt het verbinden van meerdere bankrekeningen, essentieel voor het beheren van geoormerkte zorgfondsen die via verschillende rekeningen kunnen lopen. Elke rekening wordt apart gevolgd.",
        },
      },
      {
        question: { en: "Can FAB handle cash transactions?", nl: "Kan FAB contante transacties verwerken?" },
        answer: {
          en: "Yes. You can manually input cash transactions or take a photo of a receipt — FAB uses OCR to automatically extract the details and categorize it.",
          nl: "Ja. Je kunt contante transacties handmatig invoeren of een foto van een bon maken — FAB gebruikt OCR om automatisch de details te extraheren en te categoriseren.",
        },
      },
      {
        question: { en: "Can I export my data from FAB?", nl: "Kan ik mijn gegevens exporteren uit FAB?" },
        answer: {
          en: "Yes. FAB allows you to export your complete financial data at any time in universally accepted formats. Your data belongs to you.",
          nl: "Ja. FAB stelt je in staat om je volledige financiële gegevens op elk moment te exporteren in universeel geaccepteerde formaten. Je gegevens zijn van jou.",
        },
      },
      {
        question: { en: "Does FAB offer customer support?", nl: "Biedt FAB klantenondersteuning?" },
        answer: {
          en: "Yes. FAB provides support through email and in-app chat, plus video tutorials and in-app guidance. Our team understands the unique challenges of managing disability-related finances.",
          nl: "Ja. FAB biedt ondersteuning via e-mail en in-app chat, plus videotutorials en in-app begeleiding. Ons team begrijpt de unieke uitdagingen van het beheren van financiën gerelateerd aan een beperking.",
        },
      },
      {
        question: { en: "Will FAB be available outside the Netherlands?", nl: "Komt FAB beschikbaar buiten Nederland?" },
        answer: {
          en: "FAB is initially launching in the Netherlands. Our long-term vision includes expansion to countries with similar personal budget systems, such as the UK, Germany, and Australia.",
          nl: "FAB lanceert eerst in Nederland. Onze langetermijnvisie omvat uitbreiding naar landen met vergelijkbare persoonsgebonden budgetsystemen, zoals het VK, Duitsland en Australië.",
        },
      },
    ],
  },
];

/* ─── Accordion Item Component ─── */

function AccordionItem({
  question,
  answer,
  isOpen,
  onToggle,
}: {
  question: string;
  answer: string;
  isOpen: boolean;
  onToggle: () => void;
}) {
  return (
    <div
      className={`border rounded-xl transition-all duration-300 ${
        isOpen
          ? "border-teal/30 bg-white shadow-sm"
          : "border-sand-dark/10 bg-white/60 hover:border-teal/15 hover:bg-white"
      }`}
    >
      <button
        onClick={onToggle}
        className="w-full flex items-center justify-between gap-4 p-5 text-left"
        aria-expanded={isOpen}
      >
        <span
          className={`font-sans font-medium text-[0.95rem] leading-snug transition-colors duration-200 ${
            isOpen ? "text-teal" : "text-charcoal"
          }`}
        >
          {question}
        </span>
        <motion.div
          animate={{ rotate: isOpen ? 180 : 0 }}
          transition={{ duration: 0.3, ease: [0.25, 0.1, 0.25, 1] }}
          className="shrink-0"
        >
          <ChevronDown
            className={`w-5 h-5 transition-colors duration-200 ${
              isOpen ? "text-teal" : "text-charcoal-light"
            }`}
          />
        </motion.div>
      </button>
      <AnimatePresence initial={false}>
        {isOpen && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.35, ease: [0.25, 0.1, 0.25, 1] }}
            className="overflow-hidden"
          >
            <div className="px-5 pb-5 pt-0">
              <div className="border-t border-sand-dark/10 pt-4">
                <p className="text-charcoal-light text-sm leading-relaxed">
                  {answer}
                </p>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

/* ─── Main FAQ Page ─── */

export default function FAQ() {
  const { t, lang } = useLanguage();
  const [activeCategory, setActiveCategory] = useState("general");
  const [openItems, setOpenItems] = useState<Record<string, boolean>>({});
  const [searchQuery, setSearchQuery] = useState("");
  const [waitlistOpen, setWaitlistOpen] = useState(false);

  const toggleItem = (key: string) => {
    setOpenItems((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  const currentCategory = faqCategories.find((c) => c.id === activeCategory);

  // Filter FAQ items based on search query
  const filteredCategories = useMemo(() => {
    if (!searchQuery.trim()) return null;
    const q = searchQuery.toLowerCase();
    return faqCategories
      .map((cat) => {
        const catLabel = t(cat.labelKey).toLowerCase();
        const catDesc = t(cat.descKey).toLowerCase();
        const categoryMatch = catLabel.includes(q) || catDesc.includes(q);
        return {
          ...cat,
          items: categoryMatch
            ? cat.items
            : cat.items.filter(
                (item) =>
                  item.question[lang].toLowerCase().includes(q) ||
                  item.answer[lang].toLowerCase().includes(q)
              ),
        };
      })
      .filter((cat) => cat.items.length > 0);
  }, [searchQuery, lang, t]);

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
            initial="hidden"
            animate="visible"
            variants={stagger}
            className="max-w-3xl mx-auto text-center"
          >
            <motion.div variants={fadeUp} className="mb-5">
              <span className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-sage-light text-teal text-sm font-medium tracking-wide">
                <HelpCircle className="w-4 h-4" />
                {t("faq.badge")}
              </span>
            </motion.div>
            <motion.h1
              variants={fadeUp}
              className="font-serif text-4xl sm:text-5xl lg:text-[3.25rem] leading-[1.1] tracking-tight text-charcoal mb-6"
            >
              {t("faq.title1")}{" "}
              <span className="text-teal">{t("faq.titleHighlight")}</span>
            </motion.h1>
            <motion.p
              variants={fadeUp}
              className="text-lg text-charcoal-light max-w-2xl mx-auto font-light leading-relaxed mb-10"
            >
              {t("faq.desc")}
            </motion.p>

            {/* Search Bar */}
            <motion.div variants={fadeUp} className="max-w-xl mx-auto">
              <div className="relative">
                <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-charcoal-light/60" />
                <input
                  type="text"
                  placeholder={t("faq.search")}
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full pl-12 pr-4 py-3.5 rounded-xl border border-sand-dark/15 bg-white text-charcoal placeholder:text-charcoal-light/50 focus:outline-none focus:ring-2 focus:ring-teal/20 focus:border-teal/30 transition-all duration-200 text-sm"
                />
                {searchQuery && (
                  <button
                    onClick={() => setSearchQuery("")}
                    className="absolute right-4 top-1/2 -translate-y-1/2 text-charcoal-light/60 hover:text-charcoal transition-colors text-sm"
                  >
                    {t("faq.clear")}
                  </button>
                )}
              </div>
            </motion.div>
          </motion.div>
        </div>
      </section>

      {/* ═══════════════════════════════════════════════════════════════
          FAQ CONTENT — Search Results Mode
      ═══════════════════════════════════════════════════════════════ */}
      {filteredCategories && (
        <section className="pb-20">
          <div className="container max-w-4xl">
            {filteredCategories.length === 0 ? (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="text-center py-16"
              >
                <div className="w-16 h-16 rounded-2xl bg-sand/50 flex items-center justify-center mx-auto mb-5">
                  <Search className="w-8 h-8 text-charcoal-light/40" />
                </div>
                <h3 className="font-serif text-xl text-charcoal mb-2">
                  {t("faq.noResults")}
                </h3>
                <p className="text-charcoal-light text-sm mb-6">
                  {t("faq.noResultsDesc")}
                </p>
                <Link href="/contact">
                  <Button className="rounded-xl bg-teal hover:bg-teal-light text-white px-6">
                    <MessageSquare className="w-4 h-4 mr-2" />
                    {t("faq.askDirectly")}
                  </Button>
                </Link>
              </motion.div>
            ) : (
              <div className="space-y-10">
                {filteredCategories.map((cat) => (
                  <motion.div
                    key={cat.id}
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                  >
                    <div className="flex items-center gap-3 mb-4">
                      <div className="w-8 h-8 rounded-lg bg-sage-light flex items-center justify-center">
                        <cat.icon className="w-4 h-4 text-teal" />
                      </div>
                      <h3 className="font-serif text-lg text-charcoal">
                        {t(cat.labelKey)}
                      </h3>
                      <span className="text-xs text-charcoal-light bg-sand/50 px-2 py-0.5 rounded-full">
                        {cat.items.length} {cat.items.length === 1 ? t("faq.result") : t("faq.results")}
                      </span>
                    </div>
                    <div className="space-y-3">
                      {cat.items.map((item, idx) => (
                        <AccordionItem
                          key={`search-${cat.id}-${idx}`}
                          question={item.question[lang]}
                          answer={item.answer[lang]}
                          isOpen={!!openItems[`search-${cat.id}-${idx}`]}
                          onToggle={() => toggleItem(`search-${cat.id}-${idx}`)}
                        />
                      ))}
                    </div>
                  </motion.div>
                ))}
              </div>
            )}
          </div>
        </section>
      )}

      {/* ═══════════════════════════════════════════════════════════════
          FAQ CONTENT — Category Browse Mode
      ═══════════════════════════════════════════════════════════════ */}
      {!filteredCategories && (
        <section className="pb-20">
          <div className="container">
            <div className="grid lg:grid-cols-[280px_1fr] gap-10 lg:gap-14">
              {/* Sidebar — Category Navigation */}
              <motion.aside
                initial="hidden"
                animate="visible"
                variants={stagger}
                className="lg:sticky lg:top-28 lg:self-start"
              >
                <motion.p
                  variants={fadeUp}
                  className="text-xs font-semibold uppercase tracking-widest text-charcoal-light mb-4"
                >
                  {t("faq.categories")}
                </motion.p>
                <nav className="space-y-1.5">
                  {faqCategories.map((cat) => (
                    <motion.button
                      key={cat.id}
                      variants={fadeUp}
                      onClick={() => setActiveCategory(cat.id)}
                      className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl text-left transition-all duration-200 ${
                        activeCategory === cat.id
                          ? "bg-teal/8 border border-teal/15 text-teal"
                          : "text-charcoal-light hover:bg-sand/40 hover:text-charcoal border border-transparent"
                      }`}
                    >
                      <cat.icon
                        className={`w-4.5 h-4.5 shrink-0 ${
                          activeCategory === cat.id
                            ? "text-teal"
                            : "text-charcoal-light/60"
                        }`}
                      />
                      <div>
                        <span className="text-sm font-medium block leading-tight">
                          {t(cat.labelKey)}
                        </span>
                        <span className="text-xs text-charcoal-light/60 leading-tight">
                          {cat.items.length} {t("faq.questions")}
                        </span>
                      </div>
                    </motion.button>
                  ))}
                </nav>

                {/* Quick Help Card */}
                <motion.div
                  variants={fadeUp}
                  className="mt-8 p-5 rounded-2xl bg-gradient-to-br from-teal/5 to-sage-light/30 border border-teal/10"
                >
                  <Mail className="w-6 h-6 text-teal mb-3" />
                  <h4 className="font-serif text-base text-charcoal mb-2">
                    {t("faq.cta.title")}
                  </h4>
                  <p className="text-xs text-charcoal-light leading-relaxed mb-4">
                    {t("faq.sidebarDesc")}
                  </p>
                  <Link href="/contact">
                    <Button
                      size="sm"
                      className="w-full rounded-lg bg-teal hover:bg-teal-light text-white text-xs"
                    >
                      {t("faq.contactUs")}
                      <ArrowRight className="w-3.5 h-3.5 ml-1.5" />
                    </Button>
                  </Link>
                </motion.div>
              </motion.aside>

              {/* Main Content — FAQ Accordion */}
              <motion.div
                key={activeCategory}
                initial="hidden"
                animate="visible"
                variants={stagger}
              >
                {currentCategory && (
                  <>
                    <motion.div variants={fadeUp} className="mb-8">
                      <div className="flex items-center gap-3 mb-2">
                        <div className="w-10 h-10 rounded-xl bg-sage-light flex items-center justify-center">
                          <currentCategory.icon className="w-5 h-5 text-teal" />
                        </div>
                        <div>
                          <h2 className="font-serif text-2xl text-charcoal">
                            {t(currentCategory.labelKey)}
                          </h2>
                          <p className="text-sm text-charcoal-light">
                            {t(currentCategory.descKey)}
                          </p>
                        </div>
                      </div>
                    </motion.div>

                    <div className="space-y-3">
                      {currentCategory.items.map((item, idx) => (
                        <motion.div key={idx} variants={fadeUp}>
                          <AccordionItem
                            question={item.question[lang]}
                            answer={item.answer[lang]}
                            isOpen={
                              !!openItems[`${activeCategory}-${idx}`]
                            }
                            onToggle={() =>
                              toggleItem(`${activeCategory}-${idx}`)
                            }
                          />
                        </motion.div>
                      ))}
                    </div>
                  </>
                )}
              </motion.div>
            </div>
          </div>
        </section>
      )}

      {/* ═══════════════════════════════════════════════════════════════
          BOTTOM CTA
      ═══════════════════════════════════════════════════════════════ */}
      <section className="py-20 bg-sand/30">
        <div className="container">
          <motion.div
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true, margin: "-80px" }}
            variants={stagger}
            className="max-w-2xl mx-auto text-center"
          >
            <motion.h2
              variants={fadeUp}
              className="font-serif text-3xl sm:text-4xl text-charcoal mb-5 leading-tight"
            >
              {t("cta.title")}
            </motion.h2>
            <motion.p
              variants={fadeUp}
              className="text-charcoal-light leading-relaxed mb-8"
            >
              {t("cta.desc")}
            </motion.p>
            <motion.div
              variants={fadeUp}
              className="flex flex-col sm:flex-row items-center justify-center gap-4"
            >
              <Button
                className="rounded-xl bg-teal hover:bg-teal-light text-white px-8 py-3 h-auto text-base"
                onClick={() => setWaitlistOpen(true)}
              >
                {t("cta.primary")}
                <ArrowRight className="w-4 h-4 ml-2" />
              </Button>
              <Link href="/contact">
                <Button
                  variant="outline"
                  className="rounded-xl border-teal/20 text-teal hover:bg-teal/5 px-8 py-3 h-auto text-base"
                >
                  <MessageSquare className="w-4 h-4 mr-2" />
                  {t("faq.cta.primary")}
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
