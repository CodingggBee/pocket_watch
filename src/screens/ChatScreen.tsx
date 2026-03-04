import React, { useState } from 'react';
import { 
  View, 
  Text, 
  StyleSheet, 
  ImageBackground, 
  SafeAreaView,
  TextInput,
  KeyboardAvoidingView,
  Platform,
  Image,
  TouchableOpacity,
  ScrollView
} from 'react-native';
import HeaderLogo from '../components/HeaderLogo';

interface Message {
  id: string;
  text: string;
  sender: 'user' | 'ai';
}

const ChatScreen = ({ onClose, onNext }: { onClose: () => void; onNext?: () => void }) => {
  const [question, setQuestion] = useState('');
  const [messages, setMessages] = useState<Message[]>([]);
  const [isThinking, setIsThinking] = useState(false);

  const handleSend = () => {
    if (question.trim()) {
      const newMessage: Message = {
        id: Date.now().toString(),
        text: question,
        sender: 'user',
      };
      setMessages([...messages, newMessage]);
      setQuestion('');
      // TODO: Send to AI and get response
    }
  };

  return (
    <SafeAreaView style={styles.safeArea}>
      <ImageBackground 
        source={require('../assets/splash_bg.png')} 
        style={styles.background}
        resizeMode="cover"
      >
        <KeyboardAvoidingView 
          behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
          style={styles.container}
        >
          {/* Top Section: Logo */}
          <View style={styles.topSection}>
            <HeaderLogo width={375} height={48} />
          </View>

          {/* Triangle Icon */}
          <View style={styles.triangleIconContainer}>
            <Image
              source={require('../assets/triangle_icon.png')}
              style={styles.triangleIcon}
              resizeMode="contain"
            />
          </View>

          {/* Middle Section: Messages or Instructions */}
          <View style={styles.middleSection}>
            {messages.length === 0 ? (
              <Text style={styles.instructionText}>
                Start typing to ask me a question. You could say "How do I setup a station?" or "How do I add a user?".
              </Text>
            ) : (
              <ScrollView 
                style={styles.messagesContainer}
                contentContainerStyle={styles.messagesContent}
              >
                {messages.map((msg) => (
                  <View 
                    key={msg.id} 
                    style={[
                      styles.messageBubbleContainer,
                      msg.sender === 'user' ? styles.userMessageContainer : styles.aiMessageContainer
                    ]}
                  >
                    <View style={[
                      styles.messageBubble,
                      msg.sender === 'user' ? styles.userBubble : styles.aiBubble
                    ]}>
                      <Text style={[
                        styles.messageText,
                        msg.sender === 'user' ? styles.userMessageText : styles.aiMessageText
                      ]}>
                        {msg.text}
                      </Text>
                    </View>
                  </View>
                ))}
                {isThinking && (
                  <View style={[styles.messageBubbleContainer, styles.aiMessageContainer]}>
                    <View style={styles.thinkingContainer}>
                      <Image
                        source={require('../assets/thinking_logo.png')}
                        style={styles.thinkingLogo}
                        resizeMode="contain"
                      />
                    </View>
                  </View>
                )}
              </ScrollView>
            )}
          </View>

          {/* Input Field with Send Button */}
          <View style={styles.inputContainer}>
            <TextInput
              style={styles.textInput}
              placeholder="Type your question"
              placeholderTextColor="#999"
              value={question}
              onChangeText={setQuestion}
              onSubmitEditing={handleSend}
              returnKeyType="send"
            />
            {question.trim().length > 0 && (
              <TouchableOpacity 
                style={styles.sendButton}
                onPress={handleSend}
              >
                <Image
                  source={require('../assets/send_icon.png')}
                  style={styles.sendIcon}
                  resizeMode="contain"
                />
              </TouchableOpacity>
            )}
          </View>

          {/* Next Button - Shows when no messages sent */}
          {messages.length === 0 && (
            <View style={styles.nextButtonContainer}>
              <TouchableOpacity 
                style={styles.nextButton}
                onPress={onNext}
              >
                <Text style={styles.nextButtonText}>Thanks, now take me to setup</Text>
              </TouchableOpacity>
            </View>
          )}

          {/* Microphone Icon */}
          {/* <View style={styles.micContainer}>
            <TouchableOpacity>
              <Text style={styles.micIcon}>🎤</Text>
            </TouchableOpacity>
          </View> */}
        </KeyboardAvoidingView>
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
  },
  topSection: {
    marginTop: 20,
    alignItems: 'center',
  },
  triangleIconContainer: {
    marginTop: 40,
    marginBottom: 40,
    alignItems: 'center',
  },
  triangleIcon: {
    width: 56,
    height: 56,
  },
  middleSection: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    paddingHorizontal: 20,
  },
  instructionText: {
    color: '#E7E7E7',
    fontSize: 14,
    lineHeight: 20,
    fontWeight: '400',
    textAlign: 'left',
  },
  messagesContainer: {
    flex: 1,
    width: '100%',
  },
  messagesContent: {
    paddingHorizontal: 20,
    paddingVertical: 10,
  },
  messageBubbleContainer: {
    marginBottom: 16,
  },
  aiMessageContainer: {
    alignItems: 'flex-start',
  },
  userMessageContainer: {
    alignItems: 'flex-end',
  },
  messageBubble: {
    paddingHorizontal: 16,
    paddingVertical: 12,
    maxWidth: '85%',
  },
  aiBubble: {
    backgroundColor: 'transparent',
    borderTopLeftRadius: 16,
    borderTopRightRadius: 16,
    borderBottomLeftRadius: 0,
    borderBottomRightRadius: 16,
  },
  userBubble: {
    backgroundColor: '#E7E7E7',
    borderTopLeftRadius: 16,
    borderTopRightRadius: 16,
    borderBottomLeftRadius: 16,
    borderBottomRightRadius: 0,
  },
  messageText: {
    fontSize: 14,
    lineHeight: 20,
  },
  aiMessageText: {
    color: '#E7E7E7',
  },
  userMessageText: {
    color: '#1a1a1a',
  },
  inputContainer: {
    marginBottom: 20,
    position: 'relative',
  },
  textInput: {
    backgroundColor: '#444444',
    borderRadius: 20,
    paddingHorizontal: 16,
    paddingVertical: 12,
    paddingRight: 50,
    color: '#E7E7E7',
    fontSize: 14,
  },
  sendButton: {
    position: 'absolute',
    right: 8,
    top: 8,
    width: 28,
    height: 28,
    justifyContent: 'center',
    alignItems: 'center',
    borderRadius: 32,
    gap: 10,
  },
  sendIcon: {
    width: 24,
    height: 24,
  },
  thinkingContainer: {
    paddingHorizontal: 16,
    paddingVertical: 12,
  },
  thinkingLogo: {
    width: 40,
    height: 40,
  },
  nextButtonContainer: {
    paddingHorizontal: 20,
    paddingBottom: 30,
    alignItems: 'center',
  },
  nextButton: {
    borderWidth: 2,
    borderColor: '#E84545',
    borderRadius: 20,
    paddingHorizontal: 24,
    paddingVertical: 12,
    width: '100%',
    alignItems: 'center',
    justifyContent: 'center',
  },
  nextButtonText: {
    color: '#E84545',
    fontSize: 14,
    fontWeight: '600',
  },
  micContainer: {
    alignItems: 'flex-end',
    paddingRight: 10,
    paddingBottom: 20,
  },
  micIcon: {
    fontSize: 28,
  },
});

export default ChatScreen;
