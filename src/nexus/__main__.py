"""Linha de comando do Nexus AI.


python -m Nexus buscar "pergunta"     só a recuperação, sem modelo de linguagem
python -m Nexus simples "pergunta"    Etapa 4: buscar e gerar, sem decisões
python -m Nexus agente "pergunta"     Etapa 5: agente do LangChain com ferramentas
python -m Nexus conversar             Etapa 6: o grafo, em uma conversa
python -m Nexus grafo                 imprime o grafo em Mermaid
"""

import argparse
import logging
import uuid

from langgraph.checkpoint.memory import InMemorySaver

from nexus.config import Config, criar_modelo
from nexus.ingestao import carregar_documentos, dividir_em_trechos
from nexus.recuperacao import BaseDocumental, EmbeddingsLocais


def montar_base(config: Config) -> BaseDocumental:
    documentos = carregar_documentos(config.pasta_documentos)
    trechos = dividir_em_trechos(documentos, config.tamanho_trecho, config.sobreposicao)
    base = BaseDocumental(trechos, EmbeddingsLocais(config.modelo_embeddings))
    print(
        f"Base pronta: {len(base.fontes)} documentos, {base.total_trechos} trechos.\n"
    )
    return base


def main():
    analisador = argparse.ArgumentParser(prog="Nexus", description="Nexus AI")
    sub = analisador.add_subparsers(dest="comando", required=True)
    for nome in ("buscar", "simples", "agente"):
        sub.add_parser(nome).add_argument("texto")
    sub.add_parser("conversar").add_argument("--detalhes", action="store_true")
    sub.add_parser("grafo")
    args = analisador.parse_args()
    logging.basicConfig(
        level=logging.WARNING, format="%(levelname)s %(name)s: %(message)s"
    )
    config = Config()

    if args.comando == "grafo":
        from nexus.grafo import construir_grafo

        print(construir_grafo(None, None, config).get_graph().draw_mermaid())
        return

    base = montar_base(config)

    if args.comando == "buscar":
        for i, t in enumerate(base.buscar(args.texto, config.k), start=1):
            print(f"[{i}] similaridade {t.similaridade}  {t.referencia()}")
            print("    " + t.texto.replace("\n", " ")[:300] + "\n")

    elif args.comando == "simples":
        from nexus.rag_simples import responder

        r = responder(args.texto, base, criar_modelo(config), config.k)
        for i, t in enumerate(r["trechos"], start=1):
            print(f"[{i}] {t['similaridade']}  {t['referencia']}")
        print("\nResposta:", r["resposta"])

    elif args.comando == "agente":
        from nexus.agente_langchain import criar_agente, perguntar

        print(perguntar(criar_agente(criar_modelo(config), base, config.k), args.texto))

    elif args.comando == "conversar":
        from nexus.grafo import construir_grafo, perguntar

        grafo = construir_grafo(base, criar_modelo(config), config, InMemorySaver())
        sessao = str(uuid.uuid4())
        print("Pergunte sobre os documentos. Digite 'sair' para encerrar.\n")
        while (pergunta := input("Você: ").strip()).lower() != "sair":
            r = perguntar(grafo, pergunta, sessao)
            print(f"\nNexus: {r['resposta']}")
            if r["fontes"]:
                print("Fontes:", "; ".join(r["fontes"]))
            if args.detalhes:
                print(
                    f"  decisão={r['decisao']}  consulta={r['consulta']!r}  "
                    f"tentativas={r['tentativas']}"
                )
                for t in r["trechos"] or []:
                    print(f"  {t['similaridade']}  {t['referencia']}")
            print()


if __name__ == "__main__":
    try:
        main()
    except (
        RuntimeError
    ) as erro:  # configuração ausente: mensagem curta, sem rastreamento
        raise SystemExit(f"Erro de configuração: {erro}")
