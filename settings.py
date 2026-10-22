"""Local settings loaded from .env, with environment variables taking precedence."""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")

DATA_DIR = Path(os.getenv("PHYLOGPT_DATA_DIR", str(Path(__file__).resolve().parent))).resolve()

# Linux PATH used for analysis tools; on Windows this refers to paths inside WSL.
TOOL_PATH = os.getenv("PHYLOGPT_TOOL_PATH", "")
DATASETS_BIN = os.getenv("PHYLOGPT_DATASETS_BIN", "datasets")
MAFFT_BIN = os.getenv("PHYLOGPT_MAFFT_BIN", "mafft")
RAXML_BIN = os.getenv("PHYLOGPT_RAXML_BIN", "raxml-ng")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434").rstrip("/")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gemma3:4b")
OLLAMA_TIMEOUT_SECONDS = float(os.getenv("OLLAMA_TIMEOUT_SECONDS", "600"))


def configure_entrez():
    from Bio import Entrez
    Entrez.email = os.getenv("NCBI_EMAIL", "")
    Entrez.api_key = os.getenv("NCBI_API_KEY") or None
