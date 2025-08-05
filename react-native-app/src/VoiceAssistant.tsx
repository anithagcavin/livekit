import React, { useEffect, useState, useCallback } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  Alert,
  PermissionsAndroid,
  Platform,
} from 'react-native';
import {
  Room,
  RoomEvent,
  Track,
  LocalParticipant,
  RemoteParticipant,
  TrackPublication,
  DataPacket_Kind,
  ConnectionState,
} from 'livekit-client';
import {
  LiveKitRoom,
  useRoom,
  useTracks,
  useParticipants,
  AudioSession,
} from '@livekit/react-native';

const LIVEKIT_URL = 'ws://localhost:7880';
const API_KEY = 'APIyourkey';
const API_SECRET = 'yoursecret';

interface VoiceAssistantProps {
  roomName?: string;
  userIdentity?: string;
}

export const VoiceAssistant: React.FC<VoiceAssistantProps> = ({
  roomName = 'voice-assistant-room',
  userIdentity = 'user-' + Math.random().toString(36).substr(2, 9),
}) => {
  const [token, setToken] = useState<string>('');
  const [isConnected, setIsConnected] = useState(false);
  const [isMuted, setIsMuted] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [messages, setMessages] = useState<string[]>([]);

  // Generate access token (in production, this should be done on your backend)
  const generateToken = useCallback(async () => {
    try {
      // In a real app, call your backend to generate the token
      // For demo purposes, using a simple token generation
      const response = await fetch('http://localhost:3001/api/token', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          room: roomName,
          identity: userIdentity,
        }),
      });
      
      if (response.ok) {
        const data = await response.json();
        setToken(data.token);
      } else {
        throw new Error('Failed to get token');
      }
    } catch (error) {
      console.error('Error generating token:', error);
      Alert.alert('Error', 'Failed to generate access token');
    }
  }, [roomName, userIdentity]);

  // Request microphone permissions
  const requestMicrophonePermission = async () => {
    if (Platform.OS === 'android') {
      try {
        const granted = await PermissionsAndroid.request(
          PermissionsAndroid.PERMISSIONS.RECORD_AUDIO,
        );
        return granted === PermissionsAndroid.RESULTS.GRANTED;
      } catch (err) {
        console.warn(err);
        return false;
      }
    }
    return true;
  };

  useEffect(() => {
    const setup = async () => {
      const hasPermission = await requestMicrophonePermission();
      if (hasPermission) {
        await generateToken();
      } else {
        Alert.alert('Permission Required', 'Microphone permission is required for voice chat');
      }
    };
    
    setup();
  }, [generateToken]);

  if (!token) {
    return (
      <View style={styles.container}>
        <Text style={styles.loadingText}>Loading...</Text>
      </View>
    );
  }

  return (
    <LiveKitRoom
      serverUrl={LIVEKIT_URL}
      token={token}
      connect={true}
      options={{
        adaptiveStream: true,
        dynacast: true,
      }}
      audio={true}
      video={false}
    >
      <VoiceAssistantRoom 
        isConnected={isConnected}
        setIsConnected={setIsConnected}
        isMuted={isMuted}
        setIsMuted={setIsMuted}
        isRecording={isRecording}
        setIsRecording={setIsRecording}
        messages={messages}
        setMessages={setMessages}
      />
    </LiveKitRoom>
  );
};

interface VoiceAssistantRoomProps {
  isConnected: boolean;
  setIsConnected: (connected: boolean) => void;
  isMuted: boolean;
  setIsMuted: (muted: boolean) => void;
  isRecording: boolean;
  setIsRecording: (recording: boolean) => void;
  messages: string[];
  setMessages: (messages: string[]) => void;
}

const VoiceAssistantRoom: React.FC<VoiceAssistantRoomProps> = ({
  isConnected,
  setIsConnected,
  isMuted,
  setIsMuted,
  isRecording,
  setIsRecording,
  messages,
  setMessages,
}) => {
  const room = useRoom();
  const participants = useParticipants();
  const tracks = useTracks([Track.Source.Microphone]);

  useEffect(() => {
    if (!room) return;

    const handleConnectionStateChange = (state: ConnectionState) => {
      console.log('Connection state changed:', state);
      setIsConnected(state === ConnectionState.Connected);
    };

    const handleDataReceived = (payload: Uint8Array, participant?: RemoteParticipant) => {
      try {
        const message = JSON.parse(new TextDecoder().decode(payload));
        console.log('Data received:', message);
        
        if (message.type === 'response') {
          setMessages(prev => [...prev, `Assistant: ${message.message}`]);
        }
      } catch (error) {
        console.error('Error parsing data message:', error);
      }
    };

    const handleTrackSubscribed = (
      track: Track,
      publication: TrackPublication,
      participant: RemoteParticipant,
    ) => {
      console.log('Track subscribed:', track.kind, participant.identity);
      
      if (track.kind === Track.Kind.Audio) {
        console.log('Audio track from assistant received');
        // The audio will automatically play through the device speakers
      }
    };

    // Set up event listeners
    room.on(RoomEvent.ConnectionStateChanged, handleConnectionStateChange);
    room.on(RoomEvent.DataReceived, handleDataReceived);
    room.on(RoomEvent.TrackSubscribed, handleTrackSubscribed);

    // Initial connection state
    setIsConnected(room.state === ConnectionState.Connected);

    // Cleanup
    return () => {
      room.off(RoomEvent.ConnectionStateChanged, handleConnectionStateChange);
      room.off(RoomEvent.DataReceived, handleDataReceived);
      room.off(RoomEvent.TrackSubscribed, handleTrackSubscribed);
    };
  }, [room, setIsConnected, setMessages]);

  const toggleMute = useCallback(async () => {
    if (room?.localParticipant) {
      const audioTrack = room.localParticipant.getTrackPublication(Track.Source.Microphone);
      if (audioTrack) {
        await audioTrack.setMuted(!isMuted);
        setIsMuted(!isMuted);
      }
    }
  }, [room, isMuted, setIsMuted]);

  const startRecording = useCallback(async () => {
    if (room?.localParticipant && !isRecording) {
      try {
        // Enable microphone
        await room.localParticipant.setMicrophoneEnabled(true);
        setIsRecording(true);
        setIsMuted(false);
        
        console.log('Started recording and publishing audio');
        
        // Send a data message to indicate recording started
        const message = {
          type: 'recording_started',
          timestamp: Date.now(),
        };
        
        await room.localParticipant.publishData(
          new TextEncoder().encode(JSON.stringify(message)),
          DataPacket_Kind.RELIABLE,
        );
        
      } catch (error) {
        console.error('Error starting recording:', error);
        Alert.alert('Error', 'Failed to start recording');
      }
    }
  }, [room, isRecording, setIsRecording, setIsMuted]);

  const stopRecording = useCallback(async () => {
    if (room?.localParticipant && isRecording) {
      try {
        // Disable microphone
        await room.localParticipant.setMicrophoneEnabled(false);
        setIsRecording(false);
        
        console.log('Stopped recording');
        
        // Send a data message to indicate recording stopped
        const message = {
          type: 'recording_stopped',
          timestamp: Date.now(),
        };
        
        await room.localParticipant.publishData(
          new TextEncoder().encode(JSON.stringify(message)),
          DataPacket_Kind.RELIABLE,
        );
        
      } catch (error) {
        console.error('Error stopping recording:', error);
        Alert.alert('Error', 'Failed to stop recording');
      }
    }
  }, [room, isRecording, setIsRecording]);

  const sendTextMessage = useCallback(async (text: string) => {
    if (room?.localParticipant) {
      try {
        const message = {
          type: 'text_message',
          message: text,
          timestamp: Date.now(),
        };
        
        await room.localParticipant.publishData(
          new TextEncoder().encode(JSON.stringify(message)),
          DataPacket_Kind.RELIABLE,
        );
        
        setMessages(prev => [...prev, `You: ${text}`]);
        
      } catch (error) {
        console.error('Error sending text message:', error);
      }
    }
  }, [room, setMessages]);

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.title}>Voice Assistant</Text>
        <View style={[styles.statusIndicator, { backgroundColor: isConnected ? '#4CAF50' : '#F44336' }]} />
        <Text style={styles.statusText}>
          {isConnected ? 'Connected' : 'Disconnected'}
        </Text>
      </View>

      <View style={styles.messagesContainer}>
        {messages.map((message, index) => (
          <Text key={index} style={styles.message}>
            {message}
          </Text>
        ))}
      </View>

      <View style={styles.controlsContainer}>
        <TouchableOpacity
          style={[
            styles.recordButton,
            { backgroundColor: isRecording ? '#F44336' : '#4CAF50' }
          ]}
          onPress={isRecording ? stopRecording : startRecording}
          disabled={!isConnected}
        >
          <Text style={styles.buttonText}>
            {isRecording ? 'Stop Recording' : 'Start Recording'}
          </Text>
        </TouchableOpacity>

        <TouchableOpacity
          style={[styles.muteButton, { backgroundColor: isMuted ? '#F44336' : '#2196F3' }]}
          onPress={toggleMute}
          disabled={!isConnected}
        >
          <Text style={styles.buttonText}>
            {isMuted ? 'Unmute' : 'Mute'}
          </Text>
        </TouchableOpacity>

        <TouchableOpacity
          style={styles.testButton}
          onPress={() => sendTextMessage('Hello, assistant!')}
          disabled={!isConnected}
        >
          <Text style={styles.buttonText}>Send Test Message</Text>
        </TouchableOpacity>
      </View>

      <View style={styles.infoContainer}>
        <Text style={styles.infoText}>Participants: {participants.length}</Text>
        <Text style={styles.infoText}>Audio Tracks: {tracks.length}</Text>
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f5f5',
    padding: 20,
  },
  loadingText: {
    fontSize: 18,
    textAlign: 'center',
    marginTop: 50,
  },
  header: {
    alignItems: 'center',
    marginBottom: 30,
  },
  title: {
    fontSize: 24,
    fontWeight: 'bold',
    marginBottom: 10,
  },
  statusIndicator: {
    width: 12,
    height: 12,
    borderRadius: 6,
    marginBottom: 5,
  },
  statusText: {
    fontSize: 16,
    fontWeight: '500',
  },
  messagesContainer: {
    flex: 1,
    backgroundColor: '#fff',
    borderRadius: 8,
    padding: 15,
    marginBottom: 20,
  },
  message: {
    fontSize: 14,
    marginBottom: 8,
    paddingVertical: 4,
  },
  controlsContainer: {
    gap: 15,
  },
  recordButton: {
    padding: 15,
    borderRadius: 8,
    alignItems: 'center',
  },
  muteButton: {
    padding: 15,
    borderRadius: 8,
    alignItems: 'center',
  },
  testButton: {
    padding: 15,
    borderRadius: 8,
    alignItems: 'center',
    backgroundColor: '#FF9800',
  },
  buttonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
  },
  infoContainer: {
    marginTop: 20,
    padding: 15,
    backgroundColor: '#fff',
    borderRadius: 8,
  },
  infoText: {
    fontSize: 14,
    marginBottom: 5,
  },
});

export default VoiceAssistant;