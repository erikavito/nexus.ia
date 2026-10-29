"""Etapa 3: transformar os trechos em vetores e buscar os mais parecidos com a pergunta."""

from dataclasses import dataclass

from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_core.vectorstores import InMemoryVectorStore
from langsmith import traceable

import unicodedata

FONTES_POR_DISCIPLINA = {
    "redes de computadores": "plano-redes-de-computadores.pdf",
    "programacao para web": "plano-programacao-para-web.pdf",
    "inteligencia artificial": "plano-inteligencia-artificial.pdf",
    "economia": "plano-economia.pdf",
    "design de interacao": "plano-design-de-interacao.pdf",
    "big data e ciencias de dados": "plano-big-data-e-ciencias-de-dados.pdf",
    "ciencias de dados": "plano-big-data-e-ciencias-de-dados.pdf",
}



def normalizar_texto(texto: str) -> str:
    """Normaliza acentos, pontuação e espaços para comparar consultas."""
    texto = unicodedata.normalize("NFKD", texto.casefold())

    # Remove marcas de acentuação.
    texto = "".join(
        caractere
        for caractere in texto
        if not unicodedata.combining(caractere)
    )

    # Converte pontuação e espaços especiais em espaços normais.
    texto = "".join(
        caractere if caractere.isalnum() else " "
        for caractere in texto
    )

    # Remove espaços repetidos e nas extremidades.
    return " ".join(texto.split())



def filtro_da_consulta(consulta: str) -> dict | None:
    pergunta = normalizar_texto(consulta)

    for disciplina in sorted(
        FONTES_POR_DISCIPLINA,
        key=len,
        reverse=True,
    ):
        if disciplina in pergunta:
            return {"fonte": FONTES_POR_DISCIPLINA[disciplina]}

    return None



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

    def __init__(self, trechos: list[Document], embeddings: Embeddings):
        self.loja = InMemoryVectorStore(embedding=embeddings)

        # Adiciona os trechos à base vetorial.
        self.loja.add_documents(trechos)

        # Guarda os documentos e as informações da base.
        self.documentos_indexados = trechos
        self.fontes = sorted({t.metadata["fonte"] for t in trechos})
        self.total_trechos = len(trechos)



    @traceable(run_type="retriever", name="buscar_trechos")
    def buscar(self, consulta: str, k: int) -> list[Trecho]:
        """Busca trechos e aplica os filtros explicitamente."""
        if not consulta.strip():
            return []

        filtro_info = filtro_da_consulta(consulta)
        pergunta = normalizar_texto(consulta)
        fonte_alvo = filtro_info["fonte"] if filtro_info else None

        consulta_de_conteudo = any(
            termo in pergunta
            for termo in (
                "unidades tematicas",
                "conteudos programaticos",
                "topicos de cada unidade",
                "topicos da unidade",
                "topico da unidade",
                "topicos abordados na unidade",
                "topico abordado na unidade",
                "ementa",
            )
        )

        # Recupera os documentos sem depender do filtro do vector store.
        total = len(self.documentos_indexados)
        if total == 0:
            return []

        pares = self.loja.similarity_search_with_score(
            consulta,
            k=total,
        )

        # Aplica o filtro de fonte diretamente aos resultados.
        if fonte_alvo:
            pares = [
                (doc, score)
                for doc, score in pares
                if doc.metadata.get("fonte") == fonte_alvo
            ]

        # Para conteúdos programáticos, considera as páginas iniciais.
        if fonte_alvo and consulta_de_conteudo:
            paginas_permitidas = {1, 2, 3, "1", "2", "3"}
            pares = [
                (doc, score)
                for doc, score in pares
                if doc.metadata.get("pagina") in paginas_permitidas
            ]
        else:
            pares = pares[:k]

        # Mantém primeiro os resultados mais semelhantes.
        pares.sort(key=lambda item: float(item[1]), reverse=True)

        return [
            Trecho(
                doc.page_content,
                doc.metadata["fonte"],
                doc.metadata.get("pagina"),
                round(float(score), 3),
            )
            for doc, score in pares
        ]
