const express = require('express');
const cors = require('cors');
const { AccessToken } = require('livekit-server-sdk');
require('dotenv').config();

const app = express();
const port = process.env.PORT || 3001;

// Middleware
app.use(cors());
app.use(express.json());

// LiveKit configuration
const LIVEKIT_API_KEY = process.env.LIVEKIT_API_KEY || 'APIyourkey';
const LIVEKIT_API_SECRET = process.env.LIVEKIT_API_SECRET || 'yoursecret';

// Generate token endpoint
app.post('/api/token', (req, res) => {
  try {
    const { room, identity } = req.body;
    
    if (!room || !identity) {
      return res.status(400).json({ 
        error: 'Room and identity are required' 
      });
    }

    console.log(`Generating token for room: ${room}, identity: ${identity}`);

    // Create access token
    const token = new AccessToken(LIVEKIT_API_KEY, LIVEKIT_API_SECRET, {
      identity: identity,
      ttl: '24h', // Token valid for 24 hours
    });

    // Grant permissions
    token.addGrant({
      room: room,
      roomJoin: true,
      canPublish: true,
      canSubscribe: true,
      canPublishData: true,
      roomCreate: true,
    });

    // Generate JWT token
    const jwt = token.toJwt();
    
    console.log(`Token generated successfully for ${identity} in room ${room}`);
    
    res.json({ 
      token: jwt,
      identity: identity,
      room: room
    });

  } catch (error) {
    console.error('Error generating token:', error);
    res.status(500).json({ 
      error: 'Failed to generate token',
      details: error.message 
    });
  }
});

// Health check endpoint
app.get('/health', (req, res) => {
  res.json({ 
    status: 'ok', 
    service: 'livekit-token-server',
    timestamp: new Date().toISOString()
  });
});

// Start server
app.listen(port, () => {
  console.log(`Token server running on port ${port}`);
  console.log(`Health check: http://localhost:${port}/health`);
  console.log(`Generate token: POST http://localhost:${port}/api/token`);
  console.log(`LIVEKIT_API_KEY: ${LIVEKIT_API_KEY}`);
});