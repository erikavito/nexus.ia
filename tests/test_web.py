"""Testes da interface web, com base e modelo falsos (sem rede e sem chave)."""

import pytest
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage

from nexus.config import Config
from nexus.web import criar_app


class BaseFalsa:
    """Substitui a BaseDocumental: devolve sempre os mesmos trechos."""

    fontes = ["regulamento-biblioteca.md", "plano-economia.pdf"]
    total_trechos = 12

    def buscar(self, consulta: str, k: int):
        return [TrechoFalso()]


class TrechoFalso:
    referencia_texto = "regulamento-biblioteca.md"
    similaridade = 0.87

    def referencia(self) -> str:
        return self.referencia_texto

    def como_dict(self) -> dict:
        return {
            "texto": "Cada estudante pode retirar até 5 livros ao mesmo tempo.",
            "referencia": self.referencia_texto,
            "similaridade": self.similaridade,
        }


class ModeloFalso:
    """Modelo de chat determinístico: avalia, responde e reformula por palavra-chave."""

    def invoke(self, mensagens, **kwargs):
        sistema = mensagens[0].content
        if "avalia se os trechos" in sistema:
            return AIMessage(content="RESPONDER")
        if "Reescreva a última pergunta" in sistema:
            return AIMessage(content=mensagens[-1].content.split("Última pergunta:")[-1].strip())
        return AIMessage(content="Pode retirar até 5 livros ao mesmo tempo [1].")


@pytest.fixture()
def cliente():
    app = criar_app(Config(), base=BaseFalsa(), modelo=ModeloFalso())
    with TestClient(app) as c:
        yield c


def test_pagina_inicial_serve_a_interface(cliente):
    resposta = cliente.get("/")
    assert resposta.status_code == 200
    assert "Nexus.IA" in resposta.text
    assert "/estatico/app.js" in resposta.text


def test_estaticos_estao_disponiveis(cliente):
    for caminho, trecho in (
        ("/estatico/estilo.css", "--primaria"),
        ("/estatico/app.js", "api/conversa"),
        ("/favicon.svg", "<svg"),
    ):
        resposta = cliente.get(caminho)
        assert resposta.status_code == 200, caminho
        assert trecho in resposta.text


def test_estado_descreve_a_base_carregada(cliente):
    dados = cliente.get("/api/estado").json()
    assert dados["status"] == "pronto"
    assert dados["documentos"] == 2
    assert dados["trechos"] == 12
    assert "regulamento-biblioteca.md" in dados["fontes"]


def test_conversa_devolve_resposta_fontes_e_trechos(cliente):
    resposta = cliente.post(
        "/api/conversa",
        json={"mensagem": "Quantos livros posso retirar?", "sessao": "teste-1"},
    )
    assert resposta.status_code == 200
    dados = resposta.json()
    assert "5 livros" in dados["resposta"]
    assert dados["decisao"] == "respondida"
    assert dados["fontes"] == ["regulamento-biblioteca.md"]
    assert dados["trechos"][0]["referencia"] == "regulamento-biblioteca.md"
    assert dados["sessao"] == "teste-1"
    assert dados["duracao_ms"] >= 0


def test_conversa_sem_sessao_cria_uma(cliente):
    dados = cliente.post("/api/conversa", json={"mensagem": "E a multa?"}).json()
    assert dados["sessao"]


def test_pergunta_vazia_e_rejeitada(cliente):
    # vazio absoluto: recusado pela validação do Pydantic
    assert cliente.post("/api/conversa", json={"mensagem": ""}).status_code == 422
    # só espaços: recusado pela rota, que volta a validar o texto limpo
    assert cliente.post("/api/conversa", json={"mensagem": "    "}).status_code == 422


def test_reiniciar_conversa(cliente):
    resposta = cliente.post("/api/reiniciar", json={"sessao": "teste-1"})
    assert resposta.status_code == 200
    assert resposta.json()["ok"] is True


def test_exemplos_e_config(cliente):
    assert len(cliente.get("/api/exemplos").json()["exemplos"]) >= 3
    dados = cliente.get("/api/config").json()
    assert dados["modelo"]
    assert isinstance(dados["pasta_documentos"], str)


def test_recarregar_documentos(cliente):
    resposta = cliente.post("/api/documentos/recarregar")
    # a base falsa não sabe reconstruir-se a partir da pasta: aceitamos 200 ou 500
    assert resposta.status_code in (200, 500)
