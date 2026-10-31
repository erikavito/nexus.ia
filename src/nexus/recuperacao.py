"""Etapa 3: transformar os trechos em vetores e buscar os mais parecidos com a pergunta."""

from dataclasses import dataclass

from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
import hashlib
import json
import math
from pathlib import Path
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
    """Adapta FastEmbed à interface Embeddings do LangChain."""

    def __init__(self, nome_modelo: str):
        from fastembed import TextEmbedding

        self.modelo = TextEmbedding(
            model_name=nome_modelo,
            threads=1
        )
        self.nome_modelo = nome_modelo

    def embed_documents(self, textos: list[str]) -> list[list[float]]:
        return [
            vetor.tolist()
            for vetor in self.modelo.embed(
                textos,
                batch_size=4,
                parallel=1
            )
        ]

    def embed_query(self, texto: str) -> list[float]:
        return self.embed_documents([texto])[0]

class BaseDocumental:
    def __init__(self, trechos: list[Document], embeddings: Embeddings):
        self.embeddings = embeddings
        self.documentos_indexados = trechos
        self.fontes = sorted({t.metadata["fonte"] for t in trechos})
        self.total_trechos = len(trechos)

        # Local onde o índice será salvo.
        raiz = Path(__file__).resolve().parents[2]
        self.pasta_cache = raiz / ".nexus_cache"
        self.arquivo_indice = self.pasta_cache / "indice.json"

        # Identifica se os documentos foram modificados.
        identificador = hashlib.sha256()

        for doc in trechos:
            identificador.update(doc.page_content.encode("utf-8"))
            identificador.update(
                str(doc.metadata.get("fonte", "")).encode("utf-8")
            )
            identificador.update(
                str(doc.metadata.get("pagina", "")).encode("utf-8")
            )

        self.fingerprint = identificador.hexdigest()
        self.modelo = getattr(embeddings, "nome_modelo", "")

        # Tenta reutilizar o índice salvo.
        if self._carregar_indice():
            print("Índice anterior carregado com sucesso!", flush=True)
        else:
            self._criar_indice()

    def _carregar_indice(self) -> bool:
        if not self.arquivo_indice.exists():
            return False

        try:
            with self.arquivo_indice.open("r", encoding="utf-8") as arquivo:
                dados = json.load(arquivo)

            if dados.get("fingerprint") != self.fingerprint:
                return False

            if dados.get("modelo") != self.modelo:
                return False

            self.itens = dados["itens"]

            if len(self.itens) != self.total_trechos:
                return False

            return True

        except (OSError, ValueError, KeyError, TypeError):
            return False

    def _criar_indice(self):
        self.itens = []

        print("Criando novo índice documental...", flush=True)

        for inicio in range(0, len(self.documentos_indexados), 2):
            lote = self.documentos_indexados[inicio:inicio + 2]

            vetores = self.embeddings.embed_documents(
                [doc.page_content for doc in lote]
            )

            for doc, vetor in zip(lote, vetores):
                self.itens.append({
                    "texto": doc.page_content,
                    "fonte": doc.metadata["fonte"],
                    "pagina": doc.metadata.get("pagina"),
                    "vetor": vetor,
                })

            print(
                f"Indexando: {len(self.itens)}/{self.total_trechos} trechos",
                flush=True
            )

        # Salva o índice para reutilização.
        self.pasta_cache.mkdir(parents=True, exist_ok=True)

        dados = {
            "fingerprint": self.fingerprint,
            "modelo": self.modelo,
            "itens": self.itens,
        }

        temporario = self.arquivo_indice.with_suffix(".tmp")

        with temporario.open("w", encoding="utf-8") as arquivo:
            json.dump(dados, arquivo, ensure_ascii=False)

        temporario.replace(self.arquivo_indice)

        print("Índice salvo com sucesso!", flush=True)

    @traceable(run_type="retriever", name="buscar_trechos")
    def buscar(self, consulta: str, k: int) -> list[Trecho]:
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

        if not self.itens:
            return []

        vetor_consulta = self.embeddings.embed_query(consulta)
        norma_consulta = math.sqrt(
            sum(valor * valor for valor in vetor_consulta)
        )

        pares = []

        for item in self.itens:
            if fonte_alvo and item["fonte"] != fonte_alvo:
                continue

            if fonte_alvo and consulta_de_conteudo:
                if item["pagina"] not in (1, 2, 3, "1", "2", "3"):
                    continue

            vetor = item["vetor"]

            norma_documento = math.sqrt(
                sum(valor * valor for valor in vetor)
            )

            if norma_consulta == 0 or norma_documento == 0:
                similaridade = 0.0
            else:
                produto = sum(
                    a * b for a, b in zip(vetor_consulta, vetor)
                )

                similaridade = produto / (
                    norma_consulta * norma_documento
                )

            pares.append((item, similaridade))

        pares.sort(key=lambda item: item[1], reverse=True)

        if not (fonte_alvo and consulta_de_conteudo):
            pares = pares[:k]

        return [
            Trecho(
                item["texto"],
                item["fonte"],
                item["pagina"],
                round(float(score), 3),
            )
            for item, score in pares
        ]
