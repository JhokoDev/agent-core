from typing import Any

from app.tools.tool_contract import ToolContract


TIPOS_PERMITIDOS = {
    "string": str,
    "integer": int,
    "number": (int, float),
    "boolean": bool,
    "object": dict,
    "array": list,
}


def validar_argumentos(
    ferramenta: ToolContract,
    argumentos: dict[str, Any],
) -> tuple[bool, str]:
    if not isinstance(argumentos, dict):
        return False, "Os argumentos da ferramenta devem ser um objeto."

    schema = ferramenta.argumentos or {}

    for nome, configuracao in schema.items():
        if not isinstance(configuracao, dict):
            continue

        obrigatorio = configuracao.get("obrigatorio", False)

        if obrigatorio and nome not in argumentos:
            return False, (
                f"O argumento obrigatório '{nome}' não foi informado."
            )

        if nome not in argumentos:
            continue

        valor = argumentos[nome]
        tipo = configuracao.get("tipo")

        if tipo not in TIPOS_PERMITIDOS:
            return False, (
                f"O schema da ferramenta possui o tipo "
                f"desconhecido '{tipo}'."
            )

        tipo_esperado = TIPOS_PERMITIDOS[tipo]

        # bool é uma subclasse de int em Python.
        # Por isso precisa ser tratado separadamente.
        if tipo in {"integer", "number"} and isinstance(valor, bool):
            return False, (
                f"O argumento '{nome}' deve possuir o tipo '{tipo}'."
            )

        if not isinstance(valor, tipo_esperado):
            return False, (
                f"O argumento '{nome}' deve possuir o tipo '{tipo}'."
            )

    return True, ""