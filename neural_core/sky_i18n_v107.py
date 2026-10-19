"""SKY v10.7 reviewed static controls across public/private screens.

This dictionary never translates user text, chat, documents, upload contents,
credentials, or dynamically generated information. Missing strings fall back.
"""
KEYS = [
 'Acceso SKY','Centro de Integración SKY','Chat del mundo','Comprobar modelo local',
 'Comprobar módulos','Contenido editable','Conversación con SKY','Crear MP4 con voz local',
 'Datos CSV, si aplica','Decisión de diseño','Añadir pista global',
 'Aplicar máscaras interpoladas','Audio para transcribir (máximo 10 MB, hasta 60 s)',
 'Clave privada del propietario','Animación avanzada en línea de tiempo',
 'Aplicar fotogramas a la versión editable','Aplicar máscara a última capa de imagen',
 'Compartir memoria global con proveedor','Crear mundo y publicarlo',
 'Contenido de la nota','Guardar en proyecto','Actualizar historial',
]
ROWS = {
 'en': [
  'SKY access','SKY Integration Center','World chat','Check local model','Check modules',
  'Editable content','Conversation with SKY','Create MP4 with local voice','CSV data, if applicable',
  'Design decision','Add global track','Apply interpolated masks',
  'Audio to transcribe (10 MB maximum, up to 60 seconds)','Owner private key',
  'Advanced timeline animation','Apply keyframes to editable version',
  'Apply mask to last image layer','Share global memory with provider',
  'Create and publish world','Note content','Save to project','Refresh history'],
 'pt': [
  'Acesso ao SKY','Centro de Integração SKY','Chat do mundo','Verificar modelo local',
  'Verificar módulos','Conteúdo editável','Conversa com SKY','Criar MP4 com voz local',
  'Dados CSV, se aplicável','Decisão de design','Adicionar faixa global',
  'Aplicar máscaras interpoladas','Áudio para transcrever (máximo 10 MB, até 60 s)',
  'Chave privada do proprietário','Animação avançada na linha do tempo',
  'Aplicar quadros-chave à versão editável','Aplicar máscara à última camada de imagem',
  'Compartilhar memória global com o provedor','Criar mundo e publicar',
  'Conteúdo da nota','Salvar no projeto','Atualizar histórico'],
 'fr': [
  'Accès SKY','Centre d’intégration SKY','Discussion du monde','Vérifier le modèle local',
  'Vérifier les modules','Contenu modifiable','Conversation avec SKY',
  'Créer un MP4 avec narration locale','Données CSV, le cas échéant','Décision de conception',
  'Ajouter une piste globale','Appliquer les masques interpolés',
  'Audio à transcrire (10 Mo maximum, jusqu’à 60 s)','Clé privée du propriétaire',
  'Animation avancée sur la chronologie','Appliquer les images clés à la version modifiable',
  'Appliquer le masque au dernier calque image','Partager la mémoire globale avec le fournisseur',
  'Créer et publier un monde','Contenu de la note','Enregistrer dans le projet',
  'Actualiser l’historique'],
 'ar': [
  'الدخول إلى SKY','مركز تكامل SKY','دردشة العالم','التحقق من النموذج المحلي',
  'التحقق من الوحدات','محتوى قابل للتحرير','محادثة مع SKY',
  'إنشاء MP4 بصوت محلي','بيانات CSV إن وجدت','قرار التصميم','إضافة مسار عام',
  'تطبيق الأقنعة المتدرجة','صوت للنسخ (10 ميغابايت كحد أقصى، حتى 60 ثانية)',
  'المفتاح الخاص للمالك','تحريك متقدم على الخط الزمني',
  'تطبيق الإطارات الرئيسية على النسخة القابلة للتحرير',
  'تطبيق القناع على آخر طبقة صورة','مشاركة الذاكرة العامة مع المزود',
  'إنشاء عالم ونشره','محتوى الملاحظة','حفظ في المشروع','تحديث السجل'],
 'zh': [
  '访问 SKY','SKY 集成中心','世界聊天','检查本地模型','检查模块',
  '可编辑内容','与 SKY 对话','使用本地语音创建 MP4','CSV 数据（如适用）',
  '设计决定','添加全局轨道','应用插值蒙版',
  '待转写音频（最大 10 MB，最长 60 秒）','所有者私钥',
  '高级时间轴动画','将关键帧应用到可编辑版本','将蒙版应用于最后一个图像图层',
  '与提供商共享全局记忆','创建并发布世界','笔记内容','保存到项目','刷新历史记录'],
 'ja': [
  'SKY へのアクセス','SKY 統合センター','ワールドチャット',
  'ローカルモデルを確認','モジュールを確認','編集可能な内容','SKY との会話',
  'ローカル音声で MP4 を作成','CSV データ（該当する場合）','デザインの決定',
  '全体トラックを追加','補間マスクを適用',
  '文字起こしする音声（最大 10 MB、60 秒まで）','所有者の秘密鍵',
  'タイムラインの高度なアニメーション','編集可能な版にキーフレームを適用',
  '最後の画像レイヤーにマスクを適用','プロバイダーと共有メモリを共有',
  'ワールドを作成して公開','メモの内容','プロジェクトに保存','履歴を更新'],
 'sw': [
  'Ufikiaji wa SKY','Kituo cha Uunganishaji cha SKY','Mazungumzo ya dunia',
  'Kagua modeli ya ndani','Kagua moduli','Maudhui yanayoharirika',
  'Mazungumzo na SKY','Unda MP4 kwa sauti ya ndani','Data za CSV, ikiwepo',
  'Uamuzi wa muundo','Ongeza wimbo wa jumla','Tumia barakoa zilizopatanishwa',
  'Sauti ya kunakili (kiwango cha juu MB 10, hadi sekunde 60)',
  'Ufunguo wa faragha wa mmiliki','Uhuishaji wa kina kwenye ratiba ya muda',
  'Tumia fremu muhimu kwenye toleo linaloharirika',
  'Tumia barakoa kwenye tabaka la mwisho la picha',
  'Shiriki kumbukumbu ya jumla na mtoa huduma',
  'Unda dunia na uichapishe','Maudhui ya dokezo',
  'Hifadhi kwenye mradi','Sasisha historia'],
}
assert all(len(row)==len(KEYS) for row in ROWS.values())
REVIEWED = {lang:dict(zip(KEYS,row)) for lang,row in ROWS.items()}
