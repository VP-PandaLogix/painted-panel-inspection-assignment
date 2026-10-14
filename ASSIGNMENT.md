# Take-home assignment — Painted-surface defect detection

**Role:** Computer Vision Engineer Trainee · PandaLogix™
**Time box:** 5 calendar days, starting the day you share your repository with us (step 3 below)
**AI tools:** Claude Code, Codex, Copilot and similar are **allowed and expected**. See §7.

---

## 0. Getting started

1. Click **Use this template → Create a new repository** (top right of this page). Create it
   under your own GitHub account. **Private is recommended.**
2. Clone it and download the dataset:
   ```bash
   bash scripts/get_dataset.sh        # downloads and unpacks into data/ (about 55 MB)
   ```
3. In your new repository go to **Settings → Collaborators → Add people**, add
   **`vijenderpanda`** with the **Write** role, and reply to the email that sent you this
   link with your repository URL. Your 5 days start then.
   *Why Write:* we open change requests as Issues in your repository and attach their data
   as a Release. **We never push to your branches.**
4. Replace `README.md` with your own (how to install and run your tool). This brief stays
   in `ASSIGNMENT.md`.

---

## 1. What a surface defect is

A surface defect is any local flaw in the finish of a part that a customer would see,
feel or reject — as opposed to a dimensional or assembly defect (wrong size, missing
screw). On a **painted** part the common ones are:

| defect | what it looks like | typical size |
| --- | --- | --- |
| **Dust / dirt inclusion** ("seed") | a small raised bump with a particle trapped in the paint | 0.3–2 mm |
| **Crater / fisheye** | a small round dish where paint pulled away from a contaminated spot | 0.5–3 mm |
| **Scratch** | a thin line, often only visible at a glancing angle | 0.1–0.5 mm wide, mm–cm long |
| **Run / sag** | a drip or curtain where too much paint flowed downwards | several mm |
| **Pinhole** | a tiny dark pit from trapped solvent or air | 0.2–0.5 mm |
| **Thin coat / bare spot** | lighter patch, or substrate showing through | varies |
| **Orange peel** | a bumpy, textured gloss instead of a mirror finish | whole-area texture |

Why this is hard, and why it is a good test of fundamentals:

- **Gloss is a mirror.** A shiny painted surface reflects the light source back into the
  camera only over a narrow band; elsewhere it looks dark. Highlights and reflections of
  the surroundings look like defects to a naïve algorithm.
- **Defects are tiny relative to the part.** A 0.5 mm defect on a 300 mm panel is less
  than 0.2% of its width.
- **Bad parts are rare.** A good paint line rejects very few parts, so you will have
  hundreds of good images and only a handful of bad ones. You cannot train a normal
  "good vs bad" classifier on that. You must learn what *good* looks like and flag
  anything that departs from it (anomaly detection).
- **Missing a defect is worse than a false alarm.** A defect that escapes reaches the
  end customer. A false alarm costs an inspector ten seconds to look again.

## 2. The scenario

A manufacturer paints **two-wheeler body panels** — curved, glossy, in several colours.
Today every part is checked by eye at an inspection table after the paint oven. Inspectors
tire, miss small defects on the night shift, and there is no record of what was found.

The plan is an inspection station at that table: the operator places a panel in a fixed
nest under a hooded light, presses a button, a camera takes an image, and within about a
second the station says **PASS**, **FAIL** (with where the defect is), or **UNKNOWN**
(the image cannot be trusted — re-place the part or call a person).

You are building the **software that decides**, from a still image, which of the three it
is. The camera, light and nest are already fixed; you get their images.

Station facts you can rely on:

- Image scale is **≈ 0.1 mm per pixel**. The smallest defect that **must** be caught is
  **0.5 mm** (≈ 5 px).
- Every part sits in the same nest, so the panel is in nearly the same place in every
  image (a few pixels of play).
- Lighting is controlled (hood + fixed light), but gloss highlights are present in every
  image and are **not** defects.
- The station runs on a small edge computer (Raspberry Pi 4 class, CPU only).

## 3. What you receive

The images come from a **physically-based simulator of this station**, not from a camera.
Each panel is rendered from a height map: its curvature, the orange-peel texture of real
paint and the 3-D shape of each defect are lit by the hooded light, then camera noise,
vignetting and JPEG compression are added. So gloss highlights, edge fall-off and defects
behave the way they do on real paint, and every defect has an exact ground-truth mask. Treat
the images exactly as if they came off the line.

```
data/
  station.yaml           scale (0.1 mm/px), nest position, features that are NOT defects
  golden/                3 hand-picked perfect references
  train/good/            150 images of defect-free panels -- the only training data
  val/good/              30 good
  val/bad/               30 defective (some at the panel edge, some at 0.5-0.65 mm)
  val/masks/             one PNG per bad image: white = defect pixels
  val/unknown/           3 examples of images that cannot be trusted (blur, dark, mis-seated)
  val/labels.csv         file, expected, defect_types, size_mm, edge, note
```

Images are 1024 x 768 colour JPEG. The panel has a **mounting hole** and a horizontal
**stiffening rib**, and its edge is **folded (hemmed)** so it darkens towards the boundary.
All three are part of the design, not defects.

A **hidden test set** (good, bad and untrustworthy images, never shared) is kept by us.
We run **your code** on it.

## 4. The task — v1 (days 1–2)

Build a command-line inspection tool:

```bash
python inspect.py --recipe recipes/panel_red.yaml --images path/to/dir --out results/
```

For **each image** `<name>.jpg` it must write `results/<name>.json` in exactly this shape
(we score it automatically, so the field names matter):

```json
{
  "image": "img_123456.jpg",
  "verdict": "FAIL",
  "score": 7.31,
  "defects": [ { "bbox": [412, 300, 14, 12], "size_mm": 1.2 } ],
  "time_ms": 182.4
}
```

- `verdict` is `PASS`, `FAIL` or `UNKNOWN`.
- `bbox` is `[x, y, width, height]` in pixels of the original image. A FAIL only counts as
  caught if one of your boxes is on the actual defect. A FAIL for the wrong reason is a miss.
- `time_ms` is your processing time for that image.

Also write `results/<name>_heatmap.png` (an overlay showing where the defect is) and a
`results/summary.csv` with one row per image.

Do it in two stages and **keep both**:

1. **Classical baseline, no training.** For example: align to the golden image, difference
   or local statistics, morphological clean-up, blob size filter in mm. Get a number.
2. **Anomaly model trained on good images only.** For example PatchCore or PaDiM (the
   Anomalib library is fine). Compare it honestly against stage 1.

Rules:

- The **threshold is set using `val/` only** and written into the recipe file. The tool
  must not change its threshold at run time. We will run it, unmodified, on the hidden set.
- Everything a station engineer might change — thresholds, region of interest, masks,
  minimum defect size in mm, model path — lives in the **recipe YAML**, not in the code.
- **Return `UNKNOWN`, not `PASS` or `FAIL`**, when the image itself is bad: too dark, too
  bright, blurred, or the panel is not where the nest says it should be. Decide and document
  the checks.
- **Licences:** use only permissively licensed libraries (Apache-2.0, MIT, BSD). **Do not
  use Ultralytics / YOLOv5–v11** (AGPL-3.0) and **do not use EfficientAD** (patent-encumbered).
  Check the licence of anything else you add and list it in the README.

## 5. Change requests (arrive as GitHub Issues during the assignment)

Like a real project, requirements will change while you work. Two change requests will be
opened as **Issues in your repository**, around **day 2** and **day 4**, labelled
`change-request`. Treat each like a customer ticket:

- understand it, and ask in the issue if anything is unclear
- change the code, add a test, write a `CHANGELOG.md` entry, and explain the trade-off
- reference the issue in your commits (`Fixes #1`) so the history shows the work
- evolve the project you have; do not start a fresh one for each request

Make sure GitHub notifications for your repository reach you (Watch → All activity).

## 6. What to submit (end of day 5)

1. **Your repository**, pushed, with a git tag named **`submission`** on the commit you want
   marked (`git tag submission && git push origin submission`). We read the commit
   history: small, meaningful commits over five days, not one commit at the end.
2. `README.md` — how to install and run, from a clean machine, in under 10 commands.
3. `requirements.txt` with pinned versions.
4. `tests/` — at least: recipe loading, the UNKNOWN checks, and one end-to-end run on 3
   sample images.
5. `REPORT.md` (2–4 pages):
   - what you tried, what worked, what did not, and **why**
   - classical vs anomaly model: a table with escapes, false rejects and speed
   - how you picked the threshold
   - **where your system fails** — show three failure images and explain them
   - what you would need (better light, more images, another camera angle) to do better
6. `CHANGELOG.md` — one entry per change request.
7. `AI_LOG.md` — see §7.
8. A **3–5 minute screen recording** running the tool on the validation set and walking
   through the results. Link it at the top of `REPORT.md` (unlisted YouTube or a Drive link).
9. Run `python tools/check_output.py results/` on your validation output before you tag.
   It checks the JSON format we score. A wrong format scores zero on the hidden set.

If your model file is larger than 50 MB, do not commit it. Publish it as a Release asset in
your repository and download it in your setup steps.

When you have tagged, open an issue in your repository titled **"Submission"**.

## 7. Using AI tools — `AI_LOG.md`

We expect you to use Claude Code, Codex or similar. We are **not** testing whether you can
type code by hand; we are testing whether you can **direct** an AI assistant and **catch it
when it is wrong**. In `AI_LOG.md`, record:

- the main prompts or tasks you gave the assistant
- **at least three places where its output was wrong, unsafe or not what you needed**, and
  how you noticed and fixed it
- one decision you made **against** the assistant's suggestion, and why

You must be able to explain every line in your repository on the follow-up call.

## 8. How you will be evaluated

| area | weight |
| --- | --- |
| **Results on the hidden test set** — we run your tool as submitted. Escapes (missed defects ≥ 0.5 mm) count **twice** as much as false rejects. | 30 |
| **Change requests** — handled cleanly, configurable, tested, documented | 20 |
| **Report** — clear reasoning, honest about failures, sound threshold choice | 15 |
| **Engineering** — structure, recipe-driven config, tests, README that works | 15 |
| **Git history + CHANGELOG** | 10 |
| **AI_LOG** — quality of judgement, not volume | 10 |

Shortlisted candidates get a **30-minute call**: you walk us through the code, and we ask
you to make one small change live.

A working, honest, well-explained simple solution scores higher than a complicated one
that cannot be explained. If you get stuck, write down what you tried — that counts.

## 9. Questions

Open an issue in your repository titled **"Question: …"** (we are notified as a
collaborator), or reply to the email that sent you this link. We answer within one working
day. Questions about the problem are welcome and are not marked against you.

## 10. Your work

The code you write is yours. We use it only to evaluate your application, and we do not
publish it. The dataset and this brief are provided for this assignment only.
