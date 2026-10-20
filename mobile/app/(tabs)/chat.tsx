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
import { agentApi } from '../../src/services/api';
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
      content: 'Olá! Sou o Agent Core. Diga uma tarefa para organizar, um gasto do dia ou peça para eu abrir programas no seu computador.',
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    }
  ]);
  const [inputText, setInputText] = useState('');
  const [sending, setSending] = useState(false);
  const [recording, setRecording] = useState(false);
  const [currentChatId, setCurrentChatId] = useState<string | null>(null);
  const flatListRef = useRef<FlatList>(null);

  useEffect(() => {
    flatListRef.current?.scrollToEnd({ animated: true });
  }, [messages]);

  const handleSend = async (textoParaEnviar?: string) => {
    const texto = (textoParaEnviar || inputText).trim();
    if (!texto || sending) return;

    const userMsgId = 'user_' + Date.now();
    const assistantMsgId = 'agent_' + Date.now();
    const timeStr = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

    const newMessages: ChatMessage[] = [
      ...messages,
      { id: userMsgId, role: 'user', content: texto, timestamp: timeStr },
      { id: assistantMsgId, role: 'assistant', content: '', timestamp: timeStr }
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
              msg.id === assistantMsgId ? { ...msg, content: accumulated } : msg
            )
          );
        }
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
                reasoning: response.reasoning
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
          {item.route && (
            <View style={styles.routeBadge}>
              <Text style={styles.routeBadgeText}>
                {item.route} {item.model ? `· ${item.model}` : ''}
              </Text>
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
        behavior={Platform.OS === 'ios' ? 'padding' : undefined}
        keyboardVerticalOffset={Platform.OS === 'ios' ? 90 : 0}
      >
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
  msgBubbleContainer: { marginBottom: 12, flexDirection: 'row' },
  userBubbleContainer: { justifyContent: 'flex-end' },
  agentBubbleContainer: { justifyContent: 'flex-start' },
  msgBubble: {
    maxWidth: '82%',
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
  sendIcon: { color: '#ffffff', fontSize: 18, marginLeft: 2 },
  routeBadge: {
    alignSelf: 'flex-start',
    backgroundColor: 'rgba(59, 130, 246, 0.15)',
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: 4,
    marginBottom: 6,
    borderWidth: 1,
    borderColor: 'rgba(59, 130, 246, 0.3)'
  },
  routeBadgeText: {
    color: '#60a5fa',
    fontSize: 10,
    fontWeight: '700'
  }
});
