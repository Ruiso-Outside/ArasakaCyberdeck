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

### Windows 10/11

Pela **Arasaka Central** (Loja → Apps), ou extraia o `ArasakaCyberdeck-vX.Y.Z-windows.zip` e dê dois cliques em **`install.bat`**. O instalador instala o Python 3.12 pelo winget (se ainda não houver), cria os atalhos no Menu Iniciar e na Área de Trabalho e o comando `arasaka-cyberdeck`. Não precisa de administrador. Abra e feche com **Ctrl+Alt+Espaço**. No Windows ele acha os programas do Menu Iniciar, os apps da Microsoft Store e os jogos da Steam, e as ações usam os comandos do Windows (bloquear, suspender, reiniciar, desligar).
Para remover: `powershell -ExecutionPolicy Bypass -File uninstall.ps1` (os seus dados são mantidos).

## Privacidade

Nada sai do PC: a busca é local e o Cyberdeck só guarda quantas vezes você abriu cada item
(`~/.config/arasaka-cyberdeck/usage.json`), para ordenar os resultados.

---

Arasaka é marca da CD PROJEKT RED (projeto de fã, sem fins comerciais). A fonte `cedge1` usa a licença
FontStruct Non-Commercial.
