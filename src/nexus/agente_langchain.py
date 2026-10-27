"""Etapa 5: o mesmo assistente como agente do LangChain, que decide sozinho quando buscar."""

from langchain.agents import create_agent
from langchain_core.language_models import BaseChatModel

from nexus.ferramentas import criar_ferramentas
from nexus.prompts import AGENTE
from nexus.recuperacao import BaseDocumental


def criar_agente(modelo: BaseChatModel, base: BaseDocumental, k: int):
    """Devolve um grafo compilado: create_agent é construído sobre o LangGraph."""
    return create_agent(
        model=modelo, tools=criar_ferramentas(base, k), system_prompt=AGENTE
    )


def perguntar(agente, pergunta: str) -> str:
    resultado = agente.invoke(
        {"messages": [{"role": "user", "content": pergunta}]},
        config={"recursion_limit": 10},
    )
    return resultado["messages"][-1].content
