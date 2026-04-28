# Driver YAML Spec Testing --- Resubmission to ISSRE 2026 Industry Track

## Background

**Original paper:** *The Polyglot's Dilemma: Conformance Testing a Dozen Specs in as Many Languages*, an experience report on MongoDB's 11-year journey developing the Unified Test Format (UTF) --- a YAML-based DSTL used to test ~12 native MongoDB driver implementations for conformance to shared specifications.

**Submitted:** FSE 2026 Industry Track. **Rejected** with three "weak reject" reviews on 2026-03-21.

**Resubmitting to:** ISSRE 2026 Industry Track.
- Abstracts: 2026-06-28
- Full / Short Papers: 2026-07-05
- Notification: 2026-08-12
- Camera Ready: 2026-08-19

**Authors on resubmission:**
- A. Jesse Jiryu Davis (jesse@mongodb.com) --- lead.
- Jeff Yemin --- long-tenured MongoDB drivers engineer, replacing Jeremy Mikola (no longer at MongoDB).

**Files in this directory:**
- `Drivers_Spec_Testing_FSE_2026.pdf` --- the rejected submission.
- `FSE feedback.txt` --- three reviews from the FSE PC.

## What the reviewers said (summary)

All three reviewers landed on the same core complaint: the paper is a credible retrospective but the only quantitative evidence is **LOC deleted (~12,000) and corpus growth (7 → 606 files, 1k → 124k lines)**. That speaks to maintenance efficiency, not to whether UTF actually *finds bugs* or *enforces consistency*.

Specific asks worth responding to:
1. **Defect / consistency evidence (all three reviewers).** What classes of bugs has UTF caught? What cross-driver inconsistencies did it surface that ad-hoc testing missed? Two or three case studies would help.
2. **Boundary of applicability (Reviewer C).** "We can't unify everything" is asserted but the cases where UTF was *deliberately not* applied (BSON serialization, SDAM state machine, connection string parsing) need concrete reasons why UTF is unsuitable.
3. **Single-schema-version problem (Reviewer C).** How often did monotonic schema bumps actually block drivers from adopting new specs? Quantify, don't just allude.
4. **Per-driver maintenance cost (Reviewer B).** Ongoing effort to keep each driver's test runner aligned with UTF evolution.
5. **Compare UTF to alternatives (Reviewer B).** Differential testing, property-based testing --- which fault classes does each catch?
6. **Automation / AI underexplored (Reviewer C).** Why is authoring still manual? What concrete barriers to LLM- or property-based generation exist? Move some of this from Future Work into the body.
7. **Format / template (Reviewers A and C).** FSE wanted double-column; we submitted single-column. ISSRE uses IEEEtran double-column; **must convert before resubmission**.
8. **Generalizability (Reviewer A).** Lessons must read as a technical report, not patch notes. Surface lessons that apply outside MongoDB / outside databases.

What we should *not* try to fix:
- "Limited technical novelty" (Reviewer A). The paper is an industry experience report; ISSRE Industry explicitly accepts that. We do not need to invent a new technique --- but we should sharpen the empirical case.

## Resubmission priorities

1. **More quantitative measurement.** Top priority. See proposals below.
2. **Restructure to surface generalizable lessons** (cross-language conformance, DSTL design tradeoffs, schema versioning) so the paper is not "MongoDB patch notes."
3. **Pull AI/LLM material into intro and body**, not just Future Work. The DSTL substrate is precisely what coding agents need to make polyglot driver development tractable; that is a forward-looking lesson, not an aside.
4. **Add Jeff Yemin as a co-author.** Update author block.

## Proposed quantitative measurements

Listed roughly in order of effort-to-payoff. Aim for 3--4 of these by the July 5 deadline; pick the ones that are tractable with the data we can actually access.

### A. Bug-class taxonomy from issue tracker mining (high payoff, addresses Reviewers A/B/C #1)

Once we implemented driver spec tests in YAML (both the Unified Test Format and other formats), individual drivers gradually implemented test runners and adopted the tests. Once a test runner was implemented, driver authors no longer checked in versions that failed any tests. Test failures could still sometimes occur when a driver author synced new YAML tests from the specs repo: the sync and the fix was generally checked in simultaneously.

Your task is to mine the MongoDB driver issue trackers (Jira projects per language: PYTHON, GODRIVER, NODE, JAVA, CSHARP, RUST, etc.) from the beginning of time. Use the list of drivers mentioned in the paper. Create a CSV of bugs. For each bug, classify:

- Resolution (fixed, open, works as designed, etc.)
- Relevant to which specs in the driver specs repo, if any? (https://specifications.readthedocs.io/en/latest/)
- Is it a nonconformance bug between the driver and a spec or specs?
- Does the bug description or comments say explicitly that it's an inconsistency between this driver and another driver or drivers?
- Did it predate the YAML tests for those specs?
- Could it have been prevented by a YAML test? (Delegate a subagent to search for related specific test files in the latest specs repo, and associate those files with the bug.)

### C. Test-asset amplification factor (cheap, vivid)

UTF test files are run against all ~12 drivers. So:
- N(YAML files) × N(drivers) = effective test executions per CI run.
- 606 × 12 ≈ 7,300. Translate to "lines of YAML × drivers" --- 124k × 12 ≈ 1.5M effective LOC of test, written once.
- Contrast with what writing those tests per-driver in idiomatic native test code would have required (estimate from pre-UTF driver test suites).

Cheap to compute, gives a punchy "leverage" number for the abstract.

### D. Test-runner LOC churn over time (cheap, addresses Reviewer B #4)

Per driver, mine git log of the test-runner code. Plot:
- Lines of test-runner code over time.
- Commits-per-month modifying test-runner code, before vs. after UTF adoption.

Hypothesis: UTF migration produced a step-down in churn. The 12k-line deletion is a one-time event; ongoing maintenance is the real cost claim. If the data supports it, show ongoing maintenance fell by some factor.

### E. Schema-version blockage frequency (addresses Reviewer C #2)

Reviewer C specifically called out that we hand-wave the single-schema-version problem. Make it concrete:
- Mine UTF schema git history --- when did each `schemaVersion` bump land?
- Mine each driver's test-runner repo --- when did that driver start passing tests at each `schemaVersion`?
- Compute lag (days) per (driver, schema-version) pair.
- Identify and count incidents where a driver was *blocked* from a spec because its runner was N schema versions behind.

This converts a one-sentence "Lessons Learned" item into a real graph and a recommendation.

### F. Code coverage delta from UTF (high value, high effort)

For 2--3 representative drivers, run the test suite **with vs. without** the UTF tests and measure production-code line coverage. Quantifies what fraction of driver behavior UTF actually exercises.

Effort risk: requires getting coverage tooling working in multiple languages and isolating the UTF subset. Probably the most expensive measurement on this list. Skip if A--E fill the budget.

### G. UTF vs. differential testing vs. property-based testing (addresses Reviewer B #5)

Add a focused subsection (not a full empirical study) classifying which fault classes each approach naturally catches:
- **Differential testing:** behavioral divergences across implementations *given the same input*. Cannot catch common-mode failures. No spec-author intent encoded.
- **Property-based testing:** input-space coverage; finds violations of stated invariants. Requires specs as executable properties.
- **UTF (example-based with spec-author-encoded intent):** catches both divergences (because all drivers run the same tests) and common-mode failures (because the test asserts the *intended* behavior, not just majority behavior). Weak on input-space coverage.

This is mostly conceptual but the paper currently has none of it. Adding a small table is cheap and directly addresses Reviewer B.

## AI / LLM angle for the intro

Currently AI/LLMs only appear in Future Work. Pull a paragraph forward into the introduction or a new short section. The argument:

- LLM coding agents are increasingly used to implement and maintain language-native libraries. Their effectiveness depends on **fast, machine-checkable feedback loops** and **machine-readable specifications of intent**.
- A polyglot driver ecosystem is a worst case for agents: 12 codebases, one spec, no shared core. Without UTF, an agent has no way to know whether driver X conforms.
- UTF provides exactly the substrate agents need --- a declarative test corpus that fails loudly on divergence. An agent can iterate on driver code with the same per-test signal a human gets.
- Therefore the lesson generalizes: **organizations building polyglot libraries should invest in machine-executable spec tests now** because they are the foundation for agent-assisted development of those libraries, not just for human conformance testing.

This reframes UTF from "patch-notes retrospective" to "this is what AI-ready library infrastructure looks like" --- which is also what a 2026 industry-track audience wants to hear.

## Tasks (open)

- [ ] Verify ISSRE 2026 Industry Track template (IEEEtran? Confirm column count, page limit, anonymization rules) before doing format conversion.
- [ ] Decide which 3--4 measurements from A--G to commit to. Lock by ~mid-May to leave time for data collection.
- [ ] Update author block: Jesse Davis + Jeff Yemin.
- [ ] Outline restructured paper: where do AI angle, bug-class table, consistency results, schema-blockage data, and differential/property-based comparison live?
- [ ] Draft new abstract reflecting the quantitative additions (due 2026-06-28).

## House rules (from user)

- No worktrees. Edit in place; rely on git.
- Markdown em-dashes are `---` with no spaces. No Unicode em-dashes.
- Don't catch exceptions broadly; fail loudly on the unexpected.
- If anything looks surprising or off, stop and investigate rather than pushing through.
