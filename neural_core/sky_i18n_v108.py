"""Reviewed operational status labels for SKY v10.8; no private data translations."""
KEYS = [
 'Copia cifrada','Restauración verificada','Respaldo automático',
 'Último respaldo','Verificar integridad','Retención de copias',
 'Ensayo de recuperación','Tiempo de recuperación','Estado del contenedor',
 'Modelo de voz local','Reconocimiento multilingüe','Idioma detectado',
 'Pruebas pendientes','Sin conexión','No se encontraron respaldos',
 'Solo el propietario','Datos privados','Configuración segura',
]
ROWS={
'en':['Encrypted backup','Verified restoration','Scheduled backup','Last backup','Verify integrity','Backup retention','Recovery rehearsal','Recovery time','Container status','Local voice model','Multilingual speech recognition','Detected language','Pending tests','Offline','No backups found','Owner only','Private data','Secure configuration'],
'pt':['Cópia criptografada','Restauração verificada','Backup agendado','Último backup','Verificar integridade','Retenção de backups','Ensaio de recuperação','Tempo de recuperação','Estado do contêiner','Modelo de voz local','Reconhecimento de fala multilíngue','Idioma detectado','Testes pendentes','Sem conexão','Nenhum backup encontrado','Somente o proprietário','Dados privados','Configuração segura'],
'fr':['Sauvegarde chiffrée','Restauration vérifiée','Sauvegarde planifiée','Dernière sauvegarde','Vérifier l’intégrité','Conservation des sauvegardes','Test de restauration','Temps de restauration','État du conteneur','Modèle vocal local','Reconnaissance vocale multilingue','Langue détectée','Tests en attente','Hors ligne','Aucune sauvegarde trouvée','Propriétaire uniquement','Données privées','Configuration sécurisée'],
'ar':['نسخة احتياطية مشفرة','استعادة تم التحقق منها','نسخ احتياطي مجدول','آخر نسخة احتياطية','التحقق من السلامة','الاحتفاظ بالنسخ الاحتياطية','اختبار الاستعادة','وقت الاستعادة','حالة الحاوية','نموذج صوت محلي','التعرف على الكلام متعدد اللغات','اللغة المكتشفة','اختبارات معلقة','دون اتصال','لم يتم العثور على نسخ احتياطية','المالك فقط','بيانات خاصة','إعداد آمن'],
'zh':['加密备份','已验证的恢复','定时备份','上次备份','验证完整性','备份保留','恢复演练','恢复时间','容器状态','本地语音模型','多语言语音识别','检测到的语言','待完成的测试','离线','未找到备份','仅限所有者','私人数据','安全配置'],
'ja':['暗号化バックアップ','検証済みの復元','定期バックアップ','最終バックアップ','整合性を確認','バックアップ保持','復元訓練','復元時間','コンテナの状態','ローカル音声モデル','多言語音声認識','検出された言語','未実施のテスト','オフライン','バックアップが見つかりません','所有者のみ','非公開データ','安全な設定'],
'sw':['Nakala iliyosimbwa','Urejeshaji uliothibitishwa','Nakala ya ratiba','Nakala ya mwisho','Thibitisha uadilifu','Uhifadhi wa nakala','Jaribio la urejeshaji','Muda wa kurejesha','Hali ya kontena','Mfano wa sauti wa ndani','Utambuzi wa usemi wa lugha nyingi','Lugha iliyotambuliwa','Majaribio yanayosubiri','Nje ya mtandao','Hakuna nakala zilizopatikana','Mmiliki peke yake','Data za faragha','Mipangilio salama'],
'de':['Verschlüsseltes Backup','Geprüfte Wiederherstellung','Geplantes Backup','Letztes Backup','Integrität prüfen','Backup-Aufbewahrung','Wiederherstellungstest','Wiederherstellungszeit','Containerstatus','Lokales Sprachmodell','Mehrsprachige Spracherkennung','Erkannte Sprache','Ausstehende Tests','Offline','Keine Backups gefunden','Nur Eigentümer','Private Daten','Sichere Konfiguration'],
'it':['Backup cifrato','Ripristino verificato','Backup programmato','Ultimo backup','Verifica integrità','Conservazione backup','Test di ripristino','Tempo di ripristino','Stato del contenitore','Modello vocale locale','Riconoscimento vocale multilingue','Lingua rilevata','Test in sospeso','Offline','Nessun backup trovato','Solo proprietario','Dati privati','Configurazione sicura']}
assert all(len(x)==len(KEYS) for x in ROWS.values())
REVIEWED={lang:dict(zip(KEYS,row)) for lang,row in ROWS.items()}
