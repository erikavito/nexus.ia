"""Etapa 2: carregar os documentos e dividi-los em trechos."""

import logging
from pathlib import Path

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pypdf import PdfReader

log = logging.getLogger(__name__)


def carregar_documentos(pasta: Path) -> list[Document]:
    """Lê os PDFs e Markdowns da pasta. Cada página de PDF vira um Document."""
    documentos = []
    for caminho in sorted(Path(pasta).iterdir()):
        sufixo = caminho.suffix.lower()
        if sufixo == ".pdf":
            leitor = PdfReader(caminho)
            for numero, pagina in enumerate(leitor.pages, start=1):
                texto = pagina.extract_text() or ""
                documentos.append(
                    Document(texto, metadata={"fonte": caminho.name, "pagina": numero})
                )
        elif sufixo in (".md", ".txt"):
            texto = caminho.read_text(encoding="utf-8")
            documentos.append(
                Document(texto, metadata={"fonte": caminho.name, "pagina": None})
            )
        else:
            log.warning("Ignorado, formato não suportado: %s", caminho.name)
    documentos = [d for d in documentos if d.page_content.strip()]
    if not documentos:
        raise ValueError(f"Nenhum documento com texto em {pasta}")
    return documentos


def dividir_em_trechos(
    documentos: list[Document], tamanho: int, sobreposicao: int
) -> list[Document]:
    """Divide em trechos de até 'tamanho' caracteres, com 'sobreposicao' entre vizinhos."""
    divisor = RecursiveCharacterTextSplitter(
        chunk_size=tamanho,
        chunk_overlap=sobreposicao,
        separators=["\n## ", "\n\n", "\n", ". ", " ", ""],
    )
    trechos = divisor.split_documents(documentos)
    for i, trecho in enumerate(trechos):
        trecho.metadata["id"] = f"{trecho.metadata['fonte']}#{i}"
    return trechos
