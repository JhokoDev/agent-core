import React, { useState, useEffect, useCallback } from 'react';
import {
  StyleSheet,
  Text,
  View,
  ScrollView,
  TouchableOpacity,
  ActivityIndicator,
  RefreshControl,
  Alert
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { agentApi } from '../../src/services/api';
import { Meta, Habito } from '../../src/types';

export default function LifeOSScreen() {
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [metas, setMetas] = useState<Meta[]>([]);
  const [habitos, setHabitos] = useState<Habito[]>([]);
  const [checkingIn, setCheckingIn] = useState<number | null>(null);

  const carregarDados = useCallback(async () => {
    try {
      const [metasRes, habitosRes] = await Promise.all([
        agentApi.listarMetas(),
        agentApi.listarHabitos()
      ]);
      setMetas(metasRes);
      setHabitos(habitosRes);
    } catch (err: any) {
      console.warn('Falha ao carregar Metas e Hábitos:', err.message);
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

  const handleCheckin = async (habitoId: number) => {
    try {
      setCheckingIn(habitoId);
      await agentApi.checkinHabito(habitoId);
      carregarDados();
      Alert.alert('Boa!', 'Check-in registrado e streak atualizado.');
    } catch (err: any) {
      Alert.alert('Erro', err.message || 'Falha ao registrar check-in.');
    } finally {
      setCheckingIn(null);
    }
  };

  if (loading) {
    return (
      <View style={styles.centerContainer}>
        <ActivityIndicator size="large" color="#f59e0b" />
        <Text style={styles.loadingText}>Carregando Metas e Hábitos...</Text>
      </View>
    );
  }

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: '#090a0f' }} edges={['top']}>
      <ScrollView
        style={styles.container}
        contentContainerStyle={styles.content}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor="#f59e0b" />}
      >
      <View style={styles.header}>
        <Text style={styles.eyebrow}>LIFE OS · METAS & HÁBITOS</Text>
        <Text style={styles.title}>Construção Pessoal</Text>
      </View>

      {/* Seção Hábitos & Streaks */}
      <View style={styles.sectionHeader}>
        <Text style={styles.sectionTitle}>HÁBITOS FUNDAMENTAIS (STREAKS)</Text>
      </View>

      {habitos.map((h) => {
        const jaFezHoje = h.ultimo_checkin === new Date().toISOString().split('T')[0];

        return (
          <View key={h.id} style={styles.habitoCard}>
            <View style={{ flex: 1 }}>
              <Text style={styles.habitoNome}>{h.nome.replace('_', ' ').toUpperCase()}</Text>
              <Text style={styles.habitoPilar}>Pilar: {h.pilar} · Meta: {h.frequencia}</Text>
              <View style={styles.streakRow}>
                <Text style={styles.streakEmoji}>🔥</Text>
                <Text style={styles.streakCount}>{h.streak_atual} dias seguidos</Text>
                <Text style={styles.bestStreak}>(Recorde: {h.melhor_streak})</Text>
              </View>
            </View>

            <TouchableOpacity
              style={[
                styles.checkinBtn,
                jaFezHoje && styles.checkinBtnDone
              ]}
              onPress={() => handleCheckin(h.id)}
              disabled={jaFezHoje || checkingIn === h.id}
            >
              <Text style={styles.checkinText}>
                {jaFezHoje ? '✓ Feito' : 'Fazer'}
              </Text>
            </TouchableOpacity>
          </View>
        );
      })}

      {/* Seção Árvore de Metas */}
      <View style={[styles.sectionHeader, { marginTop: 24 }]}>
        <Text style={styles.sectionTitle}>ÁRVORE DE METAS (MACRO → MESO → MICRO)</Text>
      </View>

      {metas.length === 0 ? (
        <View style={styles.emptyCard}>
          <Text style={styles.emptyText}>
            Nenhuma meta cadastrada. Converse com o agente no chat para definir seus objetivos de 6 a 12 meses.
          </Text>
        </View>
      ) : (
        metas.map((m) => (
          <View key={m.id} style={styles.metaCard}>
            <View style={styles.metaHeader}>
              <Text style={styles.metaNivel}>{m.nivel.toUpperCase()}</Text>
              {m.prazo && <Text style={styles.metaPrazo}>Prazo: {m.prazo}</Text>}
            </View>
            <Text style={styles.metaTitulo}>{m.titulo}</Text>
            <View style={styles.progressContainer}>
              <View style={[styles.progressBar, { width: `${Math.min(100, m.progresso_pct || 0)}%` }]} />
            </View>
            <Text style={styles.progressText}>{m.progresso_pct.toFixed(0)}% concluído</Text>
          </View>
        ))
      )}
    </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#090a0f' },
  content: { padding: 20, paddingBottom: 60 },
  centerContainer: { flex: 1, justifyContent: 'center', alignItems: 'center', backgroundColor: '#090a0f' },
  loadingText: { color: '#94a3b8', marginTop: 12, fontSize: 14 },
  header: { marginBottom: 20 },
  eyebrow: { color: '#f59e0b', fontSize: 11, fontWeight: '700', letterSpacing: 1.5, marginBottom: 4 },
  title: { color: '#f8fafc', fontSize: 26, fontWeight: '800' },
  sectionHeader: { marginBottom: 12 },
  sectionTitle: { color: '#94a3b8', fontSize: 11, fontWeight: '700', letterSpacing: 1.2 },
  habitoCard: {
    backgroundColor: '#131522',
    borderColor: '#242a42',
    borderWidth: 1,
    borderRadius: 16,
    padding: 16,
    marginBottom: 12,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between'
  },
  habitoNome: { color: '#f8fafc', fontSize: 15, fontWeight: '700' },
  habitoPilar: { color: '#64748b', fontSize: 12, marginTop: 2 },
  streakRow: { flexDirection: 'row', alignItems: 'center', marginTop: 6 },
  streakEmoji: { fontSize: 14, marginRight: 4 },
  streakCount: { color: '#f59e0b', fontSize: 13, fontWeight: '800' },
  bestStreak: { color: '#64748b', fontSize: 12, marginLeft: 6 },
  checkinBtn: {
    backgroundColor: '#3b82f6',
    paddingVertical: 10,
    paddingHorizontal: 16,
    borderRadius: 12
  },
  checkinBtnDone: { backgroundColor: '#1e293b', opacity: 0.8 },
  checkinText: { color: '#ffffff', fontSize: 13, fontWeight: '700' },
  emptyCard: { backgroundColor: '#13151f', borderRadius: 14, padding: 20, alignItems: 'center' },
  emptyText: { color: '#64748b', fontSize: 13, textAlign: 'center' },
  metaCard: {
    backgroundColor: '#121420',
    borderColor: '#1e243d',
    borderWidth: 1,
    borderRadius: 16,
    padding: 16,
    marginBottom: 12
  },
  metaHeader: { flexDirection: 'row', justifyContent: 'space-between', marginBottom: 6 },
  metaNivel: { color: '#6366f1', fontSize: 10, fontWeight: '800', letterSpacing: 1 },
  metaPrazo: { color: '#94a3b8', fontSize: 11 },
  metaTitulo: { color: '#f8fafc', fontSize: 16, fontWeight: '700', marginBottom: 10 },
  progressContainer: {
    height: 6,
    backgroundColor: '#1e2238',
    borderRadius: 3,
    overflow: 'hidden',
    marginBottom: 6
  },
  progressBar: { height: '100%', backgroundColor: '#6366f1' },
  progressText: { color: '#94a3b8', fontSize: 11, alignSelf: 'flex-end', fontWeight: '600' }
});
