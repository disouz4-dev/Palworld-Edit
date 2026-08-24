# -*- coding: utf-8 -*-
"""Motor de breeding (reproducao) do Palworld.

Replica o algoritmo do jogo:
  - Se o par (A,B) e uma combinacao unica, o filho e o dela.
  - Se A e B sao a mesma especie, o filho e ela mesma.
  - Senao, filho = a especie cujo combiRank e o mais proximo de
    (rankA + rankB + 1) // 2, com desempate por combiPriority maior.
    As especies-filho de combos unicos e as ignoreCombi ficam de fora desse
    calculo (so nascem pela via unica).

Dados (combiRank, elementos, combos) vem de dados/breeding.json, extraido do
jogo (via palworld.gg). Ver NOTICE: pertencem a Pocketpair.
"""
import os, json

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_eng = None


class Breeding(object):
    def __init__(self, dados):
        self.pals = dados["pals"]
        self.combos = dados["combos"]                 # [[A, B, filho], ...]
        # combos unicos indexados por par
        self.por_par = {}
        self.filhos_unicos = set()
        for a, b, c in self.combos:
            self.por_par[(a, b)] = c
            self.por_par[(b, a)] = c
            if a != c or b != c:                      # combo "de verdade" (nao so self)
                self.filhos_unicos.add(c)
        # tabela X[rank] = especie mais proxima daquele rank
        elegiveis = [k for k, v in self.pals.items()
                     if v.get("combiRank") and v["combiRank"] != 9999 and not v.get("isBoss")]
        fs = [k for k in elegiveis
              if k not in self.filhos_unicos and not self.pals[k].get("ignoreCombi")]
        self._fs = fs
        self._maxrank = max(self.pals[k]["combiRank"] for k in elegiveis) + 1
        self._X = {}

    def _melhor_para_rank(self, rank):
        if rank in self._X:
            return self._X[rank]
        melhor = None
        md = 1e18
        for k in self._fs:
            v = self.pals[k]
            d = abs(v["combiRank"] - rank)
            if d < md or (d == md and melhor is not None
                          and v["combiPriority"] > self.pals[melhor]["combiPriority"]):
                md = d
                melhor = k
        self._X[rank] = melhor
        return melhor

    def filho(self, a, b):
        """Especie que nasce de A x B (ou None se desconhecido)."""
        if (a, b) in self.por_par:
            return self.por_par[(a, b)]
        if a == b:
            return a
        if a not in self.pals or b not in self.pals:
            return None
        rank = (self.pals[a]["combiRank"] + self.pals[b]["combiRank"] + 1) // 2
        return self._melhor_para_rank(min(rank, self._maxrank))

    def pares_para(self, alvo, disponiveis):
        """Todos os pares (A,B) entre 'disponiveis' que geram 'alvo'.
        Retorna [(A, B, 'unico'|'normal')]. 'disponiveis' = conjunto de especies."""
        disp = sorted(set(disponiveis))
        out = []
        # combos unicos
        for a, b, c in self.combos:
            if c == alvo and a in disp and b in disp and (a != c or b != c):
                out.append((a, b, "unico"))
        vistos = set((a, b) for a, b, _ in out) | set((b, a) for a, b, _ in out)
        # via rank
        for i in range(len(disp)):
            for j in range(i, len(disp)):
                a, b = disp[i], disp[j]
                if (a, b) in self.por_par:
                    continue                         # ja e um combo unico
                if (a, b) in vistos:
                    continue
                if self.filho(a, b) == alvo:
                    out.append((a, b, "normal"))
        return out

    def nome(self, key, traducao=None):
        if traducao is not None:
            n = traducao(key)
            if n and n != key:
                return n
        return self.pals.get(key, {}).get("name", key)


def carregar():
    global _eng
    if _eng is None:
        p = os.path.join(BASE, "dados", "breeding.json")
        _eng = Breeding(json.load(open(p, encoding="utf-8")))
    return _eng
