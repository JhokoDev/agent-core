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
import { SafeAreaView } from 'react-native-safe-area-context';
import { agentApi } from '../../src/services/api';
import {
  DashboardStatus,
  TransacaoFinanceira,
  SaldoCaixasResponse,
  CategoriaCaixa
} from '../../src/types';

function getCategoriaLabel(cat: string): string {
  switch (cat) {
    case 'apenas_recebimento':
      return 'Apenas Recebimento';
    case 'custos_fixos':
      return 'Custos Fixos';
    case 'construcao_futuro':
      return 'Reserva & Metas';
    case 'autoaperfeicoamento':
      return 'Estudos & Dev';
    case 'livre_lazer':
      return 'Livre / Lazer';
    default:
      return cat;
  }
}

export default function FinancesScreen() {
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [dashboard, setDashboard] = useState<DashboardStatus | null>(null);
  const [transacoes, setTransacoes] = useState<TransacaoFinanceira[]>([]);
  const [saldoCaixas, setSaldoCaixas] = useState<SaldoCaixasResponse | null>(null);

  // Modal de Transação (Receita ou Despesa)
  const [transacaoModalVisible, setTransacaoModalVisible] = useState(false);
  const [tipoTransacao, setTipoTransacao] = useState<'receita' | 'despesa'>('despesa');
  const [valorTransacao, setValorTransacao] = useState('');
  const [descricaoTransacao, setDescricaoTransacao] = useState('');
  const [categoriaTransacao, setCategoriaTransacao] = useState<CategoriaCaixa>('livre_lazer');
  const [campoMa, setCampoMa] = useState('');

  // Modal de Pedágio
  const [pedagioModal, setPedagioModal] = useState(false);
  const [itemPedagio, setItemPedagio] = useState('');
  const [valorPedagio, setValorPedagio] = useState('');
  const [resultadoPedagio, setResultadoPedagio] = useState<any>(null);
  const [submitting, setSubmitting] = useState(false);

  const carregarDados = useCallback(async () => {
    try {
      const [dash, trans, caixas] = await Promise.all([
        agentApi.getDashboardStatus(),
        agentApi.listarFinancas(50),
        agentApi.obterSaldoCaixas()
      ]);
      setDashboard(dash);
      setTransacoes(trans);
      setSaldoCaixas(caixas);
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

  const abrirModalTransacao = (tipo: 'receita' | 'despesa') => {
    setTipoTransacao(tipo);
    setCategoriaTransacao(tipo === 'receita' ? 'apenas_recebimento' : 'livre_lazer');
    setValorTransacao('');
    setDescricaoTransacao('');
    setCampoMa('');
    setTransacaoModalVisible(true);
  };

  const handleSalvarTransacao = async () => {
    const val = parseFloat(valorTransacao.replace(',', '.'));
    if (isNaN(val) || val <= 0 || !descricaoTransacao.trim()) {
      Alert.alert('Aviso', 'Informe um valor válido e a descrição da transação.');
      return;
    }

    try {
      setSubmitting(true);
      await agentApi.registrarTransacao(
        tipoTransacao,
        val,
        descricaoTransacao.trim(),
        categoriaTransacao,
        campoMa.trim()
      );
      setTransacaoModalVisible(false);
      setValorTransacao('');
      setDescricaoTransacao('');
      setCampoMa('');
      carregarDados();
      Alert.alert(
        'Sucesso!',
        tipoTransacao === 'receita'
          ? `Entrada de R$ ${val.toFixed(2)} adicionada ao seu fluxo financeiro!`
          : `Gasto de R$ ${val.toFixed(2)} registrado e alocado na caixa correspondente.`
      );
    } catch (err: any) {
      Alert.alert('Erro', err.message || 'Falha ao registrar transação.');
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
        <Text style={styles.loadingText}>Carregando Inteligência Financeira...</Text>
      </View>
    );
  }

  // Cálculos de Fluxo Total
  let totalEntradas = 0;
  let totalSaidas = 0;

  if (saldoCaixas?.caixas) {
    Object.values(saldoCaixas.caixas).forEach((c) => {
      totalEntradas += c.receitas || 0;
      totalSaidas += c.despesas || 0;
    });
  }

  const volumeTotalMovimentado = totalEntradas + totalSaidas;
  const saldoLiquidoGeral = totalEntradas - totalSaidas;

  const tetoLivreHoje = saldoCaixas?.saldo_diario_restante ?? (dashboard?.financas?.saldo_restante_hoje || 0);
  const gastosHoje = saldoCaixas?.gastos_hoje ?? (dashboard?.financas?.gastos_hoje || 0);
  const tetoEstipulado = saldoCaixas?.teto_diario_livre ?? (dashboard?.financas?.teto_diario_livre || 50);

  const saldoLazerCaixa = saldoCaixas?.caixas?.livre_lazer?.saldo || 0;
  const saldoReservaMetas = saldoCaixas?.caixas?.construcao_futuro?.saldo || 0;

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: '#090a0f' }} edges={['top']}>
      <ScrollView
        style={styles.container}
        contentContainerStyle={styles.content}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor="#10b981" />}
      >
      {/* Cabeçalho */}
      <View style={styles.header}>
        <Text style={styles.eyebrow}>CONTROLE DE PATRIMÔNIO · LIFE OS</Text>
        <Text style={styles.title}>Inteligência Financeira</Text>
        <Text style={styles.subtitle}>Visão completa de fluxo, metas e limites reais de gastos</Text>
      </View>

      {/* 1. DINHEIRO QUE PASSOU NA MÃO (FLUXO TOTAL) */}
      <View style={styles.flowCard}>
        <Text style={styles.cardEyebrow}>VOLUME TOTAL MOVIMENTADO</Text>
        <Text style={styles.flowValue}>R$ {volumeTotalMovimentado.toFixed(2)}</Text>
        <Text style={styles.flowSubtext}>Total de dinheiro que entrou ou saiu da sua mão</Text>

        <View style={styles.flowRow}>
          <View style={styles.flowCol}>
            <Text style={styles.flowColLabel}>🟢 TOTAL GANHO</Text>
            <Text style={[styles.flowColValue, { color: '#34d399' }]}>+ R$ {totalEntradas.toFixed(2)}</Text>
          </View>
          <View style={styles.flowDivider} />
          <View style={styles.flowCol}>
            <Text style={styles.flowColLabel}>🔴 TOTAL GASTO</Text>
            <Text style={[styles.flowColValue, { color: '#f87171' }]}>- R$ {totalSaidas.toFixed(2)}</Text>
          </View>
          <View style={styles.flowDivider} />
          <View style={styles.flowCol}>
            <Text style={styles.flowColLabel}>💳 SALDO REAL</Text>
            <Text style={[styles.flowColValue, { color: saldoLiquidoGeral >= 0 ? '#38bdf8' : '#fb7185' }]}>
              R$ {saldoLiquidoGeral.toFixed(2)}
            </Text>
          </View>
        </View>
      </View>

      {/* 2. QUANTO POSSO GASTAR? (LEVANDO EM CONTA METAS & TETO) */}
      <View style={[styles.allowanceCard, tetoLivreHoje < 0 && styles.allowanceCardAlert]}>
        <View style={styles.allowanceHeader}>
          <Text style={{ fontSize: 24 }}>🎯</Text>
          <View style={{ flex: 1, marginLeft: 10 }}>
            <Text style={styles.allowanceTitle}>Quanto posso gastar hoje?</Text>
            <Text style={styles.allowanceSub}>Calculado protegendo suas metas e custos fixos</Text>
          </View>
        </View>

        <View style={styles.allowanceValuesRow}>
          <View>
            <Text style={styles.allowanceLabel}>DISPONÍVEL HOJE</Text>
            <Text style={[styles.allowanceBigNumber, tetoLivreHoje < 0 && { color: '#ef4444' }]}>
              R$ {tetoLivreHoje.toFixed(2)}
            </Text>
          </View>
          <View style={{ alignItems: 'flex-end' }}>
            <Text style={styles.allowanceLabel}>TETO BASE DIÁRIO</Text>
            <Text style={styles.allowanceSmallNumber}>R$ {tetoEstipulado.toFixed(2)}</Text>
            <Text style={styles.allowanceSpent}>Já gastou hoje: R$ {gastosHoje.toFixed(2)}</Text>
          </View>
        </View>

        <View style={styles.metasProtectionBanner}>
          <Text style={styles.metasProtectionText}>
            🛡️ <Text style={{ fontWeight: '700', color: '#10b981' }}>R$ {saldoReservaMetas.toFixed(2)}</Text> guardados na Reserva/Metas e blindados contra compras por impulso.
          </Text>
        </View>
      </View>

      {/* BOTÕES DE AÇÃO RÁPIDA */}
      <View style={styles.actionGrid}>
        <TouchableOpacity style={[styles.actionBtn, styles.btnIncome]} onPress={() => abrirModalTransacao('receita')}>
          <Text style={styles.actionBtnIcon}>💰</Text>
          <Text style={styles.actionBtnText}>+ Ganhei (Receita)</Text>
        </TouchableOpacity>

        <TouchableOpacity style={[styles.actionBtn, styles.btnExpense]} onPress={() => abrirModalTransacao('despesa')}>
          <Text style={styles.actionBtnIcon}>💸</Text>
          <Text style={styles.actionBtnText}>- Gastei (Despesa)</Text>
        </TouchableOpacity>

        <TouchableOpacity style={[styles.actionBtn, styles.btnPedagio]} onPress={() => setPedagioModal(true)}>
          <Text style={styles.actionBtnIcon}>⚖️</Text>
          <Text style={styles.actionBtnText}>Pedágio de Compra</Text>
        </TouchableOpacity>
      </View>

      {/* 3. AS 4 CAIXAS DO LIFE OS */}
      <View style={styles.sectionHeader}>
        <Text style={styles.sectionTitle}>AS 4 CAIXAS FINANCEIRAS DO LIFE OS</Text>
      </View>

      <View style={styles.boxesGrid}>
        {/* Caixa 1: Custos Fixos */}
        <View style={styles.boxCard}>
          <View style={styles.boxHeader}>
            <Text style={{ fontSize: 18 }}>🏢</Text>
            <Text style={styles.boxName}>Custos Fixos</Text>
          </View>
          <Text style={styles.boxSaldo}>
            R$ {(saldoCaixas?.caixas?.custos_fixos?.saldo || 0).toFixed(2)}
          </Text>
          <Text style={styles.boxDesc}>Aluguel, contas essenciais e luz</Text>
        </View>

        {/* Caixa 2: Construção de Futuro */}
        <View style={[styles.boxCard, { borderColor: '#059669' }]}>
          <View style={styles.boxHeader}>
            <Text style={{ fontSize: 18 }}>🚀</Text>
            <Text style={[styles.boxName, { color: '#34d399' }]}>Reserva & Metas</Text>
          </View>
          <Text style={[styles.boxSaldo, { color: '#34d399' }]}>
            R$ {(saldoCaixas?.caixas?.construcao_futuro?.saldo || 0).toFixed(2)}
          </Text>
          <Text style={styles.boxDesc}>Patrimônio e metas de longo prazo</Text>
        </View>

        {/* Caixa 3: Autoaperfeiçoamento */}
        <View style={styles.boxCard}>
          <View style={styles.boxHeader}>
            <Text style={{ fontSize: 18 }}>📚</Text>
            <Text style={styles.boxName}>Estudos & Dev</Text>
          </View>
          <Text style={styles.boxSaldo}>
            R$ {(saldoCaixas?.caixas?.autoaperfeicoamento?.saldo || 0).toFixed(2)}
          </Text>
          <Text style={styles.boxDesc}>Cursos, livros e ferramentas</Text>
        </View>

        {/* Caixa 4: Livre / Lazer */}
        <View style={[styles.boxCard, { borderColor: '#4f46e5' }]}>
          <View style={styles.boxHeader}>
            <Text style={{ fontSize: 18 }}>🍕</Text>
            <Text style={[styles.boxName, { color: '#818cf8' }]}>Livre / Lazer</Text>
          </View>
          <Text style={[styles.boxSaldo, { color: '#818cf8' }]}>
            R$ {(saldoCaixas?.caixas?.livre_lazer?.saldo || 0).toFixed(2)}
          </Text>
          <Text style={styles.boxDesc}>Para gastar livre sem peso na consciência</Text>
        </View>

        {/* Caixa Adicional: Apenas Recebimento (se houver recebimentos registrados) */}
        {((saldoCaixas?.caixas?.apenas_recebimento?.saldo || 0) > 0 || (saldoCaixas?.caixas?.apenas_recebimento?.receitas || 0) > 0) && (
          <View style={[styles.boxCard, { width: '100%', borderColor: '#10b981', marginTop: 8 }]}>
            <View style={styles.boxHeader}>
              <Text style={{ fontSize: 18 }}>💵</Text>
              <Text style={[styles.boxName, { color: '#34d399' }]}>Apenas Recebimento</Text>
            </View>
            <Text style={[styles.boxSaldo, { color: '#34d399' }]}>
              R$ {(saldoCaixas?.caixas?.apenas_recebimento?.saldo || 0).toFixed(2)}
            </Text>
            <Text style={styles.boxDesc}>Entradas financeiras registradas diretamente no fluxo</Text>
          </View>
        )}
      </View>

      {/* 4. EXTRATO HISTÓRICO DE TRANSAÇÕES */}
      <View style={styles.sectionHeader}>
        <Text style={styles.sectionTitle}>HISTÓRICO DE TRANSAÇÕES</Text>
      </View>

      {transacoes.length === 0 ? (
        <View style={styles.emptyCard}>
          <Text style={styles.emptyText}>Nenhuma transação registrada ainda.</Text>
        </View>
      ) : (
        transacoes.map((t) => {
          const isReceita = t.tipo === 'receita';
          const isMulta = t.tipo === 'multa_procrastinacao';
          return (
            <View key={t.id} style={styles.transactionCard}>
              <View style={styles.transIconCol}>
                <Text style={{ fontSize: 20 }}>
                  {isReceita ? '💰' : isMulta ? '⚠️' : '💸'}
                </Text>
              </View>
              <View style={{ flex: 1, marginLeft: 10 }}>
                <View style={{ flexDirection: 'row', alignItems: 'center', flexWrap: 'wrap', gap: 6 }}>
                  <Text style={styles.transTitle}>{t.descricao || getCategoriaLabel(t.categoria)}</Text>
                  {!!t.ma && (
                    <View style={styles.maBadge}>
                      <Text style={styles.maBadgeText}>ma: {t.ma}</Text>
                    </View>
                  )}
                </View>
                <Text style={styles.transSub}>
                  {t.data_hora.substring(0, 10)} · {getCategoriaLabel(t.categoria)} · {t.origem.replace('_', ' ')}
                  {!isReceita && t.horas_vida ? ` · Custa ${t.horas_vida.toFixed(1)}h de foco` : ''}
                </Text>
              </View>
              <Text
                style={[
                  styles.transValue,
                  isReceita && { color: '#34d399' },
                  isMulta && { color: '#fbbf24' }
                ]}
              >
                {isReceita ? '+' : '-'} R$ {t.valor.toFixed(2)}
              </Text>
            </View>
          );
        })
      )}

      {/* MODAL REGISTRAR TRANSAÇÃO (ENTRADA OU SAÍDA) */}
      <Modal visible={transacaoModalVisible} transparent animationType="slide">
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            {/* Seletor de Tipo no Topo do Modal */}
            <View style={styles.modalTypeSelector}>
              <TouchableOpacity
                style={[styles.modalTypeBtn, tipoTransacao === 'receita' && styles.modalTypeBtnActiveIncome]}
                onPress={() => {
                  setTipoTransacao('receita');
                  setCategoriaTransacao('apenas_recebimento');
                }}
              >
                <Text style={[styles.modalTypeBtnText, tipoTransacao === 'receita' && { color: '#10b981' }]}>
                  🟢 Ganhei (Entrada)
                </Text>
              </TouchableOpacity>

              <TouchableOpacity
                style={[styles.modalTypeBtn, tipoTransacao === 'despesa' && styles.modalTypeBtnActiveExpense]}
                onPress={() => {
                  setTipoTransacao('despesa');
                  setCategoriaTransacao('livre_lazer');
                }}
              >
                <Text style={[styles.modalTypeBtnText, tipoTransacao === 'despesa' && { color: '#ef4444' }]}>
                  🔴 Gastei (Saída)
                </Text>
              </TouchableOpacity>
            </View>

            <Text style={styles.modalTitle}>
              {tipoTransacao === 'receita' ? 'Registrar Ganho / Receita' : 'Registrar Gasto / Despesa'}
            </Text>

            <TextInput
              style={styles.modalInput}
              placeholder="Valor em R$ (ex: 150.00)"
              placeholderTextColor="#64748b"
              keyboardType="numeric"
              value={valorTransacao}
              onChangeText={setValorTransacao}
            />

            <TextInput
              style={styles.modalInput}
              placeholder={tipoTransacao === 'receita' ? 'Origem do ganho (ex: Freela, Salário)' : 'Descrição do gasto (ex: Almoço, Uber)'}
              placeholderTextColor="#64748b"
              value={descricaoTransacao}
              onChangeText={setDescricaoTransacao}
            />

            <TextInput
              style={styles.modalInput}
              placeholder="Campo 'ma' (opcional)"
              placeholderTextColor="#64748b"
              value={campoMa}
              onChangeText={setCampoMa}
              autoCapitalize="none"
            />

            {/* Seletor de Caixa de Destino */}
            <Text style={styles.inputLabel}>
              {tipoTransacao === 'receita' ? 'CATEGORIA DO RECEBIMENTO:' : 'ALOCAR NA CAIXA:'}
            </Text>
            <View style={[styles.categoryPickerRow, { flexWrap: 'wrap', gap: 6 }]}>
              {(tipoTransacao === 'receita'
                ? [
                    { id: 'apenas_recebimento', label: '💵 Apenas Recebimento' },
                    { id: 'construcao_futuro', label: '🚀 Reserva' },
                    { id: 'custos_fixos', label: '🏢 Fixos' },
                    { id: 'autoaperfeicoamento', label: '📚 Estudos' },
                    { id: 'livre_lazer', label: '🍕 Lazer' }
                  ]
                : [
                    { id: 'livre_lazer', label: '🍕 Lazer' },
                    { id: 'custos_fixos', label: '🏢 Fixos' },
                    { id: 'construcao_futuro', label: '🚀 Reserva' },
                    { id: 'autoaperfeicoamento', label: '📚 Estudos' }
                  ]
              ).map((cat) => (
                <TouchableOpacity
                  key={cat.id}
                  style={[
                    styles.categoryChip,
                    categoriaTransacao === cat.id && styles.categoryChipActive,
                    tipoTransacao === 'receita' && { minWidth: '45%', flexGrow: 1 }
                  ]}
                  onPress={() => setCategoriaTransacao(cat.id as CategoriaCaixa)}
                >
                  <Text
                    style={[
                      styles.categoryChipText,
                      categoriaTransacao === cat.id && styles.categoryChipTextActive
                    ]}
                  >
                    {cat.label}
                  </Text>
                </TouchableOpacity>
              ))}
            </View>

            <View style={styles.modalActionRow}>
              <TouchableOpacity
                style={[styles.btn, styles.btnCancel]}
                onPress={() => setTransacaoModalVisible(false)}
              >
                <Text style={styles.btnCancelText}>Cancelar</Text>
              </TouchableOpacity>
              <TouchableOpacity
                style={[
                  styles.btn,
                  tipoTransacao === 'receita' ? styles.btnIncomeConfirm : styles.btnExpenseConfirm
                ]}
                onPress={handleSalvarTransacao}
                disabled={submitting}
              >
                <Text style={styles.btnText}>
                  {submitting ? 'Salvando...' : tipoTransacao === 'receita' ? 'Salvar Ganho' : 'Salvar Gasto'}
                </Text>
              </TouchableOpacity>
            </View>
          </View>
        </View>
      </Modal>

      {/* MODAL PEDÁGIO DE COMPRA */}
      <Modal visible={pedagioModal} transparent animationType="slide">
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <Text style={styles.modalTitle}>Pedágio Anti-Impulso</Text>
            <Text style={styles.modalSubtitle}>
              Mede quantas horas de vida e quantos dias de teto aquela compra vai consumir antes de pagar:
            </Text>
            <TextInput
              style={styles.modalInput}
              placeholder="Nome do item (ex: Tênis novo)"
              placeholderTextColor="#64748b"
              value={itemPedagio}
              onChangeText={setItemPedagio}
            />
            <TextInput
              style={styles.modalInput}
              placeholder="Valor em R$ (ex: 299.90)"
              placeholderTextColor="#64748b"
              keyboardType="numeric"
              value={valorPedagio}
              onChangeText={setValorPedagio}
            />
            {resultadoPedagio && (
              <View style={styles.pedagioResultCard}>
                <Text style={styles.pedagioConselho}>{resultadoPedagio.conselho}</Text>
                <Text style={styles.pedagioHours}>
                  ⏱️ Custa {resultadoPedagio.horas_trabalho}h de foco ({resultadoPedagio.dias_trabalho} dias úteis de trabalho).
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
              <TouchableOpacity style={[styles.btn, styles.btnPedagioAction]} onPress={handleConsultarPedagio} disabled={submitting}>
                <Text style={styles.btnText}>Calcular Pedágio</Text>
              </TouchableOpacity>
            </View>
          </View>
        </View>
      </Modal>
    </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#090a0f' },
  content: { padding: 16, paddingBottom: 60 },
  centerContainer: { flex: 1, justifyContent: 'center', alignItems: 'center', backgroundColor: '#090a0f' },
  loadingText: { color: '#94a3b8', marginTop: 12, fontSize: 14 },

  header: { marginBottom: 18 },
  eyebrow: { color: '#10b981', fontSize: 11, fontWeight: '800', letterSpacing: 1.2 },
  title: { color: '#f8fafc', fontSize: 26, fontWeight: '900', marginTop: 4 },
  subtitle: { color: '#94a3b8', fontSize: 13, marginTop: 4 },

  // Cartão de Fluxo Total
  flowCard: {
    backgroundColor: '#0f172a',
    borderRadius: 16,
    padding: 18,
    borderWidth: 1,
    borderColor: '#1e293b',
    marginBottom: 16
  },
  cardEyebrow: { color: '#64748b', fontSize: 11, fontWeight: '800', letterSpacing: 1 },
  flowValue: { color: '#f8fafc', fontSize: 32, fontWeight: '900', marginTop: 4 },
  flowSubtext: { color: '#94a3b8', fontSize: 12, marginTop: 2, marginBottom: 16 },
  flowRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingTop: 12,
    borderTopWidth: 1,
    borderTopColor: '#1e293b'
  },
  flowCol: { flex: 1, alignItems: 'center' },
  flowDivider: { width: 1, backgroundColor: '#1e293b', height: '80%', alignSelf: 'center' },
  flowColLabel: { color: '#64748b', fontSize: 10, fontWeight: '700' },
  flowColValue: { fontSize: 14, fontWeight: '800', marginTop: 4 },

  // Cartão Quanto Posso Gastar
  allowanceCard: {
    backgroundColor: '#0f172a',
    borderRadius: 16,
    padding: 18,
    borderWidth: 1,
    borderColor: '#10b981',
    marginBottom: 16
  },
  allowanceCardAlert: { borderColor: '#ef4444' },
  allowanceHeader: { flexDirection: 'row', alignItems: 'center', marginBottom: 12 },
  allowanceTitle: { color: '#f8fafc', fontSize: 16, fontWeight: '800' },
  allowanceSub: { color: '#94a3b8', fontSize: 12 },
  allowanceValuesRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-end',
    marginBottom: 12
  },
  allowanceLabel: { color: '#64748b', fontSize: 10, fontWeight: '800', letterSpacing: 0.5 },
  allowanceBigNumber: { color: '#10b981', fontSize: 28, fontWeight: '900', marginTop: 2 },
  allowanceSmallNumber: { color: '#f8fafc', fontSize: 15, fontWeight: '700', marginTop: 2 },
  allowanceSpent: { color: '#94a3b8', fontSize: 11, marginTop: 2 },
  metasProtectionBanner: {
    backgroundColor: 'rgba(16, 185, 129, 0.08)',
    borderRadius: 8,
    padding: 10,
    borderWidth: 1,
    borderColor: 'rgba(16, 185, 129, 0.2)'
  },
  metasProtectionText: { color: '#cbd5e1', fontSize: 12 },

  // Botões de Ação
  actionGrid: { flexDirection: 'row', justifyContent: 'space-between', marginBottom: 20 },
  actionBtn: {
    flex: 1,
    borderRadius: 12,
    paddingVertical: 12,
    paddingHorizontal: 8,
    alignItems: 'center',
    marginHorizontal: 3
  },
  btnIncome: { backgroundColor: '#064e3b', borderWidth: 1, borderColor: '#059669' },
  btnExpense: { backgroundColor: '#450a0a', borderWidth: 1, borderColor: '#dc2626' },
  btnPedagio: { backgroundColor: '#1e1b4b', borderWidth: 1, borderColor: '#4f46e5' },
  actionBtnIcon: { fontSize: 20, marginBottom: 4 },
  actionBtnText: { color: '#f8fafc', fontSize: 11, fontWeight: '700', textAlign: 'center' },

  // As 4 Caixas
  sectionHeader: { marginBottom: 12, marginTop: 6 },
  sectionTitle: { color: '#94a3b8', fontSize: 11, fontWeight: '800', letterSpacing: 1 },
  boxesGrid: { flexDirection: 'row', flexWrap: 'wrap', justifyContent: 'space-between', marginBottom: 20 },
  boxCard: {
    width: '48%',
    backgroundColor: '#0f172a',
    borderRadius: 12,
    padding: 14,
    borderWidth: 1,
    borderColor: '#1e293b',
    marginBottom: 10
  },
  boxHeader: { flexDirection: 'row', alignItems: 'center', marginBottom: 6 },
  boxName: { color: '#f8fafc', fontSize: 13, fontWeight: '700', marginLeft: 6 },
  boxSaldo: { color: '#f8fafc', fontSize: 18, fontWeight: '900', marginBottom: 4 },
  boxDesc: { color: '#64748b', fontSize: 11, lineHeight: 14 },

  // Extrato
  emptyCard: { backgroundColor: '#0f172a', borderRadius: 12, padding: 24, alignItems: 'center' },
  emptyText: { color: '#64748b', fontSize: 13 },
  transactionCard: {
    backgroundColor: '#0f172a',
    borderRadius: 12,
    padding: 14,
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 8,
    borderWidth: 1,
    borderColor: '#1e293b'
  },
  transIconCol: {
    width: 38,
    height: 38,
    borderRadius: 10,
    backgroundColor: '#1e293b',
    justifyContent: 'center',
    alignItems: 'center'
  },
  transTitle: { color: '#f8fafc', fontSize: 14, fontWeight: '700' },
  transSub: { color: '#64748b', fontSize: 11, marginTop: 2 },
  transValue: { color: '#ef4444', fontSize: 15, fontWeight: '800' },

  // Modais
  modalOverlay: { flex: 1, backgroundColor: 'rgba(0,0,0,0.85)', justifyContent: 'flex-end' },
  modalContent: {
    backgroundColor: '#0f172a',
    borderTopLeftRadius: 24,
    borderTopRightRadius: 24,
    padding: 20,
    borderTopWidth: 1,
    borderTopColor: '#1e293b'
  },
  modalTypeSelector: {
    flexDirection: 'row',
    backgroundColor: '#1e293b',
    borderRadius: 10,
    padding: 3,
    marginBottom: 16
  },
  modalTypeBtn: { flex: 1, paddingVertical: 10, alignItems: 'center', borderRadius: 8 },
  modalTypeBtnActiveIncome: { backgroundColor: '#064e3b' },
  modalTypeBtnActiveExpense: { backgroundColor: '#450a0a' },
  modalTypeBtnText: { color: '#94a3b8', fontSize: 13, fontWeight: '700' },
  modalTitle: { color: '#f8fafc', fontSize: 18, fontWeight: '800', marginBottom: 14 },
  modalSubtitle: { color: '#94a3b8', fontSize: 13, marginBottom: 14 },
  modalInput: {
    backgroundColor: '#1e293b',
    borderRadius: 10,
    paddingHorizontal: 14,
    paddingVertical: 12,
    color: '#f8fafc',
    fontSize: 15,
    marginBottom: 12
  },
  inputLabel: { color: '#64748b', fontSize: 11, fontWeight: '800', marginBottom: 8, marginTop: 4 },
  categoryPickerRow: { flexDirection: 'row', justifyContent: 'space-between', marginBottom: 18 },
  categoryChip: {
    flex: 1,
    backgroundColor: '#1e293b',
    borderRadius: 8,
    paddingVertical: 8,
    alignItems: 'center',
    marginHorizontal: 2
  },
  categoryChipActive: { backgroundColor: '#3b82f6' },
  categoryChipText: { color: '#94a3b8', fontSize: 11, fontWeight: '600' },
  categoryChipTextActive: { color: '#ffffff', fontWeight: '800' },
  modalActionRow: { flexDirection: 'row', justifyContent: 'space-between' },
  btn: { flex: 1, paddingVertical: 14, borderRadius: 10, alignItems: 'center' },
  btnCancel: { backgroundColor: '#1e293b', marginRight: 10 },
  btnCancelText: { color: '#94a3b8', fontSize: 14, fontWeight: '700' },
  btnIncomeConfirm: { backgroundColor: '#059669' },
  btnExpenseConfirm: { backgroundColor: '#dc2626' },
  btnPedagioAction: { backgroundColor: '#4f46e5' },
  btnText: { color: '#ffffff', fontSize: 14, fontWeight: '800' },

  pedagioResultCard: {
    backgroundColor: '#1e1b4b',
    borderRadius: 10,
    padding: 14,
    marginBottom: 14,
    borderWidth: 1,
    borderColor: '#4f46e5'
  },
  pedagioConselho: { color: '#f8fafc', fontSize: 13, lineHeight: 18 },
  pedagioHours: { color: '#a5b4fc', fontSize: 12, fontWeight: '700', marginTop: 8 },

  maBadge: {
    backgroundColor: '#3b82f6',
    paddingHorizontal: 6,
    paddingVertical: 1,
    borderRadius: 4
  },
  maBadgeText: {
    color: '#ffffff',
    fontSize: 10,
    fontWeight: '800'
  }
});
