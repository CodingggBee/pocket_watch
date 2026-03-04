import React from 'react';
import { 
  View, 
  Text, 
  StyleSheet, 
  Image, 
  ImageBackground, 
  SafeAreaView 
} from 'react-native';

const WarningScreen = () => {
  return (
    <SafeAreaView style={styles.safeArea}>
      <ImageBackground 
        source={require('../assets/splash_bg.png')} 
        style={styles.background}
        resizeMode="cover"
      >
        <View style={styles.container}>
          
          {/* Top Warning Icon */}
          <Image 
            source={require('../assets/warning_icon.png')} 
            style={styles.warningIcon}
            resizeMode="contain"
          />

          {/* New: Built-in Pocketwatch Logo using Flexbox Row */}
          <View style={styles.pocketwatchRow}>
            <Text style={styles.pocketwatchText}>P O C K E T W </Text>
            {/* We are reusing the triangle logo from your splash screen here! */}
            <Image 
              source={require('../assets/logo.png')} 
              style={styles.triangleA}
              resizeMode="contain"
            />
            <Text style={styles.pocketwatchText}> T C H</Text>
          </View>

          {/* First Text Block */}
          <Text style={styles.mediumRedText}>IS</Text>
          <Text style={styles.largeBoldRedText}>MOTION SENSITIVE!</Text>

          {/* Big Spacer */}
          <View style={styles.largeSpacer} />

          {/* Huge "TO USE" Text */}
          <Text style={styles.hugeRedText}>TO USE</Text>

          {/* Big Spacer */}
          <View style={styles.largeSpacer} />

          {/* Bottom Text Block tightly stacked */}
          <Text style={styles.largeBoldRedText}>YOU MUST BE</Text>
          <Text style={styles.smallRedText}>IN A</Text>
          <Text style={styles.largeBoldRedText}>SAFE PLACE</Text>
          <Text style={styles.smallRedText}>AND</Text>
          <Text style={styles.largeBoldRedText}>STATIONARY</Text>

        </View>
      </ImageBackground>
    </SafeAreaView>
  );
};

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
    backgroundColor: '#111111',
  },
  background: {
    flex: 1,
    width: '100%',
    height: '100%',
  },
  container: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 20,
  },
  warningIcon: {
    width: 110,
    height: 110,
    marginBottom: 35, // Pushes it up a bit
  },
  
  // --- New Layout for P O C K E T W A T C H ---
  pocketwatchRow: {
    flexDirection: 'row', // Aligns the text and image side-by-side horizontally
    alignItems: 'center',
    marginBottom: 20,
  },
  pocketwatchText: {
    color: '#FFFFFF',
    fontSize: 20,
    fontWeight: 'bold',
  },
  triangleA: {
    width: 22,
    height: 22,
    marginHorizontal: -2, // Pulls the letters slightly closer to the triangle
  },
  
  // --- Adjusted Text Styling ---
  mediumRedText: {
    color: '#E23C22',
    fontSize: 20,
    fontWeight: '600',
    textAlign: 'center',
    marginBottom: 5,
    letterSpacing: 1.5,
  },
  largeBoldRedText: {
    color: '#E23C22',
    fontSize: 28, // Made larger
    fontWeight: '800',
    textAlign: 'center',
    letterSpacing: 1.5,
    lineHeight: 34, // Line height keeps the stacked text tightly together
  },
  smallRedText: {
    color: '#E23C22',
    fontSize: 15,
    fontWeight: '600',
    textAlign: 'center',
    letterSpacing: 1.5,
    lineHeight: 28,
  },
  hugeRedText: {
    color: '#E23C22',
    fontSize: 65, // Made much larger to match Figma
    fontWeight: '900',
    textAlign: 'center',
    letterSpacing: 2,
  },
  largeSpacer: {
    height: 45, // Creates that distinct empty gap above and below "TO USE"
  },
});

export default WarningScreen;