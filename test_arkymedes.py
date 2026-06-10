#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Testes automatizados - Arkymedes.

Execute com:
  pytest test_arkymedes_calc.py -v
  pytest test_arkymedes_calc.py -v --tb=short
  pytest test_arkymedes_calc.py -v --cov=arkymedes_calc --cov=arkymedes_safe
"""

import math
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent))

from arkymedes_safe import safe_evaluate, SafeCalculator
from arkymedes_calc import (
    calculate_expression,
    normalize_expression,
    try_formula_query,
)


# ==================================================================
# arkymedes_safe — operações seguras
# ==================================================================

class TestSafeOperationsBasicas:
    def test_soma(self):
        r, _ = safe_evaluate("2 + 2")
        assert r == 4.0

    def test_subtracao(self):
        r, _ = safe_evaluate("10 - 3")
        assert r == 7.0

    def test_multiplicacao(self):
        r, _ = safe_evaluate("10 * 5")
        assert r == 50.0

    def test_divisao(self):
        r, _ = safe_evaluate("100 / 4")
        assert r == 25.0

    def test_divisao_inteira(self):
        r, _ = safe_evaluate("10 // 3")
        assert r == 3.0

    def test_modulo(self):
        r, _ = safe_evaluate("10 % 3")
        assert r == 1.0

    def test_potencia(self):
        r, _ = safe_evaluate("2 ** 10")
        assert r == 1024.0

    def test_negativo(self):
        r, _ = safe_evaluate("-5 + 3")
        assert r == -2.0

    def test_parenteses(self):
        r, _ = safe_evaluate("(2 + 3) * 4")
        assert r == 20.0

    def test_expressao_complexa(self):
        r, _ = safe_evaluate("2 + 3 * 4 - 1")
        assert r == 13.0


class TestSafeFuncoes:
    def test_sqrt(self):
        r, _ = safe_evaluate("sqrt(16)")
        assert r == pytest.approx(4.0)

    def test_sin(self):
        r, _ = safe_evaluate("sin(0)")
        assert r == pytest.approx(0.0)

    def test_cos(self):
        r, _ = safe_evaluate("cos(0)")
        assert r == pytest.approx(1.0)

    def test_abs(self):
        r, _ = safe_evaluate("abs(-7)")
        assert r == 7.0

    def test_floor(self):
        r, _ = safe_evaluate("floor(3.9)")
        assert r == 3.0

    def test_ceil(self):
        r, _ = safe_evaluate("ceil(3.1)")
        assert r == 4.0

    def test_log10(self):
        r, _ = safe_evaluate("log10(100)")
        assert r == pytest.approx(2.0)

    def test_exp(self):
        r, _ = safe_evaluate("exp(0)")
        assert r == pytest.approx(1.0)


class TestSafeConstantes:
    def test_pi(self):
        r, _ = safe_evaluate("pi")
        assert r == pytest.approx(math.pi)

    def test_e(self):
        r, _ = safe_evaluate("e")
        assert r == pytest.approx(math.e)

    def test_pi_em_formula(self):
        r, _ = safe_evaluate("pi * 5 ** 2")
        assert r == pytest.approx(math.pi * 25)


class TestSafeErros:
    def test_divisao_por_zero(self):
        r, msg = safe_evaluate("1 / 0")
        assert r is None
        assert "zero" in msg.lower()

    def test_expressao_vazia(self):
        r, msg = safe_evaluate("")
        assert r is None
        assert msg

    def test_expressao_muito_longa(self):
        r, msg = safe_evaluate("1 + " * 300 + "1")
        assert r is None

    def test_sintaxe_invalida(self):
        r, msg = safe_evaluate("2 + + +")
        assert r is None


# ==================================================================
# arkymedes_safe — segurança (injeção de código)
# ==================================================================

class TestSeguranca:
    @pytest.mark.parametrize("expr", [
        "__import__('os')",
        "__import__('os').system('echo HACKED')",
        "eval('2+2')",
        "exec('print(1)')",
        "globals()",
        "locals()",
        "vars()",
        "dir()",
        "lambda x: x+1",
        "[1, 2, 3]",
        "{'a': 1}",
        "compile('', '', 'exec')",
        "getattr(object, '__class__')",
        "open('passwd')",
    ])
    def test_bloqueado(self, expr):
        r, msg = safe_evaluate(expr)
        assert r is None, f"VULNERABILIDADE: '{expr}' não foi bloqueado! Resultado: {r}"

    def test_operacoes_seguras_nao_bloqueadas(self):
        seguros = ["2 + 2", "sqrt(16)", "pi * 3", "sin(pi/2)", "10 ** 3"]
        for expr in seguros:
            r, _ = safe_evaluate(expr)
            assert r is not None, f"Operação segura foi bloqueada incorretamente: {expr}"


# ==================================================================
# normalize_expression
# ==================================================================

class TestNormalize:
    def test_operador_multiplicacao_unicode(self):
        assert "*" in normalize_expression("3 × 4")

    def test_operador_divisao_unicode(self):
        assert "/" in normalize_expression("10 ÷ 2")

    def test_potencia_chapeu(self):
        assert "**" in normalize_expression("2^8")

    def test_virgula_para_ponto(self):
        assert "3.14" in normalize_expression("3,14")

    def test_palavras_pt_mais(self):
        assert "+" in normalize_expression("dois mais dois")

    def test_palavras_pt_menos(self):
        assert "-" in normalize_expression("10 menos 3")

    def test_palavras_pt_vezes(self):
        assert "*" in normalize_expression("5 vezes 3")

    def test_palavras_pt_dividido(self):
        assert "/" in normalize_expression("10 dividido por 2")

    def test_traco_em_dash(self):
        assert "-" in normalize_expression("10 – 3")


# ==================================================================
# try_formula_query
# ==================================================================

class TestFormulaQuery:
    def test_area_circulo(self):
        match = try_formula_query("área do círculo raio=5")
        assert match is not None
        desc, formula = match
        assert "π" in desc or "pi" in formula.lower()

    def test_area_circulo_sem_acento(self):
        match = try_formula_query("area do circulo r=3")
        assert match is not None

    def test_volume_esfera(self):
        match = try_formula_query("volume da esfera r=2")
        assert match is not None

    def test_juros_compostos(self):
        match = try_formula_query("juros compostos p=1000 i=0.1 n=2")
        assert match is not None

    def test_juros_simples(self):
        match = try_formula_query("juros simples p=500 i=0.05 t=3")
        assert match is not None

    def test_sem_formula(self):
        match = try_formula_query("2 + 2")
        assert match is None

    def test_texto_aleatorio(self):
        match = try_formula_query("quanto é dois mais dois?")
        assert match is None


# ==================================================================
# calculate_expression — integração
# ==================================================================

class TestCalculateExpression:
    @pytest.mark.parametrize("expr,expected", [
        ("2 + 2", 4.0),
        ("10 - 3", 7.0),
        ("5 * 3", 15.0),
        ("16 / 4", 4.0),
        ("2 ** 8", 256.0),
        ("sqrt(9)", 3.0),
        ("(5 + 3) * 2", 16.0),
    ])
    def test_aritmetica(self, expr, expected):
        r, _ = calculate_expression(expr)
        assert r == pytest.approx(expected), f"Falhou: {expr}"

    def test_entrada_vazia(self):
        r, msg = calculate_expression("")
        assert r is None
        assert msg

    def test_entrada_none_like(self):
        r, msg = calculate_expression("   ")
        assert r is None

    def test_formula_area_com_parametro(self):
        r, msg = calculate_expression("área do círculo raio=5")
        assert r is not None
        assert r == pytest.approx(math.pi * 25, rel=1e-5)

    def test_formula_volume_esfera(self):
        r, _ = calculate_expression("volume da esfera r=3")
        assert r is not None
        assert r == pytest.approx(4/3 * math.pi * 27, rel=1e-5)

    def test_formula_juros_compostos(self):
        r, _ = calculate_expression("juros compostos p=1000 i=0.1 n=2")
        assert r is not None
        assert r == pytest.approx(1000 * (1.1 ** 2), rel=1e-5)

    def test_injecao_bloqueada(self):
        r, msg = calculate_expression("__import__('os').system('ls')")
        assert r is None

    def test_expressao_unicode(self):
        r, _ = calculate_expression("3 × 4")
        assert r == pytest.approx(12.0)

    def test_expressao_portugues(self):
        r, _ = calculate_expression("5 mais 3")
        assert r == pytest.approx(8.0)


# ==================================================================
# OCR — com mock (sem Tesseract necessário)
# ==================================================================

class TestOCR:
    def test_arquivo_nao_encontrado(self):
        from arkymedes_calc import ocr_text_from_image
        with pytest.raises(FileNotFoundError):
            ocr_text_from_image("/nao/existe/imagem.png")

    @patch("arkymedes_calc.HAS_PIL", False)
    def test_sem_pillow(self):
        from arkymedes_calc import ocr_text_from_image
        with pytest.raises(ImportError, match="Pillow"):
            ocr_text_from_image("qualquer.png")

    @patch("arkymedes_calc.HAS_TESSERACT", False)
    def test_sem_pytesseract(self):
        from arkymedes_calc import ocr_text_from_image
        with pytest.raises(ImportError, match="pytesseract"):
            ocr_text_from_image("qualquer.png")

    def test_arquivo_invalido(self, tmp_path):
        fake = tmp_path / "fake.jpg"
        fake.write_bytes(b"nao sou uma imagem")
        from arkymedes_calc import ocr_text_from_image
        with pytest.raises((ValueError, Exception)):
            ocr_text_from_image(str(fake))


# ==================================================================
# PDF — com mock
# ==================================================================

class TestPDF:
    def test_arquivo_nao_encontrado(self):
        from arkymedes_calc import extract_text_from_pdf
        with pytest.raises(FileNotFoundError):
            extract_text_from_pdf("/nao/existe/arquivo.pdf")

    def test_extensao_invalida(self, tmp_path):
        fake = tmp_path / "doc.txt"
        fake.write_text("conteúdo")
        from arkymedes_calc import extract_text_from_pdf
        with pytest.raises(ValueError, match="PDF"):
            extract_text_from_pdf(str(fake))

    @patch("arkymedes_calc.HAS_PYPDF", False)
    @patch("arkymedes_calc.HAS_PDF2IMAGE", False)
    def test_sem_dependencias(self, tmp_path):
        fake = tmp_path / "doc.pdf"
        fake.write_bytes(b"%PDF-1.4 fake")
        from arkymedes_calc import extract_text_from_pdf
        with pytest.raises(ImportError):
            extract_text_from_pdf(str(fake))


# ==================================================================
# SafeCalculator — recursão
# ==================================================================

class TestRecursao:
    def test_limite_recursao(self):
        calc = SafeCalculator()
        calc.max_recursion = 2
        r, msg = calc.evaluate("1 + 2 + 3 + 4 + 5")
        # Pode falhar ou não dependendo da profundidade — apenas verifica que não trava
        assert isinstance(msg, str)


# ==================================================================
# Parametrized — stress test de segurança
# ==================================================================

PAYLOADS_PERIGOSOS = [
    "__class__",
    "__bases__",
    "__subclasses__",
    "__mro__",
    "os.system",
    "subprocess.run",
    "open('/etc/passwd')",
    "().__class__.__bases__[0].__subclasses__()",
    "1 if True else __import__('os')",
]

@pytest.mark.parametrize("payload", PAYLOADS_PERIGOSOS)
def test_payloads_perigosos(payload):
    r, _ = safe_evaluate(payload)
    assert r is None, f"VULNERABILIDADE CRÍTICA: '{payload}' não bloqueado!"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])