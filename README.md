# Nexus.IA — Assistente Virtual Académico

Assistente que responde a perguntas sobre a vida académica **usando apenas os
documentos da faculdade** (planos de ensino, regulamentos, guias e políticas).
Cada afirmação vem com a fonte citada; quando a resposta não está nos
documentos, o assistente diz isso em vez de inventar.

O projeto tem duas formas de uso: **interface web** (navegador) e **linha de
comando**.

---

## 1. Instalação

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

Crie um ficheiro `.env` na raiz do projeto:

```ini
GROQ_API_KEY=sua_chave_aqui
```

> A chave é gratuita em <https://console.groq.com/keys>.
> Os *embeddings* correm localmente com `fastembed` (o modelo é descarregado uma
> única vez, na primeira execução) — não precisam de chave nem de internet
> depois disso.

---

## 2. Interface web (recomendado)

```bash
python -m nexus web          # http://127.0.0.1:8000
python -m nexus web --abrir  # abre o navegador automaticamente
python -m nexus web --port 8080 --host 0.0.0.0
```

O que a interface oferece:

| Recurso | Onde |
|---|---|
| Chat com histórico da conversa | ecrã principal |
| Fontes de cada resposta (chips) | abaixo da resposta |
| Trechos recuperados, decisão do grafo, tempo e nº de tentativas | “N trechos recuperados” |
| Lista dos documentos indexados | barra lateral |
| Estado da base (documentos, trechos, modelo) | cartão na barra lateral |
| Recarregar documentos depois de os editar | botão na barra lateral |
| Nova conversa (limpa o contexto do grafo) | botão no topo |
| Tema claro/escuro (fica guardado no navegador) | botão no topo |
| Perguntas sugeridas | ecrã inicial |

Atalhos: **Enter** envia, **Shift+Enter** nova linha. Clicar numa citação `[1]`
abre os trechos que a sustentam.

### Endpoints (documentados em `/api/docs`)

| Método | Rota | Para quê |
|---|---|---|
| `GET` | `/api/estado` | estado da base, documentos, modelo, sugestão de correção |
| `GET` | `/api/exemplos` | perguntas sugeridas |
| `POST` | `/api/conversa` | `{ "mensagem": "...", "sessao": "..." }` → resposta, fontes, trechos |
| `POST` | `/api/reiniciar` | limpa o histórico de uma sessão |
| `POST` | `/api/documentos/recarregar` | relê `documents/` e reindexa |
| `GET` | `/api/config` | configuração efetiva (modelo, k, limiar) |

O mesmo grafo LangGraph da linha de comando é usado pela web — a interface não
duplica lógica, só a expõe por HTTP.

---

## 3. Linha de comando

```bash
python -m nexus web                    # interface web
python -m nexus buscar "pergunta"      # só a recuperação (sem LLM)
python -m nexus simples "pergunta"     # busca + geração, sem decisões
python -m nexus agente "pergunta"      # agente LangChain com ferramentas
python -m nexus conversar              # conversa no terminal (Ctrl+D sai)
python -m nexus grafo                  # imprime o fluxo em Mermaid
python -m nexus.avaliacao local        # casos de referência e avaliadores
```

---

## 4. Acrescentar documentos

1. Coloque PDFs, `.md` ou `.txt` em `documents/`.
2. Na interface web, clique em **Recarregar documentos**; na CLI, reinicie o
   comando.
3. O índice é reconstruído e o novo documento aparece na barra lateral.

Para respostas melhores, acrescente no topo de cada documento o nome da
disciplina ou do regulamento: o recuperador usa esse nome para filtrar.

---

## 5. Estrutura

```
src/nexus/
├── __main__.py        CLI (inclui o subcomando web)
├── config.py          configuração via .env
├── ingestao.py        leitura e divisão dos documentos
├── recuperacao.py     embeddings locais + busca com filtros
├── prompts.py         prompts do avaliador, do gerador e do agente
├── rag_simples.py     busca → geração, sem decisões
├── agente_langchain.py agente com ferramentas
├── grafo.py           grafo LangGraph (avaliar, gerar, verificar, citar)
├── avaliacao.py       casos de referência e avaliadores
├── web.py             API HTTP + servidor da interface
└── estatico/
    ├── index.html     ecrã de chat
    ├── estilo.css     tema claro/escuro e layout responsivo
    ├── app.js         fetching, markdown, citações, sessões
    └── favicon.svg
```

---

## 6. Como o grafo decide

```
preparar → reformular → recuperar → avaliar ─┬─ responder → gerar → verificar ─┬─ finalizar
                                             ├─ esclarecer ────────────────────┤
                                             └─ sem_evidência ─────────────────┘
```

- **recuperar** filtra pelo documento da disciplina quando a pergunta a nomeia.
- **avaliar** verifica se os trechos sustentam uma resposta; abaixo do limiar
  (`NEXUS_LIMIAR`, 0.40 por defeito) nem chega a chamar o modelo.
- **verificar** exige citação `[n]` válida; se faltar, regenera até
  `NEXUS_MAX_TENTATIVAS` e depois responde “não encontrei nos documentos”.

---

## 7. Configuração (`.env`)

| Variável | Por defeito | Efeito |
|---|---|---|
| `GROQ_API_KEY` | — | obrigatória |
| `NEXUS_MODELO` | `openai/gpt-oss-20b` | modelo de chat |
| `NEXUS_EMBEDDINGS` | `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` | modelo local |
| `NEXUS_DOCUMENTOS` | `documents/` | pasta indexada |
| `NEXUS_K` | `4` | trechos por resposta |
| `NEXUS_LIMIAR` | `0.40` | similaridade mínima |
| `NEXUS_TAMANHO_TRECHO` | `500` | caracteres por trecho |
| `NEXUS_SOBREPOSICAO` | `80` | sobreposição entre trechos |
| `NEXUS_MAX_TENTATIVAS` | `2` | regenerações permitidas |

---

## 8. Testes

```bash
pytest                        # ingestão + interface web (base e modelo falsos)
```

Os testes da web não precisam de chave nem de rede: injetam uma base e um
modelo falsos em `criar_app()`.

---

## 9. Limitações

- O assistente só confirma o que está nos documentos; não substitui os serviços
  académicos.
- Datas, prazos e notas devem ser sempre confirmados nos canais oficiais.
- A interface web é para uso local (`127.0.0.1`). Para a expor numa rede,
  acrescente autenticação e HTTPS — não há login implementado.
