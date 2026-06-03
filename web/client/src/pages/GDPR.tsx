import LegalLayout from "@/components/LegalLayout";
import { useLanguage } from "@/contexts/LanguageContext";

export default function GDPR() {
  const { lang } = useLanguage();

  if (lang === "nl") {
    return (
      <LegalLayout title="AVG — Uw Rechten" lastUpdated="4 maart 2026">
        <h2>1. Uw Rechten onder de AVG</h2>
        <p>
          De Algemene Verordening Gegevensbescherming (AVG) geeft u als betrokkene uitgebreide rechten met betrekking tot uw persoonsgegevens. FAB respecteert deze rechten volledig en maakt het u gemakkelijk om ze uit te oefenen.
        </p>

        <h2>2. Recht op Inzage</h2>
        <p>
          U heeft het recht om te weten welke persoonsgegevens wij over u verwerken. U kunt een kopie opvragen van alle gegevens die wij over u bewaren. Wij zullen binnen 30 dagen op uw verzoek reageren.
        </p>

        <h2>3. Recht op Rectificatie</h2>
        <p>
          Als uw persoonsgegevens onjuist of onvolledig zijn, heeft u het recht om correctie te verzoeken. U kunt de meeste gegevens direct in uw accountinstellingen bijwerken.
        </p>

        <h2>4. Recht op Verwijdering</h2>
        <p>
          U heeft het recht om verwijdering van uw persoonsgegevens te verzoeken ("recht op vergetelheid"). Dit omvat:
        </p>
        <ul>
          <li>Verwijdering van uw account en alle bijbehorende gegevens</li>
          <li>Verwijdering van geüploade documenten en financiële gegevens</li>
          <li>Verwijdering van gebruiksgegevens en logbestanden</li>
        </ul>
        <p>
          <strong>Let op:</strong> Sommige gegevens moeten wij mogelijk bewaren op grond van wettelijke verplichtingen (bijv. fiscale bewaarplicht).
        </p>

        <h2>5. Recht op Beperking van Verwerking</h2>
        <p>
          U kunt verzoeken dat wij de verwerking van uw gegevens beperken terwijl een geschil wordt opgelost of wanneer u bezwaar heeft gemaakt tegen de verwerking.
        </p>

        <h2>6. Recht op Overdraagbaarheid</h2>
        <p>
          U heeft het recht om uw gegevens in een gestructureerd, gangbaar en machineleesbaar formaat te ontvangen. FAB biedt exportfunctionaliteit waarmee u uw financiële gegevens kunt downloaden in standaardformaten (CSV, PDF).
        </p>

        <h2>7. Recht van Bezwaar</h2>
        <p>
          U heeft het recht om bezwaar te maken tegen de verwerking van uw persoonsgegevens op basis van ons gerechtvaardigd belang. Wij zullen de verwerking staken tenzij wij dwingende gerechtvaardigde gronden kunnen aantonen.
        </p>

        <h2>8. Recht met Betrekking tot Geautomatiseerde Besluitvorming</h2>
        <p>
          FAB gebruikt AI voor documentcategorisatie en financiële inzichten. U heeft het recht om:
        </p>
        <ul>
          <li>Geïnformeerd te worden over geautomatiseerde besluitvorming</li>
          <li>Menselijke tussenkomst te verzoeken</li>
          <li>De beslissing aan te vechten</li>
        </ul>

        <h2>9. Hoe U Uw Rechten Uitoefent</h2>
        <p>
          U kunt uw rechten uitoefenen door:
        </p>
        <ul>
          <li>Contact met ons op te nemen via onze <a href="/contact">contactpagina</a></li>
          <li>Een e-mail te sturen met het onderwerp "AVG-verzoek"</li>
          <li>Uw accountinstellingen te gebruiken voor directe wijzigingen</li>
        </ul>
        <p>
          Wij verifiëren uw identiteit voordat wij uw verzoek verwerken en reageren binnen 30 dagen.
        </p>

        <h2>10. Klachten</h2>
        <p>
          Als u niet tevreden bent met hoe wij uw gegevens verwerken, heeft u het recht om een klacht in te dienen bij de Autoriteit Persoonsgegevens (AP), de Nederlandse toezichthouder voor gegevensbescherming.
        </p>
        <p>
          <strong>Autoriteit Persoonsgegevens</strong><br />
          Website: <a href="https://autoriteitpersoonsgegevens.nl" target="_blank" rel="noopener noreferrer">autoriteitpersoonsgegevens.nl</a>
        </p>

        <h2>11. Functionaris voor Gegevensbescherming</h2>
        <p>
          Voor vragen over gegevensbescherming kunt u contact opnemen via onze <a href="/contact">contactpagina</a> met het onderwerp "Gegevensbescherming".
        </p>
      </LegalLayout>
    );
  }

  return (
    <LegalLayout title="GDPR — Your Rights" lastUpdated="March 4, 2026">
      <h2>1. Your Rights Under GDPR</h2>
      <p>
        The General Data Protection Regulation (GDPR) gives you extensive rights regarding your personal data. FAB fully respects these rights and makes it easy for you to exercise them.
      </p>

      <h2>2. Right of Access</h2>
      <p>
        You have the right to know what personal data we process about you. You can request a copy of all data we hold about you. We will respond to your request within 30 days.
      </p>

      <h2>3. Right to Rectification</h2>
      <p>
        If your personal data is inaccurate or incomplete, you have the right to request correction. You can update most data directly in your account settings.
      </p>

      <h2>4. Right to Erasure</h2>
      <p>
        You have the right to request deletion of your personal data ("right to be forgotten"). This includes:
      </p>
      <ul>
        <li>Deletion of your account and all associated data</li>
        <li>Deletion of uploaded documents and financial data</li>
        <li>Deletion of usage data and log files</li>
      </ul>
      <p>
        <strong>Note:</strong> We may need to retain some data due to legal obligations (e.g., tax retention requirements).
      </p>

      <h2>5. Right to Restriction of Processing</h2>
      <p>
        You can request that we restrict the processing of your data while a dispute is being resolved or when you have objected to processing.
      </p>

      <h2>6. Right to Data Portability</h2>
      <p>
        You have the right to receive your data in a structured, commonly used, and machine-readable format. FAB provides export functionality that allows you to download your financial data in standard formats (CSV, PDF).
      </p>

      <h2>7. Right to Object</h2>
      <p>
        You have the right to object to the processing of your personal data based on our legitimate interest. We will cease processing unless we can demonstrate compelling legitimate grounds.
      </p>

      <h2>8. Rights Related to Automated Decision-Making</h2>
      <p>
        FAB uses AI for document categorization and financial insights. You have the right to:
      </p>
      <ul>
        <li>Be informed about automated decision-making</li>
        <li>Request human intervention</li>
        <li>Contest the decision</li>
      </ul>

      <h2>9. How to Exercise Your Rights</h2>
      <p>
        You can exercise your rights by:
      </p>
      <ul>
        <li>Contacting us through our <a href="/contact">contact page</a></li>
        <li>Sending an email with the subject "GDPR Request"</li>
        <li>Using your account settings for direct changes</li>
      </ul>
      <p>
        We will verify your identity before processing your request and respond within 30 days.
      </p>

      <h2>10. Complaints</h2>
      <p>
        If you are not satisfied with how we process your data, you have the right to file a complaint with the Autoriteit Persoonsgegevens (AP), the Dutch data protection authority.
      </p>
      <p>
        <strong>Autoriteit Persoonsgegevens</strong><br />
        Website: <a href="https://autoriteitpersoonsgegevens.nl" target="_blank" rel="noopener noreferrer">autoriteitpersoonsgegevens.nl</a>
      </p>

      <h2>11. Data Protection Officer</h2>
      <p>
        For questions about data protection, please contact us through our <a href="/contact">contact page</a> with the subject "Data Protection".
      </p>
    </LegalLayout>
  );
}
