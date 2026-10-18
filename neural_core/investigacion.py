"""Consultas bajo petición: Wikipedia ES; no es un buscador de noticias ni financiero."""
from urllib import request, parse
import json

def wikipedia(busqueda, limite=5):
    busqueda=busqueda.strip()[:180]
    if not busqueda:
        return []
    url='https://es.wikipedia.org/w/api.php?'+parse.urlencode({
        'action':'query','list':'search','srsearch':busqueda,'srlimit':min(5,limite),
        'format':'json','utf8':'1','srprop':''})
    solicitud=request.Request(url,headers={'User-Agent':'NeuralTUniversalPersonal/1.0 (personal research client)'})
    with request.urlopen(solicitud,timeout=12) as r:
        dat=json.load(r)
    return [{'titulo':e['title'],'url':'https://es.wikipedia.org/wiki/'+parse.quote(e['title'].replace(' ','_'))}
            for e in dat.get('query',{}).get('search',[])]
