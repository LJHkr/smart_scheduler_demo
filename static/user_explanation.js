(() => {
  agentNote = () => '';
  explanationHtml = (exp, title = '安排说明') => {
    if (!exp?.sentences?.length) return '';
    return `<div class="explanation"><h3>${esc(title)}</h3><ul>${exp.sentences.map(sentence => `<li>${esc(sentence)}</li>`).join('')}</ul></div>`;
  };
  renderAnswer = data => {
    q('#message').innerHTML = explanationHtml(data.explanation, '针对你的问题');
  };
})();
