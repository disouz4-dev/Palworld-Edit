<p align="center">
  <img src="assets/logo.png" alt="Palworld Editor" width="360">
</p>

<h1 align="center">Palworld Editor</h1>

<p align="center">
  Editor de save moderno para <b>Palworld (versao Xbox / Microsoft Store / Game Pass)</b> — itens, personagem e Pals.
  <br>
  <b>🇧🇷 Portugues</b> · <a href="README.md">🇺🇸 English</a>
</p>

---

> **Ferramenta nao oficial.** Sem vinculo com a Pocketpair. Use so com um save de um jogo que voce possui. Veja o [AVISO](NOTICE.md).

## Recursos

- **Itens** — altere qualquer quantidade, adicione itens que voce nao tem, por bau / armazem / inventario, com os **nomes e icones do jogo**.
- **Personagem** — nivel, experiencia e pontos de atributo.
- **Pals** — nivel, sexo, IVs (Vida/Ataque/Defesa), rank de alma e as 4 passivas, com o botao **"sugerir melhores passivas"**.
- **Tema claro / escuro** moderno (Fluent do Windows 11).
- **Backups automaticos** e restauracao com um clique. Uma copia intocada do seu save original fica guardada para sempre.

Feito para a versao **Xbox/GDK** do Palworld (aquela cujos saves ficam em
`%LOCALAPPDATA%\Packages\PocketpairInc.Palworld_*`), que os editores comuns de
Steam nao conseguem ler.

## Instalar (Windows)

Abra o **PowerShell** e rode:

```powershell
git clone https://github.com/disouz4-dev/Palworld-Edit.git
cd Palworld-Edit
powershell -ExecutionPolicy Bypass -File install.ps1
```

O instalador verifica o **Python** (instala se faltar), instala as dependencias
e cria um **atalho na Area de Trabalho** com o icone do app. Depois e so abrir
o **Palworld Editor** pela Area de Trabalho.

> Sem git? Baixe o ZIP no botao verde **Code** do GitHub, extraia e rode o
> `install.ps1` dentro da pasta.

## Como usar

1. **Feche o Palworld** antes de salvar (o jogo reescreve o save ao sair).
2. Abra o app e escolha o seu mundo.
3. Edite em **Itens / Personagem / Pals** e clique em **SALVAR NO JOGO**.
4. Se algo der errado no jogo, use **Restaurar backup** na tela inicial.

## Opcional: regerar nomes/icones a partir do jogo

Os nomes em portugues ja vem no repositorio. Os icones e outros idiomas sao
gerados a partir dos seus proprios arquivos do jogo (sao conteudo do jogo e nao
sao redistribuidos). Isso precisa da DLL do **Oodle** (a que o FModel baixa da
fonte oficial da Epic). Crie o `extracao_local.json` na raiz do projeto:

```json
{
  "paks":  "X:\...\Palworld\Pal\Content\Paks",
  "oodle": "X:\...\oodle-data-shared.dll"
}
```

Depois rode os scripts em `tools/` (`extrair_traducao.py`, `icones.py`).

## Como funciona

O save do Xbox tem quatro camadas, todas decodificadas na mao em Python:
`containers.index (WGS) → container.N → CNK0 → PlZ2 (zlib duplo) → GVAS`.
O leitor/escritor devolve o save **byte a byte identico** quando nada e editado.
Os nomes e icones de itens/Pals sao lidos direto do IoStore do jogo
(`.utoc`/`.ucas`) usando o descompressor Oodle — sem precisar exportar no FModel.

## Licenca

[MIT](LICENSE). Nomes e arte pertencem a Pocketpair — veja o [AVISO](NOTICE.md).
