// ==================== DOM ELEMENTS ====================
const degreeSelect = document.getElementById('degreeSelect');
const branchSelect = document.getElementById('branchSelect');
const yearSelect = document.getElementById('yearSelect');
const semesterSelect = document.getElementById('semesterSelect');
const loadBtn = document.getElementById('loadBtn');
const statsContainer = document.getElementById('statsContainer');
const messageDiv = document.getElementById('message');
const loadingDiv = document.getElementById('loading');

// Store degree list for reference
let degreesList = [];

// ==================== PAGE LOAD ====================
document.addEventListener('DOMContentLoaded', function() {
    console.log('Statistics page loaded');
    
    // Check if logged in as teacher
    const accessToken = localStorage.getItem('access_token');
    const userType = localStorage.getItem('user_type');
    
    if (!accessToken || userType !== 'teacher') {
        window.location.href = 'teacher-login.html';
        return;
    }
    
    // Load degrees on page load
    loadDegrees();
});

// ==================== LOAD DEGREES ====================
async function loadDegrees() {
    try {
        console.log('Loading degrees...');

        degreeSelect.innerHTML = '<option value="">Loading degrees...</option>';

        const response = await apiCall('/api/results/degrees');

        console.log("Degrees raw response:", response);

        if (!response) {
            throw new Error("No response from server");
        }

        if (response.status === "error" || response.detail) {
            throw new Error(response.message || response.detail || "Failed to load degrees");
        }

        const degrees = Array.isArray(response)
            ? response
            : response.data || response.results;

        if (!degrees || degrees.length === 0) {
            degreeSelect.innerHTML = '<option value="">No degrees found</option>';
            return;
        }

        degreesList = degrees;

        degreeSelect.innerHTML = '<option value="">Select Degree</option>';

        degreesList.forEach(degree => {
            const option = document.createElement('option');
            option.value = degree.id;
            option.textContent = degree.name;
            degreeSelect.appendChild(option);
        });

    } catch (error) {
        console.error('Error loading degrees:', error);
        degreeSelect.innerHTML = '<option value="">Failed to load degrees</option>';
        showMessage(`❌ ${error.message}`, 'error');
    }
}

// ==================== ON DEGREE CHANGE ====================
async function onDegreeChange() {
    const degreeId = degreeSelect.value;

    if (!degreeId) {
        branchSelect.innerHTML = '<option value="">Select degree first</option>';
        return;
    }

    try {
        console.log('Loading branches for degree:', degreeId);

        const response = await apiCall(`/api/results/branches?degree_id=${degreeId}`);

        console.log("Branches raw response:", response);

        if (!response) {
            throw new Error("Failed to load branches");
        }

        if (response.status === "error" || response.detail) {
            throw new Error(response.message || response.detail || "Failed to load branches");
        }

        const branches = Array.isArray(response)
            ? response
            : response.data || response.results || [];

        branchSelect.innerHTML = '<option value="">Select Branch</option>';
        branchSelect.innerHTML += '<option value="all">All Branches</option>';

        branches.forEach(branch => {
            const option = document.createElement('option');
            option.value = branch.id;
            option.textContent = branch.name;
            branchSelect.appendChild(option);
        });

    } catch (error) {
        console.error('Error loading branches:', error);
        showMessage(`❌ ${error.message}`, 'error');
    }
}

// ==================== LOAD STATISTICS ====================
async function loadStatistics() {
    const degreeId = degreeSelect.value;
    const branchId = branchSelect.value === 'all' ? null : branchSelect.value;
    const year = yearSelect.value;
    const semester = semesterSelect.value;
    
    // Validate
    if (!degreeId || !year || !semester) {
        showMessage('❌ Please select degree, batch year, and semester', 'error');
        return;
    }
    
    loadingDiv.style.display = 'block';
    loadBtn.disabled = true;
    statsContainer.innerHTML = '';
    
    try {
        console.log(`Loading statistics: degree=${degreeId}, year=${year}, semester=${semester}, branch=${branchId}`);
        
        let url = `/api/results/statistics?degree_id=${degreeId}&year=${year}&semester=${semester}`;
        if (branchId) {
            url += `&branch_id=${branchId}`;
        }
        
        const response = await apiCall(url);

        console.log("Stats raw response:", response);

        if (!response) {
            showMessage('❌ Failed to load statistics', 'error');
            loadingDiv.style.display = 'none';
            loadBtn.disabled = false;
            return;
        }

        // backend error safety
        if (response.status === "error" || response.detail) {
            showMessage(`❌ ${response.message || response.detail || 'Failed to load statistics'}`, 'error');
            loadingDiv.style.display = 'none';
            loadBtn.disabled = false;
            return;
        }

        // normalize data
        const data = response.data || response;
        console.log('Statistics data:', data);
        
        displayStatistics(data);
        showMessage(`✅ Statistics loaded`, 'info');
        
    } catch (error) {
        console.error('Error loading statistics:', error);
        showMessage(`❌ Error: ${error.message}`, 'error');
    } finally {
        loadingDiv.style.display = 'none';
        loadBtn.disabled = false;
    }
}

// ==================== DISPLAY STATISTICS ====================
function displayStatistics(data) {
    const sgpaDistribution = data.sgpa_distribution || {};
    const maxDistCount = Math.max(...Object.values(sgpaDistribution), 1);
    
    // Get degree and branch names
    const degreeName = degreesList.find(d => d.id === data.degree_id)?.name || 'Unknown';
    let branchInfo = data.branch_id ? ` - ${data.branch_id}` : ' (All Branches)';
    
    statsContainer.innerHTML = `
        <div class="stats-card">
            <h2>${degreeName}, Batch ${data.year}, Semester ${data.semester}${branchInfo}</h2>
            <div class="stats-grid">
                <div class="stat-item">
                    <h3>Total Students</h3>
                    <div class="value">${data.total_students}</div>
                </div>
                <div class="stat-item">
                    <h3>Pass Percentage</h3>
                    <div class="value">${data.pass_percentage}%</div>
                </div>
                <div class="stat-item">
                    <h3>Highest SGPA</h3>
                    <div class="value">${data.highest_sgpa}</div>
                </div>
                <div class="stat-item">
                    <h3>Average SGPA</h3>
                    <div class="value">${data.average_sgpa}</div>
                </div>
                <div class="stat-item">
                    <h3>Lowest SGPA</h3>
                    <div class="value">${data.lowest_sgpa}</div>
                </div>
            </div>
        </div>
        
        <div class="stats-card">
            <h2>Top 10 Students</h2>
            <div style="overflow-x: auto;">
                <table style="width: 100%; border-collapse: collapse;">
                    <thead>
                        <tr style="background: #f0f0f0;">
                            <th style="padding: 12px; text-align: left; border-bottom: 2px solid #667eea;">Rank</th>
                            <th style="padding: 12px; text-align: left; border-bottom: 2px solid #667eea;">Roll No</th>
                            <th style="padding: 12px; text-align: left; border-bottom: 2px solid #667eea;">SGPA</th>
                            <th style="padding: 12px; text-align: left; border-bottom: 2px solid #667eea;">Status</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${data.top_10_students.map((student, index) => `
                            <tr style="border-bottom: 1px solid #ddd;">
                                <td style="padding: 12px;">${index + 1}</td>
                                <td style="padding: 12px;">${student.roll_no}</td>
                                <td style="padding: 12px; font-weight: 600; color: #667eea;">${student.sgpa}</td>
                                <td style="padding: 12px;">
                                    <span style="padding: 4px 8px; border-radius: 4px; font-size: 12px; 
                                        ${student.status === 'pass' ? 'background: #d4edda; color: #155724;' : 
                                          student.status === 'pass_with_backlog' ? 'background: #fff3cd; color: #856404;' : 
                                          'background: #f8d7da; color: #721c24;'}">
                                        ${student.status.replace(/_/g, ' ')}
                                    </span>
                                </td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            </div>
        </div>
        
        <div class="stats-card">
            <h2>SGPA Distribution</h2>
            <div class="grade-bars">
                ${Object.entries(sgpaDistribution).map(([range, count]) => {
                    const percentage = (count / maxDistCount) * 100;
                    return `
                        <div class="grade-bar">
                            <div class="grade-label">${range}</div>
                            <div class="grade-progress">
                                <div class="grade-progress-bar" style="width: ${percentage}%">
                                    ${count}
                                </div>
                            </div>
                        </div>
                    `;
                }).join('')}
            </div>
        </div>
        
        <div class="stats-card">
            <h2>Subject-wise Failure Count (Points < 6.0)</h2>
            <div style="overflow-x: auto;">
                <table style="width: 100%; border-collapse: collapse;">
                    <thead>
                        <tr style="background: #f0f0f0;">
                            <th style="padding: 12px; text-align: left; border-bottom: 2px solid #667eea;">Subject</th>
                            <th style="padding: 12px; text-align: left; border-bottom: 2px solid #667eea;">Failures</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${Object.entries(data.subject_wise_failures).length > 0 ? 
                            Object.entries(data.subject_wise_failures).map(([subject, count]) => `
                                <tr style="border-bottom: 1px solid #ddd;">
                                    <td style="padding: 12px;">${subject}</td>
                                    <td style="padding: 12px; font-weight: 600; color: #721c24;">${count}</td>
                                </tr>
                            `).join('') : 
                            '<tr><td colspan="2" style="padding: 12px; text-align: center; color: #666;">No failures in this semester</td></tr>'
                        }
                    </tbody>
                </table>
            </div>
        </div>
    `;
}

// ==================== SHOW MESSAGE ====================
function showMessage(text, type) {
    messageDiv.textContent = text;
    messageDiv.className = `message ${type}`;
    messageDiv.style.display = 'block';
    
    if (type === 'info') {
        setTimeout(() => {
            messageDiv.style.display = 'none';
        }, 5000);
    }
}