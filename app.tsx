import React, { useState, useEffect } from 'react';
import SplashScreen from './src/screens/SplashScreen';
import WarningScreen from './src/screens/WarningScreen';
import OnboardingScreen from './src/screens/OnboardingScreen';

const App = () => {
  const [currentScreen, setCurrentScreen] = useState('Splash');

  useEffect(() => {
    // If we are on Splash, wait 3 seconds then go to Warning
    if (currentScreen === 'Splash') {
      const timer = setTimeout(() => setCurrentScreen('Warning'), 3000);
      return () => clearTimeout(timer);
    } 
    // If we are on Warning, wait 4 seconds then go to Onboarding
    else if (currentScreen === 'Warning') {
      const timer = setTimeout(() => setCurrentScreen('Onboarding'), 4000);
      return () => clearTimeout(timer);
    }
  }, [currentScreen]); // This effect re-runs every time currentScreen changes

  // Check which screen to show
  if (currentScreen === 'Splash') return <SplashScreen />;
  if (currentScreen === 'Warning') return <WarningScreen />;
  if (currentScreen === 'Onboarding') return <OnboardingScreen onNext={() => setCurrentScreen('NextScreen')} />;

  return null;
};

export default App;