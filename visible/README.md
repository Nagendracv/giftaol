# Visible: Art of Living in AI search

Hackathon MVP for problem statement #7, "Make Art of Living discoverable in AI search".

When someone in Canada asks an AI assistant "where can I learn meditation in Toronto", Art of Living does not show up. Visible measures that, works out what would change it, generates the fixes, gives AI assistants a direct line to the program catalog, and re-tests.

## What is real and what is simulated

| Piece | Status |
|---|---|
| Baseline audit (54 questions: 49 everyday + 5 using our name; 31 cities, every province, 7 in French) | **Real.** Run on 2026-11-14 through a live web search engine, the retrieval layer AI assistants use for grounded answers. Result: **8 of 49** everyday questions surface Art of Living; **5 of 5** branded ones do. Every hit was in a city with its own centre page or matched a retreat listing on a booking site. |
| Program catalog (15 programs, 5 centres) | **Real** names, levels and URLs from artofliving.org/ca-en/programs. Descriptions are short paraphrases. Dates and prices were not on the page. |
| Site check (meta tags, llms.txt, robots.txt, junk indexed pages) | **Real**, fetched 2026-11-14. |
| Projected share of voice in the lift plan | **Simulated.** Uses stated planning assumptions (e.g. a listing gets you into 35% of the questions where that site ranks). Marked SIMULATED in the UI. |
| FAQ answers and listings (English and French) | **Drafts** generated from the catalog. A teacher confirms them before publishing. |
| Live re-test | Real when `ANTHROPIC_API_KEY` is set: asks Claude with web search, located in Canada, and saves the run. |

## The strategy for raising the score

The audit shows AI answers for these questions are built from **listing sites** (Eventbrite in 24 of 49, Meetup 17, BookRetreats 15, Coursetakers 12) and competitors (Shambhala, Sri Chinmoy). Art of Living came up only where it already has a city centre page (Markham, Richmond Hill, Kitchener-Waterloo, Sherbrooke) or a retreat listing (Retreat Guru). That is direct evidence the two main levers work.

So the plan, ranked by questions reached ÷ effort:
1. **Be where AI already reads.** Post the intro workshop and Part 1 on Eventbrite, Coursetakers, Meetup per city, and Part 2 on BookRetreats. Visible generates the listing copy.
2. **Fix indexing hygiene.** Meta descriptions, retire pages titled "i 504" / "home 4" / "events old", publish a Canada llms.txt.
3. **City pages** per centre with Course, Place and FAQ schema, worded like the real questions.
4. **Answer pages** for the intents with zero presence: anxiety, sleep, breathwork, students, retreats.
5. **Directories, civic calendars, campus wellness pages and press pitches.**
6. **Direct AI access** through the MCP server and open feed, for assistants that call tools.

Then re-test, and the real number replaces the projection.

## How is this different from Semrush?

Semrush tells a marketing team how a brand scores in AI search. Visible tells the volunteer in Sherbrooke what to post tonight, writes it in English and French, posts it once they approve it, and then checks whether chatbots now send people to that event.

| | Semrush and similar tools | Visible |
|---|---|---|
| Built for | Marketing teams | Volunteers and local centre teams |
| Unit of work | A brand's overall score | One city, one event |
| After the score | A report | Ready-to-post listings, a review step, an Eventbrite draft |
| Proof | Score over time | "Did chatbots point to this event?" plus registrations |
| Wrong facts | Not checked against your own facts | Each claim checked against the approved course list |
| Language | English-first | English and French |
| Cost | Paid subscription | Open source, free to run |

## Post an event (tab 3)

Fill in the event once. Visible writes the listing for Eventbrite, Meetup, Google Business Profile and Instagram, in the order chatbots use them (Instagram last; chatbots rarely cite it). A volunteer must tick "I checked the date, place and wording" and add their name before anything can be copied or posted.

- **Eventbrite:** posted through Eventbrite's official API as a **draft** event with a free ticket. Visible never sets an event live; the volunteer opens the draft in Eventbrite and publishes it. Needs `EVENTBRITE_TOKEN` (the centre's private token) and optionally `EVENTBRITE_ORG_ID`. Tested against a mocked API until a real token is added.
- **Meetup:** ready to paste. Posting through Meetup's API needs a paid Meetup Pro account.
- **Google Business Profile** and **Instagram:** ready to paste, with a link to open each site.

## How's my event doing? (tab 4)

Paste the link of a posted event (Eventbrite drafts are added automatically). "Check now" asks a chatbot the questions a newcomer in that city would ask and records whether the answer pointed to that exact event page. For Eventbrite events it also reads registrations. Eventbrite's API does not share page views, so those stay in the Eventbrite dashboard. "Ask Visible" answers "how is the Calgary intro doing?" in one plain sentence.

The worked example (Canada Centre retreats on Retreat Guru) is checked against the real 54-question audit: chatbots pointed to it for 4 of 54 questions.

## City report cards

`report/<city>.html`: one printable page per audited city (31 cities): what people there asked, where they were sent, and a to-do list for this week with the listing text ready to paste.

## Run it

```bash
npm install
npm start            # dashboard on http://localhost:3000
npm test             # 8 tests
npm run audit        # live re-test (needs ANTHROPIC_API_KEY)
npm run mcp          # MCP server over stdio
npm run build:static # static demo into docs/ (GitHub Pages)
```

**Hosting.** `docs/` is a static copy of the dashboard (audit, lift plan, fixes, client-side program search) for GitHub Pages: Settings > Pages > Deploy from branch `main`, folder `/docs`. The MCP endpoint and live re-test need the Node server (`npm start`) on any Node host; `vercel.json` and `api/index.js` are included if you use Vercel.

Endpoints: `/api/programs?topic=anxiety&city=Toronto`, `/api/programs/:id`, `/feed.json`, `/llms.txt`, `/fixes/city/<centre>.html`, MCP over HTTP at `/mcp`.

## Demo script (3 minutes)

1. **How we're doing:** 8 of 49 everyday questions vs 5 of 5 branded. Show the province map, then "where we did come up, and why": only where we have a centre page or a listing.
2. **Lift plan tab:** tick actions and watch the simulated score move; explain it is evidence-ranked from the audit.
3. **Fixes tab:** open the Toronto city page preview, the FAQ schema, and copy one Eventbrite listing.
4. **AI feed tab:** search "anxiety" + "Toronto"; then show the same tool called from Claude through MCP.
5. **Re-test tab:** run history; after fixes go live, run again for a real before/after.

## Live features (need `ANTHROPIC_API_KEY`)

- **Try it yourself:** ask any question; see the chatbot's actual answer, the sources it used, and whether Art of Living came up.
- **Wrong-answer check:** when the answer mentions Art of Living, each claim is compared with the official catalog (correct, wrong, or not in our facts). The check uses only our fact sheet, never outside knowledge.
- **Re-test:** asks all 54 questions again and adds a dated row to "Track progress".

## Layout

```
data/            programs.json, site-facts.json, queries.json, audits/*.json (every run)
src/audit/       live audit runner (Claude + web search) and response parser
src/score.js     share of voice, by city and intent, source families
src/lift/        ranked action plan and projection
src/fixes/       JSON-LD, FAQ, llms.txt, city pages, listing kit
src/feed/        program search and MCP server
public/          dashboard
server.js        HTTP server (no framework)
```
