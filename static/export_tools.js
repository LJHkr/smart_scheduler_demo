(() => {
  const mdButton = document.querySelector('#export-md');
  const csvButton = document.querySelector('#export-csv');
  if (!mdButton || !csvButton) return;

  const safe = value => String(value ?? '').replaceAll('|', '\\|').replaceAll('\n', ' ');
  const csvCell = value => `"${String(value ?? '').replaceAll('"', '""')}"`;
  const timestamp = () => {
    const d = new Date(), pad = n => String(n).padStart(2, '0');
    return `${d.getFullYear()}${pad(d.getMonth()+1)}${pad(d.getDate())}_${pad(d.getHours())}${pad(d.getMinutes())}`;
  };
  const download = (content, type, filename, bom = false) => {
    const blob = new Blob([bom ? '\ufeff' : '', content], {type});
    const url = URL.createObjectURL(blob), anchor = document.createElement('a');
    anchor.href = url; anchor.download = filename; document.body.appendChild(anchor); anchor.click(); anchor.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  };

  function buildMarkdown(result) {
    const lines = ['# 智能排班结果', '', `- 导出时间：${new Date().toLocaleString('zh-CN')}`];
    const request = result.request?.original_text || result.request?.deepseek_interpretation?.original_text;
    if (request) lines.push(`- 用户需求：${safe(request)}`);
    lines.push(`- 生成方式：${result.mode === 'append' ? '在已有排班上追加需求' : '从 0 生成排班'}`, '');
    if (result.changes?.length) {
      lines.push('## 相对上一版的改动', '', ...result.changes.map(item => `- ${safe(item)}`), '');
    }
    lines.push('## 排班表', '', '| 日期 | 班次 | 时间 | 员工 | 店长值守 | 饮品制作 | 收银 |', '| --- | --- | --- | --- | ---: | ---: | ---: |');
    result.schedule.forEach(item => lines.push(`| ${safe(item.day)} | ${safe(item.shift)} | ${safe(item.time)} | ${item.employees.map(safe).join('、')} | ${item.coverage['店长值守']} | ${item.coverage['饮品制作']} | ${item.coverage['收银']} |`));
    lines.push('', '## 规则校验', '', '| 规则 | 结果 |', '| --- | --- |');
    Object.entries(result.validation?.rules || {}).forEach(([id, item]) => lines.push(`| ${id} | ${item.passed ? '通过' : `失败：${safe((item.messages || []).join('；'))}`} |`));
    const exp = result.explanation;
    if (exp) {
      lines.push('', '## 为什么这样安排', '', safe(exp.answer), '');
      (exp.key_reasons || []).forEach(reason => {
        lines.push(`### ${safe(reason.title)}`, '', safe(reason.detail));
        if (reason.evidence?.length) lines.push('', ...reason.evidence.map(item => `- 依据：${safe(item)}`));
        lines.push('');
      });
      if (exp.tradeoffs?.length) lines.push('### 主要取舍', '', ...exp.tradeoffs.map(item => `- ${safe(item)}`), '');
      if (exp.limitations?.length) lines.push('### 局限与边界', '', ...exp.limitations.map(item => `- ${safe(item)}`), '');
    }
    lines.push('## AI 工具使用记录', '', '- DeepSeek V4.1 Flash 用于理解自然语言、提出修订建议和生成解释。', '- Python 确定性程序用于生成排班并独立校验 R-01～R-09。', '- 员工数据来自题目材料，技能未由 AI 自行补充。', '- 正式提交前应由团队人工复核排班、文档内容和访问权限。', '');
    return lines.join('\n');
  }

  function buildCsv(result) {
    const rows = [['日期','班次','时间','员工ID','员工及岗位','人数','店长值守人数','饮品制作人数','收银人数','规则校验']];
    result.schedule.forEach(item => rows.push([
      item.day, item.shift, item.time, item.employees.join('、'),
      item.employee_details.map(e => `${e.id}-${e.position}`).join('、'), item.employees.length,
      item.coverage['店长值守'], item.coverage['饮品制作'], item.coverage['收银'],
      result.validation?.valid ? 'R-01～R-09全部通过' : '存在违规'
    ]));
    return rows.map(row => row.map(csvCell).join(',')).join('\r\n');
  }

  function getCurrent() {
    try { return currentResult; } catch (_) { return null; }
  }
  function refresh() {
    const ready = Boolean(getCurrent()?.success && getCurrent()?.schedule?.length);
    mdButton.disabled = !ready; csvButton.disabled = !ready;
  }
  setInterval(refresh, 300); refresh();
  mdButton.addEventListener('click', () => {
    const result = getCurrent(); if (!result) return;
    download(buildMarkdown(result), 'text/markdown;charset=utf-8', `智能排班_${timestamp()}.md`);
  });
  csvButton.addEventListener('click', () => {
    const result = getCurrent(); if (!result) return;
    download(buildCsv(result), 'text/csv;charset=utf-8', `智能排班_${timestamp()}.csv`, true);
  });
})();
