# -*- coding: utf-8 -*-
"""Resolve os caminhos do jogo e do Oodle usados so pela extracao de traducao.

Ordem de resolucao: variavel de ambiente > arquivo extracao_local.json (que
NAO vai para o repositorio) > vazio. Assim o codigo publico nao carrega caminhos
da maquina de ninguem.
"""
import os, json

_RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_cfg = {}
try:
    _cfg = json.load(open(os.path.join(_RAIZ, "extracao_local.json"), encoding="utf-8"))
except Exception:
    pass

def paks_dir():
    """Pasta .../Pal/Content/Paks do jogo instalado."""
    return os.environ.get("PALWORLD_PAKS") or _cfg.get("paks") or ""

def oodle_dll():
    """Caminho do oodle-data-shared.dll (ou oo2core_9_win64.dll)."""
    return os.environ.get("OODLE_DLL") or _cfg.get("oodle") or ""

def pak_file():
    return os.path.join(paks_dir(), "Pal-WinGDK.pak")

def iostore_base():
    return os.path.join(paks_dir(), "Pal-WinGDK")
