import re

with open('scripts/test_humanized_paper.py', 'r', encoding='utf-8') as f:
    text = f.read()

# 1. Update Abstract
old_abs = '''    rt = p_abs.add_run(
        "Undergraduate students at Indian engineering institutions face genuine difficulty navigating institutional academic statutes. "
        "At SR University in Warangal, regulations governing grade replacement, promotion criteria, and attendance condonation are distributed "
        "across 660 printed pages (the 2026–27 Student Handbook alongside cohort-specific volumes R23, R24, and R25). Students typically consult "
        "informal peer networks rather than official volumes, causing policy misunderstandings and missed deadlines. While generic large language "
        "models produce plausible prose, our campus experiments confirmed that they regularly hallucinate fictional university clauses and fail to cite "
        "verifiable pages. We built and deployed AURA (Autonomous University RAG Agent) to resolve this administrative gap. Indexing 1,421 page-aligned "
        "chunks, AURA integrates a precompiled regular-expression security filter, a 60-term campus colloquialism normalizer, and an automated 10-digit "
        "student roll-number cohort router with document-partitioned BM25 scoring and exact-phrase boosting. Routine administrative queries—such as "
        "emergency contacts, credit tallies, and out-of-scope probes—are handled deterministically without model inference, reducing external API costs "
        "by ~35%. Across our 33-case re-evaluation benchmark spanning six governance domains, AURA attained a 96.04% average semantic similarity, "
        "100% citation precision, 100% factual accuracy, and a 100% zero-hallucination rate, achieving a 98.62% composite score. Local in-memory BM25 "
        "retrieval ran in 0.55 ms, while client latency on Render averaged 4.19 s. Packaged as a 12.4 KB vanilla JavaScript widget requiring zero "
        "external vector database subscriptions, AURA illustrates how universities can deliver dependable, auditable governance assistants on modest budgets."
    )'''

new_abs = '''    rt = p_abs.add_run(
        "Undergraduates at SR University in Warangal rarely read the 660 pages of statutory policy that govern their degrees. Instead, "
        "when questions arise regarding attendance condonation, supplementary examinations, or grade point calculations across the R23, R24, "
        "and R25 cohorts, students consult peer chat groups where distorted rumors circulate freely. General commercial language models fail "
        "to solve this problem: in our baseline trials, unguided models fabricated non-existent policy clauses and failed to supply verifiable "
        "handbook page citations. To address these operational hurdles, we engineered AURA (Autonomous University RAG Agent), an in-memory "
        "retrieval-augmented generation assistant deployed on the university's SRAAP portal. AURA indexes 1,421 page-aligned chunks from the "
        "Student Handbook and cohort regulations without requiring paid vector databases. An intake intelligence pipeline filters prompt injections "
        "via precompiled regular expressions, maps over 60 campus colloquialisms to official administrative terminology, and parses 10-digit "
        "student enrollment numbers to route queries to the correct cohort. Retrieval couples document-partitioned BM25 with exact-phrase scoring "
        "and dense embedding re-ranking. Deterministic triaging resolves routine administrative requests without generative model calls, trimming "
        "external API expenses by roughly 35%. Evaluated across a 33-case benchmark spanning six academic domains, AURA achieved a 96.04% semantic "
        "similarity, 100% citation precision, 100% factual policy accuracy, and a 100% zero-hallucination rate, yielding a 98.62% composite quality "
        "index. In-memory retrieval executes in 0.55 ms, while cloud response on Render averages 4.19 s. Packaged as a 12.4 KB vanilla JavaScript "
        "widget, AURA provides an auditable, low-cost framework for institutional AI governance."
    )'''

if old_abs in text:
    text = text.replace(old_abs, new_abs)
    print('Abstract replaced successfully')
else:
    print('Warning: Old abstract not found directly!')

# 2. Update Introduction opening
text = text.replace(
    'STATUTORY academic regulations at technical universities are notoriously fragmented across multiple volumes.',
    'STATUTORY academic regulations at technical universities remain scattered across multiple administrative volumes.'
)

# 3. Update 'Furthermore, standard commercial'
text = text.replace(
    "clause or misquoting a passing grade mark can derail an undergraduate's degree progress. Furthermore, standard commercial APIs omit",
    "clause or misquoting a passing grade mark can derail an undergraduate's degree progress. In addition, standard commercial APIs omit"
)

# 4. Update Subsection III.E to fill Page 2 Col 2
old_iiie = '''    # Subsection III.E calibrated to end cleanly at bottom of Page 2 Col 2!
    add_subsec_heading("E. Page-Aware Document Processing and Chunking")
    add_p(
        "To guarantee dependable citations, our offline pipeline parses text along physical PDF page breaks rather than arbitrary character "
        "intervals. Across the Student Handbook and the R23, R24, and R25 regulations, the parser created 1,421 page-aligned chunks from 660 source "
        "pages, preserving metadata tags and Markdown tables intact.",
        space_aft=1
    )'''

new_iiie = '''    # Subsection III.E calibrated to end cleanly at bottom of Page 2 Col 2!
    add_subsec_heading("E. Page-Aware Document Processing and Chunking")
    add_p(
        "To guarantee dependable citations, our offline pipeline parses text along physical PDF page breaks rather than arbitrary character "
        "intervals. Across the Student Handbook and the R23, R24, and R25 regulations, the parser created 1,421 page-aligned chunks from 660 source "
        "pages. Complex tabular layouts—such as letter grade cutoffs, credit allocation matrix schedules, and fee refund timelines—were systematically "
        "converted into structured Markdown tables rather than raw flattened strings. By maintaining exact page-to-chunk bijection and embedding canonical "
        "section headers within each entry, AURA ensures that every retrieved context snippet maps directly to an inspectable physical printed page.",
        space_aft=1
    )'''

if old_iiie in text:
    text = text.replace(old_iiie, new_iiie)
    print('Subsection III.E replaced successfully')
else:
    print('Warning: Subsection III.E not matched directly')

# 5. Update 'Furthermore, storing precomputed'
text = text.replace(
    'Furthermore, storing precomputed 256-dimensional embeddings in lightweight binary flat files eliminates runtime embedding generation latency.',
    'By storing precomputed 256-dimensional embeddings in lightweight binary flat files, the system avoids runtime vector calculation overhead.'
)

with open('scripts/test_humanized_paper.py', 'w', encoding='utf-8') as f:
    f.write(text)
print('Updated scripts/test_humanized_paper.py successfully!')
