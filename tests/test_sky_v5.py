from io import BytesIO
import zipfile, json
import pytest
from PIL import Image, ImageDraw
from neural_core.sky_3d import (leer_imagen,caja_relativa,segmentar_parte,png_bytes,
                                 ensamblar_glb,crear_paquete)
from neural_core.sky_agent import calc,execute_skill,SKILLS
from neural_core import sky_evolution as ev
from neural_core.sky_vision import _check


def demo():
    im=Image.new('RGB',(48,36),'white')
    ImageDraw.Draw(im).rectangle((12,9,29,26),fill='red')
    return im


def test_bbox_validation():
    assert caja_relativa(100,100,.1,.2,.5,.6)==(10,20,50,60)
    with pytest.raises(ValueError):caja_relativa(100,100,.8,.1,.2,.9)
    with pytest.raises(ValueError):caja_relativa(100,100,0,0,1.5,1)


def test_segment_png_and_clear_background():
    part=segmentar_parte(demo(),(10,8,31,28),modo='rectangulo')
    assert part.getpixel((0,0))[-1]==0
    assert part.getpixel((16,16))[-1]==255
    assert Image.open(BytesIO(png_bytes(part))).mode=='RGBA'


def test_grabcut_fallback_never_blanks():
    p=segmentar_parte(demo(),(8,6,33,31),modo='grabcut')
    assert p.getbbox() is not None


def test_glb_assembly_and_zip_parts():
    img=demo(); a=segmentar_parte(img,(10,7,32,30),modo='rectangulo')
    other=segmentar_parte(img,(3,3,9,9),modo='rectangulo')
    parts=[{'name':'Pared','png':png_bytes(a),'depth':.1,'dx':0,'dy':0,'dz':0,'enabled':True},
           {'name':'Ventana','png':png_bytes(other),'depth':.06,'dx':.02,'dy':.01,'dz':.1,'enabled':True}]
    glb=ensamblar_glb(parts,*img.size)
    assert glb[:4]==b'glTF'
    import trimesh
    mesh=trimesh.load(BytesIO(glb),file_type='glb')
    assert len(mesh.geometry)==2
    packed=crear_paquete(parts,png_bytes(img),*img.size)
    with zipfile.ZipFile(BytesIO(packed)) as z:
        assert 'modelo_ensamblado.glb' in z.namelist()
        assert 'piezas/pieza_01.png' in z.namelist()
        assert 'piezas/pieza_02.png' in z.namelist()
        assert len(json.loads(z.read('proyecto_sky.json'))['partes'])==2


def test_no_arbitrary_execution_and_safe_math():
    assert calc('(500-120)*1.15')==pytest.approx(437.0)
    with pytest.raises(ValueError):calc('__import__("os").system("ls")')
    with pytest.raises(ValueError):calc('2**999')
    with pytest.raises(ValueError):execute_skill('shell','echo hola')
    assert len(SKILLS)>=4


def test_local_feedback_and_goals(tmp_path,monkeypatch):
    monkeypatch.setenv('SKY_EVOLUTION_DB',str(tmp_path/'ev.sqlite3'))
    ev.feedback('Studio 3D',5,'Funciona muy bien')
    assert ev.feedback_resumen()[0]['promedio']==5.0
    ev.nueva_meta('Hacer 3 piezas','piezas',3.)
    ident=ev.metas()[0]['id']
    ev.actualizar_meta(ident,2)
    assert ev.metas()[0]['actual']==2
    ev.proponer_mejora('Exportar OBJ','Necesitamos exportar otras mallas.')
    ev.cambiar_mejora(ev.mejoras()[0]['id'],'aprobada_para_desarrollo')
    assert ev.mejoras()[0]['status']=='aprobada_para_desarrollo'


def test_vision_validation():
    blob=png_bytes(demo())
    _check(blob,'image/png')
    with pytest.raises(ValueError): _check(b'junk','image/png')
    with pytest.raises(ValueError): _check(blob,'image/svg+xml')


def test_zip_reopen_project():
    from neural_core.sky_3d import importar_paquete
    img=demo(); part=segmentar_parte(img,(10,6,32,28),modo='rectangulo')
    p=[{'name':'Portón','png':png_bytes(part),'depth':.08,'dx':0,'dy':.15,'dz':0,'enabled':True}]
    packed=crear_paquete(p,png_bytes(img),*img.size)
    restored,parts=importar_paquete(packed)
    assert Image.open(BytesIO(restored)).size==img.size
    assert parts[0]['name']=='Portón'
    assert parts[0]['dy']==.15


def test_zip_bogus_is_rejected():
    from neural_core.sky_3d import importar_paquete
    with pytest.raises((ValueError, zipfile.BadZipFile)):
        importar_paquete(b'no-es-un-proyecto')


def test_local_tool_chat_commands():
    from neural_core.sky_agent import interpret_local_command
    assert interpret_local_command('/sky calcula 2*100')=='Resultado: 200.0'
    assert interpret_local_command('sky, calcula 20+2')=='Resultado: 22.0'
    assert interpret_local_command('/sky ayuda') is not None
    assert interpret_local_command('Hablame de educación') is None


def test_live_monitor_records_and_reads(tmp_path,monkeypatch):
    from neural_core import sky_live as live
    monkeypatch.setenv('SKY_EVOLUTION_DB',str(tmp_path/'live.sqlite3'))
    live.heartbeat()
    live.registrar('baqueano_web',True,120,200,'HTTP correcto')
    records=live.historial()
    assert records[0]['http_code']==200
    assert records[1]['check_name']=='sky_heartbeat'
    with pytest.raises(ValueError):live.registrar('sitio_tercero',True,1,200,'')
