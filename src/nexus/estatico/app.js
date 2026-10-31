/* Nexus.IA — interface web (JavaScript sem dependências) */
(() => {
  "use strict";

  // ------------------------------------------------------------- constantes
  const API = {
    estado: "/api/estado",
    exemplos: "/api/exemplos",
    conversa: "/api/conversa",
    reiniciar: "/api/reiniciar",
    recarregar: "/api/documentos/recarregar",
  };

  const CHAVES = { tema: "nexus.tema", sessao: "nexus.sessao", historico: "nexus.historico" };
  const LIMITE_HISTORICO = 40;

  const ROTULOS_DECISAO = {
    respondida: "respondida",
    sem_evidencia: "sem evidência nos documentos",
    esclarecer: "pedido de esclarecimento",
    falha: "falha técnica",
    invalida: "pedido inválido",
  };

  // ---------------------------------------------------------------- estado
  const estado = {
    pronto: false,
    aEnviar: false,
    geracao: 0, // muda quando se começa uma conversa nova: descarta respostas atrasadas
    indicador: null,
    sessao: localStorage.getItem(CHAVES.sessao) || novaSessao(),
    historico: carregarHistorico(),
  };

  // ------------------------------------------------------------------- dom
  const $ = (seletor) => document.querySelector(seletor);
  const app = $("#app");
  const conversa = $("#conversa");
  const boasVindas = $("#boasVindas");
  const sugestoes = $("#sugestoes");
  const formulario = $("#formulario");
  const entrada = $("#entrada");
  const botaoEnviar = $("#botaoEnviar");
  const contadorCaracteres = $("#contadorCaracteres");
  const dicaRodape = $("#dicaRodape");
  const pastilhaStatus = $("#pastilhaStatus");
  const textoStatus = $("#textoStatus");
  const detalheEstado = $("#detalheEstado");
  const sugestaoErro = $("#sugestaoErro");
  const metricas = $("#metricas");
  const acoesEstado = $("#acoesEstado");
  const botaoRecarregar = $("#botaoRecarregar");
  const listaDocumentos = $("#listaDocumentos");
  const contadorFontes = $("#contadorFontes");
  const topoSubtitulo = $("#topoSubtitulo");
  const modeloMensagem = $("#modeloMensagem");

  // -------------------------------------------------------------- utilidades
  function novaSessao() {
    const id = (crypto.randomUUID && crypto.randomUUID()) || `s-${Date.now()}-${Math.random().toString(16).slice(2)}`;
    localStorage.setItem(CHAVES.sessao, id);
    return id;
  }

  function carregarHistorico() {
    try {
      const dados = JSON.parse(sessionStorage.getItem(CHAVES.historico) || "[]");
      return Array.isArray(dados) ? dados.slice(-LIMITE_HISTORICO) : [];
    } catch {
      return [];
    }
  }

  function guardarHistorico() {
    try {
      sessionStorage.setItem(CHAVES.historico, JSON.stringify(estado.historico.slice(-LIMITE_HISTORICO)));
    } catch {
      /* sessão cheia: histórico é acessório */
    }
  }

  function escapar(texto) {
    return String(texto).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  }

  function hora() {
    return new Date().toLocaleTimeString("pt-PT", { hour: "2-digit", minute: "2-digit" });
  }

  function notificar(mensagem, tipo = "info") {
    const alvo = $("#toasts");
    const toast = document.createElement("div");
    toast.className = "toast";
    toast.dataset.tipo = tipo;
    toast.textContent = mensagem;
    alvo.appendChild(toast);
    setTimeout(() => {
      toast.style.opacity = "0";
      toast.style.transform = "translateY(6px)";
      setTimeout(() => toast.remove(), 220);
    }, 4200);
  }

  // --------------------------------------------------------- markdown mínimo
  /** Converte o texto do modelo em HTML seguro: negrito, código, listas e citações. */
  function formatar(texto) {
    const linhas = escapar(texto).split(/\r?\n/);
    const partes = [];
    let lista = null; // "ul" | "ol"

    const fecharLista = () => {
      if (lista) {
        partes.push(`</${lista}>`);
        lista = null;
      }
    };

    const emLinha = (linha) =>
      linha
        .replace(/`([^`]+)`/g, "<code>$1</code>")
        .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
        .replace(/__([^_]+)__/g, "<strong>$1</strong>")
        .replace(/\[(\d+)\]/g, '<span class="citacao" title="Trecho $1 recuperado do documento">$1</span>');

    linhas.forEach((linha) => {
      const marcada = linha.match(/^\s*([-*•])\s+(.*)$/);
      const numerada = linha.match(/^\s*(\d+)[.)]\s+(.*)$/);
      const vazia = !linha.trim();

      if (marcada || numerada) {
        const tipo = marcada ? "ul" : "ol";
        if (lista !== tipo) {
          fecharLista();
          partes.push(`<${tipo}>`);
          lista = tipo;
        }
        partes.push(`<li>${emLinha((marcada || numerada)[2])}</li>`);
        return;
      }

      fecharLista();
      if (vazia) {
        partes.push("");
        return;
      }
      partes.push(`<p>${emLinha(linha)}</p>`);
    });

    fecharLista();
    return partes.join("\n").replace(/\n{2,}/g, "\n");
  }

  // ------------------------------------------------------------- render chat
  function rolarParaFim(suave = true) {
    requestAnimationFrame(() => {
      conversa.scrollTo({ top: conversa.scrollHeight, behavior: suave ? "smooth" : "auto" });
    });
  }

  function esconderBoasVindas() {
    if (boasVindas && boasVindas.isConnected) boasVindas.remove();
  }

  function criarMensagem({ autor, texto, meta = {}, html = null, horaTexto = hora() }) {
    const fragmento = modeloMensagem.content.cloneNode(true);
    const artigo = fragmento.querySelector(".mensagem");
    artigo.dataset.autor = autor;

    const avatar = fragmento.querySelector(".avatar");
    avatar.textContent = autor === "nexus" ? "N" : "EU";
    if (autor === "nexus") avatar.classList.add("avatar-nexus");

    fragmento.querySelector(".autor").textContent = autor === "nexus" ? "Nexus.IA" : "Você";
    fragmento.querySelector(".hora").textContent = horaTexto;

    const corpo = fragmento.querySelector(".texto-mensagem");
    corpo.innerHTML = html !== null ? html : formatar(texto);

    return { fragmento, artigo, corpo, recursos: fragmento.querySelector(".recursos-mensagem"), acoes: fragmento.querySelector(".acoes-mensagem"), meta };
  }

  function acoesDeResposta(resultado, htmlResposta) {
    const acoes = document.createDocumentFragment();

    const copiar = document.createElement("button");
    copiar.type = "button";
    copiar.className = "acao";
    copiar.innerHTML = `<svg viewBox="0 0 24 24"><rect x="9" y="9" width="11" height="11" rx="2"/><path d="M15 5H6a1 1 0 0 0-1 1v9"/></svg>Copiar`;
    copiar.addEventListener("click", async () => {
      try {
        await navigator.clipboard.writeText(resultado.resposta);
        copiar.lastChild.textContent = "Copiado";
        setTimeout(() => (copiar.lastChild.textContent = "Copiar"), 1600);
      } catch {
        notificar("Não foi possível copiar neste navegador.", "erro");
      }
    });
    acoes.appendChild(copiar);

    void htmlResposta;
    return acoes;
  }

  function detalhesTecnicos(resultado) {
    const detalhes = document.createElement("details");
    detalhes.className = "detalhes";

    const trechos = resultado.trechos || [];
    detalhes.innerHTML = `
      <summary>
        <svg class="seta" viewBox="0 0 24 24"><path d="M9 6l6 6-6 6"/></svg>
        ${trechos.length ? `${trechos.length} ${trechos.length === 1 ? "trecho recuperado" : "trechos recuperados"}` : "Detalhes da consulta"}
      </summary>`;

    const conteudo = document.createElement("div");
    conteudo.className = "conteudo-detalhes";

    const info = document.createElement("div");
    info.className = "linha-info";
    const decisao = resultado.decisao || "—";
    info.innerHTML = `
      <span class="etiqueta" data-decisao="${escapar(decisao)}">${escapar(ROTULOS_DECISAO[decisao] || decisao)}</span>
      <span class="etiqueta">consulta: ${escapar(resultado.consulta || resultado.pergunta || "")}</span>
      ${resultado.duracao_ms ? `<span class="etiqueta">${(resultado.duracao_ms / 1000).toFixed(1)}s</span>` : ""}
      ${resultado.tentativas > 1 ? `<span class="etiqueta">${resultado.tentativas} tentativas</span>` : ""}`;
    conteudo.appendChild(info);

    trechos.forEach((trecho, i) => {
      const caixa = document.createElement("div");
      caixa.className = "trecho";
      const sim = typeof trecho.similaridade === "number" ? trecho.similaridade.toFixed(3) : "—";
      caixa.innerHTML = `
        <header><span class="ref">[${i + 1}] ${escapar(trecho.referencia || "")}</span><span class="sim">similaridade ${sim}</span></header>
        <p>${escapar((trecho.texto || "").replace(/\s+/g, " ")).slice(0, 700)}</p>`;
      conteudo.appendChild(caixa);
    });

    detalhes.appendChild(conteudo);
    return detalhes;
  }

  function adicionarMensagem(entradaMensagem) {
    esconderBoasVindas();
    const construida = criarMensagem(entradaMensagem);
    const { fragmento, artigo, recursos, acoes, meta } = construida;

    if (meta && meta.resultado) {
      const resultado = meta.resultado;
      if (resultado.fontes && resultado.fontes.length) {
        const bloco = document.createElement("div");
        bloco.className = "fontes";
        bloco.innerHTML = `<span class="rotulo">Fontes</span>`;
        resultado.fontes.forEach((fonte) => {
          const chip = document.createElement("span");
          chip.className = "fonte-chip";
          chip.innerHTML = `<svg viewBox="0 0 24 24"><path d="M4 5h9l3 3h4v11H4z"/></svg>${escapar(fonte)}`;
          bloco.appendChild(chip);
        });
        recursos.appendChild(bloco);
      }
      recursos.appendChild(detalhesTecnicos(resultado));
      acoes.appendChild(acoesDeResposta(resultado, construida.corpo.innerHTML));
    }

    conversa.appendChild(fragmento);
    rolarParaFim();
    return artigo;
  }

  function adicionarErro(mensagem) {
    const caixa = document.createElement("div");
    caixa.className = "erro-mensagem";
    caixa.textContent = mensagem;
    conversa.appendChild(caixa);
    rolarParaFim();
  }

  function indicadorEscrita() {
    esconderBoasVindas();
    const construida = criarMensagem({ autor: "nexus", texto: "", html: "" });
    construida.corpo.innerHTML = `<div class="escrevendo"><span></span><span></span><span></span></div>`;
    conversa.appendChild(construida.fragmento);
    rolarParaFim();
    return construida.artigo;
  }

  // ------------------------------------------------------------------ envio
  function atualizarBotao() {
    const vazio = !entrada.value.trim();
    botaoEnviar.disabled = estado.aEnviar || vazio || !estado.pronto;
    if (!estado.pronto && !estado.aEnviar) {
      dicaRodape.textContent = "A base documental está a ser preparada…";
      dicaRodape.classList.add("erro");
    } else {
      dicaRodape.textContent = "Respostas com base nos documentos indexados";
      dicaRodape.classList.remove("erro");
    }
  }

  function ajustarAltura() {
    entrada.style.height = "auto";
    entrada.style.height = `${Math.min(entrada.scrollHeight, 168)}px`;
  }

  /** Extrai uma frase legível do campo `detail` (texto ou lista de erros do Pydantic). */
  function mensagemDeErro(dados) {
    if (!dados) return "";
    const detalhe = dados.detail;
    if (typeof detalhe === "string") return detalhe;
    if (Array.isArray(detalhe) && detalhe.length) {
      return detalhe.map((d) => d.msg || d.detail || "").filter(Boolean).join(" ");
    }
    return "";
  }

  async function enviar(pergunta) {
    const texto = (pergunta || entrada.value).trim();
    if (!texto || estado.aEnviar) return;

    if (!estado.pronto) {
      notificar("A base documental ainda está a ser preparada. Tente em instantes.", "erro");
      return;
    }

    estado.aEnviar = true;
    entrada.value = "";
    ajustarAltura();
    contadorCaracteres.textContent = "0 / 1000";
    atualizarBotao();

    const geracao = estado.geracao;
    const mensagemUtilizador = { autor: "utilizador", texto };
    adicionarMensagem(mensagemUtilizador);
    estado.historico.push(mensagemUtilizador);
    guardarHistorico();

    const indicador = indicadorEscrita();
    estado.indicador = indicador;

    try {
      const resposta = await fetch(API.conversa, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ mensagem: texto, sessao: estado.sessao }),
      });

      const dados = await resposta.json().catch(() => ({}));

      if (!resposta.ok) {
        throw new Error(mensagemDeErro(dados) || `O servidor respondeu ${resposta.status}.`);
      }

      if (geracao !== estado.geracao) return; // a conversa foi reiniciada entretanto

      estado.sessao = dados.sessao || estado.sessao;
      localStorage.setItem(CHAVES.sessao, estado.sessao);

      indicador.remove();
      estado.indicador = null;
      const mensagemNexus = {
        autor: "nexus",
        texto: dados.resposta || "(sem resposta)",
        meta: { resultado: dados },
      };
      adicionarMensagem(mensagemNexus);
      estado.historico.push(mensagemNexus);
      guardarHistorico();
    } catch (erro) {
      if (geracao !== estado.geracao) return;
      indicador.remove();
      estado.indicador = null;
      adicionarErro(`Não foi possível obter a resposta: ${erro.message}`);
      notificar("Falha ao contactar o servidor.", "erro");
    } finally {
      if (geracao === estado.geracao) {
        estado.aEnviar = false;
        atualizarBotao();
        entrada.focus();
      }
    }
  }

  // -------------------------------------------------------- estado / fontes
  function pintarEstado(dados) {
    const status = dados.status || "carregando";
    pastilhaStatus.dataset.status = status;
    textoStatus.textContent =
      status === "pronto" ? "Base pronta" : status === "erro" ? "Erro na base" : "A preparar a base…";

    if (status === "pronto") {
      sugestaoErro.hidden = true;
      detalheEstado.textContent = `${dados.documentos} documentos · ${dados.trechos} trechos indexados${
        dados.preparacao_segundos ? ` em ${dados.preparacao_segundos}s` : ""
      }.`;
      metricas.hidden = false;
      $("#metricaDocumentos").textContent = dados.documentos;
      $("#metricaTrechos").textContent = dados.trechos;
      $("#metricaModelo").textContent = dados.modelo || "—";
      $("#metricaModelo").title = dados.modelo || "";
      acoesEstado.hidden = false;
      estado.pronto = true;
      pintarDocumentos(dados.fontes || []);
      topoSubtitulo.textContent = `Pergunte sobre ${dados.documentos} documentos oficiais da faculdade.`;
    } else if (status === "erro") {
      detalheEstado.textContent = dados.erro || "Não foi possível preparar a base documental.";
      if (dados.sugestao) {
        sugestaoErro.textContent = dados.sugestao;
        sugestaoErro.hidden = false;
      } else {
        sugestaoErro.hidden = true;
      }
      metricas.hidden = true;
      acoesEstado.hidden = false;
      estado.pronto = false;
    } else {
      sugestaoErro.hidden = true;
      detalheEstado.textContent = "A ler os documentos e a criar o índice de pesquisa.";
      estado.pronto = false;
    }
    atualizarBotao();
  }

  function pintarDocumentos(fontes) {
    listaDocumentos.innerHTML = "";
    contadorFontes.textContent = fontes.length;
    fontes.forEach((fonte) => {
      const tipo = (fonte.split(".").pop() || "").toLowerCase();
      const item = document.createElement("li");
      item.innerHTML = `<span class="tipo" data-tipo="${escapar(tipo)}">${escapar(tipo.slice(0, 4).toUpperCase())}</span><span class="nome" title="${escapar(fonte)}">${escapar(fonte)}</span>`;
      listaDocumentos.appendChild(item);
    });
    if (!fontes.length) {
      listaDocumentos.innerHTML = `<li><span class="nome">Nenhum documento indexado.</span></li>`;
    }
  }

  async function consultarEstado() {
    try {
      const resposta = await fetch(API.estado, { cache: "no-store" });
      if (!resposta.ok) throw new Error(`HTTP ${resposta.status}`);
      const dados = await resposta.json();
      pintarEstado(dados);
      return dados.status === "carregando";
    } catch {
      pastilhaStatus.dataset.status = "erro";
      textoStatus.textContent = "Servidor indisponível";
      detalheEstado.textContent = "Não foi possível falar com o servidor local.";
      estado.pronto = false;
      atualizarBotao();
      return false;
    }
  }

  async function vigiarEstado() {
    let continuar = await consultarEstado();
    while (continuar) {
      await new Promise((r) => setTimeout(r, 2000));
      continuar = await consultarEstado();
    }
  }

  async function carregarExemplos() {
    try {
      const resposta = await fetch(API.exemplos, { cache: "no-store" });
      if (!resposta.ok) return;
      const { exemplos } = await resposta.json();
      sugestoes.innerHTML = "";
      (exemplos || []).forEach((exemplo) => {
        const botao = document.createElement("button");
        botao.type = "button";
        botao.className = "sugestao";
        botao.textContent = exemplo;
        botao.addEventListener("click", () => {
          entrada.value = exemplo;
          ajustarAltura();
          atualizarBotao();
          enviar(exemplo);
        });
        sugestoes.appendChild(botao);
      });
    } catch {
      /* sugestões são acessórias */
    }
  }

  // ------------------------------------------------------------- ações topo
  async function novaConversa() {
    try {
      await fetch(API.reiniciar, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ sessao: estado.sessao }),
      });
    } catch {
      /* mesmo sem servidor, limpamos a vista */
    }
    // descarta turnos em voo: uma resposta atrasada não deve cair na conversa nova
    estado.geracao += 1;
    estado.aEnviar = false;
    if (estado.indicador) {
      estado.indicador.remove();
      estado.indicador = null;
    }
    estado.sessao = novaSessao();
    estado.historico = [];
    guardarHistorico();
    conversa.querySelectorAll(".mensagem, .erro-mensagem, .boas-vindas").forEach((n) => n.remove());
    conversa.appendChild(boasVindas);
    rolarParaFim(false);
    atualizarBotao();
    entrada.focus();
    notificar("Nova conversa iniciada.", "ok");
  }

  async function recarregarDocumentos() {
    botaoRecarregar.disabled = true;
    botaoRecarregar.textContent = "A recarregar…";
    try {
      const resposta = await fetch(API.recarregar, { method: "POST" });
      const dados = await resposta.json().catch(() => ({}));
      if (!resposta.ok) throw new Error(dados.detail || `HTTP ${resposta.status}`);
      notificar(`Base recarregada: ${dados.documentos} documentos, ${dados.trechos} trechos.`, "ok");
      await consultarEstado();
    } catch (erro) {
      notificar(`Falha ao recarregar: ${erro.message}`, "erro");
    } finally {
      botaoRecarregar.disabled = false;
      botaoRecarregar.textContent = "Recarregar documentos";
    }
  }

  // ------------------------------------------------------------------- tema
  function aplicarTema(tema) {
    document.documentElement.dataset.tema = tema;
    localStorage.setItem(CHAVES.tema, tema);
  }

  // -------------------------------------------------------------- arranque
  function restaurarHistorico() {
    if (!estado.historico.length) return;
    boasVindas.remove();
    estado.historico.forEach((item) => {
      const construida = criarMensagem(item);
      if (item.meta && item.meta.resultado) {
        const resultado = item.meta.resultado;
        if (resultado.fontes && resultado.fontes.length) {
          const bloco = document.createElement("div");
          bloco.className = "fontes";
          bloco.innerHTML = `<span class="rotulo">Fontes</span>`;
          resultado.fontes.forEach((fonte) => {
            const chip = document.createElement("span");
            chip.className = "fonte-chip";
            chip.innerHTML = `<svg viewBox="0 0 24 24"><path d="M4 5h9l3 3h4v11H4z"/></svg>${escapar(fonte)}`;
            bloco.appendChild(chip);
          });
          construida.recursos.appendChild(bloco);
        }
        construida.recursos.appendChild(detalhesTecnicos(resultado));
      }
      conversa.appendChild(construida.fragmento);
    });
    rolarParaFim(false);
  }

  function ligarEventos() {
    $("#botaoTema").addEventListener("click", () => {
      const atual = document.documentElement.dataset.tema === "claro" ? "escuro" : "claro";
      aplicarTema(atual);
    });

    $("#abrirLateral").addEventListener("click", () => (app.dataset.lateral = "aberta"));
    $("#fecharLateral").addEventListener("click", () => (app.dataset.lateral = "fechada"));
    $("#veu").addEventListener("click", () => (app.dataset.lateral = "fechada"));

    $("#botaoNovaConversa").addEventListener("click", novaConversa);
    botaoRecarregar.addEventListener("click", recarregarDocumentos);

    formulario.addEventListener("submit", (evento) => {
      evento.preventDefault();
      enviar();
    });

    entrada.addEventListener("keydown", (evento) => {
      if (evento.key === "Enter" && !evento.shiftKey && !evento.isComposing) {
        evento.preventDefault();
        enviar();
      }
    });

    entrada.addEventListener("input", () => {
      contadorCaracteres.textContent = `${entrada.value.length} / 1000`;
      ajustarAltura();
      atualizarBotao();
    });

    conversa.addEventListener("click", (evento) => {
      const citacao = evento.target.closest(".citacao");
      if (!citacao) return;
      const detalhes = citacao.closest(".mensagem")?.querySelector(".detalhes");
      if (detalhes) {
        detalhes.open = true;
        detalhes.scrollIntoView({ block: "nearest", behavior: "smooth" });
      }
    });

    window.addEventListener("resize", () => {
      if (window.innerWidth > 860) app.dataset.lateral = "fechada";
    });
  }

  async function iniciar() {
    aplicarTema(localStorage.getItem(CHAVES.tema) || (window.matchMedia("(prefers-color-scheme: light)").matches ? "claro" : "escuro"));
    app.dataset.lateral = "fechada";
    ligarEventos();
    ajustarAltura();
    atualizarBotao();
    restaurarHistorico();
    carregarExemplos();
    vigiarEstado();
  }

  document.addEventListener("DOMContentLoaded", iniciar);
})();
