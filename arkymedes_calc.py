#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Offline calculator assistant with secure evaluation, OCR and PDF support.

Usage examples:
  python arkymedes_calc.py --text "23 * 17"
  python arkymedes_calc.py --image "calc.png"
  python arkymedes_calc.py --text "área do círculo raio=5"

Dependencies:
  pip install pillow pytesseract pypdf pdf2image
"""

import argparse
import logging
import logging.handlers
import os
import re
from pathlib import Path
from typing import Optional, Tuple

# ------------------------------------------------------------------
# Logging
# ------------------------------------------------------------------

LOG_DIR = Path(__file__).parent / ".logs"
LOG_DIR.mkdir(exist_ok=True)

logger = logging.getLogger(__name__)

if not logger.handlers:
    _handler = logging.handlers.RotatingFileHandler(
        LOG_DIR / "arkymedes.log",
        maxBytes=1_000_000,
        backupCount=5,
        encoding="utf-8",
    )
    _handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
    logger.addHandler(_handler)
    logger.setLevel(logging.DEBUG)

# ------------------------------------------------------------------
# Importações opcionais
# ------------------------------------------------------------------

try:
    from PIL import Image, UnidentifiedImageError
    HAS_PIL = True
except ImportError:
    HAS_PIL = False
    logger.warning("Pillow não instalado — OCR de imagens indisponível.")

try:
    import pytesseract
    pytesseract.pytesseract.tesseract_cmd = os.environ.get("TESSERACT_CMD", "tesseract")
    HAS_TESSERACT = True
except ImportError:
    HAS_TESSERACT = False
    logger.warning("pytesseract não instalado — OCR indisponível.")

try:
    from pypdf import PdfReader
    HAS_PYPDF = True
except ImportError:
    HAS_PYPDF = False
    logger.warning("pypdf não instalado — leitura de PDF indisponível.")

try:
    from pdf2image import convert_from_path
    HAS_PDF2IMAGE = True
except ImportError:
    HAS_PDF2IMAGE = False
    logger.warning("pdf2image não instalado — OCR de PDF indisponível.")

from arkymedes_safe import safe_evaluate

# ------------------------------------------------------------------
# Banco de fórmulas
# ------------------------------------------------------------------

FORMULA_DB: dict[str, dict] = {
    "área do círculo": {
        "formula": "pi * r**2",
        "params": ["r"],
        "description": "Área do círculo = π × raio²",
    },
    "area do circulo": {
        "formula": "pi * r**2",
        "params": ["r"],
        "description": "Área do círculo = π × raio²",
    },
    "volume da esfera": {
        "formula": "4/3 * pi * r**3",
        "params": ["r"],
        "description": "Volume da esfera = 4/3 × π × raio³",
    },
    "juros compostos": {
        "formula": "p * (1 + i)**n",
        "params": ["p", "i", "n"],
        "description": "Juros compostos = P × (1 + i)^n",
    },
    "juros simples": {
        "formula": "p * i * t",
        "params": ["p", "i", "t"],
        "description": "Juros simples = P × i × t",
    },
}

# ------------------------------------------------------------------
# OCR
# ------------------------------------------------------------------

def ocr_text_from_image(image_path: str) -> str:
    """Extrair texto de uma imagem usando OCR.

    Raises:
        ImportError: se Pillow ou pytesseract não estiverem instalados.
        FileNotFoundError: se o arquivo não existir.
        ValueError: se o arquivo não for uma imagem válida.
        RuntimeError: se o Tesseract não estiver instalado no sistema.
    """
    if not HAS_PIL:
        raise ImportError("Pillow não instalado. Execute: pip install pillow")
    if not HAS_TESSERACT:
        raise ImportError("pytesseract não instalado. Execute: pip install pytesseract")

    path = Path(image_path)
    if not path.exists():
        raise FileNotFoundError(f"Imagem não encontrada: {image_path}")

    logger.info("Iniciando OCR: %s", image_path)

    try:
        image = Image.open(path)
    except UnidentifiedImageError as exc:
        raise ValueError(f"Arquivo não é uma imagem válida: {image_path}") from exc

    try:
        text = pytesseract.image_to_string(image, lang="por+eng")
    except pytesseract.TesseractNotFoundError as exc:
        raise RuntimeError(
            "Tesseract OCR não encontrado. Instale em: "
            "https://github.com/UB-Mannheim/tesseract/wiki"
        ) from exc

    result = text.strip()
    logger.info("OCR concluído: %d caracteres extraídos.", len(result))
    return result


# ------------------------------------------------------------------
# PDF
# ------------------------------------------------------------------

def extract_text_from_pdf(pdf_path: str) -> str:
    """Extrair texto de um PDF (texto embutido ou OCR como fallback).

    Raises:
        ImportError: se pypdf não estiver instalado.
        FileNotFoundError: se o arquivo não existir.
        ValueError: se o arquivo não for um PDF válido.
    """
    path = Path(pdf_path)
    if not path.exists():
        raise FileNotFoundError(f"PDF não encontrado: {pdf_path}")
    if path.suffix.lower() != ".pdf":
        raise ValueError(f"Arquivo não é um PDF: {pdf_path}")

    if not HAS_PYPDF:
        logger.warning("pypdf indisponível — tentando OCR direto.")
        return _ocr_pdf_pages(pdf_path)

    logger.info("Extraindo texto do PDF: %s", pdf_path)
    text_parts: list[str] = []

    try:
        reader = PdfReader(path)
    except Exception as exc:
        raise ValueError(f"Não foi possível abrir o PDF: {exc}") from exc

    for page_num, page in enumerate(reader.pages, start=1):
        try:
            page_text = page.extract_text() or ""
        except Exception as exc:
            logger.warning("Erro ao extrair página %d: %s", page_num, exc)
            page_text = ""

        if page_text.strip():
            text_parts.append(page_text)
        else:
            logger.info("Página %d sem texto — tentando OCR.", page_num)
            ocr = _ocr_pdf_page(pdf_path, page_num - 1)
            if ocr:
                text_parts.append(ocr)

    result = " ".join(text_parts).strip()
    logger.info("PDF processado: %d caracteres extraídos.", len(result))
    return result


def _ocr_pdf_pages(pdf_path: str) -> str:
    if not HAS_PDF2IMAGE:
        raise ImportError("pdf2image não instalado. Execute: pip install pdf2image")

    text_parts: list[str] = []
    try:
        images = convert_from_path(pdf_path)
    except Exception as exc:
        logger.error("Erro ao converter PDF para imagens: %s", exc)
        raise RuntimeError(f"Não foi possível converter o PDF: {exc}") from exc

    for page_num, image in enumerate(images, start=1):
        logger.info("OCR na página %d…", page_num)
        try:
            text = pytesseract.image_to_string(image, lang="por+eng")
            if text.strip():
                text_parts.append(text)
        except Exception as exc:
            logger.warning("OCR falhou na página %d: %s", page_num, exc)

    return " ".join(text_parts).strip()


def _ocr_pdf_page(pdf_path: str, page_index: int) -> str:
    if not HAS_PDF2IMAGE or not HAS_TESSERACT:
        return ""
    try:
        images = convert_from_path(
            pdf_path, first_page=page_index + 1, last_page=page_index + 1
        )
        if images:
            return pytesseract.image_to_string(images[0], lang="por+eng").strip()
    except Exception as exc:
        logger.warning("OCR página %d falhou: %s", page_index, exc)
    return ""


# ------------------------------------------------------------------
# Normalização de expressão
# ------------------------------------------------------------------

def normalize_expression(text: str) -> str:
    text = text.strip()
    text = text.replace("×", "*")
    text = text.replace("÷", "/")
    text = text.replace("^", "**")
    text = text.replace("–", "-")
    text = text.replace("—", "-")
    text = text.replace(",", ".")
    text = re.sub(r"[^0-9a-zA-Zπ\.\+\-\*\/\(\)\s_]+", "", text)
    text = re.sub(r"\bpor\b", "*", text)
    text = re.sub(r"\bmais\b", "+", text)
    text = re.sub(r"\bmenos\b", "-", text)
    text = re.sub(r"\bvezes\b", "*", text)
    text = re.sub(r"\bdividido por\b", "/", text)
    return text.strip()


# ------------------------------------------------------------------
# Fórmulas
# ------------------------------------------------------------------

def _extract_param_values(text: str, params: list[str]) -> dict[str, float]:
    """Extrair valores de parâmetros de texto como 'raio=5' ou 'r=5'."""
    values: dict[str, float] = {}
    for param in params:
        match = re.search(
            rf"(?:{param}|raio|altura|principal|taxa|tempo)\s*[=:]\s*([\d.,]+)",
            text,
            re.IGNORECASE,
        )
        if match:
            try:
                values[param] = float(match.group(1).replace(",", "."))
            except ValueError:
                pass
    return values


def try_formula_query(text: str) -> Optional[Tuple[str, str]]:
    lower = text.lower()
    for keyword, info in FORMULA_DB.items():
        if keyword in lower:
            param_values = _extract_param_values(text, info["params"])
            formula = info["formula"]
            for param, value in param_values.items():
                formula = re.sub(rf"\b{param}\b", str(value), formula)
            return info["description"], formula
    return None


# ------------------------------------------------------------------
# Cálculo principal
# ------------------------------------------------------------------

def calculate_expression(expr: str) -> Tuple[Optional[float], str]:
    """Calcular expressão matemática de forma segura.

    Returns:
        Tupla (resultado, mensagem_descritiva).
        resultado é None em caso de erro.
    """
    if not expr or not expr.strip():
        return None, "Nenhuma expressão fornecida."

    logger.debug("Calculando: %s", expr[:100])

    formula_match = try_formula_query(expr)
    if formula_match:
        description, formula = formula_match
        logger.debug("Fórmula detectada: %s → %s", description, formula)
        result, message = safe_evaluate(formula)
        if result is not None:
            logger.info("Fórmula calculada: %s = %s", description, result)
            return result, description
        logger.warning("Fórmula não calculada: %s | %s", description, message)
        return None, message

    normalized = normalize_expression(expr)
    if not normalized:
        return None, "Não foi possível extrair uma expressão matemática válida."

    result, message = safe_evaluate(normalized)
    if result is not None:
        logger.info("Cálculo OK: %s = %s", normalized, result)
    else:
        logger.warning("Cálculo falhou: %s | %s", normalized, message)
    return result, message


# ------------------------------------------------------------------
# CLI
# ------------------------------------------------------------------

def run_query(text: str) -> None:
    print(f"Entrada: {text}")
    formula_match = try_formula_query(text)
    if formula_match:
        description, formula = formula_match
        print(f"Fórmula: {description}")
        print(f"Expressão: {formula}")

    result, message = calculate_expression(text)
    if result is not None:
        print(f"Resultado: {result}")
    else:
        print(f"Erro: {message}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Assistente de cálculo offline com OCR para imagens e PDFs."
    )
    parser.add_argument("--text", type=str, help="Expressão matemática para calcular.")
    parser.add_argument("--image", type=str, help="Caminho da imagem com a expressão.")
    parser.add_argument("--pdf", type=str, help="Caminho do PDF com expressões.")
    parser.add_argument("--debug", action="store_true", help="Ativar logging detalhado.")
    args = parser.parse_args()

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    if not any([args.text, args.image, args.pdf]):
        parser.print_help()
        return

    if args.pdf:
        try:
            text = extract_text_from_pdf(args.pdf)
            print(f"Texto extraído ({len(text)} chars): {text[:200]}{'…' if len(text) > 200 else ''}")
            run_query(text)
        except (FileNotFoundError, ValueError, ImportError, RuntimeError) as exc:
            print(f"Erro: {exc}")
        return

    if args.image:
        try:
            text = ocr_text_from_image(args.image)
            print(f"Texto extraído: {text}")
            run_query(text)
        except (FileNotFoundError, ValueError, ImportError, RuntimeError) as exc:
            print(f"Erro: {exc}")
        return

    if args.text:
        run_query(args.text)


if __name__ == "__main__":
    main()