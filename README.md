# ⚔ Tartantis VTT

![Build](https://github.com/Sampsvsl/Tartantis-VTT/actions/workflows/build.yml/badge.svg)

**A mesa virtual de RPG gratuita, open source e feita de fã para fãs de Mighty Blade.**

Sem assinatura. Sem servidor pago. Sem complicação. Você baixa, clica duas vezes e está jogando em segundos — com seus amigos, pela sua própria rede.

## 🐉 O que é o Tartantis VTT?

O Tartantis VTT é um **Virtual Tabletop (VTT)** criado especialmente para mesas de **Mighty Blade**, rodando 100% na sua máquina como um servidor local. O Mestre sobe o servidor, os jogadores entram pelo browser — sem precisar instalar nada.

Pensa nele como o Foundry VTT, mas gratuito, leve e com a identidade visual do universo de Tartantis.

## ✨ Funcionalidades

🗺 **Mesa Interativa**
Imagens de fundo em qualidade máxima (PNG, JPG, WebP e mais), grid customizável com tamanho, cor e calibração de offset para mapas que já têm grid desenhado, névoa de guerra e zoom suave com suporte a HiDPI / Retina.

🪄 **Tokens**
Tokens com imagem personalizada, nome, HP e cor. Drag & drop com snap automático ao grid, régua de medição com snap em tokens e menu de contexto com edição rápida.

🎲 **Sistema de Dados**
Todos os dados (d4, d6, d8, d10, d12, d20 e d100) com animação física de arremesso, quique e brilho. São **9 skins** disponíveis: Clássico, Mármore, Obsidiana, Rubi, Safira, Esmeralda, Ouro, Prata e Dragão. Cada jogador escolhe a sua skin — e os outros veem os dados rolarem com ela. Rolagem às cegas também está disponível para o Mestre.

📋 **Fichas e Iniciativa**
Fichas de personagem integradas no sistema Mighty Blade e tracker de iniciativa com carrossel visual.

💬 **Chat e Sincronização**
Chat em tempo real via WebSocket. Todos os dados, tokens e mapa sincronizam instantaneamente entre todos os jogadores na mesa.

## 🚀 Como instalar

**Windows:** baixe o `.exe` na [página de releases](../../releases/latest), execute e pronto. Ele abre o firewall automaticamente, inicia o servidor e exibe o link para os jogadores entrarem.

**macOS:** baixe o `TartantisVTT-macOS.zip` nos [releases](../../releases/latest), extraia e mova o `.app` para Aplicativos. Na primeira vez clique com botão direito → **Abrir** para passar pelo Gatekeeper. O servidor sobe sozinho e o portal abre no browser.

**Linux (AppImage):** baixe o `.AppImage` nos [releases](../../releases/latest) e rode:
```bash
chmod +x TartantisVTT-x86_64.AppImage
./TartantisVTT-x86_64.AppImage
```

**Raspberry Pi (servidor 24/7):** o Tartantis roda perfeitamente como servidor headless, ideal para deixar ligado o tempo todo na rede:
```bash
git clone https://github.com/Sampsvsl/Tartantis-VTT.git
cd Tartantis-VTT
python3 core/server.py
```
Os jogadores acessam pelo IP da Raspberry na porta **30000** de qualquer dispositivo na rede.

## 🌐 Jogando com amigos pela internet

O Tartantis usa a porta **30000** (a mesma do Foundry VTT). Na rede local os jogadores acessam `http://[SEU-IP]:30000` direto pelo browser. Pela internet, use o túnel Cloudflare integrado no portal do Mestre ou faça port-forward da porta **30000** no seu roteador.

## 🛠 Build

Os builds são gerados automaticamente pelo GitHub Actions a cada nova tag de versão — o release sai com `.exe`, `.AppImage` e `.app` já prontos. Para buildar localmente:

```bash
bash build-linux.sh    # Linux — AppImage
bash build-macos.sh    # macOS — .app
cd windows && build.bat  # Windows — EXE
```

Dependências: **Python 3.8+** sem bibliotecas externas — tudo na stdlib.

## ☕ Apoie o Projeto

O Tartantis é feito de fã para fãs, **100% gratuito e open source**. Se o VTT está ajudando a sua mesa de Mighty Blade, considere apoiar o desenvolvimento para manter os servidores e o café em dia!

👉 **[Apoie o Tartantis no Apoia.se](https://apoia.se)**

## 📜 Licença

Distribuído sob a licença MIT. Veja o arquivo [LICENSE](LICENSE) para mais detalhes.

*Um grande abraço e boas rolagens, Samps* ⚔
