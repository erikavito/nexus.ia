
import pytest
from langchain_core.documents import Document
from nexus.recuperacao import filtro_da_consulta, normalizar_texto

from nexus.ingestao import carregar_documentos, dividir_em_trechos


def test_carrega_documento_markdown(tmp_path):
    ficheiro = tmp_path / "regulamento.md"
    ficheiro.write_text(
        "# Regulamento\nO prazo é de cinco dias.",
        encoding="utf-8",
    )

    documentos = carregar_documentos(tmp_path)

    assert len(documentos) == 1
    assert documentos[0].metadata["fonte"] == "regulamento.md"
    assert documentos[0].metadata["pagina"] is None
    assert "cinco dias" in documentos[0].page_content


def test_divide_documento_em_trechos():
    documento = Document(
        page_content="Informação académica sobre avaliações. " * 20,
        metadata={"fonte": "exemplo.md", "pagina": None},
    )

    trechos = dividir_em_trechos(
        [documento],
        tamanho=80,
        sobreposicao=10,
    )

    assert len(trechos) > 1
    assert all(len(t.page_content) <= 80 for t in trechos)
    assert all(t.metadata["fonte"] == "exemplo.md" for t in trechos)
    assert all("id" in t.metadata for t in trechos)


def test_erro_quando_pasta_nao_tem_documentos(tmp_path):
    with pytest.raises(ValueError, match="Nenhum documento com texto"):
        carregar_documentos(tmp_path)


def test_normaliza_texto_com_acentos():
    assert normalizar_texto("Inteligência Artificial") == (
        "inteligencia artificial"
    )


def test_identifica_plano_da_disciplina():
    pergunta = (
        "Quais são as unidades temáticas da disciplina "
        "de Inteligência Artificial?"
    )

    assert filtro_da_consulta(pergunta) == {
        "fonte": "plano-inteligencia-artificial.pdf"
    }
