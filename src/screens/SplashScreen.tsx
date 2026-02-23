import React from 'react';
import { 
  View, 
  Text, 
  StyleSheet, 
  Image, 
  ImageBackground, 
  StatusBar, 
  SafeAreaView 
} from 'react-native';

const SplashScreen = () => {
  return (
    <SafeAreaView style={styles.safeArea}>
      {/* Makes the top iOS/Android status bar text white */}
      <StatusBar barStyle="light-content" backgroundColor="#111111" />
      
      {/* Background Image containing the radar lines */}
      <ImageBackground 
        source={require('../assets/splash_bg.png')} 
        style={styles.background}
        resizeMode="cover"
      >
        {/* Empty view to push the logo to the center */}
        <View style={styles.spacer} />

        {/* Center Logo */}
        <View style={styles.logoContainer}>
          <Image 
            source={require('../assets/logo.png')} 
            style={styles.logo}
            resizeMode="contain"
          />
        </View>

        {/* Bottom Text Area */}
        <View style={styles.bottomContainer}>
          <Text style={styles.bottomText}>
            Process control <Text style={styles.highlightText}>in your pocket™</Text>
          </Text>
        </View>
      </ImageBackground>
    </SafeAreaView>
  );
};

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
    backgroundColor: '#111111', // Very dark background matching your design
  },
  background: {
    flex: 1,
    width: '100%',
    height: '100%',
  },
  spacer: {
    flex: 1, // Pushes the logo down to the middle
  },
  logoContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  logo: {
    width: 113,  // Adjust this based on your Figma dimensions
    height: 108, // Adjust this based on your Figma dimensions
  },
  bottomContainer: {
    flex: 1,
    justifyContent: 'flex-end',
    alignItems: 'center',
    paddingBottom: 40, // Keeps the text safely above the bottom screen edge
  },
  bottomText: {
    color: '#FFFFFF', // White text
    fontSize: 13,     // Adjust based on Figma
    fontWeight: '500',
    letterSpacing: 0.5,
  },
  highlightText: {
    color: '#E23C22', // The Red accent color from your logo
    fontWeight: '600',
  },
});

export default SplashScreen;