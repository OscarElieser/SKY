"""Offline UI glossary for SKY, applied across the same-origin interface.

The base strings are public, STATIC labels, never user messages or project files.
Full natural-language translation of arbitrary content is deliberately separate.
"""
from __future__ import annotations

# Spanish source is used for exact matches in all SKY screens.
BASE = {
 '¿Qué querés crear hoy?':'What would you like to create today?',
 'Espacios':'Spaces', 'Estudio creativo':'Creative studio', 'Idioma':'Language',
 'Guardar':'Save', 'Vista previa':'Preview', 'Proyectos':'Projects',
 'Mundos':'Worlds', 'Seguridad':'Security', 'Documentación API':'API documentation',
 'Comunidad y mundos compartidos':'Community and shared worlds',
 'Metaverso 3D':'3D metaverse', 'Estudio privado y documentos':'Private workspace and documents',
 'Estudio creativo · imágenes y video':'Creative studio · images and video',
 'Flujos de trabajo':'Workflows', 'Enviar':'Send', 'Voz':'Voice', '🎙 Voz':'🎙 Voice',
 'Entrar como usuario':'User sign-in', 'Acceso privado':'Private access',
 'Cerrar sesión':'Sign out', 'Salir':'Exit', 'Usuario':'Username', 'Contraseña':'Password',
 'Entrar':'Sign in', 'Cancelar':'Cancel', 'Ingresar a SKY':'Sign in to SKY',
 'Mis proyectos':'My projects', '◈ Mis proyectos':'◈ My projects',
 'Automatizaciones':'Automations', '⌁ Automatizaciones':'⌁ Automations',
 'Espacio de trabajo':'Workspace', '✧ Espacio de trabajo':'✧ Workspace',
 'Nueva imagen':'New image', 'Nuevo video':'New video',
 'Biblioteca personal':'Personal library', 'Importar imagen, video o audio':'Import image, video or audio',
 'Guardar en SKY':'Save in SKY', 'Descargar HTML':'Download HTML',
 'Crear proyecto':'Create project', 'Actualizar proyectos':'Refresh projects',
 'Descargar proyecto ZIP':'Download project ZIP', 'Crear mundo 3D':'Create 3D world',
 'Mundo 3D':'3D world', 'Diseño visual':'Visual design', 'Conversar':'Chat',
 'Guardar nota privada':'Save private note', 'Nota del proyecto':'Project note',
 'Guardar conversación en proyecto':'Save conversation in project',
 'Crear documento':'Create document', 'Generar imagen con IA':'Generate AI image',
 'Generación opcional con Gemini':'Optional Gemini generation',
 'Exportar proyecto editable':'Export editable project',
 'Mis creaciones':'My creations', 'Mi proyecto':'My project',
 'Importar':'Import', 'Exportar':'Export', 'Descargar':'Download',
 'Editar':'Edit', 'Eliminar':'Delete', 'Buscar':'Search',
 'Compartir':'Share', 'Confirmar':'Confirm', 'Actualizar':'Refresh',
 'Continuar':'Continue', 'Pausar':'Pause', 'Reanudar':'Resume',
 'Crear':'Create', 'Anterior':'Previous', 'Siguiente':'Next',
 'Nombre':'Name', 'Descripción':'Description', 'Contenido':'Content',
 'Privacidad':'Privacy', 'Configuración':'Settings', 'Volver a SKY':'Back to SKY',
 'Traducción parcial':'Partial translation', 'Reconocimiento de voz':'Speech recognition',
 'Subtítulos':'Subtitles', 'Doblaje':'Dubbing', 'Idioma de respuesta':'Response language',
 'Motor IA':'AI provider', 'Verificar acceso':'Verify access',
 'Clave privada SKY':'Private SKY key', 'Centro privado del creador':'Creator private center',
 'Guardar nota':'Save note', 'Proyecto':'Project', 'Proyectos persistentes · privados':'Persistent private projects',
 'Formato':'Format', 'Resultado':'Result', 'Planificación':'Planning',
 'Completado':'Completed', 'Programado':'Scheduled', 'Pausado':'Paused',
 'Seguir trabajando':'Keep working', 'Crear archivo Word/Excel/PPT/PDF':'Create a Word/Excel/PPT/PDF file',
 'Revisión':'Review', 'Aplicar':'Apply', 'Capas':'Layers', 'Ancho':'Width',
 'Alto':'Height', 'Opacidad':'Opacity', 'Título':'Title', 'Texto':'Text',
 'Guardar cambios':'Save changes', 'Seleccionar idioma':'Choose language',
 'Traducción automática':'Automatic translation', 'Se requiere autorización':'Authorization required',
}
# High-confidence core-navigation translations; other static labels fall back to Spanish,
# and an opt-in provider can translate *only public UI labels* when asked.
CORE = {
 'pt': ['O que você quer criar hoje?','Espaços','Estúdio criativo','Idioma','Salvar','Prévia','Projetos','Mundos','Segurança','Documentação da API','Comunidade e mundos compartilhados','Metaverso 3D','Espaço privado e documentos','Estúdio criativo · imagens e vídeo','Fluxos de trabalho','Enviar','Voz','🎙 Voz','Entrar como usuário','Acesso privado','Sair','Sair','Usuário','Senha','Entrar','Cancelar','Entrar no SKY','Meus projetos'],
 'fr': ['Que souhaitez-vous créer aujourd’hui ?','Espaces','Studio créatif','Langue','Enregistrer','Aperçu','Projets','Mondes','Sécurité','Documentation API','Communauté et mondes partagés','Métavers 3D','Espace privé et documents','Studio créatif · images et vidéo','Flux de travail','Envoyer','Voix','🎙 Voix','Connexion utilisateur','Accès privé','Se déconnecter','Quitter','Utilisateur','Mot de passe','Connexion','Annuler','Connexion à SKY','Mes projets'],
 'de': ['Was möchtest du heute erstellen?','Bereiche','Kreativstudio','Sprache','Speichern','Vorschau','Projekte','Welten','Sicherheit','API-Dokumentation','Gemeinschaft und geteilte Welten','3D-Metaversum','Privater Arbeitsbereich und Dokumente','Kreativstudio · Bilder und Video','Arbeitsabläufe','Senden','Stimme','🎙 Stimme','Benutzeranmeldung','Privater Zugang','Abmelden','Verlassen','Benutzername','Passwort','Anmelden','Abbrechen','Bei SKY anmelden','Meine Projekte'],
 'it': ['Cosa vuoi creare oggi?','Spazi','Studio creativo','Lingua','Salva','Anteprima','Progetti','Mondi','Sicurezza','Documentazione API','Comunità e mondi condivisi','Metaverso 3D','Area privata e documenti','Studio creativo · immagini e video','Flussi di lavoro','Invia','Voce','🎙 Voce','Accesso utente','Accesso privato','Esci','Esci','Utente','Password','Accedi','Annulla','Accedi a SKY','I miei progetti'],
 'ar': ['ماذا تريد أن تنشئ اليوم؟','المساحات','الاستوديو الإبداعي','اللغة','حفظ','معاينة','المشاريع','العوالم','الأمان','توثيق واجهة API','المجتمع والعوالم المشتركة','العالم الافتراضي ثلاثي الأبعاد','مساحة خاصة ومستندات','استوديو الصور والفيديو','سير العمل','إرسال','الصوت','🎙 صوت','دخول المستخدم','وصول خاص','تسجيل الخروج','خروج','اسم المستخدم','كلمة المرور','دخول','إلغاء','تسجيل الدخول إلى SKY','مشاريعي'],
 'zh': ['今天想创作什么？','空间','创意工作室','语言','保存','预览','项目','世界','安全','API 文档','社区与共享世界','3D 元宇宙','私人工作区与文档','创意工作室 · 图片和视频','工作流程','发送','语音','🎙 语音','用户登录','私人访问','退出登录','退出','用户名','密码','登录','取消','登录 SKY','我的项目'],
 'ja': ['今日は何を作りたいですか？','スペース','クリエイティブスタジオ','言語','保存','プレビュー','プロジェクト','ワールド','セキュリティ','API ドキュメント','コミュニティと共有ワールド','3D メタバース','プライベート作業場と文書','クリエイティブスタジオ · 画像と動画','ワークフロー','送信','音声','🎙 音声','ユーザーでログイン','非公開アクセス','ログアウト','終了','ユーザー名','パスワード','ログイン','キャンセル','SKY にログイン','マイプロジェクト'],
 'ko': ['오늘 무엇을 만들고 싶으신가요?','공간','크리에이티브 스튜디오','언어','저장','미리보기','프로젝트','세계','보안','API 문서','커뮤니티와 공유 세계','3D 메타버스','개인 작업공간 및 문서','크리에이티브 스튜디오 · 이미지와 영상','워크플로','보내기','음성','🎙 음성','사용자 로그인','개인 액세스','로그아웃','종료','사용자 이름','비밀번호','로그인','취소','SKY 로그인','내 프로젝트'],
 'ru': ['Что хотите создать сегодня?','Пространства','Творческая студия','Язык','Сохранить','Предпросмотр','Проекты','Миры','Безопасность','Документация API','Сообщество и общие миры','3D метавселенная','Личное пространство и документы','Творческая студия · фото и видео','Рабочие процессы','Отправить','Голос','🎙 Голос','Вход пользователя','Личный доступ','Выйти','Выход','Имя пользователя','Пароль','Войти','Отмена','Войти в SKY','Мои проекты'],
 'hi': ['आज आप क्या बनाना चाहते हैं?','कार्यस्थान','रचनात्मक स्टूडियो','भाषा','सहेजें','पूर्वावलोकन','परियोजनाएँ','दुनिया','सुरक्षा','API दस्तावेज़','समुदाय और साझा दुनिया','3D मेटावर्स','निजी कार्यस्थान और दस्तावेज़','रचनात्मक स्टूडियो · छवि और वीडियो','कार्यप्रवाह','भेजें','आवाज़','🎙 आवाज़','उपयोगकर्ता लॉगिन','निजी पहुँच','लॉग आउट','बाहर निकलें','उपयोगकर्ता नाम','पासवर्ड','लॉगिन','रद्द करें','SKY में लॉगिन','मेरी परियोजनाएँ'],
 'id': ['Apa yang ingin Anda buat hari ini?','Ruang','Studio kreatif','Bahasa','Simpan','Pratinjau','Proyek','Dunia','Keamanan','Dokumentasi API','Komunitas dan dunia bersama','Metaverse 3D','Ruang pribadi dan dokumen','Studio kreatif · gambar dan video','Alur kerja','Kirim','Suara','🎙 Suara','Masuk pengguna','Akses pribadi','Keluar','Keluar','Nama pengguna','Kata sandi','Masuk','Batal','Masuk ke SKY','Proyek saya'],
 'tr': ['Bugün ne oluşturmak istersiniz?','Alanlar','Yaratıcı stüdyo','Dil','Kaydet','Önizleme','Projeler','Dünyalar','Güvenlik','API belgeleri','Topluluk ve paylaşılan dünyalar','3D metaverse','Özel çalışma alanı ve belgeler','Yaratıcı stüdyo · görsel ve video','İş akışları','Gönder','Ses','🎙 Ses','Kullanıcı girişi','Özel erişim','Çıkış yap','Çıkış','Kullanıcı adı','Şifre','Giriş','İptal','SKY’a giriş','Projelerim'],
 'sw': ['Ungependa kuunda nini leo?','Nafasi','Studio ya ubunifu','Lugha','Hifadhi','Hakiki','Miradi','Dunia','Usalama','Nyaraka za API','Jamii na dunia za pamoja','Metaverse ya 3D','Nafasi binafsi na hati','Studio ya ubunifu · picha na video','Mitiririko ya kazi','Tuma','Sauti','🎙 Sauti','Ingia kama mtumiaji','Ufikiaji binafsi','Toka','Toka','Jina la mtumiaji','Nenosiri','Ingia','Ghairi','Ingia SKY','Miradi yangu'],
}
CORE_KEYS = list(BASE)[:28]
CORE_MAP = {lang: dict(zip(CORE_KEYS, translations)) for lang, translations in CORE.items()}

# Core Spanish is also exposed as an identity language for round-trip and tests.
EXTRA = {
 'ca':'Català','eu':'Euskara','gl':'Galego','ro':'Română','hu':'Magyar','cs':'Čeština',
 'sk':'Slovenčina','sv':'Svenska','da':'Dansk','no':'Norsk','fi':'Suomi','is':'Íslenska',
 'ms':'Bahasa Melayu','tl':'Filipino','my':'မြန်မာ','km':'ខ្មែរ','lo':'ລາວ','ne':'नेपाली',
 'pa':'ਪੰਜਾਬੀ','gu':'ગુજરાતી','mr':'मराठी','te':'తెలుగు','ml':'മലയാളം','kn':'ಕನ್ನಡ',
 'am':'አማርኛ','so':'Soomaali','zu':'isiZulu','xh':'isiXhosa','af':'Afrikaans',
 'sq':'Shqip','sr':'Српски','hr':'Hrvatski','bs':'Bosanski','bg':'Български',
 'et':'Eesti','lv':'Latviešu','lt':'Lietuvių','sl':'Slovenščina',
 'ka':'ქართული','hy':'Հայերեն','az':'Azərbaycanca','kk':'Қазақша',
 'uz':'Oʻzbekcha','mn':'Монгол','ps':'پښتو','ku':'Kurdî','si':'සිංහල',
 'or':'ଓଡ଼ିଆ','as':'অসমীয়া','ig':'Igbo','ha':'Hausa','rw':'Kinyarwanda',
 'mg':'Malagasy','eo':'Esperanto','cy':'Cymraeg','ga':'Gaeilge',
 'mt':'Malti','lb':'Lëtzebuergesch','bo':'བོད་ཡིག'
}


from .sky_i18n_extended import EXTRA_BASE, EXTRA_REVIEWED
BASE.update(EXTRA_BASE)

def glossary(locale: str):
    root = locale.lower().split('-')[0]
    if root == 'es': return {k:k for k in BASE}
    if root == 'en': return dict(BASE)
    return {**CORE_MAP.get(root, {}), **EXTRA_REVIEWED.get(root, {})}


def coverage(locale: str):
    source = glossary(locale)
    return {'reviewed_strings':len(source), 'total_static_strings':len(BASE),
            'complete': len(source) == len(BASE), 'mode':'offline_reviewed_partial' if source and len(source) < len(BASE) else ('offline_full_core' if source else 'fallback_es')}
