import LegalLayout from "@/components/LegalLayout";
import { useLanguage } from "@/contexts/LanguageContext";

export default function PrivacyPolicy() {
  const { lang } = useLanguage();

  if (lang === "nl") {
    return (
      <LegalLayout title="Privacybeleid" lastUpdated="4 maart 2026">
        <h2>1. Inleiding</h2>
        <p>
          FAB ("wij", "ons", "onze") respecteert uw privacy en zet zich in voor de bescherming van uw persoonsgegevens. Dit privacybeleid legt uit hoe wij uw informatie verzamelen, gebruiken, opslaan en beschermen wanneer u onze diensten gebruikt.
        </p>
        <p>
          FAB is een financieel orkestratieplatform dat geautomatiseerde boekhouding en financieel beheer biedt, met bijzondere aandacht voor mensen met een beperking of chronische ziekte die gebruikmaken van het Persoonsgebonden Budget (PGB) en andere zorggerelateerde financiële regelingen.
        </p>

        <h2>2. Verwerkingsverantwoordelijke</h2>
        <p>
          De verwerkingsverantwoordelijke voor uw persoonsgegevens is FAB, gevestigd in Nederland. Voor vragen over dit privacybeleid kunt u contact met ons opnemen via onze <a href="/contact">contactpagina</a>.
        </p>

        <h2>3. Welke Gegevens Verzamelen Wij</h2>
        <h3>3.1 Accountgegevens</h3>
        <p>Wanneer u een account aanmaakt, verzamelen wij:</p>
        <ul>
          <li>Naam en e-mailadres</li>
          <li>Inloggegevens (versleuteld opgeslagen)</li>
          <li>Accountvoorkeuren en instellingen</li>
        </ul>

        <h3>3.2 Financiële Gegevens</h3>
        <p>Om onze diensten te leveren, verwerken wij:</p>
        <ul>
          <li>Financiële documenten die u uploadt (facturen, declaraties, bankafschriften)</li>
          <li>PGB-gerelateerde financiële informatie</li>
          <li>Categorisatie- en budgetgegevens</li>
        </ul>

        <h3>3.3 Betalingsgegevens</h3>
        <p>
          Betalingen worden verwerkt via Stripe. Wij slaan geen volledige creditcardnummers of bankgegevens op. Stripe verwerkt uw betalingsgegevens in overeenstemming met PCI DSS-normen.
        </p>

        <h3>3.4 Gebruiksgegevens</h3>
        <p>Wij verzamelen automatisch:</p>
        <ul>
          <li>Apparaat- en browserinformatie</li>
          <li>IP-adres en locatiegegevens (op landniveau)</li>
          <li>Gebruikspatronen en interacties met onze dienst</li>
        </ul>

        <h2>4. Hoe Wij Uw Gegevens Gebruiken</h2>
        <p>Wij gebruiken uw gegevens voor:</p>
        <ul>
          <li><strong>Dienstverlening:</strong> Het verwerken van financiële documenten, het genereren van overzichten en het bieden van financieel inzicht</li>
          <li><strong>Accountbeheer:</strong> Het beheren van uw account, authenticatie en beveiliging</li>
          <li><strong>Communicatie:</strong> Het verzenden van servicemeldingen, updates en ondersteuning</li>
          <li><strong>Verbetering:</strong> Het analyseren van gebruikspatronen om onze diensten te verbeteren</li>
          <li><strong>Wettelijke verplichtingen:</strong> Het voldoen aan toepasselijke wet- en regelgeving</li>
        </ul>

        <h2>5. Rechtsgrond voor Verwerking</h2>
        <p>Wij verwerken uw gegevens op basis van:</p>
        <ul>
          <li><strong>Uitvoering van de overeenkomst:</strong> Noodzakelijk om onze diensten aan u te leveren</li>
          <li><strong>Toestemming:</strong> Voor optionele functies en marketingcommunicatie</li>
          <li><strong>Gerechtvaardigd belang:</strong> Voor beveiliging, fraudepreventie en dienstverbetering</li>
          <li><strong>Wettelijke verplichting:</strong> Wanneer de wet dit vereist</li>
        </ul>

        <h2>6. Gegevensbeveiliging</h2>
        <p>
          Wij nemen uitgebreide maatregelen om uw gegevens te beschermen, waaronder:
        </p>
        <ul>
          <li>End-to-end encryptie voor gevoelige financiële gegevens</li>
          <li>Beveiligde serverinfrastructuur met regelmatige beveiligingsaudits</li>
          <li>Strikte toegangscontroles en authenticatieprotocollen</li>
          <li>Regelmatige back-ups en noodherstelprocedures</li>
        </ul>

        <h2>7. Gegevensopslag en -bewaring</h2>
        <p>
          Uw gegevens worden opgeslagen op beveiligde servers binnen de Europese Economische Ruimte (EER). Wij bewaren uw gegevens zolang uw account actief is en gedurende een redelijke periode daarna, tenzij een langere bewaartermijn wettelijk vereist is.
        </p>

        <h2>8. Delen van Gegevens</h2>
        <p>Wij delen uw gegevens alleen met:</p>
        <ul>
          <li><strong>Dienstverleners:</strong> Stripe (betalingsverwerking), cloudopslagproviders</li>
          <li><strong>Wettelijke autoriteiten:</strong> Wanneer wettelijk vereist</li>
        </ul>
        <p>Wij verkopen uw persoonsgegevens nooit aan derden.</p>

        <h2>9. Uw Rechten</h2>
        <p>Op grond van de AVG heeft u het recht op:</p>
        <ul>
          <li>Inzage in uw persoonsgegevens</li>
          <li>Rectificatie van onjuiste gegevens</li>
          <li>Verwijdering van uw gegevens ("recht op vergetelheid")</li>
          <li>Beperking van de verwerking</li>
          <li>Overdraagbaarheid van gegevens</li>
          <li>Bezwaar tegen verwerking</li>
          <li>Intrekking van toestemming</li>
        </ul>
        <p>
          Om uw rechten uit te oefenen, neem contact met ons op via onze <a href="/contact">contactpagina</a> of via de <a href="/gdpr">AVG-pagina</a>.
        </p>

        <h2>10. Wijzigingen in Dit Beleid</h2>
        <p>
          Wij kunnen dit privacybeleid van tijd tot tijd bijwerken. Wij zullen u op de hoogte stellen van belangrijke wijzigingen via e-mail of een melding op onze website.
        </p>

        <h2>11. Contact</h2>
        <p>
          Voor vragen over dit privacybeleid of uw persoonsgegevens kunt u contact met ons opnemen via onze <a href="/contact">contactpagina</a>.
        </p>
      </LegalLayout>
    );
  }

  return (
    <LegalLayout title="Privacy Policy" lastUpdated="March 4, 2026">
      <h2>1. Introduction</h2>
      <p>
        FAB ("we", "us", "our") respects your privacy and is committed to protecting your personal data. This privacy policy explains how we collect, use, store, and protect your information when you use our services.
      </p>
      <p>
        FAB is a financial orchestration platform that provides automated bookkeeping and financial management, with special focus on people with disabilities or chronic conditions who use the Personal Budget (PGB) and other care-related financial arrangements in the Netherlands.
      </p>

      <h2>2. Data Controller</h2>
      <p>
        The data controller for your personal data is FAB, based in the Netherlands. For questions about this privacy policy, please contact us through our <a href="/contact">contact page</a>.
      </p>

      <h2>3. What Data We Collect</h2>
      <h3>3.1 Account Data</h3>
      <p>When you create an account, we collect:</p>
      <ul>
        <li>Name and email address</li>
        <li>Login credentials (stored encrypted)</li>
        <li>Account preferences and settings</li>
      </ul>

      <h3>3.2 Financial Data</h3>
      <p>To provide our services, we process:</p>
      <ul>
        <li>Financial documents you upload (invoices, declarations, bank statements)</li>
        <li>PGB-related financial information</li>
        <li>Categorization and budget data</li>
      </ul>

      <h3>3.3 Payment Data</h3>
      <p>
        Payments are processed through Stripe. We do not store complete credit card numbers or bank details. Stripe processes your payment data in accordance with PCI DSS standards.
      </p>

      <h3>3.4 Usage Data</h3>
      <p>We automatically collect:</p>
      <ul>
        <li>Device and browser information</li>
        <li>IP address and location data (country level)</li>
        <li>Usage patterns and interactions with our service</li>
      </ul>

      <h2>4. How We Use Your Data</h2>
      <p>We use your data for:</p>
      <ul>
        <li><strong>Service delivery:</strong> Processing financial documents, generating overviews, and providing financial insights</li>
        <li><strong>Account management:</strong> Managing your account, authentication, and security</li>
        <li><strong>Communication:</strong> Sending service notifications, updates, and support</li>
        <li><strong>Improvement:</strong> Analyzing usage patterns to improve our services</li>
        <li><strong>Legal obligations:</strong> Complying with applicable laws and regulations</li>
      </ul>

      <h2>5. Legal Basis for Processing</h2>
      <p>We process your data based on:</p>
      <ul>
        <li><strong>Contract performance:</strong> Necessary to provide our services to you</li>
        <li><strong>Consent:</strong> For optional features and marketing communications</li>
        <li><strong>Legitimate interest:</strong> For security, fraud prevention, and service improvement</li>
        <li><strong>Legal obligation:</strong> When required by law</li>
      </ul>

      <h2>6. Data Security</h2>
      <p>
        We implement comprehensive measures to protect your data, including:
      </p>
      <ul>
        <li>End-to-end encryption for sensitive financial data</li>
        <li>Secure server infrastructure with regular security audits</li>
        <li>Strict access controls and authentication protocols</li>
        <li>Regular backups and disaster recovery procedures</li>
      </ul>

      <h2>7. Data Storage and Retention</h2>
      <p>
        Your data is stored on secure servers within the European Economic Area (EEA). We retain your data for as long as your account is active and for a reasonable period thereafter, unless a longer retention period is required by law.
      </p>

      <h2>8. Data Sharing</h2>
      <p>We only share your data with:</p>
      <ul>
        <li><strong>Service providers:</strong> Stripe (payment processing), cloud storage providers</li>
        <li><strong>Legal authorities:</strong> When required by law</li>
      </ul>
      <p>We never sell your personal data to third parties.</p>

      <h2>9. Your Rights</h2>
      <p>Under the GDPR, you have the right to:</p>
      <ul>
        <li>Access your personal data</li>
        <li>Rectify inaccurate data</li>
        <li>Erase your data ("right to be forgotten")</li>
        <li>Restrict processing</li>
        <li>Data portability</li>
        <li>Object to processing</li>
        <li>Withdraw consent</li>
      </ul>
      <p>
        To exercise your rights, contact us through our <a href="/contact">contact page</a> or visit our <a href="/gdpr">GDPR page</a>.
      </p>

      <h2>10. Changes to This Policy</h2>
      <p>
        We may update this privacy policy from time to time. We will notify you of significant changes via email or a notice on our website.
      </p>

      <h2>11. Contact</h2>
      <p>
        For questions about this privacy policy or your personal data, please contact us through our <a href="/contact">contact page</a>.
      </p>
    </LegalLayout>
  );
}
