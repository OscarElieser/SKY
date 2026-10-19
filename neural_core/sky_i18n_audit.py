"""Count hardcoded STATIC text in SKY HTML without exposing personal content."""
from __future__ import annotations
from html.parser import HTMLParser
from pathlib import Path
from .sky_global_ui import BASE,glossary

class VisibleStatic(HTMLParser):
    def __init__(self):
        super().__init__();self.stack=[];self.strings=set()
    def handle_starttag(self,tag,attrs):
        self.stack.append(tag)
        attrs=dict(attrs)
        for key in ('placeholder','title','aria-label'):
            value=(attrs.get(key) or '').strip()
            if value and len(value)<=120:self.strings.add(value)
    def handle_startendtag(self,tag,attrs):
        self.handle_starttag(tag,attrs);self.handle_endtag(tag)
    def handle_endtag(self,tag):
        if self.stack:self.stack.pop()
    def handle_data(self,text):
        if any(x in ('script','style','code','textarea','option','svg') for x in self.stack):return
        text=text.strip()
        if text and len(text)<=120 and not text.startswith(('{{','<!--')):
            self.strings.add(text)


def report(static:Path,languages=('en','pt','fr','ar','zh','ja','sw')):
    pages={}
    for f in sorted(static.glob('*.html')):
        html=VisibleStatic();html.feed(f.read_text(encoding='utf-8'));pages[f.name]=sorted(html.strings)
    labels=set().union(*(set(page) for page in pages.values()))
    translations={}
    for lang in languages:
        glossary_map=glossary(lang)
        translated=sorted(label for label in labels if label in glossary_map)
        translations[lang]={'translated':len(translated),'visible_labels':len(labels),
                            'percent':round(100*len(translated)/max(len(labels),1),1)}
    missing=sorted(label for label in labels if label not in BASE)
    return {'pages':{key:len(value) for key,value in pages.items()},
            'visible_static_labels':len(labels),'known_source_labels':len(BASE),
            'missing_static_examples':missing[:40],'languages':translations,
            'public_static_only':True,'not_a_full_translation':True}
