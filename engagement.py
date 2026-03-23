"""
Batch engagement processor: like and comment on YouTube videos from a URL list.
Supports dry-run, resume, delay and error handling.
"""

import argparse
import json
import sys
import time
from pathlib import Path

from googleapiclient.errors import HttpError

from youtube_client import (
    extract_video_id,
    get_authenticated_service,
    insert_comment,
    rate_video,
)

DEFAULT_PROGRESS_FILE = Path(__file__).parent / "progress.json"
DEFAULT_URLS_FILE = Path(__file__).parent / "urls.txt"
DEFAULT_DELAY_SECONDS = 3
MAX_COMMENT_LENGTH = 10000


def load_urls(path: Path) -> list[str]:
    """Load URLs from file, one per line, skipping empty and invalid."""
    if not path.exists():
        raise FileNotFoundError(f"Arquivo de URLs não encontrado: {path}")
    urls = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        urls.append(line)
    return urls


def load_progress(path: Path) -> set[str]:
    """Load set of already-processed video IDs from progress file."""
    if not path.exists():
        return set()
    data = json.loads(path.read_text(encoding="utf-8"))
    return set(data.get("completed", []))


def save_progress(path: Path, completed: set[str]) -> None:
    """Save progress to file."""
    path.write_text(
        json.dumps({"completed": list(completed)}, indent=2),
        encoding="utf-8",
    )


def process_video(
    youtube,
    channel_id: str,
    video_id: str,
    comment_text: str | None,
    dry_run: bool,
    delay_seconds: float,
    verbose: bool = False,
) -> bool:
    """
    Like and optionally comment on a single video.
    Returns True on success, False on failure.
    """
    if dry_run:
        print(f"  [DRY-RUN] Like em {video_id}")
        if comment_text:
            print(f"  [DRY-RUN] Comentário em {video_id}: {comment_text[:50]}...")
        return True

    errors = []

    # Like
    try:
        rate_video(youtube, video_id, "like")
        print(f"  ✓ Like em {video_id}")
    except HttpError as e:
        err_detail = e.error_details if hasattr(e, "error_details") else str(e)
        errors.append(f"Like: {err_detail}")
        print(f"  ✗ Erro ao dar like em {video_id}: {err_detail}")

    if delay_seconds > 0:
        time.sleep(delay_seconds)

    # Comment
    if comment_text:
        if len(comment_text) > MAX_COMMENT_LENGTH:
            errors.append(f"Comentário: texto excede {MAX_COMMENT_LENGTH} caracteres")
        else:
            try:
                result = insert_comment(
                    youtube, video_id, comment_text,
                    fallback_channel_id=channel_id,
                    verbose=verbose,
                )
                print(f"  ✓ Comentário em {video_id}" + (f" (ID: {result.get('id', 'N/A')})" if verbose else ""))
            except (HttpError, ValueError) as e:
                err_detail = e.error_details if hasattr(e, "error_details") else str(e)
                errors.append(f"Comentário: {err_detail}")
                print(f"  ✗ Erro ao comentar em {video_id}: {err_detail}")

        if delay_seconds > 0:
            time.sleep(delay_seconds)

    return len(errors) == 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Dar like e comentar em vídeos do YouTube a partir de uma lista de URLs.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  python engagement.py --urls urls.txt --comment "Ótimo conteúdo!"
  python engagement.py --urls urls.txt --dry-run
  python engagement.py --urls urls.txt --comment-file comentarios.txt --delay 5
  python engagement.py --urls urls.txt --no-resume  # ignorar progresso anterior
  python engagement.py --urls urls.txt              # apenas likes (sem comentário)
        """,
    )
    parser.add_argument(
        "--urls",
        type=Path,
        default=DEFAULT_URLS_FILE,
        help=f"Arquivo com URLs (uma por linha). Padrão: {DEFAULT_URLS_FILE}",
    )
    parser.add_argument(
        "--comment",
        type=str,
        default=None,
        help="Texto do comentário (mesmo para todos os vídeos)",
    )
    parser.add_argument(
        "--comment-file",
        type=Path,
        default=None,
        help="Arquivo com comentários (um por linha, na ordem das URLs)",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=DEFAULT_DELAY_SECONDS,
        help=f"Segundos entre requisições. Padrão: {DEFAULT_DELAY_SECONDS}",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simular ações sem fazer requisições reais",
    )
    parser.add_argument(
        "--no-resume",
        action="store_true",
        help="Ignorar progresso anterior e processar todas as URLs",
    )
    parser.add_argument(
        "--progress-file",
        type=Path,
        default=DEFAULT_PROGRESS_FILE,
        help=f"Arquivo de progresso para retomada. Padrão: {DEFAULT_PROGRESS_FILE}",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Mostrar detalhes de debug (ID do comentário, canal usado)",
    )
    args = parser.parse_args()

    # Load URLs
    try:
        urls = load_urls(args.urls)
    except FileNotFoundError as e:
        print(f"Erro: {e}", file=sys.stderr)
        return 1

    # Extract video IDs and filter invalid
    video_ids = []
    invalid = []
    for url in urls:
        vid = extract_video_id(url)
        if vid:
            video_ids.append(vid)
        else:
            invalid.append(url)
    if invalid:
        print(f"URLs inválidas (ignoradas): {invalid}")

    if not video_ids:
        print("Nenhum vídeo válido para processar.")
        return 0

    # Load comments (opcional)
    comment_texts: list[str | None] = []
    if args.comment:
        comment_texts = [args.comment] * len(video_ids)
    elif args.comment_file:
        if not args.comment_file.exists():
            print(f"Erro: arquivo de comentários não encontrado: {args.comment_file}")
            return 1
        lines = [
            l.strip()
            for l in args.comment_file.read_text(encoding="utf-8").splitlines()
            if l.strip() and not l.strip().startswith("#")
        ]
        comment_texts = [lines[i] if i < len(lines) else None for i in range(len(video_ids))]
    else:
        comment_texts = [None] * len(video_ids)

    # Authenticate primeiro (mostra canal sempre, inclusive quando não há nada a processar)
    youtube = None
    channel_id = ""
    try:
        youtube, channel_id, channel_title = get_authenticated_service()
        print(f"Usando canal: {channel_title} (ID: {channel_id})\n")
    except Exception as e:
        if args.dry_run:
            print(f"[dry-run] Pulando auth (não foi possível autenticar: {e})\n")
        else:
            print(f"Erro de autenticação: {e}", file=sys.stderr)
            return 1

    # Resume: skip already completed
    completed = set() if args.no_resume else load_progress(args.progress_file)
    to_process = [
        (vid, comment_texts[i])
        for i, vid in enumerate(video_ids)
        if vid not in completed
    ]

    if not to_process:
        print("Todos os vídeos já foram processados. Use --no-resume para reprocessar.")
        return 0

    print(f"Vídeos a processar: {len(to_process)} de {len(video_ids)}")
    if args.dry_run:
        print("Modo DRY-RUN ativado (nenhuma ação real)")

    success_count = 0
    for idx, (video_id, comment_text) in enumerate(to_process, 1):
        print(f"\n[{idx}/{len(to_process)}] Processando {video_id}...")
        ok = process_video(
            youtube,
            channel_id,
            video_id,
            comment_text,
            args.dry_run,
            args.delay,
            verbose=args.verbose,
        )
        if ok:
            completed.add(video_id)
            success_count += 1
            save_progress(args.progress_file, completed)
        else:
            print(f"  Vídeo {video_id} teve falhas (não marcado como completo)")

    print(f"\nConcluído: {success_count} vídeos processados com sucesso.")
    if args.comment or args.comment_file:
        print("\nDica: Se comentários não aparecerem no YouTube, podem estar em análise (spam filter).")
        print("      Tente --comment-file com textos diferentes por vídeo ou --delay 8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
