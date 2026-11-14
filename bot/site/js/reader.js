(function () {
  "use strict";

  var shell = document.querySelector("[data-reader-shell]");
  if (!shell) return;
  var reader = document.body.dataset.reader || document.documentElement.dataset.reader || "civil";
  var pageContainer = document.querySelector(".reader-pages");
  var pages = pageContainer ? Array.prototype.filter.call(pageContainer.children, function (page) {
    return page.matches && page.matches("figure.reader-page");
  }) : [];
  var toc = document.querySelector("[data-reader-toc]");
  var current = document.querySelector("[data-reader-current]");
  var noteTitle = document.querySelector("[data-reader-note-title]");
  var noteCopy = document.querySelector("[data-reader-note-copy]");
  var noteProgress = document.querySelector("[data-reader-note-progress]");
  var total = pages.length;
  var activeIndex = -1;

  var notes = {
    civil: [
      ["Capa e propósito", "A capa apresenta o caderno de estudos da seletiva e os quatro eixos do material: conduta, radiocomunicação, investigação e patrulha."],
      ["Apresentação do caderno", "Esta página explica como estudar: compreender os fundamentos, identificar dificuldades e revisar antes da avaliação."],
      ["Formação e progressão", "A formação começa como aluno e pode avançar para agente e habilitações de investigação e patrulha, sempre com preparo e avaliação."],
      ["Base comum", "Esta página reúne a base comum: conduta, hierarquia, modulação, Código Q, direitos, ocorrências, investigação e patrulha."],
      ["Conduta e postura", "Respeito, disciplina, responsabilidade, equilíbrio, sigilo e colaboração formam a postura esperada durante uma ocorrência."],
      ["Radiocomunicação", "Uma modulação clara informa quem fala, o que ocorreu, onde e o que precisa ser feito, evitando conversas paralelas."],
      ["Código Q", "Aqui estão as referências de radiocomunicação, como QAP, QRA, QSL, QRV, QRX, QTH, QTI, QTC e QRR. O sumário aponta para esta página específica."],
      ["Códigos 0 a 7", "Os códigos de patrulhamento organizam a intensidade da ocorrência, do início do patrulhamento à emergência máxima e ao pedido de apoio."],
      ["Direitos e garantias", "A atuação deve respeitar silêncio, assistência jurídica, informação e integridade. Conhecer esses limites reduz erros e abusos."],
      ["Como uma investigação avança", "O fluxo passa por receber, verificar, levantar dados, ouvir, comparar, analisar e relatar sem apresentar hipótese como fato."],
      ["Entrevista investigativa", "Uma entrevista começa com preparação e escuta, usa perguntas abertas, confere pontos verificáveis e registra o relato sem mudá-lo."],
      ["Evidências e registros", "Observe, preserve, organize e relate. Um registro simples separa fato, ação, resultado e encaminhamento."],
      ["Fluxo de patrulhamento", "Patrulhar, perceber, comunicar, avaliar, apoiar e encerrar formam um fluxo de campo com atenção ao ambiente e à equipe."],
      ["Atendimento de ocorrências", "Antes, durante e depois de uma ocorrência, entenda o chamado, comunique mudanças, peça auxílio quando necessário e registre o desfecho."],
      ["Duas áreas, um integrante", "Investigação e patrulha se complementam: uma exige escuta, análise e relatórios; a outra, comunicação, observação e trabalho em equipe."],
      ["Como se preparar", "A revisão pode ser organizada por dias: conduta e direitos, radiocomunicação e Código Q, investigação e relatórios, patrulha e casos práticos."],
      ["Simulado de revisão", "Use as perguntas do simulado para responder com suas palavras antes de consultar o gabarito e identificar o que ainda precisa ser revisado."],
      ["Gabarito e encerramento", "O encerramento reforça o raciocínio por trás das respostas: identificação, localização, contexto, registro, conduta, preparo e responsabilidade."],
    ],
    peace: [
      ["Boas-vindas", "A abertura apresenta o propósito do manual: orientar a convivência e deixar claro o espírito da Peace."],
      ["Presença", "Participar é acompanhar o espaço, ler os canais e estar disponível para entender antes de agir."],
      ["Convivência", "A comunidade fica mais simples quando cada pessoa respeita o contexto do canal e o tempo das outras pessoas."],
      ["Respeito", "Respeito aparece em escolhas concretas: linguagem, limites, escuta e cuidado com quem está do outro lado."],
      ["Comunicação", "Uma comunicação direta e responsável reduz conflitos e ajuda a equipe a resolver o que realmente importa."],
      ["Responsabilidade", "Cada pessoa participa do ambiente que constrói. Assuma o impacto das suas decisões e peça ajuda quando necessário."],
      ["Participação", "Participar não é ocupar todos os espaços; é contribuir de forma útil, coerente e alinhada à comunidade."],
      ["Compromisso", "A última página fecha o manual com a ideia de continuidade: convivência é uma prática diária, não um texto lido uma vez."],
    ]
  }[reader] || [];

  function labelFor(index) {
    return notes[index] ? notes[index][0] : "Página " + String(index + 1).padStart(2, "0");
  }

  function update(index, focus) {
    if (index < 0 || index >= total || index === activeIndex && !focus) return;
    activeIndex = index;
    var pageNumber = String(index + 1).padStart(2, "0");
    var totalLabel = String(total).padStart(2, "0");
    if (current) current.textContent = pageNumber + " / " + totalLabel;
    if (noteProgress) noteProgress.textContent = pageNumber + " / " + totalLabel;
    if (noteTitle) noteTitle.textContent = labelFor(index);
    if (noteCopy) noteCopy.textContent = notes[index] ? notes[index][1] : "Acompanhe esta página como parte da sequência do material.";
    pages.forEach(function (page, pageIndex) {
      page.classList.toggle("is-current", pageIndex === index);
      page.setAttribute("aria-current", pageIndex === index ? "page" : "false");
    });
    if (toc) toc.querySelectorAll("a").forEach(function (link, linkIndex) {
      if (linkIndex === index) link.setAttribute("aria-current", "page");
      else link.removeAttribute("aria-current");
    });
    // A table-of-contents choice is a precise navigation command. Smooth
    // scrolling lets the observer report the previous page for a moment,
    // which makes the selected chapter look wrong and makes the context card
    // disagree with the requested destination. Jump directly to the page so
    // the image, active item and explanation change as one state.
    if (focus && pages[index]) {
      // The global shell uses smooth scrolling for ordinary anchors. Keep
      // that visual language elsewhere, but make a TOC selection atomic so
      // the observer cannot expose an intermediate page.
      var rootStyle = document.documentElement.style;
      var previousScrollBehavior = rootStyle.scrollBehavior;
      rootStyle.scrollBehavior = "auto";
      pages[index].scrollIntoView({ behavior: "auto", block: "start" });
      rootStyle.scrollBehavior = previousScrollBehavior;
    }
  }

  if (toc) {
    pages.forEach(function (page, index) {
      var item = document.createElement("li");
      var link = document.createElement("a");
      link.href = "#reader-page-" + (index + 1);
      link.dataset.readerIndex = String(index);
      var number = document.createElement("span");
      number.textContent = String(index + 1).padStart(2, "0");
      link.appendChild(number);
      link.appendChild(document.createTextNode(labelFor(index)));
      item.appendChild(link);
      toc.appendChild(item);
      page.id = "reader-page-" + (index + 1);
      link.addEventListener("click", function (event) {
        event.preventDefault();
        update(index, true);
        window.history.replaceState({}, document.title, "#" + page.id);
      });
    });
  }

  var observer = "IntersectionObserver" in window ? new IntersectionObserver(function (entries) {
    entries.forEach(function (entry) {
      if (entry.isIntersecting) update(pages.indexOf(entry.target), false);
    });
  }, { rootMargin: "-18% 0px -62% 0px", threshold: 0 }) : null;
  pages.forEach(function (page) { if (observer) observer.observe(page); });

  var hashIndex = pages.findIndex(function (page) { return page.id === window.location.hash.slice(1); });
  update(hashIndex >= 0 ? hashIndex : 0, hashIndex >= 0);

  // This is a light copy-deterrent for the visual reader, not a security
  // promise. Visible content can never be protected from screenshots or OCR.
  shell.addEventListener("contextmenu", function (event) { event.preventDefault(); });
  shell.addEventListener("dragstart", function (event) {
    if (event.target && event.target.tagName === "IMG") event.preventDefault();
  });
  shell.addEventListener("selectstart", function (event) {
    if (event.target && event.target.closest && event.target.closest(".reader-page")) event.preventDefault();
  });
})();
