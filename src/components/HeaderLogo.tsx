import React from 'react';
import { View, Image, StyleSheet } from 'react-native';

const HeaderLogo = ({ width = 280, height = 44 }: { width?: number; height?: number }) => {
  return (
    <View style={styles.container}>
      <Image 
        source={require('../assets/full_logo.png')} 
        style={[styles.logoImage, { width, height }]}
        resizeMode="contain"
      />
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    alignItems: 'center',
    justifyContent: 'center',
    width: '100%',
  },
  logoImage: {
    // Width and height are passed dynamically via props
  },
});

export default HeaderLogo;