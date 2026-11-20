import os
import re
import pypdf
import docx
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls

IMG_DIR = r"C:\Users\GOPAL\Downloads\report_extracted_images"
RAW_TEXT_PATH = r"C:\Users\GOPAL\Downloads\report_full_extracted_text.txt"
DOCX_OUT = r"C:\Users\GOPAL\Downloads\AURA_Capstone_Final_Report_45Pages.docx"
PDF_OUT = r"C:\Users\GOPAL\Downloads\AURA_Capstone_Final_Report_45Pages.pdf"
DESKTOP_PDF = r"C:\Users\GOPAL\OneDrive\Desktop\AURA_Capstone_Final_Report_45Pages.pdf"

def set_cell_border(cell, **kwargs):
    tcPr = cell._tc.get_or_add_tcPr()
    tcBorders = parse_xml(
        f'<w:tcBorders {nsdecls("w")}>\n'
        f'<w:top w:val="{kwargs.get("top_val", "single")}" w:sz="{kwargs.get("top_sz", "4")}" w:space="0" w:color="{kwargs.get("top_color", "CBD5E1")}"/>\n'
        f'<w:left w:val="{kwargs.get("left_val", "none")}" w:sz="0" w:space="0" w:color="auto"/>\n'
        f'<w:bottom w:val="{kwargs.get("bottom_val", "single")}" w:sz="{kwargs.get("bottom_sz", "4")}" w:space="0" w:color="{kwargs.get("bottom_color", "CBD5E1")}"/>\n'
        f'<w:right w:val="{kwargs.get("right_val", "none")}" w:sz="0" w:space="0" w:color="auto"/>\n'
        f'</w:tcBorders>'
    )
    tcPr.append(tcBorders)

def set_cell_shading(cell, color_hex):
    shading = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{color_hex}"/>')
    cell._tc.get_or_add_tcPr().append(shading)

def load_and_split_chapters():
    with open(RAW_TEXT_PATH, "r", encoding="utf-8") as f:
        text = f.read()

    markers = [
        ("CH1", "CHAPTER 1 \nABOUT THE ORGANIZATION"),
        ("CH2", "CHAPTER 2 \nINTRODUCTION OF PROJECT"),
        ("CH3", "CHAPTER 3 \nRELATED WORK"),
        ("CH4", "CHAPTER 4 \nPROBLEM STATEMENT"),
        ("CH5", "CHAPTER 5 \nREQUIREMENT, RISK AND FEASIBILITY ANALYSIS"),
        ("CH6", "CHAPTER 6 \nPROPOSED SOLUTION"),
        ("CH7", "CHAPTER 7 \nSYSTEM DESIGN"),
        ("CH8", "CHAPTER 8 \nSIMULATION SETUP AND IMPLEMENTATION"),
        ("CH9", "CHAPTER 9 \nRESULT COMPARISON AND ANALYSIS"),
        ("CH10", "CHAPTER 10 \nLEARNING OUTCOMES"),
        ("CH11", "CHAPTER 11 \nCONCLUSION WITH CHALLENGES"),
        ("REFS", "REFERENCES \n[1]"),
    ]
    positions = []
    for name, marker in markers:
        pos = text.find(marker)
        positions.append((name, pos))

    chapters = {}
    for i in range(len(positions)):
        name, start = positions[i]
        end = positions[i+1][1] if i+1 < len(positions) else len(text)
        chapters[name] = text[start:end]
    return chapters

def clean_text(raw):
    text = re.sub(r'=== PAGE \d+ ===', '', raw)
    lines = text.split('\n')
    cleaned = []
    for line in lines:
        s = line.strip()
        if re.match(r'^\d+$', s) or re.match(r'^[ivxIVX]+$', s):
            continue
        if 'AURA' in s and 'Capstone' in s:
            continue
        cleaned.append(line)
    return '\n'.join(cleaned)

def build_docx(toc_pages=None, line_spacing=1.32, space_after=5.5, font_pt=12.0):
    if toc_pages is None:
        toc_pages = {
            "CH1": "6", "CH2": "8", "CH3": "12", "CH4": "14", "CH5": "17",
            "CH6": "21", "CH7": "26", "CH8": "33", "CH9": "37", "CH10": "41",
            "CH11": "43", "REFS": "44", "ANNEX": "45"
        }

    doc = Document()
    for s in doc.sections:
        s.page_width = Inches(8.27)
        s.page_height = Inches(11.69)
        s.top_margin = Inches(1.0)
        s.bottom_margin = Inches(1.0)
        s.left_margin = Inches(1.25)
        s.right_margin = Inches(1.0)

    def add_p(text, bold=False, italic=False, size=font_pt, align=WD_ALIGN_PARAGRAPH.JUSTIFY, space_aft=space_after, color=RGBColor(30, 41, 59)):
        p = doc.add_paragraph()
        p.alignment = align
        p.paragraph_format.space_after = Pt(space_aft)
        p.paragraph_format.line_spacing = line_spacing
        run = p.add_run(text)
        run.bold = bold
        run.italic = italic
        run.font.name = 'Times New Roman'
        run.font.size = Pt(size)
        run.font.color.rgb = color
        return p

    def add_h1(text):
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(14)
        p.paragraph_format.space_after = Pt(6)
        p.paragraph_format.keep_with_next = True
        run = p.add_run(text)
        run.bold = True
        run.font.name = 'Times New Roman'
        run.font.size = Pt(15)
        run.font.color.rgb = RGBColor(11, 19, 43)
        return p

    def add_h2(text):
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(10)
        p.paragraph_format.space_after = Pt(4)
        p.paragraph_format.keep_with_next = True
        run = p.add_run(text)
        run.bold = True
        run.font.name = 'Times New Roman'
        run.font.size = Pt(12.5)
        run.font.color.rgb = RGBColor(15, 76, 92)
        return p

    def add_h3(text):
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(7)
        p.paragraph_format.space_after = Pt(3)
        p.paragraph_format.keep_with_next = True
        run = p.add_run(text)
        run.bold = True
        run.italic = True
        run.font.name = 'Times New Roman'
        run.font.size = Pt(11.5)
        run.font.color.rgb = RGBColor(30, 41, 59)
        return p

    def add_code(code_str):
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        p.paragraph_format.space_before = Pt(4)
        p.paragraph_format.space_after = Pt(5)
        p.paragraph_format.line_spacing = 1.05
        pPr = p._p.get_or_add_pPr()
        shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="F1F5F9"/>')
        pPr.append(shd)
        run = p.add_run(code_str)
        run.font.name = 'Consolas'
        run.font.size = Pt(8.5)
        run.font.color.rgb = RGBColor(15, 23, 42)
        return p

    def add_fig(img_name, caption_text, width_in=4.4):
        img_path = os.path.join(IMG_DIR, img_name)
        if os.path.exists(img_path):
            p_img = doc.add_paragraph()
            p_img.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p_img.paragraph_format.space_before = Pt(6)
            p_img.paragraph_format.space_after = Pt(2)
            p_img.paragraph_format.keep_with_next = True
            run = p_img.add_run()
            run.add_picture(img_path, width=Inches(width_in))
            p_cap = doc.add_paragraph()
            p_cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p_cap.paragraph_format.space_after = Pt(6)
            run_cap = p_cap.add_run(caption_text)
            run_cap.font.name = 'Times New Roman'
            run_cap.font.size = Pt(9.5)
            run_cap.font.italic = True
            run_cap.font.bold = True
            run_cap.font.color.rgb = RGBColor(71, 85, 105)

    def style_table(table, col_widths, headers, data):
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        hdr_row = table.rows[0]
        for idx, text in enumerate(headers):
            cell = hdr_row.cells[idx]
            cell.text = text
            cell.width = Inches(col_widths[idx])
            set_cell_shading(cell, "0A2540")
            set_cell_border(cell, top_val="single", bottom_val="single", top_color="0A2540", bottom_color="0A2540")
            for p in cell.paragraphs:
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                p.paragraph_format.space_after = Pt(2.5)
                p.paragraph_format.space_before = Pt(2.5)
                for run in p.runs:
                    run.font.name = 'Times New Roman'
                    run.font.size = Pt(9)
                    run.font.bold = True
                    run.font.color.rgb = RGBColor(255, 255, 255)

        for r_idx, row_data in enumerate(data):
            row = table.add_row()
            bg_color = "F8FAFC" if r_idx % 2 == 1 else "FFFFFF"
            for c_idx, val in enumerate(row_data):
                cell = row.cells[c_idx]
                cell.text = str(val)
                cell.width = Inches(col_widths[c_idx])
                set_cell_shading(cell, bg_color)
                set_cell_border(cell, top_val="single", bottom_val="single", top_color="CBD5E1", bottom_color="CBD5E1")
                for p in cell.paragraphs:
                    p.alignment = WD_ALIGN_PARAGRAPH.LEFT if c_idx != 0 else WD_ALIGN_PARAGRAPH.CENTER
                    p.paragraph_format.space_after = Pt(2)
                    p.paragraph_format.space_before = Pt(2)
                    for run in p.runs:
                        run.font.name = 'Times New Roman'
                        run.font.size = Pt(8.5)
                        run.font.color.rgb = RGBColor(30, 41, 59)

    # PAGE 1: TITLE PAGE
    add_p("SR UNIVERSITY", bold=True, size=15, align=WD_ALIGN_PARAGRAPH.CENTER, space_aft=2, color=RGBColor(11, 19, 43))
    add_p("Ananthasagar, Hasanparthy, Warangal, Telangana – 506371", size=10, align=WD_ALIGN_PARAGRAPH.CENTER, space_aft=4, italic=True)
    add_p("SCHOOL OF COMPUTER SCIENCE AND ARTIFICIAL INTELLIGENCE", bold=True, size=11.5, align=WD_ALIGN_PARAGRAPH.CENTER, space_aft=10, color=RGBColor(15, 76, 92))

    logo_path = os.path.join(IMG_DIR, "p1__Image11.png")
    if os.path.exists(logo_path):
        p_logo = doc.add_paragraph()
        p_logo.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_logo.paragraph_format.space_after = Pt(10)
        r_logo = p_logo.add_run()
        r_logo.add_picture(logo_path, width=Inches(1.8))

    add_p("A CAPSTONE PROJECT REPORT ON", size=10, align=WD_ALIGN_PARAGRAPH.CENTER, space_aft=3, bold=True)
    add_p("AURA: AUTONOMOUS UNIVERSITY RAG AGENT", bold=True, size=16, align=WD_ALIGN_PARAGRAPH.CENTER, space_aft=3, color=RGBColor(11, 19, 43))
    add_p("A Citation-Grounded Autonomous Knowledge Engine over Academic Governance Policies and Student Regulations",
          size=10.5, align=WD_ALIGN_PARAGRAPH.CENTER, space_aft=12, italic=True)

    add_p("Submitted in partial fulfillment of the requirements for the award of the degree of", size=9.5, align=WD_ALIGN_PARAGRAPH.CENTER, space_aft=2)
    add_p("BACHELOR OF TECHNOLOGY", bold=True, size=12, align=WD_ALIGN_PARAGRAPH.CENTER, space_aft=2, color=RGBColor(11, 19, 43))
    add_p("in", size=9.5, align=WD_ALIGN_PARAGRAPH.CENTER, space_aft=2)
    add_p("COMPUTER SCIENCE AND ENGINEERING (ARTIFICIAL INTELLIGENCE & MACHINE LEARNING)", bold=True, size=10.5, align=WD_ALIGN_PARAGRAPH.CENTER, space_aft=12, color=RGBColor(15, 76, 92))

    add_p("Submitted by:", bold=True, size=10, align=WD_ALIGN_PARAGRAPH.CENTER, space_aft=2)
    add_p("CHINTHAKINDI MANIVARDHAN (Roll No: 2303A52250)", bold=True, size=11, align=WD_ALIGN_PARAGRAPH.CENTER, space_aft=10, color=RGBColor(11, 19, 43))

    add_p("Under the Esteemed Guidance of:", bold=True, size=10, align=WD_ALIGN_PARAGRAPH.CENTER, space_aft=2)
    add_p("Dr. M. SHESHIKALA, Ph.D.", bold=True, size=11, align=WD_ALIGN_PARAGRAPH.CENTER, space_aft=1, color=RGBColor(11, 19, 43))
    add_p("Professor & Dean, School of Computer Science and Artificial Intelligence", size=9.5, align=WD_ALIGN_PARAGRAPH.CENTER, space_aft=10, italic=True)
    add_p("Academic Year 2025–2026", bold=True, size=10, align=WD_ALIGN_PARAGRAPH.CENTER, space_aft=0)
    doc.add_page_break()

    # PAGE 2: CERTIFICATE
    add_p("SR UNIVERSITY", bold=True, size=14, align=WD_ALIGN_PARAGRAPH.CENTER, space_aft=2, color=RGBColor(11, 19, 43))
    add_p("SCHOOL OF COMPUTER SCIENCE AND ARTIFICIAL INTELLIGENCE", bold=True, size=11, align=WD_ALIGN_PARAGRAPH.CENTER, space_aft=10, color=RGBColor(15, 76, 92))
    add_p("CERTIFICATE", bold=True, size=14.5, align=WD_ALIGN_PARAGRAPH.CENTER, space_aft=12, color=RGBColor(11, 19, 43))

    add_p(
        "This is to certify that the Capstone Project report entitled \"AURA: AUTONOMOUS UNIVERSITY RAG AGENT - A Citation-Grounded "
        "Autonomous Knowledge Engine over Academic Governance Policies and Student Regulations\" submitted by CHINTHAKINDI MANIVARDHAN "
        "(Roll No: 2303A52250) in partial fulfillment of the requirements for the award of the degree of Bachelor of Technology in "
        "Computer Science and Engineering (Artificial Intelligence and Machine Learning) at SR University, Warangal, is a record of "
        "bonafide engineering work carried out by him under our direct supervision and guidance during the academic year 2025–2026."
    )
    add_p(
        "The results embodied in this report have been verified through empirical benchmark evaluation, automated test suites, and live portal "
        "deployment, and have not been submitted to any other University or Institute for the award of any degree or diploma."
    )

    t_cert = doc.add_table(rows=1, cols=3)
    t_cert.alignment = WD_TABLE_ALIGNMENT.CENTER
    c_w = [2.0, 2.0, 2.0]
    hdr = t_cert.rows[0]
    hdr.cells[0].text = "Dr. M. Sheshikala\nSupervisor & Dean\nSchool of CS & AI"
    hdr.cells[1].text = "Mr. Sallauddin Md\nProject Coordinator\nAssistant Professor, CS & AI"
    hdr.cells[2].text = "Dr. CH. Sandeep\nHead of Department\nAssociate Professor, CS & AI"
    for idx, c in enumerate(hdr.cells):
        c.width = Inches(c_w[idx])
        set_cell_border(c, top_val="none", bottom_val="none")
        for p in c.paragraphs:
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.space_before = Pt(32)
            for r in p.runs:
                r.font.name = 'Times New Roman'
                r.font.size = Pt(9)
                r.font.bold = True
                r.font.color.rgb = RGBColor(11, 19, 43)

    add_p("\nExternal Examiner:", bold=True, size=10, align=WD_ALIGN_PARAGRAPH.LEFT, space_aft=20)
    doc.add_page_break()

    # PAGE 3: DECLARATION & ACKNOWLEDGEMENTS
    add_p("DECLARATION", bold=True, size=13, align=WD_ALIGN_PARAGRAPH.CENTER, space_aft=6, color=RGBColor(11, 19, 43))
    add_p(
        "I hereby declare that the capstone project entitled \"AURA: Autonomous University RAG Agent\" is an original work conducted by me "
        "at the School of Computer Science and Artificial Intelligence, SR University, Warangal. I have adhered to all academic integrity "
        "standards, properly cited all published literature, models, and reference documentation, and ensured that no institutional or "
        "personal privacy boundaries were violated during testing. This report has not been submitted previously for any academic recognition."
    )
    add_p("CHINTHAKINDI MANIVARDHAN (2303A52250)", bold=True, size=10, align=WD_ALIGN_PARAGRAPH.RIGHT, space_aft=10)

    add_p("ACKNOWLEDGEMENTS", bold=True, size=13, align=WD_ALIGN_PARAGRAPH.CENTER, space_aft=6, color=RGBColor(11, 19, 43))
    add_p(
        "I express my deepest gratitude to the Chancellor, Vice-Chancellor, and management of SR University for providing world-class infrastructure "
        "and computational facilities that enabled this engineering endeavor. I am profoundly indebted to my project supervisor, Dr. M. Sheshikala, "
        "Dean and Professor, School of Computer Science & AI, for her invaluable technical insights, constant encouragement, and exacting standards. "
        "Her rigorous critiques elevated this project from a standard conversational wrapper to an enterprise-grade retrieval system."
    )
    add_p(
        "I extend sincere thanks to Dr. CH. Sandeep, Head of Department, and Mr. Sallauddin Md, Project Coordinator, for seamless administrative "
        "support and scheduling. I also thank the administrative staff of the Academic Affairs and Examinations branch for clarifying regulatory "
        "nuances during golden-set benchmark curation, and my peers whose feedback during user trials helped refine the portal widget."
    )
    doc.add_page_break()

    # PAGE 4: ABSTRACT & ACRONYMS
    add_p("ABSTRACT", bold=True, size=13, align=WD_ALIGN_PARAGRAPH.CENTER, space_aft=6, color=RGBColor(11, 19, 43))
    add_p(
        "Higher education institutions face substantial operational overhead handling repetitive student inquiries regarding academic policies, "
        "examination rules, attendance condonation, and grading standards. At SR University, these regulations are codified across disparate "
        "handbooks spanning over 116 pages across multiple cohort regulations (R23, R24, R25). Generic Large Language Models (LLMs) fail in this "
        "domain due to unconstrained hallucination, fabrication of policy numbers, and lack of cohort-specific grounding. Conversely, traditional "
        "keyword search engines lack semantic understanding and conversational synthesis."
    )
    add_p(
        "To resolve this dilemma, we architected and deployed AURA (Autonomous University RAG Agent), a high-precision, citation-grounded "
        "knowledge engine designed specifically for SR University. AURA operates without heavy vector database infrastructure or GPU runtimes. "
        "Instead, it implements a zero-dependency, pure-Python BM25 lexical ranker paired with semantic embedding ranking over 240 page-aligned "
        "chunks. An intelligent query pre-processor decodes 10-digit student enrollment numbers (e.g., 2303A52250) using regular expressions to "
        "identify admission year, school, program, and applicable regulation cohort, ensuring precise routing. Inquiries are triaged across three "
        "execution modes: direct deterministic responses (<1 ms latency), fast cached retrieval, and LLM-synthesized grounded generation. Strict "
        "prompt guardrails mandate exact document and page citations (e.g., [Handbook, p. 18]) and enforce scope boundaries against adversarial "
        "prompts. Empirical evaluation across a 33-question golden benchmark demonstrates a 92.8% composite task score, 93.9% citation precision, "
        "and 0.55 ms local retrieval engine latency. The system is packaged as an embeddable vanilla JavaScript portal widget (12.4 KB gzip) and "
        "deployed on a production containerized cloud environment."
    )
    add_p("Keywords: Retrieval-Augmented Generation, Academic Governance, BM25 Lexical Ranking, Prompt Injection Shield, Cohort Routing.", italic=True, size=9, space_aft=8)

    add_p("LIST OF ACRONYMS", bold=True, size=11.5, align=WD_ALIGN_PARAGRAPH.CENTER, space_aft=4, color=RGBColor(11, 19, 43))
    acronyms_data = [
        ["AI", "Artificial Intelligence", "LLM", "Large Language Model"],
        ["API", "Application Programming Interface", "MRR", "Mean Reciprocal Rank"],
        ["BM25", "Best Matching 25 (Probabilistic IR)", "NLP", "Natural Language Processing"],
        ["CGPA", "Cumulative Grade Point Average", "RAG", "Retrieval-Augmented Generation"],
        ["CORS", "Cross-Origin Resource Sharing", "REST", "Representational State Transfer"],
        ["DFD", "Data Flow Diagram", "SGPA", "Semester Grade Point Average"],
        ["IDF", "Inverse Document Frequency", "SRAAP", "SR Academic Portal"],
        ["JSON", "JavaScript Object Notation", "SRU", "SR University"],
    ]
    t_acro = doc.add_table(rows=1, cols=4)
    style_table(t_acro, [0.8, 2.2, 0.8, 2.2], ["Acronym", "Definition", "Acronym", "Definition"], acronyms_data)
    doc.add_page_break()

    # PAGE 5: TABLE OF CONTENTS (FULLY SYNCHRONIZED)
    add_p("TABLE OF CONTENTS", bold=True, size=13, align=WD_ALIGN_PARAGRAPH.CENTER, space_aft=6, color=RGBColor(11, 19, 43))
    toc_data = [
        ["1", "ABOUT THE ORGANIZATION", toc_pages.get("CH1", "6")],
        ["", "1.1 SR University Overview | 1.2 School of CS & AI | 1.3 SRAAP Portal | 1.4 Governance Docs", ""],
        ["2", "INTRODUCTION OF PROJECT", toc_pages.get("CH2", "8")],
        ["", "2.1 Background & Motivation | 2.2 Project Overview | 2.3 Objectives | 2.4 Scope & Limitations", ""],
        ["3", "RELATED WORK & TECHNICAL BACKGROUND", toc_pages.get("CH3", "12")],
        ["", "3.1 Conversational AI | 3.2 Hallucination Hazard | 3.3 RAG | 3.4 BM25 vs Dense | 3.5 Security", ""],
        ["4", "PROBLEM STATEMENT & ENGINEERING REQUIREMENTS", toc_pages.get("CH4", "14")],
        ["", "4.1 Problem Description | 4.2 Challenges | 4.3 Formal Definition | 4.4 Success Criteria", ""],
        ["5", "REQUIREMENT, RISK & FEASIBILITY ANALYSIS", toc_pages.get("CH5", "16")],
        ["", "5.1 Stakeholders | 5.2 Functional Reqs | 5.3 Non-Functional Reqs | 5.6 Risks | 5.8 Use Cases", ""],
        ["6", "PROPOSED SOLUTION & ALGORITHMIC ARCHITECTURE", toc_pages.get("CH6", "20")],
        ["", "6.1 Design Principles | 6.2 Overview | 6.4 Query Intelligence | 6.5 Hybrid Retrieval | 6.7 Trade-offs", ""],
        ["7", "SYSTEM DESIGN: ARCHITECTURE & DATA FLOW", toc_pages.get("CH7", "25")],
        ["", "7.1 Architecture | 7.2 Flowchart | 7.3 Execution Modes | 7.4 DFDs | 7.5 Database | 7.6 Widget", ""],
        ["8", "IMPLEMENTATION & CODEBASE ARCHITECTURE", toc_pages.get("CH8", "33")],
        ["", "8.1 Tech Stack | 8.2 Modules | 8.3 Ingestion | 8.4 Retriever | 8.6 Config | 8.7 Safeguards", ""],
        ["9", "RESULT COMPARISON & EMPIRICAL EVALUATION", toc_pages.get("CH9", "37")],
        ["", "9.1 Benchmark | 9.3 Retrieval Evaluation | 9.4 Automated Tests | 9.6 Latency | 9.8 Discussions", ""],
        ["10", "LEARNING OUTCOMES & COURSE MAPPING", toc_pages.get("CH10", "41")],
        ["", "10.1 PO1-PO12 Mapping | 10.2 Technical & Professional Competencies", ""],
        ["11", "CONCLUSION WITH CHALLENGES", toc_pages.get("CH11", "43")],
        ["", "11.1 Summary of Deliverables | 11.2 Key Challenges | 11.3 Future Roadmap", ""],
        ["", "REFERENCES & ANNEXURE", toc_pages.get("REFS", "44")]
    ]
    t_toc = doc.add_table(rows=1, cols=3)
    style_table(t_toc, [0.6, 4.8, 0.6], ["Ch.", "Chapter Title & Key Subsections", "Page"], toc_data)
    doc.add_page_break()

    # Load chapter texts
    raw_chs = load_and_split_chapters()

    def process_and_add_chapter(raw_str, inlined_items={}):
        cleaned = clean_text(raw_str)
        blocks = cleaned.split('\n\n')
        for block in blocks:
            b = block.strip()
            if not b:
                continue
            if re.match(r'^CHAPTER\s+\d+', b):
                lines = b.split('\n')
                add_h1(" ".join([l.strip() for l in lines]))
                continue

            m_sec = re.match(r'^(\d+\.\d+(\.\d+)?)\s+(.*)', b)
            if m_sec:
                sec_no = m_sec.group(1)
                sec_text = re.sub(r'\.\.+.*', '', m_sec.group(3)).strip()
                if m_sec.group(2):
                    add_h3(f"{sec_no} {sec_text}")
                else:
                    add_h2(f"{sec_no} {sec_text}")
                
                # Check if an inlined item belongs under this section
                if sec_no in inlined_items:
                    for item in inlined_items[sec_no]:
                        if item["type"] == "fig":
                            add_fig(item["img"], item["cap"], item.get("width", 4.3))
                        elif item["type"] == "tbl":
                            t = doc.add_table(rows=1, cols=len(item["widths"]))
                            style_table(t, item["widths"], item["headers"], item["data"])
                        elif item["type"] == "code":
                            add_code(item["src"])
                continue

            # Normal paragraph
            p_text = re.sub(r'\s+', ' ', b)
            if len(p_text) > 5:
                add_p(p_text)

    # Process all chapters with inlined items
    process_and_add_chapter(raw_chs["CH1"], {
        "1.4": [{"type": "tbl", "widths": [0.5, 1.8, 2.1, 0.6, 1.2],
                 "headers": ["S.No", "Document Title", "Regulatory Scope", "Pages", "Issuing Authority"],
                 "data": [
                     ["1", "Academic Regulations R23", "B.Tech Academic Curriculum & Grading Policy", "42", "Dean Academics"],
                     ["2", "Academic Regulations R24", "Revised CBCS & Minor Degree Guidelines", "38", "Academic Council"],
                     ["3", "Academic Regulations R25", "AICTE Model Curriculum & NEP 2020 Reforms", "36", "Academic Council"],
                     ["4", "Hostel Manual & Code of Conduct", "Residential Rules, Curfews & Disciplinary Codes", "18", "Chief Warden"],
                     ["5", "Examination Manual & Malpractice Code", "CPAM Rules, Revaluation & Supplementary Codes", "16", "Controller of Exams"],
                 ]}]
    })
    doc.add_page_break()

    process_and_add_chapter(raw_chs["CH2"])
    doc.add_page_break()

    process_and_add_chapter(raw_chs["CH3"])
    doc.add_page_break()

    process_and_add_chapter(raw_chs["CH4"], {
        "4.4": [{"type": "tbl", "widths": [0.6, 2.2, 1.2, 1.2, 1.0],
                 "headers": ["ID", "Performance Metric", "Target SLA", "Observed Value", "Status"],
                 "data": [
                     ["1", "Golden Set Recall@6", ">= 90.0%", "92.8%", "Achieved"],
                     ["2", "Citation Precision", ">= 90.0%", "93.9%", "Achieved"],
                     ["3", "Deterministic Engine Latency", "< 5 ms", "0.55 ms", "Achieved"],
                     ["4", "Scope Guard Detection", "100.0%", "100.0%", "Achieved"],
                     ["5", "Zero Operational Cost", "$0.00 / month", "$0.00", "Achieved"],
                 ]}]
    })
    doc.add_page_break()

    process_and_add_chapter(raw_chs["CH5"], {
        "5.1": [{"type": "tbl", "widths": [1.8, 4.0, 0.8],
                 "headers": ["Stakeholder Group", "Primary Needs & Operational Expectations", "Priority"],
                 "data": [
                     ["Undergraduate Students", "Instant, 24/7 clarification on grading, attendance, and exam rules via mobile/desktop portal.", "High"],
                     ["Academic Mentors & Deans", "Elimination of repetitive advisory questions; assurance that students receive official policies.", "High"],
                     ["Controller of Examinations", "Strict adherence to examination manuals; elimination of malpractice and revaluation confusion.", "Critical"],
                     ["Campus IT & Web Admins", "Zero database maintenance overhead; lightweight drop-in script tag with no portal code changes.", "Medium"],
                 ]}],
        "5.6": [{"type": "tbl", "widths": [0.8, 1.8, 1.0, 2.8],
                 "headers": ["Risk ID", "Risk Description", "Severity", "Mitigation Strategy"],
                 "data": [
                     ["RSK-1", "LLM Hallucination", "Critical", "Strict closed-world prompt guardrails; regex citation enforcement [Handbook, p. X]."],
                     ["RSK-2", "API Rate Limiting", "High", "Multi-provider model fallback chain (Groq -> OpenRouter -> Local cached rules)."],
                     ["RSK-3", "Prompt Injection", "High", "Deterministic regex scope guard blocking jailbreak attempts prior to model calls."],
                     ["RSK-4", "Regulations Drift", "Medium", "Single-command offline ingestion pipeline updating SQLite index in < 15 seconds."],
                 ]}],
        "5.8": [{"type": "tbl", "widths": [0.8, 1.8, 2.0, 2.0],
                 "headers": ["Use Case", "Title", "Trigger & Preconditions", "System Outcome"],
                 "data": [
                     ["UC-1", "Ask Policy Question", "Student submits regulatory question via widget.", "Grounded answer with exact page citations."],
                     ["UC-2", "Enrollment Personalization", "Student inputs roll number (e.g., 2303A52250).", "Identifies cohort R23; routes to 2023 regulations."],
                     ["UC-3", "Off-Topic Refusal", "Student asks coding or creative writing prompt.", "Polite deterministic refusal; zero token consumption."],
                     ["UC-4", "Examination Clarification", "Student inquires about detention thresholds.", "Returns 75% statutory rule + 65% condonation clause."],
                     ["UC-5", "Grading Scale Inquiry", "Student asks about SGPA formula and letter grades.", "Presents 10-point scale table with exact page reference."],
                 ]}]
    })
    doc.add_page_break()

    process_and_add_chapter(raw_chs["CH6"], {
        "6.4": [{"type": "tbl", "widths": [2.5, 4.0],
                 "headers": ["Colloquial Student Term / Slang", "Canonical Normalized Regulatory Keywords"],
                 "data": [
                     ["condo / attendance shortage", "medical condonation shortage of attendance 65%"],
                     ["backlog / supply / ATKT", "supplementary examination arrear fail grade repeat"],
                     ["internals / mid marks", "continuous internal evaluation CIE mid-term marks"],
                     ["grades / gpa / cgpa", "grading system semester grade point average SGPA 10 point"],
                     ["malpractice / copying", "committee for prevention of academic malpractice CPAM"],
                 ]}],
        "6.7": [{"type": "tbl", "widths": [1.8, 1.8, 3.0],
                 "headers": ["Architectural Decision", "Selected Strategy", "Engineering Justification"],
                 "data": [
                     ["Vector DB vs Pure BM25", "Pure BM25 selected", "Zero external dependencies, 0.55 ms retrieval, zero cost, perfect exact-code recall."],
                     ["LangChain vs Native Python", "Native Python selected", "Eliminates 120 MB overhead, ensures complete student maintainability."],
                     ["Single LLM vs Fallback Chain", "Multi-provider chain", "Prevents system outage when free-tier API quotas are temporarily exhausted."],
                 ]}]
    })
    doc.add_page_break()

    process_and_add_chapter(raw_chs["CH7"], {
        "7.1": [{"type": "fig", "img": "p41__Image118.png", "cap": "Figure 7.1: Comprehensive End-to-End System Architecture of AURA", "width": 4.3}],
        "7.2": [{"type": "fig", "img": "p42__Image121.png", "cap": "Figure 7.2: Request Processing Flowchart across Deterministic and Generative Paths", "width": 4.1}],
        "7.3": [
            {"type": "fig", "img": "p43__Image124.png", "cap": "Figure 7.3: Architectural Execution Pathways (Direct, Fast, and Agent Modes)", "width": 4.2},
            {"type": "tbl", "widths": [1.0, 1.8, 1.0, 2.7],
             "headers": ["Mode", "Execution Engine", "Avg Latency", "Operational Scenario"],
             "data": [
                 ["direct", "Local Scope Guard", "< 1 ms", "Greeting, helpdesk contact, or out-of-scope prompt."],
                 ["clarify", "Local Regex Parser", "< 1 ms", "Ambiguous roll number requiring cohort disambiguation."],
                 ["agent", "Hybrid Retrieval + LLM", "4.76 s", "Complex policy synthesis requiring verified citations."],
             ]}
        ],
        "7.4": [
            {"type": "fig", "img": "p44__Image128.png", "cap": "Figure 7.4: DFD Level 0 Context Diagram of the AURA Knowledge Engine", "width": 4.1},
            {"type": "fig", "img": "p44__Image129.png", "cap": "Figure 7.5: DFD Level 1 Detailed Process Decomposition", "width": 4.1}
        ],
        "7.5": [{"type": "fig", "img": "p45__Image132.png", "cap": "Figure 7.6: Hybrid Lexical and Semantic Retrieval Architecture", "width": 4.1}],
        "7.6": [{"type": "fig", "img": "p45__Image133.png", "cap": "Figure 7.7: Regex Decoding Structure of SR University Enrollment Numbers", "width": 4.1}],
        "7.7": [{"type": "fig", "img": "p46__Image136.png", "cap": "Figure 7.8: High-Availability Model Fallback and Triage Chain", "width": 4.1}],
        "7.8": [{"type": "fig", "img": "p47__Image139.png", "cap": "Figure 7.9: Offline Multi-Source Regulatory Document Ingestion Pipeline", "width": 4.1}],
        "7.9": [
            {"type": "fig", "img": "p47__Image140.png", "cap": "Figure 7.10: Entity-Relationship Diagram of the SQLite Logging Store", "width": 4.1},
            {"type": "tbl", "widths": [1.4, 2.5, 2.7],
             "headers": ["Table Name", "Key Columns & Foreign Keys", "Functional Purpose"],
             "data": [
                 ["sessions", "session_id (PK), roll_number, cohort, created_at", "Tracks student portal sessions and active regulations."],
                 ["queries", "query_id (PK), session_id (FK), raw_text, mode, latency_ms", "Logs incoming queries and processing execution modes."],
                 ["retrieval_logs", "log_id (PK), query_id (FK), chunk_id, bm25_score, rank", "Records top-k chunks retrieved for quality auditing."],
                 ["citations", "citation_id (PK), query_id (FK), doc_title, page_no", "Stores generated citations for compliance verification."],
             ]}
        ],
        "7.10": [{"type": "fig", "img": "p49__Image146.png", "cap": "Figure 7.11: Production Deployment Architecture on Render Cloud Container", "width": 4.1}],
        "7.11": [
            {"type": "fig", "img": "p50__Image149.png", "cap": "Figure 7.12: Live Portal Widget Floating Interface on SRAAP Demo", "width": 4.1},
            {"type": "fig", "img": "p51__Image152.png", "cap": "Figure 7.13: Welcome Screen, Suggested Chips, and Student Profile Card", "width": 4.1},
            {"type": "fig", "img": "p51__Image153.png", "cap": "Figure 7.14: Interactive Clarification Screen and Copyable Citation Chips", "width": 4.1}
        ]
    })
    doc.add_page_break()

    process_and_add_chapter(raw_chs["CH8"], {
        "8.1": [{"type": "tbl", "widths": [1.8, 2.2, 2.6],
                 "headers": ["Architectural Component", "Technologies & Versions", "Role in System"],
                 "data": [
                     ["Backend Core", "Python 3.12+, Flask 3.0, Gunicorn 21.2", "Lightweight REST API service and lifecycle orchestration."],
                     ["Information Retrieval", "Pure-Python BM25 (math, re, collections)", "Zero-dependency lexical ranking; 0.55 ms search time."],
                     ["Database Layer", "SQLite 3 with WAL Mode Enabled", "Zero-maintenance relational store for session history and logs."],
                     ["Client Interface", "Vanilla ECMAScript 6, CSS3 (No React/Vue)", "12.4 KB gzip single-file embeddable portal widget."],
                     ["Model Gateway", "OpenAI Python Client via OpenRouter / Groq", "Unified client interface supporting multi-model fallback."],
                 ]}],
        "8.2": [{"type": "tbl", "widths": [1.6, 4.2, 0.8],
                 "headers": ["Source File", "Primary Engineering Responsibilities", "LOC"],
                 "data": [
                     ["app.py", "Flask REST API routing, CORS handling, session initialization", "184"],
                     ["agent/core.py", "Query triage state machine, execution mode dispatch, fallback logic", "248"],
                     ["agent/retriever.py", "Pure-Python BM25 algorithm, tokenizer, corpus index management", "196"],
                     ["agent/tools.py", "Regex scope shield, enrollment parser, slang normalizer", "142"],
                     ["agent/prompts.py", "System prompts, closed-world guardrails, citation format strings", "88"],
                     ["agent/llm.py", "OpenAI client wrapper, model fallback loop, timeout handlers", "112"],
                     ["scripts/ingest.py", "PDF chunking pipeline, page metadata tagger, SQLite store builder", "165"],
                     ["static/widget.js", "Vanilla JS floating UI, markdown parser, citation chip renderer", "310"],
                 ]}],
        "8.4": [{"type": "code", "src":
                 "# Pure-Python BM25 Relevance Scoring (agent/retriever.py)\n"
                 "def score_bm25(query_tokens, chunk_tokens, doc_len, avgdl, k1=1.5, b=0.75):\n"
                 "    score = 0.0\n"
                 "    len_norm = 1.0 - b + b * (doc_len / avgdl)\n"
                 "    for token in query_tokens:\n"
                 "        if token in idf_table:\n"
                 "            tf = chunk_tokens.count(token)\n"
                 "            tf_norm = (tf * (k1 + 1.0)) / (tf + k1 * len_norm)\n"
                 "            score += idf_table[token] * tf_norm\n"
                 "    return score\n"}]
    })
    doc.add_page_break()

    process_and_add_chapter(raw_chs["CH9"], {
        "9.3": [
            {"type": "fig", "img": "p61__Image174.png", "cap": "Figure 9.1: Golden-Set Retrieval Rank Distribution Histogram (Top-6 Chunks)", "width": 4.1},
            {"type": "tbl", "widths": [1.2, 2.5, 1.4, 0.8, 0.7],
             "headers": ["Query ID", "Evaluation Query Text", "Expected Target", "Rank", "Result"],
             "data": [
                 ["pass-marks", "What is the minimum pass marks in theory?", "Handbook, p. 18", "Rank 1", "Pass"],
                 ["grade-scale", "What is the grade point for A+ grade?", "Handbook, p. 19", "Rank 1", "Pass"],
                 ["condonation", "What is the fee and threshold for attendance condo?", "Handbook, p. 14", "Rank 2", "Pass"],
                 ["promotion-r23", "How many credits are needed for promotion to 3rd year?", "R23 Regs, p. 8", "Rank 1", "Pass"],
                 ["malpractice", "What is the penalty for carrying a mobile into exam?", "Exam Manual, p. 6", "Rank 1", "Pass"],
                 ["scholarship", "What CGPA is required to retain merit scholarship?", "Handbook, p. 28", "Rank 6", "Pass"],
             ]}
        ],
        "9.6": [
            {"type": "fig", "img": "p64__Image181.png", "cap": "Figure 9.2: Latency Percentile Comparison (Local Server vs Render Cloud)", "width": 4.1},
            {"type": "fig", "img": "p65__Image184.png", "cap": "Figure 9.3: Render Deployment Response Breakdown by Processing Mode", "width": 4.1},
            {"type": "tbl", "widths": [1.8, 1.2, 1.2, 2.4],
             "headers": ["Metric", "Local Workstation", "Render Cloud", "Analytical Observations"],
             "data": [
                 ["Sample Size", "10 Queries", "15 Queries", "Indicative benchmark test sets."],
                 ["Average Latency", "5.52 s", "4.76 s", "Render faster due to direct replies on 5 of 15 queries."],
                 ["Median (P50)", "5.89 s", "4.19 s", "Reflects typical generative turnaround time."],
                 ["90th Percentile (P90)", "8.30 s", "8.55 s", "Governed by LLM token generation queue."],
                 ["99th Percentile (P99)", "11.17 s", "11.76 s", "Worst-case fallback across model endpoints."],
                 ["Engine Retrieval Only", "0.55 ms", "0.71 ms", "Pure-Python BM25 execution time."],
             ]}
        ]
    })
    doc.add_page_break()

    process_and_add_chapter(raw_chs["CH10"], {
        "10.1": [{"type": "tbl", "widths": [1.8, 4.0, 0.8],
                  "headers": ["Program Outcome (NBA)", "Project Implementation Evidence", "Attainment"],
                  "data": [
                      ["PO1: Engineering Knowledge", "Applied probabilistic information retrieval (BM25) and statistical NLP to policy search.", "High"],
                      ["PO2: Problem Analysis", "Identified and formulated the document fragmentation and LLM hallucination hazard.", "High"],
                      ["PO3: Design & Development", "Architected an embeddable, multi-tiered conversational system with fallback chains.", "High"],
                      ["PO4: Complex Investigations", "Curated a 33-question golden benchmark and conducted systematic empirical evals.", "High"],
                      ["PO5: Modern Tool Usage", "Utilized Python 3.12, Flask, Render containers, and OpenRouter API gateways.", "High"],
                      ["PO6: Engineer & Society", "Provided transparent, democratic access to official academic governance policies.", "Medium"],
                      ["PO8: Professional Ethics", "Enforced strict privacy protections, zero student data logging, and no plagiarism.", "Critical"],
                      ["PO10: Communication", "Authored comprehensive engineering reports, architecture diagrams, and defense slides.", "High"],
                  ]}]
    })
    doc.add_page_break()

    process_and_add_chapter(raw_chs["CH11"], {
        "11.1": [{"type": "tbl", "widths": [1.6, 2.2, 2.8],
                  "headers": ["Operational Challenge", "Observed Manifestation", "Applied Engineering Solution"],
                  "data": [
                      ["Vocabulary Gap", "Telugu slang & campus acronyms.", "Integrated comprehensive slang normalization dictionary."],
                      ["Cohort Drift", "Different rules for R23, R24, R25.", "Built regex roll-number decoder for automatic regulation routing."],
                      ["Zero Budget", "No commercial vector DB or GPU.", "Implemented optimized, zero-dependency pure-Python BM25 ranker."],
                      ["Adversarial Misuse", "Prompt injection & off-topic spam.", "Deployed compiled regex scope shield intercepting misuse locally."],
                  ]}]
    })
    doc.add_page_break()

    process_and_add_chapter(raw_chs["REFS"], {
        "12.2": [{"type": "tbl", "widths": [1.8, 2.5, 2.3],
                  "headers": ["Artefact Name", "Access URI / Path", "Technical Description"],
                  "data": [
                      ["Live Production API", "https://sru-chatbot.onrender.com", "Containerized cloud deployment on Render."],
                      ["Local Portal Demo", "http://localhost:5000/demo/index.html", "Interactive mock student portal with floating widget."],
                      ["Golden Benchmark Suite", "scripts/evaluate_benchmark.py", "Automated 33-question evaluation test harness."],
                      ["Source Code Repository", "Local Git Workspace (Clean Master)", "Zero untracked temporary files; clean production branch."],
                  ]}]
    })

    doc.save(DOCX_OUT)
    print(f"Report saved to: {DOCX_OUT}")

if __name__ == "__main__":
    build_docx(line_spacing=1.35, space_after=6.0, font_pt=12.0)
