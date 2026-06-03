/**
 * Seed script: Insert initial blog posts into the database
 * Run with: node scripts/seed-blog.mjs
 */
import 'dotenv/config';
import mysql from 'mysql2/promise';

const DATABASE_URL = process.env.DATABASE_URL;

if (!DATABASE_URL) {
  console.error('DATABASE_URL is not set');
  process.exit(1);
}

const posts = [
  {
    title: "Introducing FAB: Financial Clarity for Everyone",
    titleNl: "Maak kennis met FAB: Financiële Helderheid voor Iedereen",
    slug: "introducing-fab",
    excerpt: "We're building FAB to solve a problem that affects over 1 million people in the Netherlands: the overwhelming complexity of managing finances while living with a disability or chronic illness.",
    excerptNl: "We bouwen FAB om een probleem op te lossen dat meer dan 1 miljoen mensen in Nederland treft: de overweldigende complexiteit van financieel beheer terwijl je leeft met een beperking of chronische ziekte.",
    content: `# Introducing FAB: Financial Clarity for Everyone

Managing finances shouldn't be a full-time job. Yet for hundreds of thousands of Dutch citizens living with disabilities or chronic illnesses, it often feels exactly like that.

## The Problem We're Solving

If you're a PGB holder, Wajong recipient, or WIA beneficiary, you know the struggle. Your financial life is scattered across:

- WhatsApp messages with care providers
- Email inboxes full of invoices
- Google Drive folders with receipts
- Multiple banking apps
- Government portals like MijnOverheid

Every week, you spend 4-8 hours just trying to keep track of it all. That's time you could spend on your health, your family, or simply living your life.

## What FAB Does Differently

FAB is not another bookkeeping app. It's a **financial orchestration platform** that:

1. **Connects** to your existing tools (email, WhatsApp, bank accounts, government portals)
2. **Processes** documents automatically using AI — receipts, invoices, statements
3. **Categorizes** everything into a unified financial picture
4. **Reports** with clarity, showing you exactly where your money goes

All of this happens with **end-to-end encryption** and **GDPR compliance** built in from day one.

## Built for the Dutch System

Unlike generic finance apps, FAB understands the Dutch healthcare and benefits system. It knows what a PGB declaration looks like. It understands WMO categories. It can distinguish between healthcare costs and household expenses.

## What's Next

We're currently in early development, building our MVP with a focus on PGB holders as our first user group. If you're interested in being among the first to try FAB, join our waitlist.

Together, we can make financial clarity accessible to everyone.`,
    contentNl: `# Maak kennis met FAB: Financiële Helderheid voor Iedereen

Financieel beheer zou geen fulltime baan moeten zijn. Toch voelt het voor honderdduizenden Nederlanders met een beperking of chronische ziekte vaak precies zo.

## Het Probleem dat We Oplossen

Als je PGB-houder, Wajong-ontvanger of WIA-gerechtigde bent, ken je de strijd. Je financiële leven is verspreid over:

- WhatsApp-berichten met zorgverleners
- E-mailinboxen vol facturen
- Google Drive-mappen met bonnetjes
- Meerdere bank-apps
- Overheidsportalen zoals MijnOverheid

Elke week besteed je 4-8 uur alleen al om alles bij te houden. Dat is tijd die je zou kunnen besteden aan je gezondheid, je familie, of gewoon aan het leven.

## Wat FAB Anders Doet

FAB is niet zomaar een boekhoudapp. Het is een **financieel orkestratieplatform** dat:

1. **Verbindt** met je bestaande tools (e-mail, WhatsApp, bankrekeningen, overheidsportalen)
2. **Verwerkt** documenten automatisch met AI — bonnetjes, facturen, afschriften
3. **Categoriseert** alles in een uniform financieel overzicht
4. **Rapporteert** met helderheid, zodat je precies ziet waar je geld naartoe gaat

Dit alles gebeurt met **end-to-end encryptie** en **AVG-compliance** vanaf dag één ingebouwd.

## Gebouwd voor het Nederlandse Systeem

In tegenstelling tot generieke financiële apps begrijpt FAB het Nederlandse zorg- en uitkeringssysteem. Het weet hoe een PGB-declaratie eruitziet. Het begrijpt WMO-categorieën. Het kan onderscheid maken tussen zorgkosten en huishoudelijke uitgaven.

## Wat Komt Er

We zijn momenteel in de vroege ontwikkelingsfase en bouwen onze MVP met een focus op PGB-houders als onze eerste gebruikersgroep. Als je geïnteresseerd bent om een van de eersten te zijn die FAB uitprobeert, schrijf je in op onze wachtlijst.

Samen kunnen we financiële helderheid toegankelijk maken voor iedereen.`,
    category: "announcement",
    published: true,
    readTimeMinutes: 4,
  },
  {
    title: "How AI Powers FAB's Document Processing",
    titleNl: "Hoe AI FAB's Documentverwerking Aandrijft",
    slug: "ai-document-processing",
    excerpt: "A deep dive into how FAB uses artificial intelligence to automatically extract, categorize, and organize financial documents from multiple sources.",
    excerptNl: "Een diepgaande blik op hoe FAB kunstmatige intelligentie gebruikt om automatisch financiële documenten uit meerdere bronnen te extraheren, categoriseren en organiseren.",
    content: `# How AI Powers FAB's Document Processing

One of FAB's core features is its ability to automatically process financial documents. But how does it actually work? Let's pull back the curtain on the technology that makes FAB tick.

## The Challenge of Unstructured Data

Financial documents come in all shapes and sizes:

- **PDF invoices** from healthcare providers
- **Photo receipts** snapped on your phone
- **Email confirmations** of bank transfers
- **WhatsApp messages** with payment details
- **Government letters** about benefit adjustments

Each of these has a different format, layout, and structure. Traditional bookkeeping software expects you to manually enter this data. FAB doesn't.

## Our Three-Stage AI Pipeline

### Stage 1: Extraction (OCR + NLP)

When a document enters FAB, our AI first extracts all readable text using advanced OCR (Optical Character Recognition). But we go beyond simple text extraction — our NLP (Natural Language Processing) models understand context.

For example, when processing a healthcare invoice, FAB identifies:
- The provider name and details
- The service date and description
- The amount and VAT breakdown
- The PGB or WMO category it belongs to

### Stage 2: Classification

Once extracted, the data is classified using our custom-trained models that understand Dutch financial categories:

- **Healthcare costs** (zorgkosten)
- **Housing expenses** (woonlasten)
- **Transportation** (vervoer)
- **Personal care** (persoonlijke verzorging)
- **And many more...**

Each classification comes with a confidence score. If the AI isn't sure, it flags the item for your review.

### Stage 3: Reconciliation

Finally, FAB cross-references the processed document against your bank statements and existing records. This catches duplicates, identifies missing payments, and ensures your books are always balanced.

## Privacy by Design

All AI processing happens with your privacy in mind:

- Documents are encrypted in transit and at rest
- Processing can happen on-device for sensitive documents
- No data is shared with third parties
- You can export or delete your data at any time

## What's Next for Our AI

We're continuously improving our models with a focus on:
- Better accuracy for handwritten receipts
- Faster processing times
- Support for more document types
- Multilingual support (starting with Dutch and English)

Stay tuned for more updates on our technology journey.`,
    contentNl: `# Hoe AI FAB's Documentverwerking Aandrijft

Een van FAB's kernfuncties is het vermogen om automatisch financiële documenten te verwerken. Maar hoe werkt het eigenlijk? Laten we een kijkje nemen achter de schermen van de technologie die FAB aandrijft.

## De Uitdaging van Ongestructureerde Data

Financiële documenten komen in alle soorten en maten:

- **PDF-facturen** van zorgverleners
- **Foto-bonnetjes** gemaakt met je telefoon
- **E-mailbevestigingen** van bankoverschrijvingen
- **WhatsApp-berichten** met betalingsgegevens
- **Overheidsbrieven** over uitkeringsaanpassingen

Elk van deze heeft een ander formaat, lay-out en structuur. Traditionele boekhoudsoftware verwacht dat je deze gegevens handmatig invoert. FAB niet.

## Onze Drietraps AI-Pipeline

### Fase 1: Extractie (OCR + NLP)

Wanneer een document FAB binnenkomt, extraheert onze AI eerst alle leesbare tekst met geavanceerde OCR (Optical Character Recognition). Maar we gaan verder dan simpele tekstextractie — onze NLP-modellen (Natural Language Processing) begrijpen context.

Bijvoorbeeld, bij het verwerken van een zorgfactuur identificeert FAB:
- De naam en gegevens van de zorgverlener
- De servicedatum en beschrijving
- Het bedrag en de BTW-specificatie
- De PGB- of WMO-categorie waartoe het behoort

### Fase 2: Classificatie

Na extractie worden de gegevens geclassificeerd met onze speciaal getrainde modellen die Nederlandse financiële categorieën begrijpen:

- **Zorgkosten**
- **Woonlasten**
- **Vervoer**
- **Persoonlijke verzorging**
- **En nog veel meer...**

Elke classificatie komt met een betrouwbaarheidsscore. Als de AI niet zeker is, markeert het het item voor jouw beoordeling.

### Fase 3: Reconciliatie

Tot slot vergelijkt FAB het verwerkte document met je bankafschriften en bestaande records. Dit vangt duplicaten op, identificeert ontbrekende betalingen en zorgt ervoor dat je boekhouding altijd klopt.

## Privacy by Design

Alle AI-verwerking gebeurt met je privacy in gedachten:

- Documenten zijn versleuteld tijdens transport en opslag
- Verwerking kan op het apparaat plaatsvinden voor gevoelige documenten
- Geen gegevens worden gedeeld met derden
- Je kunt je gegevens op elk moment exporteren of verwijderen

## Wat Komt Er voor Onze AI

We verbeteren continu onze modellen met focus op:
- Betere nauwkeurigheid voor handgeschreven bonnetjes
- Snellere verwerkingstijden
- Ondersteuning voor meer documenttypen
- Meertalige ondersteuning (beginnend met Nederlands en Engels)

Blijf op de hoogte voor meer updates over onze technologiereis.`,
    category: "technology",
    published: true,
    readTimeMinutes: 6,
  },
  {
    title: "Understanding PGB Financial Management: A Complete Guide",
    titleNl: "PGB Financieel Beheer Begrijpen: Een Complete Gids",
    slug: "pgb-financial-management-guide",
    excerpt: "Everything you need to know about managing your Persoonsgebonden Budget (PGB) finances, from declarations to budgeting, and how technology can help.",
    excerptNl: "Alles wat je moet weten over het beheren van je Persoonsgebonden Budget (PGB) financiën, van declaraties tot budgettering, en hoe technologie kan helpen.",
    content: `# Understanding PGB Financial Management: A Complete Guide

If you're a PGB (Persoonsgebonden Budget) holder in the Netherlands, you know that managing your budget comes with unique challenges. This guide covers everything you need to know about PGB financial management.

## What is a PGB?

A Persoonsgebonden Budget is a personal budget provided by the Dutch government or your health insurer that allows you to arrange and pay for your own care. Instead of receiving care directly from an institution, you receive funding to hire care providers of your choice.

## The Financial Complexity

Managing a PGB involves:

### 1. Budget Tracking
You need to track how much budget you have, how much you've spent, and how much remains. This sounds simple, but with multiple care providers and varying rates, it quickly becomes complex.

### 2. Declarations
Every payment to a care provider must be declared through the SVB (Sociale Verzekeringsbank). This means:
- Keeping accurate records of all care provided
- Submitting declarations on time
- Tracking which declarations have been approved or rejected

### 3. Care Agreements
Each care provider needs a formal care agreement (zorgovereenkomst) that specifies:
- The type of care provided
- The hourly rate
- The expected hours per week/month
- The duration of the agreement

### 4. Annual Accounting
At the end of each budget period, you need to account for all spending. Any unspent budget may need to be returned.

## Common Challenges

PGB holders frequently face:

- **Administrative overload**: Hours spent on paperwork instead of receiving care
- **Declaration delays**: Waiting weeks for SVB to process declarations
- **Budget uncertainty**: Not knowing exactly how much budget remains
- **Provider management**: Coordinating multiple care providers with different schedules and rates

## How FAB Can Help

FAB is designed specifically to address these challenges:

1. **Automatic tracking**: Connect your SVB account and bank to automatically track all PGB transactions
2. **Smart declarations**: AI-assisted declaration preparation that reduces errors
3. **Real-time budget view**: Always know exactly where your PGB stands
4. **Provider dashboard**: Manage all care agreements and provider payments in one place
5. **Compliance alerts**: Get notified before deadlines and when action is needed

## Tips for Better PGB Management

While waiting for FAB, here are some tips:

1. **Set up a separate bank account** for PGB transactions
2. **Create a simple spreadsheet** to track declarations
3. **Set calendar reminders** for declaration deadlines
4. **Keep digital copies** of all care agreements
5. **Review your budget monthly** to avoid surprises

## Join the FAB Waitlist

We're building FAB to make PGB management effortless. Join our waitlist to be among the first to experience financial clarity.`,
    contentNl: `# PGB Financieel Beheer Begrijpen: Een Complete Gids

Als je PGB-houder (Persoonsgebonden Budget) in Nederland bent, weet je dat het beheren van je budget unieke uitdagingen met zich meebrengt. Deze gids behandelt alles wat je moet weten over PGB financieel beheer.

## Wat is een PGB?

Een Persoonsgebonden Budget is een persoonlijk budget dat door de Nederlandse overheid of je zorgverzekeraar wordt verstrekt, waarmee je je eigen zorg kunt regelen en betalen. In plaats van zorg rechtstreeks van een instelling te ontvangen, ontvang je financiering om zorgverleners naar keuze in te huren.

## De Financiële Complexiteit

Het beheren van een PGB omvat:

### 1. Budgetbewaking
Je moet bijhouden hoeveel budget je hebt, hoeveel je hebt uitgegeven en hoeveel er overblijft. Dit klinkt eenvoudig, maar met meerdere zorgverleners en wisselende tarieven wordt het al snel complex.

### 2. Declaraties
Elke betaling aan een zorgverlener moet worden gedeclareerd via de SVB (Sociale Verzekeringsbank). Dit betekent:
- Nauwkeurige administratie bijhouden van alle verleende zorg
- Declaraties op tijd indienen
- Bijhouden welke declaraties zijn goedgekeurd of afgewezen

### 3. Zorgovereenkomsten
Elke zorgverlener heeft een formele zorgovereenkomst nodig die specificeert:
- Het type zorg dat wordt verleend
- Het uurtarief
- De verwachte uren per week/maand
- De duur van de overeenkomst

### 4. Jaarlijkse Verantwoording
Aan het einde van elke budgetperiode moet je alle uitgaven verantwoorden. Onbesteed budget moet mogelijk worden terugbetaald.

## Veelvoorkomende Uitdagingen

PGB-houders worden vaak geconfronteerd met:

- **Administratieve overbelasting**: Uren besteed aan papierwerk in plaats van zorg ontvangen
- **Declaratievertragingen**: Weken wachten tot de SVB declaraties verwerkt
- **Budgetonzekerheid**: Niet precies weten hoeveel budget er nog over is
- **Zorgverlenerbeheer**: Meerdere zorgverleners coördineren met verschillende roosters en tarieven

## Hoe FAB Kan Helpen

FAB is specifiek ontworpen om deze uitdagingen aan te pakken:

1. **Automatische tracking**: Verbind je SVB-account en bank om automatisch alle PGB-transacties bij te houden
2. **Slimme declaraties**: AI-ondersteunde declaratievoorbereiding die fouten vermindert
3. **Realtime budgetoverzicht**: Weet altijd precies waar je PGB staat
4. **Zorgverlenerdashboard**: Beheer alle zorgovereenkomsten en betalingen op één plek
5. **Compliance-meldingen**: Ontvang meldingen voor deadlines en wanneer actie nodig is

## Tips voor Beter PGB-Beheer

Terwijl je wacht op FAB, hier zijn enkele tips:

1. **Open een aparte bankrekening** voor PGB-transacties
2. **Maak een eenvoudig spreadsheet** om declaraties bij te houden
3. **Stel agendaherinneringen in** voor declaratiedeadlines
4. **Bewaar digitale kopieën** van alle zorgovereenkomsten
5. **Controleer je budget maandelijks** om verrassingen te voorkomen

## Schrijf Je In op de FAB Wachtlijst

We bouwen FAB om PGB-beheer moeiteloos te maken. Schrijf je in op onze wachtlijst om een van de eersten te zijn die financiële helderheid ervaart.`,
    category: "guide",
    published: true,
    readTimeMinutes: 7,
  },
];

async function seedBlog() {
  console.log('Connecting to database...');
  const connection = await mysql.createConnection(DATABASE_URL);
  
  for (const post of posts) {
    try {
      // Check if post already exists
      const [existing] = await connection.execute(
        'SELECT id FROM blog_posts WHERE slug = ?',
        [post.slug]
      );
      
      if (Array.isArray(existing) && existing.length > 0) {
        console.log(`Post "${post.slug}" already exists, skipping...`);
        continue;
      }

      await connection.execute(
        `INSERT INTO blog_posts (title, titleNl, slug, excerpt, excerptNl, content, contentNl, category, published, readTimeMinutes, publishedAt, createdAt, updatedAt)
         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NOW(), NOW(), NOW())`,
        [
          post.title,
          post.titleNl,
          post.slug,
          post.excerpt,
          post.excerptNl,
          post.content,
          post.contentNl,
          post.category,
          post.published ? 1 : 0,
          post.readTimeMinutes,
        ]
      );
      console.log(`Inserted: "${post.title}"`);
    } catch (err) {
      console.error(`Error inserting "${post.title}":`, err.message);
    }
  }

  await connection.end();
  console.log('Blog seeding complete!');
}

seedBlog().catch(console.error);
