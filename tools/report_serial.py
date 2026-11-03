#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tools/report_serial.py — تسمية التقارير: arabic-sarf-<رقم تسلسلي>.html (حكم المالك، 3 نوفمبر 2026).

كل تقريرٍ يُسلَّم يُنشر صفحة HTML واحدة باسم arabic-sarf-NNN.html في reports/، والرقم التالي يُحسب من الموجود
(لا يُعاد استعمال رقم ولا يُستبدل تقريرٌ سابق). ويُسجَّل كل تقرير في reports/arabic-sarf-index.md بتاريخه والتزامه ومصادره.

    python3 tools/report_serial.py next
    python3 tools/report_serial.py publish --title "<العنوان>" <ملف.md> [<ملف.md> …] [--link <مسار> …]
"""
import argparse, datetime, html, os, re, subprocess, sys

H = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
R = os.path.join(H, 'reports')
PAT = re.compile(r'^arabic-sarf-(\d+)\.html$')


def next_serial():
    nums = [int(m.group(1)) for _, _, fs in os.walk(R) for f in fs for m in [PAT.match(f)] if m]
    return max(nums, default=0) + 1


def _inline(s):
    s = html.escape(s)
    s = re.sub(r'`([^`]+)`', r'<code>\1</code>', s)
    s = re.sub(r'\*\*([^*]+)\*\*', r'<b>\1</b>', s)
    return s


def md_to_html(md):
    """محوّلٌ صغير لما تستعمله تقارير المشروع: عناوين، وفقرات، وقوائم متداخلة، وجداول، واقتباس، وكتل شيفرة"""
    out, lines, i = [], md.split('\n'), 0
    while i < len(lines):
        l = lines[i]
        if l.startswith('```'):
            j = i + 1
            while j < len(lines) and not lines[j].startswith('```'):
                j += 1
            out.append('<pre>' + html.escape('\n'.join(lines[i + 1:j])) + '</pre>')
            i = j + 1
            continue
        m = re.match(r'^(#{1,4}) (.*)', l)
        if m:
            n = len(m.group(1))
            out.append(f'<h{n}>{_inline(m.group(2))}</h{n}>')
            i += 1
            continue
        if l.startswith('|'):
            rows = []
            while i < len(lines) and lines[i].startswith('|'):
                rows.append(lines[i])
                i += 1
            cells = [[c.strip() for c in r.strip().strip('|').split('|')] for r in rows]
            body = [c for c in cells[2:]] if len(cells) > 1 and set(''.join(cells[1])) <= set('-: ') else cells[1:]
            t = '<div class="wrap"><table><tr>' + ''.join(f'<th>{_inline(c)}</th>' for c in cells[0]) + '</tr>'
            t += ''.join('<tr>' + ''.join(f'<td>{_inline(c)}</td>' for c in r) + '</tr>' for r in body)
            out.append(t + '</table></div>')
            continue
        if re.match(r'^\s*([-*]|\d+\.) ', l):
            stack = []
            while i < len(lines) and re.match(r'^\s*([-*]|\d+\.) ', lines[i]):
                m = re.match(r'^(\s*)([-*]|\d+\.) (.*)', lines[i])
                d, tag = len(m.group(1)) // 2, 'ol' if m.group(2)[0].isdigit() else 'ul'
                while len(stack) < d + 1:
                    out.append(f'<{tag}>')
                    stack.append(tag)
                while len(stack) > d + 1:
                    out.append(f'</{stack.pop()}>')
                out.append(f'<li>{_inline(m.group(3))}</li>')
                i += 1
            while stack:
                out.append(f'</{stack.pop()}>')
            continue
        if l.startswith('>'):
            q = []
            while i < len(lines) and lines[i].startswith('>'):
                q.append(lines[i].lstrip('> '))
                i += 1
            out.append('<blockquote>' + '<br>'.join(_inline(x) for x in q if x) + '</blockquote>')
            continue
        if l.strip():
            out.append(f'<p>{_inline(l)}</p>')
        i += 1
    return '\n'.join(out)


CSS = (':root{--bg:#fff;--fg:#1b1b1b;--mut:#666;--line:#ddd;--hd:#f6f8fa;--acc:#0b5cad}'
       '@media (prefers-color-scheme: dark){:root:not([data-theme="light"]){--bg:#0d1117;--fg:#e6edf3;--mut:#9da7b3;--line:#30363d;'
       '--hd:#161b22;--acc:#58a6ff}}'
       'body{background:var(--bg);color:var(--fg);font-family:system-ui,"Noto Naskh Arabic",sans-serif;max-width:1100px;margin:auto;'
       'padding:16px;line-height:1.8}h1{font-size:1.5rem}h2{font-size:1.25rem;border-bottom:1px solid var(--line);padding-bottom:4px;margin-top:2em}'
       'h3{font-size:1.05rem}table{border-collapse:collapse;width:100%;margin:8px 0;font-size:14px}td,th{border:1px solid var(--line);'
       'padding:4px 6px;vertical-align:top}th{background:var(--hd)}.wrap{overflow-x:auto}code{font-size:13px;background:var(--hd);'
       'padding:0 3px;border-radius:3px}pre{background:var(--hd);padding:8px;overflow-x:auto}blockquote{border-inline-start:3px solid var(--acc);'
       'margin:8px 0;padding:4px 12px;color:var(--mut)}.meta{color:var(--mut);font-size:13px}a{color:var(--acc)}')


def publish(title, sources, links):
    n = next_serial()
    name = f'arabic-sarf-{n:03d}.html'
    commit = subprocess.run(['git', '-C', H, 'rev-parse', '--short', 'HEAD'], capture_output=True, text=True).stdout.strip()
    dirty = bool(subprocess.run(['git', '-C', H, 'status', '--porcelain', '--untracked-files=no'], capture_output=True, text=True).stdout.strip())
    date = datetime.date.today().isoformat()
    body = []
    for s in sources:
        body.append(f'<section><p class="meta">المصدر: <code>{html.escape(os.path.relpath(s, H))}</code></p>'
                    + md_to_html(open(s, encoding='utf-8').read()) + '</section>')
    lk = ''.join(f'<li><a href="{html.escape(os.path.relpath(p, R))}">{html.escape(os.path.relpath(p, H))}</a></li>' for p in links)
    page = (f'<!doctype html><html lang="ar" dir="rtl"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>{html.escape(name[:-5])}</title><style>{CSS}</style>'
            f'<h1>{html.escape(name[:-5])}: {html.escape(title)}</h1>'
            f'<p class="meta">الرقم التسلسلي {n:03d} · {date} · الالتزام <code>{commit}</code>{" (مع تعديلاتٍ غير ملتزم بها)" if dirty else ""}</p>'
            + ''.join(body) + (f'<h2>الملفات المرفقة</h2><ul>{lk}</ul>' if lk else '') + '</html>')
    path = os.path.join(R, name)
    assert not os.path.exists(path)
    open(path, 'w', encoding='utf-8').write(page)
    idx = os.path.join(R, 'arabic-sarf-index.md')
    if not os.path.exists(idx):
        open(idx, 'w', encoding='utf-8').write('# فهرس التقارير (arabic-sarf-NNN.html)\n\n| الرقم | الملف | التاريخ | الالتزام | العنوان | المصادر |\n|---|---|---|---|---|---|\n')
    with open(idx, 'a', encoding='utf-8') as f:
        f.write(f"| {n:03d} | `{name}` | {date} | `{commit}` | {title} | {'، '.join('`' + os.path.relpath(s, H) + '`' for s in sources)} |\n")
    return path


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('mode', choices=('next', 'publish'))
    ap.add_argument('sources', nargs='*')
    ap.add_argument('--title', default='')
    ap.add_argument('--link', action='append', default=[])
    a = ap.parse_args()
    if a.mode == 'next':
        print(f'arabic-sarf-{next_serial():03d}.html')
    else:
        print(publish(a.title, [os.path.abspath(s) for s in a.sources], [os.path.abspath(p) for p in a.link]))
