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
  SafeAreaView
} from 'react-native';
import { agentApi } from '../../src/services/api';
import { ChatMessage } from '../../src/types';

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
      await agentApi.enviarMensagem(texto, undefined, (chunk) => {
        accumulated += chunk;
        setMessages((prev) =>
          prev.map((msg) =>
            msg.id === assistantMsgId ? { ...msg, content: accumulated } : msg
          )
        );
      });
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
          <Text style={[styles.msgText, isUser ? styles.userText : styles.agentText]}>
            {item.content || (sending && item.role === 'assistant' ? 'Pensando...' : '')}
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
  sendIcon: { color: '#ffffff', fontSize: 18, marginLeft: 2 }
});
