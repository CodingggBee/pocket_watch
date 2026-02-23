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

const VirtualCoachScreen = ({ onNext }: { onNext: () => void }) => {
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

          {/* Middle Section: Virtual Coach Text */}
          <View style={styles.middleSection}>
            <View style={styles.textLayoutBox}>
              <Text style={styles.descriptionText}>
                Select <Text style={styles.deltaIcon}>Δ</Text> at the bottom of any screen to access the <Text style={styles.italicText}>virtual coach</Text> and get your questions answered. Try it now! You can say "How do I setup a station?" or "How do I add a user?"
              </Text>
            </View>
          </View>

          {/* Bottom Section: Delta Icon Button */}
          <View style={styles.bottomSection}>
            <TouchableOpacity 
              style={styles.deltaButton}
              onPress={onNext}
            >
              <Text style={styles.deltaButtonText}>Δ</Text>
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
  deltaIcon: {
    color: '#E23C22',
    fontWeight: '700',
  },
  italicText: {
    fontStyle: 'italic',
  },
  bottomSection: {
    alignItems: 'flex-end',
    marginBottom: 40,
  },
  deltaButton: {
    width: 56,
    height: 56,
    borderRadius: 28,
    backgroundColor: '#E23C22',
    justifyContent: 'center',
    alignItems: 'center',
  },
  deltaButtonText: {
    color: '#FFFFFF',
    fontSize: 28,
    fontWeight: 'bold',
  }
});

export default VirtualCoachScreen;
