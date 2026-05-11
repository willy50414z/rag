# MinerU Docker Setup

## Quick Start

1. Put your PDF files in `pdfs/` folder
2. Run MinerU:
   ```bash
   docker compose run --rm mineru -p your-file.pdf -o /output -m auto
   ```
   Or use the helper script:
   ```bash
   run-mineru.bat your-file.pdf
   ```
3. Check output in `output/` folder

## API Server (Optional)

Start API server:
```bash
docker compose up mineru-api
```
echo $GITHUB_TOKEN | docker login ghcr.io -u willy50414z --password-stdin
API endpoint: http://localhost:8000

## Options

- `-m auto` - Auto detect (OCR or text)
- `-m txt` - Text-based PDF only
- `-m ocr` - Force OCR

## Volumes

- `pdfs/` - Input PDFs
- `output/` - Parsed output (Markdown, JSON, etc.)