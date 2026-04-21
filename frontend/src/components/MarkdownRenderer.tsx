/**
 * Lightweight Markdown renderer — no external dependencies.
 * Renders: headings, bold, italic, inline code, code blocks,
 * unordered/ordered lists, blockquotes, horizontal rules, links, tables.
 */
import React, { useMemo } from 'react';

function escapeHtml(str: string): string {
    return str
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;');
}

function injectToken(url: string): string {
    if (url.startsWith('/api/agents/')) {
        const token = typeof localStorage !== 'undefined' ? localStorage.getItem('token') : null;
        if (token && !url.includes('token=')) {
            url += (url.includes('?') ? '&' : '?') + `token=${token}`;
        }
    }
    return url;
}

function getFileIcon(fileName: string): string {
    const ext = (fileName.split('.').pop() || '').toLowerCase();
    if (ext === 'pdf') return '📄';
    if (['csv', 'xlsx', 'xls'].includes(ext)) return '📊';
    if (['docx', 'doc'].includes(ext)) return '📝';
    if (['png', 'jpg', 'jpeg', 'gif', 'webp', 'bmp'].includes(ext)) return '🖼️';
    if (['zip', 'tar', 'gz', 'rar'].includes(ext)) return '📦';
    return '📎';
}

function renderFileReadyBlock(line: string): string | null {
    const match = line.match(/^File ready:\s*\[([^\]]+)\]\(([^)]+)\)(.*)$/);
    if (!match) return null;
    const [, fileName, rawUrl, restContent] = match;
    const url = injectToken(rawUrl);
    const safeName = escapeHtml(fileName);
    const icon = getFileIcon(fileName);
    const isImage = ['png', 'jpg', 'jpeg', 'gif', 'webp', 'bmp'].includes((fileName.split('.').pop() || '').toLowerCase());
    const displayContent = restContent ? restContent.trim() : '';
    let html = `<div style="display:inline-flex;align-items:center;gap:10px;background:var(--bg-secondary);border:1px solid #2563eb;border-left:4px solid #2563eb;border-radius:8px;padding:10px 14px;margin:6px 0;min-width:200px">`;
    if (isImage) {
        html += `<img src="${url}" alt="${safeName}" style="width:40px;height:40px;object-fit:cover;border-radius:4px;border:1px solid var(--border-subtle)" loading="lazy"/>`;
    } else {
        html += `<span style="font-size:22px;flex-shrink:0">${icon}</span>`;
    }
    html += `<div style="flex:1;min-width:0">`;
    html += `<div style="font-weight:500;color:var(--text-primary);font-size:13px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:220px" title="${safeName}">${safeName}</div>`;
    html += `<a href="${url}" download="${safeName}" style="font-size:12px;color:#2563eb;text-decoration:underline;text-underline-offset:2px;font-weight:500">下载</a>`;
    html += `</div></div>`;
    if (displayContent) {
        return html + `<p style="margin:4px 0">${displayContent}</p>`;
    }
    return html + '</div>';
}

function markdownToHtml(md: string): string {
    const lines = md.split('\n');
    let html = '';
    let inCodeBlock = false;
    let codeLang = '';
    let codeLines: string[] = [];
    let inList: 'ul' | 'ol' | null = null;
    let inBlockquote = false;
    let inTable = false;
    let tableHeader = false;

    const flushList = () => {
        if (inList) { html += inList === 'ul' ? '</ul>' : '</ol>'; inList = null; }
    };
    const flushBlockquote = () => {
        if (inBlockquote) { html += '</blockquote>'; inBlockquote = false; }
    };
    const flushTable = () => {
        if (inTable) { html += '</tbody></table>'; inTable = false; tableHeader = false; }
    };

    for (let i = 0; i < lines.length; i++) {
        const line = lines[i];

        // Code block
        if (line.startsWith('```')) {
            if (!inCodeBlock) {
                flushList(); flushBlockquote(); flushTable();
                inCodeBlock = true;
                codeLang = line.slice(3).trim();
                codeLines = [];
            } else {
                const codeContent = escapeHtml(codeLines.join('\n'));
                html += `<pre style="background:var(--bg-secondary);border-radius:8px;padding:12px 16px;overflow-x:auto;margin:8px 0"><code style="font-family:monospace;font-size:12px;line-height:1.5"${codeLang ? ` class="language-${codeLang}"` : ''}>${codeContent}</code></pre>`;
                inCodeBlock = false;
                codeLang = '';
                codeLines = [];
            }
            continue;
        }
        if (inCodeBlock) { codeLines.push(line); continue; }

        // Blank line
        if (line.trim() === '') {
            flushList(); flushBlockquote(); flushTable();
            html += '<br>';
            continue;
        }

        // Headings
        const hMatch = line.match(/^(#{1,6})\s+(.*)/);
        if (hMatch) {
            flushList(); flushBlockquote(); flushTable();
            const level = hMatch[1].length;
            const sizes = ['1.6em', '1.4em', '1.2em', '1.1em', '1em', '0.9em'];
            const margins = ['20px 0 8px', '16px 0 6px', '14px 0 5px', '12px 0 4px', '10px 0 4px', '8px 0 4px'];
            html += `<h${level} style="margin:${margins[level - 1]};font-size:${sizes[level - 1]};font-weight:600;line-height:1.3">${renderInline(hMatch[2])}</h${level}>`;
            continue;
        }

        // Horizontal rule
        if (/^[-*_]{3,}$/.test(line.trim())) {
            flushList(); flushBlockquote(); flushTable();
            html += '<hr style="border:none;border-top:1px solid var(--border-color);margin:12px 0">';
            continue;
        }

        // Blockquote
        if (line.startsWith('> ')) {
            flushList(); flushTable();
            if (!inBlockquote) {
                html += '<blockquote style="border-left:3px solid var(--accent-primary);margin:8px 0;padding:4px 12px;color:var(--text-secondary);background:var(--bg-secondary);border-radius:0 4px 4px 0">';
                inBlockquote = true;
            }
            html += `<div>${renderInline(line.slice(2))}</div>`;
            continue;
        } else if (inBlockquote) {
            flushBlockquote();
        }

        // Tables
        if (line.includes('|')) {
            flushList(); flushBlockquote();
            const cols = line.split('|').map(c => c.trim()).filter((_, i, a) => i > 0 && i < a.length - 1);
            if (cols.every(c => /^[-:]+$/.test(c))) {
                tableHeader = true;
                continue;
            }
            if (!inTable) {
                html += '<table style="border-collapse:collapse;margin:8px 0;font-size:13px;width:100%"><thead>';
                inTable = true;
                tableHeader = false;
                html += '<tr>' + cols.map(c => `<th style="border:1px solid rgba(128,128,128,0.4);padding:6px 10px;background:var(--bg-secondary);text-align:left;font-weight:600">${renderInline(c)}</th>`).join('') + '</tr>';
                html += '</thead><tbody>';
            } else {
                html += '<tr>' + cols.map(c => `<td style="border:1px solid rgba(128,128,128,0.4);padding:6px 10px">${renderInline(c)}</td>`).join('') + '</tr>';
            }
            continue;
        } else if (inTable) {
            flushTable();
        }

        // Unordered list
        const ulMatch = line.match(/^(\s*)[*\-+]\s+(.*)/);
        if (ulMatch) {
            flushBlockquote(); flushTable();
            if (inList !== 'ul') { if (inList) flushList(); html += '<ul style="margin:6px 0;padding-left:24px">'; inList = 'ul'; }
            html += `<li style="margin:2px 0">${renderInline(ulMatch[2])}</li>`;
            continue;
        }

        // Ordered list
        const olMatch = line.match(/^(\s*)\d+\.\s+(.*)/);
        if (olMatch) {
            flushBlockquote(); flushTable();
            if (inList !== 'ol') { if (inList) flushList(); html += '<ol style="margin:6px 0;padding-left:24px">'; inList = 'ol'; }
            html += `<li style="margin:2px 0">${renderInline(olMatch[2])}</li>`;
            continue;
        }

        // Regular paragraph
        flushList(); flushBlockquote(); flushTable();
        const fileReadyHtml = renderFileReadyBlock(line.trim());
        if (fileReadyHtml) {
            html += fileReadyHtml;
            continue;
        }
        html += `<p style="margin:4px 0;line-height:1.7">${renderInline(line)}</p>`;
    }

    flushList(); flushBlockquote(); flushTable();
    if (inCodeBlock) {
        html += `<pre style="background:var(--bg-secondary);border-radius:8px;padding:12px 16px"><code>${escapeHtml(codeLines.join('\n'))}</code></pre>`;
    }

    return html;
}

/**
 * Renders inline Markdown (bold, italic, code, links, images) with FULL protection
 * of link/image text content from other inline rules.
 *
 * Order of operations:
 * 1. Capture all links/images and protect their text with placeholders
 * 2. Apply bold, italic, code, strikethrough on the remaining text
 * 3. Restore link/image HTML with original text (unescaped — browser will escape on render)
 */
function renderInline(text: string): string {
    const protectedSegments: string[] = [];

    // Step 1: protect link and image text by extracting them into placeholders
    // The placeholder is a string that won't be touched by subsequent regexes
    let step1 = text
        .replace(/!\[([^\]]*)\]\(([^)]+)\)/g, (match, alt, url) => {
            const safeAlt = escapeHtml(alt);
            let finalUrl = url;
            if (finalUrl.startsWith('/api/agents/')) {
                const token = localStorage.getItem('token');
                if (token && !finalUrl.includes('token=')) {
                    finalUrl += (finalUrl.includes('?') ? '&' : '?') + `token=${token}`;
                }
            }
            const idx = protectedSegments.length;
            protectedSegments.push(`<a href="${finalUrl}" target="_blank"><img src="${finalUrl}" alt="${safeAlt}" style="max-width:100%;max-height:400px;border-radius:4px;margin:8px 0;object-fit:contain;cursor:pointer" /></a>`);
            return `\x00IMG${idx}\x00`;
        })
        .replace(/\[([^\]]+)\]\(([^)]+)\)/g, (match, linkText, url) => {
            if (match.startsWith('!')) return match; // already handled above
            let finalUrl = url;
            if (finalUrl.startsWith('/api/agents/')) {
                const token = localStorage.getItem('token');
                if (token && !finalUrl.includes('token=')) {
                    finalUrl += (finalUrl.includes('?') ? '&' : '?') + `token=${token}`;
                }
            }
            const idx = protectedSegments.length;
            protectedSegments.push(`<a href="${finalUrl}" target="_blank" rel="noopener noreferrer" style="color:#2563eb;text-decoration:underline;text-underline-offset:2px">${linkText}</a>`);
            return `\x00LINK${idx}\x00`;
        });

    // Step 2: apply all inline formatting to the remaining text
    let step2 = step1
        // Bold + italic
        .replace(/\*\*\*(.*?)\*\*\*/g, '<strong><em>$1</em></strong>')
        // Bold
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/__(.*?)__/g, '<strong>$1</strong>')
        // Italic — single * only, NOT underscore (underscore in filenames breaks links)
        .replace(/\*(.*?)\*/g, '<em>$1</em>')
        // Inline code
        .replace(/`([^`]+)`/g, '<code style="background:var(--bg-secondary);padding:1px 4px;border-radius:3px;font-family:monospace;font-size:0.9em">$1</code>')
        // Strikethrough
        .replace(/~~(.*?)~~/g, '<del>$1</del>');

    // Step 3: restore protected link/image HTML
    for (let i = 0; i < protectedSegments.length; i++) {
        step2 = step2.replace(`\x00IMG${i}\x00`, protectedSegments[i]);
        step2 = step2.replace(`\x00LINK${i}\x00`, protectedSegments[i]);
    }

    return step2;
}

interface MarkdownRendererProps {
    content: string;
    style?: React.CSSProperties;
    className?: string;
}

export const MarkdownRenderer = React.memo(function MarkdownRenderer({ content, style, className }: MarkdownRendererProps) {
    const html = useMemo(() => markdownToHtml(content), [content]);
    return (
        <div
            className={className}
            style={{ lineHeight: 1.6, fontSize: 'inherit', ...style, wordBreak: 'break-word' }}
            dangerouslySetInnerHTML={{ __html: html }}
        />
    );
});

export default MarkdownRenderer;
