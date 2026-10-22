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
  ActivityIndicator
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
  const [provedor, setProvedor] = useState<'nuvem' | 'local'>('nuvem');
  const flatListRef = useRef<FlatList>(null);

  useEffect(() => {
    setProvedor(getLlmProvider());
  }, []);

  useEffect(() => {
    flatListRef.current?.scrollToEnd({ animated: true });
  }, [messages]);

  const handleToggleProvedor = (novo: 'nuvem' | 'local') => {
    setProvedor(novo);
    setLlmProvider(novo);
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
        provedor
      );

      if (response?.chatId) {
        setCurrentChatId(response.chatId);
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

  const renderMessage = ({ item }: { item: ChatMessage }) => {
    const isUser = item.role === 'user';
    const displayContent = sanitizeMessageText(item.content);

    return (
      <View
        style={[
          styles.msgBubbleContainer,
          isUser ? styles.userBubbleContainer : styles.agentBubbleContainer
        ]}
      >
        <View
          style={[
            styles.msgBubble,
            isUser ? styles.userBubble : styles.agentBubble
          ]}
        >
          {!isUser && (
            <View style={styles.badgeRow}>
              {item.provedor && (
                <View
                  style={[
                    styles.providerBadge,
                    item.provedor === 'nuvem'
                      ? styles.providerBadgeNuvem
                      : styles.providerBadgeLocal
                  ]}
                >
                  <Text
                    style={[
                      styles.providerBadgeText,
                      item.provedor === 'nuvem'
                        ? styles.providerBadgeTextNuvem
                        : styles.providerBadgeTextLocal
                    ]}
                  >
                    {item.provedor === 'nuvem' ? '☁️ Nuvem (Gemini)' : '💻 Local (Ollama)'}
                  </Text>
                </View>
              )}

              {item.route && (
                <View style={styles.routeBadge}>
                  <Text style={styles.routeBadgeText}>
                    {item.route} {item.model ? `· ${item.model}` : ''}
                  </Text>
                </View>
              )}
            </View>
          )}

          <Text style={[styles.msgText, isUser ? styles.userText : styles.agentText]}>
            {displayContent || (sending && item.role === 'assistant' ? 'Pensando...' : '')}
          </Text>
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
        {/* Barra Superior Seletora de Motor IA (Nuvem / Local) */}
        <View style={styles.providerContainer}>
          <Text style={styles.providerHeaderLabel}>MOTOR DE IA:</Text>
          <View style={styles.toggleRow}>
            <TouchableOpacity
              style={[
                styles.toggleBtn,
                provedor === 'nuvem' && styles.toggleBtnActiveNuvem
              ]}
              onPress={() => handleToggleProvedor('nuvem')}
            >
              <Text
                style={[
                  styles.toggleBtnText,
                  provedor === 'nuvem' && styles.toggleBtnTextActive
                ]}
              >
                ☁️ Nuvem (Gemini)
              </Text>
            </TouchableOpacity>

            <TouchableOpacity
              style={[
                styles.toggleBtn,
                provedor === 'local' && styles.toggleBtnActiveLocal
              ]}
              onPress={() => handleToggleProvedor('local')}
            >
              <Text
                style={[
                  styles.toggleBtnText,
                  provedor === 'local' && styles.toggleBtnTextActive
                ]}
              >
                💻 Local (Ollama)
              </Text>
            </TouchableOpacity>
          </View>
        </View>

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
            style={[styles.actionBtn, sending && styles.disabledBtn]}
            onPress={() => handleSend()}
            disabled={sending || !inputText.trim()}
          >
            {sending ? (
              <ActivityIndicator size="small" color="#ffffff" />
            ) : (
              <Text style={styles.sendIcon}>➤</Text>
            )}
          </TouchableOpacity>
        </View>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#090a0f' },
  keyboardContainer: { flex: 1 },
  listContent: { padding: 16, paddingBottom: 20 },
  providerContainer: {
    backgroundColor: '#0f111c',
    paddingHorizontal: 16,
    paddingVertical: 10,
    borderBottomWidth: 1,
    borderBottomColor: '#1e243d',
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between'
  },
  providerHeaderLabel: {
    color: '#94a3b8',
    fontSize: 10,
    fontWeight: '800',
    letterSpacing: 0.8
  },
  toggleRow: {
    flexDirection: 'row',
    backgroundColor: '#161926',
    borderRadius: 10,
    padding: 3,
    gap: 4
  },
  toggleBtn: {
    paddingHorizontal: 10,
    paddingVertical: 5,
    borderRadius: 8
  },
  toggleBtnActiveNuvem: {
    backgroundColor: '#2563eb'
  },
  toggleBtnActiveLocal: {
    backgroundColor: '#4f46e5'
  },
  toggleBtnText: {
    color: '#94a3b8',
    fontSize: 11,
    fontWeight: '700'
  },
  toggleBtnTextActive: {
    color: '#ffffff',
    fontWeight: '800'
  },
  msgBubbleContainer: { marginBottom: 12, flexDirection: 'row' },
  userBubbleContainer: { justifyContent: 'flex-end' },
  agentBubbleContainer: { justifyContent: 'flex-start' },
  msgBubble: {
    maxWidth: '85%',
    padding: 14,
    borderRadius: 18
  },
  userBubble: {
    backgroundColor: '#4338ca',
    borderBottomRightRadius: 4
  },
  agentBubble: {
    backgroundColor: '#161926',
    borderColor: '#262c45',
    borderWidth: 1,
    borderBottomLeftRadius: 4
  },
  badgeRow: {
    flexDirection: 'row',
    alignItems: 'center',
    flexWrap: 'wrap',
    gap: 6,
    marginBottom: 8
  },
  providerBadge: {
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: 4,
    borderWidth: 1
  },
  providerBadgeNuvem: {
    backgroundColor: 'rgba(37, 99, 235, 0.15)',
    borderColor: 'rgba(37, 99, 235, 0.35)'
  },
  providerBadgeLocal: {
    backgroundColor: 'rgba(79, 70, 229, 0.15)',
    borderColor: 'rgba(79, 70, 229, 0.35)'
  },
  providerBadgeText: {
    fontSize: 9,
    fontWeight: '700'
  },
  providerBadgeTextNuvem: {
    color: '#60a5fa'
  },
  providerBadgeTextLocal: {
    color: '#a5b4fc'
  },
  routeBadge: {
    backgroundColor: 'rgba(100, 116, 139, 0.15)',
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: 4,
    borderWidth: 1,
    borderColor: 'rgba(100, 116, 139, 0.3)'
  },
  routeBadgeText: {
    color: '#94a3b8',
    fontSize: 9,
    fontWeight: '700'
  },
  msgText: { fontSize: 15, lineHeight: 21 },
  userText: { color: '#f8fafc' },
  agentText: { color: '#e2e8f0' },
  msgTime: {
    fontSize: 10,
    color: '#94a3b8',
    alignSelf: 'flex-end',
    marginTop: 4
  },
  inputBar: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 10,
    paddingHorizontal: 16,
    backgroundColor: '#10121d',
    borderTopColor: '#1e243d',
    borderTopWidth: 1
  },
  textInput: {
    flex: 1,
    backgroundColor: '#161926',
    borderColor: '#262c45',
    borderWidth: 1,
    borderRadius: 22,
    color: '#f8fafc',
    paddingHorizontal: 16,
    paddingVertical: 10,
    fontSize: 15,
    maxHeight: 100,
    marginRight: 10
  },
  actionBtn: {
    width: 44,
    height: 44,
    borderRadius: 22,
    backgroundColor: '#4f46e5',
    justifyContent: 'center',
    alignItems: 'center'
  },
  disabledBtn: { backgroundColor: '#312e81', opacity: 0.7 },
  sendIcon: { color: '#ffffff', fontSize: 18, marginLeft: 2 }
});
