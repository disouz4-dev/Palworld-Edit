# -*- coding: utf-8 -*-
"""Nomes oficiais do jogo (itens, Pals, passivas, habilidades) em portugues.

Os dados sao extraidos do proprio jogo por tools/extrair_traducao.py e ficam em
dados/traducao_<idioma>.json. Aqui so carregamos e oferecemos consultas, com
fallback para o ID interno quando nao houver traducao.
"""
import os, json

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_cache = {}

def carregar(idioma="pt-BR"):
    if idioma in _cache:
        return _cache[idioma]
    p = os.path.join(BASE, "dados", "traducao_%s.json" % idioma)
    try:
        d = json.load(open(p, encoding="utf-8"))
    except Exception:
        d = {"itens": {}, "pals": {}, "passivas": {}, "habilidades": {}, "desc_itens": {}}
    _cache[idioma] = d
    return d

def nome_item(sid, idioma="pt-BR"):
    return carregar(idioma)["itens"].get(sid, sid)

def nome_pal(cid, idioma="pt-BR"):
    return carregar(idioma)["pals"].get(cid, cid)

def nome_passiva(pid, idioma="pt-BR"):
    return carregar(idioma)["passivas"].get(pid, pid)

def desc_item(sid, idioma="pt-BR"):
    return carregar(idioma)["desc_itens"].get(sid, "")

def idiomas_disponiveis():
    d = os.path.join(BASE, "dados")
    if not os.path.isdir(d):
        return ["pt-BR"]
    out = []
    for f in os.listdir(d):
        if f.startswith("traducao_") and f.endswith(".json"):
            out.append(f[len("traducao_"):-len(".json")])
    return sorted(out) or ["pt-BR"]
