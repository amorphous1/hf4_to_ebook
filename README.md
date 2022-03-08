# High Frontier 4 All Ebook Converter

A Python script that reads in the latest living rules PDFs for High Frontier 4 core rules, appendix, module 1 & 2, and outputs a Markdown file which can then be converted to epub/pdf/html or whatever.

Advantages:
- When living rules get updated, the script can just be re-run to quickly check what has changed.
- Automatically generates links for the numerous references to other sections like "(D2)", "(1B6e)" etc., which allows quickly jumping back and forth between sections on Kindle or within a PDF reader.
- Option to generate a table of contents with a configurable level of depth.

Drawbacks:
- Does not yet include conversion of images, footnotes, or margin text. This works as a quick reference, but would probably not convenient for a first read through the rules.
- The layout of the victory point table in section M2 is not yet converted nicely. There might be other smaller layout glitches.

## Getting started

- Needs a working Python installation including the [pdfplumber](https://github.com/jsvine/pdfplumber) module (`pip install pdfplumber`)
- Needs [Pandoc](https://pandoc.org) for conversion from the generated Markdown file to the desired output format

1. Download the latest [living rules files](https://docs.google.com/spreadsheets/d/1dt1g3XGxMcQPIij1uLAc-x9-TiZXiwHTX8-jYK-3hEg)
2. Edit variable `hf4_input_files` in `main.py` to contain the paths to the downloaded files in the desired order
3. Run the script to create a Markdown file: `python main.py` (this outputs the PDF page number it is currently on and can take a minute or two)
4. Use Pandoc to convert the Markdown file to the desired output format, for example
   - for epub: `pandoc hf4.md -o hf4.epub metadata.txt --toc-depth=2` (toc-depth is the desired depth for the table of contents)
   - for PDF: `pandoc hf4.md -o hf4.pdf metadata.txt --pdf-engine=xelatex --toc --toc-depth=1 -V geometry:margin=1in` (needs a [LaTeX installation](https://www.latex-project.org))
