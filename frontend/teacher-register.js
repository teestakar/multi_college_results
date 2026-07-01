// ==================== DOM ELEMENTS ====================
const teacherRegisterForm = document.getElementById('teacherRegisterForm');
const teacherIdInput = document.getElementById('teacherId');
const nameInput = document.getElementById('name');
const emailInput = document.getElementById('email');
const passwordInput = document.getElementById('password');
const submitBtn = document.getElementById('submitBtn');
const messageDiv = document.getElementById('message');
const loadingDiv = document.getElementById('loading');

// ==================== PAGE LOAD ====================
document.addEventListener('DOMContentLoaded', function() {
    console.log('Teacher register page loaded');
    
    // Check if logged in as admin teacher
    const accessToken = localStorage.getItem('access_token');
    const userType = localStorage.getItem('user_type');
    
    if (!accessToken || userType !== 'admin') {
        window.location.href = 'teacher-login.html';
        return;
    }
});

// ==================== FORM SUBMIT ====================
teacherRegisterForm.addEventListener('submit', handleRegister);

async function handleRegister(event) {
    event.preventDefault();

    const teacherId = teacherIdInput.value.trim();
    const name = nameInput.value.trim();
    const email = emailInput.value.trim();
    const password = passwordInput.value.trim();

    if (!teacherId || !name || !email || !password) {
        showMessage('❌ Please fill all fields', 'error');
        return;
    }

    loadingDiv.style.display = 'block';
    submitBtn.disabled = true;

    try {
        const data = await apiCall('/api/auth/teacher/register', {
            method: 'POST',
            body: JSON.stringify({
                teacher_id: teacherId,
                name,
                email,
                password
            })
        });

        // backend error safety
        if (data?.status === "error") {
            throw new Error(data.message || "Registration failed");
        }

        showMessage(`✅ ${data.message || "Teacher registered successfully"}`, 'success');

        teacherRegisterForm.reset();
        teacherIdInput.focus();

    } catch (error) {
        console.error(error);
        showMessage(`❌ ${error.message}`, 'error');

    } finally {
        // 🔥 ALWAYS RESET UI STATE
        loadingDiv.style.display = 'none';
        submitBtn.disabled = false;
    }
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