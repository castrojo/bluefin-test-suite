---
name: common-rationalizations
description: "Deep dive: Common Rationalizations"
metadata:
  type: reference
  audience: agents
  maturity: stable
---

## Common Rationalizations

- "The cache can target the runner user's podman storage."  
  It cannot here — the pulls run under `sudo`, so cache the root store or the pull will still miss.
- "A floating `uses:` tag is fine for a speedup-only change."  
  It is not; external actions in this repo must stay SHA-pinned.
- "We can replace `<readonly-upstream>/remove-unwanted-software` with an inline cleanup for speed."  
  The workflow currently uses `<readonly-upstream>/remove-unwanted-software@v9` for disk cleanup. Switching to an inline cleanup is only worthwhile if the action is the measured bottleneck — do not change this without profiling.
