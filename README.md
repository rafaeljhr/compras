# 🛒 Lista de Compras

Lista de compras de casa focada em alimentação. App web simples (Flask), em
português, com **dois níveis de separadores** (Categoria → Subcategoria) e uma
tab **🛒 Lista** que junta tudo o que tens para comprar. Corre no **porto 8003**.

A ideia: em vez de reescrever sempre (como nos lembretes), os produtos ficam num
**catálogo permanente** por subcategoria. Só ajustas a **quantidade a comprar**
(−/＋); depois das compras carregas em **Limpar lista** e o catálogo continua lá
para a próxima.

- Separadores **arrastáveis** (⠿) — a ordem fica guardada por dispositivo.
- **Badges** mostram quantos itens estão na lista por categoria/subcategoria.
- Estado guardado no servidor (volume `/data`) e sincroniza sozinho (~15s).

## Correr localmente
```bash
pip install -r requirements.txt
python app.py        # http://localhost:8003
```

## Docker (Raspberry Pi)
```bash
docker compose up -d --build
# http://<ip-do-pi>:8003
```

## 🆘 Deploy do zero (se o Raspberry Pi morrer)

Num Raspberry Pi novo com **Raspberry Pi OS (64-bit)** e SSH ligado:

1. Atualizar o sistema e instalar o Docker:
   ```bash
   sudo apt update && sudo apt upgrade -y
   curl -fsSL https://get.docker.com | sh
   sudo usermod -aG docker $USER && newgrp docker   # usar o docker sem sudo
   ```
2. Clonar este repositório e arrancar:
   ```bash
   git clone https://github.com/rafaeljhr/compras.git
   cd compras
   docker compose up -d --build
   ```
3. Aceder em **http://<ip-do-pi>:8003** (descobre o IP com `hostname -I`).

O serviço tem `restart: unless-stopped` e o Docker arranca no boot, por isso volta
a subir sozinho após reinícios ou falhas de energia.

### Backup / reposição dos dados
O catálogo e lista de compras fica num volume Docker chamado `compras_data`.

```bash
# backup -> cria backup.tar.gz na pasta atual
docker run --rm -v compras_data:/data -v "$PWD":/backup alpine tar czf /backup/backup.tar.gz -C /data .

# repor a partir de backup.tar.gz
docker run --rm -v compras_data:/data -v "$PWD":/backup alpine tar xzf /backup/backup.tar.gz -C /data
```

### Atualizar para a versão mais recente
```bash
cd compras && git pull && docker compose up -d --build
```
