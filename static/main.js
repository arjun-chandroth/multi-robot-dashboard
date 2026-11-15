// Global variables
let socket = io();
let fpvRecording = false;
let rearRecording = false;
let buttonActive = false;
let accelData = [];
const maxDataPoints = 50;
let plot = null;
let lidarCanvas = document.getElementById('lidar-canvas');
let lidarCtx = lidarCanvas.getContext('2d');
let lastLidarUpdate = 0;
let frameCount = 0;
let lastFpsUpdate = 0;
let currentFps = 0;
let map = null;
let marker = null;
let gpsLastSeenAt = 0;
let lidarLastSeenAt = 0;
const CONNECTION_STALE_MS = 7000;
const SENSOR_ACTIVITY_STALE_MS = 15000;
let sensorEnabledState = {
    touch: false,
    tilt: false,
    rain: false,
    gas: false,
    flame: false,
    impact: false,
    sound: false,
    pir: false,
    radar: false,
};
const SENSOR_KEYS = ['touch', 'tilt', 'rain', 'gas', 'flame', 'impact', 'sound', 'pir', 'radar'];
const SENSOR_COUNT_FIELDS = {
    touch: 'touch_count',
    tilt: 'tilt_count',
    rain: 'rain_count',
    gas: 'gas_count',
    flame: 'flame_count',
    impact: 'impact_count',
    sound: 'sound_count',
    pir: 'pir_count',
    radar: 'radar_count'
};
const SENSOR_DETECTED_FIELDS = {
    touch: 'touch_detected',
    tilt: 'tilt_detected',
    rain: 'rain_detected',
    gas: 'gas_detected',
    flame: 'flame_detected',
    impact: 'impact_detected',
    sound: 'sound_detected',
    pir: 'pir_detected',
    radar: 'radar_detected'
};
let sensorActivityState = {};

function resetSensorConnectionState() {
    const now = Date.now();
    sensorActivityState = {};
    SENSOR_KEYS.forEach((key) => {
        sensorActivityState[key] = {
            lastCount: null,
            lastActivityAt: 0,
            connected: false,
            initializedAt: now
        };
    });
}

function updateSensorConnectionFromPayload(data) {
    const now = Date.now();
    SENSOR_KEYS.forEach((key) => {
        const countField = SENSOR_COUNT_FIELDS[key];
        const detectedField = SENSOR_DETECTED_FIELDS[key];
        if (!(countField in data) || !(detectedField in data)) return;

        const countValue = Number(data[countField]) || 0;
        const detectedValue = Boolean(data[detectedField]);
        const state = sensorActivityState[key];

        if (state.lastCount === null) {
            state.lastCount = countValue;
        }

        if (countValue !== state.lastCount || detectedValue) {
            state.lastActivityAt = now;
        }

        state.lastCount = countValue;
        state.connected = state.lastActivityAt > 0 && (now - state.lastActivityAt) <= SENSOR_ACTIVITY_STALE_MS;
    });
}

function isSensorConnected(key) {
    const state = sensorActivityState[key];
    return Boolean(state && state.connected);
}

resetSensorConnectionState();






let aiStreamingMsg = null;
let currentAIMessage = null;





// Initialize all components when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Initialize components
    initButtonControls();
    initAccelPlot();
    initMap();
    initChat();
    
    // Debug: Log initialization
    console.log("DOM fully loaded and parsed");
    
    // Connection status elements
    const connectionStatus = document.getElementById('connection-status');
    const socketStatus = document.getElementById('socket-status');

    // Timer implementation
    const timerElement = document.getElementById('refresh-timer');
    if (timerElement) {
        let seconds = 30;
        timerElement.textContent = seconds;

        const timerInterval = setInterval(() => {
            seconds--;
            console.log('Timer tick:', seconds);
            timerElement.textContent = seconds;
            
            if (seconds <= 0) {
                clearInterval(timerInterval);
                console.log('Reloading page...');
                window.location.reload();
            }
        }, 1000);

        // Reset timer on user activity
        const resetTimer = () => {
            seconds = 30;
            timerElement.textContent = seconds;
        };
        
        document.addEventListener('mousemove', resetTimer);
        document.addEventListener('keydown', resetTimer);
        document.addEventListener('click', resetTimer);
    } else {
        console.error('Could not find timer element!');
    }

    // LIDAR canvas setup
    resizeLidarCanvas();
    window.addEventListener('resize', () => {
        resizeLidarCanvas();
        if (plot) {
            Plotly.relayout('accel-plot', {
                'width': document.getElementById('accel-plot').offsetWidth,
                'height': document.getElementById('accel-plot').offsetHeight
            });
        }
    });
    
    // Set initial connection status
    updateConnectionStatus(false, false, false);
    updateStatusIndicator('battery-status', false);
    updateStatusIndicator('wifi-status', false);
    updateStatusIndicator('gps-status', false);
    updateStatusIndicator('control-mode', false);
    // Initialize LIDAR canvas
    resizeLidarCanvas();
    window.addEventListener('resize', resizeLidarCanvas);
    
    // Start with a blank LIDAR canvas
    lidarCtx.fillStyle = 'black';
    lidarCtx.fillRect(0, 0, lidarCanvas.width, lidarCanvas.height);
    lidarCtx.fillStyle = 'white';
    lidarCtx.textAlign = 'center';
    lidarCtx.fillText('Waiting for LIDAR data...', lidarCanvas.width/2, lidarCanvas.height/2);

    // Socket.IO connection monitoring
    socket.on('connect', () => {
        console.log("Socket.IO connected");
        if (socketStatus) {
            socketStatus.className = 'status-dot connected';
        }
        showStatus("Connected to server", true);
        
        // Enable chat if in AI mode
        const controlMode = document.getElementById('control-mode');
        if (controlMode && controlMode.getAttribute('data-tooltip').includes('AI')) {
            const chatInput = document.getElementById('chat-input');
            const sendButton = document.getElementById('send-button');
            if (chatInput) chatInput.disabled = false;
            if (sendButton) sendButton.disabled = false;
            if (chatInput) chatInput.placeholder = "Type your message...";
        }
    });

    socket.on('disconnect', () => {
        console.log("Socket.IO disconnected");
        if (socketStatus) {
            socketStatus.className = 'status-dot disconnected';
        }
        showStatus("Disconnected from server", false);
        
        // Disable chat interface
        const chatInput = document.getElementById('chat-input');
        const sendButton = document.getElementById('send-button');
        if (chatInput) chatInput.disabled = true;
        if (sendButton) sendButton.disabled = true;
        if (chatInput) chatInput.placeholder = "Disconnected - refresh page";

        gpsLastSeenAt = 0;
        lidarLastSeenAt = 0;
        updateStatusIndicator('arduino-status', false, 'Disconnected');
        updateStatusIndicator('camera-status', false, 'Disconnected');
        updateStatusIndicator('rear-camera-status', false, 'Disconnected');
        updateStatusIndicator('lidar-status', false, 'Disconnected');
        updateStatusIndicator('gps-status', false, 'Disconnected');
        updateStatusIndicator('wifi-status', false, 'Disconnected');
        updateStatusIndicator('battery-status', false, 'Disconnected');
        resetSensorConnectionState();
        clearSensorReadings();
    });

    socket.on('connect_error', (error) => {
        console.error("Socket.IO connection error:", error);
        if (socketStatus) {
            socketStatus.className = 'status-dot disconnected';
        }
        showStatus("Connection error: " + error.message, false);
    });

    // Control mode updates
    socket.on('control_mode_update', function(data) {
        console.log("Control mode updated to:", data.mode);
        syncControlModeUI(data.mode);
        syncChatForMode(data.mode);
    });

    // Add CSS for status animations if not already present
    if (!document.getElementById('status-animations')) {
        const style = document.createElement('style');
        style.id = 'status-animations';
        style.textContent = `
            @keyframes fadeInOut {
                0% { opacity: 0; transform: translateY(10px); }
                10% { opacity: 1; transform: translateY(0); }
                90% { opacity: 1; transform: translateY(0); }
                100% { opacity: 0; transform: translateY(-10px); }
            }
            .thinking {
                opacity: 0.7;
                font-style: italic;
            }
            .status-dot {
                width: 10px;
                height: 10px;
                border-radius: 50%;
                display: inline-block;
                margin-right: 5px;
            }
            .status-dot.connected {
                background-color: #2ecc71;
            }
            .status-dot.disconnected {
                background-color: #e74c3c;
            }
            .chat-input input:disabled {
                background-color: #f0f0f0;
                cursor: not-allowed;
            }
            #send-button:disabled {
                opacity: 0.5;
                cursor: not-allowed;
            }
        `;
        document.head.appendChild(style);
    }
    
    // Debug: Log initial state
    console.log("Initialization complete. Current state:", {
        socketConnected: socket.connected,
        controlMode: document.getElementById('control-mode')?.getAttribute('data-tooltip'),
        chatEnabled: !document.getElementById('chat-input')?.disabled
    });
});

// Status indicator functions
function updateStatusIndicator(id, isConnected, statusText = null) {
    const element = document.getElementById(id);
    if (!element) return;

    const connected = Boolean(isConnected);
    element.classList.toggle('connected', connected);
    if (statusText) {
        const currentTooltip = element.getAttribute('data-tooltip') || id;
        const label = currentTooltip.includes(':') ? currentTooltip.split(':')[0] : currentTooltip;
        element.setAttribute('data-tooltip', `${label}: ${statusText}`);
    }
}

function updateConnectionStatus(arduinoConnected, cameraConnected, rearCameraConnected) {
    updateStatusIndicator('arduino-status', arduinoConnected,
        arduinoConnected ? 'Connected' : 'Disconnected');
    updateStatusIndicator('camera-status', cameraConnected,
        cameraConnected ? 'Connected' : 'Disconnected');
    updateStatusIndicator('rear-camera-status', rearCameraConnected || false,
        rearCameraConnected ? 'Connected' : 'Disconnected');
}

function updateWiFiStatus(strength) {
    const wifi = document.getElementById('wifi-status');
    if (!wifi) return;
    const icon = wifi.querySelector('i');
    const numericStrength = Number(strength);
    
    let statusText = 'Disconnected';
    if (Number.isFinite(numericStrength) && numericStrength > 0) {
        statusText = `${numericStrength}%`;
        wifi.classList.add('connected');
        
        if (numericStrength > 75) icon.className = 'bx bx-wifi';
        else if (numericStrength > 50) icon.className = 'bx bx-wifi-2';
        else if (numericStrength > 25) icon.className = 'bx bx-wifi-1';
        else icon.className = 'bx bx-wifi-0';
    } else {
        wifi.classList.remove('connected');
        icon.className = 'bx bx-wifi-off';
    }
    wifi.setAttribute('data-tooltip', `WiFi: ${statusText}`);
}

function updateBatteryStatus(level, isPlugged) {
    const battery = document.getElementById('battery-status');
    if (!battery) return;
    const icon = battery.querySelector('i');
    const numericLevel = Number(level);
    
    battery.classList.toggle('battery-plugged', isPlugged);
    battery.classList.toggle('connected', isPlugged || (Number.isFinite(numericLevel) && numericLevel > 20));
    
    if (isPlugged) {
        icon.className = 'bx bx-battery-charging';
    } else if (Number.isFinite(numericLevel) && numericLevel > 75) {
        icon.className = 'bx bx-battery-full';
    } else if (Number.isFinite(numericLevel) && numericLevel > 50) {
        icon.className = 'bx bx-battery';
    } else if (Number.isFinite(numericLevel) && numericLevel > 25) {
        icon.className = 'bx bx-battery-low';
    } else {
        icon.className = 'bx bx-battery-empty';
    }
    const displayLevel = Number.isFinite(numericLevel) ? `${numericLevel}%` : 'Disconnected';
    battery.setAttribute('data-tooltip', `Battery: ${displayLevel}${isPlugged ? ' (Charging)' : ''}`);
}












function updateRefreshTimer() {
    const timerElement = document.getElementById('refresh-timer');
    console.log('Updating timer:', refreshTimer); // Debug log
    
    if (timerElement) {
        timerElement.textContent = refreshTimer;
        
        if (refreshTimer <= 0) {
            clearInterval(refreshInterval);
            setTimeout(() => {
                window.location.reload();
            }, 1000);
        }
        refreshTimer--; // Decrement after update
    }
}





function updateControlMode(mode) {
    const controlMode = document.getElementById('control-mode');
    if (!controlMode) return;

    const normalizedMode = normalizeControlMode(mode);
    const modeLabel = getControlModeLabel(normalizedMode);
    controlMode.textContent = `MODE: ${modeLabel}`;

    // Always green — robot is always in some active mode
    controlMode.classList.add('connected');
    controlMode.setAttribute('data-tooltip', `Control Mode: ${modeLabel}`);
}

function normalizeControlMode(mode) {
    const normalized = (mode || 'BUTTONS').toString().toUpperCase();
    if (normalized === 'MANUAL') return 'BUTTONS';
    if (normalized === 'AUTONOMOUS') return 'OBSTACLE';
    return normalized;
}

function getControlModeLabel(mode) {
    const modeLabels = {
        BUTTONS: 'Manual',
        JOYSTICK: 'ROV',
        OBSTACLE: 'Autonomous',
        AI: 'AI',
        JOYMODE: 'Joy Mode'
    };
    return modeLabels[mode] || mode;
}

function setActiveModeButton(mode) {
    const normalizedMode = normalizeControlMode(mode);
    document.querySelectorAll('.mode-btn').forEach(btn => {
        btn.classList.remove('active-mode', 'active');
    });

    const activeBtn = document.querySelector(`.mode-btn[data-mode="${normalizedMode}"]`);
    if (activeBtn) activeBtn.classList.add('active-mode');
}

function syncChatForMode(mode) {
    const normalizedMode = normalizeControlMode(mode);
    const chatInput = document.getElementById('chat-input');
    const sendButton = document.getElementById('send-button');
    const messages = document.getElementById('chat-messages');

    if (normalizedMode === 'AI') {
        if (chatInput) {
            chatInput.disabled = false;
            chatInput.placeholder = 'Type your message to the AI...';
            setTimeout(() => chatInput.focus(), 100);
        }
        if (sendButton) sendButton.disabled = false;

        if (messages && messages.children.length <= 1) {
            const welcomeMsg = document.createElement('div');
            welcomeMsg.className = 'ai-message';
            welcomeMsg.innerHTML = `<strong>AI Assistant:</strong> AI mode activated! How can I assist you with the robot controls?`;
            messages.appendChild(welcomeMsg);
            messages.scrollTop = messages.scrollHeight;
        }
    } else {
        if (chatInput) {
            chatInput.disabled = true;
            chatInput.placeholder = 'Enable AI mode to chat';
        }
        if (sendButton) sendButton.disabled = true;
    }
}

function syncControlModeUI(mode) {
    const normalizedMode = normalizeControlMode(mode);
    updateControlMode(normalizedMode);
    setActiveModeButton(normalizedMode);
}

function clearSensorReadings() {
    const sensorValueIds = [
        'temperature', 'humidity', 'touch_count', 'tilt_count', 'system_temp', 'cpu_usage',
        'rain_count', 'gas_count', 'flame_count', 'impact_count', 'sound_count', 'pir_count',
        'radar_count', 'accel_x', 'accel_y', 'accel_z'
    ];
    const sensorStatusIds = [
        'touch_status', 'tilt_status', 'rain_status', 'gas_status', 'flame_status',
        'impact_status', 'sound_status', 'pir_status', 'radar_status'
    ];
    const sensorActiveClasses = [
        'touch-active', 'tilt-active', 'rain-active', 'gas-active', 'flame-active',
        'impact-active', 'sound-active', 'pir-active', 'radar-active'
    ];

    sensorValueIds.forEach((id) => {
        const element = document.getElementById(id);
        if (element) {
            element.textContent = id.startsWith('accel_') ? '0.00' : '0';
        }
    });

    sensorStatusIds.forEach((id) => {
        const element = document.getElementById(id);
        if (element) {
            element.textContent = 'Not Connected';
            element.classList.remove(...sensorActiveClasses);
        }
    });

    resetSensorConnectionState();
}

function updateSensorEnabledState(sensorEnabled = {}) {
    sensorEnabledState = {
        ...sensorEnabledState,
        ...sensorEnabled,
    };
}


function updateGpsStatus(lat, lon) {
    const gps = document.getElementById('gps-status');
    const icon = gps.querySelector('i');

    const connected = lat !== null && lon !== null;
    gps.classList.toggle('connected', connected);
    icon.className = connected ? 'bx bx-map' : 'bx bx-map-pin';
}

// Map functions - Static implementation with LPU default
function initMap() {
    if (typeof L !== 'undefined') {
        // Default coordinates (Kanyakumari, Tamil Nadu, India)
        const defaultCoords = [8.0883, 77.5384];
        
        // Create map centered at default location
        map = L.map('map').setView(defaultCoords, 16);
        
        // Add tile layer
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        }).addTo(map);
        
        // Create custom robot icon
        const robotIcon = L.icon({
            iconUrl: 'https://cdn-icons-png.flaticon.com/512/3142/3142026.png',
            iconSize: [32, 32],
            iconAnchor: [16, 16]
        });
        
        // Add default marker at LPU
        marker = L.marker(defaultCoords, {icon: robotIcon}).addTo(map);
        marker.bindPopup('Lovely Professional University, Punjab');
        
        // Add scale control
        L.control.scale().addTo(map);
        
        // Add position accuracy circle (will update with GPS data)
        L.circle(defaultCoords, {
            color: 'blue',
            fillColor: '#30f',
            fillOpacity: 0.2,
            radius: 10
        }).addTo(map);
        
        // Update connection status
        updateStatusIndicator('globe-status', true);
    }
}

// Recording functions
function toggleFpvRecording() {
    const btn = document.getElementById('fpv-record-btn');
    if (!fpvRecording) {
        // Start recording
        socket.emit('start_recording', { stream: 'fpv' });
    } else {
        stopFpvRecording();
    }
}

function pauseFpvRecording() {
    socket.emit('pause_recording', { stream: 'fpv' });
}

function stopFpvRecording() {
    socket.emit('stop_recording', { stream: 'fpv' });
}

function toggleRearRecording() {
    const btn = document.getElementById('rear-record-btn');
    if (!rearRecording) {
        // Start recording
        socket.emit('start_recording', { stream: 'rear' });
    } else {
        stopRearRecording();
    }
}

function pauseRearRecording() {
    socket.emit('pause_recording', { stream: 'rear' });
}

function stopRearRecording() {
    socket.emit('stop_recording', { stream: 'rear' });
}

// Fullscreen functions
function toggleFullscreen(element) {
    if (!document.fullscreenElement) {
        if (element.requestFullscreen) {
            element.requestFullscreen();
        } else if (element.webkitRequestFullscreen) { /* Safari */
            element.webkitRequestFullscreen();
        } else if (element.msRequestFullscreen) { /* IE11 */
            element.msRequestFullscreen();
        }
    } else {
        if (document.exitFullscreen) {
            document.exitFullscreen();
        } else if (document.webkitExitFullscreen) { /* Safari */
            document.webkitExitFullscreen();
        } else if (document.msExitFullscreen) { /* IE11 */
            document.msExitFullscreen();
        }
    }
}

// LIDAR functions
function resizeLidarCanvas() {
    const container = document.getElementById('lidar-container');
    lidarCanvas.width = container.clientWidth;
    lidarCanvas.height = container.clientHeight;
}

function drawLidarScan(scanData) {
    if (!scanData || !scanData.ranges) return;
    
    const now = Date.now();
    frameCount++;
    if (now - lastFpsUpdate >= 1000) {
        currentFps = frameCount;
        frameCount = 0;
        lastFpsUpdate = now;
        document.getElementById('lidar-fps').textContent = `FPS: ${currentFps}`;
    }
    
    const centerX = lidarCanvas.width / 2;
    const centerY = lidarCanvas.height / 2;
    const maxRadius = Math.min(centerX, centerY) * 0.9;
    
    // Clear canvas
    lidarCtx.clearRect(0, 0, lidarCanvas.width, lidarCanvas.height);
    
    // Draw axes
    lidarCtx.strokeStyle = '#333';
    lidarCtx.beginPath();
    lidarCtx.moveTo(centerX, 0);
    lidarCtx.lineTo(centerX, lidarCanvas.height);
    lidarCtx.moveTo(0, centerY);
    lidarCtx.lineTo(lidarCanvas.width, centerY);
    lidarCtx.stroke();
    
    // Draw distance circles
    for (let r = 0.25; r <= 1.0; r += 0.25) {
        lidarCtx.beginPath();
        lidarCtx.arc(centerX, centerY, maxRadius * r, 0, Math.PI * 2);
        lidarCtx.strokeStyle = '#444';
        lidarCtx.stroke();
        
        // Add distance labels
        if (scanData.range_max) {
            const dist = (scanData.range_max * r).toFixed(1);
            lidarCtx.fillStyle = '#777';
            lidarCtx.fillText(`${dist}m`, centerX + maxRadius * r + 5, centerY);
        }
    }
    
    // Draw points
    const angleMin = scanData.angle_min || 0;
    const angleIncrement = scanData.angle_increment || (2 * Math.PI / scanData.ranges.length);
    const rangeMax = scanData.range_max || 10.0;
    
    for (let i = 0; i < scanData.ranges.length; i++) {
        const range = scanData.ranges[i];
        if (range <= 0 || range > rangeMax) continue;
        
        const angle = angleMin + (i * angleIncrement);
        const x = centerX + Math.sin(angle) * (range / rangeMax) * maxRadius;
        const y = centerY - Math.cos(angle) * (range / rangeMax) * maxRadius;
        
        // Color based on distance (closer = brighter)
        const intensity = 1.0 - (range / rangeMax);
        const color = `rgb(0, ${Math.floor(255 * intensity)}, 0)`;
        
        lidarCtx.fillStyle = color;
        lidarCtx.beginPath();
        lidarCtx.arc(x, y, 2, 0, Math.PI * 2);
        lidarCtx.fill();
    }
    
    // Draw LIDAR position
    lidarCtx.fillStyle = 'red';
    lidarCtx.beginPath();
    lidarCtx.arc(centerX, centerY, 5, 0, Math.PI * 2);
    lidarCtx.fill();
    
    // Update LIDAR status
    updateStatusIndicator('lidar-status', true, 'Connected');
}

// Accelerometer functions
function initAccelPlot() {
    const container = document.getElementById('accel-plot');
    
    const data = [{
        type: 'scatter3d',
        mode: 'lines+markers',
        x: [],
        y: [],
        z: [],
        line: { width: 6, color: 'red' },
        marker: { size: 3, color: 'blue' }
    }];
    
    const layout = {
        title: 'Accelerometer 3D Orientation',
        scene: {
            xaxis: { title: 'X-Axis', range: [-20, 20] },
            yaxis: { title: 'Y-Axis', range: [-20, 20] },
            zaxis: { title: 'Z-Axis', range: [-20, 20] },
            aspectmode: 'cube'
        },
        margin: { l: 0, r: 0, b: 0, t: 30 }
    };
    
    plot = Plotly.newPlot(container, data, layout);
}

function updateAccelPlot(x, y, z) {
    accelData.push({x, y, z});
    if (accelData.length > maxDataPoints) {
        accelData.shift();
    }
    
    const xData = accelData.map(d => d.x);
    const yData = accelData.map(d => d.y);
    const zData = accelData.map(d => d.z);
    
    const update = {
        x: [xData],
        y: [yData],
        z: [zData]
    };
    
    Plotly.restyle('accel-plot', update, [0]);
}

// Control functions
function sendCommand(cmd) {
    const arduinoStatus = document.getElementById('arduino-status');
    if (arduinoStatus.classList.contains('status-disconnected')) {
        showStatus('Arduino is not connected!', false);
        return;
    }
    
    console.log("Sending command:", cmd);
    socket.emit('control', cmd);
    
    // Add small delay to prevent command flooding
    buttonActive = true;
    setTimeout(() => {
        buttonActive = false;
    }, 200);
}

function handleButtonDown(cmd) {
    sendCommand(cmd);
}

function handleButtonUp() {
    sendCommand('S');
}

function toggleRecording() {
    fetch('/record', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
    })
    .then(response => response.json())
    .then(data => {
        recording = !recording;
        const btn = document.getElementById('record-btn');
        btn.textContent = recording ? 'Stop Recording' : 'Start Recording';
        btn.classList.toggle('recording', recording);
        showStatus(data.status, true);
    })
    .catch(error => {
        showStatus('Error communicating with server', false);
    });
}

function toggleObstacleMode() {
    const btn = document.getElementById('obstacle-btn');
    const isActive = btn.classList.contains('active-mode');
    
    fetch(`/set_obstacle_mode/${isActive ? 'off' : 'on'}`, {
        method: 'POST'
    })
    .then(response => response.json())
    .then(data => {
        showStatus(data.status, true);
        syncControlModeUI(isActive ? 'BUTTONS' : 'OBSTACLE');
        syncChatForMode(isActive ? 'BUTTONS' : 'OBSTACLE');
    })
    .catch(error => {
        showStatus('Error toggling obstacle mode', false);
    });
}

function downloadSensorLogs() {
    window.location.href = '/download_sensor_logs';
}

function resetAllSensors() {
    const arduinoStatus = document.getElementById('arduino-status');
    if (arduinoStatus.classList.contains('status-disconnected')) {
        showStatus('Arduino is not connected!', false);
        return;
    }
    
    fetch('/reset_shock_count', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
    })
    .then(response => response.json())
    .then(data => {
        showStatus(data.status, true);
    })
    .catch(error => {
        showStatus('Error resetting sensors', false);
    });
}





function setControlMode(mode) {
    fetch(`/set_control_mode/${mode}`, {
        method: 'POST'
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Network response was not ok');
        }
        return response.json();
    })
    .then(data => {
        showStatus(data.status, true);
        syncControlModeUI(mode);
        syncChatForMode(mode);
    })
    .catch(error => {
        showStatus('Error changing control mode: ' + error.message, false);
        console.error('Error:', error);
    });
}





function initButtonControls() {
    const forwardBtn  = document.getElementById('forward-btn');
    const leftBtn     = document.getElementById('left-btn');
    const rightBtn    = document.getElementById('right-btn');
    const backwardBtn = document.getElementById('backward-btn');
    const stopBtn     = document.getElementById('stop-btn');
    const nwBtn       = document.getElementById('nw-btn');
    const neBtn       = document.getElementById('ne-btn');
    const swBtn       = document.getElementById('sw-btn');
    const seBtn       = document.getElementById('se-btn');

    function pressBtn(btn) {
        if (btn) btn.classList.add('btn-pressed');
    }
    function releaseBtn(btn) {
        if (btn) btn.classList.remove('btn-pressed');
    }
    function releaseAll() {
        [forwardBtn, leftBtn, rightBtn, backwardBtn, stopBtn, nwBtn, neBtn, swBtn, seBtn]
            .forEach(releaseBtn);
    }

    // Helper: attach press + release to a button
    function bindBtn(btn, downCmd, upCmd) {
        if (!btn) return;
        const onDown = (e) => { e.preventDefault(); pressBtn(btn); handleButtonDown(downCmd); };
        const onUp   = (e) => { releaseBtn(btn); if (upCmd) sendCommand(upCmd); else handleButtonUp(); };
        btn.addEventListener('mousedown',  onDown);
        btn.addEventListener('touchstart', onDown, { passive: false });
        btn.addEventListener('mouseup',    onUp);
        btn.addEventListener('touchend',   onUp);
        btn.addEventListener('mouseleave', onUp);
    }

    bindBtn(forwardBtn,  'F');
    bindBtn(leftBtn,     'L');
    bindBtn(rightBtn,    'R');
    bindBtn(backwardBtn, 'B');

    // Stop button — single tap, brief press animation
    stopBtn.addEventListener('mousedown',  (e) => { e.preventDefault(); pressBtn(stopBtn); });
    stopBtn.addEventListener('touchstart', (e) => { e.preventDefault(); pressBtn(stopBtn); }, { passive: false });
    stopBtn.addEventListener('mouseup',    () => { releaseBtn(stopBtn); sendCommand('S'); });
    stopBtn.addEventListener('touchend',   () => { releaseBtn(stopBtn); sendCommand('S'); });
    stopBtn.addEventListener('mouseleave', () => releaseBtn(stopBtn));

    // Corner buttons (A/B/C/D) — brief visual flash on click
    [nwBtn, neBtn, swBtn, seBtn].forEach(btn => {
        btn.addEventListener('mousedown',  (e) => { e.preventDefault(); pressBtn(btn); });
        btn.addEventListener('touchstart', (e) => { e.preventDefault(); pressBtn(btn); }, { passive: false });
        btn.addEventListener('mouseup',    () => setTimeout(() => releaseBtn(btn), 150));
        btn.addEventListener('touchend',   () => setTimeout(() => releaseBtn(btn), 150));
        btn.addEventListener('mouseleave', () => releaseBtn(btn));
    });

    // Release all buttons if mouse leaves window
    document.addEventListener('mouseup', releaseAll);
}








// In initChat() function
function initChat() {
    const sendBtn = document.getElementById('send-button');
    const input = document.getElementById('chat-input');
    const messages = document.getElementById('chat-messages');

    let aiMessageContainer = null;
    let isFirstMessage = true;

    function addUserMessage(text) {
        const msg = document.createElement('div');
        msg.className = 'message user';
        msg.innerHTML = `<strong>You:</strong> ${text}`;
        messages.appendChild(msg);
        messages.scrollTop = messages.scrollHeight;
    }

    function createAIMessage() {
        const msg = document.createElement('div');
        msg.className = 'message ai';
        msg.innerHTML = `<strong>AI Assistant:</strong> <span class="ai-stream"></span>`;
        messages.appendChild(msg);
        messages.scrollTop = messages.scrollHeight;
        return msg;
    }

    function sendMessage() {
        const text = input.value.trim();
        if (!text) return;

        addUserMessage(text);
        input.value = '';
        input.disabled = true;
        sendBtn.disabled = true;

        // Create new AI message container
        aiMessageContainer = createAIMessage();
        const aiStream = aiMessageContainer.querySelector('.ai-stream');

        socket.emit('ai_message', {
            text: text,
            timestamp: new Date().toISOString()
        });

        // Handle streaming response
        socket.on('ai_response', function(data) {
            if (!aiMessageContainer) return;

            switch(data.action) {
                case 'start':
                    aiStream.textContent = '';
                    break;
                
                case 'stream':
                    if (data.text) {
                        aiStream.textContent += data.text;
                        messages.scrollTop = messages.scrollHeight;
                    }
                    break;
                
                case 'end':
                    aiMessageContainer = null;
                    input.disabled = false;
                    sendBtn.disabled = false;
                    input.focus();
                    break;
                
                case 'error':
                    aiStream.textContent += `\n[ERROR: ${data.text}]`;
                    aiMessageContainer = null;
                    input.disabled = false;
                    sendBtn.disabled = false;
                    input.focus();
                    break;
            }
        });
    }

    sendBtn.addEventListener('click', sendMessage);
    input.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') sendMessage();
    });
}


function showStatus(message, isSuccess) {
    const statusDiv = document.getElementById('status-message');
    if (!statusDiv) {
        console.error("Status message div not found");
        return;
    }
    
    statusDiv.textContent = message;
    statusDiv.className = isSuccess ? 'status-message status-success' : 'status-message status-error';
    statusDiv.style.display = 'block';
    
    // Add animation
    statusDiv.style.animation = 'none';
    void statusDiv.offsetWidth; // Trigger reflow
    statusDiv.style.animation = 'fadeInOut 3s forwards';
    
    // Auto-hide after delay
    setTimeout(() => {
        statusDiv.style.display = 'none';
    }, 3000);
}








// Status message function
function showStatus(message, isSuccess) {
    const statusDiv = document.getElementById('status-message');
    statusDiv.textContent = message;
    statusDiv.className = isSuccess ? 'status-message status-success' : 'status-message status-error';
    statusDiv.style.display = 'block';
    
    setTimeout(() => {
        statusDiv.style.display = 'none';
    }, 3000);
}

// Socket event listeners
socket.on('sensor_update', function(data) {
    if (data.arduino_connected === false) {
        resetSensorConnectionState();
        clearSensorReadings();
        return;
    }

    updateSensorConnectionFromPayload(data);

    const connectedSensors = {
        touch: isSensorConnected('touch'),
        tilt: isSensorConnected('tilt'),
        rain: isSensorConnected('rain'),
        gas: isSensorConnected('gas'),
        flame: isSensorConnected('flame'),
        impact: isSensorConnected('impact'),
        sound: isSensorConnected('sound'),
        pir: isSensorConnected('pir'),
        radar: isSensorConnected('radar')
    };

    // Only update statuses that are present in this payload.
    if ('arduino_connected' in data) {
        updateStatusIndicator('arduino-status', data.arduino_connected,
            data.arduino_connected ? 'Connected' : 'Disconnected');
    }

    // Update WiFi, battery and control mode
    if ('wifi_strength' in data) {
        updateWiFiStatus(data.wifi_strength);
    }
    if ('battery_level' in data) {
        updateBatteryStatus(data.battery_level, data.battery_plugged || false);
    }
    if ('control_mode' in data && data.control_mode) {
        updateControlMode(data.control_mode);
    }

    // Update text values
    const textUpdates = {
        'temperature': data.temperature || "--",
        'humidity': data.humidity || "--",
        'touch_count': connectedSensors.touch ? (data.touch_count || "0") : "0",
        'tilt_count': connectedSensors.tilt ? (data.tilt_count || "0") : "0",
        'system_temp': data.system_temp || "--",
        'cpu_usage': data.cpu_usage || "--",
        'rain_count': connectedSensors.rain ? (data.rain_count || "0") : "0",
        'gas_count': connectedSensors.gas ? (data.gas_count || "0") : "0",
        'flame_count': connectedSensors.flame ? (data.flame_count || "0") : "0",
        'impact_count': connectedSensors.impact ? (data.impact_count || "0") : "0",
        'sound_count': connectedSensors.sound ? (data.sound_count || "0") : "0",
        'pir_count': connectedSensors.pir ? (data.pir_count || "0") : "0",
        'radar_count': connectedSensors.radar ? (data.radar_count || "0") : "0",
        'accel_x': data.accel_x || "0.00",
        'accel_y': data.accel_y || "0.00",
        'accel_z': data.accel_z || "0.00"
    };

    for (const [id, value] of Object.entries(textUpdates)) {
        const element = document.getElementById(id);
        if (element) element.textContent = value;
    }

    // Update status text and animations
    const sensorStatuses = {
        'touch': {
            text: connectedSensors.touch ? (data.touch_detected ? 'TOUCH DETECTED!' : 'No Touch') : 'Not Connected',
            active: connectedSensors.touch && data.touch_detected
        },
        'tilt': {
            text: connectedSensors.tilt ? (data.tilt_detected ? 'TILT DETECTED!' : 'Level') : 'Not Connected',
            active: connectedSensors.tilt && data.tilt_detected
        },
        'rain': {
            text: connectedSensors.rain ? (data.rain_detected ? 'RAIN DETECTED!' : 'Dry') : 'Not Connected',
            active: connectedSensors.rain && data.rain_detected
        },
        'gas': {
            text: connectedSensors.gas ? (data.gas_detected ? 'GAS DETECTED!' : 'Normal') : 'Not Connected',
            active: connectedSensors.gas && data.gas_detected
        },
        'flame': {
            text: connectedSensors.flame ? (data.flame_detected ? 'FLAME DETECTED!' : 'No Flame') : 'Not Connected',
            active: connectedSensors.flame && data.flame_detected
        },
        'impact': {
            text: connectedSensors.impact ? (data.impact_detected ? 'IMPACT DETECTED!' : 'Normal') : 'Not Connected',
            active: connectedSensors.impact && data.impact_detected
        },
        'sound': {
            text: connectedSensors.sound ? (data.sound_detected ? 'LOUD SOUND DETECTED!' : 'Quiet') : 'Not Connected',
            active: connectedSensors.sound && data.sound_detected
        },
        'pir': {
            text: connectedSensors.pir ? (data.pir_detected ? 'MOTION DETECTED!' : 'No Motion') : 'Not Connected',
            active: connectedSensors.pir && data.pir_detected
        },
        'radar': {
            text: connectedSensors.radar ? (data.radar_detected ? 'RADAR DETECTED!' : 'No Detection') : 'Not Connected',
            active: connectedSensors.radar && data.radar_detected
        }
    };

    for (const [sensor, status] of Object.entries(sensorStatuses)) {
        const element = document.getElementById(`${sensor}_status`);
        if (element) {
            element.textContent = status.text;
            if (status.active) {
                element.classList.add(`${sensor}-active`);
                setTimeout(() => element.classList.remove(`${sensor}-active`), 1000);
            }
        }
    }

    if (data.obstacle_avoidance_active === true) {
        syncControlModeUI('OBSTACLE');
        syncChatForMode('OBSTACLE');
    }
});


socket.on('accel_update', function(data) {
    document.getElementById('accel_x').textContent = (data.x || 0).toFixed(2);
    document.getElementById('accel_y').textContent = (data.y || 0).toFixed(2);
    document.getElementById('accel_z').textContent = (data.z || 0).toFixed(2);
    
    updateAccelPlot(data.x || 0, data.y || 0, data.z || 0);
});

socket.on('lidar_update', function(data) {
    drawLidarScan(data);
    lidarLastSeenAt = Date.now();
    updateStatusIndicator('lidar-status', true, 'Connected');
});

socket.on('gps_update', function(data) {
    if (data.lat && data.lon && map && marker) {
        marker.setLatLng([data.lat, data.lon]);
        map.panTo([data.lat, data.lon]);
        gpsLastSeenAt = Date.now();
        updateStatusIndicator('gps-status', true, 'Connected');
    }
});

socket.on('connection_update', function(data) {
    updateStatusIndicator('arduino-status', !!data.arduino_connected,
        data.arduino_connected ? 'Connected' : 'Disconnected');
    updateStatusIndicator('camera-status', !!data.camera_connected,
        data.camera_connected ? 'Connected' : 'Disconnected');
    updateStatusIndicator('rear-camera-status', !!data.rear_camera_connected,
        data.rear_camera_connected ? 'Connected' : 'Disconnected');

    if (!data.arduino_connected) {
        clearSensorReadings();
    }
});

setInterval(() => {
    const now = Date.now();
    const gpsConnected = gpsLastSeenAt > 0 && (now - gpsLastSeenAt) < CONNECTION_STALE_MS;
    const lidarConnected = lidarLastSeenAt > 0 && (now - lidarLastSeenAt) < CONNECTION_STALE_MS;

    updateStatusIndicator('gps-status', gpsConnected, gpsConnected ? 'Connected' : 'Disconnected');
    updateStatusIndicator('lidar-status', lidarConnected, lidarConnected ? 'Connected' : 'Disconnected');
}, 1000);

socket.on('recording_status', function(data) {
    if (data.stream === 'fpv') {
        fpvRecording = data.recording;
        const btn = document.getElementById('fpv-record-btn');
        if (fpvRecording) {
            btn.innerHTML = `
                <div class="panel-heading-actions" style="display: flex; gap: 5px;">
                    <div class="record-btn pause-btn" onclick="pauseFpvRecording()">
                        <i class='bx bx-pause'></i>
                    </div>
                    <div class="record-btn recording" onclick="stopFpvRecording()">
                        <i class='bx bx-stop'></i>
                    </div>
                </div>
            `;
        } else {
            btn.innerHTML = `
                <i class='bx bxs-video-recording'></i>
                <span>Start Recording</span>
            `;
        }
    } else if (data.stream === 'rear') {
        rearRecording = data.recording;
        const btn = document.getElementById('rear-record-btn');
        if (rearRecording) {
            btn.innerHTML = `
                <div class="panel-heading-actions" style="display: flex; gap: 5px;">
                    <div class="record-btn pause-btn" onclick="pauseRearRecording()">
                        <i class='bx bx-pause'></i>
                    </div>
                    <div class="record-btn recording" onclick="stopRearRecording()">
                        <i class='bx bx-stop'></i>
                    </div>
                </div>
            `;
        } else {
            btn.innerHTML = `
                <i class='bx bxs-video-recording'></i>
                <span>Start Recording</span>
            `;
        }
    }
});

socket.on('error', function(data) {
    showStatus(data.message, false);
});

socket.on('status', function(data) {
    showStatus(data.message, data.success);
});

// Utility functions
function updateGauge(type, value, min, max) {
    if (!value || isNaN(value)) return;
    
    const element = document.getElementById(`${type}-gauge`);
    const valueElement = document.getElementById(type === 'system-temp' ? 'system_temp' : 
                                  type === 'cpu' ? 'cpu_usage' : 
                                  type === 'touch' ? 'touch_count' : 
                                  type === 'tilt' ? 'tilt_count' :
                                  type === 'rain' ? 'rain_count' :
                                  type === 'gas' ? 'gas_count' :
                                  type === 'flame' ? 'flame_count' :
                                  type === 'impact' ? 'impact_count' :
                                  type === 'sound' ? 'sound_count' :
                                  type === 'pir' ? 'pir_count' :
                                  type === 'radar' ? 'radar_count' : type);
    
    const percentage = ((value - min) / (max - min)) * 100;
    element.style.width = `${Math.min(100, Math.max(0, percentage))}%`;
    
    // Set warning/critical states
    if (type === 'cpu' || type === 'system-temp') {
        if (value > max * 0.8) {
            element.classList.add('critical');
            valueElement.classList.add('critical');
        } else if (value > max * 0.6) {
            element.classList.add('warning');
            valueElement.classList.add('warning');
        } else {
            element.classList.remove('warning', 'critical');
            valueElement.classList.remove('warning', 'critical');
        }
    } else {
        element.classList.remove('warning', 'critical');
    }
}








// NEW JoyMode Function
function activateNewJoystickMode() {
    fetch('/set_control_mode/JOYMODE', { method: 'POST' })
        .then(res => res.json())
        .then(data => {
            console.log(data.status);
            syncControlModeUI('JOYMODE');
            syncChatForMode('JOYMODE');
        });
}

function pollNewGamepad() {
    const gamepads = navigator.getGamepads();
    if (!gamepads) return;

    const gp = gamepads[0];
    if (!gp || !gp.connected) return;

    const axes = gp.axes.map(a => parseFloat(a.toFixed(1)));
    socket.emit('joystick_input', { axes });
}

setInterval(pollNewGamepad, 100); // poll every 100ms

