import React, { useState, useRef, useEffect } from 'react';
import {
  StyleSheet,
  Text,
  View,
  TextInput,
  TouchableOpacity,
  FlatList,
  KeyboardAvoidingView,
  Platform,
  ActivityIndicator,
  Modal,
  Alert
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { agentApi, getLlmProvider, setLlmProvider } from '../../src/services/api';
import { ChatMessage } from '../../src/types';

function sanitizeMessageText(text: string): string {
  if (!text) return '';
  if (!text.includes('data: {') && !text.includes('data:{')) {
    return text;
  }
  let cleanText = '';
  let fullMessage = '';
  const lines = text.split('\n');
  for (const line of lines) {
    const trimmed = line.trim();
    if (!trimmed.startsWith('data:')) continue;
    const jsonStr = trimmed.replace(/^data:\s*/, '').trim();
    if (!jsonStr || jsonStr === '[DONE]') continue;
    try {
      const parsed = JSON.parse(jsonStr);
      if (parsed.type === 'chunk' && parsed.content) {
        cleanText += parsed.content;
      } else if (parsed.type === 'message' && parsed.content) {
        fullMessage = parsed.content;
      }
    } catch {}
  }
  return fullMessage || cleanText || text;
}

export default function ChatScreen() {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: 'welcome',
      role: 'assistant',
      content: 'Olá! Sou o Agent Core. Diga uma tarefa para agendar, registre seus gastos ou faça perguntas do dia a dia.',
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      provedor: 'nuvem'
    }
  ]);
  const [inputText, setInputText] = useState('');
  const [sending, setSending] = useState(false);
  const [currentChatId, setCurrentChatId] = useState<string | null>(null);
  const [currentChatTitle, setCurrentChatTitle] = useState<string>('Nova Conversa');
  const [provedor, setProvedor] = useState<'nuvem' | 'local'>('nuvem');
  const [selectedSkill, setSelectedSkill] = useState<string>('default');
  const [selectedSkillName, setSelectedSkillName] = useState<string>('Assistente Geral');

  // Modais de Histórico e de Agentes
  const [historyModalVisible, setHistoryModalVisible] = useState(false);
  const [chatsList, setChatsList] = useState<any[]>([]);
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [historySearch, setHistorySearch] = useState('');

  const [agentModalVisible, setAgentModalVisible] = useState(false);
  const [agentesList, setAgentesList] = useState<any[]>([]);

  const flatListRef = useRef<FlatList>(null);

  useEffect(() => {
    setProvedor(getLlmProvider());
    carregarAgentes();
  }, []);

  useEffect(() => {
    flatListRef.current?.scrollToEnd({ animated: true });
  }, [messages]);

  const carregarAgentes = async () => {
    try {
      const lista = await agentApi.listarAgentes();
      setAgentesList(lista);
    } catch {}
  };

  const handleToggleProvedor = (novo: 'nuvem' | 'local') => {
    setProvedor(novo);
    setLlmProvider(novo);
  };

  const handleAbrirHistorico = async () => {
    setLoadingHistory(true);
    setHistoryModalVisible(true);
    try {
      const lista = await agentApi.listarChats();
      setChatsList(lista);
    } catch (err: any) {
      Alert.alert('Erro', err.message || 'Falha ao carregar conversas antigas.');
    } finally {
      setLoadingHistory(false);
    }
  };

  const handleSelecionarChat = async (chatItem: any) => {
    try {
      setLoadingHistory(true);
      const dados = await agentApi.carregarChat(chatItem.id);
      if (!dados || !dados.messages) {
        Alert.alert('Aviso', 'Não foi possível carregar as mensagens desta conversa.');
        return;
      }

      const msgsFormatadas: ChatMessage[] = (dados.messages || []).map((m: any, idx: number) => {
        let timeFormatted = '';
        if (m.timestamp) {
          try {
            timeFormatted = new Date(m.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
          } catch {}
        }
        return {
          id: `hist_${idx}_${Date.now()}`,
          role: m.role || 'assistant',
          content: m.content || '',
          timestamp: timeFormatted,
          provedor: m.provedor || 'nuvem',
          model: m.model,
          route: m.route,
          reasoning: m.reasoning
        };
      });

      if (msgsFormatadas.length === 0) {
        msgsFormatadas.push({
          id: 'hist_vazio',
          role: 'assistant',
          content: 'Esta conversa anterior não possui mensagens registradas.',
          timestamp: '',
          provedor: 'nuvem'
        });
      }

      setMessages(msgsFormatadas);
      setCurrentChatId(dados.id);
      setCurrentChatTitle(dados.titulo || chatItem.titulo || 'Conversa Antiga');
      setHistoryModalVisible(false);
    } catch (err: any) {
      Alert.alert('Erro', err.message || 'Falha ao retomar conversa.');
    } finally {
      setLoadingHistory(false);
    }
  };

  const handleNovoChat = () => {
    setCurrentChatId(null);
    setCurrentChatTitle('Nova Conversa');
    setMessages([
      {
        id: 'welcome_' + Date.now(),
        role: 'assistant',
        content: 'Olá! Sou o Agent Core. Diga uma tarefa para agendar, registre seus gastos ou faça perguntas do dia a dia.',
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        provedor
      }
    ]);
    if (historyModalVisible) {
      setHistoryModalVisible(false);
    }
  };

  const handleDeletarChat = (chatItem: any) => {
    Alert.alert(
      'Excluir Conversa',
      `Deseja excluir permanentemente a conversa "${chatItem.titulo}"?`,
      [
        { text: 'Cancelar', style: 'cancel' },
        {
          text: 'Excluir',
          style: 'destructive',
          onPress: async () => {
            try {
              await agentApi.deletarChat(chatItem.id);
              if (currentChatId === chatItem.id) {
                handleNovoChat();
              }
              const atualizado = await agentApi.listarChats();
              setChatsList(atualizado);
            } catch (err: any) {
              Alert.alert('Erro', err.message || 'Falha ao excluir conversa.');
            }
          }
        }
      ]
    );
  };

  const handleSelecionarAgente = (agente: any) => {
    setSelectedSkill(agente.id);
    setSelectedSkillName(agente.nome || agente.id);
    setAgentModalVisible(false);
  };

  const handleSend = async (textoParaEnviar?: string) => {
    const texto = (textoParaEnviar || inputText).trim();
    if (!texto || sending) return;

    const userMsgId = 'user_' + Date.now();
    const assistantMsgId = 'agent_' + Date.now();
    const timeStr = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

    const newMessages: ChatMessage[] = [
      ...messages,
      { id: userMsgId, role: 'user', content: texto, timestamp: timeStr },
      { id: assistantMsgId, role: 'assistant', content: '', timestamp: timeStr, provedor }
    ];

    setMessages(newMessages);
    setInputText('');
    setSending(true);

    try {
      let accumulated = '';
      const response = await agentApi.enviarMensagem(
        texto,
        currentChatId || undefined,
        (token) => {
          accumulated += token;
          setMessages((prev) =>
            prev.map((msg) =>
              msg.id === assistantMsgId ? { ...msg, content: accumulated, provedor } : msg
            )
          );
        },
        provedor,
        selectedSkill
      );

      if (response?.chatId) {
        setCurrentChatId(response.chatId);
        if (currentChatTitle === 'Nova Conversa') {
          const autoTitle = (texto.length > 35 ? texto.slice(0, 35) + '...' : texto);
          setCurrentChatTitle(autoTitle);
        }
      }

      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === assistantMsgId
            ? {
                ...msg,
                content: response.content || accumulated,
                model: response.model,
                route: response.route,
                reasoning: response.reasoning,
                provedor: (response.provedor as any) || provedor
              }
            : msg
        )
      );
    } catch (err: any) {
      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === assistantMsgId
            ? { ...msg, content: `Erro ao conectar com o Agent Core: ${err.message}` }
            : msg
        )
      );
    } finally {
      setSending(false);
    }
  };

  const formatarDataChat = (timestampSegundos: number) => {
    if (!timestampSegundos) return '';
    try {
      const data = new Date(timestampSegundos * 1000);
      const hoje = new Date();
      const mesmoDia = data.toDateString() === hoje.toDateString();
      if (mesmoDia) {
        return `Hoje às ${data.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`;
      }
      return `${data.toLocaleDateString([], { day: '2-digit', month: '2-digit' })} ${data.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`;
    } catch {
      return '';
    }
  };

  const chatsFiltrados = chatsList.filter((c) => {
    if (!historySearch.trim()) return true;
    const q = historySearch.toLowerCase();
    return (c.titulo || '').toLowerCase().includes(q) || (c.preview || '').toLowerCase().includes(q);
  });

  const renderMessage = ({ item }: { item: ChatMessage }) => {
    const isUser = item.role === 'user';
    const displayContent = sanitizeMessageText(item.content);

    return (
      <View style={[styles.msgWrapper, isUser ? styles.msgWrapperUser : styles.msgWrapperAgent]}>
        <View style={[styles.bubble, isUser ? styles.bubbleUser : styles.bubbleAgent]}>
          {item.provedor && !isUser && (
            <View style={styles.badgeRow}>
              <View
                style={[
                  styles.engineBadge,
                  item.provedor === 'local' ? styles.engineBadgeLocal : styles.engineBadgeNuvem
                ]}
              >
                <Text style={styles.engineBadgeText}>
                  {item.provedor === 'local' ? '💻 Local (Ollama)' : '☁️ Nuvem (Gemini)'}
                </Text>
              </View>
              {item.route && (
                <View style={styles.routeBadge}>
                  <Text style={styles.routeBadgeText}>
                    {item.route === 'complexo' ? '⚡ Raciocínio' : item.route}
                  </Text>
                </View>
              )}
            </View>
          )}

          {isUser ? (
            <Text style={styles.userMsgText}>{displayContent}</Text>
          ) : (
            <Text style={styles.agentMsgText}>{displayContent || '...'}</Text>
          )}

          <Text style={styles.msgTime}>{item.timestamp}</Text>
        </View>
      </View>
    );
  };

  return (
    <SafeAreaView style={styles.container}>
      <KeyboardAvoidingView
        style={styles.keyboardContainer}
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
        keyboardVerticalOffset={Platform.OS === 'ios' ? 90 : 80}
      >
        {/* Barra Superior 1: Ações de Conversa & Seletor de Agente */}
        <View style={styles.topActionsRow}>
          <View style={styles.leftActions}>
            <TouchableOpacity style={styles.actionBtn} onPress={handleAbrirHistorico}>
              <Text style={styles.actionBtnIcon}>💬</Text>
              <Text style={styles.actionBtnText}>Histórico</Text>
            </TouchableOpacity>

            <TouchableOpacity style={styles.actionBtnNovo} onPress={handleNovoChat}>
              <Text style={styles.actionBtnNovoIcon}>➕</Text>
              <Text style={styles.actionBtnNovoText}>Novo</Text>
            </TouchableOpacity>
          </View>

          <TouchableOpacity style={styles.agentPickerBtn} onPress={() => { carregarAgentes(); setAgentModalVisible(true); }}>
            <Text style={styles.agentPickerLabel}>Agente:</Text>
            <Text style={styles.agentPickerName} numberOfLines={1}>
              {selectedSkillName}
            </Text>
            <Text style={styles.agentPickerChevron}>▾</Text>
          </TouchableOpacity>
        </View>

        {/* Barra Superior 2: Seletor de Motor IA (Nuvem / Local) */}
        <View style={styles.providerContainer}>
          <Text style={styles.providerHeaderLabel}>MOTOR:</Text>
          <View style={styles.toggleRow}>
            <TouchableOpacity
              style={[styles.toggleBtn, provedor === 'nuvem' && styles.toggleBtnActiveNuvem]}
              onPress={() => handleToggleProvedor('nuvem')}
            >
              <Text style={[styles.toggleBtnText, provedor === 'nuvem' && styles.toggleBtnTextActive]}>
                ☁️ Nuvem (Gemini)
              </Text>
            </TouchableOpacity>

            <TouchableOpacity
              style={[styles.toggleBtn, provedor === 'local' && styles.toggleBtnActiveLocal]}
              onPress={() => handleToggleProvedor('local')}
            >
              <Text style={[styles.toggleBtnText, provedor === 'local' && styles.toggleBtnTextActive]}>
                💻 Local (Ollama)
              </Text>
            </TouchableOpacity>
          </View>
        </View>

        {/* Banner de Conversa Ativa */}
        {currentChatId && (
          <View style={styles.activeChatBanner}>
            <View style={{ flex: 1 }}>
              <Text style={styles.activeChatLabel}>📌 CONVERSA ATIVA:</Text>
              <Text style={styles.activeChatTitle} numberOfLines={1}>
                {currentChatTitle}
              </Text>
            </View>
            <TouchableOpacity style={styles.activeChatCloseBtn} onPress={handleNovoChat}>
              <Text style={styles.activeChatCloseText}>Nova Conversa</Text>
            </TouchableOpacity>
          </View>
        )}

        <FlatList
          ref={flatListRef}
          data={messages}
          keyExtractor={(item) => item.id}
          renderItem={renderMessage}
          contentContainerStyle={styles.listContent}
        />

        {/* Barra de Entrada de Mensagem */}
        <View style={styles.inputBar}>
          <TextInput
            style={styles.textInput}
            placeholder="Digite ou dite uma mensagem..."
            placeholderTextColor="#64748b"
            value={inputText}
            onChangeText={setInputText}
            multiline
            maxLength={1000}
          />
          <TouchableOpacity
            style={[styles.sendButton, (!inputText.trim() || sending) && styles.sendButtonDisabled]}
            onPress={() => handleSend()}
            disabled={!inputText.trim() || sending}
          >
            {sending ? (
              <ActivityIndicator size="small" color="#ffffff" />
            ) : (
              <Text style={styles.sendIcon}>➤</Text>
            )}
          </TouchableOpacity>
        </View>
      </KeyboardAvoidingView>

      {/* MODAL 1: HISTÓRICO DE CONVERSAS */}
      <Modal
        visible={historyModalVisible}
        animationType="slide"
        transparent={false}
        onRequestClose={() => setHistoryModalVisible(false)}
      >
        <SafeAreaView style={styles.modalFullContainer}>
          <View style={styles.modalHeader}>
            <View>
              <Text style={styles.modalTitle}>Histórico de Conversas</Text>
              <Text style={styles.modalSubtitle}>Acesse e retome qualquer conversa passada</Text>
            </View>
            <TouchableOpacity style={styles.modalCloseBtn} onPress={() => setHistoryModalVisible(false)}>
              <Text style={styles.modalCloseBtnText}>✕</Text>
            </TouchableOpacity>
          </View>

          <View style={styles.modalSearchBar}>
            <TextInput
              style={styles.modalSearchInput}
              placeholder="🔍 Buscar conversa por título ou assunto..."
              placeholderTextColor="#64748b"
              value={historySearch}
              onChangeText={setHistorySearch}
            />
            <TouchableOpacity style={styles.modalNewChatBtn} onPress={handleNovoChat}>
              <Text style={styles.modalNewChatText}>➕ Nova</Text>
            </TouchableOpacity>
          </View>

          {loadingHistory ? (
            <View style={styles.modalLoading}>
              <ActivityIndicator size="large" color="#6366f1" />
              <Text style={styles.modalLoadingText}>Carregando histórico do Agent Core...</Text>
            </View>
          ) : (
            <FlatList
              data={chatsFiltrados}
              keyExtractor={(item) => item.id}
              contentContainerStyle={styles.modalListContent}
              ListEmptyComponent={
                <View style={styles.emptyContainer}>
                  <Text style={styles.emptyIcon}>📂</Text>
                  <Text style={styles.emptyTitle}>Nenhuma conversa encontrada</Text>
                  <Text style={styles.emptySub}>Suas próximas conversas serão salvas automaticamente aqui.</Text>
                </View>
              }
              renderItem={({ item }) => {
                const isActive = item.id === currentChatId;
                return (
                  <TouchableOpacity
                    style={[styles.chatCard, isActive && styles.chatCardActive]}
                    onPress={() => handleSelecionarChat(item)}
                  >
                    <View style={styles.chatCardTopRow}>
                      <Text style={[styles.chatCardTitle, isActive && styles.chatCardTitleActive]} numberOfLines={1}>
                        {item.titulo}
                      </Text>
                      <TouchableOpacity
                        style={styles.chatCardDeleteBtn}
                        onPress={() => handleDeletarChat(item)}
                      >
                        <Text style={styles.chatCardDeleteText}>🗑️</Text>
                      </TouchableOpacity>
                    </View>

                    {item.preview ? (
                      <Text style={styles.chatCardPreview} numberOfLines={2}>
                        {item.preview}
                      </Text>
                    ) : null}

                    <View style={styles.chatCardFooter}>
                      <Text style={styles.chatCardDate}>{formatarDataChat(item.atualizado_em)}</Text>
                      <View style={styles.chatCardBadge}>
                        <Text style={styles.chatCardBadgeText}>💬 {item.mensagem_count} msgs</Text>
                      </View>
                      {isActive && (
                        <View style={styles.activePill}>
                          <Text style={styles.activePillText}>Ativa</Text>
                        </View>
                      )}
                    </View>
                  </TouchableOpacity>
                );
              }}
            />
          )}
        </SafeAreaView>
      </Modal>

      {/* MODAL 2: SELETOR DE AGENTES E ESPECIALISTAS */}
      <Modal
        visible={agentModalVisible}
        animationType="fade"
        transparent={true}
        onRequestClose={() => setAgentModalVisible(false)}
      >
        <View style={styles.agentModalOverlay}>
          <View style={styles.agentModalCard}>
            <View style={styles.agentModalHeader}>
              <Text style={styles.agentModalTitle}>Escolha o Agente / Skill</Text>
              <TouchableOpacity onPress={() => setAgentModalVisible(false)}>
                <Text style={styles.modalCloseBtnText}>✕</Text>
              </TouchableOpacity>
            </View>
            <Text style={styles.agentModalSub}>
              Converse diretamente com assistentes especializados:
            </Text>

            <FlatList
              data={agentesList}
              keyExtractor={(item) => item.id}
              style={{ maxHeight: 380 }}
              renderItem={({ item }) => {
                const isSelected = selectedSkill === item.id;
                return (
                  <TouchableOpacity
                    style={[styles.agentItem, isSelected && styles.agentItemSelected]}
                    onPress={() => handleSelecionarAgente(item)}
                  >
                    <Text style={styles.agentIcon}>{item.icone || '🤖'}</Text>
                    <View style={{ flex: 1, marginLeft: 10 }}>
                      <Text style={[styles.agentName, isSelected && styles.agentNameSelected]}>
                        {item.nome}
                      </Text>
                      <Text style={styles.agentType}>Tipo: {item.tipo || 'skill'}</Text>
                    </View>
                    {isSelected && <Text style={styles.agentCheck}>✓</Text>}
                  </TouchableOpacity>
                );
              }}
            />
          </View>
        </View>
      </Modal>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#090a0f' },
  keyboardContainer: { flex: 1 },

  // Ações de Topo (Histórico + Agente)
  topActionsRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 16,
    paddingTop: 10,
    paddingBottom: 8,
    backgroundColor: '#0c0e17',
    borderBottomWidth: 1,
    borderBottomColor: '#171b2d'
  },
  leftActions: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8
  },
  actionBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#1e243d',
    paddingHorizontal: 10,
    paddingVertical: 6,
    borderRadius: 8,
    gap: 4
  },
  actionBtnIcon: { fontSize: 13 },
  actionBtnText: { color: '#f8fafc', fontSize: 12, fontWeight: '700' },
  actionBtnNovo: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#3b82f6',
    paddingHorizontal: 10,
    paddingVertical: 6,
    borderRadius: 8,
    gap: 4
  },
  actionBtnNovoIcon: { fontSize: 11, color: '#fff' },
  actionBtnNovoText: { color: '#ffffff', fontSize: 12, fontWeight: '800' },

  agentPickerBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#131522',
    borderColor: '#262d47',
    borderWidth: 1,
    paddingHorizontal: 10,
    paddingVertical: 6,
    borderRadius: 8,
    maxWidth: 160
  },
  agentPickerLabel: { color: '#64748b', fontSize: 11, marginRight: 4 },
  agentPickerName: { color: '#a5b4fc', fontSize: 12, fontWeight: '700', flexShrink: 1 },
  agentPickerChevron: { color: '#64748b', fontSize: 12, marginLeft: 4 },

  // Seletor de Motor IA
  providerContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 16,
    paddingVertical: 8,
    backgroundColor: '#0f121d',
    borderBottomWidth: 1,
    borderBottomColor: '#1e2238'
  },
  providerHeaderLabel: {
    color: '#94a3b8',
    fontSize: 10,
    fontWeight: '800',
    letterSpacing: 0.8
  },
  toggleRow: {
    flexDirection: 'row',
    gap: 8
  },
  toggleBtn: {
    paddingVertical: 4,
    paddingHorizontal: 10,
    borderRadius: 14,
    backgroundColor: '#181b2a',
    borderWidth: 1,
    borderColor: '#262b42'
  },
  toggleBtnActiveNuvem: {
    backgroundColor: '#1e3a8a',
    borderColor: '#3b82f6'
  },
  toggleBtnActiveLocal: {
    backgroundColor: '#312e81',
    borderColor: '#6366f1'
  },
  toggleBtnText: {
    color: '#64748b',
    fontSize: 11,
    fontWeight: '600'
  },
  toggleBtnTextActive: {
    color: '#ffffff',
    fontWeight: '700'
  },

  // Banner Conversa Ativa
  activeChatBanner: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    backgroundColor: '#111827',
    borderBottomWidth: 1,
    borderBottomColor: '#1f2937',
    paddingHorizontal: 16,
    paddingVertical: 6
  },
  activeChatLabel: { color: '#38bdf8', fontSize: 9, fontWeight: '800', letterSpacing: 1 },
  activeChatTitle: { color: '#f8fafc', fontSize: 12, fontWeight: '600', marginTop: 1 },
  activeChatCloseBtn: {
    backgroundColor: '#1f2937',
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 6
  },
  activeChatCloseText: { color: '#94a3b8', fontSize: 10, fontWeight: '700' },

  // Lista de Mensagens
  listContent: {
    padding: 16,
    paddingBottom: 24
  },
  msgWrapper: {
    marginVertical: 6,
    flexDirection: 'row'
  },
  msgWrapperUser: { justifyContent: 'flex-end' },
  msgWrapperAgent: { justifyContent: 'flex-start' },
  bubble: {
    maxWidth: '85%',
    borderRadius: 16,
    paddingHorizontal: 14,
    paddingVertical: 10
  },
  bubbleUser: {
    backgroundColor: '#2563eb',
    borderBottomRightRadius: 4
  },
  bubbleAgent: {
    backgroundColor: '#161928',
    borderColor: '#262a42',
    borderWidth: 1,
    borderBottomLeftRadius: 4
  },
  badgeRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    marginBottom: 6
  },
  engineBadge: {
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: 4
  },
  engineBadgeNuvem: { backgroundColor: '#1e3a8a' },
  engineBadgeLocal: { backgroundColor: '#312e81' },
  engineBadgeText: { color: '#93c5fd', fontSize: 9, fontWeight: '700' },
  routeBadge: {
    backgroundColor: '#064e3b',
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: 4
  },
  routeBadgeText: { color: '#6ee7b7', fontSize: 9, fontWeight: '700' },
  userMsgText: { color: '#ffffff', fontSize: 15, lineHeight: 21 },
  agentMsgText: { color: '#f1f5f9', fontSize: 15, lineHeight: 22 },
  msgTime: {
    color: '#64748b',
    fontSize: 10,
    marginTop: 4,
    alignSelf: 'flex-end'
  },

  // Barra de Input
  inputBar: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 12,
    paddingVertical: 8,
    backgroundColor: '#0c0e17',
    borderTopWidth: 1,
    borderTopColor: '#1e243d'
  },
  textInput: {
    flex: 1,
    backgroundColor: '#161826',
    borderColor: '#272d47',
    borderWidth: 1,
    borderRadius: 20,
    paddingHorizontal: 16,
    paddingVertical: 8,
    color: '#f8fafc',
    fontSize: 15,
    maxHeight: 100
  },
  sendButton: {
    backgroundColor: '#6366f1',
    width: 40,
    height: 40,
    borderRadius: 20,
    justifyContent: 'center',
    alignItems: 'center',
    marginLeft: 8
  },
  sendButtonDisabled: { opacity: 0.5 },
  sendIcon: { color: '#ffffff', fontSize: 18, marginLeft: 2 },

  // Modal de Histórico
  modalFullContainer: { flex: 1, backgroundColor: '#090a0f' },
  modalHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 20,
    paddingVertical: 16,
    borderBottomWidth: 1,
    borderBottomColor: '#1e243d'
  },
  modalTitle: { color: '#f8fafc', fontSize: 20, fontWeight: '800' },
  modalSubtitle: { color: '#64748b', fontSize: 12, marginTop: 2 },
  modalCloseBtn: { padding: 6 },
  modalCloseBtnText: { color: '#94a3b8', fontSize: 18, fontWeight: '700' },

  modalSearchBar: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 16,
    paddingVertical: 12,
    gap: 8,
    borderBottomWidth: 1,
    borderBottomColor: '#161928'
  },
  modalSearchInput: {
    flex: 1,
    backgroundColor: '#131522',
    borderColor: '#242a42',
    borderWidth: 1,
    borderRadius: 12,
    paddingHorizontal: 12,
    paddingVertical: 8,
    color: '#f8fafc',
    fontSize: 13
  },
  modalNewChatBtn: {
    backgroundColor: '#2563eb',
    paddingHorizontal: 14,
    paddingVertical: 10,
    borderRadius: 12
  },
  modalNewChatText: { color: '#ffffff', fontSize: 12, fontWeight: '700' },
  modalLoading: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  modalLoadingText: { color: '#94a3b8', marginTop: 12, fontSize: 14 },
  modalListContent: { padding: 16, paddingBottom: 40 },

  chatCard: {
    backgroundColor: '#121420',
    borderColor: '#1e243d',
    borderWidth: 1,
    borderRadius: 14,
    padding: 14,
    marginBottom: 10
  },
  chatCardActive: { borderColor: '#38bdf8', backgroundColor: '#131b2e' },
  chatCardTopRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  chatCardTitle: { color: '#f8fafc', fontSize: 15, fontWeight: '700', flex: 1, marginRight: 8 },
  chatCardTitleActive: { color: '#38bdf8' },
  chatCardDeleteBtn: { padding: 4 },
  chatCardDeleteText: { fontSize: 14 },
  chatCardPreview: { color: '#94a3b8', fontSize: 12, marginTop: 6, lineHeight: 17 },
  chatCardFooter: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginTop: 10
  },
  chatCardDate: { color: '#64748b', fontSize: 11 },
  chatCardBadge: { backgroundColor: '#1e243d', paddingHorizontal: 6, paddingVertical: 2, borderRadius: 6 },
  chatCardBadgeText: { color: '#94a3b8', fontSize: 10, fontWeight: '600' },
  activePill: { backgroundColor: '#0284c7', paddingHorizontal: 6, paddingVertical: 2, borderRadius: 6 },
  activePillText: { color: '#ffffff', fontSize: 10, fontWeight: '800' },

  emptyContainer: { alignItems: 'center', paddingVertical: 60 },
  emptyIcon: { fontSize: 40, marginBottom: 12 },
  emptyTitle: { color: '#f8fafc', fontSize: 16, fontWeight: '700' },
  emptySub: { color: '#64748b', fontSize: 13, textAlign: 'center', marginTop: 4, paddingHorizontal: 30 },

  // Modal Agentes
  agentModalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.7)',
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20
  },
  agentModalCard: {
    width: '100%',
    backgroundColor: '#131522',
    borderColor: '#262d47',
    borderWidth: 1,
    borderRadius: 18,
    padding: 20
  },
  agentModalHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  agentModalTitle: { color: '#f8fafc', fontSize: 18, fontWeight: '800' },
  agentModalSub: { color: '#94a3b8', fontSize: 12, marginTop: 4, marginBottom: 14 },
  agentItem: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 12,
    paddingHorizontal: 12,
    borderRadius: 12,
    marginBottom: 6,
    backgroundColor: '#171a2b'
  },
  agentItemSelected: { backgroundColor: '#1e293b', borderColor: '#3b82f6', borderWidth: 1 },
  agentIcon: { fontSize: 20 },
  agentName: { color: '#f8fafc', fontSize: 14, fontWeight: '700' },
  agentNameSelected: { color: '#60a5fa' },
  agentType: { color: '#64748b', fontSize: 11, marginTop: 2 },
  agentCheck: { color: '#38bdf8', fontSize: 16, fontWeight: '800' }
});
