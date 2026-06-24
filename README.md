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
