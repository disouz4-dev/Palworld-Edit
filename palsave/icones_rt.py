# -*- coding: utf-8 -*-
"""Carrega em tempo real as miniaturas de icone (PNG) para a interface.

Os PNGs sao gerados por tools/icones.py em dados/icones/<ItemID>.png. Aqui so
carregamos sob demanda como tk.PhotoImage, guardando referencia (senao o Tk
descarta a imagem e ela some).
"""
import os
import tkinter as tk

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIR_ITENS = os.path.join(BASE, "dados", "icones")
DIR_PALS = os.path.join(BASE, "dados", "icones_pals")
_cache = {}

def _carrega(pasta, chave):
    if chave in _cache:
        return _cache[chave]
    p = os.path.join(pasta, chave + ".png")
    img = None
    if os.path.exists(p):
        try:
            img = tk.PhotoImage(file=p)
        except Exception:
            img = None
    _cache[chave] = img
    return img

def item(sid):
    return _carrega(DIR_ITENS, sid)

def pal(cid):
    return _carrega(DIR_PALS, cid)

def tem_itens():
    return os.path.isdir(DIR_ITENS) and any(f.endswith(".png") for f in os.listdir(DIR_ITENS))
