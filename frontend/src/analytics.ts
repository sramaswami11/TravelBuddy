declare global {
  function gtag(...args: unknown[]): void;
}

export function trackAffiliateClick(linkType: string, destination: string): void {
  if (typeof gtag === 'undefined') return;
  gtag('event', 'affiliate_click', { link_type: linkType, destination });
}

export function trackSearch(origin: string, budgetUsd: number, durationDays: number): void {
  if (typeof gtag === 'undefined') return;
  gtag('event', 'search_submitted', { origin, budget_usd: budgetUsd, duration_days: durationDays });
}
