# Human steps

Steps that only Shreyas can do, in order. While Shreyas was away, Claude was allowed to open and merge the pull request, create the pre-release and set the About box and topics. Check each of those on GitHub before you redo it.

Release commit: 8fb00cfa50f4861f80a58c9e8b4249b8c2dfb374

The commits after the release commit only record this SHA and the hand-off notes. Tag the release commit.

## 1. Make main the default branch

The GitHub repo was empty when the build started. The build pushed the first README commit as `main`, but GitHub made `claude/build-permitcheck` the default because it arrived first. In Settings, General, Default branch, pick `main`.

## 2. Check that CI runs

Open the Actions tab. The `CI` workflow should run on `claude/build-permitcheck` and finish green in under five minutes. The build session ran the same steps locally (`./init.sh`, `permitcheck eval --split both --check`, `permitcheck readme --check`, `scripts/assert_zero_false_approve.py` and `scripts/check_links.py`) and all passed.

## 3. Open and merge the pull request

1. Open a pull request from `claude/build-permitcheck` into `main`, unless one is already merged.
2. Read the diff.
3. Merge with a merge commit, not a squash, so the release commit stays in the history of `main`.

## 4. Tag the release candidate

```bash
git fetch origin
git tag -a v0.1.0-rc1 8fb00cfa50f4861f80a58c9e8b4249b8c2dfb374 -m "Release candidate 1"
git push origin v0.1.0-rc1
```

Or create a pre-release with that tag on GitHub.

## 5. Run the secret scan once more

```bash
gitleaks git -v .
```

The build ran it on the full history with no findings.

## 6. Record mode on a free provider

This is the step the build could not do (feature F17). Without it, the LLM extractor stays untested live.

1. Create a free key at Groq (https://console.groq.com/keys). Check the free limits first. Send only synthetic text, because some free tiers can train on prompts.
2. Run locally:

   ```bash
   ./init.sh
   export GROQ_API_KEY=your-key            # never commit it
   .venv/bin/permitcheck eval --extractor llm-record --split heldout
   .venv/bin/python scripts/assert_zero_false_approve.py results/eval_heldout_llm.json
   ```

3. Or add the secret `GROQ_API_KEY` in the repo settings and run the `Record LLM extractor (manual)` workflow from the Actions tab.
4. If the check passes, commit `results/eval_heldout_llm.json` and `fixtures/llm/`, then set `passes` to true for F17 in `feature_list.json`. If it finds a false approve, fix the extractor or the checker. Never change the answer key.
5. Decide whether the README should show the LLM numbers. Today it shows only the rule-based extractor.

## 7. Make the repo public

All history becomes public at that moment. Read `docs/build/BUILD_PROMPT.md` first (step 11).

## 8. Turn on Pages

Settings, Pages, deploy from the `main` branch and the `/docs` folder. `docs/index.html` is the results page. Put the Pages URL in the About box.

## 9. Social preview, About box and topics

- Upload `docs/social-preview.png` in Settings, General, Social preview.
- The description is in `docs/GITHUB_ABOUT.md`. The topics are in `docs/topics.txt`, one per line.

## 10. Pin the repo

Pin it on your profile, or list it in your profile README.

## 11. Decide whether the build prompt stays public

`docs/build/BUILD_PROMPT.md` holds the full prompt the agents followed. Keep it, trim it or remove it before the repo goes public.

## 12. Publish to PyPI (optional)

The name `permitcheck` was free on PyPI on 2026-11-20. If you want the package, set up trusted publishing on PyPI for this repo and add a release workflow. The build did not do this.

## 13. Update the human checks in the README

The README lists four human checks as "not done yet". Change each one only after you do it.

## 14. Show it to a real permit reviewer

Only if you want to, and only after you ask them first. Do it yourself.
