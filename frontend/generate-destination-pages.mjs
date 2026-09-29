import { readFileSync, writeFileSync, mkdirSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));

const destinations = JSON.parse(
  readFileSync(join(__dirname, '../backend/data/destinations.json'), 'utf8')
);

function toSlug(city) {
  return city.toLowerCase().replace(/\s+/g, '-').replace(/[^a-z0-9-]/g, '');
}

function estimatedFlight(region) {
  return region === 'domestic' ? 299 : 499;
}

function locationLabel(dest) {
  return dest.state ? `${dest.city}, ${dest.state}` : `${dest.city}, ${dest.country}`;
}

function generatePage(dest) {
  const slug = toSlug(dest.city);
  const flight = estimatedFlight(dest.region);
  const hotel7 = dest.avg_hotel_per_night * 7;
  const car7 = dest.avg_car_per_day * 7;
  const total = flight + hotel7 + car7;
  const loc = locationLabel(dest);
  const tagLine = dest.tags.slice(0, 3).map(t => t.charAt(0).toUpperCase() + t.slice(1)).join(' · ');
  const metaDesc = `Plan a trip to ${dest.city}. Estimated 7-day cost from $${total.toLocaleString()} including round-trip flights, hotel, and car rental. Top attractions: ${dest.popular_attractions.slice(0, 2).join(', ')} and more.`;

  const attractionsJsonLd = dest.popular_attractions
    .map(a => `      { "@type": "TouristAttraction", "name": "${a}" }`)
    .join(',\n');

  const attractionItems = dest.popular_attractions
    .map(a => `      <li>${a}</li>`)
    .join('\n');

  const tagChips = dest.tags
    .map(t => `    <span class="tag">${t}</span>`)
    .join('\n');

  return `<!doctype html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Trip to ${dest.city}: Flights, Hotels &amp; Activities — packedNbooked</title>
  <meta name="description" content="${metaDesc}" />
  <link rel="canonical" href="https://packednbooked.com/trips/${slug}/" />
  <link rel="icon" type="image/svg+xml" href="/favicon.svg" />

  <meta property="og:type" content="website" />
  <meta property="og:url" content="https://packednbooked.com/trips/${slug}/" />
  <meta property="og:site_name" content="packedNbooked" />
  <meta property="og:title" content="Trip to ${dest.city}: Flights, Hotels &amp; Activities — packedNbooked" />
  <meta property="og:description" content="${metaDesc}" />
  <meta property="og:image" content="https://packednbooked.com/og-image.png" />

  <meta name="twitter:card" content="summary_large_image" />
  <meta name="twitter:title" content="Trip to ${dest.city}: Flights, Hotels &amp; Activities — packedNbooked" />
  <meta name="twitter:description" content="${metaDesc}" />
  <meta name="twitter:image" content="https://packednbooked.com/og-image.png" />

  <script async src="https://www.googletagmanager.com/gtag/js?id=G-WMRHM2T8MD"></script>
  <script>
    window.dataLayer = window.dataLayer || [];
    function gtag(){dataLayer.push(arguments);}
    gtag('js', new Date());
    gtag('config', 'G-WMRHM2T8MD');
  </script>

  <script type="application/ld+json">
  {
    "@context": "https://schema.org",
    "@type": "TouristDestination",
    "name": "${dest.city}",
    "description": "${metaDesc}",
    "url": "https://packednbooked.com/trips/${slug}/",
    "touristType": ${JSON.stringify(dest.tags)},
    "includesAttraction": [
${attractionsJsonLd}
    ]
  }
  </script>

  <style>
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f9fafb; color: #111827; line-height: 1.6; }
    a { color: inherit; text-decoration: none; }

    /* Nav */
    .nav { background: #1e1b4b; padding: .875rem 1rem; }
    .nav-inner { max-width: 900px; margin: 0 auto; display: flex; align-items: center; justify-content: space-between; }
    .brand { font-size: 1.15rem; font-weight: 900; color: white; letter-spacing: -.01em; }
    .brand span { color: #fbbf24; }
    .nav-cta { background: #fbbf24; color: #1e1b4b; font-weight: 700; font-size: .85rem; padding: .4rem 1rem; border-radius: .5rem; }
    .nav-cta:hover { background: #f59e0b; }

    /* Hero */
    .hero { background: linear-gradient(135deg, #1e1b4b 0%, #3730a3 55%, #4f46e5 100%); color: white; padding: 4rem 1rem 3.5rem; text-align: center; }
    .hero h1 { font-size: clamp(2rem, 5vw, 3.25rem); font-weight: 900; line-height: 1.1; }
    .hero-sub { color: #c7d2fe; margin-top: .5rem; font-size: 1rem; }
    .tags { display: flex; flex-wrap: wrap; gap: .5rem; justify-content: center; margin-top: 1.25rem; }
    .tag { background: rgba(255,255,255,.15); border-radius: 999px; padding: .25rem .8rem; font-size: .8rem; font-weight: 500; text-transform: capitalize; }
    .hero-cta { display: inline-block; margin-top: 2rem; background: #fbbf24; color: #1e1b4b; font-weight: 800; font-size: 1rem; padding: .875rem 2.25rem; border-radius: .75rem; }
    .hero-cta:hover { background: #f59e0b; }

    /* Content */
    .container { max-width: 860px; margin: 0 auto; padding: 2.5rem 1rem 3rem; }
    .card { background: white; border-radius: 1rem; padding: 1.75rem; margin-bottom: 1.5rem; box-shadow: 0 1px 4px rgba(0,0,0,.07); }
    .card h2 { font-size: 1.15rem; font-weight: 700; color: #1e1b4b; margin-bottom: 1.25rem; }

    /* Cost table */
    .cost-table { width: 100%; border-collapse: collapse; }
    .cost-table td { padding: .55rem 0; font-size: .95rem; color: #374151; vertical-align: middle; }
    .cost-table td + td { text-align: right; font-weight: 600; }
    .cost-table tr:not(:last-child) td { border-bottom: 1px solid #f3f4f6; }
    .cost-table .total td { font-size: 1.05rem; font-weight: 800; color: #4f46e5; padding-top: .9rem; border-top: 2px solid #e0e7ff; border-bottom: none; }
    .cost-note { font-size: .78rem; color: #9ca3af; margin-top: .9rem; }

    /* Attractions */
    .attraction-list { list-style: none; display: grid; grid-template-columns: repeat(auto-fill, minmax(190px, 1fr)); gap: .6rem; }
    .attraction-list li { background: #f3f4f6; border-radius: .6rem; padding: .65rem 1rem; font-size: .9rem; font-weight: 500; color: #374151; }
    .attraction-list li::before { content: "★ "; color: #fbbf24; }

    /* Bottom CTA */
    .bottom-cta { text-align: center; padding: 1.5rem 0 .5rem; }
    .bottom-cta p { color: #6b7280; margin-bottom: 1.1rem; font-size: .95rem; }
    .btn { display: inline-block; background: #4f46e5; color: white; font-weight: 700; font-size: 1rem; padding: .875rem 2.25rem; border-radius: .75rem; }
    .btn:hover { background: #4338ca; }

    /* Footer */
    footer { background: white; border-top: 1px solid #e5e7eb; padding: 1.75rem 1rem; text-align: center; font-size: .85rem; color: #6b7280; }
    .footer-brand { font-weight: 900; color: #1f2937; font-size: 1rem; }
    .footer-brand span { color: #f59e0b; }
    .footer-links { margin-top: .5rem; }
    .footer-links a { margin: 0 .75rem; }
    .footer-links a:hover { color: #4f46e5; }
    .footer-legal { margin-top: .5rem; font-size: .78rem; }
  </style>
</head>
<body>

<nav class="nav">
  <div class="nav-inner">
    <a href="/" class="brand">packed<span>N</span>booked</a>
    <a href="/" class="nav-cta">Plan a trip &rarr;</a>
  </div>
</nav>

<section class="hero">
  <h1>Trip to ${dest.city}</h1>
  <p class="hero-sub">${loc} &nbsp;&middot;&nbsp; ${tagLine}</p>
  <div class="tags">
${tagChips}
  </div>
  <a href="/" class="hero-cta">Plan my trip to ${dest.city} &rarr;</a>
</section>

<div class="container">

  <div class="card">
    <h2>Estimated 7-Day Trip Cost</h2>
    <table class="cost-table">
      <tr>
        <td>Flights (round trip, estimated)</td>
        <td>~$${flight.toLocaleString()}</td>
      </tr>
      <tr>
        <td>Hotel &nbsp;<small style="color:#9ca3af;font-weight:400">(7 nights &times; $${dest.avg_hotel_per_night}/night avg)</small></td>
        <td>~$${hotel7.toLocaleString()}</td>
      </tr>
      <tr>
        <td>Car rental &nbsp;<small style="color:#9ca3af;font-weight:400">(7 days &times; $${dest.avg_car_per_day}/day avg)</small></td>
        <td>~$${car7.toLocaleString()}</td>
      </tr>
      <tr class="total">
        <td>Estimated total (per person)</td>
        <td>~$${total.toLocaleString()}</td>
      </tr>
    </table>
    <p class="cost-note">Estimates are based on average market prices and vary by origin city, season, and how far in advance you book. Use packedNbooked to get real-time prices for your specific travel dates.</p>
  </div>

  <div class="card">
    <h2>Popular Attractions in ${dest.city}</h2>
    <ul class="attraction-list">
${attractionItems}
    </ul>
  </div>

  <div class="bottom-cta">
    <p>Enter your budget and departure city — we'll find the best complete trip to ${dest.city} for you.</p>
    <a href="/" class="btn">Find flights, hotels &amp; activities &rarr;</a>
  </div>

</div>

<footer>
  <div class="footer-brand">packed<span>N</span>booked</div>
  <div class="footer-links">
    <a href="/privacy">Privacy Policy</a>
    <a href="/terms">Terms of Use</a>
    <a href="mailto:hello@packednbooked.com">Contact</a>
  </div>
  <div class="footer-legal">&copy; ${new Date().getFullYear()} packedNbooked &nbsp;&middot;&nbsp; Some links on this site are affiliate links.</div>
</footer>

</body>
</html>`;
}

// Generate pages
const sitemapUrls = [];
for (const dest of destinations) {
  const slug = toSlug(dest.city);
  const dir = join(__dirname, 'public', 'trips', slug);
  mkdirSync(dir, { recursive: true });
  writeFileSync(join(dir, 'index.html'), generatePage(dest), 'utf8');
  sitemapUrls.push(`https://packednbooked.com/trips/${slug}/`);
  console.log(`  + /trips/${slug}/`);
}

// Update sitemap.xml
const destEntries = sitemapUrls
  .map(url => `  <url>\n    <loc>${url}</loc>\n    <changefreq>monthly</changefreq>\n    <priority>0.8</priority>\n  </url>`)
  .join('\n');

const sitemap = `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>https://packednbooked.com/</loc>
    <changefreq>weekly</changefreq>
    <priority>1.0</priority>
  </url>
  <url>
    <loc>https://packednbooked.com/privacy</loc>
    <changefreq>monthly</changefreq>
    <priority>0.3</priority>
  </url>
${destEntries}
</urlset>`;

writeFileSync(join(__dirname, 'public', 'sitemap.xml'), sitemap, 'utf8');
console.log(`\nGenerated ${destinations.length} destination pages + updated sitemap.xml`);
