"""Etapa 7: o fluxo explícito do Nexus AI, orquestrado com LangGraph."""

import logging
import re
from typing import Annotated, TypedDict

from langchain_core.messages import AIMessage, AnyMessage, HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages

from nexus.config import Config
from nexus.prompts import AVALIAR, REFORMULAR, RESPONDER, formatar_trechos

log = logging.getLogger(__name__)


CITACAO = re.compile(r"\[(\d+)\]")
VEREDITOS = {
    "RESPONDER": "responder",
    "ESCLARECER": "esclarecer",
    "SEM_EVIDENCIA": "sem_evidencia",
}
MSG_SEM_EVIDENCIA = (
    "Não encontrei nos documentos disponíveis informação suficiente para "
    "responder com segurança. Documentos consultados: {docs}."
)
MSG_FALHA = "Não foi possível responder agora, por uma falha técnica. Tente de novo em instantes."


class EstadoNexus(TypedDict, total=False):
    messages: Annotated[
        list[AnyMessage], add_messages
    ]  # a conversa, acumulada entre turnos
    pergunta: str  # a pergunta deste turno, como o usuário escreveu
    consulta: str  # a pergunta reescrita, usada na busca
    trechos: list[dict]  # o que a recuperação devolveu
    decisao: str  # para onde o fluxo vai
    resposta: str
    fontes: list[str]
    tentativas: int  # quantas vezes o nó gerar já rodou neste turno
    erro: str


def construir_grafo(base, modelo, config: Config, checkpointer=None):

    def preparar(estado: EstadoNexus) -> dict:
        pergunta = estado["messages"][-1].content.strip()
        limpo = {
            "pergunta": pergunta,
            "consulta": pergunta,
            "trechos": [],
            "resposta": "",
            "fontes": [],
            "tentativas": 0,
            "erro": "",
        }
        if not pergunta or len(pergunta) > 1000:
            return {
                **limpo,
                "decisao": "invalida",
                "resposta": "Envie uma pergunta com texto, de até 1000 caracteres.",
            }
        return {**limpo, "decisao": "ok"}

    def reformular(estado: EstadoNexus) -> dict:
        anteriores = estado["messages"][:-1][-6:]
        if not anteriores:  # primeira pergunta: nada a reescrever
            return {}
        historico = "\n".join(
            f"{'Usuário' if m.type == 'human' else 'Nexus'}: {m.content}"
            for m in anteriores
        )
        try:
            r = modelo.invoke(
                [
                    SystemMessage(REFORMULAR),
                    HumanMessage(
                        f"Histórico:\n{historico}\n\nÚltima pergunta: {estado['pergunta']}"
                    ),
                ]
            )
        except Exception as e:  # sem reescrita, segue com a pergunta original  # noqa: BLE001
            log.warning("Reformulação falhou: %s", e)
            return {}
        return {"consulta": r.content.strip() or estado["pergunta"]}

    def recuperar(estado: EstadoNexus) -> dict:
        try:
            trechos = base.buscar(estado["consulta"], config.k)
        except Exception as e:
            log.exception("Falha na recuperação")
            return {"erro": f"recuperação: {type(e).__name__}"}
        return {"trechos": [t.como_dict() for t in trechos]}

    def avaliar(estado: EstadoNexus) -> dict:
        if estado.get("erro"):
            return {"decisao": "falha"}
        trechos = estado["trechos"]
        if not trechos or trechos[0]["similaridade"] < config.limiar:
            return {"decisao": "sem_evidencia"}  # nem chama o modelo
        try:
            r = modelo.invoke(
                [
                    SystemMessage(AVALIAR),
                    HumanMessage(
                        f"Trechos:\n{formatar_trechos(trechos)}\n\nPergunta: {estado['consulta']}"
                    ),
                ]
            )
        except Exception as e:  # noqa: BLE001
            return {"decisao": "falha", "erro": f"modelo: {type(e).__name__}"}
        palavras = r.content.strip().upper().split()
        veredito = palavras[0].strip(".:") if palavras else ""
        return {
            "decisao": VEREDITOS.get(veredito, "sem_evidencia")
        }  # inválido: conservador

    def gerar(estado: EstadoNexus) -> dict:
        aviso = ""
        if estado.get("tentativas", 0) > 0:
            aviso = (
                "\n\nA resposta anterior foi rejeitada por não citar corretamente os "
                "trechos. Cite o número do trecho, entre colchetes, após cada afirmação."
            )
        try:
            r = modelo.invoke(
                [
                    SystemMessage(RESPONDER),
                    HumanMessage(
                        f"Trechos:\n{formatar_trechos(estado['trechos'])}\n\n"
                        f"Pergunta: {estado['consulta']}{aviso}"
                    ),
                ]
            )
        except Exception as e:  # noqa: BLE001
            return {"decisao": "falha", "erro": f"modelo: {type(e).__name__}"}
        return {
            "resposta": r.content.strip(),
            "tentativas": estado.get("tentativas", 0) + 1,
        }

    def verificar(estado: EstadoNexus) -> dict:
        if estado.get("erro"):
            return {"decisao": "falha"}
        resposta, trechos = estado["resposta"], estado["trechos"]
        if "NAO_ENCONTREI" in resposta:
            return {"decisao": "sem_evidencia"}
        citados = {int(n) for n in CITACAO.findall(resposta)}
        if citados and all(1 <= n <= len(trechos) for n in citados):
            fontes = sorted({trechos[n - 1]["referencia"] for n in citados})
            return {"decisao": "respondida", "fontes": fontes}
        if estado["tentativas"] < config.max_tentativas:
            return {"decisao": "regenerar"}
        return {"decisao": "sem_evidencia"}

    def sem_evidencia(estado: EstadoNexus) -> dict:
        return {
            "resposta": MSG_SEM_EVIDENCIA.format(docs=", ".join(base.fontes)),
            "fontes": [],
        }

    def esclarecer(estado: EstadoNexus) -> dict:
        locais = sorted({t["referencia"] for t in estado["trechos"]})
        return {
            "resposta": "Sua pergunta pode se referir a assuntos diferentes. Encontrei "
            f"informações relacionadas em: {'; '.join(locais)}. "
            "Sobre qual assunto você quer saber?",
            "fontes": [],
        }

    def falha(estado: EstadoNexus) -> dict:
        log.error("Turno encerrado por falha: %s", estado.get("erro"))
        return {"resposta": MSG_FALHA, "fontes": []}

    def finalizar(estado: EstadoNexus) -> dict:
        texto = estado["resposta"]
        if estado.get("fontes"):
            texto += "\n\nFontes: " + "; ".join(estado["fontes"])
        return {"messages": [AIMessage(texto)]}

    g = StateGraph(EstadoNexus)
    for no in (
        preparar,
        reformular,
        recuperar,
        avaliar,
        gerar,
        verificar,
        sem_evidencia,
        esclarecer,
        falha,
        finalizar,
    ):
        g.add_node(no.__name__, no)

    g.add_edge(START, "preparar")
    g.add_conditional_edges(
        "preparar",
        lambda e: e["decisao"],
        {"ok": "reformular", "invalida": "finalizar"},
    )
    g.add_edge("reformular", "recuperar")
    g.add_edge("recuperar", "avaliar")
    g.add_conditional_edges(
        "avaliar",
        lambda e: e["decisao"],
        {
            "responder": "gerar",
            "esclarecer": "esclarecer",
            "sem_evidencia": "sem_evidencia",
            "falha": "falha",
        },
    )
    g.add_edge("gerar", "verificar")
    g.add_conditional_edges(
        "verificar",
        lambda e: e["decisao"],
        {
            "respondida": "finalizar",
            "regenerar": "gerar",
            "sem_evidencia": "sem_evidencia",
            "falha": "falha",
        },
    )
    for no in ("sem_evidencia", "esclarecer", "falha"):
        g.add_edge(no, "finalizar")
    g.add_edge("finalizar", END)
    return g.compile(checkpointer=checkpointer)


def perguntar(grafo, pergunta: str, sessao: str = "padrao") -> dict:
    """Executa um turno da conversa. 'sessao' separa conversas no checkpointer."""
    estado = grafo.invoke(
        {"messages": [HumanMessage(pergunta)]},
        config={
            "configurable": {"thread_id": sessao},
            "recursion_limit": 25,
            "run_name": "nexus-turno",
            "tags": ["nexus-ai"],
        },
    )
    return {
        chave: estado.get(chave)
        for chave in (
            "resposta",
            "decisao",
            "fontes",
            "trechos",
            "consulta",
            "tentativas",
            "erro",
        )
    }
