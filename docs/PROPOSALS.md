# Proposals

Ideas that the brief does not list. Shreyas picks what gets built. Nothing here is built yet.

1. **Static reviewer page.** The stretch item from the brief. A page in `docs/` that loads one checklist and lets a reviewer accept or reject each item, then download the choices as JSON. It would need no server.
2. **Label learning from the review queue.** Many needs-human items come from labels the extractor does not know. A reviewer could map a new label to a field once, and the extractor would read it from then on. The map would live in a reviewed file, never learned silently.
3. **Per-rule false-approve table.** The eval already counts false approves by rule. A table by rule would show which checks carry the most risk.
4. **A second fictional code.** A second city with different setbacks would test that nothing in the checker is tied to Larkspur Hollow.
5. **Plan drawings.** Out of scope for this demo. Reading dimensions from drawings would need image models and a new eval set.
