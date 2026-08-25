# -*- coding: utf-8 -*-
"""Decodificador Oodle opcional.

O save do JOGADOR (Players/*.sav) e comprimido com Oodle (PlM1). O jogo linka o
Oodle estaticamente, entao nao existe DLL separada nele. Para LER esse save
precisamos de um Oodle qualquer (ex.: o `oodle-data-shared.dll` do FModel, ou um
`oo2core_*.dll` de outro jogo UE). Ao GRAVAR, reescrevemos como zlib (PlZ), que o
jogo tambem le -- entao so precisamos DESCOMPRIMIR com Oodle, nunca comprimir.

Se nenhum Oodle for encontrado, os recursos que dependem do save do jogador
(pontos de tecnologia) ficam indisponiveis, mas o resto do editor funciona.
"""
import os, glob, ctypes

_dll = None
_caminho = None


def _candidatos(config_path=None):
    c = []
    if config_path:
        c.append(config_path)
    if os.environ.get("OODLE_DLL"):
        c.append(os.environ["OODLE_DLL"])
    la = os.environ.get("LOCALAPPDATA", "")
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    alvos = ("oodle-data-shared.dll", "oo2core_9_win64.dll", "oo2core_8_win64.dll")
    # os.walk (ao contrario do glob) entra em pastas ocultas como o '.data' do FModel.
    # Raizes LIMITADAS para nao varrer a home inteira.
    raizes = [os.path.join(base, "fmodel"), os.path.join(la, "FModel"), base]
    for raiz in raizes:
        if not os.path.isdir(raiz):
            continue
        for dirpath, _dirs, arqs in os.walk(raiz):
            for nome in alvos:
                if nome in arqs:
                    c.append(os.path.join(dirpath, nome))
            if dirpath.count(os.sep) - raiz.count(os.sep) >= 6:
                _dirs[:] = []                 # limita a profundidade
    vistos, out = set(), []
    for x in c:
        if x and x not in vistos and os.path.isfile(x):
            vistos.add(x); out.append(x)
    return out


def carregar(config_path=None):
    """Tenta carregar um Oodle. Retorna o caminho usado, ou None."""
    global _dll, _caminho
    if _dll is not None:
        return _caminho
    for cam in _candidatos(config_path):
        try:
            d = ctypes.CDLL(cam)
            d.OodleLZ_Decompress.restype = ctypes.c_longlong
            d.OodleLZ_Decompress.argtypes = [
                ctypes.c_char_p, ctypes.c_longlong, ctypes.c_char_p, ctypes.c_longlong,
                ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_void_p, ctypes.c_longlong,
                ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_longlong, ctypes.c_int]
            _dll, _caminho = d, cam
            return cam
        except Exception:
            continue
    return None


def disponivel(config_path=None):
    return carregar(config_path) is not None


def decompress(comp, unc_size, config_path=None):
    if carregar(config_path) is None:
        raise RuntimeError("Oodle indisponivel (nenhum DLL encontrado)")
    out = ctypes.create_string_buffer(unc_size)
    n = _dll.OodleLZ_Decompress(comp, len(comp), out, unc_size, 0, 0, 0, None, 0,
                                None, None, None, 0, 3)
    if n != unc_size:
        raise RuntimeError("Oodle devolveu %d, esperado %d" % (n, unc_size))
    return out.raw[:unc_size]
