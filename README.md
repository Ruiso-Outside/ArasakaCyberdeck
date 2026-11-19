# ARASAKA CYBERDECK

Lançador rápido com o visual da Arasaka para **Zorin OS e Ubuntu**. Aperte **Ctrl+Alt+Espaço**, digite
umas letras e aperte Enter.

## O que ele abre

| Tipo | De onde vem |
|---|---|
| **Apps** | Os mesmos do menu do sistema, inclusive Flatpak e Snap |
| **Jogos** | Os jogos instalados na Steam (também os da biblioteca em outro disco) |
| **VMs** | As máquinas virtuais do **Arasaka Blackwall**: Enter liga a VM direto |
| **Módulos** | Os módulos instalados na **Arasaka Central**: abre a Central já no módulo |
| **Pastas** | Pasta pessoal, Documentos, Downloads, Imagens... |
| **Ações** | Bloquear a tela, suspender, encerrar a sessão, reiniciar e desligar (esses dois perguntam antes) |
| **Contas** | Digite `2+3*4` ou `1250*0,15`: o resultado aparece e Enter copia |

A busca entende o começo das palavras (`blackw`), as iniciais (`ad` → Arasaka Daemon), palavras-chave do
app (`navegador` → Firefox) e letras puladas (`ffox` → Firefox). O que você abre mais vai subindo na lista, e
com a busca vazia aparecem os mais usados.

## Teclas

| Tecla | Faz |
|---|---|
| **Ctrl+Alt+Espaço** | Abre (de novo: fecha) |
| **Enter** | Abre o item escolhido |
| **↑ ↓** ou **Tab** | Escolhe |
| **Ctrl+1 … Ctrl+9** | Abre direto o item daquela posição |
| **Esc** ou clicar fora | Fecha |

Para trocar o atalho: Configurações > Teclado > Atalhos personalizados > Arasaka Cyberdeck (ou instale
com `./install.sh --atalho='<Super>space'`).

## Instalar

Pela **Arasaka Central** (Loja → Apps), ou:

```bash
./install.sh
```

Rode **sem sudo**. Para remover: `./uninstall.sh` (tira também o atalho de teclado).

## Privacidade

Nada sai do PC: a busca é local e o Cyberdeck só guarda quantas vezes você abriu cada item
(`~/.config/arasaka-cyberdeck/usage.json`), para ordenar os resultados.

---

Arasaka é marca da CD PROJEKT RED (projeto de fã, sem fins comerciais). A fonte `cedge1` usa a licença
FontStruct Non-Commercial.
