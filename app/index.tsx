import React, { useEffect, useState } from 'react';
import { useRouter } from 'expo-router';
import SplashScreen from '@/src/screens/SplashScreen';
import WarningScreen from '@/src/screens/WarningScreen';
import OnboardingScreen from '@/src/screens/OnboardingScreen';
import SecurityScreen from '@/src/screens/SecurityScreen';
import NavigationScreen from '@/src/screens/NavigationScreen';
import VirtualCoachScreen from '@/src/screens/VirtualCoachScreen';
import ChatScreen from '@/src/screens/ChatScreen';
import SetupScreen from '@/src/screens/SetupScreen';
import TermsScreen from '@/src/screens/TermsScreen';
import PrivacyScreen from '@/src/screens/PrivacyScreen';

export default function Splash() {
  const router = useRouter();
  const [currentScreen, setCurrentScreen] = useState<'splash' | 'warning' | 'onboarding' | 'security' | 'navigation' | 'virtualcoach' | 'chat' | 'setup' | 'terms' | 'privacy'>('splash');
  const [previousScreen, setPreviousScreen] = useState<'setup' | null>(null);

  useEffect(() => {
    // Show splash for 3 seconds, then switch to warning screen
    const splashTimer = setTimeout(() => {
      setCurrentScreen('warning');
    }, 3000);

    return () => clearTimeout(splashTimer);
  }, []);

  useEffect(() => {
    if (currentScreen === 'warning') {
      // Show warning screen for 5 seconds, then switch to onboarding
      const warningTimer = setTimeout(() => {
        setCurrentScreen('onboarding');
      }, 5000);

      return () => clearTimeout(warningTimer);
    }
  }, [currentScreen]);

  const handleOnboardingNext = () => {
    // When user taps Next on onboarding, go to security screen
    setCurrentScreen('security');
  };

  const handleSecurityNext = () => {
    // When user taps Next on security, go to navigation screen
    setCurrentScreen('navigation');
  };

  const handleNavigationNext = () => {
    // When user taps Next on navigation, go to virtual coach screen
    setCurrentScreen('virtualcoach');
  };

  const handleVirtualCoachNext = () => {
    // When user taps virtual coach button, go to chat screen
    setCurrentScreen('chat');
  };

  const handleChatNext = () => {
    // When user finishes chat, go to setup screen
    setCurrentScreen('setup');
  };

  const handleSetupNext = () => {
    // When user finishes setup, go to main app
    router.replace('/(tabs)');
  };

  const handleViewTerms = () => {
    // When user taps terms link, go to terms screen
    setPreviousScreen('setup');
    setCurrentScreen('terms');
  };

  const handleViewPrivacy = () => {
    // When user taps privacy link, go to privacy screen
    setPreviousScreen('setup');
    setCurrentScreen('privacy');
  };

  const handleCloseLegal = () => {
    // When user closes terms or privacy, go back to setup
    if (previousScreen) {
      setCurrentScreen(previousScreen);
      setPreviousScreen(null);
    }
  };

  return (
    <>
      {currentScreen === 'splash' && <SplashScreen />}
      {currentScreen === 'warning' && <WarningScreen />}
      {currentScreen === 'onboarding' && <OnboardingScreen onNext={handleOnboardingNext} />}
      {currentScreen === 'security' && <SecurityScreen onNext={handleSecurityNext} />}
      {currentScreen === 'navigation' && <NavigationScreen onNext={handleNavigationNext} />}
      {currentScreen === 'virtualcoach' && <VirtualCoachScreen onNext={handleVirtualCoachNext} />}
      {currentScreen === 'chat' && <ChatScreen onClose={handleChatNext} onNext={handleChatNext} />}
      {currentScreen === 'setup' && <SetupScreen onSetupAccount={handleSetupNext} onReceivedInvitation={handleSetupNext} onLogin={handleSetupNext} onViewTerms={handleViewTerms} onViewPrivacy={handleViewPrivacy} />}
      {currentScreen === 'terms' && <TermsScreen onClose={handleCloseLegal} />}
      {currentScreen === 'privacy' && <PrivacyScreen onClose={handleCloseLegal} />}
    </>
  );
}
