# SKY Android — autorización oficial de Instagram

**Estado: preparación de conexión, no cuenta enlazada.** Este documento
define la primera integración Instagram de SKY Android sin depender de SKY
Windows. En `0.8.6` la aplicación presenta una guía para pasar de cuenta
personal a Creador y registrar los requisitos para Meta. **Aún no ejecuta
un flujo OAuth ni consulta métricas o publica por API.**

## 1. Preparación en el Samsung

1. Abrir Instagram → Perfil → ☰ → Tipo de cuenta y herramientas →
   Cambiar a cuenta profesional.
2. Elegir **Creador**. Revisar la privacidad antes de aceptar: las
   cuentas profesionales son públicas. Se conservan publicaciones y
   seguidores del perfil al cambiar.
3. Confirmar el **Panel para profesionales** en Instagram.
4. En SKY → Ajustes → MIS REDES → Instagram → Preparar acceso oficial
   de Instagram → **Ya cambié a Creador**. Esto registra solamente una
   **declaración local**; no es una verificación de Meta ni autorización.
5. No compartir contraseñas, código 2FA, Instagram App Secret ni tokens.

## 2. Registrar la aplicación en Meta

Crear una aplicación en <https://developers.facebook.com/apps/> y agregar
**Instagram API with Instagram Login**. Esta ruta admite cuentas
profesionales de tipo Creador o Empresa **sin exigir una Página de
Facebook**. No usar Basic Display API obsoleta.

Configurar en Meta la URL HTTPS de retorno de un **backend autenticado**
de SKY. No pegar el secreto de Meta en un APK, un chat o GitHub.
El registro y los permisos dependen del estado y revisión de la app
en Meta.

Separar permisos por finalidad:
- **Identidad profesional mínima:** `instagram_business_basic`.
- **Estadísticas autorizadas:** `instagram_business_manage_insights`.
- **Publicación autorizada:** `instagram_business_content_publish`.
- **Comentarios/mensajes:** mantener desactivados hasta que se diseñen
  y aprueben herramientas de moderación adecuadas.

Evitar solicitar permisos no utilizados. No pedir contraseñas sociales
ni copiar cookies del navegador.

## 3. Backend OAuth pendiente de implementar

La arquitectura prevista es:

1. Android toca **Conectar Instagram** cuando la app Meta y el backend
   estén realmente configurados.
2. SKY backend genera estado CSRF de un solo uso, con expiración y
   redirección HTTPS registrada en Meta.
3. El navegador oficial de Instagram presenta el consentimiento.
4. Meta devuelve código a la URL HTTPS del backend; el backend valida
   estado CSRF, identidad y el código antes de intercambiarlo por token.
5. El secreto de Meta queda únicamente en servidor; tokens cifrados con
   acceso limitado y rotación/renovación, auditoría y revocación.
6. Android recibe únicamente estado **conectado verificado**, permisos
   concedidos y fecha de caducidad. No debe suponer conexión al guardar
   un `@usuario` o indicar que es Creador.
7. Comprobar lectura real de métricas. Publicar solo con autorización
   adecuada, registro de resultados, revisión de contenido y manejo
   de errores/cuotas.

**Bloqueadores reales:** no se conoce todavía el identificador de una
aplicación Meta registrada específicamente para SKY, su URL HTTPS de
retorno ni un backend OAuth configurado. No se pueden completar ni
simular esos pasos desde Android hasta que existan y estén autorizados.

## 4. Pruebas

- Personal o tipo desconocido → no mostrar acceso API como activo.
- Creador/Empresa indicado → solo «preparación»; no «conectado».
- Sin Meta App o backend HTTPS → impedir OAuth y publicación.
- Intentos de importar contraseñas/URLs privadas → rechazar.
- Probar el futuro OAuth con una cuenta bajo los roles permitidos de la
  app y revisar la política de Meta antes de ampliar a usuarios reales.
- La conversión de la cuenta la realiza el propietario en Instagram;
  SKY no cambia la privacidad ni el tipo de cuenta automáticamente.

## Fuentes de Meta

- [Instagram API — Colección oficial de Meta en Postman](https://www.postman.com/meta/instagram/documentation/6yqw8pt/instagram-api)
- [Meta for Developers](https://developers.facebook.com/apps/)
- [Instagram Platform — Business Login](https://developers.facebook.com/docs/instagram-platform/instagram-api-with-instagram-login/business-login)

**El teléfono sigue siendo el núcleo de SKY.** El backend OAuth es un
servicio de credenciales en la nube y no requiere instalar ni mantener
encendido SKY Windows.
