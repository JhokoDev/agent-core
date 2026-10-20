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
import { DashboardStatus, TransacaoFinanceira } from '../../src/types';

export default function FinancesScreen() {
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [dashboard, setDashboard] = useState<DashboardStatus | null>(null);
  const [transacoes, setTransacoes] = useState<TransacaoFinanceira[]>([]);

  // Modais de gasto e pedágio
  const [gastoModal, setGastoModal] = useState(false);
  const [pedagioModal, setPedagioModal] = useState(false);
  const [valorGasto, setValorGasto] = useState('');
  const [descricaoGasto, setDescricaoGasto] = useState('');
  const [itemPedagio, setItemPedagio] = useState('');
  const [valorPedagio, setValorPedagio] = useState('');
  const [resultadoPedagio, setResultadoPedagio] = useState<any>(null);
  const [submitting, setSubmitting] = useState(false);

  const carregarDados = useCallback(async () => {
    try {
      const [dash, trans] = await Promise.all([
        agentApi.getDashboardStatus(),
        agentApi.listarFinancas(20)
      ]);
      setDashboard(dash);
      setTransacoes(trans);
    } catch (err: any) {
      console.warn('Falha ao carregar finanças:', err.message);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    carregarDados();
  }, [carregarDados]);

  const onRefresh = () => {
    setRefreshing(true);
    carregarDados();
  };

  const handleSalvarGasto = async () => {
    const val = parseFloat(valorGasto.replace(',', '.'));
    if (isNaN(val) || val <= 0 || !descricaoGasto.trim()) {
      Alert.alert('Aviso', 'Informe um valor válido e a descrição do gasto.');
      return;
    }

    try {
      setSubmitting(true);
      await agentApi.registrarGasto(val, descricaoGasto.trim(), 'alimentacao_lazer');
      setGastoModal(false);
      setValorGasto('');
      setDescricaoGasto('');
      carregarDados();
      Alert.alert('Sucesso', 'Gasto registrado e deduzido do seu teto diário.');
    } catch (err: any) {
      Alert.alert('Erro', err.message || 'Falha ao registrar gasto.');
    } finally {
      setSubmitting(false);
    }
  };

  const handleConsultarPedagio = async () => {
    const val = parseFloat(valorPedagio.replace(',', '.'));
    if (isNaN(val) || val <= 0 || !itemPedagio.trim()) {
      Alert.alert('Aviso', 'Informe o valor e o nome do item a ser consultado.');
      return;
    }

    try {
      setSubmitting(true);
      const res = await agentApi.calcularPedagio(val, itemPedagio.trim());
      setResultadoPedagio(res);
    } catch (err: any) {
      Alert.alert('Erro', err.message || 'Falha ao calcular pedágio.');
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <View style={styles.centerContainer}>
        <ActivityIndicator size="large" color="#10b981" />
        <Text style={styles.loadingText}>Carregando Finanças...</Text>
      </View>
    );
  }

  const fin = dashboard?.financas;

  return (
    <ScrollView
      style={styles.container}
      contentContainerStyle={styles.content}
      refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor="#10b981" />}
    >
      <View style={styles.header}>
        <Text style={styles.eyebrow}>LIFE OS · FINANÇAS ZERO-PLANILHA</Text>
        <Text style={styles.title}>Orçamento Diário</Text>
      </View>

      {/* Cartão de Teto Diário */}
      <View style={[styles.mainCard, fin?.estourou && styles.mainCardAlert]}>
        <Text style={styles.cardEyebrow}>DISPONÍVEL PARA HOJE</Text>
        <Text style={[styles.cardValue, fin?.estourou && styles.cardValueAlert]}>
          R$ {fin?.saldo_restante_hoje.toFixed(2) || '0.00'}
        </Text>
        <Text style={styles.cardFooter}>
          Teto estipulado: R$ {fin?.teto_diario_livre.toFixed(2)} · Gastos hoje: R$ {fin?.gastos_hoje.toFixed(2)}
        </Text>
      </View>

      {/* Botões Rápidos */}
      <View style={styles.actionRow}>
        <TouchableOpacity style={[styles.btn, styles.btnAdd]} onPress={() => setGastoModal(true)}>
          <Text style={styles.btnText}>+ Registrar Gasto</Text>
        </TouchableOpacity>
        <TouchableOpacity style={[styles.btn, styles.btnPedagio]} onPress={() => setPedagioModal(true)}>
          <Text style={styles.btnText}>⚖️ Pedágio de Compra</Text>
        </TouchableOpacity>
      </View>

      {/* Extrato Recente */}
      <View style={styles.sectionHeader}>
        <Text style={styles.sectionTitle}>ÚLTIMAS TRANSAÇÕES (PIX & NOTIFICAÇÕES)</Text>
      </View>

      {transacoes.length === 0 ? (
        <View style={styles.emptyCard}>
          <Text style={styles.emptyText}>Nenhuma despesa recente registrada.</Text>
        </View>
      ) : (
        transacoes.map((t) => (
          <View key={t.id} style={styles.transactionCard}>
            <View style={{ flex: 1 }}>
              <Text style={styles.transTitle}>{t.descricao || t.categoria}</Text>
              <Text style={styles.transSub}>
                {t.origem.replace('_', ' ')} · Custa {t.horas_vida ? t.horas_vida.toFixed(1) : '0'}h de trabalho
              </Text>
            </View>
            <Text style={styles.transValue}>- R$ {t.valor.toFixed(2)}</Text>
          </View>
        ))
      )}

      {/* Modal Registrar Gasto */}
      <Modal visible={gastoModal} transparent animationType="slide">
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <Text style={styles.modalTitle}>Registrar Gasto Rápido</Text>
            <TextInput
              style={styles.modalInput}
              placeholder="Valor em R$ (ex: 25.50)"
              placeholderTextColor="#9ca3af"
              keyboardType="numeric"
              value={valorGasto}
              onChangeText={setValorGasto}
            />
            <TextInput
              style={styles.modalInput}
              placeholder="O que você comprou? (ex: Almoço / Uber)"
              placeholderTextColor="#9ca3af"
              value={descricaoGasto}
              onChangeText={setDescricaoGasto}
            />
            <View style={styles.modalActionRow}>
              <TouchableOpacity style={[styles.btn, styles.btnCancel]} onPress={() => setGastoModal(false)}>
                <Text style={styles.btnCancelText}>Cancelar</Text>
              </TouchableOpacity>
              <TouchableOpacity style={[styles.btn, styles.btnAdd]} onPress={handleSalvarGasto} disabled={submitting}>
                <Text style={styles.btnText}>Salvar Gasto</Text>
              </TouchableOpacity>
            </View>
          </View>
        </View>
      </Modal>

      {/* Modal Pedágio de Compra */}
      <Modal visible={pedagioModal} transparent animationType="slide">
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <Text style={styles.modalTitle}>Pedágio Anti-Impulso</Text>
            <Text style={styles.modalSubtitle}>
              Consulte antes de comprar para ver o custo real em horas da sua vida:
            </Text>
            <TextInput
              style={styles.modalInput}
              placeholder="Nome do item (ex: Fone de Ouvido)"
              placeholderTextColor="#9ca3af"
              value={itemPedagio}
              onChangeText={setItemPedagio}
            />
            <TextInput
              style={styles.modalInput}
              placeholder="Valor em R$ (ex: 200.00)"
              placeholderTextColor="#9ca3af"
              keyboardType="numeric"
              value={valorPedagio}
              onChangeText={setValorPedagio}
            />
            {resultadoPedagio && (
              <View style={styles.pedagioResultCard}>
                <Text style={styles.pedagioVerdict}>{resultadoPedagio.veredito}</Text>
                <Text style={styles.pedagioReason}>{resultadoPedagio.motivo}</Text>
                <Text style={styles.pedagioHours}>
                  Equivale a {resultadoPedagio.horas_trabalho_necessarias?.toFixed(1)} horas de trabalho.
                </Text>
              </View>
            )}
            <View style={styles.modalActionRow}>
              <TouchableOpacity
                style={[styles.btn, styles.btnCancel]}
                onPress={() => {
                  setPedagioModal(false);
                  setResultadoPedagio(null);
                }}
              >
                <Text style={styles.btnCancelText}>Fechar</Text>
              </TouchableOpacity>
              <TouchableOpacity style={[styles.btn, styles.btnPedagio]} onPress={handleConsultarPedagio} disabled={submitting}>
                <Text style={styles.btnText}>Avaliar Compra</Text>
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
  eyebrow: { color: '#10b981', fontSize: 11, fontWeight: '700', letterSpacing: 1.5, marginBottom: 4 },
  title: { color: '#f8fafc', fontSize: 26, fontWeight: '800' },
  mainCard: {
    backgroundColor: '#101c18',
    borderColor: '#064e3b',
    borderWidth: 1,
    borderRadius: 20,
    padding: 20,
    marginBottom: 20
  },
  mainCardAlert: { borderColor: '#ef4444', backgroundColor: '#201015' },
  cardEyebrow: { color: '#6ee7b7', fontSize: 11, fontWeight: '800', letterSpacing: 1.2 },
  cardValue: { color: '#10b981', fontSize: 34, fontWeight: '900', marginVertical: 6 },
  cardValueAlert: { color: '#ef4444' },
  cardFooter: { color: '#94a3b8', fontSize: 12 },
  actionRow: { flexDirection: 'row', gap: 10, marginBottom: 28 },
  btn: { paddingVertical: 12, paddingHorizontal: 16, borderRadius: 12, alignItems: 'center', justifyContent: 'center' },
  btnAdd: { backgroundColor: '#059669', flex: 1 },
  btnPedagio: { backgroundColor: '#4338ca', flex: 1 },
  btnText: { color: '#ffffff', fontSize: 13, fontWeight: '700' },
  sectionHeader: { marginBottom: 12 },
  sectionTitle: { color: '#94a3b8', fontSize: 11, fontWeight: '700', letterSpacing: 1.2 },
  emptyCard: { backgroundColor: '#13151f', borderRadius: 14, padding: 20, alignItems: 'center' },
  emptyText: { color: '#64748b', fontSize: 13 },
  transactionCard: {
    backgroundColor: '#121420',
    borderColor: '#1e243d',
    borderWidth: 1,
    borderRadius: 14,
    padding: 14,
    marginBottom: 10,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between'
  },
  transTitle: { color: '#f8fafc', fontSize: 15, fontWeight: '700' },
  transSub: { color: '#64748b', fontSize: 12, marginTop: 2 },
  transValue: { color: '#f87171', fontSize: 16, fontWeight: '800' },
  modalOverlay: { flex: 1, backgroundColor: 'rgba(0,0,0,0.7)', justifyContent: 'center', padding: 20 },
  modalContent: { backgroundColor: '#161926', borderRadius: 20, padding: 20, borderWidth: 1, borderColor: '#262c45' },
  modalTitle: { color: '#f8fafc', fontSize: 18, fontWeight: '700', marginBottom: 12 },
  modalSubtitle: { color: '#94a3b8', fontSize: 13, marginBottom: 14 },
  modalInput: {
    backgroundColor: '#0c0e17',
    borderColor: '#262c45',
    borderWidth: 1,
    borderRadius: 12,
    color: '#f8fafc',
    padding: 12,
    fontSize: 14,
    marginBottom: 12
  },
  modalActionRow: { flexDirection: 'row', justifyContent: 'flex-end', gap: 10, marginTop: 8 },
  btnCancel: { backgroundColor: '#262626', paddingHorizontal: 16 },
  btnCancelText: { color: '#94a3b8', fontWeight: '600' },
  pedagioResultCard: {
    backgroundColor: '#1e1b4b',
    borderColor: '#4338ca',
    borderWidth: 1,
    borderRadius: 12,
    padding: 12,
    marginVertical: 10
  },
  pedagioVerdict: { color: '#a5b4fc', fontSize: 14, fontWeight: '800' },
  pedagioReason: { color: '#e0e7ff', fontSize: 13, marginTop: 4 },
  pedagioHours: { color: '#38bdf8', fontSize: 12, marginTop: 6, fontWeight: '700' }
});
