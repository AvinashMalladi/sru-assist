"""Master Executive Pitch Deck Generator for AURA.
Completely eliminates the 'empty giant box' look by utilizing rich, structured layouts:
- Slide 1: Executive Title, Subtitle, Institutional Pill, 3 Full-Height Stat/Pillar Cards, Presenter Footer
- Slide 2: High-Density 6-Row Comparison Matrix (Table Layout with colored headers, full vertical fill, 0 wasted space)
- Slide 3: 4-Step Pipeline Flow (Top) + 2 Structured Technical Cards (Bottom, filled with lead-ins and descriptions)
- Slide 4: 3 Balanced, Rich Vertical Columns (Architecture, Lifecycle, Governance - full height, zero bottom voids)
- Slide 5: 2x2 Structured Grid (4 balanced cards: Perimeter Defense, Numerical Fences, Portal Embed, Failover Cascade)
- Slide 6: 4-Member Architecture Division (Left) + 5-Point Phase 2 Production Roadmap (Right) - fully populated
"""

import pptx
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.enum.shapes import MSO_SHAPE

def build_perfect_presentation(output_path="AURA_Executive_Presentation.pptx"):
    prs = pptx.Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    blank_layout = prs.slide_layouts[6]

    # Executive Color Palette
    C_BG = RGBColor(10, 16, 32)           # Deep Obsidian Slate (#0A1020)
    C_CARD_BG = RGBColor(17, 26, 49)      # Midnight Card Navy (#111A31)
    C_CARD_ALT = RGBColor(22, 33, 62)     # Slightly elevated slate navy
    C_CARD_BORDER = RGBColor(34, 52, 94)  # Elegant Card Border (#22345E)
    C_HEADER_BAR = RGBColor(23, 38, 77)   # Category Pill Navy (#17264D)

    # Accent Colors
    C_AMBER = RGBColor(245, 158, 11)      # Gold Accent (#F59E0B)
    C_BLUE = RGBColor(56, 189, 248)       # Sky/Tech Blue (#38BDF8)
    C_GREEN = RGBColor(16, 185, 129)      # Emerald (#10B981)
    C_ROSE = RGBColor(244, 63, 94)        # Crimson / Alert (#F43F5E)
    C_PURPLE = RGBColor(168, 85, 247)     # Violet Accent (#A855F7)

    # Typography Colors
    C_WHITE = RGBColor(255, 255, 255)
    C_TEXT_LIGHT = RGBColor(235, 240, 250)
    C_TEXT_MUTED = RGBColor(156, 175, 205)

    FONT = "Calibri"

    def set_bg(slide):
        bg = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, Inches(13.333), Inches(7.5))
        bg.fill.solid()
        bg.fill.fore_color.rgb = C_BG
        bg.line.fill.background()
        return bg

    def add_header(slide, pill_text, title_text, subtitle_text, accent_color=C_BLUE):
        # Pill
        pw = Inches(max(2.5, len(pill_text) * 0.105 + 0.45))
        pill = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(0.40), pw, Inches(0.28))
        pill.fill.solid()
        pill.fill.fore_color.rgb = C_HEADER_BAR
        pill.line.color.rgb = accent_color
        pill.line.width = Pt(1.2)
        ptf = pill.text_frame
        ptf.margin_left = ptf.margin_top = ptf.margin_right = ptf.margin_bottom = 0
        pp = ptf.paragraphs[0]
        pp.text = pill_text.upper()
        pp.font.name = FONT
        pp.font.size = Pt(9.5)
        pp.font.bold = True
        pp.font.color.rgb = accent_color
        pp.alignment = PP_ALIGN.CENTER

        # Title & Subtitle single box
        tb = slide.shapes.add_textbox(Inches(0.8), Inches(0.75), Inches(11.733), Inches(0.90))
        tf = tb.text_frame
        tf.word_wrap = True
        tf.margin_left = tf.margin_top = tf.margin_right = tf.margin_bottom = 0

        p0 = tf.paragraphs[0]
        p0.text = title_text
        p0.font.name = FONT
        p0.font.size = Pt(22)
        p0.font.bold = True
        p0.font.color.rgb = C_WHITE
        p0.space_after = Pt(2)

        p1 = tf.add_paragraph()
        p1.text = subtitle_text
        p1.font.name = FONT
        p1.font.size = Pt(11.5)
        p1.font.color.rgb = C_TEXT_MUTED

    def add_filled_card(slide, left, top, width, height, accent_color=None):
        card = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height)
        card.fill.solid()
        card.fill.fore_color.rgb = C_CARD_BG
        card.line.color.rgb = C_CARD_BORDER
        card.line.width = Pt(1.2)

        if accent_color:
            strip = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left + Inches(0.04), top + Inches(0.02), width - Inches(0.08), Inches(0.05))
            strip.fill.solid()
            strip.fill.fore_color.rgb = accent_color
            strip.line.fill.background()

        return card

    # =========================================================================
    # SLIDE 1: HERO & EXECUTIVE OVERVIEW
    # =========================================================================
    s1 = prs.slides.add_slide(blank_layout)
    set_bg(s1)

    # University Pill
    u_pill = s1.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(0.60), Inches(4.5), Inches(0.32))
    u_pill.fill.solid()
    u_pill.fill.fore_color.rgb = C_HEADER_BAR
    u_pill.line.color.rgb = C_AMBER
    u_pill.line.width = Pt(1.2)
    utf = u_pill.text_frame
    utf.margin_left = utf.margin_top = utf.margin_right = utf.margin_bottom = 0
    up = utf.paragraphs[0]
    up.text = "SR UNIVERSITY · B.TECH SENIOR DESIGN 2026"
    up.font.name = FONT
    up.font.size = Pt(9.5)
    up.font.bold = True
    up.font.color.rgb = C_AMBER
    up.alignment = PP_ALIGN.CENTER

    # Hero Title Box
    h_box = s1.shapes.add_textbox(Inches(0.8), Inches(1.05), Inches(11.733), Inches(1.85))
    htf = h_box.text_frame
    htf.word_wrap = True
    htf.margin_left = htf.margin_top = htf.margin_right = htf.margin_bottom = 0

    hp1 = htf.paragraphs[0]
    hp1.text = "AURA: Autonomous University RAG Agent"
    hp1.font.name = FONT
    hp1.font.size = Pt(32)
    hp1.font.bold = True
    hp1.font.color.rgb = C_WHITE
    hp1.space_after = Pt(4)

    hp2 = htf.add_paragraph()
    hp2.text = "Citation-Grounded Academic Regulation Intelligence & Multi-Cohort Governance"
    hp2.font.name = FONT
    hp2.font.size = Pt(14.5)
    hp2.font.color.rgb = C_BLUE
    hp2.space_after = Pt(6)

    hp3 = htf.add_paragraph()
    hp3.text = "An embeddable enterprise AI advisory layer engineered for official university portals, eliminating hallucination risks through strict handbook grounding, automated regulation routing, and persistent session memory."
    hp3.font.name = FONT
    hp3.font.size = Pt(11)
    hp3.font.color.rgb = C_TEXT_MUTED

    # 3 High-Density Pillars
    c_w = Inches(3.72)
    c_h = Inches(3.60)
    c_top = Inches(3.05)

    s1_data = [
        (Inches(0.8), "PILLAR 01 · TRUST & AUDITABILITY", "100% Policy Grounding", C_AMBER, [
            ("Strict Page Citations", "Every single response explicitly cites approved handbook pages (e.g., Handbook 2026-27 p. 34)."),
            ("Zero Hallucination Policy", "Eliminates fabricated passing thresholds and false promotion promises that create legal liability."),
            ("Institutional Scope Defense", "Courteously intercepts and rejects out-of-scope tasks, programming assignments, and exam tampering."),
            ("Verified Contact Escalation", "Unlisted campus queries automatically route to verified Chief Warden and Dean Student Welfare contacts.")
        ]),
        (Inches(4.8), "PILLAR 02 · REGULATION ROUTING", "Automated Cohort Disambiguation", C_BLUE, [
            ("10-Digit Roll Parsing", "Algorithmically decodes admission year, school, degree, and program from enrollment numbers (e.g. 2303A51042)."),
            ("Multi-Regulation Routing", "Resolves contradictory policies between R23 (0-backlog 3rd-year rule) and 2026-27 credit frameworks."),
            ("Targeted Advisory Chips", "Dynamically generates contextual suggestion chips based on the decoded student department."),
            ("Student Slang Translation", "Maps colloquialisms ('att', 'condo', 'dabbulu') into official academic taxonomy.")
        ]),
        (Inches(8.8), "PILLAR 03 · ENTERPRISE PERSISTENCE", "Persistent State Architecture", C_GREEN, [
            ("Relational SQLite WAL Engine", "Zero-dependency local persistence with Write-Ahead Logging for non-blocking multi-student concurrency."),
            ("Instant History Restoration", "Re-entering a roll number automatically fetches past dialogue turns and renders a visual restore divider."),
            ("Retroactive Session Binding", "Anonymous queries asked prior to identification are seamlessly bound to the student profile."),
            ("Dynamic Knowledge Ingestion", "POST /api/sync allows university staff to ingest new circulars and fee notices without restarting servers.")
        ])
    ]

    for left_pos, tag, title, col, bullets in s1_data:
        add_filled_card(s1, left_pos, c_top, c_w, c_h, accent_color=col)
        tb = s1.shapes.add_textbox(left_pos + Inches(0.22), c_top + Inches(0.18), c_w - Inches(0.44), c_h - Inches(0.28))
        tf = tb.text_frame
        tf.word_wrap = True
        tf.margin_left = tf.margin_top = tf.margin_right = tf.margin_bottom = 0

        p_tag = tf.paragraphs[0]
        p_tag.text = tag
        p_tag.font.name = FONT
        p_tag.font.size = Pt(8.5)
        p_tag.font.bold = True
        p_tag.font.color.rgb = col
        p_tag.space_after = Pt(2)

        p_title = tf.add_paragraph()
        p_title.text = title
        p_title.font.name = FONT
        p_title.font.size = Pt(13)
        p_title.font.bold = True
        p_title.font.color.rgb = C_WHITE
        p_title.space_after = Pt(8)

        for lead, body in bullets:
            pb = tf.add_paragraph()
            pb.space_after = Pt(5)

            r1 = pb.add_run()
            r1.text = f"• {lead}: "
            r1.font.name = FONT
            r1.font.size = Pt(9.5)
            r1.font.bold = True
            r1.font.color.rgb = C_WHITE

            r2 = pb.add_run()
            r2.text = body
            r2.font.name = FONT
            r2.font.size = Pt(9)
            r2.font.color.rgb = C_TEXT_LIGHT

    # Presenter Ribbon at Bottom
    team_bar = s1.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.8), Inches(6.80), Inches(11.733), Inches(0.38))
    team_bar.fill.solid()
    team_bar.fill.fore_color.rgb = C_HEADER_BAR
    team_bar.line.color.rgb = C_CARD_BORDER
    team_bar.line.width = Pt(1.0)
    tbf = team_bar.text_frame
    tbf.margin_left = tbf.margin_top = tbf.margin_right = tbf.margin_bottom = 0
    tp = tbf.paragraphs[0]
    tp.text = "ENGINEERING TEAM:  Avinash Malladi (Lead Architect)  •  Team Member 2 (Hybrid RAG)  •  Team Member 3 (Backend & DB)  •  Team Member 4 (Frontend & QA)"
    tp.font.name = FONT
    tp.font.size = Pt(9.5)
    tp.font.bold = True
    tp.font.color.rgb = C_TEXT_MUTED
    tp.alignment = PP_ALIGN.CENTER

    # =========================================================================
    # SLIDE 2: THE INSTITUTIONAL RISK - COMPARISON MATRIX TABLE (NO EMPTY SPACE!)
    # =========================================================================
    s2 = prs.slides.add_slide(blank_layout)
    set_bg(s2)
    add_header(s2, "01 · Problem Statement & Need", 
               "Why Generic LLMs Fail in University Governance", 
               "Public commercial chatbots create severe academic and legal liability; AURA delivers verifiable institutional trust.",
               accent_color=C_ROSE)

    # 6-Row Evaluation Matrix Table (Full width and height, beautifully styled)
    table_shape = s2.shapes.add_table(6, 3, Inches(0.8), Inches(1.80), Inches(11.733), Inches(5.15))
    tbl = table_shape.table
    tbl.columns[0].width = Inches(2.40)  # Dimension
    tbl.columns[1].width = Inches(4.66)  # Public LLMs
    tbl.columns[2].width = Inches(4.67)  # AURA Architecture

    matrix_rows = [
        ("Evaluation Dimension", "Public Commercial LLMs (ChatGPT / Claude)", "AURA Institutional Architecture"),
        ("Policy Grounding", 
         "Fabricates passing marks and cutoff criteria; tells failing students they are eligible, creating severe institutional and legal exposure.", 
         "100% citation-grounded; every statement is strictly linked to approved handbook page references (e.g. Handbook 2026-27 p. 34)."),
        ("Cohort Disambiguation", 
         "Conflates contradictory regulations across batches; confuses B.Tech R23 policies with 2026-27 credit circulars.", 
         "Algorithmic 10-digit enrollment parser routes queries to the student's exact regulation cohort before retrieval."),
        ("Numerical Precision", 
         "Semantic vector distance blurs critical thresholds; cannot reliably separate 64.9% (detention) from 65.0% (medical condonation).", 
         "Lexical BM25 locks hard numerical cutoffs (45% aggregate pass marks, 64.9% non-condonable detention, 0-backlog rules)."),
        ("Edge-Case Escalation", 
         "Hallucinates unlisted rules (e.g. campus pet policies) or produces generic unhelpful disclaimers.", 
         "Graceful escalation protocol connects students directly to verified Dean Student Welfare & Chief Warden contacts."),
        ("Session State Memory", 
         "Stateless amnesia; loses student cohort and conversation context on page refresh, requiring repetitive explanations.", 
         "Persistent SQLite WAL engine reloads previous dialogue turns, visual restore dividers, and tailored suggestion chips.")
    ]

    for r_idx, (col0, col1, col2) in enumerate(matrix_rows):
        is_header = (r_idx == 0)
        row_cells = [tbl.cell(r_idx, 0), tbl.cell(r_idx, 1), tbl.cell(r_idx, 2)]
        texts = [col0, col1, col2]

        for c_idx, cell in enumerate(row_cells):
            cell.fill.solid()
            if is_header:
                cell.fill.fore_color.rgb = C_HEADER_BAR if c_idx == 0 else (RGBColor(60, 20, 30) if c_idx == 1 else RGBColor(15, 50, 35))
            else:
                cell.fill.fore_color.rgb = C_CARD_BG if (r_idx % 2 == 1) else C_CARD_ALT

            cell.margin_left = Inches(0.18)
            cell.margin_right = Inches(0.18)
            cell.margin_top = Inches(0.12)
            cell.margin_bottom = Inches(0.12)

            cp = cell.text_frame.paragraphs[0]
            cp.text = texts[c_idx]
            cp.font.name = FONT

            if is_header:
                cp.font.size = Pt(11)
                cp.font.bold = True
                cp.font.color.rgb = C_WHITE if c_idx == 0 else (C_ROSE if c_idx == 1 else C_GREEN)
            else:
                if c_idx == 0:
                    cp.font.size = Pt(10.5)
                    cp.font.bold = True
                    cp.font.color.rgb = C_AMBER
                elif c_idx == 1:
                    cp.font.size = Pt(9.5)
                    cp.font.color.rgb = RGBColor(250, 190, 195)
                else:
                    cp.font.size = Pt(9.5)
                    cp.font.color.rgb = C_TEXT_LIGHT

    # =========================================================================
    # SLIDE 3: SYSTEM TOPOLOGY & HYBRID RETRIEVAL PIPELINE
    # =========================================================================
    s3 = prs.slides.add_slide(blank_layout)
    set_bg(s3)
    add_header(s3, "02 · System Architecture & Retrieval", 
               "Guarded Hybrid RAG & Regulation Disambiguation", 
               "Dual-branch retrieval pipeline combining exact lexical precision with semantic intent understanding.",
               accent_color=C_BLUE)

    # 4-Stage Horizontal Pipeline
    steps = [
        ("STAGE 01", "Student Input", "Query + Roll Number\nSlang & Typo Normalizer"),
        ("STAGE 02", "Cohort Routing", "10-Digit Roll Decoder\nR23 vs 2026-27 Knowledge"),
        ("STAGE 03", "Hybrid Search", "Lexical BM25 + Semantic\nReciprocal Rank Fusion"),
        ("STAGE 04", "Guarded Synthesis", "Single-Pass Auto Injection\nStrict Page Citation Lock")
    ]

    st_w = Inches(2.70)
    st_h = Inches(1.25)
    st_top = Inches(1.80)

    for i, (tag, title, desc) in enumerate(steps):
        sx = Inches(0.8 + i * 3.01)
        scard = s3.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, sx, st_top, st_w, st_h)
        scard.fill.solid()
        scard.fill.fore_color.rgb = C_CARD_BG
        scard.line.color.rgb = C_BLUE if i == 2 else C_CARD_BORDER
        scard.line.width = Pt(1.2)

        stb = s3.shapes.add_textbox(sx + Inches(0.12), st_top + Inches(0.10), st_w - Inches(0.24), st_h - Inches(0.20))
        stf = stb.text_frame
        stf.word_wrap = True
        stf.margin_left = stf.margin_top = stf.margin_right = stf.margin_bottom = 0

        sp0 = stf.paragraphs[0]
        sp0.text = tag
        sp0.font.name = FONT
        sp0.font.size = Pt(8.5)
        sp0.font.bold = True
        sp0.font.color.rgb = C_AMBER
        sp0.alignment = PP_ALIGN.CENTER
        sp0.space_after = Pt(1)

        sp1 = stf.add_paragraph()
        sp1.text = title
        sp1.font.name = FONT
        sp1.font.size = Pt(11.5)
        sp1.font.bold = True
        sp1.font.color.rgb = C_WHITE
        sp1.alignment = PP_ALIGN.CENTER
        sp1.space_after = Pt(2)

        sp2 = stf.add_paragraph()
        sp2.text = desc
        sp2.font.name = FONT
        sp2.font.size = Pt(8.5)
        sp2.font.color.rgb = C_TEXT_MUTED
        sp2.alignment = PP_ALIGN.CENTER

    # Lower Deep Dive Cards: Branch 1 vs Branch 2 (Extended to 3.70" height to fill vertically)
    bot_w = Inches(5.72)
    bot_h = Inches(3.70)
    bot_top = Inches(3.25)

    # Branch 1
    add_filled_card(s3, Inches(0.8), bot_top, bot_w, bot_h, accent_color=C_BLUE)
    tb_b1 = s3.shapes.add_textbox(Inches(1.05), bot_top + Inches(0.18), bot_w - Inches(0.50), bot_h - Inches(0.30))
    tf_b1 = tb_b1.text_frame
    tf_b1.word_wrap = True
    tf_b1.margin_left = tf_b1.margin_top = tf_b1.margin_right = tf_b1.margin_bottom = 0

    p_b1t = tf_b1.paragraphs[0]
    p_b1t.text = "BRANCH 1 · HARD NUMERICAL PRECISION"
    p_b1t.font.name = FONT
    p_b1t.font.size = Pt(8.5)
    p_b1t.font.bold = True
    p_b1t.font.color.rgb = C_BLUE
    p_b1t.space_after = Pt(2)

    p_b1h = tf_b1.add_paragraph()
    p_b1h.text = "Lexical BM25 & Exact Phrase Reranker"
    p_b1h.font.name = FONT
    p_b1h.font.size = Pt(13.5)
    p_b1h.font.bold = True
    p_b1h.font.color.rgb = C_WHITE
    p_b1h.space_after = Pt(8)

    b1_items = [
        ("Exact Numerical Thresholds", "Locks onto exact percentages and criteria (45% aggregate pass marks, 64.9% vs 65.0% attendance cutoffs, 0-backlog rules)."),
        ("Slang & Typo Normalizer", "Pre-processing maps student colloquialisms ('att', 'condo', 'dabbulu', 'chits') into formal academic vocabulary."),
        ("Zero Vector Distortion", "Guarantees that strict numerical regulations are never distorted by approximate vector cosine proximity."),
        ("Deterministic Reranking", "Boosts exact phrase matches from regulatory tables to guarantee 100% grounded context retrieval.")
    ]
    for lead, desc in b1_items:
        pb = tf_b1.add_paragraph()
        pb.space_after = Pt(5)

        r1 = pb.add_run()
        r1.text = f"• {lead}: "
        r1.font.name = FONT
        r1.font.size = Pt(10)
        r1.font.bold = True
        r1.font.color.rgb = C_WHITE

        r2 = pb.add_run()
        r2.text = desc
        r2.font.name = FONT
        r2.font.size = Pt(9.5)
        r2.font.color.rgb = C_TEXT_LIGHT

    # Branch 2
    add_filled_card(s3, Inches(6.8), bot_top, bot_w, bot_h, accent_color=C_PURPLE)
    tb_b2 = s3.shapes.add_textbox(Inches(7.05), bot_top + Inches(0.18), bot_w - Inches(0.50), bot_h - Inches(0.30))
    tf_b2 = tb_b2.text_frame
    tf_b2.word_wrap = True
    tf_b2.margin_left = tf_b2.margin_top = tf_b2.margin_right = tf_b2.margin_bottom = 0

    p_b2t = tf_b2.paragraphs[0]
    p_b2t.text = "BRANCH 2 · CONVERSATIONAL UNDERSTANDING"
    p_b2t.font.name = FONT
    p_b2t.font.size = Pt(8.5)
    p_b2t.font.bold = True
    p_b2t.font.color.rgb = C_PURPLE
    p_b2t.space_after = Pt(2)

    p_b2h = tf_b2.add_paragraph()
    p_b2h.text = "Dense Semantic Vector Matching & Fusion"
    p_b2h.font.name = FONT
    p_b2h.font.size = Pt(13.5)
    p_b2h.font.bold = True
    p_b2h.font.color.rgb = C_WHITE
    p_b2h.space_after = Pt(8)

    b2_items = [
        ("Conversational Intent", "Captures nuanced student queries, multi-part questions, and natural language paraphrasing."),
        ("Reciprocal Rank Fusion", "Merges top candidates from both BM25 and vector rankers into a deduplicated, high-precision context window."),
        ("Single-Pass Context Injection", "Injects verified context directly into the prompt to eliminate multi-round API latency and cost."),
        ("Dual-Provider Resilience", "Primary Google Gemini 3.1 Flash-Lite automatically cascades to secondary OpenRouter models upon provider downtime.")
    ]
    for lead, desc in b2_items:
        pb = tf_b2.add_paragraph()
        pb.space_after = Pt(5)

        r1 = pb.add_run()
        r1.text = f"• {lead}: "
        r1.font.name = FONT
        r1.font.size = Pt(10)
        r1.font.bold = True
        r1.font.color.rgb = C_WHITE

        r2 = pb.add_run()
        r2.text = desc
        r2.font.name = FONT
        r2.font.size = Pt(9.5)
        r2.font.color.rgb = C_TEXT_LIGHT

    # =========================================================================
    # SLIDE 4: STATE ARCHITECTURE & DATA PERSISTENCE (FULL HEIGHT CARDS)
    # =========================================================================
    s4 = prs.slides.add_slide(blank_layout)
    set_bg(s4)
    add_header(s4, "03 · State & Concurrency Architecture", 
               "Relational State Memory & Zero-Trust Privacy", 
               "Zero-dependency relational architecture using SQLite WAL mode for concurrent multi-student session memory.",
               accent_color=C_AMBER)

    s4_w = Inches(3.72)
    s4_h = Inches(5.15)
    s4_top = Inches(1.80)

    s4_pillars = [
        (Inches(0.8), "STORAGE ENGINE", "Relational SQLite WAL Engine", C_BLUE, [
            ("Zero Overhead Architecture", "Built using Python's native sqlite3 engine without requiring costly cloud database infrastructure."),
            ("Write-Ahead Logging (WAL)", "Enables concurrent reads and writes across multiple Gunicorn workers without database lockouts."),
            ("Two-Table Relational Schema", "'students' table maintains profiles and regulation cohorts; 'conversations' archives timestamped dialogue turns."),
            ("Turnkey Portability", "Compact single-file relational storage format designed for instant campus handoff and deployment."),
            ("Local Disk Isolation", "Runs entirely inside the application container without network database latency or external connection failures.")
        ]),
        (Inches(4.8), "SESSION LIFECYCLE", "Session Restoration & State", C_AMBER, [
            ("Instant History Reload", "Entering a hall ticket number automatically fetches past dialogue turns and renders a visual restore divider."),
            ("Retroactive Session Binding", "Anonymous queries submitted earlier in the session are linked to the student once their ID is entered."),
            ("Dynamic Contextual Chips", "Generates personalized suggestion chips tailored to student branch and cohort (e.g. CS & AI Assistant Dean Contact)."),
            ("Client Storage Migration", "Client-side storage seamlessly upgrades legacy cached sessions without data loss."),
            ("Turn Boundary Tracking", "Maintains dialogue turn boundaries to feed past student context cleanly into multi-round conversations.")
        ]),
        (Inches(8.8), "DATA GOVERNANCE", "Zero-Trust Privacy Governance", C_GREEN, [
            ("Zero Sensitive Storage", "The system never stores student passwords, private academic marks, or personal phone numbers."),
            ("Syntax-Only Extraction", "10-digit roll number is parsed strictly algorithmically to identify academic cohort and degree stream."),
            ("Git Data Isolation", "All conversation database files are permanently excluded from Git version control (.gitignore)."),
            ("SQL Injection Immunity", "100% of database interactions utilize parameterized SQL placeholders, preventing injection exploits."),
            ("Stateless Handoff", "Student profile information can be cleared instantly via DELETE /api/history without leaving residual data.")
        ])
    ]

    for left_pos, tag, title, col, bullets in s4_pillars:
        add_filled_card(s4, left_pos, s4_top, s4_w, s4_h, accent_color=col)
        tb = s4.shapes.add_textbox(left_pos + Inches(0.22), s4_top + Inches(0.18), s4_w - Inches(0.44), s4_h - Inches(0.30))
        tf = tb.text_frame
        tf.word_wrap = True
        tf.margin_left = tf.margin_top = tf.margin_right = tf.margin_bottom = 0

        p_tag = tf.paragraphs[0]
        p_tag.text = tag
        p_tag.font.name = FONT
        p_tag.font.size = Pt(8.5)
        p_tag.font.bold = True
        p_tag.font.color.rgb = col
        p_tag.space_after = Pt(2)

        p_title = tf.add_paragraph()
        p_title.text = title
        p_title.font.name = FONT
        p_title.font.size = Pt(13)
        p_title.font.bold = True
        p_title.font.color.rgb = C_WHITE
        p_title.space_after = Pt(8)

        for lead, body in bullets:
            pb = tf.add_paragraph()
            pb.space_after = Pt(6)

            r1 = pb.add_run()
            r1.text = f"• {lead}: "
            r1.font.name = FONT
            r1.font.size = Pt(9.5)
            r1.font.bold = True
            r1.font.color.rgb = C_WHITE

            r2 = pb.add_run()
            r2.text = body
            r2.font.name = FONT
            r2.font.size = Pt(9)
            r2.font.color.rgb = C_TEXT_LIGHT

    # =========================================================================
    # SLIDE 5: ENTERPRISE SECURITY & PORTAL INTEGRATION (4-QUADRANT GRID)
    # =========================================================================
    s5 = prs.slides.add_slide(blank_layout)
    set_bg(s5)
    add_header(s5, "04 · Production Hardening & Integration", 
               "Enterprise Governance & Security Guardrails", 
               "Robust institutional guardrails, multi-tier LLM failover, and zero-code portal embeddability.",
               accent_color=C_GREEN)

    # 4-Quadrant Grid (2x2) - Each quadrant filled with high-impact engineering specs
    q_w = Inches(5.72)
    q_h = Inches(2.45)
    q_top1 = Inches(1.80)
    q_top2 = Inches(4.45)

    quadrants = [
        # Quad 1: Top-Left (Security & Sanitization)
        (Inches(0.8), q_top1, "PERIMETER & INJECTION DEFENSE", "SQL Injection & XSS Sanitization", C_ROSE, [
            ("Parameterized SQL Queries", "100% of database interactions use parameterized placeholders (?); immune to SQL injection attacks."),
            ("Strict XSS Escaping", "All user messages and cited outputs are sanitized before DOM rendering to eliminate cross-site scripting."),
            ("Anti-Jailbreak Persona Lock", "Rigid system prompt fences reject prompt manipulation and unauthorized policy override attempts.")
        ]),
        # Quad 2: Top-Right (Portal Embed & Sync)
        (Inches(6.8), q_top1, "PORTAL INTEGRATION & SYNC", "Single-Tag Embed & Ingestion API", C_BLUE, [
            ("Single-Tag Embeddability", "Integrates into official university portals (sraap.in) via a single lightweight vanilla JS script tag."),
            ("Dynamic Sync API (POST /api/sync)", "Portal administrators push newly approved circulars or fee notices dynamically without restarting servers."),
            ("Zero Framework Dependencies", "Runs entirely in pure vanilla JavaScript and native Python standard libraries without external heavy frameworks.")
        ]),
        # Quad 3: Bottom-Left (Scope & Numerical Boundaries)
        (Inches(0.8), q_top2, "INSTITUTIONAL INTEGRITY", "Scope Fencing & Numerical Cutoffs", C_AMBER, [
            ("Institutional Scope Guard", "Courteously declines off-topic questions, homework programming requests, and exam tampering."),
            ("Hard Numerical Boundaries", "Enforces strict handbook cutoffs (64.9% attendance = non-condonable detention; 65.0% = medical condonation)."),
            ("Human Authority Escalation", "Unlisted campus queries automatically escalate to verified Chief Warden and Dean Student Welfare contacts.")
        ]),
        # Quad 4: Bottom-Right (High Availability & Failover)
        (Inches(6.8), q_top2, "SYSTEM RESILIENCE", "Multi-Tier LLM Failover & Fallback", C_GREEN, [
            ("Dual-Provider LLM Failover", "Primary Google Gemini 3.1 Flash-Lite automatically cascades to secondary OpenRouter models upon provider downtime."),
            ("Graceful Auto-RAG Fallback", "When upstream LLM APIs experience rate limits, the system extracts verified facts directly from indexed handbook chunks."),
            ("Minimal Resource Footprint", "Operates efficiently within standard container limits (<200MB RAM) without expensive vector DB costs.")
        ])
    ]

    for q_left, q_top, tag, title, col, bullets in quadrants:
        add_filled_card(s5, q_left, q_top, q_w, q_h, accent_color=col)
        tb = s5.shapes.add_textbox(q_left + Inches(0.20), q_top + Inches(0.14), q_w - Inches(0.40), q_h - Inches(0.24))
        tf = tb.text_frame
        tf.word_wrap = True
        tf.margin_left = tf.margin_top = tf.margin_right = tf.margin_bottom = 0

        p_tag = tf.paragraphs[0]
        p_tag.text = tag
        p_tag.font.name = FONT
        p_tag.font.size = Pt(8.5)
        p_tag.font.bold = True
        p_tag.font.color.rgb = col
        p_tag.space_after = Pt(2)

        p_title = tf.add_paragraph()
        p_title.text = title
        p_title.font.name = FONT
        p_title.font.size = Pt(12)
        p_title.font.bold = True
        p_title.font.color.rgb = C_WHITE
        p_title.space_after = Pt(6)

        for lead, body in bullets:
            pb = tf.add_paragraph()
            pb.space_after = Pt(4)

            r1 = pb.add_run()
            r1.text = f"• {lead}: "
            r1.font.name = FONT
            r1.font.size = Pt(9.5)
            r1.font.bold = True
            r1.font.color.rgb = C_WHITE

            r2 = pb.add_run()
            r2.text = body
            r2.font.name = FONT
            r2.font.size = Pt(9)
            r2.font.color.rgb = C_TEXT_LIGHT

    # =========================================================================
    # SLIDE 6: ENGINEERING OWNERSHIP & PRODUCTION ROADMAP (BALANCED TWO COLUMNS)
    # =========================================================================
    s6 = prs.slides.add_slide(blank_layout)
    set_bg(s6)
    add_header(s6, "05 · Ownership & Phase 2 Roadmap", 
               "Engineering Division & Phase 2 Production Roadmap", 
               "Four-member software engineering ownership alongside our campus production roadmap.",
               accent_color=C_PURPLE)

    s6_w = Inches(5.72)
    s6_h = Inches(5.15)
    s6_top = Inches(1.80)

    # Left: 4-Member Team Ownership
    add_filled_card(s6, Inches(0.8), s6_top, s6_w, s6_h, accent_color=C_AMBER)
    tb_t = s6.shapes.add_textbox(Inches(1.05), s6_top + Inches(0.18), s6_w - Inches(0.50), s6_h - Inches(0.30))
    tf_t = tb_t.text_frame
    tf_t.word_wrap = True
    tf_t.margin_left = tf_t.margin_top = tf_t.margin_right = tf_t.margin_bottom = 0

    p_tt = tf_t.paragraphs[0]
    p_tt.text = "CORE ENGINEERING ROLES"
    p_tt.font.name = FONT
    p_tt.font.size = Pt(8.5)
    p_tt.font.bold = True
    p_tt.font.color.rgb = C_AMBER
    p_tt.space_after = Pt(2)

    p_th = tf_t.add_paragraph()
    p_th.text = "4-Member Architecture Division"
    p_th.font.name = FONT
    p_th.font.size = Pt(13.5)
    p_th.font.bold = True
    p_th.font.color.rgb = C_WHITE
    p_th.space_after = Pt(8)

    team_members = [
        ("Avinash Malladi (Team Lead)", "AI Agent Architect & Orchestration Lead", "Engineered agent/core.py orchestration loop, single-pass auto-context injection, safety fences, and multi-tier LLM failover between Gemini and OpenRouter."),
        ("Team Member 2", "Hybrid RAG & Retrieval Systems Engineer", "Built agent/retriever.py dual-branch pipeline (BM25 + Dense Semantic), exact numerical phrase reranker, and student slang/typo dictionary in agent/normalize.py."),
        ("Team Member 3", "Backend Systems & Database Engineer", "Architected Flask REST API in app.py, agent/db.py SQLite WAL concurrent schema, 10-digit roll decoder (R23 vs 2026-27), and conversation history restoration endpoints."),
        ("Team Member 4", "Frontend Integration & Quality Assurance Lead", "Engineered static/widget.js embeddable widget, session history restore UI with divider, dynamic suggestion chips, and automated security verification test suites.")
    ]

    for name, role, desc in team_members:
        pb = tf_t.add_paragraph()
        pb.space_after = Pt(6)

        r1 = pb.add_run()
        r1.text = f"• {name} "
        r1.font.name = FONT
        r1.font.size = Pt(10)
        r1.font.bold = True
        r1.font.color.rgb = C_WHITE

        r2 = pb.add_run()
        r2.text = f"({role}): {desc}"
        r2.font.name = FONT
        r2.font.size = Pt(9)
        r2.font.color.rgb = C_TEXT_LIGHT

    # Right: Phase 2 Production Roadmap (What We Are Going To Do)
    add_filled_card(s6, Inches(6.8), s6_top, s6_w, s6_h, accent_color=C_GREEN)
    tb_m = s6.shapes.add_textbox(Inches(7.05), s6_top + Inches(0.18), s6_w - Inches(0.50), s6_h - Inches(0.30))
    tf_m = tb_m.text_frame
    tf_m.word_wrap = True
    tf_m.margin_left = tf_m.margin_top = tf_m.margin_right = tf_m.margin_bottom = 0

    p_mt = tf_m.paragraphs[0]
    p_mt.text = "WHAT WE ARE GOING TO DO"
    p_mt.font.name = FONT
    p_mt.font.size = Pt(8.5)
    p_mt.font.bold = True
    p_mt.font.color.rgb = C_GREEN
    p_mt.space_after = Pt(2)

    p_mh = tf_m.add_paragraph()
    p_mh.text = "Phase 2 Production Engineering Roadmap"
    p_mh.font.name = FONT
    p_mh.font.size = Pt(13.5)
    p_mh.font.bold = True
    p_mh.font.color.rgb = C_WHITE
    p_mh.space_after = Pt(8)

    roadmap_items = [
        ("Live ERP / SIS Webhooks", "Direct authenticated webhook integration with SR University's SRAAP portal to pull live attendance percentages and exam dues clearance via secure student tokens."),
        ("Proactive Academic Risk Alerts", "Autonomous alert triggers warning students when attendance drops below condonable thresholds (75% early notice, 65% critical detention risk)."),
        ("Multi-School Knowledge Graph", "Scaling knowledge indexing beyond B.Tech to encompass Postgraduate regulations (M.Tech, MBA, MCA, Ph.D.) and allied healthcare circulars."),
        ("Multilingual Vernacular Voice", "Integrating regional Telugu and Hindi speech-to-text and text-to-speech layers for accessible guidance across all student cohorts."),
        ("Institutional Telemetry Portal", "Administrative analytics dashboard tracking student confusion points, circular effectiveness, and high-frequency FAQ trends.")
    ]

    for lead, desc in roadmap_items:
        pb = tf_m.add_paragraph()
        pb.space_after = Pt(6)

        r1 = pb.add_run()
        r1.text = f"• {lead}: "
        r1.font.name = FONT
        r1.font.size = Pt(10)
        r1.font.bold = True
        r1.font.color.rgb = C_WHITE

        r2 = pb.add_run()
        r2.text = desc
        r2.font.name = FONT
        r2.font.size = Pt(9)
        r2.font.color.rgb = C_TEXT_LIGHT

    prs.save(output_path)
    print(f"Master executive deck built with 100% density at: {output_path}")

if __name__ == "__main__":
    build_perfect_presentation()

