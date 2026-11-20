# Prompt for Claude Cowork

Paste everything below the line into Claude Cowork.

---

You are helping Shreyas finish the browser steps for his private GitHub repo `shreyas-tech7/permitcheck`. Read `docs/HUMAN_STEPS.md` in the repo first.

Do only steps that are free and can be undone:

1. Open the Actions tab and report whether the latest `CI` run on `main` and on `claude/build-permitcheck` is green. If one is red, copy the failing step name and its last lines.
2. In Settings, General, check that the default branch is `main`. If not, tell Shreyas. Do not change it yourself unless he says so.
3. Check the About box. The description should match `docs/GITHUB_ABOUT.md` and the topics should match `docs/topics.txt`. Fill in what is missing.
4. Upload `docs/social-preview.png` as the social preview in Settings, General.
5. Check the Releases page for a `v0.1.0-rc1` pre-release on the release commit named in `docs/HUMAN_STEPS.md`. Report what you see.

Do not:

- make the repo public,
- publish a package,
- enter any key, token or secret,
- sign in for Shreyas or create an account,
- pay for anything or change a billing setting,
- delete a branch, a tag or a release.

When you finish, write a short report of what you checked and changed. Then end with this prompt for the next Claude Code session, filled in:

> Context: permitcheck is a permit-check demo. The model extracts, plain code decides, and unclear cases go to a person. It runs on a fictional city with synthetic data.
> Complete: every feature except F17 (the live LLM record run). Zero false approves on the held-out set for the rule-based extractor.
> Open: F17 needs a free Groq key (see `docs/HUMAN_STEPS.md`, step 6), plus anything this Cowork report found.
> Read docs/build/BUILD_PROMPT.md and follow it. Resume from PROGRESS.md on branch claude/build-permitcheck. Do not ask questions. Do not stop until every Done-means item is true or blocked with a fallback.
