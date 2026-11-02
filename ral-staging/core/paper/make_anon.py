"""Builds the double-anonymous review versions (main_anon.tex, supplement_anon.tex) from the named sources.
Removes authors, affiliations and the running-head names; the code citation points to an anonymized repository;
PDF metadata are cleared and then checked for identifying strings."""
import re, subprocess, sys

ANON_URL = "https://anonymous.4open.science/r/leakage-aware-staging-ral"
IDENT = re.compile(r"alam|rafique|kaust|lums|risc lab|syed|hamza|github\.com/alam", re.I)

s = open("main.tex").read()
a = s.index("\\author{"); b = s.index("\\markboth{")
s = s[:a] + "\\author{Anonymous Authors}\n" + s[b:]
s = re.sub(r"\\markboth\{([^}]*)\}\{[^:}]*:", r"\\markboth{\1}{Anonymous:", s)
s = re.sub(r"\\bibitem\{alam2026code\}[^\n]*",
           "\\\\bibitem{alam2026code} Anonymous, ``Code and data for leakage-aware robot staging (anonymized for review),'' 2026. [Online]. Available: " + ANON_URL, s)
s = s.replace("\\begin{document}", "\\hypersetup{pdfauthor={},pdftitle={},pdfsubject={},pdfkeywords={},pdfcreator={}}\n\\begin{document}", 1)
s = s.replace("alam2026code", "code2026")
open("main_anon.tex", "w").write(s)

t = open("supplement.tex").read()
t = re.sub(r"\\author\{[^}]*\}", r"\\author{Anonymous Authors}", t)
if "hyperref" in t:
    t = t.replace("\\begin{document}", "\\hypersetup{pdfauthor={},pdftitle={},pdfcreator={}}\n\\begin{document}", 1)
open("supplement_anon.tex", "w").write(t)

for f in ("main_anon", "supplement_anon"):
    for _ in range(2):
        subprocess.run(["pdflatex", "-interaction=nonstopmode", f + ".tex"], capture_output=True)
    txt = subprocess.run(["pdftotext", f + ".pdf", "-"], capture_output=True, text=True).stdout
    raw = open(f + ".pdf", "rb").read().decode("latin-1")
    info = subprocess.run(["pdfinfo", f + ".pdf"], capture_output=True, text=True).stdout
    hits = sorted(set(m.group(0) for m in IDENT.finditer(txt + raw + info)))
    pages = re.search(r"Pages:\s+(\d+)", info).group(1)
    print(f, "pages", pages, "identifying strings:", hits or "none")
    if hits:
        sys.exit(1)
