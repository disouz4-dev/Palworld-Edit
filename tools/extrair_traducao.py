# -*- coding: utf-8 -*-
"""Extrai os textos oficiais do jogo (nomes de itens, Pals, passivas, habilidades)
direto do IoStore do Palworld, para o idioma escolhido. Sem FModel, sem usmap.

As DataTables de texto localizadas ficam em L10N/<idioma>/.../DT_*Text*.uasset.
Cada linha aparece no bloco de export como o trio de FStrings:
    [nome da tabela]  [CHAVE_TextData]  [valor traduzido]
Basta parear CHAVE (sem o sufixo _TextData) com o valor seguinte.
"""
import sys, os, struct, re, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import iostore

def fstrings(buf):
    out=[]; i=0; n=len(buf)
    while i<n-4:
        ln=struct.unpack_from("<i",buf,i)[0]
        if ln<0 and -ln<600:
            nb=-ln; s=buf[i+4:i+4+nb*2]
            if len(s)==nb*2 and s[-2:]==b"\x00\x00":
                try:
                    txt=s[:-2].decode("utf-16-le"); out.append(txt); i+=4+nb*2; continue
                except Exception: pass
        elif 1<ln<400:
            s=buf[i+4:i+4+ln]
            if len(s)==ln and s[-1:]==b"\x00" and all(32<=c<127 for c in s[:-1]):
                out.append(s[:-1].decode()); i+=4+ln; continue
        i+=1
    return out

def extrair_idioma(idioma):
    t=iostore.carregar(); idx=iostore._dir_index(t)
    pasta="L10N/%s/Pal/DataTable/Text/" % idioma
    tabelas=[k for k in idx if pasta in k and k.endswith(".uasset")]
    chave_valor={}
    for k in tabelas:
        try:
            b=iostore.extrair(t, idx[k])
            hsize=struct.unpack_from("<I",b,4)[0]
            ss=fstrings(b[hsize:])
        except Exception as ex:
            print("  falha em", k.split("/")[-1], ex); continue
        for j,s in enumerate(ss):
            if s.endswith("_TextData") and j+1<len(ss):
                chave_valor[s[:-9]]=ss[j+1]
    return chave_valor

def mapa(cv, prefixo):
    out={}
    for k,v in cv.items():
        if k.startswith(prefixo): out[k[len(prefixo):]]=v
    return out

if __name__=="__main__":
    idioma = sys.argv[1] if len(sys.argv)>1 else "pt-BR"
    print("extraindo idioma:", idioma)
    cv=extrair_idioma(idioma)
    print("chaves totais:", len(cv))
    dados={
        "idioma": idioma,
        "itens": mapa(cv,"ITEM_NAME_"),
        "pals":  mapa(cv,"PAL_NAME_"),
        "passivas": mapa(cv,"PASSIVE_"),
        "habilidades": mapa(cv,"ACTION_SKILL_"),
        "desc_itens": mapa(cv,"ITEM_DESC_"),
    }
    # prefixos de passiva/skill podem variar: descobre os mais comuns
    import collections
    pref=collections.Counter(k.rsplit("_",1)[0].split("_")[0]+"_" for k in cv)
    for nome,m in dados.items():
        if isinstance(m,dict): print("  %-12s %d" % (nome, len(m)))
    out=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),"dados","traducao_%s.json"%idioma)
    json.dump(dados, open(out,"w",encoding="utf-8"), ensure_ascii=False, indent=0)
    print("salvo:", out)
    # amostra de prefixos para achar passivas/skills
    print("\nprefixos de chave mais comuns:", pref.most_common(15))
