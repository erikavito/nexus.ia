"""Configuração do Nexus AI, lida de variáveis de ambiente."""

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


RAIZ = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Config:
    pasta_documentos: Path = Path(os.getenv("NEXUS_DOCUMENTOS", RAIZ / "documents"))
    modelo: str = os.getenv("NEXUS_MODELO", "openai/gpt-oss-20b")
    modelo_embeddings: str = os.getenv(
        "NEXUS_EMBEDDINGS",
        "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
    )
    tamanho_trecho: int = int(os.getenv("NEXUS_TAMANHO_TRECHO", "500"))
    sobreposicao: int = int(os.getenv("NEXUS_SOBREPOSICAO", "80"))
    k: int = int(os.getenv("NEXUS_K", "4"))
    limiar: float = float(os.getenv("NEXUS_LIMIAR", "0.40"))
    max_tentativas: int = int(os.getenv("NEXUS_MAX_TENTATIVAS", "2"))


def criar_modelo(config: Config):
    """Cria o modelo de linguagem. É o único ponto que conhece o fornecedor."""
    if not os.getenv("GROQ_API_KEY"):
        raise RuntimeError("Defina GROQ_API_KEY no ambiente ou no arquivo .env")
    from langchain_groq import ChatGroq

    return ChatGroq(
        model=config.modelo, temperature=0, max_tokens=1024, timeout=30, max_retries=2
    )
