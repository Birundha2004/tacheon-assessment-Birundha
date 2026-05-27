# Product Brief: Marketing Performance Intelligence Tool
**Version:** 1.0 (Scoping Document)  
**Author:** Birundha  
**Date:** May 2026  
**Status:** Proposed — v1 Scope

---

## The Problem

Right now, answering one simple question — *"How is our marketing performing across channels, and where should we focus?"* — takes too long and depends too much on one person.

Someone has to manually log into Google Analytics, pull Meta Ads data, check LinkedIn or email campaign stats, stitch it all together in a spreadsheet, and write a summary. The answer looks different every time depending on who does it. If that person is busy or unavailable, the question just sits unanswered.

This is a knowledge bottleneck masquerading as a reporting problem.

---

## The Goal

Build a lightweight internal tool that gives the team a consistent, reliable answer to that question — without changing how they currently work or the tools they already use.

The tool is intentionally designed to fit around existing workflows rather than requiring teams to adopt a new operational process.

---

## Who Is This For?

**Primary user: The internal analyst / account manager**

This person is the one currently doing the manual stitching. They're the bottleneck. The tool should make their job faster — not replace their judgment, but eliminate the grunt work of pulling and assembling numbers.

**Secondary user: The client-facing team member**

Someone who needs to walk into a client call knowing the current state of performance across channels. They don't need raw data — they need a clear summary they can speak to confidently.

I am deliberately **not** scoping this for direct client access in v1. Building a client-facing view adds complexity around branding, access control, and data trust that we don't need to solve yet. Get it right internally first.

---

## What the Tool Does in v1

The tool answers one question per brand, on demand:

> *"How is [Brand X] performing across [channels] this week / this month, and where should the team focus?"*

It does this by:

1. **Pulling data from connected marketing platforms** — whichever ones the team already uses (e.g. Google Analytics 4, Meta Ads Manager, Google Ads). No new tools, no new logins.
2. **Presenting a unified summary view** — key metrics per channel in one place: impressions, clicks, spend, conversions, CPC, ROAS — whatever is relevant per channel.
3. **Surfacing one or two signals worth acting on** — simple rule-based signals designed to surface notable performance changes: e.g. "Spend is up 30% but conversions are flat — worth investigating Meta," or "Organic is outperforming paid this week."
4. **Showing a last-refreshed timestamp** — so the user always knows how current the data is.

That's it. No predictions. No auto-generated reports. No client portal. Just a fast, consistent answer to the question the team is already asking every week.

---

## What a Successful Interaction Looks Like

An analyst opens the tool, selects a brand and a date range, and within 30 seconds sees:

- This week's performance across channels in a single view
- Which channel is over/underperforming relative to last week or last month
- One or two highlighted signals that suggest where to look next
- A clear data freshness indicator

They walk away knowing what to say on the client call — without opening four tabs, exporting two CSVs, or waiting for someone else to do it.

---

## Where the Data Comes From

| Channel | Source | How It Gets In |
|---|---|---|
| Website traffic | Google Analytics 4 | GA4 Data API (read-only) |
| Paid social | Meta Ads Manager | Meta Marketing API |
| Paid search | Google Ads | Google Ads API |
| Email (if used) | Mailchimp / HubSpot | Their respective APIs |

All connections use read-only API access. No data is written back to any platform. Credentials are stored securely and managed by one person on the team — this does not require every user to authenticate individually in v1.

**Data refresh:** Pulled on a schedule (e.g. every morning at 7am) and cached. The tool does not call APIs live on every page load — that would be slow and hit rate limits.

---

## Architecture Flow

```
Marketing APIs (GA4 / Meta Ads / Google Ads / Email)
                        ↓
           Scheduled Data Pull (daily 7am)
                        ↓
            Normalisation Layer
            (flatten, clean, derive metrics)
                        ↓
         Cached Performance Store
                        ↓
          Insight & Signal Engine
          (rule-based: flag anomalies)
                        ↓
       Internal Summary Interface
       (brand selector → channel view → one signal)
```

The architecture intentionally separates ingestion, normalisation, and presentation layers so additional channels can be added later without redesigning the entire system.

---

## How a User Interacts With It

The interface is intentionally simple:

```
[ Select Brand ▾ ]   [ Date Range ▾ ]   [ Refresh ]

─────────────────────────────────────────────
CHANNEL SUMMARY — Brand X — Last 7 days
─────────────────────────────────────────────
Google Ads       Spend: ₹12,400  |  ROAS: 3.2x  |  ↑ vs last week
Meta Ads         Spend: ₹8,200   |  ROAS: 1.8x  |  ↓ vs last week
Organic (GA4)    Sessions: 4,300 |  Conv: 2.1%  |  → stable

⚡ Signal: Meta spend increased 22% this week but ROAS dropped. Review creative.

Last updated: Today, 7:04am
─────────────────────────────────────────────
```

No charts in v1. No drill-downs. No exports. Just the numbers and one actionable signal. We can add more later once we know what the team actually uses.

---

## What I Am Explicitly Not Building in v1

| Feature | Why Not |
|---|---|
| Client-facing dashboard | Adds auth, branding, trust complexity — not needed to prove value internally |
| Automated PDF/email reports | Adds delivery infrastructure — manual sharing is fine for now |
| Predictive analytics or AI recommendations | Too early; we don't have enough trust in the data pipeline yet |
| Historical trend charts | Valuable, but not needed to answer the core question in v1 |
| Self-serve API connections by users | Security and complexity risk — one admin manages credentials in v1 |
| Multi-brand comparison view | Useful later; single-brand view is the core job to be done |

The principle: **if removing it doesn't break the core use case, it's not in v1.**

---

## What Would Make Users Trust This Tool

Trust is earned through consistency and transparency, not features.

- **Always show when data was last refreshed.** A stale number shown confidently is worse than no number.
- **Show the source for each metric.** "Google Ads API" not just "Paid Search."
- **Don't show a metric if the data pull failed.** Show an error state instead. Partial data presented as complete is the fastest way to lose trust.
- **Match the numbers to what the team already sees in the native tools** — at least in the first few weeks. Calibration matters.

---

## Success Metrics for v1

The tool is successful if:

- Analysts spend significantly less time preparing performance summaries
- Teams stop manually stitching together data from multiple platforms
- Users trust the data enough to rely on it during client discussions
- The same question receives a consistent answer regardless of who uses the tool

---

## What I Would Revisit With More Time

- Talk to 2–3 analysts and account managers before finalising the metric set. I've assumed ROAS, CPC, conversions — but the team may weight things differently per client.
- Understand how many brands and channels are actually in scope. The complexity of the API layer changes significantly at 3 brands vs 30.
- Explore whether a Slack bot or Google Sheets integration would serve the team better than a standalone web tool — given the constraint that they won't change their existing workflow.
- Define what "signal" means more precisely. The v1 rule-based approach is a placeholder for something smarter once we have data.

---

## Risks and Constraints

- Different platforms define metrics differently, which may create reporting inconsistencies
- API rate limits or downtime may affect refresh reliability
- Users may initially compare the tool against native platform dashboards, so metric consistency is important
- Some platforms may provide delayed or incomplete data depending on API limitations

---

## One-Page Summary

| | |
|---|---|
| **Core question answered** | How is marketing performing right now, and where should we focus? |
| **Primary user** | Internal analyst / account manager |
| **v1 format** | Internal web tool (or Slack bot — to validate) |
| **Data sources** | GA4, Meta Ads, Google Ads (read-only APIs) |
| **Refresh cadence** | Scheduled daily pull, cached |
| **What's in v1** | Per-brand channel summary + one actionable signal + data freshness |
| **What's not in v1** | Client portal, charts, predictions, automated reports |
| **Success metric** | Team stops manually pulling data for the weekly performance question |
