import pdfplumber
import re
from operator import itemgetter
from collections import defaultdict

hf4_input_files = ["../hf4_core.pdf", "../hf4_appendix.pdf", "../hf4_module1.pdf", "../hf4_module2.pdf"]
hf4_margin_width = 128
hf4_font_to_markup = {
    "MyriadPro-Light": "", "MyriadPro-Regular": "", "MyriadPro-Black": "",  # regular fonts
    "MyriadPro-Semibold": "**", "MyriadPro-Bold": "**",                     # bold fonts
    "MyriadPro-BoldCondIt": "_", "MyriadPro-BoldIt": "_",                   # bold italic fonts (marked up just italic)
    "MyriadPro-It": "_", "MyriadPro-LightIt": "_", "MyriadPro-It-SC700": "_",  # italic fonts
    "MyriadPro-BoldCond": "",           # used for examples, marked up as blockquote instead
    "AstronomicSignsSt": "<starsign>",  # special character font, see hf4_letter_to_starsign
}
hf4_letter_to_starsign = {
    # Venus   Mercury   Mars      Jupyter   Saturn    Uranus    Neptune   Ceres     Earth
    "C": "♀", "D": "☿", "E": "♂", "F": "♃", "G": "♄", "H": "♅", "J": "♆", "K": "⚳", "M": "♁", " ": " ",
}
hf4_page_to_extra_rects = defaultdict(list, {
    24: [{'top': 475, 'bottom': 723, 'x0': 41, 'y0': 841.9 - 723, 'x1': 552, 'y1': 841.9 - 475}],
    34: [{'top': 555, 'bottom': 792, 'x0': 41, 'y0': 841.9 - 792, 'x1': 555, 'y1': 841.9 - 555}],
    43: [{'top': 360, 'bottom': 795, 'x0': 637, 'y0': 841.9 - 795, 'x1': 1149, 'y1': 841.9 - 360}],
    49: [{'top': 164, 'bottom': 270, 'x0': 637, 'y0': 841.9 - 270, 'x1': 1149, 'y1': 841.9 - 164}]
})


# known issue: interleaved texts "EXAMPLE [J1b]" (and similar) due to line top being between two other lines
def collate_line(line_chars):  # adapted from pdfplumber.utils.collate_line
    result, text, font = [], "", None
    for char in sorted(line_chars, key=itemgetter("x1")):
        charfont = char["fontname"][7:]  # drop font name prefix like "FCVRLH+" or "XQWETX+"
        if font is None or hf4_font_to_markup[font] == hf4_font_to_markup[charfont] or char["text"] == ' ':
            text += char["text"]
        else:
            result.append((text, font))
            text = char["text"]
        font = font if char["text"] == " " else charfont
    result.append((text, font))
    return result


def add_bol_markup(text, fontname):
    heading1 = re.search(r"^[\s]*([1-3]?[A-Z])\.[\s]+", text)
    if heading1 or (text == "Glossary" and fontname == "MyriadPro-Bold"):
        anchor = text if heading1 is None else heading1.group(1)
        return "# " + text, " {#a" + anchor + "}"
    heading2 = re.search(r"^[\s]*([1-3]?[A-Z][0-9]+)\.[\s]+", text)
    if heading2:
        return "## " + text, " {#a" + heading2.group(1) + "}"
    ordered_list = re.search(r"^[\s]*([a-z1-9]\.)[\s]*", text)
    if ordered_list:
        return "\n" + add_markup(ordered_list.group(1) + " " + text[len(ordered_list.group(0)):], fontname), ""
    unordered_list = re.search(r"^[\s]*•[\s]+", text)
    if unordered_list:
        return "\n-  " + add_markup(text[len(unordered_list.group(0)):], fontname), ""
    if fontname == "MyriadPro-BoldCond":  # mark up examples as blockquote
        return "> " + add_markup(text, fontname), ""
    return add_markup(text, fontname), ""


def add_markup(text, fontname):
    if not text.strip():
        return text
    if fontname == "AstronomicSignsSt":
        return "".join([hf4_letter_to_starsign[ch] for ch in text])

    # hack to prevent marking up single full stops / parentheses etc (markdown does not like those)
    markup = "" if len(text.strip()) == 1 and not text.strip()[0].isalnum() else hf4_font_to_markup[fontname]
    pre = " " + markup if text[0] == " " else markup
    post = markup + " " if text[-1] == " " else markup
    inner = re.sub("(^|[^A-Za-z0-9])([1-3]?[A-Z][1-9][0-9]?)", r"\1[\2](#a\2)", text)  # add internal link - (A1)[#A1]
    return pre + inner.strip() + post


def is_within_rects(char, rects):
    return any([r["x0"] < char["x0"] < r["x1"] and r["x0"] < char["x1"] < r["x1"] and
                r["y0"] < char["y0"] < r["y1"] and r["y0"] < char["y1"] < r["y1"] for r in rects])


def extract_main_section(section, image_rects):  # TODO try improving VP table extraction
    markdown, last_y0 = "", -1
    for line_chars in pdfplumber.utils.cluster_objects(section.chars, "doctop", pdfplumber.utils.DEFAULT_Y_TOLERANCE):
        if is_within_rects(line_chars[0], image_rects):
            continue
        if last_y0 > 0 and line_chars[0]["y1"] + 3 < last_y0:  # start new paragraph
            markdown += "\n"
        collated_line = collate_line(line_chars)
        bol_markdown, maybe_anchor = add_bol_markup(collated_line[0][0], collated_line[0][1])
        markdown += bol_markdown
        for (text, fontname) in collated_line[1:]:
            markdown += add_markup(text, fontname)
        markdown += maybe_anchor + "\n"
        last_y0 = line_chars[0]["y0"]
    return markdown


def no_footnote(obj): return obj["object_type"] != "char" or obj["height"] >= 6 or obj["text"] == " "
def no_huge_text(obj): return obj["object_type"] != "char" or obj["height"] <= 20
def no_transparent_text(obj): return obj["object_type"] != "char" or len(obj["non_stroking_color"]) == 4


def extract_page(a4page, a4pagenum):
    if a4pagenum == 2 or (111 < a4pagenum < 203) or (226 < a4pagenum < 303) or (a4pagenum > 325):
        return ""  # exclude tables of contents, card descriptions, and essays

    footnote_hline_top = max([line["top"] for line in a4page.lines if line["width"] > 400], default=a4page.height)
    main_section_bbox = (hf4_margin_width, 0, a4page.width, footnote_hline_top) if a4pagenum % 2 == 0 \
        else (0, 0, a4page.width - hf4_margin_width, footnote_hline_top)
    main_section = a4page.within_bbox(main_section_bbox, relative=True)\
        .filter(no_footnote).filter(no_huge_text).filter(no_transparent_text)
    rects = [r for r in a4page.rects if r["linewidth"] > 0] + hf4_page_to_extra_rects[a4pagenum]

    page_comment = f"\n[comment{a4pagenum}]: # (page {a4pagenum})\n\n"
    print(page_comment)
    return page_comment + extract_main_section(main_section, rects)


if __name__ == "__main__":  # `pip3 freeze > requirements.txt` to export dependencies to file
    with open("hf4.md", "w", encoding="utf-8") as out:  # `pandoc hf4.md -o hf4.epub metadata.txt --toc-depth=2` to generate
        for docnum, doc in enumerate(hf4_input_files):
            with pdfplumber.open(doc) as pdf:
                for pagenum, page in enumerate(pdf.pages[1:-1]):  # exclude unnecessary first and last A4 pages
                    left = page.within_bbox((0, 0, 0.5 * float(page.width), page.height - 40))
                    out.write(extract_page(left, 2 * pagenum + 2 + 100 * docnum))
                    right = page.within_bbox((0.5 * float(page.width), 0, float(page.width), page.height - 40))
                    out.write(extract_page(right, 2 * pagenum + 3 + 100 * docnum))
