## Why

Today's AI Daily ranking publish flow can already produce usable cards and publish to Xiaohongshu, but the default body copy still reads like a machine-assembled digest. It mostly stitches together topic titles and raw `summary_zh` text, so the post often misses the one thing users actually want from a daily roundup: a quick, human-sounding sense of what happened today in AI and why these topics matter together.

## What Changes

- Add a dedicated ranking-copy composition capability that turns the day's top AI topics into a short editorial-style summary instead of a title-plus-summary dump.
- Require default ranking copy to ground its wording in concrete same-day hotspot signals, such as repeated themes, notable launches, open-source momentum, research movement, or platform-level news appearing in the selected topics.
- Add tone and structure rules for ranking publish copy so it sounds like an informed human operator: conversational but factual, selective rather than exhaustive, and concise enough for Xiaohongshu reading habits.
- Define fallback behavior so the system still produces publishable copy when some topic summaries are noisy, repetitive, English-only, or low-signal.
- Explicitly keep hashtag normalization, duplicate-summary cleanup, card differentiation, and publish-result normalization out of scope for this change because those concerns belong to `improve-xhs-ranking-publish-quality`.
- Preserve compatibility with existing ranking cards and publish APIs while changing the default content-generation behavior for AI Daily whole-ranking posts.

## Capabilities

### New Capabilities
- `ai-daily-ranking-editorial-copy`: Generate default AI Daily whole-ranking publish copy as a human-sounding editorial summary grounded in the day's selected hotspot topics.

### Modified Capabilities
<!-- None. This change introduces a new editorial-copy capability without modifying existing baseline OpenSpec capabilities. -->

## Impact

- Affected code: `app/services/publish/ai_daily_publish_service.py`, related AI Daily topic/context helpers, ranking publish tests, and any shared prompt/composition utilities introduced for ranking copy generation.
- Affected behavior: default `publish_ai_daily_ranking` content becomes more human, more selective, and more reflective of the day's actual AI theme mix.
- Affected operator experience: users should get a ranking post that feels closer to “someone read today's AI feed and summarized the big picture” instead of a plain bulletin.
