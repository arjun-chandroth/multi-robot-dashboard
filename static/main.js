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

    // Initial status updates
    updateStatusIndicator('battery-status', true);
    updateStatusIndicator('control-mode', true);

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
        const modeElement = document.getElementById('control-mode');
        if (modeElement) {
            modeElement.setAttribute('data-tooltip', `Control Mode: ${data.mode}`);
            
            // Update status colors
            if (data.mode === 'JOYSTICK') {
                modeElement.className = 'status-badge status-joystick';
            } else if (data.mode === 'AI') {
                modeElement.className = 'status-badge status-ai';
            } else if (data.mode === 'OBSTACLE') {
                modeElement.className = 'status-badge status-lidar';
            } else {
                modeElement.className = 'status-badge status-connected';
            }
        }

        // Update button states
        document.querySelectorAll('.mode-btn').forEach(btn => {
            btn.classList.remove('active-mode');
        });
        
        const activeBtn = document.querySelector(`.mode-btn[onclick*="${data.mode}"]`);
        if (activeBtn) {
            activeBtn.classList.add('active-mode');
        }

        // Handle AI mode specifically
        const chatInput = document.getElementById('chat-input');
        const sendButton = document.getElementById('send-button');
        const messages = document.getElementById('chat-messages');
        
        if (data.mode === 'AI') {
            // Enable chat interface
            if (chatInput) {
                chatInput.disabled = false;
                chatInput.placeholder = "Type your message to the AI...";
                setTimeout(() => chatInput.focus(), 100);
            }
            if (sendButton) sendButton.disabled = false;

            // Add welcome message if chat is empty
            if (messages && messages.children.length <= 1) {
                const welcomeMsg = document.createElement('div');
                welcomeMsg.className = 'ai-message';
                welcomeMsg.innerHTML = `<strong>AI Assistant:</strong> AI mode activated! How can I assist you with the robot controls?`;
                messages.appendChild(welcomeMsg);
                messages.scrollTop = messages.scrollHeight;
            }
        } else {
            // Disable chat interface
            if (chatInput) {
                chatInput.disabled = true;
                chatInput.placeholder = "Enable AI mode to chat";
            }
            if (sendButton) sendButton.disabled = true;
        }
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
    element.classList.toggle('connected', isConnected);
    if (statusText) {
        element.setAttribute('data-tooltip', `${element.getAttribute('data-tooltip').split(':')[0]}: ${statusText}`);
    }
}

function updateConnectionStatus(arduinoConnected, cameraConnected, rearCameraConnected) {
    updateStatusIndicator('arduino-status', arduinoConnected);
    updateStatusIndicator('camera-status', cameraConnected);
    updateStatusIndicator('rear-camera-status', rearCameraConnected || false);
    updateStatusIndicator('globe-status', arduinoConnected);

    // Update the connection status badges
    const arduinoStatus = document.getElementById('arduino-status');
    const cameraStatus = document.getElementById('camera-status');
    
    if (arduinoConnected) {
        arduinoStatus.className = 'status-badge status-connected';
        arduinoStatus.textContent = 'Arduino: Connected';
    } else {
        arduinoStatus.className = 'status-badge status-disconnected';
        arduinoStatus.textContent = 'Arduino: Disconnected';
    }
    
    if (cameraConnected) {
        cameraStatus.className = 'status-badge status-connected';
        cameraStatus.textContent = 'Camera: Connected';
    } else {
        cameraStatus.className = 'status-badge status-disconnected';
        cameraStatus.textContent = 'Camera: Disconnected';
    }
}

function updateWiFiStatus(strength) {
    const wifi = document.getElementById('wifi-status');
    const icon = wifi.querySelector('i');
    
    let statusText = 'Disconnected';
    if (strength > 0) {
        statusText = `${strength}%`;
        wifi.classList.add('connected');
        
        if (strength > 75) icon.className = 'bx bx-wifi';
        else if (strength > 50) icon.className = 'bx bx-wifi-2';
        else if (strength > 25) icon.className = 'bx bx-wifi-1';
        else icon.className = 'bx bx-wifi-0';
    } else {
        wifi.classList.remove('connected');
        icon.className = 'bx bx-wifi-off';
    }
    wifi.setAttribute('data-tooltip', `WiFi: ${statusText}`);
}

function updateBatteryStatus(level, isPlugged) {
    const battery = document.getElementById('battery-status');
    const icon = battery.querySelector('i');
    
    battery.classList.toggle('battery-plugged', isPlugged);
    battery.classList.toggle('connected', isPlugged || level > 20);
    
    if (isPlugged) {
        icon.className = 'bx bx-battery-charging';
    } else if (level > 75) {
        icon.className = 'bx bx-battery-full';
    } else if (level > 50) {
        icon.className = 'bx bx-battery';
    } else if (level > 25) {
        icon.className = 'bx bx-battery-low';
    } else {
        icon.className = 'bx bx-battery-empty';
    }
    battery.setAttribute('data-tooltip', `Battery: ${level}%${isPlugged ? ' (Charging)' : ''}`);
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
    const icon = controlMode.querySelector('i');
    
    if (mode === 'BUTTONS') icon.className = 'bx bx-chip';
    else if (mode === 'JOYSTICK') icon.className = 'bx bx-joystick';
    else if (mode === 'OBSTACLE') icon.className = 'bx bx-run';
    
    controlMode.setAttribute('data-tooltip', `Control Mode: ${mode}`);
}


function updateGpsStatus(lat, lon) {
    const gps = document.getElementById('gps-status');
    const icon = gps.querySelector('i');

    const connected = lat !== null && lon !== null;
    gps.classList.toggle('connected', connected);
    icon.className = connected ? 'bx bx-map' : 'bx bx-map-pin';
}

// Map functions - Static implementation
function initMap() {
    if (typeof L !== 'undefined') {
        // Static coordinates (Delhi, India)
        const staticCoords = [28.6139, 77.2090];
        
        // Create map centered at static location
        map = L.map('map').setView(staticCoords, 16);
        
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
        
        // Add static marker
        marker = L.marker(staticCoords, {icon: robotIcon}).addTo(map);
        
        // Add scale control
        L.control.scale().addTo(map);
        
        // Add position accuracy circle
        L.circle(staticCoords, {
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
    document.getElementById('lidar-status').className = 'status-badge status-lidar';
    document.getElementById('lidar-status').textContent = 'LIDAR: Connected';
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
        btn.classList.toggle('active-mode', !isActive);
        
        // Update other mode buttons
        document.querySelectorAll('.mode-btn:not(#obstacle-btn)').forEach(btn => {
            btn.classList.remove('active-mode');
        });
        
        // Update control mode display
        const modeElement = document.getElementById('control-mode');
        if (!isActive) {
            modeElement.textContent = 'Control Mode: OBSTACLE';
            modeElement.className = 'status-badge status-lidar';
        } else {
            modeElement.textContent = 'Control Mode: BUTTONS';
            modeElement.className = 'status-badge status-connected';
        }
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

        // Update all mode buttons
        document.querySelectorAll('.mode-btn').forEach(btn => {
            btn.classList.remove('active-mode');
        });
        
        const clickedBtn = document.querySelector(`.mode-btn[onclick*="${mode}"]`);
        if (clickedBtn) clickedBtn.classList.add('active-mode');

        // Update control mode display
        const modeElement = document.getElementById('control-mode');
        if (modeElement) {
            modeElement.textContent = `Control Mode: ${mode}`;
            
            // Reset all status classes first
            modeElement.classList.remove('status-connected', 'status-joystick', 'status-ai', 'status-lidar');
            
            // Add appropriate status class
            if (mode === 'JOYSTICK') {
                modeElement.classList.add('status-joystick');
            } else if (mode === 'AI') {
                modeElement.classList.add('status-ai');
            } else if (mode === 'OBSTACLE') {
                modeElement.classList.add('status-lidar');
            } else {
                modeElement.classList.add('status-connected');
            }
        }

        // Handle AI mode specifically
        const chatInput = document.getElementById('chat-input');
        const sendButton = document.getElementById('send-button');
        const messages = document.getElementById('chat-messages');

        if (mode === 'AI') {
            // Enable chat interface
            if (chatInput) {
                chatInput.disabled = false;
                chatInput.placeholder = "Type your message to the AI...";
                setTimeout(() => chatInput.focus(), 100);
            }
            if (sendButton) sendButton.disabled = false;

            // Add welcome message if chat is empty
            if (messages && messages.children.length <= 1) {
                const welcomeMsg = document.createElement('div');
                welcomeMsg.className = 'mt-2 ai-message';
                welcomeMsg.innerHTML = `<strong>AI Assistant:</strong> AI mode activated! How can I assist you with the robot controls?`;
                messages.appendChild(welcomeMsg);
                messages.scrollTop = messages.scrollHeight;
            }
        } else {
            // Disable chat interface
            if (chatInput) {
                chatInput.disabled = true;
                chatInput.placeholder = "Enable AI mode to chat";
            }
            if (sendButton) sendButton.disabled = true;
        }
    })
    .catch(error => {
        showStatus('Error changing control mode: ' + error.message, false);
        console.error('Error:', error);
    });
}





function initButtonControls() {
    const forwardBtn = document.getElementById('forward-btn');
    const leftBtn = document.getElementById('left-btn');
    const rightBtn = document.getElementById('right-btn');
    const backwardBtn = document.getElementById('backward-btn');
    const stopBtn = document.getElementById('stop-btn');
    
    // Set button press handlers
    forwardBtn.addEventListener('mousedown', () => handleButtonDown('F'));
    forwardBtn.addEventListener('touchstart', () => handleButtonDown('F'));
    
    leftBtn.addEventListener('mousedown', () => handleButtonDown('L'));
    leftBtn.addEventListener('touchstart', () => handleButtonDown('L'));
    
    rightBtn.addEventListener('mousedown', () => handleButtonDown('R'));
    rightBtn.addEventListener('touchstart', () => handleButtonDown('R'));
    
    backwardBtn.addEventListener('mousedown', () => handleButtonDown('B'));
    backwardBtn.addEventListener('touchstart', () => handleButtonDown('B'));
    
    // Set button release handlers
    forwardBtn.addEventListener('mouseup', handleButtonUp);
    forwardBtn.addEventListener('touchend', handleButtonUp);
    
    leftBtn.addEventListener('mouseup', handleButtonUp);
    leftBtn.addEventListener('touchend', handleButtonUp);
    
    rightBtn.addEventListener('mouseup', handleButtonUp);
    rightBtn.addEventListener('touchend', handleButtonUp);
    
    backwardBtn.addEventListener('mouseup', handleButtonUp);
    backwardBtn.addEventListener('touchend', handleButtonUp);
    
    // Stop button
    stopBtn.addEventListener('click', () => sendCommand('S'));
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
    // Update status icons
    updateStatusIndicator('arduino-status', data.arduino_connected, 
        data.arduino_connected ? 'Connected' : 'Disconnected');
    updateStatusIndicator('camera-status', data.camera_connected, 
        data.camera_connected ? 'Connected' : 'Disconnected');
    updateStatusIndicator('rear-camera-status', data.rear_camera_connected, 
        data.rear_camera_connected ? 'Connected' : 'Disconnected');
    updateStatusIndicator('lidar-status', data.lidar_connected, 
        data.lidar_connected ? 'Connected' : 'Disconnected');
    updateStatusIndicator('gps-status', data.location?.lat && data.location?.lon, 
        data.location?.lat ? 'Connected' : 'Disconnected');

    // Update WiFi, battery and control mode
    updateWiFiStatus(data.wifi_strength);
    updateBatteryStatus(data.battery_level, data.battery_plugged || false);
    updateControlMode(data.control_mode);

    // Update text values
    const textUpdates = {
        'temperature': data.temperature || "--",
        'humidity': data.humidity || "--",
        'touch_count': data.touch_count || "0",
        'tilt_count': data.tilt_count || "0",
        'system_temp': data.system_temp || "--",
        'cpu_usage': data.cpu_usage || "--",
        'rain_count': data.rain_count || "0",
        'gas_count': data.gas_count || "0",
        'flame_count': data.flame_count || "0",
        'impact_count': data.impact_count || "0",
        'sound_count': data.sound_count || "0",
        'pir_count': data.pir_count || "0",
        'radar_count': data.radar_count || "0",
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
            text: data.touch_detected ? 'TOUCH DETECTED!' : 'No Touch',
            active: data.touch_detected
        },
        'tilt': {
            text: data.tilt_detected ? 'TILT DETECTED!' : 'Level',
            active: data.tilt_detected
        },
        'rain': {
            text: data.rain_detected ? 'RAIN DETECTED!' : 'Dry',
            active: data.rain_detected
        },
        'gas': {
            text: data.gas_detected ? 'GAS DETECTED!' : 'Normal',
            active: data.gas_detected
        },
        'flame': {
            text: data.flame_detected ? 'FLAME DETECTED!' : 'No Flame',
            active: data.flame_detected
        },
        'impact': {
            text: data.impact_detected ? 'IMPACT DETECTED!' : 'Normal',
            active: data.impact_detected
        },
        'sound': {
            text: data.sound_detected ? 'LOUD SOUND DETECTED!' : 'Quiet',
            active: data.sound_detected
        },
        'pir': {
            text: data.pir_detected ? 'MOTION DETECTED!' : 'No Motion',
            active: data.pir_detected
        },
        'radar': {
            text: data.radar_detected ? 'RADAR DETECTED!' : 'No Detection',
            active: data.radar_detected
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

    // Update obstacle button state
    const obstacleBtn = document.getElementById('obstacle-btn');
    if (obstacleBtn) {
        if (data.obstacle_avoidance_active) {
            obstacleBtn.classList.add('active-mode');
        } else {
            obstacleBtn.classList.remove('active-mode');
        }
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
    document.getElementById('lidar-status').className = 'status-badge status-lidar';
    document.getElementById('lidar-status').textContent = 'LIDAR: Connected';
});

socket.on('gps_update', function(data) {
    if (data.lat && data.lon && map && marker) {
        marker.setLatLng([data.lat, data.lon]);
        map.panTo([data.lat, data.lon]);
    }
});

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

socket.on('control_mode_update', function(data) {
    const modeElement = document.getElementById('control-mode');
    modeElement.textContent = `Control Mode: ${data.mode}`;
    
    if (data.mode === 'JOYSTICK') {
        modeElement.className = 'status-badge status-joystick';
    } else if (data.mode === 'OBSTACLE') {
        modeElement.className = 'status-badge status-lidar';
    } else {
        modeElement.className = 'status-badge status-connected';
    }
    
    document.querySelectorAll('.mode-btn').forEach(btn => {
        btn.classList.remove('active-mode');
    });
    
    if (data.mode === 'OBSTACLE') {
        document.getElementById('obstacle-btn').classList.add('active-mode');
    } else {
        document.querySelector(`.mode-btn[onclick*="${data.mode}"]`).classList.add('active-mode');
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
            document.querySelectorAll('.mode-btn').forEach(btn => btn.classList.remove('active-mode'));
            document.getElementById('new-joystick-btn').classList.add('active-mode');
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

