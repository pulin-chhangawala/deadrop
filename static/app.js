/*
 * deadrop - frontend JavaScript
 * Handles drag-and-drop upload, progress tracking, and clipboard copy.
 */

const dropZone = document.getElementById('drop-zone');
const fileInput = document.getElementById('file-input');
const options = document.getElementById('options');
const uploadBtn = document.getElementById('upload-btn');
const progress = document.getElementById('progress');
const progressFill = document.getElementById('progress-fill');
const progressText = document.getElementById('progress-text');
const result = document.getElementById('result');
const downloadLink = document.getElementById('download-link');
const copyBtn = document.getElementById('copy-btn');
const anotherBtn = document.getElementById('another-btn');

let selectedFile = null;

// --- drag and drop ---

dropZone.addEventListener('click', () => fileInput.click());

dropZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropZone.classList.add('dragover');
});

dropZone.addEventListener('dragleave', () => {
    dropZone.classList.remove('dragover');
});

dropZone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropZone.classList.remove('dragover');
    
    if (e.dataTransfer.files.length > 0) {
        selectFile(e.dataTransfer.files[0]);
    }
});

fileInput.addEventListener('change', () => {
    if (fileInput.files.length > 0) {
        selectFile(fileInput.files[0]);
    }
});

function selectFile(file) {
    selectedFile = file;
    
    // update drop zone appearance
    dropZone.classList.add('has-file');
    const content = dropZone.querySelector('.drop-zone-content p');
    const sizeStr = file.size > 1024 * 1024 
        ? `${(file.size / (1024 * 1024)).toFixed(1)} MB`
        : `${(file.size / 1024).toFixed(1)} KB`;
    content.textContent = `${file.name} (${sizeStr})`;
    
    // show options
    options.classList.remove('hidden');
}

// --- upload ---

uploadBtn.addEventListener('click', async () => {
    if (!selectedFile) return;
    
    // hide options, show progress
    options.classList.add('hidden');
    dropZone.classList.add('hidden');
    progress.classList.remove('hidden');
    
    const formData = new FormData();
    formData.append('file', selectedFile);
    formData.append('expiry', document.getElementById('expiry').value);
    formData.append('max_downloads', document.getElementById('max-downloads').value);
    
    try {
        const xhr = new XMLHttpRequest();
        
        xhr.upload.addEventListener('progress', (e) => {
            if (e.lengthComputable) {
                const pct = Math.round((e.loaded / e.total) * 100);
                progressFill.style.width = `${pct}%`;
                progressText.textContent = `uploading... ${pct}%`;
            }
        });
        
        xhr.addEventListener('load', () => {
            if (xhr.status === 200) {
                const data = JSON.parse(xhr.responseText);
                showResult(data);
            } else {
                const err = JSON.parse(xhr.responseText);
                progressText.textContent = `error: ${err.error || 'upload failed'}`;
                progressText.style.color = '#f87171';
            }
        });
        
        xhr.addEventListener('error', () => {
            progressText.textContent = 'network error: is the server running?';
            progressText.style.color = '#f87171';
        });
        
        xhr.open('POST', '/upload');
        xhr.send(formData);
        
    } catch (err) {
        progressText.textContent = `error: ${err.message}`;
        progressText.style.color = '#f87171';
    }
});

function showResult(data) {
    progress.classList.add('hidden');
    result.classList.remove('hidden');
    
    downloadLink.value = data.url;
    
    const meta = document.getElementById('result-meta');
    const sizeStr = data.size > 1024 * 1024
        ? `${(data.size / (1024 * 1024)).toFixed(1)} MB`
        : `${(data.size / 1024).toFixed(1)} KB`;
    meta.textContent = `${sizeStr} • expires in ${data.expires_in} • ${data.max_downloads} download(s)`;
}

// --- clipboard ---

copyBtn.addEventListener('click', async () => {
    try {
        await navigator.clipboard.writeText(downloadLink.value);
        copyBtn.textContent = 'copied!';
        setTimeout(() => { copyBtn.textContent = 'copy'; }, 2000);
    } catch {
        // fallback for older browsers
        downloadLink.select();
        document.execCommand('copy');
        copyBtn.textContent = 'copied!';
        setTimeout(() => { copyBtn.textContent = 'copy'; }, 2000);
    }
});

// --- reset ---

anotherBtn.addEventListener('click', () => {
    result.classList.add('hidden');
    dropZone.classList.remove('hidden', 'has-file');
    
    const content = dropZone.querySelector('.drop-zone-content p');
    content.innerHTML = 'drop a file here or <span class="browse-link">browse</span>';
    
    selectedFile = null;
    fileInput.value = '';
    progressFill.style.width = '0%';
    progressText.style.color = '';
});
