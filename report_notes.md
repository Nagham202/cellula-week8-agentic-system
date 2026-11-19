# Report Notes: Document Pipeline + Retriever Agent (Nagham)

## Summary

**My part:** the document pipeline (PDF/DOCX/TXT -> clean -> chunk -> embeddings -> Qdrant) and
the Retriever Agent, which only finds evidence and never answers.

**Final pipeline**
```
upload:    load -> clean -> chunk (500/100, source/page/section/chapter) -> bge-small dense + BM25 sparse -> Qdrant (local)
question:  query rewriter (LLM) -> metadata filter (rules) -> hybrid search, RRF (20 candidates)
           -> reranker (MiniLM-L-6 cross-encoder) -> context selector (no near-copies, all named files, size budget) -> 6 evidence items
```

**Interface for the team:** `retrieve(question, chat_history, top_k, filters)`,
`retrieve_more(query, already_seen_ids, top_k)` (Analyst feedback loop), `retrieve_with_details(...)`,
`ingest_file(path)`, `delete_source`, `list_sources`, `count_chunks`; `fake_retriever` for offline tests;
shared `src/llm.py` (`get_llm(role)`, Groq -> OpenRouter -> Ollama). See README.md.

**Key results** (28 test questions: 11 meaning, 11 exact-term, 6 follow-ups; right document + page)

| Version | hit@1 | hit@3 | hit@5 | MRR |
|---|---|---|---|---|
| semantic only | 0.71 | 0.82 | 0.89 | 0.77 |
| keyword (BM25) only | 0.64 | 0.86 | 0.86 | 0.74 |
| hybrid (RRF) | 0.75 | 0.89 | 0.93 | 0.83 |
| hybrid + query rewriter + alternatives | 0.82 | 0.93 | 0.96 | 0.88 |
| **full pipeline (+ reranker + selector)** | 0.79 | **0.96** | 0.96 | 0.88 |

- Semantic wins on reworded questions, keyword on codes/numbers; hybrid is as good as the better one in each group.
- The query rewriter matters for follow-ups (MRR 0.67 -> 0.92) and changes nothing on clear questions.
- The reranker adds little on this set (it is near its ceiling); the biggest reranker was the worst and slowest.
- Still unsolved: "Which pre-trained model writes the answers?" (paper says "Generator: BART").
- Caveats: small set (1 question = 0.036), questions written by me after reading the passages.

**Checks:** 50 pytest tests (no LLM calls; fake LLM for the rewriter, temporary Qdrant folders);
end-to-end script: upload -> ask -> follow-up -> re-upload (old version gone) -> delete, 7/7 OK.

**Main challenges** (details below): pypdf returns footers out of position; page numbers with 1 vs
2 digits; heading-only chunks; references/appendix labeled as "Discussion"; free OpenRouter model
removed (404) or busy (429); multi-query RRF over-weighting a repeated expansion; near-identical
fake test chunks correctly removed by the selector.

## Decisions

### Retriever design: fixed pipeline (not an LLM agent)
- Chosen: `retrieve()` always runs rewrite -> hybrid search -> rerank -> select.
- Alternative: an LLM agent that chooses which tools to call.
- Why: simpler to debug and test piece by piece, fewer LLM calls (free-tier limits),
  predictable results. The task requires the Retriever to *use* these tools, not
  that an LLM must choose them. Agent-like behavior comes from the Analyst's
  feedback loop (`retrieve_more`).

### Work order change
- Moved the fake retriever to Step 1 so teammates can start building the Analyst
  and Answer agents right away, using the agreed evidence format.
- The fake lived in the final file (`src/retriever/retriever.py`) with the final
  function names, so teammates' import line never changed when the real search
  replaced it (Step 7; the fake then moved to `fake_retriever.py` for tests). Fake data includes the CNN 92/95/89 example (for the Analyst's
  calculator), a DOCX item with page None (for the Answer Agent's citations), and
  one extra item only reachable via `retrieve_more` (for the feedback loop).

## Setup
- Python 3.12 venv, packages in requirements.txt (LLM packages added at Step 7).
- Shared config.py: QDRANT_PATH, COLLECTION_NAME, CHUNK_SIZE=500, CHUNK_OVERLAP=100,
  SPARSE_MODEL="Qdrant/bm25", TOP_K=6, LLM_PROVIDER. DENSE_MODEL decided at Step 4.

### Loaders: reuse Week 6 (trimmed to PDF/DOCX/TXT)
- Alternatives: LangChain community loaders (extra package, 0-based pages,
  docx2txt drops tables), `unstructured` (heavy install).
- Kept: one Document per PDF page, empty/scanned pages skipped, DOCX tables kept,
  SourceError with one clear message per broken file.
- Changed: `page = None` for DOCX/TXT so every chunk has the same keys;
  removed PPTX/WAV/web loaders and the logger; no cleaning inside loaders.
- Test files: Week 6 samples (kito_manual.pdf 3 pages, hr_policy.docx, nova_faq.txt).

### Cleaning (src/pipeline/cleaning.py)
Order: normalize -> remove repeated headers/footers (PDF only) -> join broken lines -> drop empty pages.
- Normalize: Unicode NFKC ("ﬁ" -> "fi", non-breaking space -> space), one space
  between words, at most one empty line in a row.
- Headers/footers: a line is a header/footer if its pattern (digits replaced by "#")
  appears in the top 2 or bottom 2 lines of at least half the pages. Only removed
  from those edge positions, never from the middle of a page. Skipped for PDFs with
  fewer than 3 pages (a repeat could be a coincidence).
- Broken lines: join when the next line starts with a lowercase letter; remove
  the hyphen if the previous line ends with "-"; never join after a line ending
  with ":" (equations, lists). Table rows, headings, list items stay separate.
  Arabic has no lowercase, so Arabic lines are never joined (safe: a missed join
  is harmless because the chunker keeps nearby lines together anyway).
- Empty pages: dropped after cleaning; page numbers in metadata stay the original ones.

Test file: scripts/make_messy_pdf.py -> data/samples/messy_report.pdf (4 pages:
repeated header, "Page N of 4", hyphen break "docu-/ments", extra spaces,
page 3 only header+footer, a model table with BERT-base, an "Equation 12").

### Chunking + metadata (src/pipeline/chunking.py)
- 500/100 RecursiveCharacterTextSplitter (Week 6 result).
- Sections: chose simple heading rules over no sections (can't answer "Chapter 4"
  questions) and over an LLM (1 call per page, free-tier limits). A line is a heading
  if it is at most 80 characters, does not end with ".", and matches
  "4 Results" / "4.2 Training" / "Chapter 4: Results" / "Section 2.1 Models".
  A section continues on the next page until the next heading.
- Two extra fields on every chunk: `section` (heading text, for citations) and
  `chapter` (top number, for the "Chapter 4" filter; covers 4.1, 4.2 ...).
- Header on every chunk: "Source: file.pdf, page 2, section: 2. Models and Results".
- chunk_id: "file.pdf_p2_c3" (page + running number in the file) or "file.docx_c5".
- Heading-only pieces (heading = last line of a page) are dropped; the text follows
  in the next chunk with the same section.
- Added in Step 5: named headings (exact line "Abstract", "References",
  "Acknowledgments", "Broader Impact", ... -> chapter None) and appendix letter
  headings ("G Parameters" -> chapter "G"), the letter ones only after "References"
  so a sentence like "A Kito robot moves shelves" is never taken as a heading.
  Before this, references and appendix pages 10-19 of the RAG paper were labeled
  "6 Discussion". Now the paper's full structure is found (Abstract, 1-6, Broader
  Impact, Acknowledgments, References, A-H).
- Known limits: other unnumbered headings are not detected; a short numbered list
  item without a full stop can look like a heading.

### Embedding model: BAAI/bge-small-en-v1.5 (fastembed 0.9.1)
| Model | Languages | Size | Dim | Why not / why |
|---|---|---|---|---|
| **bge-small-en-v1.5** | English | 67 MB | 384 | chosen: fast, tiny, strong retrieval for its size |
| bge-base-en-v1.5 | English | 210 MB | 768 | slightly better, ~3x slower (compare in Step 10) |
| nomic-embed-text-v1.5 | English | 520 MB | 768 | Week 6 model; big for a small gain |
| multilingual-e5-large | 100+ incl. Arabic | 2.24 GB | 1024 | only if Arabic docs are needed; BM25 is English-tuned too |
| paraphrase-multilingual-MiniLM-L12-v2 | multilingual | 220 MB | 384 | built for sentence similarity, weaker at passage retrieval |
- Query prefix for bge: "Represent this sentence for searching relevant passages: ".
- One line in config.py; changing it = delete data/qdrant and ingest again.

### Qdrant: qdrant-client directly (not langchain-qdrant)
- Hybrid search, filters and reranking need Qdrant's own objects anyway; one library
  instead of two layers. Teammates never touch Qdrant, they only call retrieve().
- Local mode (data/qdrant), cosine distance, named vectors "dense" and "bm25" (sparse).
- Point id = uuid5(chunk_id): same chunk_id always gives the same id, so a re-upload
  overwrites the same points.
- Re-upload (like Week 6): upsert new chunks first, then delete leftovers
  (same source, chunk_id not in the new list). A failure never loses the old version.
- Local mode locks the folder: only one program at a time (one shared client;
  clear error message if another program has it open).

### Hybrid search: BM25 sparse vectors + Qdrant RRF fusion
- BM25 via fastembed "Qdrant/bm25": lowercase, stopwords removed, English stemming,
  words stored as hashed ids. Qdrant applies IDF itself (modifier=IDF), so word
  rarity stays correct as files are added. Chunks: embed(); questions: query_embed().
- Fusion options: Qdrant built-in RRF (chosen: one call, filter applies to both
  searches), own weighted sum (cosine 0-1 vs BM25 0-30+ needs normalizing, fragile),
  own RRF code (two calls, filters twice).
- RRF: score = sum of 1/(rank + k) over both lists; Qdrant uses k = 2 with ranks
  from 0, so #1 in both lists = 1/2 + 1/2 = 1.0. Uses ranks, not scores.
- Each search fetches 20 candidates (HYBRID_CANDIDATES) before merging.
- Scores only mean something inside one search type (told teammates: use for ordering).

### Metadata filter (src/retriever/filters.py)
- Options: simple rules (chosen), an LLM that returns JSON (1 call per question, can
  invent file names, harder to test), or rules + the LLM rewriter (decide at Step 7).
- Filter = plain dict {"sources": [...], "pages": [first, last], "chapter": "4"}, so the
  Streamlit app can also pass one from a dropdown without importing Qdrant.
- Rules: file names are matched only against files really stored in Qdrant
  (list_sources), with or without extension, "_" or space ("rag_paper.pdf",
  "rag_paper", "rag paper"); several names -> any of them (document comparison).
  "page 4" / "pages 2-4" / "pages 2 to 4" -> page range; "chapter 4" /
  "section 4.2" -> chapter "4"; "appendix G" -> chapter "G".
- The filter goes inside both prefetches of the hybrid search.
- Fallback: a filter can match nothing ("page 2 of hr_policy.docx": DOCX has no
  pages; "page 50" of a 19-page paper). relax_filters() keeps only the file names;
  retrieve() will retry with it and tell the Analyst the filter was relaxed.
- Known limits: "section 4.2" filters the whole chapter 4; vague names
  ("the robot manual") are not understood by the rules.

### First real retrieve() (src/retriever/retriever.py)
- Replaced the fake with: filters (from the app, or read from the question) ->
  hybrid search -> fallback with relax_filters if nothing is found.
  Same function names and list format, so teammates' code did not change.
- retrieve_more(query, already_seen_ids): same search, but Qdrant leaves out the
  chunks the Analyst already has (must_not chunk_id in seen ids), so the feedback
  loop always brings new evidence. Filters are also read from the Analyst's query.
- retrieve_with_details(): returns {"evidence", "search_query", "filters",
  "filters_relaxed"}. Chosen instead of changing retrieve()'s return type (would
  break teammates' code). For the Orchestrator / a "how did we search" panel.
- Optional `filters` argument on retrieve() so the Streamlit app can pass a
  "search only in" choice.
- The fake moved to src/retriever/fake_retriever.py (same functions) for
  teammates' tests that should not need Qdrant or models.

### Shared LLM helper (src/llm.py, for the whole team)
- Options: LangChain chat classes (chosen: Week 6 code, built-in with_fallbacks,
  Analyst can use bind_tools) vs the openai package for all three providers
  (1 package, but own fallback code and more manual tool calling).
- get_llm(role): role = "rewriter" / "analyst" / "answer", each with its own Groq
  model because Groq limits are per model. gpt-oss models use reasoning_effort="low"
  (hidden thinking tokens count against the limit, Week 6).
- LLM_PROVIDER = main provider; fallbacks groq -> openrouter -> ollama, skipping
  providers without a key. Missing key for the MAIN provider = clear error (no silent
  switch). max_retries=2 so a busy provider hands over quickly.
- Keys in .env (git-ignored), template in .env.example.
- OpenRouter free models (checked 2026-11-07): "openai/gpt-oss-20b:free" no longer
  exists (404, paid only). Gemma 4 free models returned 429 (shared free capacity
  busy). NVIDIA Nemotron free models answered: rewriter =
  nemotron-3.5-lightning:free, analyst/answer = nemotron-3-ultra-550b-a55b:free.
  Avoided "stealth"/preview models and "openrouter/free" (random model each time,
  results can't be repeated). Free models change often -> check before the demo.
- Test (python -m src.llm): groq 0.3 s, ollama 0.1 s, openrouter OK after the change.
- pytest: 3 tests in tests/test_llm.py (no calls sent), 33 total, all pass.

### Query rewriter (src/retriever/query_rewriter.py)
- Week 4 recipe: clear rules, 3 few-shot examples, temperature 0, JSON reply,
  forgiving parser (finds {...} inside extra text / code fences), safe fallback
  (LLM error or broken reply -> search the original question).
- Output: {"query", "alternatives" (max 2), "rewritten"}. Rules: resolve "it/its/they",
  expand an abbreviation only if sure (keeping it), keep exact terms (file names,
  page/chapter numbers, codes, model names, numbers), never add facts.
- Chat history: [{"role": "user"/"assistant", "content"}], last 3 turns, assistant
  answers cut to 400 characters (Week 6).
- Search: rewritten query + alternatives + the original question (safety net), all
  merged by RRF in one Qdrant call (hybrid_search extra_queries). Filters are read
  from original + rewritten text (a file name may only be in the conversation).
- Every question is rewritten (switch: USE_QUERY_REWRITER); retrieve_more is not
  (the Analyst's query is already specific). Model: Groq openai/gpt-oss-20b.
- Examples: "What are its disadvantages?" (after "What is RAG?") -> "What are the
  disadvantages of Retrieval-Augmented Generation (RAG)?"; "and what about E47?"
  -> "What does error E47 mean on the Kito robot?"; "DPR" left unexpanded (not sure).

### Reranker (src/retriever/reranker.py)
- Two-stage retrieval: hybrid search gives 20 candidates (fast, approximate), a
  cross-encoder reads question + chunk together and re-scores them (precise, slower).
- Options: fastembed TextCrossEncoder (chosen: installed, ONNX, local, no torch),
  sentence-transformers CrossEncoder (needs PyTorch), LLM reranker (1 big call per
  question, free-tier limits, less stable scores).
- Model chosen by measuring 3 (see Results): Xenova/ms-marco-MiniLM-L-6-v2 (80 MB).
- Scores mapped to 0..1 with sigmoid. Very low (< 0.05) usually = not relevant, but
  related chunks often all get ~0.99, so a high score is no proof of "enough evidence".
- Reranks against the rewritten query. Switch: USE_RERANKER.

### Context selector (src/retriever/selector.py)
- Options: greedy + duplicate threshold (chosen: simple, one clear rule) vs MMR
  (mixes relevance and similarity scales with a lambda that is hard to tune/explain).
- Goes down the reranked list; skips a chunk if cosine similarity (dense vectors) to an
  already chosen chunk > 0.92, or if it would exceed 4,500 characters (~1,100 tokens;
  the first chunk is always kept). Max 8 chunks (default 6).
- If the question names 2+ files (comparison), the best chunk of each file is taken
  first, then the list is sorted best-first again.
- Threshold check: among all pairs of top-20 candidates for the 28 questions (4,737
  pairs), 0 above 0.95, 6 above 0.92, 71 above 0.85. The pairs above 0.92 were real
  repeats: the paper's abstract vs. the same sentences in its introduction (0.936),
  title vs. "Appendices for <title>" (0.939), neighbouring reference-list entries.

## Results

### Cleaning
| File | Documents before -> after | Characters before -> after |
|---|---|---|
| hr_policy.docx | 1 -> 1 | 483 -> 483 |
| kito_manual.pdf | 3 -> 3 | 979 -> 976 (only trailing newlines) |
| messy_report.pdf | 4 -> 3 | 1058 -> 819 |
| nova_faq.txt | 1 -> 1 | 775 -> 774 (only trailing newline) |
- messy_report.pdf: header and page numbers removed from all pages, page 3 dropped,
  "docu-ments" -> "documents", table rows kept separate.
- pytest: 8 tests in tests/test_cleaning.py, all pass (no files, no LLM).
- Real paper (rag_paper.pdf, Lewis et al. 2020, arXiv 2005.11401, 19 pages):
  page numbers removed after the digit-group fix (see Challenges).

### Chunking
| File | Chunks | Size (characters) | Sections |
|---|---|---|---|
| hr_policy.docx | 1 | 506 | 0 |
| kito_manual.pdf | 3 | 314-394 | 0 |
| messy_report.pdf | 3 | 264-354 | 2 |
| nova_faq.txt | 2 | 403-411 | 0 |
| rag_paper.pdf | 200 | 68-571 | 19 |
- The heading rule found all 20 numbered headings of the RAG paper (1 Introduction ...
  6 Discussion, incl. 2.1-4.5) with no false matches. 19 remain as sections because
  "4 Results" is directly followed by "4.1 ..." (heading-only piece dropped);
  chapter 4 chunks still have chapter = "4".
- Heading-only chunks: 11 chunks under 150 characters before the fix, 6 after
  (the rest are real content such as formulas).
- pytest: 4 tests in tests/test_chunking.py (12 total), all pass.

### Ingestion + semantic search (first check, 6 questions)
- 5 files -> 209 chunks; rag_paper.pdf (200 chunks) in 3.2 s on M4 Pro.
- Re-uploading messy_report.pdf: total stays 209 (replaced, not duplicated).
- Correct document ranked #1 for all 6 questions.
- "What does error E31 mean?": correct chunk #1 but score only 0.560 vs 0.545 for an
  unrelated chunk -> semantic search is weak on codes/IDs (motivation for BM25).
- pytest: 3 tests in tests/test_store.py (temporary Qdrant folder), 15 total, all pass.

### Semantic vs keyword vs hybrid (eval/questions.json, 22 questions, top 5)
Script: eval/compare_search.py, full table in eval/results/search_comparison.md.
A hit = a chunk from the right document and page. MRR = average of 1/rank of the
first right chunk (0 if not in top 5).

| Search | Questions | hit@1 | hit@3 | hit@5 | MRR |
|---|---|---|---|---|---|
| semantic | all (22) | 0.77 | 0.82 | 0.91 | 0.81 |
| keyword | all (22) | 0.77 | 0.86 | 0.86 | 0.82 |
| **hybrid** | all (22) | **0.82** | **0.91** | **0.95** | **0.88** |
| semantic | meaning (11) | 0.64 | 0.73 | 0.91 | 0.70 |
| keyword | meaning (11) | 0.55 | 0.73 | 0.73 | 0.64 |
| hybrid | meaning (11) | 0.64 | 0.82 | 0.91 | 0.75 |
| semantic | exact (11) | 0.91 | 0.91 | 0.91 | 0.91 |
| keyword | exact (11) | 1.00 | 1.00 | 1.00 | 1.00 |
| hybrid | exact (11) | 1.00 | 1.00 | 1.00 | 1.00 |

- Semantic is better on "meaning" questions (hit@5 0.91 vs 0.73), keyword on "exact"
  questions (1.00 vs 0.91). Hybrid is as good as the better one in each group and
  best overall.
- Where keyword helps: "What does 15.3B refer to?" semantic not in top 5, keyword #1.
- Where semantic helps: "Which optimizer was used?" (text says "Adam") semantic #1,
  keyword not in top 5 (the word "optimizer" is not in the text).
- Fails in all three: "Which pre-trained model writes the answers?" (paper: "Generator:
  BART") -> to retry with query rewriter / reranker.
- First version had only 7 easy exact questions: all methods scored 1.00 because the
  small collection has just one chunk about error codes. Added 4 harder ones (numbers
  and names inside tables/technical text) to really test exact terms.
- Caveats: 22 questions (1 question = 0.045), I wrote the questions after reading the
  passages; the differences are a direction, not a proof.
- pytest: 3 tests in tests/test_search.py (keyword finds a code, semantic finds a
  synonym, hybrid returns the agreed format), 19 total, all pass.

### Query rewriter: on vs off (28 questions, 6 of them follow-ups with chat history)
Rewrites cached in eval/results/rewrites.json (28 LLM calls once, 0 fallbacks).

| Version | All (28) hit@1 | hit@3 | MRR | Follow-up (6) hit@1 | hit@3 | MRR |
|---|---|---|---|---|---|---|
| hybrid | 0.75 | 0.89 | 0.83 | 0.50 | 0.83 | 0.67 |
| hybrid+rewrite | 0.79 | 0.93 | 0.87 | 0.67 | 1.00 | 0.83 |
| **hybrid+rewrite+alts** | **0.82** | **0.93** | **0.88** | **0.83** | **1.00** | **0.92** |
- Meaning and exact questions: identical with and without the rewriter (no harm).
- Follow-ups: "How well did RAG do on it?" (it = FEVER): not in top 5 -> #1.
- Kept alternatives ON (best numbers). Small loss: "Which model is used to find the
  documents?" rank 4 -> 5 with alternatives.
- Observed weak case (not in the test set): "How does RAG do on fact verification?"
  -> the expansion "Retrieval-Augmented Generation (RAG)" appears in the query and both
  alternatives, so the messy_report title chunk ("Retrieval-Augmented Generation: A
  Short Study") ranks high in every list and RRF puts it #1. The reranker (next step)
  should fix this kind of case.
- Caveat: only 6 follow-up questions; a direction, not a proof.
- pytest: 7 tests in tests/test_query_rewriter.py with a fake LLM (no API calls);
  retriever tests switch the rewriter off; 40 total, all pass.

### Reranker models (eval/compare_rerankers.py, 28 questions, 20 candidates -> top 5)
| Reranker | hit@1 | hit@3 | hit@5 | MRR | ms/question |
|---|---|---|---|---|---|
| no reranker (hybrid+rewrite+alts) | 0.82 | 0.93 | 0.96 | 0.88 | 0 |
| **MiniLM-L-6 (80 MB)** | 0.79 | **0.96** | 0.96 | 0.88 | **86** |
| MiniLM-L-12 (120 MB) | 0.79 | 0.96 | 0.96 | 0.87 | 170 |
| bge-reranker-base (1 GB) | 0.71 | 0.93 | 0.93 | 0.81 | 382 |
- Small gain only: +1 question in the top 3, -1 at rank 1, same MRR. The test set is
  near its ceiling (hit@5 0.96 already), so there is little room to improve.
- The biggest model was the worst here (lost "And can I work from home?" and two
  follow-ups) and 4x slower -> bigger is not automatically better; measure.
- Fixed the Step 8 weak case: "How does RAG do on fact verification?" messy_report
  title chunk #1 -> #3, two "3.4 Fact Verification" chunks on top.
- Still unsolved: "Which pre-trained model writes the answers?" The right chunk
  ("2.3 Generator: BART") IS among the 20 candidates (#13) but no reranker moves it
  into the top 5: "writes the answers" vs "generator" is too far apart.
- Decision: keep MiniLM-L-6 ON (cheap, never worse on average, fixes a real weak case,
  the two-stage design from the task), with a switch to turn it off.

### Full pipeline (retrieve(): rewrite + alts -> 20 candidates -> rerank -> select)
- Same as rerank only on the test set: hit@1 0.79, hit@3 0.96, hit@5 0.96, MRR 0.88
  (no near-duplicates in the top 5 of this collection, so the selector removes nothing).
- Comparison question ("Compare kito_manual.pdf and rag_paper.pdf ...") returns chunks
  from both files.
- pytest: 5 tests in tests/test_reranker_and_selector.py; retriever tests needed
  different text per fake page (near-identical fake chunks were correctly dropped as
  duplicates by the selector); 45 total, all pass.

### Metadata filter tests
| Question | Filter | Top 3 results |
|---|---|---|
| According to Chapter 4 of rag_paper.pdf, how well does RAG do on fact verification? | sources rag_paper.pdf, chapter 4 | p6, p7, p7 all "4.4 Fact Verification" |
| (same question, no filter words) | none | p6, p7 "4.4", and p5 "3.4 Fact Verification" (experiment setup, chapter 3) |
| What is on page 19 of the RAG paper? | sources rag_paper.pdf, pages 19-19 | all page 19 |
| What does the kito_manual say about error codes? | sources kito_manual.pdf | all kito_manual.pdf (p3 first) |
| Compare messy_report.pdf and rag_paper.pdf: can the knowledge be updated without retraining? | both sources | messy_report p1, rag_paper p9, p8 |
| What is in Appendix G? | chapter G | all "G Parameters" (p18-19) |
| What is on page 50 of rag_paper.pdf? | pages 50-50 | 0 results -> needs fallback |
| What does page 2 of hr_policy.docx say about leave? | pages 2-2 | 0 results (DOCX has no pages) -> needs fallback |
- pytest: 6 tests in tests/test_filters.py (no LLM; one uses a temporary Qdrant),
  25 total, all pass.

### First real retrieve()
- "How does RAG do on fact verification?": 6 chunks, all from 4.4 / 3.4 Fact Verification.
- retrieve_more("FEVER label accuracy of RAG compared to BART", 6 seen ids): 4 new
  chunks (incl. the page 8 results table), none of the 6 repeated.
- "page 2 of hr_policy.docx": first search 0 results -> relaxed to the file only ->
  hr_policy.docx_c1, filters_relaxed = True.
- App filter {"sources": ["messy_report.pdf"]}: only messy_report.pdf chunks.
- pytest: 5 tests in tests/test_retriever.py, 30 total, all pass.

## Challenges
- pypdf returns text in drawing order, not page position: the footer "Page 1 of 4"
  came out as line 2, right after the header. That's why the rule checks both the
  top and bottom lines instead of only the last line for footers.
- First version joined "score = 0.7 * accuracy" (starts lowercase) onto the
  sentence before it. Fixed with the "don't join after ':'" rule.
- Page numbers were not removed on the 19-page real paper: one "#" per digit made
  "9" -> "#" and "12" -> "##" two different patterns, each on less than half the
  pages. Fixed by turning a group of digits into one "#". My 4-page test PDF could
  not show this, so testing on a real document was needed.
- Known limits: "state-of-" + "the-art" would become "state-ofthe-art" (rare);
  a table that ends a page with a single-number line could look like a page number.

## Agreed formats (final)
- Chunk payload: {source, type, page, section, chapter, chunk_id, text} (section, chapter added).
- Evidence item: {source, page, text, score, chunk_id} + type, section, chapter.
- `retrieve(question, chat_history=None, top_k=6, filters=None)`
- `retrieve_more(query, already_seen_ids=None, top_k=4)`
- chat_history: [{"role": "user"/"assistant", "content": "..."}], oldest first.

## Open questions for the team (status)
- Reranker and context selector: built in my part (they sit between search and the Analyst);
  separate files, easy to hand over if the team decides otherwise. -> confirm with team
- DOCX/TXT have page = None: the Answer Agent cites only the file name (or the section). -> confirm
- Shared LLM helper: written by me (src/llm.py), roles "rewriter", "analyst", "answer".
- Embedding model: proposed BAAI/bge-small-en-v1.5 (English). -> confirm (Arabic would need
  multilingual-e5-large and a different BM25 language).


---

# Week 8: FastAPI Backend + Terraform (Nagham)

Team split: me = FastAPI deployment + Terraform. Teammate 2 = voice (speech to text) + image OCR.
Teammate 3 = Report Generator Agent (PDF).

## Summary
- FastAPI app (api/): 7 endpoints (/health, /upload, /sources, DELETE /sources/{name}, /ask, /ask-voice,
  /report), Pydantic models for every request/response, clear 400/404/422/503/500 errors, logging to
  logs/api.log, models and Qdrant loaded once at startup. Teammates' functions are fakes behind one import.
- Answer cache (SQLite): repeated question 0.002 s instead of about 2.5 s, 0 LLM calls.
- 24 API tests (TestClient, fakes, temporary database): all pass in about 1.3 s. Whole suite: 101 pass.
- Dockerfile: 1.52 GB image, healthy container, keys passed at run time (never in the image), data on a volume.
- Terraform (infra/, Docker provider, small module): fmt, init, validate and plan all pass
  ("Plan: 3 to add, 0 to change, 0 to destroy"); outputs saved in infra/results/.
- Docs: api/README.md (endpoints, contracts, Docker, tests), infra/README.md (design, variables, outputs,
  how to init/validate/plan, secrets), plus a short section in the main README.

## Decisions

### Endpoints (proposed to the team)
GET /health, POST /upload, GET /sources, DELETE /sources/{name}, POST /ask, POST /ask-voice, POST /report.
- Images go through /upload too (no separate /ocr): the client doesn't need to know how a file is read.
- /ask calls chat_graph.ask() (Orchestrator + Answer Agent + cache), the same function Streamlit uses.

### Function contracts for teammates (fakes in api/fakes.py until theirs are ready)
- transcribe(audio_path) -> str
- extract_text(image_path) -> str
- generate_report(question, answer, analysis, sources, style) -> pdf_path

### Qdrant lock: one program at a time
Local Qdrant allows only one program to open data/qdrant. Chosen: run the API and Streamlit one at a time
for now; later Streamlit will call the API, so only the API opens Qdrant. uvicorn runs with 1 worker.
Rejected: Qdrant server in Docker (removes the lock but more setup and changes the Week 7 store code).

### Uploads
Saved to a temporary folder with the real file name (it becomes the citation), ingested, then deleted
(chunks live in Qdrant). Allowed: PDF, DOCX, TXT (images later with OCR). Limit: 20 MB (config.MAX_UPLOAD_MB).

### Pydantic models (api/schemas.py)
Every response has a model, so /docs shows teammates the exact format, and bad input gets an automatic 422.

### Extras added before the API work
- Answer cache (src/cache.py, SQLite file data/cache.sqlite3): same question -> saved answer, 0 tokens.
  Key = normalized question + settings; cleared when documents change; follow-ups in a conversation
  are not cached; only answers with sources are saved; 24 h expiry. Same idea as Week 6 (Redis), but
  SQLite needs no server.
- Streamlit app restyled to match the Week 6 app, in dark mode.

## Results

### Step 1-2: /health, /upload, /sources, DELETE /sources/{name}
- /health -> {"status": "ok"}
- /upload "Lina Haddad.pdf" -> 200, 10 chunks; /sources -> 7 files, 221 chunks
- /upload x.exe -> 400 "Unsupported file type"; empty .txt -> 400 "No text could be found"
- DELETE unknown name -> 404

### Step 3: /ask (real LLM calls)
- {"question": "What does error E31 mean?"} -> 200, answer cites kito_manual.pdf page 3, from_cache false
- Follow-up "How do I fix it?" with 2 history messages -> 200, 3 steps (stop, clean, restart),
  sources kito_manual.pdf pages 2 and 3, from_cache false (follow-ups are never cached)
- Empty question -> 422; role "robot" -> 422 (checked by Pydantic before any LLM call, 0 tokens)

### Chat history: the client sends it with every /ask (stateless API)
Same format ask() and Streamlit already use. Rejected: server-side sessions (needs storage, expiry,
a "new conversation" endpoint, and history is lost on restart).

### Step 4: fakes + /ask-voice + /report + images in /upload (with fakes, temporary database)
- Image upload (.png) -> fake OCR text -> ingest_text() -> same cleaning/chunking/Qdrant -> 200, 1 chunk
- /ask-voice (.m4a) -> transcript + answer + sources + analysis; .txt -> 400 with the allowed types
- /report -> 200, application/pdf, downloads as report.pdf; empty answer -> 422
- Full test suite: 79 passed
- Against the real running server (real LLM, fake voice/OCR/report): image upload -> 1 chunk, deleted;
  /ask-voice -> transcript + real answer (kito_manual.pdf p3) in 2.2 s; the same question on /ask right
  after -> from_cache true (the voice question had filled the cache); /report -> 1-page PDF download
  with the question, sources and style; empty answer -> 422; .png to /ask-voice -> 400

### Report input: /ask returns the analysis too
ask() now returns analysis (also saved in the cache; CACHE_VERSION 1 -> 2 so old entries without it are
not reused). The client sends question + answer + analysis + sources to /report: no extra LLM calls, and
the report shows the same answer the user saw. Rejected: /report runs the question again (tokens twice,
answer may differ).

### Report style: optional plain-text instructions
style: str | None, e.g. "formal, navy headings, large title". Teammate 3's agent turns the words into fonts,
sizes and colors, so the agent really controls the design. Rejected: a fixed dict of design fields.

### Fakes (api/fakes.py)
Same names and inputs/outputs as agreed. main.py imports them in one line; swapping to the real code
changes only that line. Fake report = a small reportlab PDF in data/reports/ (git-ignored).

### Step 5: errors, loading models once, logging
Found: when every LLM provider fails, the Answer Agent returns "Sorry, the answer could not be generated"
with status 200 (looks like success), and the Analyst doesn't catch errors (plain 500, no message).
Fixed in the API layer only (teammates' code unchanged):
- answer_or_503(): wraps ask() for /ask and /ask-voice. An exception, or the Answer Agent's error message
  -> 503 "The AI service is not available right now". Logged with the full traceback.
- Global exception handler: any unplanned error -> 500 JSON {"detail": "... see logs/api.log"} + traceback in
  the log, instead of a plain-text crash.
- Startup (FastAPI lifespan): loads the dense + BM25 embedding models and the reranker, and opens Qdrant.
  The first question no longer waits for models, and a locked database stops the server at startup with
  a clear message instead of failing on the first request.
- Logging: Python logging to the terminal and logs/api.log (git-ignored): uploads, deletes, rejected files,
  each answer with time, from_cache and number of sources, transcripts, reports, errors.
Live results (running server): startup "Loading the models and opening Qdrant..." -> "Ready" in 0.2 s
(models already downloaded); new question 2.45 s with 3 Groq calls in the log (rewriter, analyst, answer);
same question again 0.002 s from the cache; .py upload -> 400 (logged as "Rejected"); unknown delete -> 404;
a second server started while the first held data/qdrant -> "Application startup failed" with the clear
Qdrant lock message, and the first server kept working.
Simulated results: LLM exception -> 503; Answer Agent error message -> 503; /ask-voice with LLM down -> 503;
bug in /sources -> 500 JSON + traceback in the log; normal /ask -> 200.

### Step 6: automatic API tests (tests/test_api.py)
24 tests with FastAPI's TestClient, one or more per endpoint, success and error cases:
/health; /upload (txt, image via OCR fake, wrong type 400, too big 400, empty 400, ../../ path kept to the
name); /sources (empty, counts, delete, unknown 404); /ask (reply, history passed as dicts, empty question
422 with no ask() call, bad role 422, LLM exception 503, Answer Agent error message 503); /ask-voice
(transcript + answer, non-audio 400, silence 400 with no ask() call); /report (PDF bytes, every field
reaches the report agent, empty answer 422); unexpected bug 500 JSON.
How: ask() replaced by a fake (no LLM calls, no tokens), temporary Qdrant folder per test (monkeypatch),
reports written to a temporary folder. Result: 24 passed in 1.33 s, even while the real server held the
data/qdrant lock (proves the tests never open the real database). Whole suite: 101 passed, 2 failed only
because of that lock (Week 7 tests that use the real database).

### Step 7: Dockerfile (Docker Desktop 4.99, engine 29.9.3, linux/aarch64)
- Base python:3.12-slim; requirements installed before copying code (layer cache: code changes rebuild in
  seconds); only config.py, src/, api/ copied (.dockerignore excludes .env, .venv, data, tests, ...).
- Embedding, BM25 and reranker models downloaded during the build (FASTEMBED_CACHE_PATH=/app/models), so the
  container starts without internet access to the model hub.
- Secrets: not in the image. Passed at start with --env-file .env (config.py already reads os.getenv).
  Checked: no .env file and no GROQ_API_KEY inside the image.
- Data: /app/data is a VOLUME; the project's data/ folder is mounted with -v, so Qdrant (223 chunks), the cache
  and reports survive container restarts. Still one program at a time (stop local uvicorn/Streamlit first).
- HEALTHCHECK calls /health every 30 s; uvicorn --host 0.0.0.0 (reachable from outside) --workers 1 (Qdrant lock).
Results: first build 1 min 55 s; image 1.52 GB. Container status "healthy" after 18 s; startup log
"Loading the models..." -> "Ready" in 0.27 s; /sources -> 7 files, 223 chunks (mounted data);
/ask "How long does the Kito robot take to charge?" -> "about 90 minutes [kito_manual.pdf, page 1]" in 4.4 s.
Rejected: Colima (free, terminal only, extra Terraform setting); skipping Docker (no running evidence, and the
Terraform Docker provider needs a running engine even for plan).

### Step 8-9: Terraform (v1.17.2, provider kreuzwerker/docker v3.9.0)
Provider choice: Docker provider (describes the image, volume and container on the local Docker engine).
Rejected: AWS provider with fake credentials (more concepts: networks, IAM, instance types; can't be run to check).
Structure: infra/providers.tf, variables.tf, main.tf, outputs.tf, terraform.tfvars.example and a small module
infra/modules/app/ (main.tf, variables.tf, outputs.tf, versions.tf) = everything one copy of the API needs.
Resources: docker_image (built from the project Dockerfile, rebuilt when Dockerfile/requirements/code change,
using a hash of the files as a trigger), docker_volume (data: Qdrant, cache, reports), docker_container (port,
memory limit, restart unless-stopped, keys as env, volume at /app/data, healthcheck on /health).
Variables: docker_socket, app_name, api_port (validated 1024-65535), memory_mb, groq_api_key and
openrouter_api_key (sensitive). Outputs: api_url, docs_url, container_name, data_volume.
Secrets: real values in infra/terraform.tfvars (git-ignored, like .env); state files and saved plans git-ignored
(they can hold secrets); .terraform.lock.hcl committed (pins the provider version for the team).
Results (saved in infra/results/):
- terraform fmt -recursive -check: exit 0 (all files formatted)
- terraform init: installed kreuzwerker/docker v3.9.0, lock file created
- terraform validate: "Success! The configuration is valid."
- terraform plan (placeholder key): "Plan: 3 to add, 0 to change, 0 to destroy"; env shown as (sensitive value);
  the placeholder key appears 0 times in the saved output; outputs api_url http://localhost:8000, docs_url,
  container_name docs-chat-api, data_volume docs-chat-api-data
- Variables: -var api_port=9000 -var app_name=docs-chat-api-test -> every name, the port and api_url change
- Validation: -var api_port=80 -> "api_port must be between 1024 and 65535."
terraform apply was not run (not required; nothing is created).

### Known limitation
/ask-voice takes only the audio (no chat history yet), so voice follow-ups like "how do I fix it?"
are treated as new questions.

## Challenges
- Qdrant local mode lock: the API failed to open data/qdrant while the Streamlit app was running.
- /docs test returned 422 "json_invalid": the request box had two JSON objects and a trailing comma.
  The error points to the exact character (loc ["body", 42]); FastAPI rejects it before our code runs.
- logger.exception() inside the global exception handler logged "NoneType: None" (no traceback), because it
  only finds the error inside an except block. Fixed with logger.error(..., exc_info=error).
- brew install --cask docker-desktop stopped at a sudo step (needs the Mac password in a real terminal);
  Homebrew rolled back cleanly and kept the download, so the second run (by me in the terminal) was quick.
- Homebrew could not install Terraform (outdated macOS Command Line Tools). Installed the official
  darwin_arm64 binary from releases.hashicorp.com into ~/.local/bin after checking its SHA256 checksum.
- Docker Desktop's socket is ~/.docker/run/docker.sock, not /var/run/docker.sock -> made it a variable.
- terraform init failed: "registry.terraform.io does not have a provider named hashicorp/docker". The module
  didn't declare its provider source, so Terraform guessed hashicorp/docker. Fixed with
  modules/app/versions.tf (source = kreuzwerker/docker).
- Since the API opens Qdrant at startup, the two Week 7 tests that use the real data/qdrant fail while the
  server runs (lock). They pass with the server stopped; the API tests use a temporary database.
