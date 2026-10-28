"""La subasta explica fallos sin exponer credenciales ni respuestas privadas."""
import io
import os
import unittest
import urllib.error
from unittest.mock import patch

from neural_core import sky_ai_diagnostics, sky_cerebro


class TestSkyAiDiagnostics(unittest.TestCase):
    def tearDown(self):
        sky_cerebro.preferir(None)
        from neural_core import sky_ai_auction
        with sky_ai_auction._FALLOS_LOCK:
            sky_ai_auction._FALLOS.clear()

    def test_http_429_quota_without_leaking_provider_message_or_url(self):
        err = urllib.error.HTTPError(
            'https://example.com?key=SKY_SECRET_NEVER_SHOW', 429, 'Private message', {},
            io.BytesIO(b'{"error":{"status":"RESOURCE_EXHAUSTED",'
                       b'"message":"My private API key is SKY_SECRET_NEVER_SHOW"}}'))
        value = sky_ai_diagnostics.error_seguro('gemini', err)
        self.assertIn('GEMINI HTTP 429', value)
        self.assertIn('RESOURCE_EXHAUSTED', value)
        self.assertNotIn('SKY_SECRET_NEVER_SHOW', value)
        self.assertNotIn('Private message', value)

    def test_openai_429_billing_code_is_different_from_rate(self):
        err = urllib.error.HTTPError(
            'https://test.invalid/secret=NEVER_SHOW', 429, 'private', {},
            io.BytesIO(b'{"error":{"code":"credit_balance_exhausted",'
                       b'"message":"NEVER_SHOW private details"}}'))
        value = sky_ai_diagnostics.error_seguro('openai', err)
        self.assertIn('credit_balance_exhausted', value)
        self.assertIn('saldo agotado', value)
        self.assertNotIn('NEVER_SHOW', value)

    def test_groq_restricted_model_code_without_raw_message(self):
        err = urllib.error.HTTPError(
            'https://host.invalid/?key=NEVER_SHOW', 403, 'private', {},
            io.BytesIO(b'{"error":{"code":"model_permission_blocked_project",'
                       b'"message":"NEVER_SHOW private content"}}'))
        texto = sky_ai_diagnostics.error_seguro('groq', err)
        self.assertIn('model_permission_blocked_project', texto)
        self.assertIn('permisos', texto)
        self.assertNotIn('NEVER_SHOW', texto)

    def test_anthropic_400_spending_limit_classified_without_message(self):
        err = urllib.error.HTTPError(
            'https://host.invalid/', 400, 'private', {},
            io.BytesIO(b'{"error":{"type":"invalid_request_error",'
                       b'"message":"You have reached your organization spending limit. NEVER_SHOW"}}'))
        texto = sky_ai_diagnostics.error_seguro('anthropic', err)
        self.assertIn('posible limite de gasto', texto)
        self.assertNotIn('NEVER_SHOW', texto)

    def test_http_404_model_and_nonjson_body(self):
        err = urllib.error.HTTPError(
            'https://host.test/key=SECRET', 404, 'bad', {},
            io.BytesIO(b'the key SECRET is invalid'))
        value = sky_ai_diagnostics.error_seguro('openai', err)
        self.assertIn('OPENAI HTTP 404', value)
        self.assertIn('modelo', value)
        self.assertNotIn('SECRET', value)

    def test_redact_urlerror(self):
        err = urllib.error.URLError('SKY_SECRET_NEVER_SHOW')
        self.assertNotIn('SKY_SECRET_NEVER_SHOW',
                         sky_ai_diagnostics.error_seguro('gemini', err))

    def test_auction_reports_each_provider_failure(self):
        def fake_events(provider, texto, history, modo, info):
            if provider == 'gemini':
                yield 'error', 'GEMINI HTTP 429: cuota agotada'
            else:
                yield 'error', 'OPENAI HTTP 401: autenticacion rechazada'

        with patch.dict(os.environ, {'SKY_CEREBRO':'subasta','SKY_LOCAL_ONLY':'0'}, clear=False), \
             patch('neural_core.sky_ai_auction.ofertas',
                   return_value=[{'proveedor':'gemini'}, {'proveedor':'openai'}]), \
             patch('neural_core.sky_cerebro._eventos_nube', side_effect=fake_events), \
             patch('neural_core.sky_metricas.registrar'):
            sky_cerebro.preferir(None)
            result = sky_cerebro.decidir('Explica la fotosintesis', modo='chat')
        self.assertEqual(result['tipo'], 'error')
        self.assertIn('gemini', result['mensaje'])
        self.assertIn('openai', result['mensaje'])
        self.assertIn('429', result['mensaje'])
        self.assertIn('401', result['mensaje'])

    def test_partial_response_never_retries_cloud(self):
        def fake_events(provider, texto, history, modo, info):
            yield 'delta', 'respuesta parcial'
            yield 'error', 'GEMINI HTTP 503: servicio indisponible'

        with patch.dict(os.environ, {'SKY_CEREBRO':'subasta','SKY_LOCAL_ONLY':'0'}, clear=False), \
             patch('neural_core.sky_ai_auction.ofertas',
                   return_value=[{'proveedor':'gemini'}, {'proveedor':'openai'}]), \
             patch('neural_core.sky_cerebro._eventos_nube', side_effect=fake_events) as requests, \
             patch('neural_core.sky_metricas.registrar'):
            sky_cerebro.preferir(None)
            answer = sky_cerebro.decidir('Explica', modo='chat')
            self.assertEqual(answer['tipo'], 'error')
            self.assertEqual(requests.call_count, 1)

    def test_invalid_api_response_never_discloses_internal_exception_text(self):
        exc = RuntimeError('SKY_SECRET_NEVER_SHOW')
        self.assertNotIn('SKY_SECRET_NEVER_SHOW',
                         sky_ai_diagnostics.error_seguro('openai', exc))


if __name__ == '__main__':
    unittest.main()
