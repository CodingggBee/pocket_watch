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

interface PrivacyScreenProps {
  onClose?: () => void;
}

const PrivacyScreen = ({ onClose }: PrivacyScreenProps) => {
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
            <Text style={styles.title}>Privacy Policy</Text>
            
            <Text style={styles.sectionTitle}>Privacy and Protection of Proprietary Business Information</Text>
            <Text style={styles.text}>
              Our Privacy Policy governs the collection, use, and disclosure of your personal information. By using the App, you consent to be bound by these Terms.
            </Text>

            <Text style={styles.sectionTitle}>Proprietary Data from Unauthorized Access</Text>
            <Text style={styles.text}>
              Restrictions, disclosure or circumvention. However, we cannot guarantee the security of Proprietary Data from unauthorized access, with various online services, the internet or of electronic storage in 100% secure.
            </Text>

            <Text style={styles.sectionTitle}>Data Security Responsibilities</Text>
            <Text style={styles.text}>
              It is your responsibility to regularly back up your Proprietary Data. Any failure on your part with respect to such back up duties is not an obligation of cloud-computing service offers offered by major cloud-computing providers and protection measures for proprietary business data stored with private cloud-computing service providers from major cloud providers.
            </Text>

            <Text style={styles.sectionTitle}>Industry-Standard Security Measures</Text>
            <Text style={styles.text}>
              We employ industry-standard security measures to protect your account, data information and online transactions. For the employment of the security services offered by major cloud-computing providers, which may offer features such as encryption, access controls, restrictions, and API that may restrict the operation to the internet or electronic storage in 100% secure.
            </Text>

            <Text style={styles.sectionTitle}>Protection Measures for Enterprise Resources Planning Systems</Text>
            <Text style={styles.text}>
              We implement industry-standard security and encryption techniques to provide protection for Proprietary Data from unauthorized access, disclosure or circumvention. However, due to the inherent risks associated with internet and electronic storage, we cannot guarantee 100% security.
            </Text>

            <Text style={styles.sectionTitle}>Microsoft Azure and Cloud Security Services</Text>
            <Text style={styles.text}>
              Our provides the services from the App for the latest backup and disaster recovery. Azure Backup, and also Azure Site Recovery for fast backup on the latest cloud features and access controls.
            </Text>

            <Text style={styles.sectionTitle}>Data Protection and Cloud-Hosted Databases</Text>
            <Text style={styles.text}>
              Cloud-hosting service provides you with third-party Application data and information collected by our service. You acknowledge and agree that the Company will employ the cloud-hosted vendor's confidentiality data and provision of all security and integrity of such service-related data management.
            </Text>

            <Text style={styles.sectionTitle}>Security Measures and Cloud Services</Text>
            <Text style={styles.text}>
              Cloud-computing service by reputable cloud-computing providers to enhance the protection of your data. You acknowledge and agree that the Company will employ the cloud-hosted provider's performance and integrity of such service-related protection.
            </Text>

            <Text style={styles.sectionTitle}>Data Storage and Protection</Text>
            <Text style={styles.text}>
              We strive to ensure the security and integrity of your Proprietary Data with the App and to ensure the protection of your confidential information and personal data. You acknowledge and agree that the Company will employ the cloud-hosted provider's services with features such as encryption, access controls, restrictions, and API with the ability to restrict the operation to the internet or electronic storage in 100% secure.
            </Text>

            <Text style={styles.sectionTitle}>Service Level Agreements</Text>
            <Text style={styles.text}>
              We employ Google Cloud Storage as the primary cloud-computing service for data storage, Amazon Cloud for long-term archival and backup and backups.
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

export default PrivacyScreen;
