import React from 'react';
// Deliberately bounded Markdown, no HTML interpretation, embeds or remote images.
function inline(text:string):React.ReactNode[]{
 return text.split(/(`[^`]+`|\*\*[^*]+\*\*|\[[^\]]+\]\([^)]+\))/g).map((part,i)=>{
  if(part.startsWith('`')&&part.endsWith('`'))return <code key={i}>{part.slice(1,-1)}</code>;
  if(part.startsWith('**')&&part.endsWith('**'))return <strong key={i}>{part.slice(2,-2)}</strong>;
  const link=/^\[([^\]]+)\]\(([^)]+)\)$/.exec(part);
  if(link&&/^(https?:\/\/|mailto:)/i.test(link[2]))return <a key={i} href={link[2]} rel="noreferrer noopener" target="_blank">{link[1]}</a>;
  return part;
 });
}
export function Markdown({text}:{text:string}){
 const lines=text.split('\n'),out:React.ReactNode[]=[];let i=0;
 while(i<lines.length){const line=lines[i];
  if(line.startsWith('```')){const language=line.slice(3).trim();const code:string[]=[];i++;while(i<lines.length&&!lines[i].startsWith('```'))code.push(lines[i++]);if(i<lines.length)i++;const value=code.join('\n');out.push(<section className="code-block" key={out.length}><div><span>{language||'代码'}</span><button onClick={e=>{void navigator.clipboard.writeText(value).then(()=>{e.currentTarget?.setAttribute('aria-label','代码已复制')}).catch(()=>{})}} aria-label="复制代码">复制</button></div><pre><code>{value}</code></pre></section>);continue;}
  if(i+1<lines.length&&line.includes('|')&&/^\s*\|?[\s:|-]+\|[\s:|-]*$/.test(lines[i+1])){const cells=(s:string)=>s.trim().replace(/^\||\|$/g,'').split('|').map(x=>x.trim());const headers=cells(line),rows:string[][]=[];i+=2;while(i<lines.length&&lines[i].includes('|'))rows.push(cells(lines[i++]));out.push(<div className="table-scroll" key={out.length}><table><thead><tr>{headers.map((x,j)=><th key={j}>{inline(x)}</th>)}</tr></thead><tbody>{rows.map((row,j)=><tr key={j}>{row.map((x,k)=><td key={k}>{inline(x)}</td>)}</tr>)}</tbody></table></div>);continue;}
  if(/^#{1,6} /.test(line)){const heading=line.replace(/^#+ /,'');out.push(<h3 key={out.length}>{inline(heading)}</h3>);i++;continue;}
  if(/^>\s?/.test(line)){const quote:string[]=[];while(i<lines.length&&/^>/.test(lines[i]))quote.push(lines[i++].replace(/^>\s?/,''));out.push(<blockquote key={out.length}>{inline(quote.join('\n'))}</blockquote>);continue;}
  if(/^\s*[-*] /.test(line)){const items:string[]=[];while(i<lines.length&&/^\s*[-*] /.test(lines[i]))items.push(lines[i++].replace(/^\s*[-*] /,''));out.push(<ul key={out.length}>{items.map((x,j)=><li key={j}>{inline(x)}</li>)}</ul>);continue;}
  if(/^\s*\d+\. /.test(line)){const items:string[]=[];while(i<lines.length&&/^\s*\d+\. /.test(lines[i]))items.push(lines[i++].replace(/^\s*\d+\. /,''));out.push(<ol key={out.length}>{items.map((x,j)=><li key={j}>{inline(x)}</li>)}</ol>);continue;}
  if(!line.trim()){i++;continue;}const paragraph=[line];i++;while(i<lines.length&&lines[i].trim()&&!/^(```|#{1,6} |>|\s*[-*] |\s*\d+\. )/.test(lines[i])&&!(i+1<lines.length&&lines[i].includes('|')&&/^[\s:|-]+$/.test(lines[i+1])))paragraph.push(lines[i++]);out.push(<p key={out.length}>{inline(paragraph.join('\n'))}</p>);
 }
 return <div className="markdown">{out}</div>;
}
