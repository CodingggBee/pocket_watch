import React from 'react';
import { 
  View, 
  Text, 
  StyleSheet, 
  ImageBackground, 
  SafeAreaView,
  TouchableOpacity
} from 'react-native';
import HeaderLogo from '../components/HeaderLogo';

const SecurityScreen = ({ onNext }: { onNext: () => void }) => {
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

          {/* Middle Section: Security Text */}
          <View style={styles.middleSection}>
            <View style={styles.textLayoutBox}>
              <Text style={styles.descriptionText}>
                Your data is secure with Pocketwatch. GPS ensures plant data is accessible only onsite and no data is ever stored on any mobile device.
              </Text>
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
    paddingHorizontal: 30,
  },
  topSection: {
    marginTop: 40,
    alignItems: 'center',
  },
  middleSection: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  textLayoutBox: {
    width: 285,
    height: 176,
    gap: 16,
    opacity: 1,
  },
  descriptionText: {
    fontWeight: '500',
    fontSize: 18,
    lineHeight: 28,
    color: '#E7E7E7',
  },
  bottomSection: {
    alignItems: 'flex-end',
    marginBottom: 40,
  },
  nextButton: {
    borderColor: '#E23C22',
    borderWidth: 1.5,
    borderRadius: 25,
    paddingVertical: 10,
    paddingHorizontal: 40,
  },
  buttonText: {
    color: '#E23C22',
    fontSize: 16,
    fontWeight: 'bold',
  }
});

export default SecurityScreen;
