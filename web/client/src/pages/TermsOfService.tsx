import LegalLayout from "@/components/LegalLayout";
import { useLanguage } from "@/contexts/LanguageContext";

export default function TermsOfService() {
  const { lang } = useLanguage();

  if (lang === "nl") {
    return (
      <LegalLayout title="Algemene Voorwaarden" lastUpdated="9 augustus 2026">
        <h2>1. Aanvaarding van Voorwaarden</h2>
        <p>
          Door gebruik te maken van FAB ("de Dienst"), gaat u akkoord met deze Algemene Voorwaarden. Als u niet akkoord gaat met deze voorwaarden, gebruik de Dienst dan niet. FAB behoudt zich het recht voor deze voorwaarden op elk moment te wijzigen.
        </p>

        <h2>2. Beschrijving van de Dienst</h2>
        <p>
          FAB is een lokaal financieel operations-platform voor ondersteunde boekhoudwerkstromen. De Dienst omvat onder meer:
        </p>
        <ul>
          <li>Geautomatiseerde verwerking en categorisering van financiële documenten</li>
          <li>Classificatie en rapportage van PGB-gerelateerd bewijs, zonder directe SVB-indiening</li>
          <li>Financiële overzichten en rapportages</li>
          <li>Import van ondersteunde bankafschriftbestanden en functiegebonden providerkoppelingen</li>
          <li>Vertrouwensscores, validatie en beoordelingswachtrijen</li>
        </ul>

        <h2>3. Accountregistratie</h2>
        <p>
          Om de Dienst te gebruiken, moet u een account aanmaken. U bent verantwoordelijk voor het vertrouwelijk houden van uw inloggegevens en voor alle activiteiten die onder uw account plaatsvinden. U stemt ermee in om:
        </p>
        <ul>
          <li>Nauwkeurige en volledige informatie te verstrekken bij registratie</li>
          <li>Uw accountinformatie actueel te houden</li>
          <li>Ons onmiddellijk op de hoogte te stellen van ongeautoriseerd gebruik</li>
          <li>Uw account niet te delen met derden</li>
        </ul>

        <h2>4. Implementatie en Externe Kosten</h2>
        <h3>4.1 Lokale FAB-runtime</h3>
        <p>
          Deze release meet lokaal FAB-gebruik niet en verkoopt geen abonnement of transactietegoed. De implementatie-eigenaar beheert de Windows-host, opslag, back-ups, beveiliging en operationele configuratie.
        </p>
        <h3>4.2 Externe diensten</h3>
        <p>
          Google, Wave, OCR-, AI-, tunnel-, hosting- en andere externe diensten vallen onder hun eigen voorwaarden, quota en kosten. FAB berekent of factureert die kosten niet.
        </p>
        <h3>4.3 Optionele commerciële facturatie</h3>
        <p>
          De aanwezige Stripe-betalingsmethode is standaard uitgeschakeld en mag alleen worden geactiveerd nadat een afzonderlijk factureringsproces, meting, privacygrondslag en voorwaarden daadwerkelijk zijn ingericht. De huidige lokale implementatie verzamelt geen betaalmethode.
        </p>

        <h2>5. Aanvaardbaar Gebruik</h2>
        <p>U stemt ermee in de Dienst niet te gebruiken voor:</p>
        <ul>
          <li>Illegale activiteiten of het overtreden van toepasselijke wetgeving</li>
          <li>Het uploaden van schadelijke, misleidende of frauduleuze inhoud</li>
          <li>Het verstoren of belasten van de Dienst of de bijbehorende infrastructuur</li>
          <li>Het proberen toegang te krijgen tot accounts of gegevens van andere gebruikers</li>
          <li>Het reverse-engineeren of kopiëren van de Dienst</li>
        </ul>

        <h2>6. Intellectueel Eigendom</h2>
        <p>
          Alle intellectuele eigendomsrechten op de Dienst, inclusief software, ontwerp, teksten en logo's, behoren toe aan FAB. U krijgt een beperkte, niet-exclusieve licentie om de Dienst te gebruiken in overeenstemming met deze voorwaarden.
        </p>
        <p>
          U behoudt alle rechten op de gegevens en documenten die u uploadt naar de Dienst.
        </p>

        <h2>7. Gegevensverwerking</h2>
        <p>
          Uw gebruik van de Dienst is ook onderworpen aan ons <a href="/privacy">Privacybeleid</a>. Door de Dienst te gebruiken, stemt u in met de verwerking van uw gegevens zoals beschreven in dat beleid.
        </p>

        <h2>8. Beperking van Aansprakelijkheid</h2>
        <p>
          FAB biedt de Dienst "zoals deze is" aan. Hoewel wij streven naar nauwkeurigheid en betrouwbaarheid, garanderen wij niet dat de Dienst foutloos of ononderbroken beschikbaar is. FAB is niet aansprakelijk voor:
        </p>
        <ul>
          <li>Indirecte, incidentele of gevolgschade</li>
          <li>Verlies van gegevens of bedrijfsonderbreking</li>
          <li>Fouten in AI-gegenereerde categorisaties of berekeningen</li>
          <li>Beslissingen genomen op basis van informatie uit de Dienst</li>
        </ul>
        <p>
          <strong>Belangrijk:</strong> FAB is een hulpmiddel voor financieel beheer en vervangt geen professioneel financieel of fiscaal advies. Raadpleeg altijd een gekwalificeerde adviseur voor belangrijke financiële beslissingen.
        </p>

        <h2>9. Beschikbaarheid</h2>
        <p>
          Wij streven naar een hoge beschikbaarheid van de Dienst, maar kunnen geen 100% uptime garanderen. Wij behouden ons het recht voor de Dienst tijdelijk te onderbreken voor onderhoud of updates.
        </p>

        <h2>10. Beëindiging</h2>
        <p>
          Stop de Dienst pas nadat het grootboek, brondocumenten, herstelsnapshot, encryptieherstelmateriaal en noodzakelijke exports zijn gecontroleerd. Bewaring en verwijdering volgen de ingestelde lokale procedures en toepasselijke wettelijke termijnen.
        </p>

        <h2>11. Toepasselijk Recht</h2>
        <p>
          Op deze voorwaarden is Nederlands recht van toepassing. Geschillen worden voorgelegd aan de bevoegde rechter in Nederland.
        </p>

        <h2>12. Contact</h2>
        <p>
          Voor vragen over deze voorwaarden kunt u contact met ons opnemen via onze <a href="/contact">contactpagina</a>.
        </p>
      </LegalLayout>
    );
  }

  return (
    <LegalLayout title="Terms of Service" lastUpdated="August 9, 2026">
      <h2>1. Acceptance of Terms</h2>
      <p>
        By using FAB ("the Service"), you agree to these Terms of Service. If you do not agree to these terms, do not use the Service. FAB reserves the right to modify these terms at any time.
      </p>

      <h2>2. Description of Service</h2>
      <p>
        FAB is a local financial operations platform for supported bookkeeping workflows. The Service includes, among other things:
      </p>
      <ul>
        <li>Automated processing and categorization of financial documents</li>
        <li>Classification and reporting of PGB-related evidence without direct SVB submission</li>
        <li>Financial overviews and reporting</li>
        <li>Supported bank-statement imports and capability-specific provider connectors</li>
        <li>Confidence scoring, validation, and review queues</li>
      </ul>

      <h2>3. Account Registration</h2>
      <p>
        To use the Service, you must create an account. You are responsible for keeping your login credentials confidential and for all activities that occur under your account. You agree to:
      </p>
      <ul>
        <li>Provide accurate and complete information during registration</li>
        <li>Keep your account information up to date</li>
        <li>Notify us immediately of any unauthorized use</li>
        <li>Not share your account with third parties</li>
      </ul>

      <h2>4. Deployment and External Costs</h2>
      <h3>4.1 Local FAB Runtime</h3>
      <p>
        This release does not meter local FAB use or sell a subscription or transaction allowance. The deployment owner manages the Windows host, storage, backups, security, and operational configuration.
      </p>
      <h3>4.2 External Services</h3>
      <p>
        Google, Wave, OCR, AI, tunnel, hosting, and other external services retain their own terms, quotas, and costs. FAB does not calculate or invoice those costs.
      </p>
      <h3>4.3 Optional Commercial Billing</h3>
      <p>
        The included Stripe payment-method path is disabled by default and may only be activated after a separate billing process, metering system, privacy basis, and terms are actually configured. The current local deployment does not collect a payment method.
      </p>

      <h2>5. Acceptable Use</h2>
      <p>You agree not to use the Service for:</p>
      <ul>
        <li>Illegal activities or violating applicable laws</li>
        <li>Uploading harmful, misleading, or fraudulent content</li>
        <li>Disrupting or overloading the Service or its infrastructure</li>
        <li>Attempting to access other users' accounts or data</li>
        <li>Reverse-engineering or copying the Service</li>
      </ul>

      <h2>6. Intellectual Property</h2>
      <p>
        All intellectual property rights in the Service, including software, design, text, and logos, belong to FAB. You are granted a limited, non-exclusive license to use the Service in accordance with these terms.
      </p>
      <p>
        You retain all rights to the data and documents you upload to the Service.
      </p>

      <h2>7. Data Processing</h2>
      <p>
        Your use of the Service is also subject to our <a href="/privacy">Privacy Policy</a>. By using the Service, you consent to the processing of your data as described in that policy.
      </p>

      <h2>8. Limitation of Liability</h2>
      <p>
        FAB provides the Service "as is." While we strive for accuracy and reliability, we do not guarantee that the Service will be error-free or uninterrupted. FAB is not liable for:
      </p>
      <ul>
        <li>Indirect, incidental, or consequential damages</li>
        <li>Loss of data or business interruption</li>
        <li>Errors in AI-generated categorizations or calculations</li>
        <li>Decisions made based on information from the Service</li>
      </ul>
      <p>
        <strong>Important:</strong> FAB is a financial management tool and does not replace professional financial or tax advice. Always consult a qualified advisor for important financial decisions.
      </p>

      <h2>9. Availability</h2>
      <p>
        We strive for high availability of the Service but cannot guarantee 100% uptime. We reserve the right to temporarily interrupt the Service for maintenance or updates.
      </p>

      <h2>10. Termination</h2>
      <p>
        Stop the Service only after verifying the ledger, source documents, recovery snapshot, encryption recovery material, and required exports. Retention and deletion follow the configured local procedures and applicable statutory periods.
      </p>

      <h2>11. Governing Law</h2>
      <p>
        These terms are governed by the laws of the Netherlands. Disputes shall be submitted to the competent court in the Netherlands.
      </p>

      <h2>12. Contact</h2>
      <p>
        For questions about these terms, please contact us through our <a href="/contact">contact page</a>.
      </p>
    </LegalLayout>
  );
}
