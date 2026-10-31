# Nexus.IA — Assistente Virtual Acadêmico

O **Nexus.IA** é um assistente virtual inteligente desenvolvido para facilitar o acesso às informações acadêmicas por meio da inteligência artificial e da recuperação de informações em documentos institucionais.

O sistema permite que estudantes façam perguntas em linguagem natural e recebam respostas fundamentadas nos documentos disponibilizados na base de conhecimento, como planos de ensino, regulamentos, guias e políticas acadêmicas.

O objetivo é oferecer consultas mais simples e rápidas, com indicação das fontes utilizadas e evitando respostas sem evidências documentais.

---

## 1. Funcionalidades

- **Interface web:** interação com o assistente diretamente pelo navegador.
- **Chat com histórico:** mantém o contexto das mensagens durante a conversa.
- **Recuperação semântica:** localiza trechos relevantes nos documentos utilizando embeddings.
- **Respostas com fontes:** apresenta referências dos documentos utilizados na resposta.
- **Base documental:** consulta arquivos PDF, Markdown e TXT.
- **Índice persistente:** armazena localmente os vetores gerados para reutilizá-los em execuções futuras, quando os documentos e o modelo permanecem compatíveis.
- **Recarregamento de documentos:** permite atualizar a base documental pela interface web.
- **Agente inteligente:** utiliza ferramentas para realizar buscas nos documentos.
- **Fluxo com LangGraph:** avalia evidências, gera respostas, verifica citações e trata perguntas sem informações suficientes.
- **Avaliação de respostas:** disponibiliza casos de referência e avaliadores determinísticos.
- **Interface responsiva:** apresenta tema claro e escuro.

## 2. Tecnologias utilizadas

| Tecnologia | Aplicação |
|---|---|
| Python | Desenvolvimento principal |
| LangChain | Integração com modelos e ferramentas |
| LangGraph | Construção do fluxo de atendimento |
| LangSmith | Avaliação e acompanhamento de experimentos |
| Groq | Provedor do modelo de linguagem |
| FastEmbed | Geração local de embeddings |
| FastAPI | Desenvolvimento da API web |
| Uvicorn | Servidor da aplicação |
| HTML | Estrutura da interface |
| CSS | Estilização da interface |
| JavaScript | Interações e comunicação com a API |
| PyPDF | Leitura de documentos PDF |
| Pytest | Testes automatizados |
| Git e GitHub | Controle de versão |

## 3. Estrutura do projeto

```text
nexus.ia/
│
├── documents/
│   ├── guia-avaliacoes.pdf
│   ├── guia-de-atendimento.md
│   ├── manual-laboratorios.md
│   ├── perguntas-frequentes-academicas.md
│   ├── plano-big-data-e-ciencias-de-dados.pdf
│   ├── plano-design-de-interacao.pdf
│   ├── plano-economia.pdf
│   ├── plano-inteligencia-artificial.pdf
│   ├── plano-programacao-para-web.pdf
│   ├── plano-redes-de-computadores.pdf
│   ├── politica-estagio.pdf
│   ├── regulamento-biblioteca.md
│   └── sobre-assistente.md
│
├── src/
│   └── nexus/
│       ├── estatico/
│       │   ├── app.js
│       │   ├── estilo.css
│       │   ├── favicon.svg
│       │   └── index.html
│       │
│       ├── __init__.py
│       ├── __main__.py
│       ├── agente_langchain.py
│       ├── avaliacao.py
│       ├── config.py
│       ├── ferramentas.py
│       ├── grafo.py
│       ├── ingestao.py
│       ├── prompts.py
│       ├── rag_simples.py
│       ├── recuperacao.py
│       └── web.py
│
├── tests/
│   ├── test_ingestao.py
│   └── test_web.py
│
├── .env.example
├── .gitignore
├── pyproject.toml
└── README.md
```

### Principais módulos

- `__main__.py`: disponibiliza os comandos de execução do sistema.
- `config.py`: centraliza as configurações e a criação do modelo de linguagem.
- `ingestao.py`: realiza a leitura e divisão dos documentos em trechos.
- `recuperacao.py`: gera embeddings, cria o índice documental e realiza a busca semântica.
- `prompts.py`: contém as instruções utilizadas pelos componentes de inteligência artificial.
- `rag_simples.py`: implementa a recuperação de informações seguida da geração de respostas.
- `agente_langchain.py`: implementa o assistente com ferramentas de busca.
- `ferramentas.py`: disponibiliza ferramentas para consulta à base documental.
- `grafo.py`: organiza o fluxo de atendimento utilizando LangGraph.
- `avaliacao.py`: contém os casos de referência e os avaliadores.
- `web.py`: disponibiliza a API e o servidor da interface web.

## 4. Pré-requisitos

Para instalar e executar o projeto, é necessário:

- Python 3.10 ou superior.
- Git.
- Acesso à internet durante a instalação das dependências e o primeiro download do modelo de embeddings.
- Uma chave de API da Groq.

## 5. Instalação e configuração

### 5.1. Clonar o repositório

```bash
git clone https://github.com/erikavito/nexus.ia.git
```

### 5.2. Acessar a pasta

```bash
cd nexus.ia
```

### 5.3. Criar o ambiente virtual

```bash
python -m venv .venv
```

### 5.4. Ativar o ambiente virtual

**Linux / Chromebook:**

```bash
source .venv/bin/activate
```

**Windows:**

```bash
.venv\Scripts\activate
```

### 5.5. Instalar as dependências

```bash
pip install -e ".[dev]"
```

### 5.6. Configurar a chave de API

Crie um arquivo `.env` na raiz do projeto, seguindo o modelo `.env.example`.

Adicione sua chave:

```env
GROQ_API_KEY=sua_chave_aqui
```

A chave pode ser obtida em:

https://console.groq.com/keys

**Importante:** não compartilhe sua chave de API e não envie o arquivo `.env` para o GitHub.

Os embeddings são processados localmente com FastEmbed. O modelo é baixado na primeira utilização.

## 6. Como executar o projeto

### 6.1. Interface web

Com o ambiente virtual ativado, execute:

```bash
python -m nexus web
```

A aplicação estará disponível em:

```text
http://127.0.0.1:8000
```

Para abrir o navegador automaticamente:

```bash
python -m nexus web --abrir
```

Para escolher outra porta:

```bash
python -m nexus web --port 8080
```

### 6.2. Linha de comando

O projeto também permite utilizar o assistente diretamente pelo terminal.

| Comando | Funcionalidade |
|---|---|
| `python -m nexus buscar "pergunta"` | Realiza somente a recuperação de informações |
| `python -m nexus simples "pergunta"` | Recupera informações e gera uma resposta |
| `python -m nexus agente "pergunta"` | Executa o agente LangChain |
| `python -m nexus conversar` | Inicia uma conversa pelo terminal |
| `python -m nexus grafo` | Exibe o fluxo do grafo em Mermaid |
| `python -m nexus.avaliacao local` | Executa a avaliação local |

Para visualizar detalhes durante a conversa:

```bash
python -m nexus conversar --detalhes
```

## 7. Como funciona a recuperação de informações

O Nexus.IA utiliza uma abordagem de recuperação aumentada por geração (RAG).

O funcionamento ocorre nas seguintes etapas:

1. **Ingestão:** leitura dos documentos armazenados na pasta `documents/`.
2. **Divisão:** separação dos conteúdos em trechos menores.
3. **Vetorização:** transformação dos trechos em embeddings utilizando FastEmbed.
4. **Indexação:** armazenamento dos vetores e metadados em um índice local.
5. **Recuperação:** identificação dos trechos mais relevantes para a pergunta.
6. **Avaliação:** análise das evidências recuperadas.
7. **Geração:** construção da resposta utilizando o modelo de linguagem.
8. **Verificação:** conferência das citações e das evidências utilizadas.

O fluxo utiliza o LangGraph para organizar as decisões do assistente.

## 8. Índice documental persistente

Para evitar reconstruir todo o índice a cada execução, o projeto possui um mecanismo de armazenamento local.

O índice fica na pasta:

```text
.nexus_cache/
```

O sistema verifica a compatibilidade entre os documentos, o modelo de embeddings e o índice salvo.

Quando os dados permanecem compatíveis, o índice anterior é reutilizado. Caso contrário, um novo índice é construído.

Essa pasta é local e está protegida pelo `.gitignore`, portanto não precisa ser enviada ao GitHub.

## 9. API da interface web

A aplicação utiliza FastAPI para disponibilizar os seguintes endpoints:

| Método | Rota | Descrição |
|---|---|---|
| GET | `/api/estado` | Consulta o estado da aplicação e da base documental |
| GET | `/api/exemplos` | Retorna perguntas sugeridas |
| POST | `/api/conversa` | Envia uma pergunta ao assistente |
| POST | `/api/reiniciar` | Reinicia uma sessão de conversa |
| POST | `/api/documentos/recarregar` | Recarrega os documentos da base |
| GET | `/api/config` | Consulta as configurações efetivas |

A documentação interativa da API está disponível em:

```text
http://127.0.0.1:8000/api/docs
```

## 10. Adicionar novos documentos

Para acrescentar novos conteúdos à base de conhecimento:

1. Adicione arquivos PDF, Markdown (`.md`) ou texto (`.txt`) à pasta `documents/`.
2. Inicie a aplicação.
3. Utilize a opção **Recarregar documentos** na interface web.
4. Aguarde a preparação da nova base documental.

O sistema realiza novamente a leitura e a indexação dos conteúdos.

## 11. Configurações disponíveis

As configurações podem ser personalizadas por meio das variáveis de ambiente.

| Variável | Valor padrão | Descrição |
|---|---|---|
| `GROQ_API_KEY` | Obrigatória | Chave de acesso à Groq |
| `NEXUS_MODELO` | `openai/gpt-oss-20b` | Modelo de linguagem |
| `NEXUS_EMBEDDINGS` | `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` | Modelo de embeddings |
| `NEXUS_DOCUMENTOS` | `documents/` | Diretório dos documentos |
| `NEXUS_K` | `4` | Quantidade padrão de trechos recuperados |
| `NEXUS_LIMIAR` | `0.40` | Limiar de similaridade |
| `NEXUS_TAMANHO_TRECHO` | `500` | Tamanho dos trechos |
| `NEXUS_SOBREPOSICAO` | `80` | Sobreposição entre trechos |
| `NEXUS_MAX_TENTATIVAS` | `2` | Número máximo de tentativas de geração |

## 12. Avaliação e testes

O projeto possui testes automatizados na pasta `tests/`.

Para executar:

```bash
pytest
```

Para executar a avaliação local do assistente:

```bash
python -m nexus.avaliacao local
```

Para registrar um experimento no LangSmith:

```bash
python -m nexus.avaliacao langsmith
```

A avaliação pelo LangSmith também exige a configuração de `LANGSMITH_API_KEY`.

## 13. Limitações

- As respostas dependem dos documentos disponíveis na base de conhecimento.
- Informações que não possuem evidências documentais podem resultar em pedidos de esclarecimento ou indicação de ausência de evidências.
- Os embeddings são processados localmente, mas o modelo de linguagem depende da API da Groq.
- A interface web está configurada para uso local por padrão.
- A aplicação não possui autenticação de usuários implementada.

## 14. Repositório

**GitHub:** https://github.com/erikavito/nexus.ia

---

**Nexus.IA — Assistente Virtual Acadêmico**

*Conectando inteligência artificial e conhecimento acadêmico para facilitar o acesso à informação.*