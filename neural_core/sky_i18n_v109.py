"""Reviewed operational UI status phrases for v10.9, no personal content."""
KEYS = ['Conexión segura','Certificado verificado','Servidor de respaldo',
        'Recuperación en otro equipo','Restauración completada','Prueba de infraestructura',
        'Reconocimiento de voz real','Medición de precisión','No comprobado']
ROWS = {
'en':['Secure connection','Verified certificate','Backup server','Recovery on another computer','Restoration completed','Infrastructure test','Real speech recognition','Accuracy measurement','Not verified'],
'pt':['Conexão segura','Certificado verificado','Servidor de backup','Recuperação em outro computador','Restauração concluída','Teste de infraestrutura','Reconhecimento de voz real','Medição de precisão','Não verificado'],
'fr':['Connexion sécurisée','Certificat vérifié','Serveur de sauvegarde','Restauration sur un autre ordinateur','Restauration terminée','Test d’infrastructure','Reconnaissance vocale réelle','Mesure de précision','Non vérifié'],
'de':['Sichere Verbindung','Verifiziertes Zertifikat','Backup-Server','Wiederherstellung auf einem anderen Computer','Wiederherstellung abgeschlossen','Infrastrukturtest','Echte Spracherkennung','Genauigkeitsmessung','Nicht überprüft'],
'it':['Connessione sicura','Certificato verificato','Server di backup','Ripristino su un altro computer','Ripristino completato','Test dell’infrastruttura','Riconoscimento vocale reale','Misurazione della precisione','Non verificato'],
'ar':['اتصال آمن','شهادة تم التحقق منها','خادم النسخ الاحتياطي','استعادة على جهاز آخر','اكتملت الاستعادة','اختبار البنية التحتية','التعرف الفعلي على الكلام','قياس الدقة','لم يتم التحقق'],
'zh':['安全连接','已验证证书','备份服务器','在另一台计算机上恢复','恢复完成','基础设施测试','真实语音识别','准确率测量','未经验证'],
'ja':['安全な接続','検証済みの証明書','バックアップサーバー','別のコンピューターで復元','復元完了','インフラストラクチャテスト','実際の音声認識','精度測定','未検証'],
'sw':['Muunganisho salama','Cheti kilichothibitishwa','Seva ya nakala rudufu','Urejeshaji kwenye kompyuta nyingine','Urejeshaji umekamilika','Jaribio la miundombinu','Utambuzi halisi wa sauti','Upimaji wa usahihi','Haijathibitishwa'],
}
assert all(len(row)==len(KEYS) for row in ROWS.values())
REVIEWED={lang:dict(zip(KEYS,row)) for lang,row in ROWS.items()}
