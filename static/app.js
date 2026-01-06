// Campus color mapping (matching the image reference)
const CAMPUS_COLORS = {
    'ONLINE': '#dc3545',      // Red
    'BUS': '#007bff',         // Blue
    'CAC': '#ffc107',         // Yellow
    'D/C': '#28a745',         // Green
    'LIV': '#fd7e14',         // Orange
    'DOWNTOWN': '#e83e8c',    // Pink
    'CAMDEN': '#6f42c1',      // Purple
    'NEWARK': '#6c757d',      // Light Purple
    '': '#6c757d'             // Grey (Other/Unknown)
};

const CAMPUS_NAMES = {
    'ONLINE': 'Online',
    'BUS': 'Busch',
    'CAC': 'College Avenue',
    'D/C': 'Douglass / Cook',
    'LIV': 'Livingston',
    'DOWNTOWN': 'Downtown',
    'CAMDEN': 'Camden',
    'NEWARK': 'Newark',
    '': 'Other/Unknown'
};

// Course History Management
function loadCourseHistory() {
    const saved = localStorage.getItem('rutgers_course_history');
    if (saved) {
        try {
            const courses = JSON.parse(saved);
            return courses;
        } catch (e) {
            console.error('Error loading course history:', e);
            return [];
        }
    }
    return [];
}

function saveCourseHistory(courses) {
    try {
        localStorage.setItem('rutgers_course_history', JSON.stringify(courses));
        return true;
    } catch (e) {
        console.error('Error saving course history:', e);
        return false;
    }
}

function parseCourseCodes(input) {
    // Parse course codes from text (handles commas, newlines, spaces)
    const codes = input
        .split(/[,\n\r]+/)
        .map(code => code.trim())
        .filter(code => {
            // Validate format: 3 digits : 3 digits (e.g., 220:102)
            return /^\d{2,3}:\d{3}$/.test(code);
        });
    return [...new Set(codes)]; // Remove duplicates
}

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    const chatInput = document.getElementById('chatInput');
    const sendButton = document.getElementById('sendButton');
    const chatLog = document.getElementById('chatLog');
    
    // Send message on button click
    sendButton.addEventListener('click', sendMessage);
    
    // Send message on Enter key
    chatInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });
    
    // Initialize campus legend
    updateCampusLegend();
    
    // Course History UI
    const toggleHistory = document.getElementById('toggleHistory');
    const historyPanel = document.getElementById('courseHistoryPanel');
    const historyInput = document.getElementById('courseHistoryInput');
    const saveHistoryBtn = document.getElementById('saveHistory');
    const clearHistoryBtn = document.getElementById('clearHistory');
    const historyStatus = document.getElementById('historyStatus');
    
    // Load saved history
    const savedCourses = loadCourseHistory();
    if (savedCourses.length > 0) {
        historyInput.value = savedCourses.join('\n');
    }
    
    // Toggle history panel
    toggleHistory.addEventListener('click', () => {
        const isVisible = historyPanel.style.display !== 'none';
        historyPanel.style.display = isVisible ? 'none' : 'block';
        toggleHistory.textContent = isVisible ? 'Show' : 'Hide';
    });
    
    // Save history
    saveHistoryBtn.addEventListener('click', () => {
        const input = historyInput.value.trim();
        if (!input) {
            showHistoryStatus('Please enter at least one course code.', 'error');
            return;
        }
        
        const courses = parseCourseCodes(input);
        if (courses.length === 0) {
            showHistoryStatus('No valid course codes found. Format: 220:102, 198:111', 'error');
            return;
        }
        
        if (saveCourseHistory(courses)) {
            showHistoryStatus(`Saved ${courses.length} course(s): ${courses.join(', ')}`, 'success');
            // Send to backend
            updateBackendHistory(courses);
        } else {
            showHistoryStatus('Error saving course history.', 'error');
        }
    });
    
    // Clear history
    clearHistoryBtn.addEventListener('click', () => {
        if (confirm('Clear all course history?')) {
            historyInput.value = '';
            saveCourseHistory([]);
            showHistoryStatus('Course history cleared.', 'success');
            updateBackendHistory([]);
        }
    });
    
    function showHistoryStatus(message, type) {
        historyStatus.textContent = message;
        historyStatus.className = `history-status ${type}`;
        setTimeout(() => {
            historyStatus.className = 'history-status';
        }, 5000);
    }
    
    function updateBackendHistory(courses) {
        // Get session ID
        const sessionId = localStorage.getItem('rutgers_session_id') || 'default_' + Date.now();
        if (!localStorage.getItem('rutgers_session_id')) {
            localStorage.setItem('rutgers_session_id', sessionId);
        }
        
        // Send to backend API
        fetch('/api/course-history', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Session-ID': sessionId
            },
            body: JSON.stringify({ courses: courses })
        })
        .then(response => response.json())
        .then(data => {
            console.log('Course history updated on backend:', data);
        })
        .catch(error => {
            console.error('Error updating backend history:', error);
        });
    }
});

function sendMessage() {
    const chatInput = document.getElementById('chatInput');
    const message = chatInput.value.trim();
    
    if (!message) return;
    
    // Add user message to chat
    addMessageToChat(message, 'user');
    
    // Clear input and disable button
    chatInput.value = '';
    sendButton.disabled = true;
    sendButton.textContent = 'Sending...';
    
    // Get session ID (simple implementation)
    const sessionId = localStorage.getItem('rutgers_session_id') || 'default_' + Date.now();
    if (!localStorage.getItem('rutgers_session_id')) {
        localStorage.setItem('rutgers_session_id', sessionId);
    }
    
    // Send to backend
    fetch('/api/chat', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-Session-ID': sessionId
        },
        body: JSON.stringify({ message: message })
    })
    .then(response => response.json())
    .then(data => {
        // Add bot response
        addMessageToChat(data.text_response, 'bot');
        
        // Update schedule if available
        if (data.schedule_data && data.schedule_data.schedule) {
            console.log('Schedule data received:', data.schedule_data);
            renderSchedule(data.schedule_data);
        } else {
            console.log('No schedule data in response');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        addMessageToChat('Sorry, an error occurred. Please try again.', 'bot');
    })
    .finally(() => {
        sendButton.disabled = false;
        sendButton.textContent = 'Send';
        chatInput.focus();
    });
}

function addMessageToChat(text, type) {
    const chatLog = document.getElementById('chatLog');
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${type}-message`;
    
    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    
    // Convert markdown-like text to HTML
    const htmlText = formatMessage(text);
    contentDiv.innerHTML = htmlText;
    
    messageDiv.appendChild(contentDiv);
    chatLog.appendChild(messageDiv);
    
    // Scroll to bottom
    chatLog.scrollTop = chatLog.scrollHeight;
}

function formatMessage(text) {
    // Simple markdown-like formatting
    let html = text
        .replace(/\n/g, '<br>')
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/\*(.*?)\*/g, '<em>$1</em>')
        .replace(/`(.*?)`/g, '<code>$1</code>')
        .replace(/^### (.*$)/gm, '<h3>$1</h3>')
        .replace(/^## (.*$)/gm, '<h2>$1</h2>')
        .replace(/^# (.*$)/gm, '<h1>$1</h1>');
    
    return html;
}

function renderSchedule(scheduleData) {
    const visualizer = document.getElementById('scheduleVisualizer');
    
    console.log('Rendering schedule:', scheduleData);
    
    if (!scheduleData || !scheduleData.schedule || scheduleData.schedule.length === 0) {
        console.log('No schedule data to render');
        visualizer.innerHTML = `
            <div class="empty-schedule">
                <div class="empty-icon">📅</div>
                <p>No schedule to display</p>
            </div>
        `;
        return;
    }
    
    // Build schedule grid
    const days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday'];
    const timeSlots = generateTimeSlots(scheduleData.schedule);
    
    if (timeSlots.length === 0) {
        console.error('No time slots generated');
        visualizer.innerHTML = `
            <div class="empty-schedule">
                <div class="empty-icon">📅</div>
                <p>Could not generate schedule grid</p>
            </div>
        `;
        return;
    }
    
    let html = '<div class="schedule-grid">';
    
    // Header row
    html += '<div class="schedule-header-cell">Time</div>';
    days.forEach(day => {
        html += `<div class="schedule-header-cell">${day.substring(0, 3)}</div>`;
    });
    
    // Time slots and day columns
    timeSlots.forEach(timeSlot => {
        // Time label
        html += `<div class="schedule-time-cell">${timeSlot.label}</div>`;
        
        // Day columns
        days.forEach(day => {
            html += `<div class="schedule-day-column" data-day="${day}" data-time="${timeSlot.minutes}"></div>`;
        });
    });
    
    html += '</div>';
    visualizer.innerHTML = html;
    
    console.log('Schedule grid created with', timeSlots.length, 'time slots');
    
    // Add course blocks
    scheduleData.schedule.forEach(section => {
        if (!section.meetings || section.meetings.length === 0) {
            console.warn('Section has no meetings:', section);
            return;
        }
        
        section.meetings.forEach(meeting => {
            if (!meeting) return;
            
            // Normalize day name
            const rawDay = meeting.day;
            const day = normalizeDay(rawDay);
            if (!day) {
                console.warn('Meeting has invalid day:', rawDay, meeting);
                return;
            }
            
            const startMinutes = timeToMinutes(meeting.start_time_24h || meeting.start_time);
            const endMinutes = timeToMinutes(meeting.end_time_24h || meeting.end_time);
            
            if (!startMinutes || !endMinutes) {
                console.warn('Could not parse times:', {
                    start: meeting.start_time_24h || meeting.start_time,
                    end: meeting.end_time_24h || meeting.end_time,
                    meeting
                });
                return;
            }
            
            const dayColumn = visualizer.querySelector(`[data-day="${day}"]`);
            if (!dayColumn) {
                console.warn('Day column not found for:', day, 'Available columns:', 
                    Array.from(visualizer.querySelectorAll('[data-day]')).map(el => el.getAttribute('data-day')));
                return;
            }
            
            const courseBlock = createCourseBlock(section, meeting, startMinutes, endMinutes, timeSlots);
            if (courseBlock) {
                dayColumn.appendChild(courseBlock);
            }
        });
    });
    
    // Update campus legend
    updateCampusLegend(scheduleData.schedule);
}

function createCourseBlock(section, meeting, startMinutes, endMinutes, timeSlots) {
    const block = document.createElement('div');
    block.className = 'course-block';
    
    if (!timeSlots || timeSlots.length === 0) {
        console.error('No time slots provided');
        return block;
    }
    
    // Calculate position and height
    const firstSlot = timeSlots[0];
    const slotHeight = 40; // pixels per 30-minute slot
    const top = ((startMinutes - firstSlot.minutes) / 30) * slotHeight;
    const height = ((endMinutes - startMinutes) / 30) * slotHeight;
    
    if (top < 0 || height <= 0) {
        console.warn('Invalid position/height:', { top, height, startMinutes, endMinutes });
        return block;
    }
    
    block.style.top = `${Math.max(0, top)}px`;
    block.style.height = `${Math.max(height, 60)}px`;
    
    // Get campus color
    const campus = meeting.campus || meeting.campus_abbrev || '';
    const campusKey = campus.toUpperCase();
    const color = CAMPUS_COLORS[campusKey] || CAMPUS_COLORS[''] || '#6c757d';
    block.style.backgroundColor = color;
    
    // Course info
    const courseTitle = section.course_title || section.course_key || 'Unknown';
    const courseCode = section.course_key || '';
    const building = meeting.building || meeting.room || 'TBA';
    const timeStr = `${meeting.start_time} - ${meeting.end_time}`;
    
    block.innerHTML = `
        <div class="course-block-title">${courseTitle}</div>
        <div class="course-block-code">${courseCode}</div>
        <div class="course-block-time">${timeStr}</div>
        <div class="course-block-building">${building}</div>
    `;
    
    return block;
}

function normalizeDay(dayStr) {
    if (!dayStr) return null;
    const dayMap = {
        'M': 'Monday', 'MONDAY': 'Monday',
        'T': 'Tuesday', 'TUESDAY': 'Tuesday',
        'W': 'Wednesday', 'WEDNESDAY': 'Wednesday',
        'TH': 'Thursday', 'R': 'Thursday', 'THURSDAY': 'Thursday',
        'F': 'Friday', 'FRIDAY': 'Friday'
    };
    const upper = dayStr.toUpperCase().trim();
    if (dayMap[upper]) return dayMap[upper];
    // Try partial match
    for (const [key, value] of Object.entries(dayMap)) {
        if (upper.includes(key) || key.includes(upper)) {
            return value;
        }
    }
    return null;
}

function generateTimeSlots(schedule) {
    // Find min and max times
    let minTime = 24 * 60; // 11:59 PM
    let maxTime = 0; // 12:00 AM
    
    if (!schedule || !Array.isArray(schedule)) {
        console.error('Invalid schedule data:', schedule);
        return [];
    }
    
    schedule.forEach(section => {
        if (!section || !section.meetings || !Array.isArray(section.meetings)) {
            console.warn('Invalid section:', section);
            return;
        }
        
        section.meetings.forEach(meeting => {
            if (!meeting) return;
            
            const start = timeToMinutes(meeting.start_time_24h || meeting.start_time);
            const end = timeToMinutes(meeting.end_time_24h || meeting.end_time);
            
            if (start && start > 0) minTime = Math.min(minTime, start);
            if (end && end > 0) maxTime = Math.max(maxTime, end);
        });
    });
    
    // If no valid times found, return empty
    if (minTime >= 24 * 60 || maxTime <= 0) {
        console.error('No valid times found in schedule');
        return [];
    }
    
    // Round to nearest hour, with padding
    minTime = Math.floor(minTime / 60) * 60;
    maxTime = Math.ceil(maxTime / 60) * 60;
    
    // Add padding
    minTime = Math.max(minTime - 60, 7 * 60); // Start at 7 AM at earliest
    maxTime = Math.min(maxTime + 60, 23 * 60); // End at 11 PM at latest
    
    // Generate 30-minute slots
    const slots = [];
    for (let minutes = minTime; minutes <= maxTime; minutes += 30) {
        slots.push({
            minutes: minutes,
            label: minutesToTime(minutes)
        });
    }
    
    return slots;
}

function timeToMinutes(timeStr) {
    if (!timeStr) return null;
    
    // Convert to string and trim
    timeStr = String(timeStr).trim();
    
    // Handle 24h format (HH:MM or H:MM)
    const match24 = timeStr.match(/^(\d{1,2}):(\d{2})$/);
    if (match24) {
        const h = parseInt(match24[1]);
        const m = parseInt(match24[2]);
        if (h >= 0 && h < 24 && m >= 0 && m < 60) {
            return h * 60 + m;
        }
    }
    
    // Handle 12h format (H:MM AM/PM or HH:MM AM/PM)
    const match12 = timeStr.match(/^(\d{1,2}):(\d{2})\s*(AM|PM|am|pm)$/i);
    if (match12) {
        let h = parseInt(match12[1]);
        const m = parseInt(match12[2]);
        const period = match12[3].toUpperCase();
        
        if (h < 1 || h > 12 || m < 0 || m >= 60) return null;
        
        if (period === 'PM' && h !== 12) h += 12;
        if (period === 'AM' && h === 12) h = 0;
        
        return h * 60 + m;
    }
    
    // Try to parse without AM/PM (assume 24h if reasonable, otherwise assume PM)
    const matchNoPeriod = timeStr.match(/^(\d{1,2}):(\d{2})$/);
    if (matchNoPeriod) {
        let h = parseInt(matchNoPeriod[1]);
        const m = parseInt(matchNoPeriod[2]);
        if (h >= 0 && h < 24 && m >= 0 && m < 60) {
            // If hour is 1-11, might be ambiguous, but assume 24h format
            return h * 60 + m;
        }
    }
    
    console.warn('Could not parse time:', timeStr);
    return null;
}

function minutesToTime(minutes) {
    const h = Math.floor(minutes / 60);
    const m = minutes % 60;
    const period = h >= 12 ? 'PM' : 'AM';
    const h12 = h > 12 ? h - 12 : (h === 0 ? 12 : h);
    return `${h12}:${m.toString().padStart(2, '0')} ${period}`;
}

function updateCampusLegend(schedule) {
    const legend = document.getElementById('campusLegend');
    const campuses = new Set();
    
    if (schedule) {
        schedule.forEach(section => {
            section.meetings.forEach(meeting => {
                const campus = (meeting.campus || meeting.campus_abbrev || '').toUpperCase();
                if (campus) campuses.add(campus);
            });
        });
    }
    
    // Always show common campuses
    const commonCampuses = ['ONLINE', 'BUS', 'CAC', 'D/C', 'LIV'];
    commonCampuses.forEach(campus => campuses.add(campus));
    
    let html = '';
    Array.from(campuses).sort().forEach(campus => {
        const color = CAMPUS_COLORS[campus] || CAMPUS_COLORS[''];
        const name = CAMPUS_NAMES[campus] || campus;
        html += `
            <div class="legend-item">
                <div class="legend-color" style="background-color: ${color}"></div>
                <span>${name}</span>
            </div>
        `;
    });
    
    legend.innerHTML = html;
}

