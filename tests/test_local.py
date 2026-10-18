import io
import zipfile
import pytest
from PIL import Image
from neural_core.mercados import rentabilidad_historica, cripto_precios
from neural_core.monetizacion import simular_ventas, resumen_comercial, agregar_cliente, listar_clientes, cambiar_etapa, crear_tablas
from neural_core.creadores import campana
from neural_core.seguridad import revisar_archivo
from neural_core.multimedia import convertir_imagen
from neural_core import storage


def test_rendimiento():
    assert rentabilidad_historica(100,110)==pytest.approx(10)
    with pytest.raises(ValueError): rentabilidad_historica(0,1)


def test_escenario():
    r=simular_ventas(25,100,5,50)
    assert r['ventas_esperadas']==5
    assert r['margen_proyectado']==75
    with pytest.raises(ValueError): simular_ventas(25,50,110,10)


def test_cripto_validacion_antes_de_red():
    with pytest.raises(ValueError): cripto_precios(['moneda-falsa'])


def test_generador_publicitario():
    text=campana('Baqueano','turistas','diseño de rutas','US$30','TikTok')
    assert 'Baqueano' in text and 'CTA' in text


def test_security_y_zip_sospechoso():
    report=revisar_archivo('secrets.py',b'api_key = "abcdef1234567890"')
    assert any('credencial' in x for x in report['observaciones'])
    b=io.BytesIO()
    with zipfile.ZipFile(b, 'w') as z: z.writestr('../escapar.txt','x')
    report=revisar_archivo('b.zip',b.getvalue())
    assert any('traversal' in x for x in report['observaciones'])


def test_conversion_imagen():
    b=io.BytesIO()
    Image.new('RGB',(600,300),'white').save(b,format='PNG')
    out,size=convertir_imagen(b.getvalue(),'WEBP',80,400)
    assert out[:4]==b'RIFF'
    assert size==(400,200)


def test_embudo_crm_sqlite_temporal(tmp_path, monkeypatch):
    monkeypatch.setattr(storage,'DB',tmp_path/'test.sqlite3')
    storage.iniciar(); crear_tablas()
    agregar_cliente('Comercio local','Contenido digital',100,'USD','propuesta')
    r=resumen_comercial()
    assert r['USD']['potencial']==100
    assert r['USD']['estimado']==65
    registro=listar_clientes()[0]
    cambiar_etapa(registro['id'],'ganado')
    r=resumen_comercial()
    assert r['USD']['confirmado']==100
    assert r['USD']['potencial']==0
