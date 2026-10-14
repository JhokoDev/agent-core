/** Captura e preferências do navegador, isoladas das páginas e do HTTP. */
export const audioDevices = {
  enumerate: () => navigator.mediaDevices.enumerateDevices(),
  acquire: (inputId: string) => navigator.mediaDevices.getUserMedia({ audio: inputId ? { deviceId: { ideal: inputId } } : true }),
  savedInput: () => localStorage.getItem('harvey-input-id') || '',
  savedOutput: () => localStorage.getItem('harvey-output-id') || '',
  saveInput: (value: string) => localStorage.setItem('harvey-input-id', value),
  saveOutput: (value: string) => localStorage.setItem('harvey-output-id', value),
};
