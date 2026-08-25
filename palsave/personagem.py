# -*- coding: utf-8 -*-
"""Le e edita os dados do personagem do jogador (dentro do Level.sav).

Em CharacterSaveParameterMap cada personagem tem um RawData que e, por dentro,
outra lista de propriedades no formato GVAS. Ali ficam nivel, experiencia,
pontos de status nao gastos e os pontos ja distribuidos em cada atributo.

O decodificador da palworld-save-tools quebra aqui porque e de uma versao
antiga do jogo: ele exige que os bytes acabem exatamente onde ele espera, e na
v1.0 sobra coisa no fim. A solucao e ler as propriedades e guardar o resto como
um bloco opaco, devolvido intacto na hora de gravar.

Os pontos de tecnologia NAO estao aqui - ficam em Players/*.sav, que usa Oodle.
"""
from palworld_save_tools.archive import FArchiveReader, FArchiveWriter

# nome interno do atributo (o jogo guarda em japones) -> rotulo em portugues
ATRIBUTOS = {
    "最大HP": "Vida (HP)",
    "最大SP": "Estamina",
    "攻撃力": "Ataque",
    "所持重量": "Peso carregado",
    "持ち運び重量": "Peso carregado",
    "捕獲率": "Taxa de captura",
    "作業速度": "Velocidade de trabalho",
    "移動速度アップ": "Velocidade de movimento",
    "空腹率低減": "Reducao da fome",
    "経験値ボーナス": "Bonus de experiencia",
    "泳ぎ速度": "Velocidade de nado",
    "ジャンプ力": "Altura do pulo",
    "状態異常耐性": "Resistencia a efeitos",
    "パルスフィアホーミング": "Mira das Pal Spheres",
    "虹パッシブ率": "Chance de passiva arco-iris",
    "食料腐敗低減": "Reducao do apodrecimento",
    "滑空速度": "Velocidade de planeio",
    "崖登り速度": "Velocidade de escalada",
    "MaxHP": "Vida (HP)",
    "MaxSP": "Estamina",
    "Attack": "Ataque",
    "MaxInventoryWeight": "Peso carregado",
    "CaptureRate": "Taxa de captura",
    "WorkSpeed": "Velocidade de trabalho",
}


def _rotulo(nome):
    return ATRIBUTOS.get(nome, nome)


class Personagem(object):
    """Um personagem do CharacterSaveParameterMap, com o RawData ja aberto."""

    def __init__(self, entrada):
        self.entrada = entrada
        self._prop = entrada["value"]["RawData"]
        brutos = bytes(self._prop["value"]["values"])
        r = FArchiveReader(brutos)
        self.obj = r.properties_until_end()
        self.cauda = r.data.read()          # bytes finais, devolvidos como estao
        self.sp = self.obj.get("SaveParameter", {}).get("value", {})

    # ---------- leitura ----------
    @property
    def e_jogador(self):
        return bool(self.sp.get("IsPlayer", {}).get("value"))

    @property
    def apelido(self):
        return self.sp.get("NickName", {}).get("value")

    def _num(self, chave):
        n = self.sp.get(chave)
        if n is None:
            return None
        v = n.get("value")
        if isinstance(v, dict):                      # FixedPoint64 etc.
            v = v.get("Value", {}).get("value", v)
        return v

    @property
    def nivel(self):
        return self._num("Level")

    @property
    def exp(self):
        return self._num("Exp")

    @property
    def pontos_livres(self):
        return self._num("UnusedStatusPoint")

    def _lista(self, chave):
        n = self.sp.get(chave)
        if not n:
            return []
        return n["value"]["values"]

    def status(self):
        """[(chave_interna, rotulo, pontos, no_dict)] dos atributos."""
        out = []
        for lista in ("GotStatusPointList", "GotExStatusPointList"):
            for it in self._lista(lista):
                nome = it["StatusName"]["value"]
                out.append((lista, _rotulo(nome), it["StatusPoint"]["value"], it))
        return out

    # ---------- escrita ----------
    def set_nivel(self, v):
        if "Level" in self.sp:
            self.sp["Level"]["value"] = int(v)

    def set_exp(self, v):
        if "Exp" in self.sp:
            self.sp["Exp"]["value"] = int(v)

    def set_pontos_livres(self, v):
        if "UnusedStatusPoint" in self.sp:
            self.sp["UnusedStatusPoint"]["value"] = int(v)

    @staticmethod
    def set_status(no, v):
        no["StatusPoint"]["value"] = int(v)

    def gravar(self):
        """Serializa de volta para o RawData da entrada."""
        w = FArchiveWriter()
        w.properties(self.obj)
        dados = w.bytes() + self.cauda
        self._prop["value"]["values"] = list(dados)


def jogadores(level):
    """Todos os personagens que sao jogadores."""
    out = []
    for ent in level.ws["CharacterSaveParameterMap"]["value"]:
        brutos = bytes(ent["value"]["RawData"]["value"]["values"])
        if b"IsPlayer" not in brutos:
            continue
        try:
            p = Personagem(ent)
        except Exception:
            continue
        if p.e_jogador:
            out.append(p)
    return out


# ---------------------------------------------------------------------------
# Extensao: tratamento de Pals (personagens que nao sao o jogador)
# ---------------------------------------------------------------------------

def _set_num(node, v):
    """Escreve um numero respeitando se o value e escalar ou {'type','value'}."""
    if isinstance(node.get("value"), dict) and "value" in node["value"]:
        node["value"]["value"] = int(v)
    else:
        node["value"] = int(v)


def _get_num(node):
    if node is None:
        return None
    v = node.get("value")
    if isinstance(v, dict):
        return v.get("value")
    return v


class PalWrap(object):
    """Envolve uma entrada de CharacterSaveParameterMap que e um Pal."""

    TALENTOS = [("Talent_HP", "Vida"), ("Talent_Shot", "Ataque"),
                ("Talent_Melee", "Corpo a corpo"), ("Talent_Defense", "Defesa")]

    def __init__(self, entrada):
        self.entrada = entrada
        self._prop = entrada["value"]["RawData"]
        brutos = bytes(self._prop["value"]["values"])
        r = FArchiveReader(brutos)
        self.obj = r.properties_until_end()
        self.cauda = r.data.read()
        self.sp = self.obj.get("SaveParameter", {}).get("value", {})

    # leitura
    @property
    def e_jogador(self):
        return bool(self.sp.get("IsPlayer", {}).get("value"))

    @property
    def especie(self):
        return self.sp.get("CharacterID", {}).get("value", "")

    @property
    def nivel(self):
        return _get_num(self.sp.get("Level")) or 1

    @property
    def genero(self):
        g = self.sp.get("Gender", {}).get("value")
        if isinstance(g, dict):
            g = g.get("value", "")
        return "F" if "Female" in str(g) else ("M" if "Male" in str(g) else "?")

    def talento(self, chave):
        return _get_num(self.sp.get(chave)) or 0

    @property
    def passivas(self):
        n = self.sp.get("PassiveSkillList")
        if not n:
            return []
        return list(n["value"]["values"])

    @property
    def rank(self):
        return _get_num(self.sp.get("Rank")) or 1

    # escrita
    def set_nivel(self, v):
        if "Level" in self.sp:
            _set_num(self.sp["Level"], v)

    def set_genero(self, mf):
        alvo = "EPalGenderType::Female" if mf.upper().startswith("F") else "EPalGenderType::Male"
        g = self.sp.get("Gender")
        if g and isinstance(g.get("value"), dict):
            g["value"]["value"] = alvo

    def set_talento(self, chave, v):
        if chave in self.sp:
            _set_num(self.sp[chave], max(0, min(int(v), 100)))

    def set_passivas(self, lista):
        n = self.sp.get("PassiveSkillList")
        lista = [x for x in lista if x][:4]
        if n:
            n["value"]["values"] = lista
        elif lista:
            # cria a propriedade a partir de um molde nao existe; ignora se ausente
            pass

    def set_rank(self, v):
        if "Rank" in self.sp:
            _set_num(self.sp["Rank"], max(1, min(int(v), 5)))

    # -------- injecao (muitos Pals nao guardam o campo quando esta no padrao) --------
    def _garante(self, chave, molde):
        import copy
        if chave not in self.sp and molde is not None:
            self.sp[chave] = copy.deepcopy(molde)

    def set_condensacao_estrelas(self, estrelas, molde=None):
        """estrelas 0-4 -> campo Rank 1-5 (cria o campo se faltar)."""
        self._garante("Rank", molde)
        if "Rank" in self.sp:
            _set_num(self.sp["Rank"], max(1, min(int(estrelas) + 1, 5)))

    def set_talento_f(self, chave, v, molde=None):
        self._garante(chave, molde)
        if chave in self.sp:
            _set_num(self.sp[chave], max(0, min(int(v), 100)))

    def set_passivas_f(self, lista, molde=None):
        lista = [x for x in lista if x][:4]
        self._garante("PassiveSkillList", molde)
        n = self.sp.get("PassiveSkillList")
        if n:
            n["value"]["values"] = lista

    # almas da Estatua do Poder (GotExStatusPointList existe em todos os Pals)
    _ALMA_JP = {"hp": "最大HP", "sp": "最大SP", "atk": "攻撃力",
                "peso": "所持重量", "trabalho": "作業速度"}

    def set_alma(self, qual, valor):
        campo = self.sp.get("GotExStatusPointList")
        jp = self._ALMA_JP.get(qual)
        if not campo or not jp:
            return
        for e in campo["value"]["values"]:
            if e.get("StatusName", {}).get("value") == jp:
                _set_num(e["StatusPoint"], int(valor))
                return

    def set_aptidoes(self, enum_rank, molde_lista=None):
        """enum_rank: {'Mining': 4, ...} (nome do enum). Cria/substitui a lista."""
        import copy
        self._garante("GotWorkSuitabilityAddRankList", molde_lista)
        campo = self.sp.get("GotWorkSuitabilityAddRankList")
        if not campo:
            return
        base = campo["value"]["values"]
        modelo = copy.deepcopy(base[0]) if base else None
        if modelo is None:
            return
        novos = []
        for work, rank in enum_rank.items():
            e = copy.deepcopy(modelo)
            e["WorkSuitability"]["value"]["value"] = "EPalWorkSuitability::" + work
            _set_num(e["Rank"], int(rank))
            novos.append(e)
        campo["value"]["values"] = novos

    def gravar(self):
        w = FArchiveWriter()
        w.properties(self.obj)
        self._prop["value"]["values"] = list(w.bytes() + self.cauda)


def moldes(pals):
    """Coleta 'moldes' de campos que muitos Pals nao guardam, para poder injeta-los."""
    campos = ("Level", "Rank", "Talent_HP", "Talent_Shot", "Talent_Defense",
              "PassiveSkillList", "GotWorkSuitabilityAddRankList")
    m = {}
    for c in campos:
        if c == "GotWorkSuitabilityAddRankList":
            m[c] = next((p.sp[c] for p in pals
                         if c in p.sp and p.sp[c]["value"]["values"]), None)
        else:
            m[c] = next((p.sp[c] for p in pals if c in p.sp), None)
    # Rank (condensacao) e um ByteProperty simples: se NENHUM Pal tem (save sem
    # nenhum condensado), montamos o molde do zero para a condensacao sempre valer.
    if m["Rank"] is None:
        m["Rank"] = {"id": None, "value": {"type": "None", "value": 1}, "type": "ByteProperty"}
    return m


def pals_do_mundo(level):
    """Todos os Pals (nao-jogadores) que da para editar."""
    out = []
    for ent in level.ws["CharacterSaveParameterMap"]["value"]:
        rb = bytes(ent["value"]["RawData"]["value"]["values"])
        if b"IsPlayer" in rb:
            continue
        try:
            p = PalWrap(ent)
        except Exception:
            continue
        if p.especie:
            out.append(p)
    return out
