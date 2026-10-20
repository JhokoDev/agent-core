import unittest
import asyncio
import os
import tempfile
from pathlib import Path

from app.services.life_os.database import LifeOSDatabase
from app.services.life_os.finance import LifeOSFinanceEngine
from app.services.life_os.service import LifeOSService

class TestLifeOS(unittest.TestCase):
    def setUp(self):
        # Usar banco temporário isolado para não sujar o data/life_os.db
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_life_os.db"
        self.db = LifeOSDatabase(self.db_path)
        self.service = LifeOSService()
        self.service.db = self.db
        self.service.finance = LifeOSFinanceEngine(self.db)
        self.service.escalation.db = self.db

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_criar_e_limite_3_tarefas_criticas(self):
        """Verifica se a 4ª tarefa crítica no mesmo dia é rebaixada para 'importante' para evitar sobrecarga."""
        t1 = self.service.criar_tarefa({"titulo": "Critica 1", "criticidade": "critica", "data_prevista": "2026-10-20"})
        t2 = self.service.criar_tarefa({"titulo": "Critica 2", "criticidade": "critica", "data_prevista": "2026-10-20"})
        t3 = self.service.criar_tarefa({"titulo": "Critica 3", "criticidade": "critica", "data_prevista": "2026-10-20"})
        t4 = self.service.criar_tarefa({"titulo": "Critica 4", "criticidade": "critica", "data_prevista": "2026-10-20"})

        self.assertEqual(t1["criticidade"], "critica")
        self.assertEqual(t2["criticidade"], "critica")
        self.assertEqual(t3["criticidade"], "critica")
        self.assertEqual(t4["criticidade"], "importante")  # Rebaixada para importante!

    def test_adiamento_com_memoria_comportamental(self):
        """Verifica se os motivos de adiamento são acumulados no histórico JSON da tarefa."""
        t = self.service.criar_tarefa({"titulo": "Estudar Algoritmos", "criticidade": "importante"})
        tarefa_id = t["id"]

        self.service.adiar_tarefa(tarefa_id, motivo="Tive que almoçar", minutos=20)
        t_adiada = self.service.obter_tarefa(tarefa_id)

        self.assertEqual(t_adiada["postpone_count"], 1)
        self.assertEqual(len(t_adiada["postpone_reasons"]), 1)
        self.assertEqual(t_adiada["postpone_reasons"][0]["motivo"], "Tive que almoçar")

        # Segundo adiamento
        self.service.adiar_tarefa(tarefa_id, motivo="Preguiça momentânea", minutos=15)
        t_adiada2 = self.service.obter_tarefa(tarefa_id)
        self.assertEqual(t_adiada2["postpone_count"], 2)
        self.assertEqual(len(t_adiada2["postpone_reasons"]), 2)

    def test_conclusao_com_proof_of_work(self):
        """Verifica a conclusão de tarefa registrando a prova de conclusão."""
        t = self.service.criar_tarefa({"titulo": "Fazer deploy do módulo", "proof_of_work_type": "texto"})
        tarefa_id = t["id"]

        concluida = self.service.concluir_tarefa(tarefa_id, prova="Commit hash 83f7a1b enviado com sucesso")
        self.assertEqual(concluida["status"], "concluida")
        self.assertIn("83f7a1b", concluida["proof_of_work_data"])

    def test_parser_financeiro_horas_de_vida_e_teto(self):
        """Testa o parsing de notificações bancárias, cálculo de Horas de Vida e Teto Diário Livre."""
        self.db.definir_config("valor_hora_trabalho", "25.0")  # R$ 25 por hora
        self.db.definir_config("teto_diario_livre", "50.0")     # Teto diário de R$ 50

        # Gasto dentro do teto
        res1 = self.service.finance.processar_notificacao_bancaria(
            app_origem="com.nu.production",
            texto="Você pagou R$ 30,00 para Padaria Estrela",
            titulo="Compra aprovada"
        )
        self.assertTrue(res1["sucesso"])
        self.assertEqual(res1["valor"], 30.0)
        self.assertEqual(res1["horas_vida"], 1.2)  # 30 / 25 = 1.2 horas
        self.assertFalse(res1["estourou_teto"])
        self.assertEqual(res1["saldo_restante"], 20.0)

        # Segundo gasto estourando o teto
        res2 = self.service.finance.processar_notificacao_bancaria(
            app_origem="com.intermedium",
            texto="Pix enviado no valor de R$ 25,00 para Lanches",
            titulo="Pix Realizado"
        )
        self.assertTrue(res2["sucesso"])
        self.assertEqual(res2["valor"], 25.0)
        self.assertTrue(res2["estourou_teto"])  # 30 + 25 = 55 > 50!
        self.assertIn("TETO DIÁRIO ESTOURADO", res2["feedback"])

    def test_pedagio_de_compra(self):
        """Testa o cálculo do pedágio anti-impulso."""
        self.db.definir_config("valor_hora_trabalho", "20.0")
        self.db.definir_config("teto_diario_livre", "50.0")

        pedagio = self.service.finance.calcular_pedagio_compra(valor_compra=200.0, nome_item="Headset Novo")
        self.assertEqual(pedagio["horas_trabalho"], 10.0)
        self.assertEqual(pedagio["dias_teto_livre"], 4.0)
        self.assertIn("10.0h de foco", pedagio["conselho"])

    def test_auto_tetris_reorganiza_agenda(self):
        """Testa o Auto-Tetris empurrando tarefas de rotina subsequentes quando uma crítica atrasa."""
        t1 = self.service.criar_tarefa({
            "titulo": "Finalizar Feature Crítica",
            "criticidade": "critica",
            "horario_previsto": "14:00"
        })
        t2 = self.service.criar_tarefa({
            "titulo": "Limpar caixa de entrada",
            "criticidade": "rotina",
            "horario_previsto": "15:00"
        })

        resultado_tetris = self.service.escalation.executar_auto_tetris(
            tarefa_critica_id=t1["id"],
            minutos_estouro=30
        )
        self.assertTrue(resultado_tetris["sucesso"])
        self.assertEqual(resultado_tetris["minutos_empurrados"], 30)

        t2_atualizada = self.service.obter_tarefa(t2["id"])
        self.assertEqual(t2_atualizada["horario_previsto"], "15:30")

    def test_api_rotas_com_testclient(self):
        """Testa a integração das rotas do FastAPI no app principal."""
        from fastapi.testclient import TestClient
        from app.api.main import app

        with TestClient(app) as client:
            # 1. Status geral
            res_status = client.get("/api/life/status")
            self.assertEqual(res_status.status_code, 200)
            data_status = res_status.json()
            self.assertIn("tarefas_total_hoje", data_status)
            self.assertIn("financas", data_status)

            # 2. Criar tarefa via API
            payload_tarefa = {
                "titulo": "Revisar Módulo de Arquitetura",
                "criticidade": "critica",
                "micro_step_sugerido": "Abrir o VS Code na pasta certa",
                "contexto_execucao": "pc"
            }
            res_post = client.post("/api/life/tarefas", json=payload_tarefa)
            self.assertEqual(res_post.status_code, 200)
            tarefa_criada = res_post.json()
            t_id = tarefa_criada["id"]

            # 3. Adiar tarefa via API
            res_adiar = client.post(f"/api/life/tarefas/{t_id}/adiar", json={
                "motivo": "Reunião de emergência",
                "minutos_adiamento": 20
            })
            self.assertEqual(res_adiar.status_code, 200)
            self.assertEqual(res_adiar.json()["postpone_count"], 1)

            # 4. Webhook de notificação bancária via API
            res_banco = client.post("/api/life/financas/webhook-banco", json={
                "app_origem": "com.nu.production",
                "texto": "Compra de R$ 42,50 no débito aprovada",
                "titulo": "Nubank"
            })
            self.assertEqual(res_banco.status_code, 200)
            self.assertTrue(res_banco.json()["sucesso"])

            # 5. Ação ntfy (Estou a caminho)
            res_acao = client.post("/api/life/acoes-ntfy", json={
                "acao": "estou_a_caminho",
                "tarefa_id": t_id
            })
            self.assertEqual(res_acao.status_code, 200)
            self.assertTrue(res_acao.json()["sucesso"])

            # 6. Concluir tarefa via botão ntfy
            res_concluir = client.post("/api/life/acoes-ntfy", json={
                "acao": "concluir",
                "tarefa_id": t_id
            })
            self.assertEqual(res_concluir.status_code, 200)
            self.assertTrue(res_concluir.json()["sucesso"])

            # 7. Limpeza: remover tarefa criada no teste
            client.delete(f"/api/life/tarefas/{t_id}")

if __name__ == "__main__":
    unittest.main()
