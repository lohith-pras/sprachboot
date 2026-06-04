# Design — SprachBoot

Locked design system. Future Hallmark runs read this file first; pages defer
to it. Amend intentionally — the file is the rule. `website/css/tokens.css` is
the canonical token source; this file is the human-readable contract.

## System
- Genre · playful
- Macrostructure · Bento Grid (Hum loves it; also OK: Marquee Hero, Stat-Led, Narrative Workflow)
- Theme · catalog Hum (cream paper · pear + sky-cyan + coral multi-accent · rounded-sans)
- Axes · light (paper L 97%) / rounded-sans (Plus Jakarta Sans) / multi-accent
- Nav · N1b SaaS three-section (frost-on-scroll). Footer · Ft8 marquee.

## Tokens (canonical · `website/css/tokens.css` is the source of truth)
```css
:root {
  --color-paper:        oklch(97% 0.012 95);   /* cream — never pure white */
  --color-paper-2:      oklch(94% 0.016 95);
  --color-paper-3:      oklch(91% 0.020 95);
  --color-ink:          oklch(20% 0.012 250);  /* near-black — never pure black */
  --color-ink-2:        oklch(42% 0.014 250);
  --color-rule:         oklch(20% 0.012 250 / 0.12);

  --color-accent:       oklch(86% 0.18 95);    /* pear — primary action */
  --color-accent-deep:  oklch(76% 0.20 95);    /* button edge / cast */
  --color-accent-2:     oklch(66% 0.18 235);   /* cyan — links / hover tint */
  --color-accent-3:     oklch(68% 0.24 18);    /* coral — single pop per page */
  --color-accent-ink:   oklch(20% 0.012 250);  /* ink reads on pear; paper reads on coral/cyan */
  --color-focus:        oklch(60% 0.19 235);

  --font-display: "Plus Jakarta Sans", "Geist", system-ui, sans-serif;
  --font-body:    "Plus Jakarta Sans", "Geist", system-ui, sans-serif;
  --font-mono:    "JetBrains Mono", ui-monospace, monospace;

  /* 4-pt spacing scale: --space-2xs … --space-4xl. See tokens.css.        */
  /* Type scale, fluid clamp: --text-xs … --text-display + --text-counter. */

  --ease-spring: cubic-bezier(0.34, 1.56, 0.64, 1);  /* card lift only */
  --ease-snap:   cubic-bezier(0.22, 1, 0.36, 1);     /* tick-ups, reveals */
  --ease-press:  cubic-bezier(0.2, 0.7, 0.3, 1);     /* button press */
  --ease-out:    cubic-bezier(0.16, 1, 0.3, 1);
  --dur-short: 140ms;  --dur-mid: 220ms;  --dur-long: 600ms;

  --radius-card: 20px;  --radius-pill: 999px;  --radius-input: 12px;
}
```

## CTA voice
- Primary · pear fill (`--color-accent`) · pill radius · solid colour EDGE + soft ground shadow · press DOWN on `:active` (the press is the feedback). Never `scale()`, never spring overshoot.
- Secondary · `.btn--soft` (flat lift) or `.btn--outline` (hairline, accent fills on hover) · same pill radius.
- Coral is the single high-energy pop — one moment per page, never a second primary.

## Motion stance
- Loud-but-disciplined: card lift on hover · one counter tick-up · one star-burst on primary action · one character mark that pulses. Cap one CTA wobble + one character moment per page.
- Reduced-motion fallback · animations off, counters render final value, ≤150 ms opacity crossfade.

## Rules carried from Hum (non-negotiable)
- No serif anywhere · no pure white/black · no square corners · no accent-to-accent gradients · no invented metrics · bento ≤ 8 tiles.

## Exports
`website/css/tokens.css` is the source of truth. For Tailwind v4 `@theme`,
DTCG `tokens.json`, or shadcn/ui CSS variables, say *"extend design.md with
Tailwind exports"* (or the format you want) — Hallmark appends them.
