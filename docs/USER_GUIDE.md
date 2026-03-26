# Deviation Engine – User Guide

This guide explains how to use Deviation Engine as an end user: from your first run, through creating timelines, to generating narratives, translations, images, and audio.

If you are setting up the project for the first time, complete the steps in [`docs/technical/SETUP_AND_RUN.md`](docs/technical/SETUP_AND_RUN.md) (or the Quick Start in [`README.md`](README.md)) before following this guide.

---

## 1. Core Concepts (What You Work With)

- Deviation Point:
  - A specific date in real history within the supported range (1880–2004).
  - A clear description of "what changed".
  - A scenario type (e.g., local_deviation, global_deviation, reality_fracture).
- Timeline:
  - A complete alternate history built from your deviation point.
  - Contains one or more Generations.
- Generation:
  - A time segment within a timeline.
  - Contains:
    - Structured analytical report (8 sections).
    - Optional narrative prose.
    - Attached media (images, audio).
- Skeleton:
  - An editable list of key events.
  - You review and refine this before generating a full Generation from it.
- Media:
  - Image prompts and generated images.
  - Audio scripts and TTS audio tracks.
  - NotebookLM AI podcast audio.
- Translation:
  - Localized versions of your reports, narratives, and scripts.
- Historical Figures:
  - Characters detected in or added to your timeline, with AI-generated profiles.
  - Enables in-character chat within the context of your alternate world.
- Temporal Atlas:
  - An interactive D3.js canvas showing all your timelines as branching paths from a shared main axis.
- Ripple Map:
  - A force-directed graph showing the causal web of events within a timeline.

You will mainly interact with timelines, skeletons, media, and translations via the web UI.

---

## 2. Accessing the Application

After starting backend and frontend:

- Frontend UI: http://localhost:5173
- API docs (for reference only): http://localhost:8000/docs

Use a modern browser (Chrome, Edge, Firefox, Safari). Keep the backend terminal open during use.

---

## 3. First Run Checklist

Before creating content:

1. Open http://localhost:5173.
2. Verify the home/landing page loads without errors.
3. Open the Settings page:
   - Confirm your LLM provider is configured under **§ I. Language Model** (Gemini, OpenRouter, Anthropic, or OpenAI).
   - (Optional) Go to **Advanced Configuration** → **§ III. Translation** to configure DeepL.
   - (Optional) Go to **Advanced Configuration** → **§ V. Integrations** → toggle **NotebookLM Podcast Generation** if you have `nlm` installed and authenticated.
   - (Optional) Go to **Advanced Configuration** → **§ V. Integrations** → enable **CLIProxy** if you want to use a Claude or OpenAI subscription instead of API keys (see inline instructions).
4. Return to the console/home to start creating your first scenario.

If any step fails, consult setup docs or backend logs.

---

## 4. Creating Your First Timeline

You have two main options:

### 4.1 Skeleton Workflow (Recommended)

Use when:
- You care about realism, coherence, or fine control over events.
- You want to review/edit the key events before committing.

Steps:

1. Navigate:
   - In the top navigation, open:
     - "Skeleton Workflow" or the equivalent entry point from the home/console.

2. Define your deviation:
   - Deviation date:
     - Choose a date in the allowed range (1880–2004).
   - Deviation description:
     - Write a concrete change, e.g.:
       - "The 1929 stock market crash is prevented by a coordinated central bank intervention."
   - Simulation years:
     - Choose how far into the future to simulate (e.g., 10–30 years).
   - Scenario type:
     - Select one:
       - local_deviation, global_deviation, reality_fracture, geological_shift, external_intervention
     - Use the examples panel (if available) to quickly pick strong inputs.

3. Generate skeleton:
   - Click "Generate Skeleton".
   - Wait for AI processing (~30–60 seconds).
   - The page will display 15–25 key events across the chosen period.

4. Review and edit events:
   Typical actions:
   - Edit: Refine descriptions for clarity or tone.
   - Add: Insert missing events that matter to your scenario.
   - Delete: Remove events that feel implausible or out-of-scope.
   - Reorder: Adjust event order to improve causal flow.
   Recommended practices:
   - Keep cause-and-effect clear.
   - Maintain consistent geopolitical and technological logic.

5. Approve skeleton:
   - When satisfied, click "Approve Skeleton".
   - This freezes the event structure for generation (you can always create another skeleton later).

6. Generate the full Generation:
   - Choose Narrative Mode:
     - none → fastest, structured analysis only.
     - basic → single-pass narrative.
     - advanced_omniscient → high-quality, neutral third-person.
     - advanced_custom_pov → specify a custom perspective in the UI.
   - Click "Generate from Skeleton".
   - Wait (~60–120 seconds).
   - Result:
     - A new timeline with at least one Generation:
       - 8-section analytical report.
       - Optional narrative.
       - Model metadata for transparency.

7. Explore your result:
   - Use the generation selector / timeline controls to inspect the period.
   - View both structured sections and narrative tabs.

### 4.2 Direct Generation (Faster, Less Control)

Use when:
- You want immediate results and trust the AI to handle structure.

Steps:

1. Navigate to "Console" or "Generate Timeline" screen.
2. Fill in:
   - Deviation date.
   - Deviation description.
   - Simulation years.
   - Scenario type.
   - Narrative mode.
3. Click "Generate Timeline".
4. Wait for completion and then:
   - Inspect the generated Generation (analysis + narrative).
   - Save or extend as needed.

---

## 5. Working with Saved Timelines

Once you have timelines, manage them via the Library/Saved Timelines view.

Key actions:

- Open a timeline:
  - Shows all Generations: you can switch between segments.
- Inspect a Generation:
  - Analytical sections (executive summary, politics, economics, etc.).
  - Narrative prose (if enabled).
  - Associated media (images, audio).
- Extend a timeline:
  - From the timeline view, choose "Extend Timeline".
  - Option A: Extension Skeleton:
    - Generate/edit/approve events for the new period.
    - Then generate a new Generation from it.
  - Option B: Direct Extension:
    - Add more simulation years and generate immediately.
- Delete:
  - Remove a timeline you no longer need (note: this is destructive).

Use extensions to follow long-term consequences without redoing the initial deviation.

---

## 6. Image Generation Workflow

Images help visualize your alternate history. The system uses prompt skeletons, then generates image URLs (e.g., via Pollinations.ai).

Typical flow (from a timeline):

1. Open a timeline and navigate to the Images tab or media section.
2. Generate image prompt skeleton:
   - Choose:
     - Target timeline (and optionally a specific Generation).
     - Number of images (e.g., 3–20).
     - Focus areas (political, economic, social, technological, military, cultural).
   - Click "Generate Image Prompts".
3. Review prompts:
   - Edit prompt text to:
     - Emphasize historical style, atmosphere, or key figures.
   - Adjust:
     - Titles, descriptions.
     - Event years.
     - Style notes (e.g., "sepia-toned 1920s photograph", "newsreel frame").
4. Approve the prompts:
   - When the list looks coherent, approve the skeleton.
5. Generate images:
   - Click "Generate Images".
   - The system requests images and displays them in a gallery.
6. Browse and manage:
   - View images in a grid/lightbox.
   - Remove ones you don't like.
   - Regenerate prompts if needed (new skeleton).

Tips:
- Start with fewer prompts, refine language, then scale up.
- Keep stylistic notes consistent for a documentary-like feel.

---

## 7. Translation Workflow

If DeepL or LLM-based translation is configured, you can localize your content.

Supported concepts:
- Translating structured reports (all 8 sections).
- Translating narrative prose.
- Translating audio scripts.

Typical usage:

1. Configure translation:
   - In **Settings → Advanced Configuration → § III. Translation**:
     - Enable DeepL with an API key, or rely on LLM translation (where available).
2. In a timeline view:
   - Select target language from the language selector.
3. For a Generation:
   - Click:
     - "Translate Generation" to translate the analytical sections, or
     - "Translate Narrative" on the narrative tab.
4. Review:
   - Translation appears with:
     - Method indicator (DeepL / LLM).
     - Option to show original text.
5. Retry / switch method:
   - Delete an existing translation (where supported).
   - Re-run with another method if you need different style/quality.

Guidelines:
- Use DeepL for fast, large-volume translations.
- Use LLM mode (if enabled) for nuanced or creative texts.

Supported languages: Hungarian, German, Spanish, Italian, French, Portuguese, Polish, Dutch, Japanese, Chinese.

---

## 8. Audio Content

The Audio Studio offers two independent pipelines for turning your scenario into audio. Both are accessible from the **Audio Studio** panel on any timeline.

### 8.1 Script + Google TTS

Full control over narration: generate a script, review it, then produce audio.

1. Open a timeline and scroll to the Audio Studio / Audio section.
2. Choose content:
   - Select which Generations or sections to base the script on.
3. Select a preset:
   - Documentary Narration
   - Two Historians Podcast
   - News Bulletin
   - Narrative Storytelling
4. (Optional) Add instructions:
   - e.g., "Emphasize economic impact and avoid technical jargon."
5. Generate:
   - Click "Generate Audio Script".
   - Wait for processing; review the resulting script.
6. Edit and approve:
   - Adjust phrasing, length, or emphasis.
   - Approve when finalized.
7. Generate audio:
   - Select target language and voice options (where available).
   - Click "Generate Audio".
8. Playback:
   - Use built-in controls to play, pause, or scrub.
   - Regenerate or delete audio if not satisfied.

### 8.2 NotebookLM Audio

Uses Google's NotebookLM to generate a natural-sounding AI podcast discussion about your timeline. Two AI hosts genuinely discuss your content rather than simply reading it.

Requires: `nlm` CLI installed and authenticated. See [NotebookLM Setup in README](../README.md#notebooklm-audio-setup) for instructions.

Enable: **Settings → Advanced Configuration → § V. Integrations** → toggle **NotebookLM Podcast Generation**.

Steps:

1. Open any timeline → **Audio Studio** → **NotebookLM** tab.
2. Select generations to include (reports and/or narrative prose).
3. Choose format:
   - **Deep Dive**: Two-host podcast exploring the alternate history in depth.
   - **Brief**: Concise summary of key events and implications.
   - **Critique**: Critical analysis examining strengths and weaknesses.
   - **Debate**: Two perspectives debating plausibility and consequences.
4. Set length and language options.
5. (Optional) Add focus instructions, e.g.:
   - "Focus on the economic consequences."
   - "Discuss as if you lived through these events."
6. Click **Generate NotebookLM Audio**.
7. Wait 5–20 minutes (Google processes this externally).
8. The finished audio appears in the Past Generations section when complete.

Comparison:

| | Script + Google TTS | NotebookLM Audio |
| --- | --- | --- |
| **Sound** | Narrated, documentary-style | Natural conversation between two AI hosts |
| **Formats** | 4 scripted presets | Deep Dive, Brief, Critique, Debate |
| **Control** | Full script editing | Focus instructions only |
| **Speed** | ~5–10 minutes | 5–20 minutes (processed by Google) |
| **Cost** | Free (with rate limit) | Free (uses your Google account) |
| **API key required** | Yes (Google TTS) | No — uses `nlm` CLI + your Google login |

---

## 9. Historical Figure Chat

Bring the people of your alternate timeline to life.

### 9.1 Detecting and Adding Figures

1. Open any timeline with at least one generation.
2. Find the **Historical Figures** panel.
3. Auto-detect:
   - Click **Scan Timeline** to automatically find historical figures mentioned in the content.
4. Add custom characters:
   - Click **Add Custom** and provide a name and biography.

### 9.2 Generating Profiles

1. Select a figure and click **Generate Profile**.
2. Set a cutoff year — the profile captures the character as they exist up to that point in your alternate timeline.
3. Wait ~30–60 seconds.
4. The profile includes: personality, beliefs, speaking style, and known relationships.

### 9.3 Chatting

1. Once a figure is **Ready**, click **Chat**.
2. Pick a year context for the conversation.
3. The figure responds in character — they only know what happened in your alternate world up to their year context.
4. Responses are grounded in actual timeline events via RAG retrieval.

Tips:
- Generate profiles at different cutoff years to capture character development over time.
- Use multiple figures to explore different perspectives on the same events.

---

## 10. Temporal Atlas

Explore all your timelines on a unified D3.js canvas.

1. Navigate to **Atlas** in the top navigation.
2. The canvas shows:
   - A main time axis with deviation point diamond medallions.
   - Colour-coded branching paths for each alternate timeline.
   - Animated floating rope branches with cursor interaction.
   - Particle animation showing causal energy propagation.
3. Click on any timeline branch or node to navigate to that timeline.

Use the Atlas to compare the scale and divergence of multiple timelines at a glance.

---

## 11. Ripple Map

Explore the causal web of your alternate history with an interactive force-directed graph.

1. Open any timeline and navigate to **Ripple Map** (or access it from the Atlas).
2. The graph shows:
   - Nodes coloured by domain (political, economic, social, technological, cultural, military).
   - Node size represents magnitude of the event.
   - Directional edges showing causal relationships between events.
3. Use the filter controls to:
   - Filter by domain.
   - Filter by confidence level.
   - Filter by generation.
4. Switch between **Linear** and **Radial** layout modes.
5. Click any node to open a detail panel with the event description and relationships.

Use the Ripple Map to understand how your deviation propagated through different domains of history.

---

## 12. Exporting and Importing Timelines

Use exports to back up, share, or move timelines between installations.

### 12.1 Export

1. Open the desired timeline.
2. Click "Export Timeline".
3. The app downloads a `.devtl` file containing:
   - Deviation info.
   - All Generations and narrative content.
   - Skeleton snapshots and metadata.
   - (Note: image binaries are not included; URLs are preserved.)

You can also export individual generations as Markdown from the generation view.

### 12.2 Import

1. Go to the "Import Timeline" section (e.g., in Library/Saved Timelines).
2. Select a `.devtl` file exported earlier.
3. Upload:
   - The system validates structure and creates a new local timeline.
4. Open:
   - You are redirected to the imported timeline with a new ID.

This is the recommended way to share complex scenarios.

---

## 13. Best Practices for High-Quality Scenarios

- Write sharp deviation statements:
  - Focus on one clear change.
  - Avoid overly broad or vague changes.
- Respect time and scope:
  - Choose simulation ranges that let consequences unfold without becoming incoherent.
- Use Skeleton Workflow for:
  - Classroom use.
  - Serious alternate history writing.
  - Content you plan to share or publish.
- Iterate:
  - If a result feels off:
    - Adjust the skeleton.
    - Regenerate only the affected segments.
- Track realism vs. speculation:
  - Use scenario types consistently to signal how "wild" the scenario is meant to be.

---

## 14. Troubleshooting (User-Facing)

If something doesn't work as expected:

- No response / endless loading:
  - Check backend terminal for errors.
  - Confirm the API is reachable at http://localhost:8000/health or `/docs`.
- Empty or broken UI:
  - Refresh the page.
  - Confirm `npm run dev` is still running.
- Generation failures:
  - Verify your LLM provider configuration (Settings page).
  - Ensure API keys are valid and not rate-limited.
- Translation errors:
  - Confirm DeepL or LLM translation is enabled.
  - Check error messages or backend logs.
- NotebookLM Audio not appearing:
  - Confirm the feature is enabled in **Settings → Advanced Configuration → § V. Integrations**.
  - Run `nlm login --check` in your terminal to verify authentication.
  - Note: generation takes 5–20 minutes; check Past Generations after waiting.
- CLIProxy generation fails:
  - Confirm `cliproxyapi` is running in a terminal on your machine.
  - If the session expired, re-authenticate: `cliproxyapi --browser-auth`.
  - Verify CLIProxy is enabled in **Settings → Advanced Configuration → § V. Integrations**.
- Historical Figure Chat not responding correctly:
  - Ensure the timeline has at least one generation with content.
  - Try regenerating the figure's profile.

For persistent issues, consult:
- Project issues on GitHub.

---

## 15. Quick Reference: Common Flows

- "I want a polished, realistic alternate history":
  - Use Skeleton Workflow → Approve → Advanced Omniscient narrative → Optional images + translations.
- "I need a quick draft idea":
  - Use direct generation with Basic or None narrative.
- "I want visuals and audio for a class or video":
  - Generate timeline → Add images via Image tab → Create Audio Script → Generate TTS → Export timeline.
- "I want a natural-sounding podcast about my scenario":
  - Generate timeline → Audio Studio → NotebookLM tab → Deep Dive format → wait 5–20 minutes.
- "I want to interview a historical figure from my alternate world":
  - Open timeline → Historical Figures panel → Scan Timeline → Generate Profile → Chat.
- "I want to see how all my timelines relate to each other":
  - Navigate to Atlas → browse the branching visualisation.
- "I want to understand the causal chain of my scenario":
  - Open timeline → Ripple Map → filter by domain or generation.

This user guide is the primary reference for non-developer users of Deviation Engine and complements the technical docs under `docs/technical/`.
