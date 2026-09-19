(() => {
  const mdButton = document.querySelector('#export-md'), csvButton = document.querySelector('#export-csv');
  if (!mdButton || !csvButton) return;
  const safe = value => String(value ?? '').replaceAll('|', '\\|').replaceAll('\n', ' ');
  const csvCell = value => `"${String(value ?? '').replaceAll('"', '""')}"`;
  const timestamp = () => {const d=new Date(),p=n=>String(n).padStart(2,'0');return `${d.getFullYear()}${p(d.getMonth()+1)}${p(d.getDate())}_${p(d.getHours())}${p(d.getMinutes())}`};
  const download = (content,type,name,bom=false) => {const blob=new Blob([bom?'\ufeff':'',content],{type}),url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download=name;document.body.appendChild(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),1000)};
  function buildMarkdown(result){
    const lines=['# 智能排班结果','',`- 导出时间：${new Date().toLocaleString('zh-CN')}`];
    const request=result.request?.original_text||result.request?.deepseek_interpretation?.original_text;if(request)lines.push(`- 用户需求：${safe(request)}`);
    lines.push('', '## 排班表','', '| 日期 | 班次 | 时间 | 员工 | 店长值守 | 饮品制作 | 收银 |','| --- | --- | --- | --- | ---: | ---: | ---: |');
    result.schedule.forEach(x=>lines.push(`| ${safe(x.day)} | ${safe(x.shift)} | ${safe(x.time)} | ${x.employees.map(safe).join('、')} | ${x.coverage['店长值守']} | ${x.coverage['饮品制作']} | ${x.coverage['收银']} |`));
    if(result.changes?.length)lines.push('','## 相对上一版的改动','',...result.changes.map(x=>`- ${safe(x)}`));
    if(result.explanation?.sentences?.length)lines.push('','## 安排说明','',...result.explanation.sentences.map(x=>`- ${safe(x)}`));
    lines.push('','## 规则检查','',...Object.entries(result.validation?.rules||{}).map(([id,item])=>`- ${id}：${item.passed?'通过':'未通过'}`));
    lines.push('','## AI 工具使用记录','','- DeepSeek 用于理解用户需求、生成调整建议和面向用户的安排说明。','- 排班结果经过程序规则检查。','- 正式提交前由团队人工复核。','');
    return lines.join('\n');
  }
  function buildCsv(result){const rows=[['日期','班次','时间','员工ID','员工及岗位','人数','店长值守人数','饮品制作人数','收银人数','规则检查']];result.schedule.forEach(x=>rows.push([x.day,x.shift,x.time,x.employees.join('、'),x.employee_details.map(e=>`${e.id}-${e.position}`).join('、'),x.employees.length,x.coverage['店长值守'],x.coverage['饮品制作'],x.coverage['收银'],result.validation?.valid?'全部通过':'存在问题']));return rows.map(row=>row.map(csvCell).join(',')).join('\r\n')}
  const current=()=>{try{return currentResult}catch(_){return null}};
  const refresh=()=>{const ready=Boolean(current()?.success&&current()?.schedule?.length);mdButton.disabled=!ready;csvButton.disabled=!ready};setInterval(refresh,300);refresh();
  mdButton.onclick=()=>{const result=current();if(result)download(buildMarkdown(result),'text/markdown;charset=utf-8',`智能排班_${timestamp()}.md`)};
  csvButton.onclick=()=>{const result=current();if(result)download(buildCsv(result),'text/csv;charset=utf-8',`智能排班_${timestamp()}.csv`,true)};
})();
