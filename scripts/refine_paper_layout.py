import re

with open('scripts/test_humanized_paper.py', 'r', encoding='utf-8') as f:
    text = f.read()

# 1. Add keep_with_next to add_sec_heading and add_subsec_heading
old_sec_heading = '''    def add_sec_heading(title):
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_before = Pt(4.5)
        p.paragraph_format.space_after  = Pt(1.5)
        p.paragraph_format.line_spacing = Pt(9.8)
        run = p.add_run(title)
        run.bold = True
        run.font.name = 'Times New Roman'
        run.font.size = Pt(9.5)'''

new_sec_heading = '''    def add_sec_heading(title):
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_before = Pt(4.5)
        p.paragraph_format.space_after  = Pt(1.5)
        p.paragraph_format.line_spacing = Pt(9.8)
        p.paragraph_format.keep_with_next = True
        run = p.add_run(title)
        run.bold = True
        run.font.name = 'Times New Roman'
        run.font.size = Pt(9.5)'''

text = text.replace(old_sec_heading, new_sec_heading)

old_subsec_heading = '''    def add_subsec_heading(title):
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        p.paragraph_format.space_before = Pt(3)
        p.paragraph_format.space_after  = Pt(1)
        p.paragraph_format.line_spacing = Pt(9.8)
        run = p.add_run(title)
        run.italic = True
        run.bold = True
        run.font.name = 'Times New Roman'
        run.font.size = Pt(9.0)'''

new_subsec_heading = '''    def add_subsec_heading(title):
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        p.paragraph_format.space_before = Pt(3)
        p.paragraph_format.space_after  = Pt(1)
        p.paragraph_format.line_spacing = Pt(9.8)
        p.paragraph_format.keep_with_next = True
        run = p.add_run(title)
        run.italic = True
        run.bold = True
        run.font.name = 'Times New Roman'
        run.font.size = Pt(9.0)'''

text = text.replace(old_subsec_heading, new_subsec_heading)

# 2. Perfect calibration of Subsection III.E to fill Page 2 Col 2 cleanly (67 words)
old_iiie = '''    # Subsection III.E calibrated to end cleanly at bottom of Page 2 Col 2!
    add_subsec_heading("E. Page-Aware Document Processing and Chunking")
    add_p(
        "To guarantee dependable citations, our offline pipeline parses text along physical PDF page breaks rather than arbitrary character "
        "intervals. Across the Student Handbook and the R23, R24, and R25 regulations, the parser created 1,421 page-aligned chunks from 660 source "
        "pages. Complex tabular layouts—such as letter grade cutoffs, credit allocation matrix schedules, and fee refund timelines—were systematically "
        "converted into structured Markdown tables rather than raw flattened strings. By maintaining exact page-to-chunk bijection and embedding canonical "
        "section headers within each entry, AURA ensures that every retrieved context snippet maps directly to an inspectable physical printed page.",
        space_aft=1
    )'''

new_iiie = '''    # Subsection III.E calibrated to end cleanly at bottom of Page 2 Col 2!
    add_subsec_heading("E. Page-Aware Document Processing and Chunking")
    add_p(
        "To guarantee dependable citations, our offline pipeline parses text along physical PDF page breaks rather than arbitrary character "
        "intervals. Across the Student Handbook and the R23, R24, and R25 regulations, the parser created 1,421 page-aligned chunks from 660 source "
        "pages. Complex tabular layouts—such as letter grade cutoffs, promotion thresholds, and fee refund schedules—were converted into "
        "structured Markdown tables, ensuring each snippet maps directly to an inspectable physical printed page.",
        space_aft=1
    )'''

text = text.replace(old_iiie, new_iiie)

with open('scripts/test_humanized_paper.py', 'w', encoding='utf-8') as f:
    f.write(text)

print('Refinements applied to scripts/test_humanized_paper.py')
