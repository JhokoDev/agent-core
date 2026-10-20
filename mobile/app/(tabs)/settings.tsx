import React, { useState } from 'react';
import {
  StyleSheet,
  Text,
  View,
  ScrollView,
  TextInput,
  TouchableOpacity,
  Switch,
  Alert
} from 'react-native';
import { setApiConfig, getApiBaseUrl, getBundlerHost, agentApi } from '../../src/services/api';

export default function SettingsScreen() {
  const detectedHost = getBundlerHost();
  const [serverUrl, setServerUrl] = useState(() => {
    const current = getApiBaseUrl();
    if (!current || current.includes('127.0.0.1') || current.includes('localhost')) {
      return `http://${detectedHost}:8000`;
    }
    return current;
  });
  const [token, setToken] = useState('minhasenha_super_segura_de_32_caracteres_minimo_aqui');
  const [modoImprevisto, setModoImprevisto] = useState(false);
  const [motivoImprevisto, setMotivoImprevisto] = useState('');
  const [testing, setTesting] = useState(false);

  const handleUsarIpDetectado = () => {
    const defaultUrl = `http://${detectedHost}:8000`;
    setServerUrl(defaultUrl);
    setApiConfig(defaultUrl, token.trim());
    Alert.alert('IP Aplicado', `URL redefinida para ${defaultUrl}`);
  };

  const handleSalvarConexao = async () => {
    if (!serverUrl.trim()) {
      Alert.alert('Aviso', 'Informe a URL do servidor.');
      return;
    }
    await setApiConfig(serverUrl.trim(), token.trim());
    Alert.alert('Configuração Salva', 'A URL do servidor Agent Core foi atualizada e salva.');
  };

  const handleTestarConexao = async () => {
    setTesting(true);
    try {
      await setApiConfig(serverUrl.trim(), token.trim());
      const res = await agentApi.getDashboardStatus();
      Alert.alert(
        'Conexão Bem-Sucedida!',
        `Agent Core online respondendo na data ${res.data}.`
      );
    } catch (err: any) {
      Alert.alert('Falha na Conexão', err.message || 'Verifique se o backend está rodando e o Tailscale está ativo.');
    } finally {
      setTesting(false);
    }
  };

  const handleToggleModoImprevisto = (value: boolean) => {
    if (value && !motivoImprevisto.trim()) {
      Alert.alert('Aviso', 'Informe o motivo do imprevisto antes de pausar a cobrança.');
      return;
    }
    setModoImprevisto(value);
    if (value) {
      Alert.alert(
        'Modo Imprevisto Ativado',
        'As cobranças e alarmes automáticos foram suspensos para o restante do período de emergência.'
      );
    }
  };

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      <View style={styles.header}>
        <Text style={styles.eyebrow}>CENTRAL & CONECTIVIDADE</Text>
        <Text style={styles.title}>Ajustes do Agente</Text>
      </View>

      {/* Configuração de Conexão com PC (Tailscale) */}
      <View style={styles.card}>
        <Text style={styles.cardTitle}>Conexão com o PC (Tailscale / LAN)</Text>
        <Text style={styles.cardSubtitle}>
          Endereço do backend FastAPI rodando no seu computador:
        </Text>

        <Text style={styles.inputLabel}>URL DO SERVIDOR</Text>
        <TextInput
          style={styles.input}
          value={serverUrl}
          onChangeText={setServerUrl}
          placeholder="Ex: http://100.x.x.x:8000"
          placeholderTextColor="#64748b"
          autoCapitalize="none"
          autoCorrect={false}
        />

        <Text style={styles.inputLabel}>TOKEN DE AUTENTICAÇÃO</Text>
        <TextInput
          style={styles.input}
          value={token}
          onChangeText={setToken}
          placeholder="Token Bearer do .env"
          placeholderTextColor="#64748b"
          secureTextEntry
          autoCapitalize="none"
          autoCorrect={false}
        />

        <TouchableOpacity
          style={{ marginBottom: 14, padding: 8, backgroundColor: '#1e293b', borderRadius: 8, alignItems: 'center' }}
          onPress={handleUsarIpDetectado}
        >
          <Text style={{ color: '#818cf8', fontSize: 13, fontWeight: '600' }}>
            Usar IP Detectado ({detectedHost}:8000)
          </Text>
        </TouchableOpacity>

        <View style={styles.btnRow}>
          <TouchableOpacity
            style={[styles.btn, styles.btnTest]}
            onPress={handleTestarConexao}
            disabled={testing}
          >
            <Text style={styles.btnTestText}>
              {testing ? 'Testando...' : '⚡ Testar Conexão'}
            </Text>
          </TouchableOpacity>

          <TouchableOpacity style={[styles.btn, styles.btnSave]} onPress={handleSalvarConexao}>
            <Text style={styles.btnSaveText}>Salvar</Text>
          </TouchableOpacity>
        </View>
      </View>

      {/* Válvula de Escape: Modo Imprevisto */}
      <View style={styles.card}>
        <View style={styles.switchHeader}>
          <View style={{ flex: 1, marginRight: 10 }}>
            <Text style={styles.cardTitle}>Modo Imprevisto (Válvula de Escape)</Text>
            <Text style={styles.cardSubtitle}>
              Pausa imediatamente as cobranças em caso de emergência médica ou familiar real.
            </Text>
          </View>
          <Switch
            value={modoImprevisto}
            onValueChange={handleToggleModoImprevisto}
            trackColor={{ false: '#334155', true: '#ef4444' }}
            thumbColor={modoImprevisto ? '#ffffff' : '#94a3b8'}
          />
        </View>

        {modoImprevisto ? (
          <View style={styles.alertBanner}>
            <Text style={styles.alertText}>🚨 Cobranças ativas estão temporariamente suspensas.</Text>
          </View>
        ) : (
          <TextInput
            style={[styles.input, { marginTop: 12 }]}
            value={motivoImprevisto}
            onChangeText={setMotivoImprevisto}
            placeholder="Qual o imprevisto de hoje? (obrigatório para ativar)"
            placeholderTextColor="#64748b"
          />
        )}
      </View>

      {/* Informações do Sistema */}
      <View style={[styles.card, { marginBottom: 30 }]}>
        <Text style={styles.cardTitle}>Agent Core Life OS</Text>
        <Text style={styles.systemInfo}>Versão do App: 1.0.0 (Expo Mobile)</Text>
        <Text style={styles.systemInfo}>Integrações: Windows Win32 · Chrome WebSocket · Whisper · Ollama</Text>
        <Text style={styles.systemInfo}>Repositório: github.com/JhokoDev/agent-core</Text>
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#090a0f' },
  content: { padding: 20, paddingBottom: 60 },
  header: { marginBottom: 20 },
  eyebrow: { color: '#6366f1', fontSize: 11, fontWeight: '700', letterSpacing: 1.5, marginBottom: 4 },
  title: { color: '#f8fafc', fontSize: 26, fontWeight: '800' },
  card: {
    backgroundColor: '#121420',
    borderColor: '#1e243d',
    borderWidth: 1,
    borderRadius: 16,
    padding: 18,
    marginBottom: 16
  },
  cardTitle: { color: '#f8fafc', fontSize: 16, fontWeight: '700' },
  cardSubtitle: { color: '#64748b', fontSize: 13, marginTop: 4, marginBottom: 12 },
  inputLabel: { color: '#94a3b8', fontSize: 10, fontWeight: '800', letterSpacing: 1, marginBottom: 6 },
  input: {
    backgroundColor: '#0c0e17',
    borderColor: '#262c45',
    borderWidth: 1,
    borderRadius: 12,
    color: '#f8fafc',
    padding: 12,
    fontSize: 14,
    marginBottom: 14
  },
  btnRow: { flexDirection: 'row', gap: 10, marginTop: 6 },
  btn: { paddingVertical: 12, borderRadius: 12, alignItems: 'center', justifyContent: 'center' },
  btnTest: { backgroundColor: '#1e1b4b', borderColor: '#4338ca', borderWidth: 1, flex: 1.2 },
  btnSave: { backgroundColor: '#4f46e5', flex: 1 },
  btnTestText: { color: '#c7d2fe', fontSize: 13, fontWeight: '700' },
  btnSaveText: { color: '#ffffff', fontSize: 13, fontWeight: '700' },
  switchHeader: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' },
  alertBanner: {
    backgroundColor: '#450a0a',
    borderColor: '#991b1b',
    borderWidth: 1,
    borderRadius: 10,
    padding: 12,
    marginTop: 12
  },
  alertText: { color: '#fecaca', fontSize: 13, fontWeight: '700' },
  systemInfo: { color: '#64748b', fontSize: 12, marginTop: 4 }
});
