"""Etapa 3: transformar os trechos em vetores e buscar os mais parecidos com a pergunta."""

from dataclasses import dataclass

from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_core.vectorstores import InMemoryVectorStore
from langsmith import traceable


@dataclass
class Trecho:
    texto: str
    fonte: str
    pagina: int | None
    similaridade: float

    def referencia(self) -> str:
        return f"{self.fonte}, p. {self.pagina}" if self.pagina else self.fonte

    def como_dict(self) -> dict:
        """Formato simples, que o estado do LangGraph consegue guardar e serializar."""
        return {
            "texto": self.texto,
            "referencia": self.referencia(),
            "similaridade": self.similaridade,
        }


class EmbeddingsLocais(Embeddings):
    """Adapta a biblioteca fastembed à interface Embeddings do LangChain.


    O modelo é baixado uma vez e roda no próprio computador, sem chave e sem custo
    por chamada. Qualquer outro provedor de embeddings que implemente a mesma
    interface pode substituir esta classe sem mudar o resto do projeto."""

    def __init__(self, nome_modelo: str):
        from fastembed import TextEmbedding

        self.modelo = TextEmbedding(model_name=nome_modelo)

    def embed_documents(self, textos: list[str]) -> list[list[float]]:
        return [vetor.tolist() for vetor in self.modelo.embed(textos)]

    def embed_query(self, texto: str) -> list[float]:
        return self.embed_documents([texto])[0]


class BaseDocumental:
    """Guarda os trechos e seus vetores em memória e responde a buscas."""

    def __init__(self, trechos: list[Document], embeddings: Embeddings):
        self.loja = InMemoryVectorStore(embedding=embeddings)
        self.loja.add_documents(trechos)
        self.fontes = sorted({t.metadata["fonte"] for t in trechos})
        self.total_trechos = len(trechos)

    @traceable(run_type="retriever", name="buscar_trechos")
    def buscar(self, consulta: str, k: int) -> list[Trecho]:
        """Devolve os k trechos mais similares, do mais para o menos similar."""
        if not consulta.strip():
            return []
        pares = self.loja.similarity_search_with_score(consulta, k=k)
        return [
            Trecho(
                doc.page_content,
                doc.metadata["fonte"],
                doc.metadata.get("pagina"),
                round(float(score), 3),
            )
            for doc, score in pares
        ]
