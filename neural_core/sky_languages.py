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
    ordered=[]
    for entry in (header or '')[:400].split(','):
        part=entry.split(';')[0].strip()
        if part and part!='*':ordered.append(normalize(part))
    return next((lang for lang in ordered if lang.split('-')[0] in PHRASES),'es')

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
    # A script hint is NOT full language detection. Avoid pretending otherwise.
    scripts=[('ar',r'[\u0600-\u06ff]'),('zh',r'[\u4e00-\u9fff]'),
             ('ja',r'[\u3040-\u30ff]'),('ko',r'[\uac00-\ud7af]'),
             ('ru',r'[\u0400-\u04ff]'),('hi',r'[\u0900-\u097f]')]
    for code,pattern in scripts:
        if re.search(pattern,text):return {'hint':code,'confidence':'script_only'}
    return {'hint':None,'confidence':'unknown'}
