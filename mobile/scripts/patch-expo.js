const fs = require('fs');
const path = require('path');

const targetFile = path.join(
  __dirname,
  '..',
  'node_modules',
  'expo-notifications',
  'build',
  'TopicSubscriptionModule.android.js'
);

try {
  if (fs.existsSync(targetFile)) {
    const safeContent = `import { requireOptionalNativeModule } from 'expo-modules-core';
const nativeModule = requireOptionalNativeModule('ExpoTopicSubscriptionModule');
export default nativeModule || {
  addListener: () => {},
  removeListeners: () => {},
  subscribeToTopicAsync: () => Promise.resolve(null),
  unsubscribeFromTopicAsync: () => Promise.resolve(null),
};
`;
    fs.writeFileSync(targetFile, safeContent, 'utf8');
    console.log('[patch-expo] Patched TopicSubscriptionModule.android.js for Expo Go compatibility.');
  }
} catch (err) {
  console.warn('[patch-expo] Could not patch expo-notifications:', err.message);
}
