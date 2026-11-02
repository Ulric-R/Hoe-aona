import { Pipe, PipeTransform } from '@angular/core';

function escape(text: string): string {
  return text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

function inline(text: string, sourceCount: number): string {
  let out = escape(text);
  out = out.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
  out = out.replace(/(^|[^*])\*([^*]+)\*/g, '$1<em>$2</em>');
  out = out.replace(/\[([^\]]+)\]\((https?:\/\/[^)\s]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>');
  // Références [n] vers la liste des sources de l'article
  out = out.replace(/\[(\d{1,2})\]/g, (m, n) =>
    Number(n) >= 1 && Number(n) <= sourceCount ? `<sup class="cite">[${n}]</sup>` : m);
  return out;
}

/** Rendu Markdown minimal et sûr (titres, paragraphes, listes, gras, italique, liens, références). */
@Pipe({ name: 'markdown' })
export class MarkdownPipe implements PipeTransform {
  transform(markdown: string | null | undefined, sourceCount = 99): string {
    if (!markdown) return '';
    const html: string[] = [];
    let list: 'ul' | 'ol' | null = null;
    const close = () => { if (list) { html.push(`</${list}>`); list = null; } };
    for (const raw of markdown.split(/\r?\n/)) {
      const line = raw.trimEnd();
      const heading = /^(#{1,4})\s+(.*)$/.exec(line);
      const bullet = /^\s*[-*]\s+(.*)$/.exec(line);
      const ordered = /^\s*\d+[.)]\s+(.*)$/.exec(line);
      if (heading) {
        close();
        const level = Math.min(heading[1].length + 1, 4);
        html.push(`<h${level}>${inline(heading[2], sourceCount)}</h${level}>`);
      } else if (bullet || ordered) {
        const tag = bullet ? 'ul' : 'ol';
        if (list !== tag) { close(); html.push(`<${tag}>`); list = tag; }
        html.push(`<li>${inline((bullet ?? ordered)![1], sourceCount)}</li>`);
      } else if (line.trim()) {
        close();
        html.push(`<p>${inline(line, sourceCount)}</p>`);
      } else {
        close();
      }
    }
    close();
    return html.join('');
  }
}
