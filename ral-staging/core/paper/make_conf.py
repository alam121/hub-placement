"""RA-L initial submission: ieeeconf conference format (letterpaper, 10 pt), built from the anonymized source."""
import subprocess
s = open("main_anon.tex").read()
s = s.replace("\\documentclass[letterpaper,journal]{IEEEtran}\n\\IEEEoverridecommandlockouts",
              "\\documentclass[letterpaper, 10 pt, conference]{ieeeconf}\n\\IEEEoverridecommandlockouts\n\\overrideIEEEmargins", 1)
s = s.replace("\\newtheorem{lemma}{Lemma}", "\\makeatletter\\@ifundefined{IEEEkeywords}{\\newenvironment{IEEEkeywords}"
              "{\\noindent\\textbf{\\textit{Index Terms}---}\\small\\bfseries}{\\par}}{}\\makeatother\n\\newtheorem{lemma}{Lemma}", 1)
open("main_conf_anon.tex", "w").write(s)
for _ in range(2):
    r = subprocess.run(["pdflatex", "-interaction=nonstopmode", "main_conf_anon.tex"], capture_output=True, text=True)
print([l for l in r.stdout.splitlines() if l.startswith(("Output", "Overfull", "!"))])
