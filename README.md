# Tartantis VTT

![Build](https://github.com/Sampsvsl/Tartantis-VTT/actions/workflows/build.yml/badge.svg)

Mesa virtual de RPG gratuita, open source e feita para mesas de Mighty Blade.

Sem assinatura, sem servidor pago e sem setup complicado: você instala, abre e já pode jogar com seu grupo pela sua rede.

## O que é o Tartantis VTT

O Tartantis VTT é um Virtual Tabletop (VTT) focado em Mighty Blade, rodando localmente na sua máquina. O Mestre sobe a mesa e os jogadores entram pelo navegador, sem precisar instalar cliente.

## Funcionalidades

**Mesa interativa**
Suporte a mapas em alta qualidade (PNG, JPG, WebP e outros), grid configurável com calibração de offset, névoa de guerra e zoom suave com suporte a telas HiDPI/Retina.

**Tokens**
Tokens com imagem, nome, HP e cor. Arrastar e soltar com encaixe no grid, régua com snap em tokens e menu de contexto para edição rápida.

**Sistema de dados**
Rolagem de d4, d6, d8, d10, d12, d20 e d100 com animação física. O projeto inclui 9 skins de dados (Clássico, Mármore, Obsidiana, Rubi, Safira, Esmeralda, Ouro, Prata e Dragão), com sincronização visual para todos os jogadores.

**Fichas e iniciativa**
Fichas integradas ao sistema de Mighty Blade e tracker de iniciativa com exibição em carrossel.

**Chat e sincronização**
Chat em tempo real via WebSocket, com sincronização imediata de mapa, tokens e estado da mesa.

## Instalação

**Windows**
Baixe o `.exe` na [pagina de releases](../../releases/latest), execute e pronto. O app abre o firewall automaticamente, inicia o servidor e mostra o link para os jogadores.

**macOS**
Baixe `TartantisVTT-macOS.zip` em [releases](../../releases/latest), extraia e mova o `.app` para Aplicativos. Na primeira execução, clique com o botão direito em **Abrir** para passar pelo Gatekeeper.

**Linux (AppImage)**

```bash
chmod +x TartantisVTT-x86_64.AppImage
./TartantisVTT-x86_64.AppImage
```

**Raspberry Pi (servidor 24/7)**

```bash
git clone https://github.com/Sampsvsl/Tartantis-VTT.git
cd Tartantis-VTT
python3 core/server.py
```

Os jogadores acessam pelo IP da Raspberry na porta **30000**.

## Jogando pela internet

O Tartantis usa a porta **30000**. Em rede local, os jogadores entram por `http://[SEU-IP]:30000`. Para jogar pela internet, use o túnel Cloudflare integrado no portal do Mestre ou configure port-forward da porta 30000 no roteador.

## Build

Os builds são gerados automaticamente no GitHub Actions a cada nova tag de versão. Também é possível buildar localmente:

```bash
bash build-linux.sh      # Linux (AppImage)
bash build-macos.sh      # macOS (.app)
cd windows && build.bat  # Windows (.exe)
```

Dependência principal: **Python 3.8+** (stdlib).

## Apoie o projeto

Se o Tartantis está ajudando sua mesa, você pode apoiar o desenvolvimento em:

**[Apoia.se Tartantis VTT](https://apoia.se/tartantis-vtt)**

## Licença

Distribuído sob a licença MIT. Veja [LICENSE](LICENSE) para detalhes.
