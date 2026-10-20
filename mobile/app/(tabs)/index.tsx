import React, { useState, useEffect, useCallback } from 'react';
import {
  StyleSheet,
  Text,
  View,
  ScrollView,
  TouchableOpacity,
  ActivityIndicator,
  RefreshControl,
  Modal,
  TextInput,
  Alert
} from 'react-native';
import { agentApi } from '../../src/services/api';
import { DashboardStatus, Tarefa } from '../../src/types';

export default function CockpitScreen() {
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [dashboard, setDashboard] = useState<DashboardStatus | null>(null);

  // Modais de ação
  const [postponeModalVisible, setPostponeModalVisible] = useState(false);
  const [completeModalVisible, setCompleteModalVisible] = useState(false);
  const [selectedTask, setSelectedTask] = useState<Tarefa | null>(null);
  const [postponeReason, setPostponeReason] = useState('');
  const [proofText, setProofText] = useState('');
  const [actionLoading, setActionLoading] = useState(false);

  // Entrada Rápida de Atividades (Inbox Cognitivo)
  const [quickInput, setQuickInput] = useState('');
  const [quickSubmitting, setQuickSubmitting] = useState(false);

  const handleQuickSubmit = async () => {
    if (!quickInput.trim()) return;
    try {
      setQuickSubmitting(true);
      const res = await agentApi.enviarInbox(quickInput.trim());
      if (res.status === 'criado') {
        Alert.alert('✅ Registrado com Sucesso!', res.feedback || 'Atividade adicionada ao seu Life OS.');
        setQuickInput('');
        carregarDados();
      } else if (res.status === 'aguardando_confirmacao') {
        Alert.alert('⚠️ Ajuste Necessário', res.mensagem);
      } else {
        Alert.alert('Aviso', res.mensagem || 'Não foi possível processar a entrada.');
      }
    } catch (err: any) {
      Alert.alert('Erro', err.message || 'Falha ao enviar para o Inbox.');
    } finally {
      setQuickSubmitting(false);
    }
  };

  const carregarDados = useCallback(async () => {
    try {
      const data = await agentApi.getDashboardStatus();
      setDashboard(data);
    } catch (err: any) {
      console.warn('Falha ao carregar cockpit:', err.message);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    carregarDados();
    const interval = setInterval(carregarDados, 15000); // Polling suave a cada 15s
    return () => clearInterval(interval);
  }, [carregarDados]);

  const onRefresh = () => {
    setRefreshing(true);
    carregarDados();
  };

  const handlePrepararPC = async (tarefaId: number) => {
    try {
      setActionLoading(true);
      await agentApi.prepararPC(tarefaId);
      Alert.alert(
        'PC Notificado!',
        'O Agent Core no seu Windows está abrindo o VS Code e as ferramentas agora.'
      );
    } catch (err: any) {
      Alert.alert('Erro', err.message || 'Falha ao conectar com o PC.');
    } finally {
      setActionLoading(false);
    }
  };

  const handleConfirmarAdiar = async () => {
    if (!selectedTask || !postponeReason.trim()) {
      Alert.alert('Aviso', 'Por favor informe o motivo do adiamento.');
      return;
    }
    try {
      setActionLoading(true);
      await agentApi.adiarTarefa(selectedTask.id, postponeReason.trim(), 15);
      setPostponeModalVisible(false);
      setPostponeReason('');
      carregarDados();
      Alert.alert('Tarefa Adiada', 'Novo horário agendado para daqui a 15 minutos.');
    } catch (err: any) {
      Alert.alert('Erro', err.message || 'Falha ao adiar tarefa.');
    } finally {
      setActionLoading(false);
    }
  };

  const handleConfirmarConclusao = async () => {
    if (!selectedTask) return;
    try {
      setActionLoading(true);
      await agentApi.concluirTarefa(selectedTask.id, proofText.trim());
      setCompleteModalVisible(false);
      setProofText('');
      carregarDados();
      Alert.alert('Parabéns!', 'Tarefa concluída e registrada no seu Life OS.');
    } catch (err: any) {
      Alert.alert('Erro', err.message || 'Falha ao concluir tarefa.');
    } finally {
      setActionLoading(false);
    }
  };

  if (loading) {
    return (
      <View style={styles.centerContainer}>
        <ActivityIndicator size="large" color="#6366f1" />
        <Text style={styles.loadingText}>Sincronizando com Agent Core...</Text>
      </View>
    );
  }

  const tarefasCriticas = dashboard?.tarefas_criticas_hoje || [];
  const financas = dashboard?.financas;

  return (
    <ScrollView
      style={styles.container}
      contentContainerStyle={styles.content}
      refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor="#6366f1" />}
    >
      {/* Cabeçalho de Status Diário */}
      <View style={styles.header}>
        <Text style={styles.eyebrow}>COCKPIT DIÁRIO · AGENT CORE</Text>
        <Text style={styles.title}>Foco de Hoje</Text>
        <Text style={styles.subtitle}>
          {dashboard?.tarefas_concluidas_hoje || 0} de {dashboard?.tarefas_total_hoje || 0} tarefas concluídas
        </Text>
      </View>

      {/* Teto Diário Rápido */}
      {financas && (
        <View style={[styles.financeCard, financas.estourou && styles.financeCardAlert]}>
          <View>
            <Text style={styles.financeLabel}>TETO DISPONÍVEL HOJE</Text>
            <Text style={[styles.financeValue, financas.estourou && styles.financeValueAlert]}>
              R$ {financas.saldo_restante_hoje.toFixed(2)}
            </Text>
          </View>
          <Text style={styles.financeSpent}>Gastos hoje: R$ {financas.gastos_hoje.toFixed(2)}</Text>
        </View>
      )}

      {/* Barra de Entrada Rápida de Atividades (Inbox Cognitivo) */}
      <View style={styles.quickInputCard}>
        <Text style={styles.quickInputLabel}>⚡ REGISTRO RÁPIDO · O QUE PRECISA FAZER?</Text>
        <View style={styles.quickInputRow}>
          <TextInput
            style={styles.quickInputField}
            placeholder="Ex: Entregar API às 18h sem falta / Estudar React"
            placeholderTextColor="#64748b"
            value={quickInput}
            onChangeText={setQuickInput}
            onSubmitEditing={handleQuickSubmit}
            returnKeyType="send"
          />
          <TouchableOpacity
            style={[styles.quickInputBtn, (!quickInput.trim() || quickSubmitting) && styles.quickInputBtnDisabled]}
            onPress={handleQuickSubmit}
            disabled={!quickInput.trim() || quickSubmitting}
          >
            <Text style={styles.quickInputBtnText}>{quickSubmitting ? '...' : 'Agendar'}</Text>
          </TouchableOpacity>
        </View>
      </View>

      {/* Seção das 3 Tarefas Críticas */}
      <View style={styles.sectionHeader}>
        <Text style={styles.sectionTitle}>AS 3 TAREFAS CRÍTICAS</Text>
        <Text style={styles.sectionBadge}>{tarefasCriticas.length}/3</Text>
      </View>

      {tarefasCriticas.length === 0 ? (
        <View style={styles.emptyCard}>
          <Text style={styles.emptyEmoji}>🎯</Text>
          <Text style={styles.emptyTitle}>Sem tarefas críticas pendentes!</Text>
          <Text style={styles.emptySubtitle}>
            Você cumpriu o foco principal do dia ou ainda não definiu prioridades no chat.
          </Text>
        </View>
      ) : (
        tarefasCriticas.map((tarefa) => {
          const isCritica = tarefa.criticidade === 'critica';
          const atrasada = tarefa.escalation_level > 1;

          return (
            <View
              key={tarefa.id}
              style={[
                styles.taskCard,
                isCritica && styles.taskCardCritica,
                atrasada && styles.taskCardAtrasada
              ]}
            >
              <View style={styles.taskHeader}>
                <View style={styles.badgeRow}>
                  <Text
                    style={[
                      styles.badge,
                      isCritica ? styles.badgeCritica : styles.badgeImportante
                    ]}
                  >
                    {tarefa.criticidade.toUpperCase()}
                  </Text>
                  {tarefa.horario_previsto && (
                    <Text style={styles.timeBadge}>⏰ {tarefa.horario_previsto}</Text>
                  )}
                  {tarefa.postpone_count > 0 && (
                    <Text style={styles.postponeBadge}>
                      {tarefa.postpone_count}x adiada
                    </Text>
                  )}
                </View>

                {tarefa.escalation_level > 0 && (
                  <Text style={styles.escalationBadge}>
                    Nível {tarefa.escalation_level}
                  </Text>
                )}
              </View>

              <Text style={styles.taskTitle}>{tarefa.titulo}</Text>

              {tarefa.descricao ? (
                <Text style={styles.taskDesc}>{tarefa.descricao}</Text>
              ) : null}

              {/* Banner de Micro-Passo para vencer procrastinação */}
              {tarefa.micro_step_sugerido ? (
                <View style={styles.microStepCard}>
                  <Text style={styles.microStepLabel}>⚡ PRIMEIRO PASSO DE 2 MINUTOS:</Text>
                  <Text style={styles.microStepText}>{tarefa.micro_step_sugerido}</Text>
                </View>
              ) : null}

              {/* Botões de Ação */}
              <View style={styles.actionRow}>
                {tarefa.contexto_execucao === 'pc' && (
                  <TouchableOpacity
                    style={[styles.btn, styles.btnPC]}
                    onPress={() => handlePrepararPC(tarefa.id)}
                    disabled={actionLoading}
                  >
                    <Text style={styles.btnText}>💻 Estou indo pro PC</Text>
                  </TouchableOpacity>
                )}

                <TouchableOpacity
                  style={[styles.btn, styles.btnPostpone]}
                  onPress={() => {
                    setSelectedTask(tarefa);
                    setPostponeModalVisible(true);
                  }}
                  disabled={actionLoading}
                >
                  <Text style={styles.btnPostponeText}>⏳ Adiar</Text>
                </TouchableOpacity>

                <TouchableOpacity
                  style={[styles.btn, styles.btnComplete]}
                  onPress={() => {
                    setSelectedTask(tarefa);
                    setCompleteModalVisible(true);
                  }}
                  disabled={actionLoading}
                >
                  <Text style={styles.btnCompleteText}>✓ Concluir</Text>
                </TouchableOpacity>
              </View>
            </View>
          );
        })
      )}

      {/* Modal de Adiamento */}
      <Modal visible={postponeModalVisible} transparent animationType="slide">
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <Text style={styles.modalTitle}>Adiar Tarefa (+15m)</Text>
            <Text style={styles.modalSubtitle}>
              O Agent Core exige uma justificativa real para recalcular a prioridade:
            </Text>
            <TextInput
              style={styles.modalInput}
              placeholder="Ex: Tive um imprevisto / Reunião estendeu..."
              placeholderTextColor="#9ca3af"
              value={postponeReason}
              onChangeText={setPostponeReason}
              multiline
              numberOfLines={3}
            />
            <View style={styles.modalActionRow}>
              <TouchableOpacity
                style={[styles.btn, styles.btnCancel]}
                onPress={() => setPostponeModalVisible(false)}
              >
                <Text style={styles.btnCancelText}>Cancelar</Text>
              </TouchableOpacity>
              <TouchableOpacity
                style={[styles.btn, styles.btnConfirm]}
                onPress={handleConfirmarAdiar}
                disabled={actionLoading}
              >
                <Text style={styles.btnConfirmText}>Confirmar (+15m)</Text>
              </TouchableOpacity>
            </View>
          </View>
        </View>
      </Modal>

      {/* Modal de Conclusão / Proof of Work */}
      <Modal visible={completeModalVisible} transparent animationType="slide">
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <Text style={styles.modalTitle}>Concluir Tarefa</Text>
            <Text style={styles.modalSubtitle}>
              {selectedTask?.proof_of_work_type !== 'click'
                ? 'Esta tarefa crítica requer comprovação do que foi feito:'
                : 'Confirmar conclusão desta tarefa no seu Life OS?'}
            </Text>
            {selectedTask?.proof_of_work_type !== 'click' && (
              <TextInput
                style={styles.modalInput}
                placeholder="Descreva o que foi entregue ou commit realizado..."
                placeholderTextColor="#9ca3af"
                value={proofText}
                onChangeText={setProofText}
                multiline
                numberOfLines={3}
              />
            )}
            <View style={styles.modalActionRow}>
              <TouchableOpacity
                style={[styles.btn, styles.btnCancel]}
                onPress={() => setCompleteModalVisible(false)}
              >
                <Text style={styles.btnCancelText}>Voltar</Text>
              </TouchableOpacity>
              <TouchableOpacity
                style={[styles.btn, styles.btnComplete]}
                onPress={handleConfirmarConclusao}
                disabled={actionLoading}
              >
                <Text style={styles.btnCompleteText}>Confirmar Conclusão</Text>
              </TouchableOpacity>
            </View>
          </View>
        </View>
      </Modal>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#090a0f' },
  content: { padding: 20, paddingBottom: 60 },
  centerContainer: { flex: 1, justifyContent: 'center', alignItems: 'center', backgroundColor: '#090a0f' },
  loadingText: { color: '#94a3b8', marginTop: 12, fontSize: 14 },
  header: { marginBottom: 20 },
  eyebrow: { color: '#6366f1', fontSize: 11, fontWeight: '700', letterSpacing: 1.5, marginBottom: 4 },
  title: { color: '#f8fafc', fontSize: 26, fontWeight: '800' },
  subtitle: { color: '#64748b', fontSize: 14, marginTop: 2 },
  financeCard: {
    backgroundColor: '#13151f',
    borderColor: '#1e2238',
    borderWidth: 1,
    borderRadius: 16,
    padding: 16,
    marginBottom: 24,
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center'
  },
  financeCardAlert: { borderColor: '#ef4444', backgroundColor: '#1c1015' },
  financeLabel: { color: '#94a3b8', fontSize: 10, fontWeight: '700', letterSpacing: 1 },
  financeValue: { color: '#10b981', fontSize: 22, fontWeight: '800', marginTop: 2 },
  financeValueAlert: { color: '#ef4444' },
  financeSpent: { color: '#64748b', fontSize: 12 },
  quickInputCard: {
    backgroundColor: '#121420',
    borderColor: '#4338ca',
    borderWidth: 1,
    borderRadius: 16,
    padding: 14,
    marginBottom: 20
  },
  quickInputLabel: { color: '#818cf8', fontSize: 10, fontWeight: '800', letterSpacing: 0.8, marginBottom: 8 },
  quickInputRow: { flexDirection: 'row', gap: 8, alignItems: 'center' },
  quickInputField: {
    flex: 1,
    backgroundColor: '#0c0e17',
    borderColor: '#1e243d',
    borderWidth: 1,
    borderRadius: 10,
    color: '#f8fafc',
    paddingHorizontal: 12,
    paddingVertical: 10,
    fontSize: 13
  },
  quickInputBtn: {
    backgroundColor: '#4f46e5',
    paddingVertical: 11,
    paddingHorizontal: 14,
    borderRadius: 10,
    alignItems: 'center',
    justifyContent: 'center'
  },
  quickInputBtnDisabled: { backgroundColor: '#312e81', opacity: 0.6 },
  quickInputBtnText: { color: '#ffffff', fontSize: 12, fontWeight: '800' },
  sectionHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 },
  sectionTitle: { color: '#94a3b8', fontSize: 11, fontWeight: '700', letterSpacing: 1.2 },
  sectionBadge: { color: '#6366f1', fontSize: 12, fontWeight: '700' },
  taskCard: {
    backgroundColor: '#121420',
    borderColor: '#1e243d',
    borderWidth: 1,
    borderRadius: 16,
    padding: 16,
    marginBottom: 16
  },
  taskCardCritica: { borderColor: '#f59e0b', backgroundColor: '#141420' },
  taskCardAtrasada: { borderColor: '#ef4444', backgroundColor: '#1c1218' },
  taskHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 },
  badgeRow: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  badge: { fontSize: 10, fontWeight: '700', paddingHorizontal: 8, paddingVertical: 3, borderRadius: 6 },
  badgeCritica: { backgroundColor: '#78350f', color: '#fef3c7' },
  badgeImportante: { backgroundColor: '#1e3a5f', color: '#bae6fd' },
  timeBadge: { color: '#94a3b8', fontSize: 11, marginLeft: 4 },
  postponeBadge: { color: '#f87171', fontSize: 11, fontWeight: '600' },
  escalationBadge: { color: '#ef4444', fontSize: 11, fontWeight: '700' },
  taskTitle: { color: '#f8fafc', fontSize: 17, fontWeight: '700', marginBottom: 6 },
  taskDesc: { color: '#94a3b8', fontSize: 13, lineHeight: 18, marginBottom: 12 },
  microStepCard: {
    backgroundColor: '#1e1b4b',
    borderColor: '#4338ca',
    borderWidth: 1,
    borderRadius: 10,
    padding: 10,
    marginBottom: 14
  },
  microStepLabel: { color: '#a5b4fc', fontSize: 10, fontWeight: '800', letterSpacing: 0.8 },
  microStepText: { color: '#e0e7ff', fontSize: 13, marginTop: 2, fontWeight: '600' },
  actionRow: { flexDirection: 'row', gap: 8, marginTop: 4 },
  btn: { paddingVertical: 10, paddingHorizontal: 12, borderRadius: 10, alignItems: 'center', justifyContent: 'center' },
  btnPC: { backgroundColor: '#312e81', flex: 1.2 },
  btnPostpone: { backgroundColor: '#262626', flex: 1 },
  btnComplete: { backgroundColor: '#059669', flex: 1 },
  btnText: { color: '#c7d2fe', fontSize: 12, fontWeight: '700' },
  btnPostponeText: { color: '#f87171', fontSize: 12, fontWeight: '700' },
  btnCompleteText: { color: '#ecfdf5', fontSize: 12, fontWeight: '700' },
  emptyCard: { backgroundColor: '#121420', borderRadius: 16, padding: 30, alignItems: 'center' },
  emptyEmoji: { fontSize: 40, marginBottom: 12 },
  emptyTitle: { color: '#f8fafc', fontSize: 16, fontWeight: '700', textAlign: 'center' },
  emptySubtitle: { color: '#64748b', fontSize: 13, textAlign: 'center', marginTop: 4 },
  modalOverlay: { flex: 1, backgroundColor: 'rgba(0,0,0,0.7)', justifyContent: 'center', padding: 20 },
  modalContent: { backgroundColor: '#161926', borderRadius: 20, padding: 20, borderWidth: 1, borderColor: '#262c45' },
  modalTitle: { color: '#f8fafc', fontSize: 18, fontWeight: '700' },
  modalSubtitle: { color: '#94a3b8', fontSize: 13, marginTop: 4, marginBottom: 14 },
  modalInput: {
    backgroundColor: '#0c0e17',
    borderColor: '#262c45',
    borderWidth: 1,
    borderRadius: 12,
    color: '#f8fafc',
    padding: 12,
    fontSize: 14,
    textAlignVertical: 'top',
    marginBottom: 16
  },
  modalActionRow: { flexDirection: 'row', justifyContent: 'flex-end', gap: 10 },
  btnCancel: { backgroundColor: '#262626', paddingHorizontal: 16 },
  btnCancelText: { color: '#94a3b8', fontWeight: '600' },
  btnConfirm: { backgroundColor: '#4f46e5', paddingHorizontal: 16 },
  btnConfirmText: { color: '#ffffff', fontWeight: '700' }
});
