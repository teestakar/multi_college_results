// ==================== DOM ELEMENTS ====================
const studentRegisterForm = document.getElementById('studentRegisterForm');
const rollNoInput = document.getElementById('rollNo');
const nameInput = document.getElementById('name');
const emailInput = document.getElementById('email');
const passwordInput = document.getElementById('password');
const degreeInput = document.getElementById('degree');
const branchInput = document.getElementById('branch');
const yearSelect = document.getElementById('year');
const submitBtn = document.getElementById('submitBtn');
const messageDiv = document.getElementById('message');
const loadingDiv = document.getElementById('loading');

// ==================== PAGE LOAD ====================
document.addEventListener('DOMContentLoaded', function() {
    console.log('Student register page loaded');
    
    // Check if logged in as admin teacher
    const accessToken = localStorage.getItem('access_token');
    const userType = localStorage.getItem('user_type');
    
    if (!accessToken || userType !== 'teacher') {
        window.location.href = 'teacher-login.html';
        return;
    }
});

// ==================== FORM SUBMIT ====================
studentRegisterForm.addEventListener('submit', handleRegister);

async function handleRegister(event) {
    event.preventDefault();

    const rollNo = rollNoInput.value.trim();
    const name = nameInput.value.trim();
    const email = emailInput.value.trim();
    const password = passwordInput.value.trim();
    const degree = degreeInput.value.trim();
    const branch = branchInput.value.trim();
    const year = parseInt(yearSelect.value);

    if (!rollNo || !name || !email || !password || !degree || !branch || !year) {
        showMessage('❌ Please fill all fields', 'error');
        return;
    }

    loadingDiv.style.display = 'block';
    submitBtn.disabled = true;

    try {
        const data = await apiCall('/api/auth/register', {
            method: 'POST',
            body: JSON.stringify({
                roll_no: rollNo,
                name,
                email,
                password,
                degree,
                branch,
                year
            })
        });

        // backend error safety
        if (data?.status === "error") {
            throw new Error(data.message || "Registration failed");
        }

        showMessage(`✅ ${data.message || "Student registered successfully"}`, 'success');

        studentRegisterForm.reset();
        rollNoInput.focus();

    } catch (error) {
        console.error(error);
        showMessage(`❌ ${error.message}`, 'error');

    } finally {
        // 🔥 ALWAYS RESET UI
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