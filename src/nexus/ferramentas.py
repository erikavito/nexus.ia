"""Etapa 6: ferramentas que o modelo pode pedir para usar.


As ferramentas são criadas dentro de uma função para receberem a base documental
já carregada, sem variáveis globais.
"""
from langchain.tools import tool

from nexus.recuperacao import BaseDocumental


def criar_ferramentas(base: BaseDocumental, k: int) -> list:


    @tool
    def buscar_documentos(consulta: str) -> str:
        """Busca nos documentos da faculdade os trechos mais relacionados à consulta.
        Use para qualquer pergunta sobre regras, prazos, horários ou procedimentos."""
        trechos = base.buscar(consulta[:500], k)
        if not trechos:
            return "Nenhum trecho encontrado."
        return "\n\n".join(f"Fonte: {t.referencia()} (similaridade {t.similaridade})\n{t.texto}"
                        for t in trechos)


    @tool
    def listar_documentos() -> str:
        """Lista os documentos disponíveis para consulta, com o total de trechos indexados."""
        return f"{len(base.fontes)} documentos, {base.total_trechos} trechos: " + \
            ", ".join(base.fontes)


    return [buscar_documentos, listar_documentos]
