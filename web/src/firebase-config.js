// Import the functions you need from the SDKs you need
import { initializeApp } from 'firebase/app';
import { getAnalytics } from 'firebase/analytics';

// Your web app's Firebase configuration
// For Firebase JS SDK v7.20.0 and later, measurementId is optional
const firebaseConfig = {
  apiKey: 'AIzaSyBn4KcCGSevoTzOL4QLb7Krb7G8qFPtHy0',
  authDomain: 'harmony-of-dissonance-drop.firebaseapp.com',
  projectId: 'harmony-of-dissonance-drop',
  storageBucket: 'harmony-of-dissonance-drop.firebasestorage.app',
  messagingSenderId: '177756049872',
  appId: '1:177756049872:web:0157e8621c4285bc55e9d5',
  measurementId: 'G-SEZDZXYDFW',
};

// Initialize Firebase
export const app = initializeApp(firebaseConfig);
export const analytics = getAnalytics(app);
