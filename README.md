# YouTube Video Engagement Tool

Ferramenta para dar **like** e **comentar** em vídeos do YouTube em lote, usando sua conta via OAuth 2.0 e a YouTube Data API v3.

## Funcionalidades

- Like em vídeos (`videos.rate`)
- Comentários (`commentThreads.insert`)
- Delay configurável entre requisições (evitar rate limit e spam filter)
- **Dry-run**: simular sem executar
- **Retomada**: continua de onde parou em caso de interrupção
- **Verbose**: exibe canal em uso e ID dos comentários criados
- Tratamento de erros por vídeo

---

## Setup no Google Cloud

### 1. Criar projeto

1. Acesse [Google Cloud Console](https://console.cloud.google.com/)
2. Crie um novo projeto ou selecione um existente

### 2. Habilitar a API

1. **APIs e Serviços** → **Biblioteca**
2. Busque **YouTube Data API v3**
3. Clique em **Habilitar**

### 3. Tela de consentimento OAuth

1. **APIs e Serviços** → **Tela de consentimento OAuth**
2. Tipo: **Externo**
3. Em **Escopos**, adicione: `https://www.googleapis.com/auth/youtube.force-ssl`
4. Em **Usuários de teste**, adicione o e-mail da conta do canal YouTube que usará a ferramenta
5. Salve

### 4. Credenciais OAuth 2.0

1. **APIs e Serviços** → **Credenciais** → **Criar credenciais** → **ID do cliente OAuth**
2. Tipo: **Aplicativo da Web**
3. Em **URIs de redirecionamento autorizados**, adicione:
   - `http://localhost:8080/`
   - `http://localhost:8080/callback`
4. Baixe o JSON e salve como `client_secret.json` na pasta do projeto

---

## Instalação

```bash
cd youtube-video-engagement-tool
python -m venv venv
source venv/bin/activate   # Linux/macOS
# ou: venv\Scripts\activate   # Windows

pip install -r requirements.txt
```

---

## Uso

### Primeira execução

O navegador abrirá para login no Google. O `token.json` será criado para as próximas execuções. Use a conta do canal que fará likes e comentários.

### Arquivos de entrada

- **urls.txt**: uma URL do YouTube por linha
- **comentarios.txt**: um comentário por linha (ordem corresponde às URLs). Use para evitar spam filter com comentários idênticos.

### Exemplos

```bash
# Apenas likes
python engagement.py --urls urls.txt

# Like + comentário único
python engagement.py --urls urls.txt --comment "Ótimo conteúdo!"

# Comentários diferentes por vídeo (recomendado)
python engagement.py --urls urls.txt --comment-file comentarios.txt --delay 8

# Dry-run (simular)
python engagement.py --urls urls.txt --comment "Teste" --dry-run

# Reprocessar tudo (ignorar progresso)
python engagement.py --urls urls.txt --comment-file comentarios.txt --no-resume --delay 8

# Modo verbose (exibe canal e ID dos comentários)
python engagement.py --urls urls.txt --comment-file comentarios.txt -v --delay 8
```

### Opções

| Opção | Padrão | Descrição |
|-------|--------|-----------|
| `--urls` | `urls.txt` | Arquivo com URLs |
| `--comment` | - | Comentário único para todos |
| `--comment-file` | - | Arquivo com um comentário por linha |
| `--delay` | 3 | Segundos entre requisições |
| `--dry-run` | - | Simular sem executar |
| `--no-resume` | - | Ignorar progresso e reprocessar tudo |
| `--verbose`, `-v` | - | Exibir detalhes de debug |

### Teste em um vídeo

Para testar comentário em um único vídeo:

```bash
python test_single_comment.py VIDEO_ID "Texto do comentário"
```

---

## Estrutura do projeto

```
youtube-video-engagement-tool/
├── engagement.py             # Script principal
├── youtube_client.py         # Cliente API e OAuth
├── test_single_comment.py    # Teste em um vídeo
├── split_batches.py          # Divide em lotes de 150
├── requirements.txt
├── urls.txt.example          # Modelo para urls.txt
├── comentarios.txt.example   # Modelo para comentarios.txt
├── lotes/                    # URLs e comentários divididos
│   ├── README.md
│   ├── urls_1.txt
│   ├── comentarios_1.txt
│   └── ...
└── README.md
```

### Dividir em lotes (evitar cota diária)

Para dividir `urls.txt` e `comentarios.txt` em arquivos de 150 itens na pasta `lotes/`:

```bash
python split_batches.py
```

Depois rode um lote por dia:

```bash
python engagement.py --urls lotes/urls_1.txt --comment-file lotes/comentarios_1.txt --no-resume --delay 8
```

---

## Retomada

O progresso é salvo em `progress.json`. Se o script for interrompido, execute novamente sem `--no-resume` para continuar de onde parou.

---

## Observações

- **Cota da API**: 10.000 unidades/dia (grátis). ~52 unidades por vídeo (like + comentário). Use `split_batches.py` e rode um lote por dia (~150 vídeos) para ficar dentro da cota
- Use `--delay 8` ou maior ao comentar em vários vídeos para reduzir chance de spam filter
- Comentários idênticos em muitos vídeos podem ser filtrados pelo YouTube
- Vídeos "Para crianças" não aceitam comentários
- O canal exibido no início é o que será usado para likes e comentários
