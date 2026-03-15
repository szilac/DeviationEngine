import React from 'react';

const Section = ({ children }: { children: React.ReactNode }) => (
  <div className="border border-border px-6 py-6 space-y-4">{children}</div>
);

const SectionTitle = ({ num, title }: { num: string; title: string }) => (
  <div>
    <p className="rubric-label mb-1">§ {num}</p>
    <h2 className="font-display text-xl text-gold leading-tight">{title}</h2>
    <div className="double-rule mt-3" />
  </div>
);


const Row = ({ marker = '—', markerClass = 'text-dim', children }: { marker?: string; markerClass?: string; children: React.ReactNode }) => (
  <div className="flex gap-3">
    <span className={`font-mono text-xs shrink-0 mt-0.5 ${markerClass}`}>{marker}</span>
    <span className="font-body text-base text-dim leading-relaxed">{children}</span>
  </div>
);

const Card = ({ children, className = '' }: { children: React.ReactNode; className?: string }) => (
  <div className={`border border-border bg-parchment px-4 py-3 ${className}`}>{children}</div>
);

const AboutPage: React.FC = () => {
  return (
    <div className="min-h-screen py-10 px-4">
      <div className="max-w-5xl mx-auto space-y-5">

        {/* Disclaimer */}
        <div className="border border-warning/50 bg-warning/5 px-6 py-6 space-y-4">
          <div>
            <p className="rubric-label mb-1">§ Disclaimer</p>
            <h1 className="font-display text-2xl text-warning leading-tight">
              This application generates purely fictional alternate history scenarios.
            </h1>
            <div className="double-rule mt-3" />
          </div>
          <div className="font-body text-base text-dim space-y-3 leading-relaxed">
            <p>
              All timelines, events, narratives, and analyses produced by the Deviation Engine are{' '}
              <strong className="text-ink">works of fiction</strong> created by artificial intelligence.
              They do not represent historical facts, predictions, or authoritative analysis.
            </p>
            <p>The generated content is intended solely for:</p>
            <div className="grid grid-cols-2 gap-2 mt-1">
              {['Entertainment and creative exploration', 'Educational thought experiments about causality', 'Speculative fiction writing inspiration', 'Understanding complex historical systems'].map(item => (
                <div key={item} className="flex gap-2 items-start">
                  <span className="font-mono text-xs text-gold shrink-0 mt-0.5">✓</span>
                  <span className="font-body text-base text-dim">{item}</span>
                </div>
              ))}
            </div>
            <p>
              <strong className="text-ink">Do not use for:</strong>{' '}
              Academic research, historical reference, political decision-making, or any context requiring factual accuracy.
            </p>
          </div>
        </div>

        {/* I. What is the Deviation Engine */}
        <Section>
          <SectionTitle num="I." title="What is the Deviation Engine?" />
          <p className="font-body text-base text-dim leading-relaxed">
            The Deviation Engine is an AI-powered alternate history simulator that explores "what if" scenarios.
            By defining a point of divergence from actual history, you can generate detailed timelines showing
            how events might have unfolded differently — complete with structured analysis, narrative prose,
            images, and audio content.
          </p>
        </Section>

        {/* II. Scenario Types */}
        <Section>
          <SectionTitle num="II." title="Scenario Types" />
          <p className="font-body text-base text-dim leading-relaxed">
            Choose from five distinct scenario types, each with curated examples to guide your exploration:
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {[
              { label: 'Local Deviation',       desc: 'Single historical change with strict realism',              examples: 'Assassination prevented, discovery delayed',   color: 'border-t-2 border-t-gold' },
              { label: 'Global Deviation',      desc: 'Large-scale event affecting the entire world',              examples: 'Pandemic controlled, economic collapse',        color: 'border-t-2 border-t-quantum' },
              { label: 'Reality Fracture',      desc: 'Fundamental break in laws of nature or physics',           examples: 'Magic becomes real, time anomalies',            color: 'border-t-2 border-t-dim' },
              { label: 'Geological Shift',      desc: 'Physical environmental or geographic changes',              examples: 'Earthquakes, climate shifts, land formations',   color: 'border-t-2 border-t-warning' },
              { label: 'External Intervention', desc: 'Time traveler, alien contact, or external actor intervenes', examples: 'Future technology, alien contact',              color: 'border-t-2 border-t-rubric-dim' },
            ].map(s => (
              <Card key={s.label} className={s.color}>
                <div className="font-mono text-xs tracking-widest uppercase text-ink mb-1">{s.label}</div>
                <div className="font-body text-base text-dim leading-snug mb-2">{s.desc}</div>
                <div className="font-mono text-[9px] text-faint">{s.examples}</div>
              </Card>
            ))}
          </div>
        </Section>

        {/* III. Multi-Agent AI System */}
        <Section>
          <SectionTitle num="III." title="Multi-Agent AI System" />
          <p className="font-body text-base text-dim leading-relaxed">
            The Deviation Engine uses a multi-agent architecture where each AI agent specialises in a
            different aspect of timeline generation. Each agent can be independently configured with
            different LLM models to optimise cost or quality.
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2">
            {[
              { name: 'Historian Agent',          desc: 'Structured analytical reports across political, economic, social, and technological domains' },
              { name: 'Skeleton Agent',            desc: 'Editable event timelines (15–25 key events) for user-guided generation' },
              { name: 'Skeleton Historian Agent',  desc: 'Detailed reports from user-approved skeleton events' },
              { name: 'Storyteller Agent',         desc: 'Immersive narrative prose in multiple styles (omniscient or custom POV)' },
              { name: 'Illustrator Agent',         desc: 'Detailed image prompts for AI visual generation via Pollinations.ai' },
              { name: 'Script Writer Agent',       desc: 'Timeline content transformed into professional audio scripts' },
              { name: 'Character Profiler Agent',  desc: 'Biographical profiles for historical figures with personality and speaking style' },
              { name: 'Impersonator Agent',        desc: 'In-character conversations as historical figures within their temporal knowledge' },
              { name: 'Ripple Analyst Agent',      desc: 'Causal node and edge extraction for interactive causal graph visualisation' },
            ].map(a => (
              <Card key={a.name}>
                <div className="font-mono text-xs tracking-widest uppercase text-ink mb-1">{a.name}</div>
                <div className="font-body text-base text-dim leading-relaxed">{a.desc}</div>
              </Card>
            ))}
          </div>
        </Section>

        {/* IV. How to Use */}
        <Section>
          <SectionTitle num="IV." title="How to Use" />
          <div className="space-y-6">

            {/* Step 1 */}
            <div className="space-y-3">
              <div className="flex items-center gap-3">
                <span className="font-mono text-[10px] border border-gold-dim text-gold w-5 h-5 flex items-center justify-center shrink-0">1</span>
                <span className="font-mono text-xs tracking-widest uppercase text-ink">Create a Timeline</span>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 ml-8">
                <Card>
                  <div className="font-mono text-xs tracking-widest uppercase text-quantum mb-2">Method A — Direct Generation</div>
                  <p className="font-body text-base text-dim mb-2">Navigate to <strong className="text-ink">Deviation Console</strong> and specify:</p>
                  <div className="space-y-1">
                    {['Deviation Date: when does history diverge? (1880–1970)', 'Duration: how many years to simulate (1–50)', 'Description: what event causes the deviation?', 'Scenario Type: choose from 5 types', 'Narrative Mode: how the story is told'].map(item => (
                      <Row key={item} marker="·">{item}</Row>
                    ))}
                  </div>
                  <p className="font-mono text-[9px] text-faint mt-2">~60–120 seconds</p>
                </Card>
                <Card>
                  <div className="font-mono text-xs tracking-widest uppercase text-gold mb-2">Method B — Skeleton Workflow (Recommended)</div>
                  <p className="font-body text-base text-dim mb-2">Navigate to <strong className="text-ink">Skeleton Workflow</strong> for more control:</p>
                  <div className="space-y-1">
                    {['Enter the same deviation details', 'Generate skeleton: 15–25 key events (~30–60s)', 'Review the event structure', 'Edit events (optional): add, delete, reorder', 'Approve skeleton when satisfied', 'Choose narrative mode and generate full report'].map((item, i) => (
                      <Row key={item} marker={`${i + 1}.`} markerClass="text-gold-dim">{item}</Row>
                    ))}
                  </div>
                </Card>
              </div>
            </div>

            {/* Steps 2–10 */}
            {[
              { n: 2, title: 'Explore the Timeline', items: [
                'View the Temporal Atlas showing the deviation point and alternate branches',
                'Read Structured Reports with detailed analysis across 8 domains',
                'Read Narrative Prose for an immersive storytelling experience',
                'Translate content into 11 languages using the language selector',
                'Browse different time periods when multiple chronicles exist',
                'View Source Skeleton to see the exact events used (skeleton workflow only)',
                'Explore Historical Figures — detect, profile, and chat with characters',
              ]},
              { n: 3, title: 'Extend a Timeline', items: [
                'Open any saved timeline and click "Extend Chronicle" in the sidebar',
                'Add additional years to continue the simulation',
                'Provide optional context for new events or circumstances',
                'Use Skeleton Extension (recommended) for more control over new events',
              ]},
              { n: 4, title: 'Generate Images', items: [
                'Navigate to the Images tab and click "Generate Image Prompts"',
                'Specify count (3–20), optional focus areas, and source generation',
                'Review and edit prompts, then approve — then generate',
                'Free AI image generation via Pollinations.ai (no API key needed)',
              ]},
              { n: 5, title: 'Create Audio Content', items: [
                'Open Audio Studio from the timeline header',
                'Select chronicles to include and choose a style preset',
                'Review and edit the generated script before audio generation',
                'Generate audio via Google TTS — multi-language supported',
              ]},
              { n: 6, title: 'Translate Content', items: [
                'Use the Language Selector on any report to choose from 11 languages',
                'DeepL API: fast (~5 seconds), requires API key, 500k chars/month free',
                'LLM Translation: native quality (~30 seconds), context-aware',
                'Translations cached permanently — translate once, read instantly',
              ]},
              { n: 7, title: 'Compare Timelines via Temporal Atlas', items: [
                'Navigate to /atlas or click Atlas in the navigation',
                'Select up to 6 timelines using the selector panel',
                'Compare how different deviations evolve relative to ground truth',
              ]},
              { n: 8, title: 'Chat with Historical Figures', items: [
                'Open the Characters panel (ψ Characters) from any timeline header',
                'Scan Timeline to auto-detect figures, or Add Custom to create your own',
                'Generate Profile — set a cutoff year and wait ~30–60 seconds',
                'Click Chat and choose a year context to start in-character conversation',
                'The character responds knowing only events up to their year context',
              ]},
              { n: 9, title: 'Explore the Ripple Map', items: [
                'Click "Ripple Map" in the timeline header',
                'Select generations to include and generate the causal graph',
                'Switch between Linear (time-axis) and Radial (concentric rings) views',
                'Click any node to highlight its causal chain; filter by domain',
              ]},
              { n: 10, title: 'Export & Import Timelines', items: [
                'Click "Export Timeline" in the actions menu to download a .devtl file',
                'File contains complete data — generations, narratives, skeletons',
                'Go to Library and click "Import Timeline" to restore from a .devtl file',
              ]},
            ].map(({ n, title, items }) => (
              <div key={n} className="space-y-2">
                <div className="flex items-center gap-3">
                  <span className="font-mono text-[10px] border border-gold-dim text-gold w-5 h-5 flex items-center justify-center shrink-0">{n}</span>
                  <span className="font-mono text-xs tracking-widest uppercase text-ink">{title}</span>
                </div>
                <div className="ml-8 space-y-1">
                  {items.map(item => <Row key={item}>{item}</Row>)}
                </div>
              </div>
            ))}
          </div>
        </Section>

        {/* V–VIII: Advanced — two-column grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">

          {/* V. Per-Agent Models */}
          <Section>
            <SectionTitle num="V." title="Per-Agent Model Configuration" />
            <p className="font-body text-base text-dim leading-relaxed">
              In <strong className="text-ink">Settings</strong>, configure a different LLM model per agent
              to optimise cost or quality independently.
            </p>
            <div className="space-y-2">
              {[
                ['Cost Optimisation', 'Cheap models for skeleton/structure, premium for narratives'],
                ['Quality Focus',     'High-end models for all agents — maximum coherence and detail'],
                ['Balanced Approach', 'Mid-tier for analysis, premium for creative content'],
              ].map(([label, desc]) => (
                <Row key={label} marker="§" markerClass="text-gold">
                  <strong className="text-ink">{label}:</strong> {desc}
                </Row>
              ))}
            </div>
            <p className="font-mono text-[9px] text-faint italic">
              Each generated report tracks which models were used.
            </p>
          </Section>

          {/* VI. Translation */}
          <Section>
            <SectionTitle num="VI." title="Translation Service" />
            <div className="grid grid-cols-2 gap-2">
              <Card>
                <div className="font-mono text-xs tracking-widest uppercase text-quantum mb-2">DeepL API</div>
                <div className="space-y-1 font-body text-base text-dim">
                  <div>Speed: ~5 seconds</div>
                  <div>Quality: reliable for most content</div>
                  <div>Setup: free key (500k chars/month)</div>
                </div>
              </Card>
              <Card>
                <div className="font-mono text-xs tracking-widest uppercase text-gold mb-2">LLM Translation</div>
                <div className="space-y-1 font-body text-base text-dim">
                  <div>Speed: ~30 seconds</div>
                  <div>Quality: native, context-aware</div>
                  <div>Setup: uses existing LLM config</div>
                </div>
              </Card>
            </div>
            <div className="space-y-1 pt-1">
              {[
                ['Audio Scripts',       'Conversational tone, filler word adaptation'],
                ['Historical Reports',  'Academic terminology, formal register'],
                ['Narrative Prose',     'Literary quality, emotional resonance'],
                ['Smart Caching',       'Translate once, read instantly'],
              ].map(([label, desc]) => (
                <Row key={label} marker="§" markerClass="text-gold">
                  <strong className="text-ink">{label}:</strong> {desc}
                </Row>
              ))}
            </div>
          </Section>

          {/* VII. RAG */}
          <Section>
            <SectionTitle num="VII." title="AI Smart Search (RAG)" />
            <p className="font-body text-base text-dim leading-relaxed">
              Vector-based context retrieval dramatically reduces API costs while maintaining historical accuracy.
            </p>
            <div className="grid grid-cols-2 gap-2">
              <Card>
                <div className="font-mono text-xs tracking-widest uppercase text-gold mb-2">Smart Search — Recommended</div>
                <div className="space-y-1 font-body text-base text-dim">
                  <div>~99% fewer tokens vs Full Context</div>
                  <div>ChromaDB + Gemini embeddings</div>
                  <div>Retrieves only relevant events</div>
                </div>
              </Card>
              <Card>
                <div className="font-mono text-[10px] tracking-widest uppercase text-dim mb-2">Full Context (Legacy)</div>
                <div className="space-y-1 font-body text-base text-dim">
                  <div>Loads all historical data</div>
                  <div>Higher token cost</div>
                  <div>Auto-fallback if RAG unavailable</div>
                </div>
              </Card>
            </div>
            <div className="space-y-1">
              {[
                'Configure in Settings → Debug → Default Context Mode',
                'Per-timeline override available in Advanced Options',
                'Index ground truth: python scripts/index_ground_truth.py',
              ].map(item => <Row key={item}>{item}</Row>)}
            </div>
          </Section>

          {/* VIII. Data Management */}
          <Section>
            <SectionTitle num="VIII." title="Data Management & Purge" />
            <Card className="border-rubric-dim">
              <p className="font-body text-base text-rubric/90 leading-relaxed">
                Danger Zone: the Purge feature performs a complete application reset.
                This cannot be undone. Export important timelines first.
              </p>
            </Card>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="rubric-label mb-2">Deleted</p>
                <div className="space-y-1">
                  {['All timelines & generations', 'All skeletons', 'Audio scripts, files, images', 'Character profiles & chats', 'Vector store (user content)', 'Stored API keys'].map(item => (
                    <Row key={item} marker="✗" markerClass="text-rubric">{item}</Row>
                  ))}
                </div>
              </div>
              <div>
                <p className="rubric-label mb-2">Preserved</p>
                <div className="space-y-1">
                  {['Provider & model settings', 'Per-agent model settings', 'Audio presets', 'Ground truth data', 'Debug preferences'].map(item => (
                    <Row key={item} marker="✓" markerClass="text-success">{item}</Row>
                  ))}
                </div>
              </div>
            </div>
            <Card>
              <p className="font-mono text-[9px] tracking-widest uppercase text-dim mb-2">Via CLI</p>
              <pre className="font-mono text-xs text-quantum overflow-x-auto">python scripts/purge_data.py [--include-ground-truth] [--yes]</pre>
            </Card>
          </Section>
        </div>

        {/* IX. Tips */}
        <Section>
          <SectionTitle num="IX." title="Tips for Best Results" />
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-8 gap-y-2">
            {[
              ['Use Skeleton Workflow',       'Review and edit events before generating for best results'],
              ['Be Specific',                 'Detailed deviation descriptions produce more coherent timelines'],
              ['Start Small',                 'Try 5–10 year durations first to test your deviation'],
              ['Use Extensions',              'Build complex scenarios incrementally with new context'],
              ['Experiment with Narratives',  'Try different modes to see how perspective changes the story'],
              ['Compare Variations',          'Create multiple timelines with slight changes to explore possibilities'],
              ['Optimise Model Usage',        'Per-agent model config in Settings to balance cost and quality'],
              ['Generate Images',             'Edit prompts before generating for better visual results'],
              ['Create Audio Content',        'Multiple preset styles and Google TTS for professional output'],
              ['Use Translations',            'Translations are cached — translate once, read instantly'],
              ['Export & Share',              '.devtl export format for backups and sharing'],
              ['Chat Across Years',           'Generate profiles at different cutoff years for character development'],
            ].map(([label, desc]) => (
              <Row key={label} marker="✓" markerClass="text-gold">
                <strong className="text-ink">{label}:</strong> {desc}
              </Row>
            ))}
          </div>
        </Section>

        {/* X. LLM & Performance Tips */}
        <Section>
          <SectionTitle num="X." title="LLM & Performance Tips" />
          <div className="space-y-4">

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <Card className="border-t-2 border-t-gold">
                <div className="font-mono text-xs tracking-widest uppercase text-gold mb-2">Recommended Models</div>
                <p className="font-body text-base text-dim leading-relaxed">
                  Gemini Flash models (2.5, 3.0) are the recommended default for all agents. They offer a generous
                  free-tier rate limit and up to 1 million token context window — well suited for the long prompts
                  Deviation Engine generates.
                </p>
              </Card>
              <Card className="border-t-2 border-t-quantum">
                <div className="font-mono text-xs tracking-widest uppercase text-quantum mb-2">Rate Limit Fallback</div>
                <p className="font-body text-base text-dim leading-relaxed">
                  If you hit the rate limit on one Gemini Flash version, switch to the other — Gemini 2.5 Flash and
                  3.0 Flash operate on separate quotas and produce nearly identical output quality.
                </p>
              </Card>
            </div>

            <div className="space-y-2">
              <p className="rubric-label">Per-Agent Model Recommendations</p>
              {[
                ['Skeleton · Historian · Ripple Analyst', 'Structure-heavy tasks — capable reasoning models work well'],
                ['Storyteller · Character Profiler',      'Creative output — higher-quality models produce noticeably better results'],
                ['Translator Agent',                      'Must use a multilingual model; Gemini Flash and GPT-series are reliable choices'],
                ['Impersonator Agent',                    'Conversational tasks — smaller, faster models (Flash Lite, GPT-4o mini) work fine and reduce cost'],
              ].map(([label, desc]) => (
                <Row key={label} marker="§" markerClass="text-gold">
                  <strong className="text-ink">{label}:</strong> {desc}
                </Row>
              ))}
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <Card>
                <div className="font-mono text-xs tracking-widest uppercase text-gold mb-2">RAG — Smart Search</div>
                <div className="space-y-1 font-body text-base text-dim">
                  <div>~99% fewer tokens vs Full Context</div>
                  <div>Good quality — occasionally less consistent if retrieval misses relevant context</div>
                  <div>Recommended default for most use cases</div>
                </div>
              </Card>
              <Card>
                <div className="font-mono text-[10px] tracking-widest uppercase text-dim mb-2">Full Context (Legacy)</div>
                <div className="space-y-1 font-body text-base text-dim">
                  <div>High token usage and cost</div>
                  <div>Rich, consistent context across the whole period</div>
                  <div>May overwhelm models with small context windows</div>
                </div>
              </Card>
            </div>

            <div className="space-y-2">
              {[
                ['OpenRouter',         'Requires a small credit balance — not a subscription. Costs are very low and a modest top-up lasts a long time. Provides access to almost all major LLMs; pay attention to each model\'s context window and per-token pricing.'],
                ['Transient Failures', 'LLM providers occasionally fail during periods of high server load. If a generation fails unexpectedly, wait a few minutes and try again. Check the backend terminal for detailed error output.'],
                ['NotebookLM Audio',   'Requires separate setup: install notebooklm-cli, authenticate with your Google account, then enable in Settings → Audio.'],
              ].map(([label, desc]) => (
                <Row key={label} marker="✓" markerClass="text-gold">
                  <strong className="text-ink">{label}:</strong> {desc}
                </Row>
              ))}
            </div>

          </div>
        </Section>

        {/* Footer */}
        <div className="text-center py-6">
          <div className="double-rule mb-4" />
          <p className="font-mono text-xs text-faint tracking-widest uppercase">
            Deviation Engine — AI-Powered Alternate History Exploration
          </p>
          <p className="font-body text-xs text-faint mt-1 italic">
            Remember: this is fiction. Have fun exploring the possibilities.
          </p>
          <p className="font-mono text-xs text-faint mt-3">|ψ⟩</p>
        </div>

      </div>
    </div>
  );
};

export default AboutPage;
