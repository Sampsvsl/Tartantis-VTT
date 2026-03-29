# ⚔ Tartantis VTT

**A mesa virtual de RPG gratuita, open source e feita de fã para fãs de Mighty Blade.**

Sem assinatura. Sem servidor pago. Sem complicação. Você baixa, clica duas vezes e está jogando em segundos — com seus amigos, pela sua própria rede.

---

## 🐉 O que é o Tartantis VTT?

O Tartantis VTT é um **Virtual Tabletop (VTT)** criado especialmente para mesas de **Mighty Blade**, rodando 100% na sua máquina como um servidor local. O Mestre sobe o servidor, os jogadores entram pelo browser — sem precisar instalar nada.

Pensa nele como o Foundry VTT, mas gratuito, leve e com a identidade visual do universo de Tartantis.

---

## ✨ Funcionalidades

🗺 **Mesa Interativa**
- Imagens de fundo em qualidade máxima (PNG, JPG, WebP e mais)
- Grid customizável: tamanho, cor (dourado, branco ou preto) e calibração de offset para mapas que já têm grid desenhado
- Névoa de guerra para o Mestre controlar o que os jogadores veem
- Zoom e pan suaves com suporte a HiDPI / Retina

🪄 **Tokens**
- Tokens com imagem personalizada, nome, HP e cor
- Drag & drop com snap automático ao grid
- Régua de medição de distância entre quadrados, com snap em tokens
- Menu de contexto com edição rápida

🎲 **Sistema de Dados**
- Todos os dados: d4, d6, d8, d10, d12, d20 e d100
- Animação física com arremesso, quique e brilho
- **9 skins de dados** (Clássico, Mármore, Obsidiana, Rubi, Safira, Esmeralda, Ouro, Prata e Dragão)
- Skins por jogador — cada um vê os dados do amigo com a skin dele
- Rolagem às cegas para o Mestre

📋 **Fichas e Iniciativa**
- Fichas de personagem integradas (sistema Mighty Blade)
- Tracker de iniciativa com carrossel visual

💬 **Chat e Sincronização**
- Chat em tempo real via WebSocket
- Todos os dados, tokens e mapa sincronizam instantaneamente entre todos os jogadores

---

## 🚀 Como instalar

### Windows
1. Baixe o `.exe` na [página de releases](../../releases/latest)
2. Execute — ele abre o firewall automaticamente e inicia o servidor
3. Compartilhe o link exibido na tela para os jogadores entrarem

### Linux (AppImage)
1. Baixe o `.AppImage` na [página de releases](../../releases/latest)
2. Dê permissão de execução e rode:
```bash
chmod +x TartantisVTT-x86_64.AppImage
./TartantisVTT-x86_64.AppImage
```

### Linux / macOS (código fonte)
```bash
git clone https://github.com/Sampsvsl/Tartantis-VTT.git
cd Tartantis-VTT
bash install.sh
```

### Raspberry Pi (servidor 24/7)
O Tartantis roda perfeitamente como servidor headless — ideal para deixar ligado o tempo todo na rede:
```bash
git clone https://github.com/Sampsvsl/Tartantis-VTT.git
cd Tartantis-VTT
python3 core/server.py
```
Os jogadores acessam pelo IP da Raspberry na porta **30000** de qualquer dispositivo na rede.

---

## 🌐 Jogando com amigos pela internet

O Tartantis usa a porta **30000** (a mesma do Foundry VTT).

**Rede local:** os jogadores acessam `http://[SEU-IP]:30000` direto pelo browser.

**Pela internet:** use o túnel Cloudflare integrado no portal do Mestre, ou faça port-forward da porta **30000** no seu roteador.

---

## 🛠 Build (para desenvolvedores)

### Linux — AppImage
```bash
bash build-linux.sh
```

### Windows — EXE
```bash
cd windows
build.bat
```

Dependências: **Python 3.8+** (sem bibliotecas externas — tudo na stdlib).

---

## ☕ Apoie o Projeto

O Tartantis é feito de fã para fãs, **100% gratuito e open source**. Se o VTT está ajudando a sua mesa de Mighty Blade, considere apoiar o desenvolvimento para manter os servidores e o café em dia!

👉 **[Apoie o Tartantis no Apoia.se](https://apoia.se)**

---

## 📜 Licença

Distribuído sob a licença MIT. Veja o arquivo [LICENSE](LICENSE) para mais detalhes.

---

*Um grande abraço e boas rolagens,*
*Samps* ⚔
