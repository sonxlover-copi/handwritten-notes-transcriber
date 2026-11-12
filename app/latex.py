"""Build a safe LaTeX document and compile it to PDF with Tectonic."""

import re
import subprocess
import tempfile
from app.config import LATEX_COMPILER
from pathlib import Path

from app.transcriber import PageStructure

MATH_MARKER = re.compile(r"(\\\[.*?\\\]|\\\(.*?\\\)|\$\$.*?\$\$|\$.*?\$)", re.DOTALL)
COMMAND = re.compile(r"\\([A-Za-z]+|.)")

# Only mathematical commands are accepted from the model.
# Text outside math is escaped separately, so it cannot become LaTeX code.
SAFE_MATH_COMMANDS = {
    "alpha", "beta", "gamma", "delta", "epsilon", "varepsilon", "theta", "lambda",
    "mu", "nu", "pi", "rho", "sigma", "tau", "phi", "varphi", "omega", "Gamma",
    "Delta", "Sigma", "Omega", "frac", "sqrt", "ln", "log", "sin", "cos", "tan",
    "exp", "max", "min", "sup", "inf", "lim", "argmin", "argmax", "mathbb", "mathcal",
    "mathfrak", "mathbf", "boldsymbol", "mathrm", "operatorname", "text", "left", "right",
    "langle", "rangle", "lVert", "rVert", "Vert", "cdot", "times", "le", "ge", "neq",
    "approx", "in", "notin", "subset", "subseteq", "forall", "exists", "partial", "nabla",
    "top", "otimes", "oplus", "pm", "mp", "to", "mapsto", "ell", "infty", "quad",
    "qquad", "big", "Big", "bigg", "Bigg", "displaystyle", "limits",
}
SAFE_MATH_SYMBOLS = {r"\\", r"\,", r"\;", r"\!", r"\%", r"\{", r"\}", r"\|", r"\_"}


def escape_text(text: str) -> str:
    """Escape characters that have a special meaning in LaTeX text."""
    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    return "".join(replacements.get(char, char) for char in text)


def safe_math(expression: str) -> str:
    """Allow common math notation and replace unexpected TeX with a review marker."""
    expression = expression.strip().strip("$")
    if expression.startswith((r"\(", r"\[")) and expression.endswith((r"\)", r"\]")):
        expression = expression[2:-2].strip()
    if not expression or len(expression) > 1500:
        return r"\text{[формула требует проверки]}"

    for command in COMMAND.findall(expression):
        if command.isalpha() and command not in SAFE_MATH_COMMANDS:
            return r"\text{[формула требует проверки]}"
        if not command.isalpha() and "\\" + command not in SAFE_MATH_SYMBOLS:
            return r"\text{[формула требует проверки]}"

    # TeX treats unmatched or inverted braces as syntax, so reject broken math.
    brace_depth = 0
    for char in expression:
        if char == "{":
            brace_depth += 1
        elif char == "}":
            brace_depth -= 1
            if brace_depth < 0:
                return r"\text{[формула требует проверки]}"
    if brace_depth:
        return r"\text{[формула требует проверки]}"

    # Prevent TeX comments or parameter expansion in model-produced math.
    if "#" in expression or "%" in expression:
        return r"\text{[формула требует проверки]}"

    return expression


def render_text_with_math(text: str) -> str:
    """Escape prose while preserving explicitly marked math expressions."""
    parts = MATH_MARKER.split(text)
    rendered = []
    for part in parts:
        if not part:
            continue
        if MATH_MARKER.fullmatch(part):
            if part.startswith(("\\[", "$$")):
                expression = part[2:-2]
                rendered.append(r"\[" + safe_math(expression) + r"\]")
            else:
                expression = part[2:-2] if part.startswith(r"\(") else part[1:-1]
                rendered.append(r"\(" + safe_math(expression) + r"\)")
        else:
            # Keep the line structure of the source page.
            rendered.append(escape_text(part).replace("\n", r"\par " + "\n"))
    return "".join(rendered)


def render_block(block) -> str:
    """Turn one structured block into a small LaTeX fragment."""
    text = render_text_with_math(block.text)
    if block.kind == "heading":
        command = {1: "section*", 2: "subsection*", 3: "subsubsection*"}[block.level]
        return f"\\{command}{{{text}}}\n"
    if block.kind == "formula":
        return r"\[" + safe_math(block.text) + r"\]" + "\n"
    if block.kind == "list_item":
        # Numbered exercises already contain their own number in the transcription.
        if re.match(r"^\s*(\d+[.)]|\([а-яА-Я0-9]+\))", block.text):
            return r"\noindent " + text + r"\par" + "\n"
        return r"\noindent\textbullet\hspace{0.5em}" + text + r"\par" + "\n"
    return text + r"\par" + "\n"


def make_latex(pages: list[PageStructure], fallback_title: str) -> str:
    """Create a complete LaTeX source from page structures."""
    title = next((page.title for page in pages if page.title), fallback_title)
    body = [r"\begin{center}", r"{\LARGE\bfseries " + escape_text(title) + r"}\par", r"\end{center}"]

    for page_index, page in enumerate(pages):
        if page_index:
            body.append(r"\newpage")
            if page.title and page.title != title:
                body.append(r"\section*{" + escape_text(page.title) + "}")

        if page.metadata:
            metadata = r"\quad\textbullet\quad ".join(escape_text(item) for item in page.metadata)
            body.append(r"{\small " + metadata + r"}\\[0.8em]")

        for block in page.blocks:
            body.append(render_block(block))

    document_body = "\n".join(body)
    return rf"""\documentclass[12pt,a4paper]{{article}}
\usepackage{{fontspec}}
\usepackage{{amsmath,amssymb}}
\usepackage[margin=22mm]{{geometry}}
\setmainfont{{DejaVu Serif}}
\setlength{{\parindent}}{{0pt}}
\setlength{{\parskip}}{{6pt}}
\begin{{document}}
{document_body}
\end{{document}}
"""


def compile_pdf(latex_source: str) -> bytes:
    """Compile generated source in a temporary directory; never use a shell."""
    with tempfile.TemporaryDirectory(prefix="notes-tex-") as temp_dir:
        source_path = Path(temp_dir) / "document.tex"
        pdf_path = Path(temp_dir) / "document.pdf"
        source_path.write_text(latex_source, encoding="utf-8")

        result = subprocess.run(
            [LATEX_COMPILER, "--untrusted", "--keep-logs", source_path.name],
            cwd=temp_dir,
            capture_output=True,
            text=True,
            timeout=600,
            check=False,
        )
        if result.returncode != 0 or not pdf_path.exists():
            raise RuntimeError("Не удалось собрать PDF из LaTeX.")

        return pdf_path.read_bytes()
