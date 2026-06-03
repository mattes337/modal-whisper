Task: condense a transcript, keeping ONLY medically/clinically/health-relevant content.
(Adapt "medical" to the actual domain if the video is non-medical — keep substantive, drop filler.)

INPUT FILE: {BLOCKS_JSON} (UTF-8 JSON). Structure:
{ "title":..., "url":..., "language":..., "duration":..., "blocks":[ {"t":"HH:MM:SS","text":"..."} , ... ] }
There are {N} blocks. Read the whole file. Topic: {TITLE}.

FOR EACH block produce a condensed version of its text:
- KEEP: concrete facts — markers/parameters, reference ranges & values, units, interpretation,
  causes, symptoms, deficiencies, recommendations, nutrition/supplement/therapy advice,
  organ/system relations, any substantive domain fact.
- REMOVE: filler words, greetings, small talk, self-introductions/biography, meta-talk
  ("we'll share the presentation now", "thanks for joining"), repetition, conversational prose, hedging.
- Output condensed text as terse bullet-style phrases separated by " • " (no full sentences needed).
  Keep the SAME language as the source. For German, use NATIVE umlauts (ä ö ü ß), not ae/oe/ue/ss.
- If a block has NO relevant content (pure intro/filler/chitchat), set its text to exactly "—".
- PRESERVE every block's timestamp "t". Keep ALL {N} blocks in order (even "—" ones).
- Do NOT invent facts. Only condense what is present. Do not translate.

ALSO produce "summary": a 3-5 sentence abstract (same language) of the whole video — main topics & themes.

OUTPUT: write {CONDENSED_JSON} (UTF-8, ensure_ascii=False) with EXACT structure:
{ "summary": "<abstract>", "blocks": [ {"t":"HH:MM:SS","text":"<condensed>"}, ... {N} items ... ] }

Use Python with encoding='utf-8' to write. After writing, verify it reloads as JSON.
Report: number of blocks written, number that are "—", and print the summary.
