#!/usr/bin/env python3
"""
Script para testar comentário em um único vídeo.
Mostra a resposta completa da API para diagnóstico.
Uso: python test_single_comment.py VIDEO_ID "Texto do comentário"
"""

import sys
from youtube_client import get_authenticated_service, insert_comment

def main():
    if len(sys.argv) < 3:
        print("Uso: python test_single_comment.py VIDEO_ID \"Texto do comentário\"")
        print("Exemplo: python test_single_comment.py dQw4w9WgXcQ \"Ótimo vídeo!\"")
        return 1

    video_id = sys.argv[1]
    comment_text = sys.argv[2]

    print("Autenticando...")
    youtube, channel_id, channel_title = get_authenticated_service()
    print(f"Canal: {channel_title} ({channel_id})")
    print(f"Comentando no vídeo {video_id}...")
    print()

    try:
        result = insert_comment(youtube, video_id, comment_text, fallback_channel_id=channel_id)
        print("SUCESSO! Resposta da API:")
        print(f"  Comment Thread ID: {result.get('id')}")
        print(f"  Vídeo: {result.get('snippet', {}).get('videoId')}")
        comment = result.get('snippet', {}).get('topLevelComment', {})
        print(f"  Texto: {comment.get('snippet', {}).get('textOriginal')}")
        print()
        print("Se o comentário não aparecer no YouTube:")
        print("- Pode estar em análise (spam filter) por comentários idênticos")
        print("- Vídeo 'Para crianças' tem comentários desativados")
        print("- Tente um comentário mais personalizado/diferente")
        return 0
    except Exception as e:
        print(f"ERRO: {e}")
        if hasattr(e, 'error_details'):
            print(f"Detalhes: {e.error_details}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
