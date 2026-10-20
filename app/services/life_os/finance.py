import re
import logging
from typing import Dict, Any, Tuple, Optional
from app.services.life_os.database import LifeOSDatabase

logger = logging.getLogger("LifeOSFinance")

class LifeOSFinanceEngine:
    """
    Motor Financeiro Zero-Planilha.
    Intercepta notificações bancárias de apps Android (Nubank, Inter, PicPay, etc.),
    traduz gastos para 'Horas de Vida' de esforço e monitora o Teto Diário Livre.
    """

    def __init__(self, db: LifeOSDatabase):
        self.db = db

    def extrair_dados_notificacao(self, app_origem: str, texto: str, titulo: str = "") -> Tuple[float, str, str, str]:
        """
        Extrai (valor, tipo, categoria, descricao) do texto bruto de notificações bancárias.
        """
        texto_limpo = f"{titulo} {texto}".strip()
        
        # Regex para capturar valores monetários em Real (ex: R$ 45,90 ou R$45.90 ou 45,90)
        match_valor = re.search(r"R\$\s*([0-9]{1,3}(?:\.[0-9]{3})*,[0-9]{2}|[0-9]+[.,][0-9]{2})", texto_limpo, re.IGNORECASE)
        
        valor = 0.0
        if match_valor:
            valor_str = match_valor.group(1).replace(".", "").replace(",", ".")
            try:
                valor = float(valor_str)
            except ValueError:
                valor = 0.0

        # Identificação de Tipo (Receita vs Despesa)
        texto_lower = texto_limpo.lower()
        if any(termo in texto_lower for termo in ["recebeu", "transferência recebida", "pix recebido", "estorno", "depósito"]):
            tipo = "receita"
        else:
            tipo = "despesa"

        # Sugestão heurística de categoria
        if any(termo in texto_lower for termo in ["aluguel", "luz", "água", "energia", "internet", "fatura"]):
            categoria = "custos_fixos"
        elif any(termo in texto_lower for termo in ["investimento", "reserva", "cdb", "tesouro", "aporte"]):
            categoria = "construcao_futuro"
        elif any(termo in texto_lower for termo in ["curso", "livro", "udemy", "alura", "hardware", "faculdade"]):
            categoria = "autoaperfeicoamento"
        else:
            categoria = "livre_lazer"

        # Descrição simplificada
        descricao = texto[:120]

        return valor, tipo, categoria, descricao

    def processar_notificacao_bancaria(
        self,
        app_origem: str,
        texto: str,
        titulo: str = ""
    ) -> Dict[str, Any]:
        """
        Processa a notificação capturada pelo MacroDroid e persiste a transação.
        Gera o feedback com 'Horas de Vida' e status do Teto Diário.
        """
        valor, tipo, categoria, descricao = self.extrair_dados_notificacao(app_origem, texto, titulo)

        if valor <= 0:
            logger.info(f"[Finance] Notificação ignorada (sem valor monetário detectado): {texto}")
            return {
                "sucesso": False,
                "motivo": "Valor monetário não identificado na notificação",
                "texto_original": texto
            }

        # Registrar transação no SQLite
        transacao_id = self.db.registrar_transacao(
            tipo=tipo,
            valor=valor,
            categoria=categoria,
            descricao=descricao,
            origem=f"macrodroid:{app_origem}",
            raw_payload=f"{titulo} | {texto}"
        )

        # Cálculos de impacto comportamental
        valor_hora = float(self.db.obter_config("valor_hora_trabalho", "25.0"))
        horas_vida = round(valor / valor_hora, 1) if valor_hora > 0 else 0.0

        teto_diario = float(self.db.obter_config("teto_diario_livre", "50.0"))
        gastos_hoje = self.db.obter_gastos_hoje()
        saldo_restante = round(teto_diario - gastos_hoje, 2)

        estourou_teto = saldo_restante < 0

        # Geração do feedback
        if tipo == "despesa":
            if estourou_teto:
                feedback = (
                    f"🚨 TETO DIÁRIO ESTOURADO! Você gastou R$ {valor:.2f} ({horas_vida}h de trabalho). "
                    f"Você está R$ {abs(saldo_restante):.2f} além do limite de hoje. Foco no essencial!"
                )
            else:
                feedback = (
                    f"💸 Gasto registrado: R$ {valor:.2f} ({horas_vida}h de esforço). "
                    f"Ainda restam R$ {saldo_restante:.2f} do seu teto livre de hoje."
                )
        else:
            feedback = f"💰 Entrada registrada: R$ {valor:.2f}! Bom trabalho."

        return {
            "sucesso": True,
            "transacao_id": transacao_id,
            "valor": valor,
            "tipo": tipo,
            "categoria": categoria,
            "horas_vida": horas_vida,
            "gastos_hoje": gastos_hoje,
            "teto_diario": teto_diario,
            "saldo_restante": saldo_restante,
            "estourou_teto": estourou_teto,
            "feedback": feedback
        }

    def calcular_pedagio_compra(self, valor_compra: float, nome_item: str = "Item") -> Dict[str, Any]:
        """
        Modo 'Guardião Financeiro' / Pedágio de Compra:
        Mede o custo de uma compra por impulso antes de você pagar.
        """
        valor_hora = float(self.db.obter_config("valor_hora_trabalho", "25.0"))
        horas_trabalho = round(valor_compra / valor_hora, 1) if valor_hora > 0 else 0.0
        dias_trabalho = round(horas_trabalho / 8.0, 1)

        teto_diario = float(self.db.obter_config("teto_diario_livre", "50.0"))
        dias_teto = round(valor_compra / teto_diario, 1) if teto_diario > 0 else 0.0

        conselho = (
            f"Comprar '{nome_item}' por R$ {valor_compra:.2f} custará {horas_trabalho}h de foco "
            f"({dias_trabalho} dias úteis inteiros de trabalho) ou o equivalente a {dias_teto} dias do seu teto livre. "
            f"Vale a pena trocar esse tempo de vida por isso agora?"
        )

        return {
            "item": nome_item,
            "valor": valor_compra,
            "horas_trabalho": horas_trabalho,
            "dias_trabalho": dias_trabalho,
            "dias_teto_livre": dias_teto,
            "conselho": conselho
        }
