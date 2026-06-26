// ==================== DOM ELEMENTS ====================
const welcomeNameEl = document.getElementById('welcomeName');
const teacherIdEl = document.getElementById('teacherId');
const collegeIdEl = document.getElementById('collegeId');
const collegeNameEl = document.getElementById('collegeName');
const roleEl = document.getElementById('role');
const userLabelEl = document.getElementById('userLabel');
const studentRegisterCardEl = document.getElementById('studentRegisterCard');
const teacherRegisterCardEl = document.getElementById('teacherRegisterCard');
const messageDiv = document.getElementById('message');

// ==================== PAGE LOAD ====================
document.addEventListener('DOMContentLoaded', function() {
    console.log('Teacher dashboard page loaded');
    
    // Check if logged in as teacher
    const accessToken = localStorage.getItem('access_token');
    const userType = localStorage.getItem('user_type');
    
    if (!accessToken || userType !== 'teacher') {
        window.location.href = 'teacher-login.html';
        return;
    }
    
    // Display teacher info from localStorage
    const userName = localStorage.getItem('user_name');
    
    welcomeNameEl.textContent = userName ? userName.split(' ')[0] : 'Teacher';
    userLabelEl.textContent = `👨‍🏫 ${userName || 'Teacher'}`;
    
    // Load full profile from backend
    loadTeacherProfile();
});

// ==================== LOAD TEACHER PROFILE ====================
async function loadTeacherProfile() {
    try {
        console.log('Loading teacher profile...');
        
        const data = await apiCall('/api/auth/teacher/me');

        console.log('Teacher profile data:', data);

        console.log('Teacher profile data:', data);

        // Update UI with profile data
        teacherIdEl.textContent = data.teacher_id;
        roleEl.textContent = data.role === 'admin' ? 'Admin' : 'Teacher';
        collegeNameEl.textContent = data.college_name;
        collegeIdEl.textContent = data.college_id;

        // Show admin cards only if user is admin
        if (data.role === 'admin') {
            studentRegisterCardEl.style.display = 'block';
            teacherRegisterCardEl.style.display = 'block';
        }

    } catch (error) {
        console.error('Error loading teacher profile:', error);
        logout();
    }
}

// ==================== LOGOUT ====================
function logout() {
    console.log('Logging out...');
    localStorage.clear();
    window.location.href = 'teacher-login.html';
}

// ==================== SHOW MESSAGE ====================
function showMessage(text, type) {
    messageDiv.textContent = text;
    messageDiv.className = `message ${type}`;
    messageDiv.style.display = 'block';
    
    if (type === 'success') {
        setTimeout(() => {
            messageDiv.style.display = 'none';
        }, 5000);
    }
}