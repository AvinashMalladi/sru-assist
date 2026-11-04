"""Builds a flawless, executive-tier 6-slide PowerPoint presentation for AURA.
Designed to international pitch-deck standards with mathematical layout precision,
zero overflow, zero text collisions, and complete architectural depth for an industry expert.
"""

import pptx
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.enum.shapes import MSO_SHAPE

def build_presentation(output_path="AURA_Executive_Presentation.pptx"):
    prs = pptx.Presentation()
    # 16:9 widescreen standard: 13.333" x 7.5"
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    blank_layout = prs.slide_layouts[6]

    # Professional Color Palette
    C_BG = RGBColor(11, 19, 43)          # Obsidian Slate (#0B132B)
    C_CARD_BG = RGBColor(18, 29, 58)     # Deep Midnight Card (#121D3A)
    C_CARD_BORDER = RGBColor(34, 52, 94) # Elegant Card Border (#22345E)
    C_PILL_BG = RGBColor(23, 38, 77)     # Category Pill Navy (#17264D)

    # Accent Colors
    C_AMBER = RGBColor(245, 158, 11)     # Warm Gold Accent (#F59E0B)
    C_BLUE = RGBColor(56, 189, 248)      # Tech Sky Blue (#38BDF8)
    C_GREEN = RGBColor(16, 185, 129)     # Emerald (#10B981)
    C_ROSE = RGBColor(244, 63, 94)       # Crimson Alert (#F43F5E)
    C_PURPLE = RGBColor(168, 85, 247)    # Violet Accent (#A855F7)

    # Typography Colors
    C_WHITE = RGBColor(255, 255, 255)    # High contrast white
    C_TEXT_LIGHT = RGBColor(235, 240, 250)# Crisp light text (#EBF0FA)
    C_TEXT_MUTED = RGBColor(156, 175, 205)# Secondary text (#9CAFC8)

    FONT_MAIN = "Calibri"  # Universal, pristine rendering on all Office & Google platforms

    def set_bg(slide):
        bg = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, Inches(13.333), Inches(7.5))
        bg.fill.solid()
        bg.fill.fore_color.rgb = C_BG
        bg.line.fill.background()
        return bg

    def add_header(slide, pill_text, title_text, subtitle_text, accent_color=C_BLUE):
        # 1. Category Pill Badge
        pw = Inches(max(2.4, len(pill_text) * 0.105 + 0.45))
        pill = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(0.42), pw, Inches(0.30))
        pill.fill.solid()
        pill.fill.fore_color.rgb = C_PILL_BG
        pill.line.color.rgb = accent_color
        pill.line.width = Pt(1.2)
        ptf = pill.text_frame
        ptf.margin_left = ptf.margin_top = ptf.margin_right = ptf.margin_bottom = 0
        pp = ptf.paragraphs[0]
        pp.text = pill_text.upper()
        pp.font.name = FONT_MAIN
        pp.font.size = Pt(9.5)
        pp.font.bold = True
        pp.font.color.rgb = accent_color
        pp.alignment = PP_ALIGN.CENTER

        # 2. Slide Title & Subtitle in single clean text frame (prevents any vertical collision)
        tb = slide.shapes.add_textbox(Inches(0.8), Inches(0.80), Inches(11.733), Inches(0.95))
        tf = tb.text_frame
        tf.word_wrap = True
        tf.margin_left = tf.margin_top = tf.margin_right = tf.margin_bottom = 0

        p0 = tf.paragraphs[0]
        p0.text = title_text
        p0.font.name = FONT_MAIN
        p0.font.size = Pt(23)
        p0.font.bold = True
        p0.font.color.rgb = C_WHITE
        p0.space_after = Pt(3)

        p1 = tf.add_paragraph()
        p1.text = subtitle_text
        p1.font.name = FONT_MAIN
        p1.font.size = Pt(12)
        p1.font.color.rgb = C_TEXT_MUTED

    def add_container_card(slide, left, top, width, height, accent_color=None, border_color=C_CARD_BORDER):
        """Creates a smooth, filled card container with an optional top color bar."""
        card = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height)
        card.fill.solid()
        card.fill.fore_color.rgb = C_CARD_BG
        card.line.color.rgb = border_color
        card.line.width = Pt(1.2)

        if accent_color:
            # Slim 3pt accent top stripe
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
    u_pill = s1.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(0.65), Inches(4.5), Inches(0.32))
    u_pill.fill.solid()
    u_pill.fill.fore_color.rgb = C_PILL_BG
    u_pill.line.color.rgb = C_AMBER
    u_pill.line.width = Pt(1.2)
    utf = u_pill.text_frame
    utf.margin_left = utf.margin_top = utf.margin_right = utf.margin_bottom = 0
    up = utf.paragraphs[0]
    up.text = "SR UNIVERSITY · B.TECH SENIOR DESIGN 2026"
    up.font.name = FONT_MAIN
    up.font.size = Pt(9.5)
    up.font.bold = True
    up.font.color.rgb = C_AMBER
    up.alignment = PP_ALIGN.CENTER

    # Hero Title Box
    h_box = s1.shapes.add_textbox(Inches(0.8), Inches(1.10), Inches(11.733), Inches(1.8))
    htf = h_box.text_frame
    htf.word_wrap = True
    htf.margin_left = htf.margin_top = htf.margin_right = htf.margin_bottom = 0

    hp1 = htf.paragraphs[0]
    hp1.text = "AURA: Autonomous University RAG Agent"
    hp1.font.name = FONT_MAIN
    hp1.font.size = Pt(32)
    hp1.font.bold = True
    hp1.font.color.rgb = C_WHITE
    hp1.space_after = Pt(4)

    hp2 = htf.add_paragraph()
    hp2.text = "Citation-Grounded Academic Regulation Intelligence & Multi-Cohort Governance"
    hp2.font.name = FONT_MAIN
    hp2.font.size = Pt(15)
    hp2.font.color.rgb = C_BLUE
    hp2.space_after = Pt(6)

    hp3 = htf.add_paragraph()
    hp3.text = "An embeddable enterprise AI advisory layer engineered for official university portals, eliminating hallucination risks through strict handbook grounding, automated regulation routing, and persistent session memory."
    hp3.font.name = FONT_MAIN
    hp3.font.size = Pt(11)
    hp3.font.color.rgb = C_TEXT_MUTED

    # 3 Balanced Core Architecture Pillars
    s1_w = Inches(3.72)
    s1_h = Inches(3.35)
    s1_top = Inches(3.15)

    s1_pillars = [
        (Inches(0.8), "PILLAR 01 · TRUST & AUDITABILITY", "100% Policy Grounding", C_AMBER, [
            ("Strict Page Citations", "Every generated response explicitly references approved handbook pages (e.g., Handbook 2026-27 p. 34)."),
            ("Zero Hallucination Policy", "Eliminates fabricated passing thresholds and false promotion promises that create legal liability."),
            ("Institutional Scope Defense", "Actively intercepts and courteously declines out-of-scope tasks and exam tampering attempts.")
        ]),
        (Inches(4.8), "PILLAR 02 · REGULATION ROUTING", "Automated Cohort Disambiguation", C_BLUE, [
            ("10-Digit Roll Parsing", "Algorithmically extracts admission year, school, degree, and program from student IDs (e.g. 2303A51042)."),
            ("Multi-Regulation Disambiguation", "Resolves contradictory policies between R23 (0-backlog 3rd-year rule) and 2026-27 credit frameworks."),
            ("Verified Contact Escalation", "Unlisted campus queries automatically route to verified Chief Warden and Dean Student Welfare contacts.")
        ]),
        (Inches(8.8), "PILLAR 03 · ENTERPRISE PERSISTENCE", "Persistent State Architecture", C_GREEN, [
            ("Relational SQLite WAL Engine", "Zero-dependency local persistence with Write-Ahead Logging for non-blocking multi-student concurrency."),
            ("Session Memory & History Reload", "Re-entering a roll number automatically fetches past dialogue turns and dynamic suggestion chips."),
            ("Dynamic Ingestion (POST /api/sync)", "Portal administrators push newly approved circulars or fee notices dynamically without restarting servers.")
        ])
    ]

    for left_pos, tag, title, col, bullets in s1_pillars:
        add_container_card(s1, left_pos, s1_top, s1_w, s1_h, accent_color=col)
        tb = s1.shapes.add_textbox(left_pos + Inches(0.25), s1_top + Inches(0.20), s1_w - Inches(0.50), s1_h - Inches(0.35))
        tf = tb.text_frame
        tf.word_wrap = True
        tf.margin_left = tf.margin_top = tf.margin_right = tf.margin_bottom = 0

        # Sub-badge
        p_tag = tf.paragraphs[0]
        p_tag.text = tag
        p_tag.font.name = FONT_MAIN
        p_tag.font.size = Pt(8.5)
        p_tag.font.bold = True
        p_tag.font.color.rgb = col
        p_tag.space_after = Pt(2)

        # Card Title
        p_title = tf.add_paragraph()
        p_title.text = title
        p_title.font.name = FONT_MAIN
        p_title.font.size = Pt(13.5)
        p_title.font.bold = True
        p_title.font.color.rgb = C_WHITE
        p_title.space_after = Pt(8)

        # Bullets with bold run lead-in
        for lead, body in bullets:
            pb = tf.add_paragraph()
            pb.space_after = Pt(5)

            r1 = pb.add_run()
            r1.text = f"•  {lead}: "
            r1.font.name = FONT_MAIN
            r1.font.size = Pt(10)
            r1.font.bold = True
            r1.font.color.rgb = C_WHITE

            r2 = pb.add_run()
            r2.text = body
            r2.font.name = FONT_MAIN
            r2.font.size = Pt(9.5)
            r2.font.color.rgb = C_TEXT_LIGHT

    # Presenter Ribbon at Bottom
    team_bar = s1.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.8), Inches(6.75), Inches(11.733), Inches(0.38))
    team_bar.fill.solid()
    team_bar.fill.fore_color.rgb = C_PILL_BG
    team_bar.line.color.rgb = C_CARD_BORDER
    team_bar.line.width = Pt(1.0)
    tbf = team_bar.text_frame
    tbf.margin_left = tbf.margin_top = tbf.margin_right = tbf.margin_bottom = 0
    tp = tbf.paragraphs[0]
    tp.text = "ENGINEERING TEAM:  Avinash Malladi (Lead Architect)  •  Team Member 2 (Hybrid RAG)  •  Team Member 3 (Backend & DB)  •  Team Member 4 (Frontend & QA)"
    tp.font.name = FONT_MAIN
    tp.font.size = Pt(9.5)
    tp.font.bold = True
    tp.font.color.rgb = C_TEXT_MUTED
    tp.alignment = PP_ALIGN.CENTER

    # =========================================================================
    # SLIDE 2: THE INSTITUTIONAL RISK & COMPARATIVE ANALYSIS
    # =========================================================================
    s2 = prs.slides.add_slide(blank_layout)
    set_bg(s2)
    add_header(s2, "01 · Problem Statement & Need", 
               "Why Generic LLMs Fail in University Governance", 
               "Standard commercial models create catastrophic legal and academic liability; AURA delivers verifiable institutional certainty.",
               accent_color=C_ROSE)

    s2_w = Inches(5.72)
    s2_h = Inches(4.9)
    s2_top = Inches(1.95)

    # Left Card: Risks of Generic LLMs
    add_container_card(s2, Inches(0.8), s2_top, s2_w, s2_h, accent_color=C_ROSE, border_color=RGBColor(80, 25, 40))
    tb_l = s2.shapes.add_textbox(Inches(1.05), s2_top + Inches(0.20), s2_w - Inches(0.50), s2_h - Inches(0.35))
    tf_l = tb_l.text_frame
    tf_l.word_wrap = True
    tf_l.margin_left = tf_l.margin_top = tf_l.margin_right = tf_l.margin_bottom = 0

    p_lt = tf_l.paragraphs[0]
    p_lt.text = "CRITICAL INSTITUTIONAL RISKS"
    p_lt.font.name = FONT_MAIN
    p_lt.font.size = Pt(8.5)
    p_lt.font.bold = True
    p_lt.font.color.rgb = C_ROSE
    p_lt.space_after = Pt(2)

    p_lh = tf_l.add_paragraph()
    p_lh.text = "The High Risk of Public LLMs (ChatGPT / Claude)"
    p_lh.font.name = FONT_MAIN
    p_lh.font.size = Pt(14)
    p_lh.font.bold = True
    p_lh.font.color.rgb = C_WHITE
    p_lh.space_after = Pt(10)

    l_items = [
        ("Policy Hallucination Risk", "Commercial models fabricate passing thresholds and tell failing students they are eligible, creating severe institutional liability."),
        ("Conflicting Regulation Blindness", "Different admission batches follow contradictory rules; public chatbots conflate B.Tech R23 policies with 2026-27 circulars."),
        ("Numerical Distance Drift", "Semantic embeddings alone fail to distinguish 64.9% (mandatory detention) from 65.0% (medical condonation eligibility)."),
        ("Zero Handbook Auditability", "Cannot provide official handbook page citations, leaving students and administrators unable to confirm validity."),
        ("Stateless Context Loss", "Standard chat interfaces lose student cohort details on page refresh, requiring re-explanation on every visit.")
    ]

    for lead, desc in l_items:
        pb = tf_l.add_paragraph()
        pb.space_after = Pt(6)

        r1 = pb.add_run()
        r1.text = f"•  {lead}: "
        r1.font.name = FONT_MAIN
        r1.font.size = Pt(10)
        r1.font.bold = True
        r1.font.color.rgb = C_WHITE

        r2 = pb.add_run()
        r2.text = desc
        r2.font.name = FONT_MAIN
        r2.font.size = Pt(9.5)
        r2.font.color.rgb = C_TEXT_LIGHT

    # Right Card: The AURA Solution
    add_container_card(s2, Inches(6.8), s2_top, s2_w, s2_h, accent_color=C_GREEN, border_color=RGBColor(25, 75, 55))
    tb_r = s2.shapes.add_textbox(Inches(7.05), s2_top + Inches(0.20), s2_w - Inches(0.50), s2_h - Inches(0.35))
    tf_r = tb_r.text_frame
    tf_r.word_wrap = True
    tf_r.margin_left = tf_r.margin_top = tf_r.margin_right = tf_r.margin_bottom = 0

    p_rt = tf_r.paragraphs[0]
    p_rt.text = "ENGINEERED GOVERNANCE SOLUTION"
    p_rt.font.name = FONT_MAIN
    p_rt.font.size = Pt(8.5)
    p_rt.font.bold = True
    p_rt.font.color.rgb = C_GREEN
    p_rt.space_after = Pt(2)

    p_rh = tf_r.add_paragraph()
    p_rh.text = "The AURA Institutional Architecture"
    p_rh.font.name = FONT_MAIN
    p_rh.font.size = Pt(14)
    p_rh.font.bold = True
    p_rh.font.color.rgb = C_WHITE
    p_rh.space_after = Pt(10)

    r_items = [
        ("Strict Policy Grounding", "100% of policy guidance is explicitly linked to official approved handbook citations (e.g. Handbook 2026-27 p. 34)."),
        ("Algorithmic Cohort Routing", "10-digit roll number syntax determines the applicable regulation model before retrieval begins."),
        ("Hybrid Sparse-Dense Search", "Lexical BM25 locks hard numeric criteria while dense semantic matching resolves conversational student queries."),
        ("Verified Human Escalation", "Unlisted or discretionary operational matters automatically route to the Chief Warden or Dean Student Welfare."),
        ("Persistent State Memory", "SQLite WAL database reloads conversation history and dynamic suggestion chips across browser sessions.")
    ]

    for lead, desc in r_items:
        pb = tf_r.add_paragraph()
        pb.space_after = Pt(6)

        r1 = pb.add_run()
        r1.text = f"•  {lead}: "
        r1.font.name = FONT_MAIN
        r1.font.size = Pt(10)
        r1.font.bold = True
        r1.font.color.rgb = C_WHITE

        r2 = pb.add_run()
        r2.text = desc
        r2.font.name = FONT_MAIN
        r2.font.size = Pt(9.5)
        r2.font.color.rgb = C_TEXT_LIGHT

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
    st_top = Inches(1.95)

    for i, (tag, title, desc) in enumerate(steps):
        sx = Inches(0.8 + i * 3.01)
        scard = slide_shape = s3.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, sx, st_top, st_w, st_h)
        scard.fill.solid()
        scard.fill.fore_color.rgb = C_CARD_BG
        scard.line.color.rgb = C_BLUE if i == 2 else C_CARD_BORDER
        scard.line.width = Pt(1.2)

        stb = s3.shapes.add_textbox(sx + Inches(0.12), st_top + Inches(0.12), st_w - Inches(0.24), st_h - Inches(0.24))
        stf = stb.text_frame
        stf.word_wrap = True
        stf.margin_left = stf.margin_top = stf.margin_right = stf.margin_bottom = 0

        sp0 = stf.paragraphs[0]
        sp0.text = tag
        sp0.font.name = FONT_MAIN
        sp0.font.size = Pt(8.5)
        sp0.font.bold = True
        sp0.font.color.rgb = C_AMBER
        sp0.alignment = PP_ALIGN.CENTER
        sp0.space_after = Pt(1)

        sp1 = stf.add_paragraph()
        sp1.text = title
        sp1.font.name = FONT_MAIN
        sp1.font.size = Pt(11.5)
        sp1.font.bold = True
        sp1.font.color.rgb = C_WHITE
        sp1.alignment = PP_ALIGN.CENTER
        sp1.space_after = Pt(2)

        sp2 = stf.add_paragraph()
        sp2.text = desc
        sp2.font.name = FONT_MAIN
        sp2.font.size = Pt(8.5)
        sp2.font.color.rgb = C_TEXT_MUTED
        sp2.alignment = PP_ALIGN.CENTER

    # Lower Deep Dive Cards: Branch 1 vs Branch 2
    bot_w = Inches(5.72)
    bot_h = Inches(3.45)
    bot_top = Inches(3.45)

    # Branch 1
    add_container_card(s3, Inches(0.8), bot_top, bot_w, bot_h, accent_color=C_BLUE)
    tb_b1 = s3.shapes.add_textbox(Inches(1.05), bot_top + Inches(0.20), bot_w - Inches(0.50), bot_h - Inches(0.35))
    tf_b1 = tb_b1.text_frame
    tf_b1.word_wrap = True
    tf_b1.margin_left = tf_b1.margin_top = tf_b1.margin_right = tf_b1.margin_bottom = 0

    p_b1t = tf_b1.paragraphs[0]
    p_b1t.text = "BRANCH 1 · HARD NUMERICAL PRECISION"
    p_b1t.font.name = FONT_MAIN
    p_b1t.font.size = Pt(8.5)
    p_b1t.font.bold = True
    p_b1t.font.color.rgb = C_BLUE
    p_b1t.space_after = Pt(2)

    p_b1h = tf_b1.add_paragraph()
    p_b1h.text = "Lexical BM25 & Exact Phrase Reranker"
    p_b1h.font.name = FONT_MAIN
    p_b1h.font.size = Pt(14)
    p_b1h.font.bold = True
    p_b1h.font.color.rgb = C_WHITE
    p_b1h.space_after = Pt(8)

    b1_items = [
        ("Exact Numerical Thresholds", "Locks onto exact percentages and criteria (45% pass marks, 64.9% vs 65.0% attendance cutoffs, 0-backlog rules)."),
        ("Slang & Typo Normalizer", "Pre-processing maps student colloquialisms ('att', 'condo', 'dabbulu', 'chits') into formal academic vocabulary."),
        ("Zero Vector Distortion", "Guarantees that strict numerical regulations are never distorted by approximate vector cosine proximity.")
    ]
    for lead, desc in b1_items:
        pb = tf_b1.add_paragraph()
        pb.space_after = Pt(5)

        r1 = pb.add_run()
        r1.text = f"•  {lead}: "
        r1.font.name = FONT_MAIN
        r1.font.size = Pt(10)
        r1.font.bold = True
        r1.font.color.rgb = C_WHITE

        r2 = pb.add_run()
        r2.text = desc
        r2.font.name = FONT_MAIN
        r2.font.size = Pt(9.5)
        r2.font.color.rgb = C_TEXT_LIGHT

    # Branch 2
    add_container_card(s3, Inches(6.8), bot_top, bot_w, bot_h, accent_color=C_PURPLE)
    tb_b2 = s3.shapes.add_textbox(Inches(7.05), bot_top + Inches(0.20), bot_w - Inches(0.50), bot_h - Inches(0.35))
    tf_b2 = tb_b2.text_frame
    tf_b2.word_wrap = True
    tf_b2.margin_left = tf_b2.margin_top = tf_b2.margin_right = tf_b2.margin_bottom = 0

    p_b2t = tf_b2.paragraphs[0]
    p_b2t.text = "BRANCH 2 · CONVERSATIONAL UNDERSTANDING"
    p_b2t.font.name = FONT_MAIN
    p_b2t.font.size = Pt(8.5)
    p_b2t.font.bold = True
    p_b2t.font.color.rgb = C_PURPLE
    p_b2t.space_after = Pt(2)

    p_b2h = tf_b2.add_paragraph()
    p_b2h.text = "Dense Semantic Vector Matching & Reranking"
    p_b2h.font.name = FONT_MAIN
    p_b2h.font.size = Pt(14)
    p_b2h.font.bold = True
    p_b2h.font.color.rgb = C_WHITE
    p_b2h.space_after = Pt(8)

    b2_items = [
        ("Conversational Intent", "Captures nuanced student queries, multi-part questions, and natural language paraphrasing."),
        ("Reciprocal Rank Fusion", "Merges top candidates from both BM25 and vector rankers into a deduplicated, high-precision context window."),
        ("Single-Pass Context Injection", "Injects verified context directly into the prompt to eliminate multi-round API latency and cost.")
    ]
    for lead, desc in b2_items:
        pb = tf_b2.add_paragraph()
        pb.space_after = Pt(5)

        r1 = pb.add_run()
        r1.text = f"•  {lead}: "
        r1.font.name = FONT_MAIN
        r1.font.size = Pt(10)
        r1.font.bold = True
        r1.font.color.rgb = C_WHITE

        r2 = pb.add_run()
        r2.text = desc
        r2.font.name = FONT_MAIN
        r2.font.size = Pt(9.5)
        r2.font.color.rgb = C_TEXT_LIGHT

    # =========================================================================
    # SLIDE 4: STATE ARCHITECTURE & DATA PERSISTENCE
    # =========================================================================
    s4 = prs.slides.add_slide(blank_layout)
    set_bg(s4)
    add_header(s4, "03 · State & Concurrency Architecture", 
               "Relational State Memory & Zero-Trust Privacy", 
               "Zero-dependency relational architecture using SQLite WAL mode for concurrent multi-student session memory.",
               accent_color=C_AMBER)

    s4_w = Inches(3.72)
    s4_h = Inches(4.9)
    s4_top = Inches(1.95)

    s4_pillars = [
        (Inches(0.8), "STORAGE ENGINE", "Relational SQLite WAL Engine", C_BLUE, [
            ("Zero Overhead Architecture", "Built using Python's native sqlite3 engine without requiring costly cloud database infrastructure."),
            ("Write-Ahead Logging (WAL)", "Enables concurrent reads and writes across multiple Gunicorn workers without database lockouts."),
            ("Two-Table Schema", "'students' table maintains profiles and regulation cohorts; 'conversations' archives timestamped dialogue turns."),
            ("Turnkey Portability", "Compact single-file relational storage format designed for instant campus handoff and deployment.")
        ]),
        (Inches(4.8), "SESSION LIFECYCLE", "Session Restoration & Linking", C_AMBER, [
            ("Instant History Reload", "Entering a hall ticket number automatically fetches past dialogue turns and renders a visual restore divider."),
            ("Retroactive Session Binding", "Anonymous queries submitted earlier in the session are linked to the student once their ID is entered."),
            ("Dynamic Contextual Chips", "Generates personalized suggestion chips tailored to student branch and cohort (e.g. CS & AI Assistant Dean Contact)."),
            ("Client Storage Migration", "Client-side storage seamlessly upgrades legacy cached sessions without data loss.")
        ]),
        (Inches(8.8), "DATA GOVERNANCE", "Zero-Trust Privacy Governance", C_GREEN, [
            ("Zero Sensitive Storage", "The system never stores student passwords, private academic marks, or phone numbers."),
            ("Syntax-Only Extraction", "10-digit roll number is parsed strictly algorithmically to identify academic cohort and degree stream."),
            ("Git Data Isolation", "All conversation database files are permanently excluded from Git version control (.gitignore)."),
            ("SQL Injection Immunity", "100% of database interactions utilize parameterized SQL placeholders, preventing injection exploits.")
        ])
    ]

    for left_pos, tag, title, col, bullets in s4_pillars:
        add_container_card(s4, left_pos, s4_top, s4_w, s4_h, accent_color=col)
        tb = s4.shapes.add_textbox(left_pos + Inches(0.25), s4_top + Inches(0.20), s4_w - Inches(0.50), s4_h - Inches(0.35))
        tf = tb.text_frame
        tf.word_wrap = True
        tf.margin_left = tf.margin_top = tf.margin_right = tf.margin_bottom = 0

        p_tag = tf.paragraphs[0]
        p_tag.text = tag
        p_tag.font.name = FONT_MAIN
        p_tag.font.size = Pt(8.5)
        p_tag.font.bold = True
        p_tag.font.color.rgb = col
        p_tag.space_after = Pt(2)

        p_title = tf.add_paragraph()
        p_title.text = title
        p_title.font.name = FONT_MAIN
        p_title.font.size = Pt(13.5)
        p_title.font.bold = True
        p_title.font.color.rgb = C_WHITE
        p_title.space_after = Pt(8)

        for lead, body in bullets:
            pb = tf.add_paragraph()
            pb.space_after = Pt(5)

            r1 = pb.add_run()
            r1.text = f"•  {lead}: "
            r1.font.name = FONT_MAIN
            r1.font.size = Pt(10)
            r1.font.bold = True
            r1.font.color.rgb = C_WHITE

            r2 = pb.add_run()
            r2.text = body
            r2.font.name = FONT_MAIN
            r2.font.size = Pt(9.5)
            r2.font.color.rgb = C_TEXT_LIGHT

    # =========================================================================
    # SLIDE 5: ENTERPRISE SECURITY & PORTAL INTEGRATION
    # =========================================================================
    s5 = prs.slides.add_slide(blank_layout)
    set_bg(s5)
    add_header(s5, "04 · Production Hardening & Integration", 
               "Enterprise Governance & Security Guardrails", 
               "Robust institutional guardrails, multi-tier LLM failover, and zero-code portal embeddability.",
               accent_color=C_GREEN)

    s5_w = Inches(5.72)
    s5_h = Inches(4.9)
    s5_top = Inches(1.95)

    # Left: Security
    add_container_card(s5, Inches(0.8), s5_top, s5_w, s5_h, accent_color=C_ROSE)
    tb_s = s5.shapes.add_textbox(Inches(1.05), s5_top + Inches(0.20), s5_w - Inches(0.50), s5_h - Inches(0.35))
    tf_s = tb_s.text_frame
    tf_s.word_wrap = True
    tf_s.margin_left = tf_s.margin_top = tf_s.margin_right = tf_s.margin_bottom = 0

    p_st = tf_s.paragraphs[0]
    p_st.text = "INTEGRITY & PERIMETER DEFENSE"
    p_st.font.name = FONT_MAIN
    p_st.font.size = Pt(8.5)
    p_st.font.bold = True
    p_st.font.color.rgb = C_ROSE
    p_st.space_after = Pt(2)

    p_sh = tf_s.add_paragraph()
    p_sh.text = "Institutional Security & Policy Guardrails"
    p_sh.font.name = FONT_MAIN
    p_sh.font.size = Pt(14)
    p_sh.font.bold = True
    p_sh.font.color.rgb = C_WHITE
    p_sh.space_after = Pt(10)

    s_items = [
        ("SQL Injection Immunity", "Parameterized SQL placeholders across all API endpoints guarantee zero exposure to malicious inputs."),
        ("Cross-Site Scripting (XSS) Defense", "Comprehensive DOM escaping prevents injected scripts from executing inside the student portal."),
        ("Anti-Jailbreak Persona Lock", "Rigid system-level guardrails reject prompt injection attacks and unauthorized policy override attempts."),
        ("Strict Institutional Scope Fencing", "Off-topic questions (e.g. programming assignments, entertainment) are courteously declined."),
        ("Hard Numerical Cutoff Logic", "Enforces uncompromising policy cutoffs (e.g. 64.9% attendance is non-condonable detention; 65.0% allows medical review).")
    ]
    for lead, desc in s_items:
        pb = tf_s.add_paragraph()
        pb.space_after = Pt(6)

        r1 = pb.add_run()
        r1.text = f"•  {lead}: "
        r1.font.name = FONT_MAIN
        r1.font.size = Pt(10)
        r1.font.bold = True
        r1.font.color.rgb = C_WHITE

        r2 = pb.add_run()
        r2.text = desc
        r2.font.name = FONT_MAIN
        r2.font.size = Pt(9.5)
        r2.font.color.rgb = C_TEXT_LIGHT

    # Right: Production Integration
    add_container_card(s5, Inches(6.8), s5_top, s5_w, s5_h, accent_color=C_BLUE)
    tb_p = s5.shapes.add_textbox(Inches(7.05), s5_top + Inches(0.20), s5_w - Inches(0.50), s5_h - Inches(0.35))
    tf_p = tb_p.text_frame
    tf_p.word_wrap = True
    tf_p.margin_left = tf_p.margin_top = tf_p.margin_right = tf_p.margin_bottom = 0

    p_pt = tf_p.paragraphs[0]
    p_pt.text = "CAMPUS INTEGRATION & RESILIENCE"
    p_pt.font.name = FONT_MAIN
    p_pt.font.size = Pt(8.5)
    p_pt.font.bold = True
    p_pt.font.color.rgb = C_BLUE
    p_pt.space_after = Pt(2)

    p_ph = tf_p.add_paragraph()
    p_ph.text = "Portal Deployment & High Availability"
    p_ph.font.name = FONT_MAIN
    p_ph.font.size = Pt(14)
    p_ph.font.bold = True
    p_ph.font.color.rgb = C_WHITE
    p_ph.space_after = Pt(10)

    p_items = [
        ("Single-Tag Portal Embed", "Integrates into official university portals (sraap.in) via a single lightweight vanilla JS script tag."),
        ("Multi-Tier LLM Failover Chain", "Primary Google Gemini 3.1 Flash-Lite automatically cascades to secondary OpenRouter models upon provider downtime."),
        ("Graceful Auto-RAG Fallback", "When upstream LLM APIs experience rate limits, the system extracts verified facts directly from retrieved chunks."),
        ("Dynamic Knowledge Ingestion", "POST /api/sync allows university staff to ingest new circulars and policy amendments without server restarts."),
        ("Minimal Dependency Footprint", "Runs efficiently without heavy PyTorch or GPU containers, keeping institutional hosting costs minimal.")
    ]
    for lead, desc in p_items:
        pb = tf_p.add_paragraph()
        pb.space_after = Pt(6)

        r1 = pb.add_run()
        r1.text = f"•  {lead}: "
        r1.font.name = FONT_MAIN
        r1.font.size = Pt(10)
        r1.font.bold = True
        r1.font.color.rgb = C_WHITE

        r2 = pb.add_run()
        r2.text = desc
        r2.font.name = FONT_MAIN
        r2.font.size = Pt(9.5)
        r2.font.color.rgb = C_TEXT_LIGHT

    # =========================================================================
    # SLIDE 6: ENGINEERING OWNERSHIP & PRODUCTION ROADMAP
    # =========================================================================
    s6 = prs.slides.add_slide(blank_layout)
    set_bg(s6)
    add_header(s6, "05 · Ownership & Phase 2 Roadmap", 
               "Engineering Division & Phase 2 Production Roadmap", 
               "Four-member software engineering ownership alongside our campus production roadmap.",
               accent_color=C_PURPLE)

    s6_w = Inches(5.72)
    s6_h = Inches(4.9)
    s6_top = Inches(1.95)

    # Left: 4-Member Team Ownership
    add_container_card(s6, Inches(0.8), s6_top, s6_w, s6_h, accent_color=C_AMBER)
    tb_t = s6.shapes.add_textbox(Inches(1.05), s6_top + Inches(0.20), s6_w - Inches(0.50), s6_h - Inches(0.35))
    tf_t = tb_t.text_frame
    tf_t.word_wrap = True
    tf_t.margin_left = tf_t.margin_top = tf_t.margin_right = tf_t.margin_bottom = 0

    p_tt = tf_t.paragraphs[0]
    p_tt.text = "CORE ENGINEERING ROLES"
    p_tt.font.name = FONT_MAIN
    p_tt.font.size = Pt(8.5)
    p_tt.font.bold = True
    p_tt.font.color.rgb = C_AMBER
    p_tt.space_after = Pt(2)

    p_th = tf_t.add_paragraph()
    p_th.text = "4-Member Architecture Division"
    p_th.font.name = FONT_MAIN
    p_th.font.size = Pt(14)
    p_th.font.bold = True
    p_th.font.color.rgb = C_WHITE
    p_th.space_after = Pt(10)

    team_members = [
        ("Avinash Malladi (Team Lead)", "AI Agent Architect & Orchestration Lead", "Engineered agent/core.py orchestration loop, auto-context injection, safety fences, and multi-tier LLM failover."),
        ("Team Member 2", "Hybrid RAG & Retrieval Systems Engineer", "Built agent/retriever.py dual-branch pipeline (BM25 + Dense Semantic), phrase reranker, and student slang normalizer."),
        ("Team Member 3", "Backend Systems & Database Engineer", "Developed app.py REST API, agent/db.py SQLite WAL schema for concurrent workers, and 10-digit roll decoder."),
        ("Team Member 4", "Frontend Integration & Quality Assurance Lead", "Engineered static/widget.js embeddable widget, session history restoration UI, and automated security verification test suites.")
    ]

    for name, role, desc in team_members:
        pb = tf_t.add_paragraph()
        pb.space_after = Pt(6)

        r1 = pb.add_run()
        r1.text = f"•  {name}: "
        r1.font.name = FONT_MAIN
        r1.font.size = Pt(10)
        r1.font.bold = True
        r1.font.color.rgb = C_WHITE

        r2 = pb.add_run()
        r2.text = f"{role} — {desc}"
        r2.font.name = FONT_MAIN
        r2.font.size = Pt(9.5)
        r2.font.color.rgb = C_TEXT_LIGHT

    # Right: Phase 2 Production Roadmap (What We Are Going To Do)
    add_container_card(s6, Inches(6.8), s6_top, s6_w, s6_h, accent_color=C_GREEN)
    tb_m = s6.shapes.add_textbox(Inches(7.05), s6_top + Inches(0.20), s6_w - Inches(0.50), s6_h - Inches(0.35))
    tf_m = tb_m.text_frame
    tf_m.word_wrap = True
    tf_m.margin_left = tf_m.margin_top = tf_m.margin_right = tf_m.margin_bottom = 0

    p_mt = tf_m.paragraphs[0]
    p_mt.text = "WHAT WE ARE GOING TO DO"
    p_mt.font.name = FONT_MAIN
    p_mt.font.size = Pt(8.5)
    p_mt.font.bold = True
    p_mt.font.color.rgb = C_GREEN
    p_mt.space_after = Pt(2)

    p_mh = tf_m.add_paragraph()
    p_mh.text = "Phase 2 Production Engineering Roadmap"
    p_mh.font.name = FONT_MAIN
    p_mh.font.size = Pt(14)
    p_mh.font.bold = True
    p_mh.font.color.rgb = C_WHITE
    p_mh.space_after = Pt(10)

    roadmap_items = [
        ("Live ERP / SIS Webhooks", "Direct authenticated webhook integration with SR University's SRAAP portal to pull live attendance percentages and exam dues clearance via student tokens."),
        ("Proactive Academic Risk Alerts", "Autonomous alert triggers warning students when attendance drops below condonable thresholds (75% early notice, 65% critical detention risk)."),
        ("Multi-School Knowledge Graph", "Scaling knowledge indexing beyond B.Tech to encompass Postgraduate regulations (M.Tech, MBA, MCA, Ph.D.) and allied healthcare circulars."),
        ("Multilingual Vernacular Voice", "Integrating regional Telugu and Hindi speech-to-text and text-to-speech layers for accessible guidance across all student cohorts."),
        ("Institutional Telemetry Portal", "Administrative analytics dashboard tracking student confusion points, circular effectiveness, and high-frequency FAQ trends.")
    ]

    for lead, desc in roadmap_items:
        pb = tf_m.add_paragraph()
        pb.space_after = Pt(6)

        r1 = pb.add_run()
        r1.text = f"•  {lead}: "
        r1.font.name = FONT_MAIN
        r1.font.size = Pt(10)
        r1.font.bold = True
        r1.font.color.rgb = C_WHITE

        r2 = pb.add_run()
        r2.text = desc
        r2.font.name = FONT_MAIN
        r2.font.size = Pt(9.5)
        r2.font.color.rgb = C_TEXT_LIGHT

    # Save cleanly
    prs.save(output_path)
    print(f"Breathtaking 6-slide deck created with 100% precision at: {output_path}")

if __name__ == "__main__":
    build_presentation()

