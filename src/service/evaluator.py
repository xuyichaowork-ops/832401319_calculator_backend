"""Safe mathematical expression evaluator.

This module implements a small recursive-descent parser for arithmetic
expressions.  It deliberately does NOT use ``eval`` / ``exec`` / any code
execution builtin, satisfying the assignment's security constraint
("后端禁止使用 eval、exec 或任意代码执行方法处理用户输入").

Supported grammar
-----------------
    expression := term (('+' | '-') term)*
    term       := factor (('*' | '/') factor)*
    factor     := ('+' | '-') factor
                | NUMBER
                | '(' expression ')'
    NUMBER     := DIGIT+ ('.' DIGIT+)?

Supports: + - * / , parentheses, unary plus/minus, decimals.
Division by zero and malformed input raise ``EvalError``.
"""

import re

__all__ = ["EvalError", "evaluate", "normalize_expression"]


class EvalError(Exception):
    """Raised when the input expression cannot be parsed or evaluated."""


# Token pattern: optional leading whitespace, then a NUMBER or an OPERATOR.
_TOKEN_RE = re.compile(
    r"""
    \s*
    (?:
        (?P<NUMBER>\d+\.\d+|\d+\.|\.\d+|\d+)
      | (?P<OP>[+\-*/()])
    )
    """,
    re.VERBOSE,
)


def normalize_expression(expr: str) -> str:
    """Map common display operators to ASCII equivalents used by the parser.

    The calculator UI may send ``×``, ``÷`` and the Unicode minus ``−``;
    this converts them so the parser only has to deal with ASCII.
    """
    if not isinstance(expr, str):
        raise EvalError("表达式必须是字符串")
    table = {
        "\u00d7": "*",  # ×
        "\u00f7": "/",  # ÷
        "\u2212": "-",  # − minus sign
        "\uff0a": "*",  # ＊ fullwidth asterisk
        "\uff0d": "-",  # － fullwidth hyphen-minus
        "\uff0f": "/",  # ／ fullwidth solidus
    }
    for k, v in table.items():
        expr = expr.replace(k, v)
    return expr


def tokenize(expr: str):
    """Split an expression string into a list of (TYPE, VALUE) tokens."""
    tokens = []
    pos = 0
    length = len(expr)
    while pos < length:
        match = _TOKEN_RE.match(expr, pos)
        if not match or match.end() == pos:
            # Skip a single whitespace character if present, else fail.
            if expr[pos].isspace():
                pos += 1
                continue
            raise EvalError(f"无法识别的字符：{expr[pos]!r}")
        pos = match.end()
        if match.group("NUMBER") is not None:
            tokens.append(("NUMBER", float(match.group("NUMBER"))))
        else:
            tokens.append(("OP", match.group("OP")))
    return tokens


class _Parser:
    """Recursive-descent parser + evaluator over a token list."""

    def __init__(self, tokens):
        self.tokens = tokens
        self.i = 0

    def _peek(self):
        if self.i < len(self.tokens):
            return self.tokens[self.i]
        return (None, None)

    def _advance(self):
        tok = self._peek()
        self.i += 1
        return tok

    def parse(self):
        if not self.tokens:
            raise EvalError("空表达式")
        value = self._expression()
        if self.i != len(self.tokens):
            raise EvalError("表达式存在多余的符号")
        return value

    def _expression(self):
        value = self._term()
        while self._peek()[0] == "OP" and self._peek()[1] in "+-":
            op = self._advance()[1]
            rhs = self._term()
            value = value + rhs if op == "+" else value - rhs
        return value

    def _term(self):
        value = self._factor()
        while self._peek()[0] == "OP" and self._peek()[1] in "*/":
            op = self._advance()[1]
            rhs = self._factor()
            if op == "*":
                value = value * rhs
            else:
                if rhs == 0:
                    raise EvalError("除数不能为 0")
                value = value / rhs
        return value

    def _factor(self):
        tok = self._peek()
        # Unary sign.
        if tok[0] == "OP" and tok[1] in "+-":
            op = self._advance()[1]
            value = self._factor()
            return -value if op == "-" else value
        # Parenthesised sub-expression.
        if tok[0] == "OP" and tok[1] == "(":
            self._advance()
            value = self._expression()
            nxt = self._peek()
            if nxt[0] != "OP" or nxt[1] != ")":
                raise EvalError("括号不匹配")
            self._advance()
            return value
        # Number literal.
        if tok[0] == "NUMBER":
            self._advance()
            return tok[1]
        raise EvalError("表达式格式错误")


def format_result(value: float) -> str:
    """Render a float result compactly (integers without decimals)."""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    # %g removes floating-point noise and trailing zeros.
    return f"{value:.12g}"


def evaluate(expression: str) -> str:
    """Parse and evaluate ``expression``; return the result as a string.

    Raises ``EvalError`` on invalid syntax or division by zero.
    """
    normalized = normalize_expression(expression).strip()
    if not normalized:
        raise EvalError("表达式为空白")
    if len(normalized) > 200:
        raise EvalError("表达式过长")
    tokens = tokenize(normalized)
    parser = _Parser(tokens)
    result = parser.parse()
    return format_result(result)
