import React from 'react';
import { Tabs } from 'expo-router';
import { Text, Platform } from 'react-native';

export default function TabLayout() {
  return (
    <Tabs
      screenOptions={{
        tabBarActiveTintColor: '#6366f1',
        tabBarInactiveTintColor: '#64748b',
        tabBarStyle: {
          backgroundColor: '#0c0e17',
          borderTopColor: '#1e243d',
          height: Platform.OS === 'android' ? 68 : 60,
          paddingBottom: Platform.OS === 'android' ? 12 : 8,
          paddingTop: 6
        },
        headerStyle: {
          backgroundColor: '#090a0f'
        },
        headerTintColor: '#f8fafc',
        headerTitleStyle: {
          fontWeight: '800'
        }
      }}
    >
      <Tabs.Screen
        name="index"
        options={{
          title: 'Cockpit',
          headerShown: false,
          tabBarIcon: ({ color }) => (
            <Text style={{ fontSize: 20 }}>🎯</Text>
          )
        }}
      />
      <Tabs.Screen
        name="chat"
        options={{
          title: 'Chat IA',
          headerTitle: 'Agent Core · Conversa',
          tabBarIcon: ({ color }) => (
            <Text style={{ fontSize: 20 }}>💬</Text>
          )
        }}
      />
      <Tabs.Screen
        name="finances"
        options={{
          title: 'Finanças',
          headerShown: false,
          tabBarIcon: ({ color }) => (
            <Text style={{ fontSize: 20 }}>💰</Text>
          )
        }}
      />
      <Tabs.Screen
        name="life"
        options={{
          title: 'Life OS',
          headerShown: false,
          tabBarIcon: ({ color }) => (
            <Text style={{ fontSize: 20 }}>🔥</Text>
          )
        }}
      />
      <Tabs.Screen
        name="settings"
        options={{
          title: 'Ajustes',
          headerShown: false,
          tabBarIcon: ({ color }) => (
            <Text style={{ fontSize: 20 }}>⚙️</Text>
          )
        }}
      />
    </Tabs>
  );
}
