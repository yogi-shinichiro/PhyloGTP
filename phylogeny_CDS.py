"""Align CDS sequences and infer a tree using Linux or WSL tools."""
from pathlib import Path
from tool_runner import linux_path, run_tool
from settings import MAFFT_BIN, RAXML_BIN


def make_tree(gene):
    # Only a file basename is accepted; paths remain within the working folder.
    if not gene or gene in (".", "..") or any(c in gene for c in ("/", "\\", "\x00")):
        raise ValueError("遺伝子名にはファイルパスを指定できません。")
    folder = Path.cwd()
    input_fasta = folder / f"{gene}_CDS.fasta"
    clean_fasta = folder / f"{gene}_clean.fasta"
    aligned_fasta = folder / f"{gene}_aligned.fasta"
    prefix = folder / f"{gene}_tree"

    with input_fasta.open(encoding="utf-8") as fin, clean_fasta.open("w", encoding="utf-8") as fout:
        for line in fin:
            if line.startswith(">"):
                line = line.replace("organism=", "").replace(" ", "_")
            fout.write(line)

    print("===== Multiple Alignment (MAFFT) =====")
    run_tool([MAFFT_BIN, "--auto", linux_path(clean_fasta)],
             cwd=folder, output=aligned_fasta, timeout=3600)
    print("===== Phylogenetic Tree (RAxML-NG) =====")
    run_tool([RAXML_BIN, "--all", "--msa", linux_path(aligned_fasta),
              "--model", "GTR+G", "--bs-trees", "100", "--threads", "AUTO",
              "--prefix", linux_path(prefix), "--redo"], cwd=folder, timeout=86400)
    tree = Path(f"{prefix}.raxml.bestTree")
    if not tree.is_file():
        raise RuntimeError("系統樹の出力ファイルが見つかりません。")
    return str(tree)
