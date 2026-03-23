#!/usr/bin/env python3
"""
Divide urls.txt e comentarios.txt em lotes de 150 itens.
Arquivos gerados em lotes/urls_N.txt e lotes/comentarios_N.txt
"""

import sys
from pathlib import Path

CHUNK = 150
ROOT = Path(__file__).parent
URLS_FILE = ROOT / "urls.txt"
COMENTARIOS_FILE = ROOT / "comentarios.txt"
OUT_DIR = ROOT / "lotes"


def main() -> int:
    if not URLS_FILE.exists():
        print(f"Erro: {URLS_FILE} não encontrado")
        return 1
    if not COMENTARIOS_FILE.exists():
        print(f"Erro: {COMENTARIOS_FILE} não encontrado")
        return 1

    OUT_DIR.mkdir(exist_ok=True)

    urls = [l.strip() for l in URLS_FILE.read_text(encoding="utf-8").splitlines() if l.strip()]
    comentarios = [l.strip() for l in COMENTARIOS_FILE.read_text(encoding="utf-8").splitlines() if l.strip()]

    if len(urls) != len(comentarios):
        print(f"Aviso: {len(urls)} URLs vs {len(comentarios)} comentários")

    n = min(len(urls), len(comentarios))
    print(f"Dividindo {n} itens em lotes de {CHUNK}...")

    for i in range(0, n, CHUNK):
        chunk_num = i // CHUNK + 1
        chunk_urls = urls[i:i+CHUNK]
        chunk_coments = comentarios[i:i+CHUNK]

        (OUT_DIR / f"urls_{chunk_num}.txt").write_text("\n".join(chunk_urls) + "\n", encoding="utf-8")
        (OUT_DIR / f"comentarios_{chunk_num}.txt").write_text("\n".join(chunk_coments) + "\n", encoding="utf-8")

        print(f"  lotes/urls_{chunk_num}.txt e lotes/comentarios_{chunk_num}.txt: {len(chunk_urls)} itens")

    print("Concluído!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
