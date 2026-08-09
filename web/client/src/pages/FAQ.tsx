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
          en: "FAB (Fully Automated Bookkeeping) is a local-first financial operations platform. It accepts supported local, scanner, Gmail, Google Drive, and selected photo documents, extracts and validates bookkeeping data, and records every decision in an auditable local ledger. Wave delivery is capability and approval gated, while MijnGeldzaken uses a supervised master-ledger export.",
          nl: "FAB (Fully Automated Bookkeeping) is een lokaal financieel werkplatform. Het verwerkt ondersteunde lokale, scanner-, Gmail-, Google Drive- en geselecteerde fotodocumenten, extraheert en valideert boekhoudgegevens en legt elke beslissing vast in een controleerbaar lokaal grootboek. Wave-verwerking is afhankelijk van mogelijkheden en goedkeuring; MijnGeldzaken gebruikt een begeleide master-ledgerexport.",
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
          en: "No. FAB keeps its own auditable master ledger and uses capability-specific connectors. Wave supports verified reads and guarded delivery where the configured API or supervised executor allows it. MijnGeldzaken remains a supervised export, and direct SVB or PSD2 account changes are not currently available.",
          nl: "Nee. FAB houdt een eigen controleerbaar master ledger bij en gebruikt koppelingen op basis van hun werkelijke mogelijkheden. Wave ondersteunt geverifieerde leesacties en beveiligde verwerking waar de ingestelde API of begeleide executor dat toestaat. MijnGeldzaken blijft een begeleide export; directe SVB- of PSD2-accountwijzigingen zijn momenteel niet beschikbaar.",
        },
      },
      {
        question: { en: "How much time does FAB require from me each week?", nl: "Hoeveel tijd kost FAB me per week?" },
        answer: {
          en: "The required time depends on document quality, connector readiness, and the number of exceptions. FAB automates eligible local work and concentrates unresolved evidence, duplicates, and external approvals in review queues; it does not promise a fixed weekly time saving.",
          nl: "De benodigde tijd hangt af van de documentkwaliteit, gereedheid van koppelingen en het aantal uitzonderingen. FAB automatiseert geschikt lokaal werk en bundelt onopgelost bewijs, duplicaten en externe goedkeuringen in beoordelingswachtrijen; het belooft geen vaste wekelijkse tijdsbesparing.",
        },
      },
      {
        question: { en: "Is FAB available on mobile devices?", nl: "Is FAB beschikbaar op mobiele apparaten?" },
        answer: {
          en: "The operator dashboard is responsive and can be opened in a modern mobile browser when FAB is deployed through a secure authenticated endpoint. There is no separate native mobile app, and credential installation or provider setup is best completed on the Windows host.",
          nl: "Het operator-dashboard is responsief en kan in een moderne mobiele browser worden geopend wanneer FAB via een beveiligd en geauthenticeerd endpoint is geïmplementeerd. Er is geen aparte mobiele app; installatie van inloggegevens en providerinstellingen doe je het beste op de Windows-host.",
        },
      },
      {
        question: { en: "Can FAB work offline?", nl: "Kan FAB offline werken?" },
        answer: {
          en: "Local intake, OCR, validation, review, reporting, and ledger operations can run without internet after installation. Gmail, Drive, Wave, and other provider actions require connectivity and current authorization. FAB does not silently replay an external financial mutation merely because connectivity returns.",
          nl: "Lokale inname, OCR, validatie, beoordeling, rapportage en grootboekbewerkingen kunnen na installatie zonder internet werken. Gmail, Drive, Wave en andere provideracties vereisen verbinding en actuele autorisatie. FAB voert een externe financiële wijziging niet stilzwijgend opnieuw uit zodra de verbinding terugkeert.",
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
          en: "The authoritative operations ledger, diagnostics, and recovery metadata are stored on the configured FAB host. Source documents remain in their configured folders or provider sources unless an explicit, evidence-gated move is approved. Supported provider delivery transmits only the data required for that approved operation.",
          nl: "Het gezaghebbende operationele grootboek, diagnostiek en herstelmetadata staan op de ingestelde FAB-host. Brondocumenten blijven in hun ingestelde mappen of providerbronnen tenzij een expliciete, bewijsgebonden verplaatsing is goedgekeurd. Ondersteunde providerverwerking verstuurt alleen de gegevens die voor die goedgekeurde handeling nodig zijn.",
        },
      },
      {
        question: { en: "Is my data encrypted?", nl: "Zijn mijn gegevens versleuteld?" },
        answer: {
          en: "Supported provider credentials are protected locally, including Windows current-user protection for the Wave credential store, and provider traffic uses HTTPS. The financial ledger and source folders must also be protected with Windows account controls, BitLocker or equivalent disk encryption, and secured backups. FAB does not claim blanket end-to-end encryption for every local file.",
          nl: "Ondersteunde providerinloggegevens worden lokaal beschermd, waaronder Windows-beveiliging voor de huidige gebruiker bij Wave, en providerverkeer gebruikt HTTPS. Bescherm ook het financiële grootboek en de bronmappen met Windows-accountbeheer, BitLocker of gelijkwaardige schijfversleuteling en beveiligde back-ups. FAB claimt geen algemene end-to-endversleuteling voor elk lokaal bestand.",
        },
      },
      {
        question: { en: "Does FAB comply with GDPR?", nl: "Voldoet FAB aan de AVG?" },
        answer: {
          en: "FAB is designed for data minimization, local control, auditable processing, export, and explicit provider consent. Legal compliance still depends on how the operator configures retention, access, backups, provider agreements, and deletion procedures; the software alone cannot certify an organization as GDPR compliant.",
          nl: "FAB is ontworpen voor dataminimalisatie, lokale controle, controleerbare verwerking, export en expliciete providertoestemming. Juridische naleving hangt ook af van de ingestelde bewaartermijnen, toegang, back-ups, verwerkersafspraken en verwijderprocedures; de software alleen kan een organisatie niet AVG-conform verklaren.",
        },
      },
      {
        question: { en: "What authentication methods does FAB support?", nl: "Welke authenticatiemethoden ondersteunt FAB?" },
        answer: {
          en: "The local dashboard uses FAB session authentication, while the HAI operations interface requires a separate service token. Remote access must be placed behind an authenticated HTTPS gateway. Native biometric login and a built-in 2FA enrollment flow are not part of the current release.",
          nl: "Het lokale dashboard gebruikt FAB-sessieauthenticatie; de HAI-operationsinterface vereist een apart servicetoken. Plaats externe toegang achter een geauthenticeerde HTTPS-gateway. Eigen biometrisch inloggen en een ingebouwde 2FA-inschrijving maken geen deel uit van de huidige release.",
        },
      },
      {
        question: { en: "Can someone else access my FAB account?", nl: "Kan iemand anders toegang krijgen tot mijn FAB-account?" },
        answer: {
          en: "Do not share the Windows account, FAB session, provider credentials, or HAI service token. A dedicated trusted-person read-only role is not currently available; use operating-system access controls and an authenticated remote gateway if another person must be granted access.",
          nl: "Deel het Windows-account, de FAB-sessie, providerinloggegevens of het HAI-servicetoken niet. Een aparte alleen-lezenrol voor een vertrouwenspersoon is momenteel niet beschikbaar; gebruik besturingssysteemtoegang en een geauthenticeerde externe gateway als iemand anders toegang nodig heeft.",
        },
      },
      {
        question: { en: "Which Dutch regulations does FAB comply with?", nl: "Aan welke Nederlandse regelgeving voldoet FAB?" },
        answer: {
          en: "FAB provides evidence retention, audit trails, VAT-oriented fields, review gates, and export controls that can support Dutch administration. It does not provide legal, tax, AFM, AP, or SVB certification. A qualified adviser remains responsible for validating the configured workflow and every filing or declaration.",
          nl: "FAB biedt bewijsbewaring, auditlogs, btw-gerichte velden, beoordelingspoorten en exportcontroles die de Nederlandse administratie kunnen ondersteunen. Het levert geen juridische, fiscale, AFM-, AP- of SVB-certificering. Een bevoegde adviseur blijft verantwoordelijk voor validatie van de werkwijze en iedere aangifte of declaratie.",
        },
      },
      {
        question: { en: "Does FAB use my data for anything other than my financial management?", nl: "Gebruikt FAB mijn gegevens voor iets anders dan mijn financieel beheer?" },
        answer: {
          en: "The current local release does not aggregate or transmit population analytics and does not contain an advertising-data pipeline. Any future research use would require a separately documented purpose, explicit consent, governance, and a verified anonymization process.",
          nl: "De huidige lokale release verzamelt of verstuurt geen populatie-analyses en bevat geen advertentiedatapijplijn. Toekomstig onderzoeksgebruik vereist een apart vastgelegd doel, expliciete toestemming, governance en een geverifieerd anonimiseringsproces.",
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
          en: "PGB (Persoonsgebonden Budget) is a Dutch personal care budget. FAB can classify PGB-related documents and transactions, preserve evidence, and include them in local reports and exports. It does not currently submit declarations, contracts, or payments to SVB.",
          nl: "PGB (Persoonsgebonden Budget) is een Nederlands persoonsgebonden zorgbudget. FAB kan PGB-gerelateerde documenten en transacties classificeren, bewijs bewaren en opnemen in lokale rapporten en exports. Het dient momenteel geen declaraties, contracten of betalingen in bij de SVB.",
        },
      },
      {
        question: { en: "Does FAB integrate directly with the SVB?", nl: "Integreert FAB direct met de SVB?" },
        answer: {
          en: "No. The current release has no direct SVB portal connector. Supported SVB and PGB evidence can be imported into the local ledger for classification, reconciliation, and reporting, but portal data and contracts are not synchronized automatically.",
          nl: "Nee. De huidige release heeft geen directe koppeling met het SVB-portaal. Ondersteund SVB- en PGB-bewijs kan in het lokale grootboek worden geïmporteerd voor classificatie, afstemming en rapportage, maar portaalgegevens en contracten worden niet automatisch gesynchroniseerd.",
        },
      },
      {
        question: { en: "How does FAB handle earmarked healthcare funds?", nl: "Hoe gaat FAB om met geoormerkte zorgfondsen?" },
        answer: {
          en: "FAB preserves source, category, account, and evidence metadata so earmarked activity can be kept distinguishable in the local ledger. Operators must validate the mappings and review exceptions; FAB does not guarantee that configured rules prevent every form of fund mixing.",
          nl: "FAB bewaart bron-, categorie-, rekening- en bewijsmetadata zodat geoormerkte activiteiten in het lokale grootboek te onderscheiden blijven. Gebruikers moeten mappings valideren en uitzonderingen beoordelen; FAB garandeert niet dat ingestelde regels iedere vermenging voorkomen.",
        },
      },
      {
        question: { en: "Can FAB help with WLZ and WMO care arrangements?", nl: "Kan FAB helpen met WLZ- en WMO-zorgregelingen?" },
        answer: {
          en: "WLZ- and WMO-related documents can be retained, tagged, reviewed, and reported through the local ledger. FAB does not encode or validate the complete current rule set for either scheme, so eligibility and reporting decisions require professional review.",
          nl: "WLZ- en WMO-gerelateerde documenten kunnen via het lokale grootboek worden bewaard, gelabeld, beoordeeld en gerapporteerd. FAB bevat of valideert niet het volledige actuele regelstelsel van beide regelingen; aanspraken en verantwoording vereisen professionele beoordeling.",
        },
      },
      {
        question: { en: "Does FAB support Wajong and WIA benefits?", nl: "Ondersteunt FAB Wajong- en WIA-uitkeringen?" },
        answer: {
          en: "Wajong- and WIA-related records can be assigned distinct categories and evidence in the local ledger. FAB does not manage benefit entitlement or automatically apply UWV rules.",
          nl: "Wajong- en WIA-gerelateerde gegevens kunnen aparte categorieën en bewijs krijgen in het lokale grootboek. FAB beheert geen uitkeringsrechten en past UWV-regels niet automatisch toe.",
        },
      },
      {
        question: { en: "Can FAB generate reports for SVB accountability?", nl: "Kan FAB rapporten genereren voor SVB-verantwoording?" },
        answer: {
          en: "FAB can produce local ledger, evidence, and financial-report exports that help prepare an SVB or tax review. No export is universally accepted or submitted automatically; validate the selected period, classifications, evidence, and target format before filing.",
          nl: "FAB kan lokale grootboek-, bewijs- en financiële exports maken ter voorbereiding van SVB- of belastingcontrole. Geen export is universeel geaccepteerd of wordt automatisch ingediend; valideer periode, classificaties, bewijs en doelformaat vóór indiening.",
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
          en: "Commercial billing is not enabled in this local FAB release. The operator remains responsible for Windows hosting, backups, OCR or AI services, secure remote access, and any provider fees configured outside FAB.",
          nl: "Commerciële facturering is niet ingeschakeld in deze lokale FAB-release. De gebruiker blijft verantwoordelijk voor Windows-hosting, back-ups, OCR- of AI-diensten, beveiligde externe toegang en eventuele providerkosten buiten FAB.",
        },
      },
      {
        question: { en: "Is there a free tier?", nl: "Is er een gratis versie?" },
        answer: {
          en: "There is no metered free tier or transaction allowance in this release. Local use is not billed by FAB itself, although configured infrastructure and third-party providers may have their own costs and quotas.",
          nl: "Deze release heeft geen gemeten gratis versie of transactietegoed. FAB zelf factureert lokaal gebruik niet, maar ingestelde infrastructuur en externe providers kunnen eigen kosten en quota hebben.",
        },
      },
      {
        question: { en: "Can I set a spending cap?", nl: "Kan ik een bestedingslimiet instellen?" },
        answer: {
          en: "No FAB billing cap exists because the application does not meter or invoice local use. Operational safety limits, provider rate limits, and service quotas are separate controls and should be configured at the relevant provider.",
          nl: "Er is geen FAB-factureringslimiet omdat de toepassing lokaal gebruik niet meet of factureert. Operationele veiligheidslimieten, providerlimieten en servicequota zijn aparte controles die bij de betreffende provider moeten worden ingesteld.",
        },
      },
      {
        question: { en: "Can I see my current usage in real time?", nl: "Kan ik mijn huidige gebruik in real-time zien?" },
        answer: {
          en: "The operations dashboard shows intake, review, connector, worker, export, and recovery status. It does not calculate infrastructure or third-party billing costs.",
          nl: "Het operations-dashboard toont inname-, beoordeling-, koppeling-, worker-, export- en herstelstatus. Het berekent geen infrastructuur- of externe providerkosten.",
        },
      },
      {
        question: { en: "How am I billed?", nl: "Hoe word ik gefactureerd?" },
        answer: {
          en: "FAB does not generate subscription invoices or collect iDEAL payments. Any supplier invoice for hosting or connected services is managed directly with that supplier.",
          nl: "FAB maakt geen abonnementsfacturen en incasseert geen iDEAL-betalingen. Facturen voor hosting of gekoppelde diensten worden rechtstreeks met die leverancier afgehandeld.",
        },
      },
      {
        question: { en: "What happens if I stop using FAB?", nl: "Wat gebeurt er als ik stop met FAB?" },
        answer: {
          en: "Stop the FAB services only after confirming that the ledger, source documents, recovery snapshot, encryption recovery material, and required exports are intact. FAB itself adds no application cancellation fee; separately contracted providers keep their own terms.",
          nl: "Stop de FAB-diensten pas nadat het grootboek, de brondocumenten, herstelsnapshot, encryptieherstelmateriaal en vereiste exports intact zijn gecontroleerd. FAB zelf rekent geen annuleringskosten; apart afgesloten providers behouden hun eigen voorwaarden.",
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
          en: "FAB detects missing or conflicting fields, records a review blocker, and can prepare a suggested follow-up. The current bookkeeping release does not autonomously send that message or apply a reply to the ledger without review.",
          nl: "FAB detecteert ontbrekende of tegenstrijdige velden, legt een beoordelingsblokkade vast en kan een voorgestelde opvolging voorbereiden. De huidige boekhoudrelease verstuurt die boodschap niet autonoom en past een antwoord niet zonder beoordeling toe op het grootboek.",
        },
      },
      {
        question: { en: "Does FAB send emails without my permission?", nl: "Verstuurt FAB e-mails zonder mijn toestemming?" },
        answer: {
          en: "External email sending is not enabled in the current bookkeeping workflow. Suggested follow-up text remains local and review blocked; the user sends it through an approved communication channel.",
          nl: "Externe e-mailverzending is niet ingeschakeld in de huidige boekhoudworkflow. Voorgestelde opvolgtekst blijft lokaal en geblokkeerd voor beoordeling; de gebruiker verstuurt deze via een goedgekeurd communicatiekanaal.",
        },
      },
      {
        question: { en: "What happens if a vendor does not respond?", nl: "Wat gebeurt er als een leverancier niet reageert?" },
        answer: {
          en: "The unresolved item remains visible in the review queue and audit trail. Automatic vendor reminders and retry limits are not active in this release, so the operator controls any external follow-up.",
          nl: "Het onopgeloste item blijft zichtbaar in de beoordelingswachtrij en auditlog. Automatische leveranciersherinneringen en pogingslimieten zijn niet actief in deze release; de gebruiker beheert externe opvolging.",
        },
      },
      {
        question: { en: "How does FAB decide what to flag for my review?", nl: "Hoe bepaalt FAB wat gemarkeerd wordt voor mijn beoordeling?" },
        answer: {
          en: "Confidence thresholds, validation rules, duplicate evidence, and connector capabilities determine whether an item can proceed. Corrections are retained as audit evidence and may inform configured categorization history; FAB does not promise unsupervised self-learning or steadily increasing accuracy.",
          nl: "Vertrouwensdrempels, validatieregels, duplicaatbewijs en koppelingsmogelijkheden bepalen of een item verder kan. Correcties blijven als auditbewijs bewaard en kunnen ingestelde categorisatiehistorie ondersteunen; FAB belooft geen onbegeleid zelfleren of voortdurend toenemende nauwkeurigheid.",
        },
      },
      {
        question: { en: "Does FAB automatically delete documents from my inbox?", nl: "Verwijdert FAB automatisch documenten uit mijn inbox?" },
        answer: {
          en: "Gmail source messages are not deleted. Drive documents are moved to the configured archive only after FAB verifies the Wave transaction and exact attachment SHA-256 readback; otherwise they remain in place and become review blocked. Direct WhatsApp intake is not available.",
          nl: "Gmail-bronberichten worden niet verwijderd. Drive-documenten gaan alleen naar het ingestelde archief nadat FAB de Wave-transactie en exacte SHA-256 van de bijlage heeft teruggelezen; anders blijven ze staan en worden ze geblokkeerd voor beoordeling. Directe WhatsApp-inname is niet beschikbaar.",
        },
      },
      {
        question: { en: "How often does FAB scan for new data?", nl: "Hoe vaak scant FAB naar nieuwe gegevens?" },
        answer: {
          en: "The autonomous worker interval and Windows Task Scheduler configuration control recurring processing. The dashboard reports worker state and provides guarded run controls; it does not currently expose generic frequency sliders for every connector.",
          nl: "Het interval van de autonome worker en Windows Taakplanner bepalen terugkerende verwerking. Het dashboard toont de workerstatus en biedt beveiligde uitvoerbediening; het bevat momenteel geen algemene frequentieschuiven voor iedere koppeling.",
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
          en: "Install FAB on the Windows host, open the Activation Checklist, and use the connector setup panels for local paths, Google authorization, Wave credentials, worker scheduling, recovery, and remote-access checks. Completion time depends on provider consent and the host configuration; no fixed setup duration is promised.",
          nl: "Installeer FAB op de Windows-host, open de Activatiechecklist en gebruik de koppelingspanelen voor lokale paden, Google-autorisatie, Wave-inloggegevens, workerplanning, herstel en controle van externe toegang. De duur hangt af van providertoestemming en hostconfiguratie; er geldt geen vaste installatietijd.",
        },
      },
      {
        question: { en: "Does FAB support multiple bank accounts?", nl: "Ondersteunt FAB meerdere bankrekeningen?" },
        answer: {
          en: "FAB can import supported statement files from multiple accounts and preserve their account identities during reconciliation. Direct PSD2 bank connections are not included in the current release.",
          nl: "FAB kan ondersteunde afschriftbestanden van meerdere rekeningen importeren en hun rekeningidentiteit tijdens afstemming behouden. Directe PSD2-bankkoppelingen zijn niet opgenomen in de huidige release.",
        },
      },
      {
        question: { en: "Can FAB handle cash transactions?", nl: "Kan FAB contante transacties verwerken?" },
        answer: {
          en: "Cash receipts can enter through supported file, scanner, Gmail, Drive, or selected photo intake paths. OCR extracts candidate fields and low-confidence or incomplete results go to review; the current dashboard does not provide a separate manual cash-journal form.",
          nl: "Contante bonnen kunnen via ondersteunde bestands-, scanner-, Gmail-, Drive- of geselecteerde foto-inname binnenkomen. OCR extraheert kandidaatvelden en onzekere of onvolledige resultaten gaan naar beoordeling; het huidige dashboard heeft geen apart handmatig kasboekformulier.",
        },
      },
      {
        question: { en: "Can I export my data from FAB?", nl: "Kan ik mijn gegevens exporteren uit FAB?" },
        answer: {
          en: "FAB provides documented ledger, report, support-bundle, and recovery exports for their intended workflows. Export coverage and target compatibility must be checked before relying on an export for migration, filing, or disaster recovery.",
          nl: "FAB biedt gedocumenteerde grootboek-, rapport-, supportbundel- en herstelexports voor hun bedoelde werkstromen. Controleer exportdekking en compatibiliteit met het doel voordat je een export gebruikt voor migratie, aangifte of calamiteitenherstel.",
        },
      },
      {
        question: { en: "Does FAB offer customer support?", nl: "Biedt FAB klantenondersteuning?" },
        answer: {
          en: "FAB includes an operator runbook, activation checklist, diagnostics, audit history, and an exportable support bundle. No staffed email, chat, video-support channel, or response-time service level is bundled with this release.",
          nl: "FAB bevat een gebruikershandleiding, activatiechecklist, diagnostiek, auditgeschiedenis en exporteerbare supportbundel. Deze release bevat geen bemand e-mail-, chat- of video-ondersteuningskanaal en geen gegarandeerde reactietijd.",
        },
      },
      {
        question: { en: "Will FAB be available outside the Netherlands?", nl: "Komt FAB beschikbaar buiten Nederland?" },
        answer: {
          en: "FAB is currently designed and tested for Dutch bookkeeping workflows. Tax, banking, care-budget, reporting, and regulatory behavior for other countries has not been validated.",
          nl: "FAB is momenteel ontworpen en getest voor Nederlandse boekhoudwerkstromen. Belasting-, bank-, zorgbudget-, rapportage- en regelgevingsgedrag voor andere landen is niet gevalideerd.",
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
