import LegalLayout from "@/components/LegalLayout";
import { useLanguage } from "@/contexts/LanguageContext";

export default function CookiePolicy() {
  const { lang } = useLanguage();

  if (lang === "nl") {
    return (
      <LegalLayout title="Cookiebeleid" lastUpdated="4 maart 2026">
        <h2>1. Wat Zijn Cookies</h2>
        <p>
          Cookies zijn kleine tekstbestanden die op uw apparaat worden geplaatst wanneer u onze website bezoekt. Ze helpen ons de website goed te laten werken, de beveiliging te verbeteren en te begrijpen hoe onze dienst wordt gebruikt.
        </p>

        <h2>2. Cookies Die Wij Gebruiken</h2>
        <h3>2.1 Strikt Noodzakelijke Cookies</h3>
        <p>
          Deze cookies zijn essentieel voor het functioneren van de website. Zonder deze cookies kunnen basisfuncties zoals inloggen en beveiliging niet werken. Deze cookies kunnen niet worden uitgeschakeld.
        </p>
        <ul>
          <li><strong>Sessiecookie:</strong> Houdt uw inlogstatus bij (verloopt bij het sluiten van de browser of na de sessieduur)</li>
          <li><strong>CSRF-token:</strong> Beschermt tegen cross-site request forgery-aanvallen</li>
          <li><strong>Taalvoorkeur:</strong> Onthoudt uw gekozen taal (Engels of Nederlands)</li>
        </ul>

        <h3>2.2 Functionele Cookies</h3>
        <p>
          Deze cookies onthouden uw voorkeuren en instellingen om uw ervaring te verbeteren:
        </p>
        <ul>
          <li><strong>Themavoorkeur:</strong> Onthoudt uw weergave-instellingen</li>
          <li><strong>Formuliergegevens:</strong> Onthoudt tijdelijk ingevulde formuliergegevens</li>
        </ul>

        <h3>2.3 Analytische Cookies</h3>
        <p>
          Wij gebruiken analytische cookies om te begrijpen hoe bezoekers onze website gebruiken. Deze gegevens helpen ons de website te verbeteren. De verzamelde gegevens zijn geanonimiseerd.
        </p>

        <h3>2.4 Cookies van Derden</h3>
        <p>
          Onze betalingsverwerker Stripe kan cookies plaatsen wanneer u een betaling verricht. Deze cookies vallen onder het privacybeleid van Stripe.
        </p>

        <h2>3. Cookiebeheer</h2>
        <p>
          U kunt cookies beheren via uw browserinstellingen. De meeste browsers bieden de mogelijkheid om:
        </p>
        <ul>
          <li>Alle cookies te blokkeren</li>
          <li>Cookies van derden te blokkeren</li>
          <li>Een melding te ontvangen wanneer een cookie wordt geplaatst</li>
          <li>Alle cookies te verwijderen bij het sluiten van de browser</li>
        </ul>
        <p>
          <strong>Let op:</strong> Het blokkeren van strikt noodzakelijke cookies kan ervoor zorgen dat de website niet goed functioneert.
        </p>

        <h2>4. Meer Informatie</h2>
        <p>
          Voor meer informatie over cookies en hoe u ze kunt beheren, bezoek <a href="https://www.allaboutcookies.org" target="_blank" rel="noopener noreferrer">allaboutcookies.org</a>.
        </p>
        <p>
          Voor vragen over ons cookiebeleid kunt u contact met ons opnemen via onze <a href="/contact">contactpagina</a>.
        </p>
      </LegalLayout>
    );
  }

  return (
    <LegalLayout title="Cookie Policy" lastUpdated="March 4, 2026">
      <h2>1. What Are Cookies</h2>
      <p>
        Cookies are small text files placed on your device when you visit our website. They help us make the website function properly, improve security, and understand how our service is used.
      </p>

      <h2>2. Cookies We Use</h2>
      <h3>2.1 Strictly Necessary Cookies</h3>
      <p>
        These cookies are essential for the website to function. Without them, basic features like login and security cannot work. These cookies cannot be disabled.
      </p>
      <ul>
        <li><strong>Session cookie:</strong> Maintains your login status (expires when browser closes or after session duration)</li>
        <li><strong>CSRF token:</strong> Protects against cross-site request forgery attacks</li>
        <li><strong>Language preference:</strong> Remembers your chosen language (English or Dutch)</li>
      </ul>

      <h3>2.2 Functional Cookies</h3>
      <p>
        These cookies remember your preferences and settings to improve your experience:
      </p>
      <ul>
        <li><strong>Theme preference:</strong> Remembers your display settings</li>
        <li><strong>Form data:</strong> Temporarily remembers filled-in form data</li>
      </ul>

      <h3>2.3 Analytical Cookies</h3>
      <p>
        We use analytical cookies to understand how visitors use our website. This data helps us improve the website. The collected data is anonymized.
      </p>

      <h3>2.4 Third-Party Cookies</h3>
      <p>
        Our payment processor Stripe may place cookies when you make a payment. These cookies are subject to Stripe's privacy policy.
      </p>

      <h2>3. Cookie Management</h2>
      <p>
        You can manage cookies through your browser settings. Most browsers offer the ability to:
      </p>
      <ul>
        <li>Block all cookies</li>
        <li>Block third-party cookies</li>
        <li>Receive a notification when a cookie is placed</li>
        <li>Delete all cookies when closing the browser</li>
      </ul>
      <p>
        <strong>Note:</strong> Blocking strictly necessary cookies may prevent the website from functioning properly.
      </p>

      <h2>4. More Information</h2>
      <p>
        For more information about cookies and how to manage them, visit <a href="https://www.allaboutcookies.org" target="_blank" rel="noopener noreferrer">allaboutcookies.org</a>.
      </p>
      <p>
        For questions about our cookie policy, please contact us through our <a href="/contact">contact page</a>.
      </p>
    </LegalLayout>
  );
}
