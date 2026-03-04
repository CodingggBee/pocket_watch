import React, { useState } from 'react';
import { 
  View, 
  Text, 
  StyleSheet, 
  ImageBackground, 
  SafeAreaView,
  TouchableOpacity,
  Image,
  Pressable
} from 'react-native';

interface SetupScreenProps {
  onSetupAccount?: () => void;
  onReceivedInvitation?: () => void;
  onLogin?: () => void;
  onViewTerms?: () => void;
  onViewPrivacy?: () => void;
}

const SetupScreen = ({ onSetupAccount, onReceivedInvitation, onLogin, onViewTerms, onViewPrivacy }: SetupScreenProps) => {
  const [agreedToTerms, setAgreedToTerms] = useState(false);

  return (
    <SafeAreaView style={styles.safeArea}>
      <ImageBackground 
        source={require('../assets/splash_bg.png')} 
        style={styles.background}
        resizeMode="cover"
      >
        <View style={styles.container}>
          {/* Phone Mockups Image */}
          <View style={styles.phoneContainer}>
            <Image
              source={require('../assets/setup_phones.png')}
              style={styles.phoneImage}
              resizeMode="contain"
            />
          </View>

          {/* Welcome Text */}
          <View style={styles.textContainer}>
            <Text style={styles.welcomeText}>Welcome to PocketWatch. Let's get started!</Text>
          </View>

          {/* Buttons */}
          <View style={styles.buttonsContainer}>
            <TouchableOpacity 
              style={[styles.button, styles.primaryButton]}
              onPress={onSetupAccount}
            >
              <Text style={styles.primaryButtonText}>Set up an account</Text>
            </TouchableOpacity>

            <TouchableOpacity 
              style={[styles.button, styles.secondaryButton]}
              onPress={onReceivedInvitation}
            >
              <Text style={styles.secondaryButtonText}>I received an invitation</Text>
            </TouchableOpacity>
          </View>

          {/* Login Text */}
          <View style={styles.loginContainer}>
            <Text style={styles.loginText}>
              Already have an account?{' '}
              <Text 
                style={styles.loginLink}
                onPress={onLogin}
              >
                Login
              </Text>
            </Text>
          </View>

          {/* Terms Checkbox */}
          <View style={styles.termsContainer}>
            <Pressable 
              style={styles.checkbox}
              onPress={() => setAgreedToTerms(!agreedToTerms)}
            >
              <View style={[styles.checkboxBox, agreedToTerms && styles.checkboxBoxChecked]}>
                {agreedToTerms && <Text style={styles.checkmark}>✓</Text>}
              </View>
            </Pressable>
            <Text style={styles.termsText}>
              I have read, and agree with the PocketWatch{' '}
              <Text 
                style={styles.termsLink}
                onPress={onViewTerms}
              >
                terms of use
              </Text>
              {' '}and{' '}
              <Text 
                style={styles.termsLink}
                onPress={onViewPrivacy}
              >
                privacy policy
              </Text>
            </Text>
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
    paddingHorizontal: 20,
    justifyContent: 'space-between',
    paddingVertical: 40,
  },
  phoneContainer: {
    alignItems: 'center',
    height: 280,
    justifyContent: 'center',
  },
  phoneImage: {
    width: 320,
    height: 280,
  },
  textContainer: {
    alignItems: 'center',
    marginVertical: 20,
  },
  welcomeText: {
    fontSize: 24,
    fontWeight: '700',
    color: '#FFFFFF',
    textAlign: 'center',
    lineHeight: 32,
  },
  buttonsContainer: {
    gap: 12,
  },
  button: {
    paddingVertical: 16,
    borderRadius: 12,
    alignItems: 'center',
    justifyContent: 'center',
  },
  primaryButton: {
    backgroundColor: '#E84545',
  },
  primaryButtonText: {
    color: '#FFFFFF',
    fontSize: 16,
    fontWeight: '600',
  },
  secondaryButton: {
    backgroundColor: '#E84545',
  },
  secondaryButtonText: {
    color: '#FFFFFF',
    fontSize: 16,
    fontWeight: '600',
  },
  loginContainer: {
    alignItems: 'center',
    marginVertical: 12,
  },
  loginText: {
    fontSize: 14,
    color: '#E7E7E7',
  },
  loginLink: {
    color: '#E84545',
    fontWeight: '600',
  },
  termsContainer: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 12,
    marginTop: 20,
  },
  checkbox: {
    marginTop: 2,
  },
  checkboxBox: {
    width: 20,
    height: 20,
    borderWidth: 2,
    borderColor: '#666666',
    borderRadius: 4,
    justifyContent: 'center',
    alignItems: 'center',
  },
  checkboxBoxChecked: {
    backgroundColor: '#E84545',
    borderColor: '#E84545',
  },
  checkmark: {
    color: '#FFFFFF',
    fontSize: 14,
    fontWeight: 'bold',
  },
  termsText: {
    flex: 1,
    fontSize: 12,
    color: '#E7E7E7',
    lineHeight: 18,
  },
  termsLink: {
    color: '#E84545',
    fontWeight: '600',
  },
});

export default SetupScreen;
