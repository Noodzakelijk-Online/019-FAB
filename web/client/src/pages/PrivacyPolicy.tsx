import LegalLayout from "@/components/LegalLayout";
import { useLanguage } from "@/contexts/LanguageContext";

export default function PrivacyPolicy() {
  const { lang } = useLanguage();

  if (lang === "nl") {
    return (
      <LegalLayout title="Privacybeleid" lastUpdated="9 augustus 2026">
        <h2>1. Inleiding</h2>
        <p>
          FAB ("wij", "ons", "onze") respecteert uw privacy en zet zich in voor de bescherming van uw persoonsgegevens. Dit privacybeleid legt uit hoe wij uw informatie verzamelen, gebruiken, opslaan en beschermen wanneer u onze diensten gebruikt.
        </p>
        <p>
          FAB is een financieel orkestratieplatform dat geautomatiseerde boekhouding en financieel beheer biedt, met bijzondere aandacht voor mensen met een beperking of chronische ziekte die gebruikmaken van het Persoonsgebonden Budget (PGB) en andere zorggerelateerde financiële regelingen.
        </p>

        <h2>2. Verwerkingsverantwoordelijke</h2>
        <p>
          De eigenaar van deze FAB-implementatie bepaalt in beginsel doelen, bronnen, bewaartermijnen en gekoppelde providers en is doorgaans de verwerkingsverantwoordelijke, tenzij een toepasselijke overeenkomst anders bepaalt. Leg de verantwoordelijke en contactgegevens vast vóór productiegebruik.
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
          Commerciële facturatie is in de lokale implementatie standaard uitgeschakeld. Alleen wanneer de implementatie-eigenaar deze functie expliciet activeert, verwerkt Stripe de betaalmethode rechtstreeks; FAB hoort geen volledige kaartnummers op te slaan.
        </p>

        <h3>3.4 Gebruiksgegevens</h3>
        <p>De lokale dienst kan voor beveiliging en diagnose vastleggen:</p>
        <ul>
          <li>Technische aanvraagmetadata, tijdstippen en foutcodes</li>
          <li>IP-adressen voor authenticatie, misbruikpreventie en audit wanneer van toepassing</li>
          <li>Worker-, koppeling- en gebruikersacties in het lokale auditlog</li>
        </ul>
        <p>Deze release bevat geen ingebouwde advertentieanalyse of land-geolocatiepijplijn.</p>

        <h2>4. Hoe Wij Uw Gegevens Gebruiken</h2>
        <p>Wij gebruiken uw gegevens voor:</p>
        <ul>
          <li><strong>Dienstverlening:</strong> Het verwerken van financiële documenten, het genereren van overzichten en het bieden van financieel inzicht</li>
          <li><strong>Accountbeheer:</strong> Het beheren van uw account, authenticatie en beveiliging</li>
          <li><strong>Communicatie:</strong> Het lokaal voorbereiden van meldingen en ondersteuningsinformatie; externe verzending vereist een apart ingericht kanaal</li>
          <li><strong>Verbetering:</strong> Het lokaal onderzoeken van fouten, prestaties en beoordeelde correcties</li>
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
          <li>Lokale bescherming van ondersteunde providergeheimen, waaronder Windows-gebruikersbescherming voor Wave</li>
          <li>HTTPS voor providerverkeer en een geauthenticeerde HTTPS-gateway voor externe toegang</li>
          <li>Sessieauthenticatie, een apart HAI-servicetoken, auditlogs en goedkeuringspoorten</li>
          <li>Door de eigenaar beheerde schijfversleuteling, back-ups en geteste herstelprocedures</li>
        </ul>

        <h2>7. Gegevensopslag en -bewaring</h2>
        <p>
          Het gezaghebbende grootboek en de operationele metadata staan op de ingestelde FAB-host. Brondocumenten kunnen lokaal of bij expliciet gekoppelde providers staan. De implementatie-eigenaar moet opslaglocatie, EER-vereisten, bewaartermijnen, wettelijke boekhoudtermijnen en gecontroleerde verwijdering configureren en documenteren.
        </p>

        <h2>8. Delen van Gegevens</h2>
        <p>Wij delen uw gegevens alleen met:</p>
        <ul>
          <li><strong>Ingerichte providers:</strong> alleen providers die de eigenaar expliciet autoriseert, zoals Google of Wave voor de geselecteerde handeling, en Stripe uitsluitend wanneer commerciële facturatie bewust is ingeschakeld</li>
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
    <LegalLayout title="Privacy Policy" lastUpdated="August 9, 2026">
      <h2>1. Introduction</h2>
      <p>
        FAB ("we", "us", "our") respects your privacy and is committed to protecting your personal data. This privacy policy explains how we collect, use, store, and protect your information when you use our services.
      </p>
      <p>
        FAB is a financial orchestration platform that provides automated bookkeeping and financial management, with special focus on people with disabilities or chronic conditions who use the Personal Budget (PGB) and other care-related financial arrangements in the Netherlands.
      </p>

      <h2>2. Data Controller</h2>
      <p>
        The owner of this FAB deployment ordinarily determines purposes, sources, retention, and connected providers and is therefore usually the data controller unless an applicable agreement says otherwise. Record the responsible entity and contact details before production use.
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
        Commercial billing is disabled by default in the local deployment. Only when the deployment owner explicitly enables it does Stripe process a payment method directly; FAB should not store complete card numbers.
      </p>

      <h3>3.4 Usage Data</h3>
      <p>The local service may retain the following for security and diagnosis:</p>
      <ul>
        <li>Technical request metadata, timestamps, and error codes</li>
        <li>IP addresses for authentication, abuse prevention, and audit where applicable</li>
        <li>Worker, connector, and operator actions in the local audit trail</li>
      </ul>
      <p>This release has no built-in advertising analytics or country-geolocation pipeline.</p>

      <h2>4. How We Use Your Data</h2>
      <p>We use your data for:</p>
      <ul>
        <li><strong>Service delivery:</strong> Processing financial documents, generating overviews, and providing financial insights</li>
        <li><strong>Account management:</strong> Managing your account, authentication, and security</li>
        <li><strong>Communication:</strong> Preparing local notifications and support information; external delivery requires a separately configured channel</li>
        <li><strong>Improvement:</strong> Investigating errors, performance, and reviewed corrections locally</li>
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
        <li>Local protection for supported provider secrets, including Windows user protection for Wave</li>
        <li>HTTPS for provider traffic and an authenticated HTTPS gateway for remote access</li>
        <li>Session authentication, a separate HAI service token, audit trails, and approval gates</li>
        <li>Owner-managed disk encryption, backups, and tested recovery procedures</li>
      </ul>

      <h2>7. Data Storage and Retention</h2>
      <p>
        The authoritative ledger and operational metadata are stored on the configured FAB host. Source documents may be local or held by explicitly connected providers. The deployment owner must configure and document storage location, EEA requirements, retention, statutory bookkeeping periods, and controlled deletion.
      </p>

      <h2>8. Data Sharing</h2>
      <p>We only share your data with:</p>
      <ul>
        <li><strong>Configured providers:</strong> only providers explicitly authorized by the owner, such as Google or Wave for the selected operation, and Stripe only when commercial billing is deliberately enabled</li>
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
