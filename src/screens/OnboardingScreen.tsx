import React from 'react';
import { 
  View, 
  Text, 
  StyleSheet, 
  ImageBackground, 
  SafeAreaView,
  TouchableOpacity
} from 'react-native';
import HeaderLogo from '../components/HeaderLogo'; // Importing our new reusable logo!

const OnboardingScreen = ({ onNext }: { onNext: () => void }) => {
  return (
    <SafeAreaView style={styles.safeArea}>
      <ImageBackground 
        source={require('../assets/splash_bg.png')} 
        style={styles.background}
        resizeMode="cover"
      >
        <View style={styles.container}>
          
          {/* Top Section: Logo */}
          <View style={styles.topSection}>
            <HeaderLogo width={375} height={48} />
          </View>

          {/* Middle Section: Text */}
          <View style={styles.middleSection}>
            <View style={styles.textLayoutBox}>
              <Text style={styles.descriptionText}>
                Welcome to PocketWatch where manufacturing processes are monitored 24/7 and performance metrics made visible from the convenience of your pocket!
              </Text>
              {/* If you have another text or element here, the 'gap: 16' will automatically space them out! */}
            </View>
          </View>

          {/* Bottom Section: Next Button */}
          <View style={styles.bottomSection}>
            <TouchableOpacity 
              style={styles.nextButton}
              onPress={onNext}
            >
              <Text style={styles.buttonText}>Next</Text>
            </TouchableOpacity>
          </View>

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
    paddingHorizontal: 30, // Gives breathing room on the left and right
  },
  topSection: {
    marginTop: 40, // Pushes the logo down from the top edge
    alignItems: 'center',
  },
  middleSection: {
    flex: 1, 
    justifyContent: 'center', // This dynamically handles your Figma "top" so it scales perfectly
    alignItems: 'center', // Centers the text vertically in its space
  },
  descriptionText: {
    fontWeight: '500',
    fontSize: 18,
    lineHeight: 28,
    color: '#E7E7E7', 
  },
  bottomSection: {
    alignItems: 'flex-end', // Pushes the button to the right side
    marginBottom: 40, // Keeps the button off the bottom edge
  },
  nextButton: {
    borderColor: '#E23C22',
    borderWidth: 1.5,
    borderRadius: 25, // Makes the pill shape
    paddingVertical: 10,
    paddingHorizontal: 40,
  },
  buttonText: {
    color: '#E23C22',
    fontSize: 16,
    fontWeight: 'bold',
  },
  textLayoutBox: {
    width: 285,
    height: 176,
    gap: 16,       // React Native supports Figma's gap perfectly!
    opacity: 1,
  },

});

export default OnboardingScreen;