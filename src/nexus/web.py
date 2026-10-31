"""Etapa 9: interface web do Nexus AI.

Sobe um servidor local (FastAPI + Uvicorn) que serve uma interface de chat
para o mesmo grafo usado pela linha de comando. Nada do motor é duplicado:
o grafo, a base documental e o modelo vêm de `nexus.grafo` e `nexus.config`.

    python -m nexus web                 # http://127.0.0.1:8000
    python -m nexus web --port 8080     # outra porta
    python -m nexus web --abrir         # abre o navegador
"""

from __future__ import annotations

import contextlib
import logging
import threading
import time
import uuid
from dataclasses import asdict
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from nexus.config import Config

log = logging.getLogger(__name__)

PASTA_ESTATICA = Path(__file__).resolve().parent / "estatico"
TAMANHO_MAXIMO_PERGUNTA = 1000
TAMANHO_MAXIMO_MENSAGEM = 1000


# ------------------------------------------------------------------ esquemas


class PedidoConversa(BaseModel):
    mensagem: str = Field(min_length=1, max_length=TAMANHO_MAXIMO_MENSAGEM)
    sessao: str = Field(default="", max_length=80)


class PedidoReinicio(BaseModel):
    sessao: str = Field(default="", max_length=80)


# ------------------------------------------------------------------ estado


class EstadoNexus:
    """Carrega a base documental uma vez e guarda o grafo pronto para uso.

    O carregamento (que envolve ler PDFs e gerar embeddings) corre numa thread
    separada para que o servidor abra imediatamente: a interface mostra
    "a preparar a base" enquanto isso.
    """

    def __init__(self, config: Config, base=None, modelo=None):
        self.config = config
        self.base = base
        self.modelo = modelo
        self.grafo = None
        self.status = "carregando"
        self.erro: str | None = None
        self.iniciado_em: float | None = None
        self.pronto_em: float | None = None
        self._trava = threading.Lock()

    # -- carga ---------------------------------------------------------

    def preparar(self, em_segundo_plano: bool = True) -> None:
        if em_segundo_plano:
            threading.Thread(target=self._carregar, daemon=True).start()
        else:
            self._carregar()

    def _carregar(self) -> None:
        self.iniciado_em = time.perf_counter()
        try:
            if self.base is None:
                from nexus.__main__ import montar_base

                self.base = montar_base(self.config)
            if self.modelo is None:
                from nexus.config import criar_modelo

                self.modelo = criar_modelo(self.config)
            self.grafo = self._compilar()
            self.status = "pronto"
            self.pronto_em = time.perf_counter()
            log.info("Base pronta em %.1fs", self.pronto_em - self.iniciado_em)
        except Exception as erro:  # noqa: BLE001 — a interface precisa mostrar a causa
            self.status = "erro"
            self.erro = str(erro) or type(erro).__name__
            log.exception("Falha ao preparar a base")

    def _compilar(self):
        from langgraph.checkpoint.memory import InMemorySaver

        from nexus.grafo import construir_grafo

        return construir_grafo(self.base, self.modelo, self.config, InMemorySaver())

    def recarregar_base(self) -> None:
        """Relê a pasta de documentos (útil ao acrescentar planos novos)."""
        self.status = "carregando"
        self.erro = None
        self.base = None
        self._carregar()

    # -- consulta ------------------------------------------------------

    def exigir_pronto(self) -> None:
        if self.status == "pronto":
            return
        if self.status == "erro":
            raise HTTPException(status_code=503, detail=f"Base indisponível: {self.erro}")
        raise HTTPException(status_code=503, detail="A base documental ainda está a ser preparada.")

    @property
    def recursos(self) -> dict:
        base = self.base
        return {
            "documentos": len(base.fontes) if base else 0,
            "trechos": base.total_trechos if base else 0,
            "segundos": (
                round((self.pronto_em - self.iniciado_em), 1)
                if self.pronto_em and self.iniciado_em
                else None
            ),
        }


def sugestao_para(erro: str | None) -> str | None:
    """Traduz erros comuns de configuração numa indicação accionável."""
    if not erro:
        return None
    if "GROQ_API_KEY" in erro:
        return "Crie um ficheiro .env na raiz do projeto com GROQ_API_KEY=sua_chave."
    if "No module named" in erro:
        modulo = erro.split("No module named")[-1].strip(" '\"")
        return f"Falta a dependência '{modulo}'. Execute: pip install -e . (com o ambiente virtual ativo)."
    if "Nenhum documento" in erro:
        return "Coloque PDFs ou ficheiros Markdown na pasta documents/ e recarregue."
    return None


EXEMPLOS_PADRAO = [
    "Quantos livros posso retirar ao mesmo tempo na biblioteca?",
    "Qual é a jornada diária máxima do estágio?",
    "Quais são as unidades temáticas de Inteligência Artificial?",
    "Como peço a segunda chamada de uma avaliação?",
    "Que regras se aplicam ao uso de IA nos trabalhos?",
    "Qual é o horário de funcionamento dos laboratórios?",
]


# ------------------------------------------------------------------ aplicação


def criar_app(
    config: Config | None = None,
    base=None,
    modelo=None,
    em_segundo_plano: bool | None = None,
) -> FastAPI:
    """Cria a aplicação. `base` e `modelo` podem ser injetados nos testes."""
    config = config or Config()
    estado = EstadoNexus(config, base=base, modelo=modelo)

    @contextlib.asynccontextmanager
    async def ciclo(app: FastAPI):
        em_thread = estado.base is None if em_segundo_plano is None else em_segundo_plano
        estado.preparar(em_segundo_plano=em_thread)
        yield

    app = FastAPI(
        title="Nexus.IA",
        description="Assistente virtual académico — interface web",
        version="0.1.0",
        docs_url="/api/docs",
        redoc_url=None,
        lifespan=ciclo,
    )
    app.state.nexus = estado
    app.state.trava = threading.Lock()

    # -- páginas -------------------------------------------------------

    @app.get("/", include_in_schema=False)
    def inicio():
        return FileResponse(PASTA_ESTATICA / "index.html")

    @app.get("/favicon.svg", include_in_schema=False)
    def favicon():
        return FileResponse(PASTA_ESTATICA / "favicon.svg", media_type="image/svg+xml")

    # -- API -----------------------------------------------------------

    @app.get("/api/estado")
    def estado_api() -> dict:
        return {
            "status": estado.status,
            "erro": estado.erro,
            "sugestao": sugestao_para(estado.erro),
            "modelo": config.modelo,
            "embeddings": config.modelo_embeddings,
            "documentos": estado.recursos["documentos"],
            "trechos": estado.recursos["trechos"],
            "preparacao_segundos": estado.recursos["segundos"],
            "fontes": estado.base.fontes if estado.base else [],
            "limiar": config.limiar,
            "k": config.k,
        }

    @app.get("/api/exemplos")
    def exemplos_api() -> dict:
        return {"exemplos": EXEMPLOS_PADRAO}

    @app.post("/api/documentos/recarregar")
    def recarregar() -> dict:
        if estado.status == "carregando":
            raise HTTPException(status_code=409, detail="A base já está a ser preparada.")
        base_anterior = estado.base
        estado.recarregar_base()
        if estado.status == "erro":
            # volta ao estado anterior para não deixar a interface sem serviço
            estado.base = base_anterior
            estado.grafo = estado._compilar() if base_anterior and estado.modelo else estado.grafo
            estado.status = "pronto" if estado.grafo else "erro"
            raise HTTPException(status_code=500, detail=f"Falha ao recarregar: {estado.erro}")
        return {"ok": True, **estado.recursos}

    @app.post("/api/conversa")
    def conversa(pedido: PedidoConversa) -> JSONResponse:
        estado.exigir_pronto()
        pergunta = pedido.mensagem.strip()
        if not pergunta:
            raise HTTPException(status_code=422, detail="Envie uma pergunta com texto.")
        if len(pergunta) > TAMANHO_MAXIMO_PERGUNTA:
            raise HTTPException(
                status_code=422,
                detail=f"A pergunta deve ter até {TAMANHO_MAXIMO_PERGUNTA} caracteres.",
            )

        sessao = (pedido.sessao or "").strip() or str(uuid.uuid4())
        inicio = time.perf_counter()
        from nexus.grafo import perguntar

        try:
            with app.state.trava:  # um turno por vez: o checkpointer é partilhado
                resultado = perguntar(estado.grafo, pergunta, sessao)
        except Exception as erro:  # noqa: BLE001 — resposta de erro amigável
            log.exception("Falha ao responder")
            raise HTTPException(
                status_code=500, detail=f"Falha técnica ao responder: {type(erro).__name__}"
            ) from erro

        trechos = [
            {
                "referencia": t.get("referencia"),
                "similaridade": t.get("similaridade"),
                "texto": t.get("texto", ""),
            }
            for t in (resultado.get("trechos") or [])
        ]
        return JSONResponse(
            {
                "sessao": sessao,
                "pergunta": pergunta,
                "resposta": resultado.get("resposta") or "",
                "decisao": resultado.get("decisao"),
                "fontes": resultado.get("fontes") or [],
                "consulta": resultado.get("consulta"),
                "tentativas": resultado.get("tentativas") or 0,
                "trechos": trechos,
                "duracao_ms": round((time.perf_counter() - inicio) * 1000),
            }
        )

    @app.post("/api/reiniciar")
    def reiniciar(pedido: PedidoReinicio) -> dict:
        sessao = (pedido.sessao or "").strip()
        if sessao and estado.grafo is not None:
            try:
                estado.grafo.checkpointer.delete_thread(sessao)
            except Exception:  # noqa: BLE001 — apagar histórico é acessório
                log.warning("Não foi possível apagar a sessão %s", sessao)
        return {"ok": True, "sessao": sessao or str(uuid.uuid4())}

    @app.get("/api/config")
    def config_api() -> dict:
        dados = asdict(config)
        dados["pasta_documentos"] = str(dados["pasta_documentos"])
        return dados

    if PASTA_ESTATICA.is_dir():
        app.mount("/estatico", StaticFiles(directory=PASTA_ESTATICA), name="estatico")

    return app


def servidor(host: str = "127.0.0.1", porta: int = 8000, abrir: bool = False) -> None:
    """Arranca o servidor. Usado por `python -m nexus web`."""
    import uvicorn

    url = f"http://{host}:{porta}"
    print(f"\n  Nexus.IA — interface web em {url}")
    print("  A preparar a base documental... (Ctrl+C para parar)\n")
    if abrir:
        threading.Timer(1.5, lambda: __import__("webbrowser").open(url)).start()
    uvicorn.run(criar_app(), host=host, port=porta, log_level="warning")


if __name__ == "__main__":
    # Alternativa sem tocar na CLI:  python -m nexus.web [host] [porta]
    import sys

    servidor(
        host=sys.argv[1] if len(sys.argv) > 1 else "127.0.0.1",
        porta=int(sys.argv[2]) if len(sys.argv) > 2 else 8000,
    )
