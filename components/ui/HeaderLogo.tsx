import React from 'react';
import { View, Text, Image, StyleSheet } from 'react-native';

const HeaderLogo = () => {
  return (
    <View style={styles.pocketwatchRow}>
      <Text style={styles.pocketwatchText}>P O C K E T W </Text>
      <Image 
        source={require('../assets/logo.png')} 
        style={styles.triangleA}
        resizeMode="contain"
      />
      <Text style={styles.pocketwatchText}> T C H</Text>
    </View>
  );
};

const styles = StyleSheet.create({
  pocketwatchRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
  },
  pocketwatchText: {
    color: '#FFFFFF',
    fontSize: 20,
    fontWeight: 'bold',
    letterSpacing: 2, // Added a little spacing to match the design better
  },
  triangleA: {
    width: 20,
    height: 20,
    marginHorizontal: -2, 
  },
});

export default HeaderLogo;