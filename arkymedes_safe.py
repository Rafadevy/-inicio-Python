#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Arkymedes — Módulo de avaliação segura - Secure expression evaluation without code injection risk."""

import ast
import operator
import math
import re
import logging
from typing import Tuple, Optional, Any

logger = logging.getLogger(__name__)

# Whitelist de operações permitidas
SAFE_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}

# Whitelist de funções matemáticas seguras
SAFE_FUNCTIONS = {
    'abs': abs,
    'sqrt': math.sqrt,
    'sin': math.sin,
    'cos': math.cos,
    'tan': math.tan,
    'asin': math.asin,
    'acos': math.acos,
    'atan': math.atan,
    'sinh': math.sinh,
    'cosh': math.cosh,
    'tanh': math.tanh,
    'exp': math.exp,
    'log': math.log,
    'log10': math.log10,
    'log2': math.log2,
    'ln': math.log,
    'ceil': math.ceil,
    'floor': math.floor,
    'round': round,
    'min': min,
    'max': max,
    'sum': sum,
    'pow': pow,
}

# Whitelist de constantes seguras
MAX_POWER = 10000
MAX_ABS_RESULT = 1e100

SAFE_CONSTANTS = {
    'pi': math.pi,
    'e': math.e,
    'tau': math.tau,
    'inf': math.inf,
    'nan': math.nan,
}


class SafeCalculator:
    """Avaliador seguro de expressões matemáticas."""
    
    def __init__(self):
        self.max_recursion = 100
        self.recursion_depth = 0
    
    def evaluate(self, expression: str) -> Tuple[Optional[float], str]:
        """
        Avaliar expressão de forma segura.
        
        Returns:
            Tupla (resultado, mensagem)
            - resultado: float se sucesso, None se erro
            - mensagem: descrição de sucesso ou erro
        """
        try:
            # Reset recursion counter
            self.recursion_depth = 0
            
            # Validação de entrada
            validation_error = self._validate_input(expression)
            if validation_error:
                logger.warning(f"Validação falhou: {validation_error} (input: {expression})")
                return None, f"Entrada inválida: {validation_error}"
            
            # Parse da expressão
            try:
                tree = ast.parse(expression, mode='eval')
            except SyntaxError as e:
                logger.warning(f"Erro de sintaxe: {e}")
                return None, f"Erro de sintaxe: {str(e)}"
            
            # Validação da AST
            security_error = self._validate_ast(tree.body)
            if security_error:
                logger.warning(f"Violação de segurança detectada: {security_error}")
                return None, f"Operação não permitida: {security_error}"
            
            # Avaliação
            result = self._eval_node(tree.body)
            
            # Validar resultado
            if isinstance(result, (int, float)):
                if math.isnan(result):
                    return None, "Resultado: NaN (operação inválida)"
                if math.isinf(result):
                    return None, "Resultado: infinito"
                return float(result), str(float(result))
            
            return None, f"Resultado inválido: {type(result)}"
            
        except ZeroDivisionError:
            logger.warning("Divisão por zero")
            return None, "Erro: Divisão por zero"
        
        except Exception as e:
            logger.exception(f"Erro durante avaliação: {e}")
            return None, f"Erro: {str(e)}"
    
    def _validate_input(self, expression: str) -> Optional[str]:
        """Validar entrada antes de processar."""
        if not expression or not expression.strip():
            return "Expressão vazia"
        
        if len(expression) > 1000:
            return "Expressão muito longa"
        
        # Detectar palavras-chave perigosas
        dangerous_keywords = [
            '__', 'import', 'exec', 'eval', 'open', 'file',
            'compile', 'globals', 'locals', 'vars', 'dir',
            'getattr', 'setattr', 'delattr', 'type',
            'lambda', 'class', 'def', 'return'
        ]
        
        lower_expr = expression.lower()
        for keyword in dangerous_keywords:
            if keyword in lower_expr:
                return f"Palavra-chave proibida: {keyword}"
        
        return None
    
    def _validate_ast(self, node: ast.expr) -> Optional[str]:
        """Validar AST para detectar operações perigosas."""
        if isinstance(node, ast.Expression):
            return self._validate_ast(node.body)
        
        elif isinstance(node, ast.Constant):
            # Literais numéricos são seguros
            return None
        
        elif isinstance(node, ast.Name):
            # Apenas constantes pré-aprovadas
            if node.id not in SAFE_CONSTANTS:
                return f"Variável não permitida: {node.id}"
            return None
        
        elif isinstance(node, ast.BinOp):
            # Operações binárias são seguras se operadores forem permitidos
            if type(node.op) not in SAFE_OPERATORS:
                return f"Operador não permitido: {type(node.op).__name__}"
            left_error = self._validate_ast(node.left)
            if left_error:
                return left_error
            return self._validate_ast(node.right)
        
        elif isinstance(node, ast.UnaryOp):
            # Operações unárias
            if type(node.op) not in SAFE_OPERATORS:
                return f"Operador unário não permitido: {type(node.op).__name__}"
            return self._validate_ast(node.operand)
        
        elif isinstance(node, ast.Call):
            # Apenas funções pré-aprovadas
            if isinstance(node.func, ast.Name):
                if node.func.id not in SAFE_FUNCTIONS:
                    return f"Função não permitida: {node.func.id}"
            else:
                return "Chamadas aninhadas não permitidas"
            
            # Validar argumentos
            for arg in node.args:
                error = self._validate_ast(arg)
                if error:
                    return error
            
            return None
        
        elif isinstance(node, ast.List):
            # Listas não são permitidas
            return "Listas não são permitidas"
        
        elif isinstance(node, ast.Dict):
            # Dicts não são permitidas
            return "Dicionários não são permitidos"
        
        elif isinstance(node, ast.Lambda):
            return "Lambdas não são permitidas"
        
        elif isinstance(node, ast.Compare):
            # Comparações podem ser permitidas (≠, <, >, ≤, ≥, ==)
            # Mas vamos bloquear por enquanto
            return "Comparações não são permitidas"
        
        elif isinstance(node, ast.BoolOp):
            # And/Or não são permitidos
            return "Operadores booleanos não são permitidos"
        
        else:
            return f"Tipo de nó não permitido: {type(node).__name__}"
    
    def _eval_node(self, node: ast.expr) -> Any:
        """Avaliar nó da AST recursivamente."""
        self.recursion_depth += 1
        if self.recursion_depth > self.max_recursion:
            raise RuntimeError("Profundidade de recursão excedida")
        
        try:
            if isinstance(node, ast.Constant):
                return node.value
            
            elif isinstance(node, ast.Name):
                return SAFE_CONSTANTS[node.id]
            
            elif isinstance(node, ast.BinOp):
                left = self._eval_node(node.left)
                right = self._eval_node(node.right)
                op_func = SAFE_OPERATORS[type(node.op)]
                if type(node.op).__name__ == "Pow":
                    if abs(right) > MAX_POWER:
                        raise ValueError("Expoente muito grande")
                result = op_func(left, right)
                if isinstance(result, (int, float)) and abs(result) > MAX_ABS_RESULT:
                    raise ValueError("Resultado excede limite permitido")
                return result
            
            elif isinstance(node, ast.UnaryOp):
                operand = self._eval_node(node.operand)
                op_func = SAFE_OPERATORS[type(node.op)]
                return op_func(operand)
            
            elif isinstance(node, ast.Call):
                func = SAFE_FUNCTIONS[node.func.id]
                args = [self._eval_node(arg) for arg in node.args]
                return func(*args)
            
            else:
                raise ValueError(f"Tipo de nó não suportado: {type(node).__name__}")
        
        finally:
            self.recursion_depth -= 1


# Instância global
_calculator = SafeCalculator()


def safe_evaluate(expression: str) -> Tuple[Optional[float], str]:
    """
    Avaliar expressão de forma segura (interface pública).
    
    Args:
        expression: String da expressão matemática
    
    Returns:
        Tupla (resultado, mensagem)
    """
    return _calculator.evaluate(expression)


# Testes básicos
if __name__ == "__main__":
    test_cases = [
        ("2 + 2", True),
        ("10 * 5", True),
        ("sqrt(16)", True),
        ("sin(pi/2)", True),
        ("__import__('os')", False),
        ("eval('2+2')", False),
        ("exec('print(1)')", False),
        ("globals()", False),
        ("lambda x: x+1", False),
        ("[1,2,3]", False),
    ]
    
    print("\n" + "="*70)
    print("🔒 TESTE DE SEGURANÇA - Safe Calculator")
    print("="*70 + "\n")
    
    for expr, should_pass in test_cases:
        result, message = safe_evaluate(expr)
        status = "✓" if (result is not None) == should_pass else "✗"
        result_str = f"{result:.4f}" if result is not None else "BLOQUEADO"
        print(f"{status} {expr:.<30} {result_str:>15} | {message[:30]}")
    
    print("\n" + "="*70 + "\n")
