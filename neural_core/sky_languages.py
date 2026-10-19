"""SKY v10.1: negotiated language preferences and an extensible offline phrase book.

Language choices are BCP-47-style tags. The offline dictionary is intentionally
limited to reviewed UI strings; arbitrary translation requires opt-in provider.
"""
from __future__ import annotations
import json, os, re, threading
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
LANGUAGES={
 'es':'Español','en':'English','pt':'Português','fr':'Français','de':'Deutsch',
 'it':'Italiano','ar':'العربية','zh':'中文','ja':'日本語','ko':'한국어',
 'hi':'हिन्दी','ru':'Русский','nl':'Nederlands','tr':'Türkçe','sw':'Kiswahili',
 'qu':'Runasimi','nah':'Nāhuatl','mi':'Te Reo Māori','id':'Bahasa Indonesia',
 'th':'ไทย','vi':'Tiếng Việt','pl':'Polski','uk':'Українська','el':'Ελληνικά',
 'he':'עברית','fa':'فارسی','bn':'বাংলা','ur':'اردو','ta':'தமிழ்','yo':'Yorùbá',
 'ht':'Kreyòl ayisyen'
}
from .sky_global_ui import EXTRA, glossary, coverage
LANGUAGES.update(EXTRA)
# Only these locales have hand-reviewed OFFLINE UI labels. Others may be
# selected and preserved but fall back to Spanish for untranslated strings.
PHRASES={
 'es':{'hello':'¿Qué querés crear hoy?','write':'Escribí a SKY','spaces':'Espacios','studio':'Estudio creativo','language':'Idioma','save':'Guardar','preview':'Vista previa','creator':'Creador','projects':'Proyectos','worlds':'Mundos','security':'Seguridad'},
 'en':{'hello':'What would you like to create today?','write':'Message SKY','spaces':'Spaces','studio':'Creative studio','language':'Language','save':'Save','preview':'Preview','creator':'Creator','projects':'Projects','worlds':'Worlds','security':'Security'},
 'pt':{'hello':'O que você quer criar hoje?','write':'Escreva para SKY','spaces':'Espaços','studio':'Estúdio criativo','language':'Idioma','save':'Salvar','preview':'Prévia','creator':'Criador','projects':'Projetos','worlds':'Mundos','security':'Segurança'},
 'fr':{'hello':'Que souhaitez-vous créer aujourd’hui ?','write':'Écrire à SKY','spaces':'Espaces','studio':'Studio créatif','language':'Langue','save':'Enregistrer','preview':'Aperçu','creator':'Créateur','projects':'Projets','worlds':'Mondes','security':'Sécurité'},
 'de':{'hello':'Was möchtest du heute erstellen?','write':'SKY schreiben','spaces':'Bereiche','studio':'Kreativstudio','language':'Sprache','save':'Speichern','preview':'Vorschau','creator':'Ersteller','projects':'Projekte','worlds':'Welten','security':'Sicherheit'},
 'it':{'hello':'Cosa vuoi creare oggi?','write':'Scrivi a SKY','spaces':'Spazi','studio':'Studio creativo','language':'Lingua','save':'Salva','preview':'Anteprima','creator':'Creatore','projects':'Progetti','worlds':'Mondi','security':'Sicurezza'},
 'ar':{'hello':'ماذا تريد أن تنشئ اليوم؟','write':'اكتب إلى SKY','spaces':'المساحات','studio':'الاستوديو الإبداعي','language':'اللغة','save':'حفظ','preview':'معاينة','creator':'المنشئ','projects':'المشاريع','worlds':'العوالم','security':'الأمان'},
 'zh':{'hello':'今天想创作什么？','write':'给 SKY 发送消息','spaces':'空间','studio':'创意工作室','language':'语言','save':'保存','preview':'预览','creator':'创作者','projects':'项目','worlds':'世界','security':'安全'},
 'ja':{'hello':'今日は何を作りたいですか？','write':'SKY にメッセージ','spaces':'スペース','studio':'クリエイティブスタジオ','language':'言語','save':'保存','preview':'プレビュー','creator':'クリエイター','projects':'プロジェクト','worlds':'ワールド','security':'セキュリティ'},
 'ko':{'hello':'오늘 무엇을 만들고 싶으신가요?','write':'SKY에 메시지 보내기','spaces':'공간','studio':'크리에이티브 스튜디오','language':'언어','save':'저장','preview':'미리보기','creator':'제작자','projects':'프로젝트','worlds':'세계','security':'보안'},
}
TAG=re.compile(r'^[a-zA-Z]{2,3}(?:-[a-zA-Z0-9]{2,8}){0,3}$')
_LOCK=threading.RLock()

def normalize(value: str|None, *,strict=False)->str:
    raw=(value or '').strip()
    if not raw:return 'es'
    if not TAG.fullmatch(raw):
        if strict:raise ValueError('Etiqueta de idioma inválida')
        return 'es'
    tag=raw.lower();root=tag.split('-')[0]
    if strict and root not in LANGUAGES:raise ValueError('Idioma todavía no incluido en el catálogo')
    return tag if root in LANGUAGES else 'es'

def negotiate(header:str|None):
    """Respect q weights; skip unsupported tags rather than prematurely picking es."""
    candidates=[]
    for idx,entry in enumerate((header or '')[:600].split(',')[:20]):
        part,*attributes=entry.strip().split(';')
        part=part.strip()
        if not TAG.fullmatch(part):continue
        root=part.lower().split('-')[0]
        if root not in LANGUAGES:continue
        quality=1.0
        for attr in attributes:
            if attr.strip().lower().startswith('q='):
                try:quality=float(attr.strip()[2:])
                except ValueError:quality=0
                break
        if 0<quality<=1:candidates.append((quality,-idx,part.lower()))
    return sorted(candidates,reverse=True)[0][2] if candidates else 'es'

def phrase(code:str,language:str='es'):
    root=normalize(language).split('-')[0]
    return PHRASES.get(root,{}).get(code,PHRASES['es'].get(code))

def preferences_path():
    return Path(os.getenv('SKY_LANGUAGE_PREFS') or ROOT/'local_data'/'sky_language_prefs.json')

def get_preference():
    path=preferences_path()
    with _LOCK:
        try:
            data=json.loads(path.read_text(encoding='utf-8'))
            return normalize(data.get('language'))
        except (FileNotFoundError,ValueError,OSError,TypeError):return 'es'

def set_preference(language:str):
    tag=normalize(language,strict=True)
    path=preferences_path()
    with _LOCK:
        path.parent.mkdir(parents=True,exist_ok=True)
        temp=path.with_suffix('.tmp')
        temp.write_text(json.dumps({'language':tag},ensure_ascii=False),encoding='utf-8')
        try:os.chmod(temp,0o600)
        except OSError:pass
        temp.replace(path)
    return tag

def script_hint(text:str):
    """Only identify the dominant *script*; not a reliable spoken language.

    Several languages share scripts (Arabic/Persian/Urdu; Han/Chinese/Japanese;
    Latin for many world languages). Explicit language selection takes priority.
    """
    scripts=[('ja',r'[\u3040-\u30ff]'),('ko',r'[\uac00-\ud7af]'),
             ('ar',r'[\u0600-\u06ff]'),('he',r'[\u0590-\u05ff]'),
             ('hi',r'[\u0900-\u097f]'),('bn',r'[\u0980-\u09ff]'),
             ('pa',r'[\u0a00-\u0a7f]'),('gu',r'[\u0a80-\u0aff]'),
             ('ta',r'[\u0b80-\u0bff]'),('te',r'[\u0c00-\u0c7f]'),
             ('kn',r'[\u0c80-\u0cff]'),('ml',r'[\u0d00-\u0d7f]'),
             ('th',r'[\u0e00-\u0e7f]'),('lo',r'[\u0e80-\u0eff]'),
             ('km',r'[\u1780-\u17ff]'),('my',r'[\u1000-\u109f]'),
             ('si',r'[\u0d80-\u0dff]'),('am',r'[\u1200-\u137f]'),
             ('ka',r'[\u10a0-\u10ff]'),('hy',r'[\u0530-\u058f]'),
             ('el',r'[\u0370-\u03ff]'),('bo',r'[\u0f00-\u0fff]'),
             ('ru',r'[\u0400-\u04ff]'),('zh',r'[\u4e00-\u9fff]')]
    for code,pattern in scripts:
        if re.search(pattern,text):return {'hint':code,'confidence':'script_only'}
    return {'hint':None,'confidence':'unknown'}
