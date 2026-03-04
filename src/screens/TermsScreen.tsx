import React from 'react';
import { 
  View, 
  Text, 
  StyleSheet, 
  ImageBackground, 
  SafeAreaView,
  ScrollView,
  TouchableOpacity
} from 'react-native';

interface TermsScreenProps {
  onClose?: () => void;
}

const TermsScreen = ({ onClose }: TermsScreenProps) => {
  return (
    <SafeAreaView style={styles.safeArea}>
      <ImageBackground 
        source={require('../assets/splash_bg.png')} 
        style={styles.background}
        resizeMode="cover"
      >
        <View style={styles.container}>
          {/* Header */}
          <View style={styles.header}>
            <TouchableOpacity onPress={onClose}>
              <Text style={styles.backButton}>‹</Text>
            </TouchableOpacity>
            <Text style={styles.headerTitle}>Privacy and terms</Text>
            <View style={{ width: 24 }} />
          </View>

          {/* Content */}
          <ScrollView style={styles.content} contentContainerStyle={styles.contentContainer}>
            <Text style={styles.title}>Terms and Conditions</Text>
            
            <Text style={styles.sectionTitle}>Terms and Conditions</Text>
            <Text style={styles.text}>
              These Terms and Conditions ("Terms") govern your use of the PocketWatch mobile and web application ("App") provided by PocketWatch Virtual Select LLC ("Company" or "we"). By downloading, installing, or using the App, you agree to comply with and be bound by these Terms. If you do not agree with these Terms, please do not use the App.
            </Text>

            <Text style={styles.sectionTitle}>1. License and Restrictions</Text>
            <Text style={styles.text}>
              By accessing or using the App, we grant you an ongoing, non-exclusive, revocable, limited license to use the App for its intended business purposes and retain from engaging in any other conduct with the App.
            </Text>

            <Text style={styles.sectionTitle}>2. User Accounts</Text>
            <Text style={styles.text}>
              To access certain features of the App, you will be required to create an account ("User Account"). You are responsible for maintaining the confidentiality of your password and the accuracy of all information contained within your account. You agree to notify us immediately of any unauthorized use of your account.
            </Text>

            <Text style={styles.sectionTitle}>3. Intellectual Property</Text>
            <Text style={styles.text}>
              The App and its content, including but not limited to text, graphics, logos, images, audio clips, digital downloads, data compilations, intellectual property, distribution of software, and software is the exclusive property of PocketWatch Virtual Select LLC.
            </Text>

            <Text style={styles.sectionTitle}>4. Privacy</Text>
            <Text style={styles.text}>
              Our Privacy Policy governs the collection, use, and disclosure of your personal information. By using the App, you consent to be bound by these Terms.
            </Text>

            <Text style={styles.sectionTitle}>5. Data Security</Text>
            <Text style={styles.text}>
              We are committed to maintaining the confidentiality or security of any Proprietary Data that you provide to the App and/or associated with the App. Due to the inherent risks associated with internet and electronic storage, we store all Proprietary Data on cloud-computing service provider's servers, which may not ensure the security of Proprietary Data.
            </Text>

            <Text style={styles.sectionTitle}>6. Cloud-Computing Services</Text>
            <Text style={styles.text}>
              To provide you with full ownership and control of your Proprietary Data, we do not cash any sample files without your consent associated with our cloud-hosted databases. Where a customer fails to delete their associated Proprietary Data salesby for the purpose of providing you with the Access services.
            </Text>

            <Text style={styles.sectionTitle}>7. Microsoft Azure</Text>
            <Text style={styles.text}>
              Azure provides the services with the App for backup and disaster recovery. Azure Virtual Recovery, Cloud Backup, and Azure Site Recovery for fast backup and disaster recovery.
            </Text>
          </ScrollView>
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
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 16,
    paddingVertical: 16,
    borderBottomWidth: 1,
    borderBottomColor: '#333333',
  },
  backButton: {
    fontSize: 28,
    color: '#E7E7E7',
    width: 24,
  },
  headerTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: '#E7E7E7',
  },
  content: {
    flex: 1,
  },
  contentContainer: {
    paddingHorizontal: 16,
    paddingVertical: 20,
  },
  title: {
    fontSize: 20,
    fontWeight: '700',
    color: '#E7E7E7',
    marginBottom: 24,
  },
  sectionTitle: {
    fontSize: 14,
    fontWeight: '600',
    color: '#E7E7E7',
    marginTop: 16,
    marginBottom: 8,
  },
  text: {
    fontSize: 12,
    color: '#E7E7E7',
    lineHeight: 18,
    marginBottom: 12,
  },
});

export default TermsScreen;
