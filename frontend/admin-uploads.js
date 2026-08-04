const messageDiv = document.getElementById("message");
const loadingDiv = document.getElementById("loading");
const uploadsListDiv = document.getElementById("uploadsList");

document.addEventListener("DOMContentLoaded", loadUploads);

async function loadUploads() {
    try {
        const data = await apiCall("/api/admin/uploads/pending");

        loadingDiv.style.display = "none";

        if (!data.uploads || data.uploads.length === 0) {
            uploadsListDiv.innerHTML =
                '<p style="color:#666;text-align:center;">No pending uploads</p>';
            return;
        }

        uploadsListDiv.innerHTML = data.uploads.map(upload => `
            <div class="upload-item" id="upload-${upload.upload_id}">
                <div class="upload-info">
                    <p><strong>File:</strong> ${upload.file_name}</p>
                    <p><strong>Teacher:</strong> ${upload.teacher_name}</p>
                    <p><strong>Marks Count:</strong> ${upload.marks_count}</p>
                    <p><strong>Uploaded:</strong> ${new Date(upload.uploaded_at).toLocaleString()}</p>

                    <div class="upload-status status-pending"
                         id="status-${upload.upload_id}">
                        🟡 Pending
                    </div>
                </div>

                <div class="upload-actions"
                     id="actions-${upload.upload_id}">

                    <button class="btn btn-download"
                        onclick="downloadCSV('${upload.upload_id}')">
                        Download
                    </button>

                    <button class="btn btn-approve"
                        onclick="approveUpload('${upload.upload_id}')">
                        Approve
                    </button>

                    <button class="btn btn-reject"
                        onclick="rejectUpload('${upload.upload_id}')">
                        Reject
                    </button>

                </div>
            </div>
        `).join("");

    } catch (error) {
        loadingDiv.style.display = "none";
        showMessage(error.message, "error");
    }
}

async function downloadCSV(uploadId) {

    try {

        const response = await fetch(
            `${API_BASE_URL}/api/admin/uploads/${uploadId}/download`,
            {
                headers: {
                    Authorization: `Bearer ${localStorage.getItem("access_token")}`
                }
            }
        );

        if (!response.ok)
            throw new Error("Download failed");

        const blob = await response.blob();

        const url = window.URL.createObjectURL(blob);

        const a = document.createElement("a");

        a.href = url;
        a.download = "upload.csv";
        a.click();

    } catch (error) {

        showMessage(error.message, "error");

    }
}

async function approveUpload(uploadId) {

    const status = document.getElementById(`status-${uploadId}`);
    const actions = document.getElementById(`actions-${uploadId}`);

    status.className = "upload-status status-processing";
    status.innerHTML = "🔵 Processing...";

    actions.innerHTML = "";

    try {

        const queued = await apiCall(
            `/api/admin/uploads/${uploadId}/approve`,
            {
                method: "POST"
            }
        );

        pollTask(uploadId, queued.task_id);

    } catch (error) {

        setFailure(uploadId, error.message);

    }
}

async function pollTask(uploadId, taskId) {

    try {

        const data = await apiCall(`/api/admin/tasks/${taskId}`);

        if (data.status === "SUCCESS") {

            setSuccess(uploadId, data.result);

        }
        else if (data.status === "FAILURE") {

            setFailure(uploadId, data.error);

        }
        else {

            setTimeout(() => {
                pollTask(uploadId, taskId);
            }, 1500);

        }

    } catch (error) {

        setFailure(uploadId, error.message);

    }

}

function setSuccess(uploadId, result) {

    const status = document.getElementById(`status-${uploadId}`);
    const actions = document.getElementById(`actions-${uploadId}`);

    status.className = "upload-status status-success";

    status.innerHTML = `
        🟢 Approved<br><br>
        Inserted : ${result.inserted}<br>
        Updated : ${result.updated}<br>
        Skipped : ${result.skipped}<br>
        Failed : ${result.failed}
    `;

    actions.innerHTML = `
        <button class="btn btn-dismiss"
            onclick="dismissUpload('${uploadId}')">
            Dismiss
        </button>
    `;
}

function setFailure(uploadId, error) {

    const status = document.getElementById(`status-${uploadId}`);
    const actions = document.getElementById(`actions-${uploadId}`);

    status.className = "upload-status status-failure";

    status.innerHTML = `
        🔴 Approval Failed<br><br>
        ${error}
    `;

    actions.innerHTML = `
        <button class="btn btn-download"
            onclick="downloadCSV('${uploadId}')">
            Download
        </button>

        <button class="btn btn-approve"
            onclick="approveUpload('${uploadId}')">
            Approve Again
        </button>

        <button class="btn btn-reject"
            onclick="rejectUpload('${uploadId}')">
            Reject
        </button>
    `;
}

function dismissUpload(uploadId) {

    document.getElementById(`upload-${uploadId}`).remove();

    if (uploadsListDiv.children.length === 0) {
        uploadsListDiv.innerHTML =
            '<p style="color:#666;text-align:center;">No pending uploads</p>';
    }

}

async function rejectUpload(uploadId) {

    const reason = prompt("Enter rejection reason:");

    if (!reason)
        return;

    try {

        await apiCall(
            `/api/admin/uploads/${uploadId}/reject`,
            {
                method: "POST",
                body: JSON.stringify({
                    reason
                })
            }
        );

        dismissUpload(uploadId);

        showMessage("Upload rejected successfully", "success");

    } catch (error) {

        showMessage(error.message, "error");

    }

}

function showMessage(text, type) {

    messageDiv.textContent = text;
    messageDiv.className = `message ${type}`;

    setTimeout(() => {
        messageDiv.className = "message";
    }, 5000);

}