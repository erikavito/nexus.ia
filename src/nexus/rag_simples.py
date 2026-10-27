"""Etapa 4: primeira versão. Recupera trechos e pede ao modelo uma resposta baseada neles.


Não há decisão nenhuma aqui: a sequência é sempre buscar e depois gerar.
"""
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from nexus.prompts import RESPONDER, formatar_trechos
from nexus.recuperacao import BaseDocumental


def responder(pergunta: str, base: BaseDocumental, modelo: BaseChatModel, k: int) -> dict:
    trechos = [t.como_dict() for t in base.buscar(pergunta, k)]          # recuperação
    mensagens = [SystemMessage(RESPONDER),
            HumanMessage(f"Trechos:\n{formatar_trechos(trechos)}\n\nPergunta: {pergunta}")]
    resposta = modelo.invoke(mensagens)                                   # geração
    return {"resposta": resposta.content, "trechos": trechos}


