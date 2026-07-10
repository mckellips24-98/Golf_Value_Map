# Golf Value Map — MN Golf Card + PCC Course Explorer

A free, mobile-friendly web app that maps every **Minnesota Golf Card** course and
every **Public Country Club (PCC)** course, flags the ones in **both** programs,
and helps you decide where to play today.

No accounts. No database. No monthly fees. Just files you own.

---

## What's in this folder

| File | What it is | Do you edit it? |
|---|---|---|
| `index.html` | The page structure | Rarely |
| `styles.css` | Colors, fonts, layout | Only if you want a new look |
| `app.js` | All the app logic | Rarely |
| `data/courses.js` | **All course data** — the file the app actually loads | **Yes** |
| `data/courses.json` | Same data as plain JSON (for validating / reuse) | Optional |
| `build_data.py` | Optional helper that regenerates both data files from tidy lists | Optional |
| `README.md` | This file | — |

---

## Run it on your computer (10 seconds)

Just **double-click `index.html`** — it opens in your browser and works
immediately, courses and all. No server, no setup.

(The app loads its data from `data/courses.js` through a `<script>` tag, which
is why double-clicking works. An earlier common gotcha — a blank course list
when opening the file directly — came from loading data a different way; this
version avoids it. You need an internet connection the first time so the map
tiles and map library can load.)

---

## Put it online with GitHub Pages (free, ~10 minutes)

1. Create a free account at **github.com** if you don't have one.
2. Click the **+** (top right) → **New repository**.
   - Name it something like `golf-value-map`
   - Keep it **Public**
   - Click **Create repository**
3. On the new repo page, click **uploading an existing file**.
4. Drag in **everything in this folder** (including the `data` folder with
   `courses.js` inside it) and click **Commit changes**.
5. Go to **Settings → Pages** (left sidebar).
6. Under **Branch**, choose `main` and folder `/ (root)`, then **Save**.
7. Wait ~1 minute, refresh the page, and GitHub shows your live link:
   `https://YOUR-USERNAME.github.io/golf-value-map/`

Send that link to your friends. It works on any phone — no app store needed.

**To update later:** edit the file on GitHub (open the file → pencil icon →
Commit changes). The live site updates automatically within a minute.

---

## Updating course data each season

Everything the app shows comes from `data/courses.js`. Two ways to update:

### Option A — edit the data file directly (simplest)
Open `data/courses.js`. The very first line is `window.GVM_DATA =` and the very
last line is `;` — **leave those two lines alone**. Everything between them is
ordinary JSON you can edit. Each course looks like this:

```json
{
  "id": "benson-golf-club",
  "name": "Benson Golf Club",
  "city": "Benson",
  "state": "MN",
  "lat": 45.315,
  "lng": -95.6,
  "coordSource": "city-approximate",
  "address": "2222 Atlantic Ave, Benson, MN 56215",
  "phone": "320-842-7901",
  "website": "https://www.bensongolfclub.com",
  "par": "72",
  "mgc": {
    "level": "A",
    "levelText": "Valid anytime. Holidays and July 3-5 not included.",
    "cartCodes": ["1", "2", "6"],
    "cartNotes": ["No golf cart discount", "No driving range discount", "Power cart required"],
    "rideARound": false,
    "offer": "2-for-1: one free 18-hole green fee..."
  },
  "pcc": { "tier": "1", "tierText": "Tier 1: ...", "note": "" }
}
```

Rules of thumb:
- A course **only on the Golf Card** has `"pcc": null`.
- A course **only in PCC** has `"mgc": null`.
- A course in **both** has both filled in.
- To add a course, copy an existing block, paste it, and change the values.
  Give it a unique `"id"` (lowercase, hyphens, no spaces).
- **Watch your commas** — every block needs a comma after it except the last one
  in the list. If the course list comes up empty after an edit, a stray or
  missing comma is the usual cause. To check: copy everything **between** the
  first line and the last `;` and paste it into https://jsonlint.com — it points
  to the exact line. (Or just edit `data/courses.json`, validate it there, and
  run `build_data.py` to regenerate `courses.js`.)

### Option B — regenerate with the Python script
If you're comfortable running one command, edit the tidy lists at the top of
`build_data.py` (they read like a spreadsheet), then run:
```
python3 build_data.py
```
It rewrites `data/courses.json` for you and checks for missing coordinates and
duplicate names.

### Making map pins exact
Pins currently use **city-level coordinates** so every course appears on the map
immediately. To make a pin exact:
1. Find the course on Google Maps and right-click the clubhouse.
2. Click the coordinates to copy them (e.g. `45.3182, -95.6011`).
3. In `data/courses.js`, paste them into that course's `"lat"` and `"lng"` and
   change `"coordSource"` to `"exact"`.

---

## What's saved on your phone

Favorites, notes, and the savings log are stored in your **browser's local
storage** — private to your device, free, and no login. Clearing your browser
data erases them, and they don't sync between devices. Friends who open your
link get their own favorites and savings log.

## Sharing a shortlist

Pick 2–4 courses with **+ Compare** (or favorite a few), then hit
**Share this shortlist** in the Compare tab. It creates a link like
`...?list=benson-golf-club,red-wing-golf-club` that opens the app pre-filtered
to just those courses — perfect for planning with your foursome.

---

## Honest limitations

- **Restriction badges and "Playable now" are estimates** parsed from each
  program's published rules. Courses change policies mid-season. Always confirm
  before driving out.
- **PCC-only courses** don't list phone/address/website on the PCC site, so
  those fields are blank until you fill them in (the app shows a note where
  data is missing).
- Data was pulled from minnesotagolfcard.com and thepubliccc.com in **July 2026**.
  Neither site offers an official data feed, so future updates are manual —
  usually a once-a-season, 30-minute job.
- This is an unofficial fan-made tool, not affiliated with either program.
